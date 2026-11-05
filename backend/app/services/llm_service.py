"""
LLM Service
Supports Anthropic Claude and OpenAI with tool use and streaming.
"""

import json
from typing import Any, AsyncGenerator

import anthropic
import openai
import structlog

from ..core.config import settings

log = structlog.get_logger()


class LLMService:
    """Multi-provider LLM service with tool calling and streaming."""

    BASE_SYSTEM_PROMPT = """You are a helpful general-purpose AI assistant with access to Gmail and web search tools.

HOW TO DECIDE WHAT TO DO:
- Email questions (read inbox, search emails, send, reply, etc.) → use Gmail tools.
- Truly real-time data only you cannot know (today's live stock price, breaking news in the last hour, etc.) → use web_search.
- General knowledge, software concepts, version numbers, how-things-work → answer directly from your training. Do NOT call web_search for things you already know.
- Conversational messages (hi, thanks, etc.) → respond normally without any tools.

WHEN web_search RETURNS AN ERROR OR EMPTY RESULTS:
- Do NOT say "could not be found". Instead, answer the question from your own training knowledge.

CRITICAL RULES:
1. NEVER say "Gmail is not connected" if you have Gmail tools available — use them.
2. NEVER make up email content. Always call the tool and report real results.
3. NEVER ask the user for their Gmail password or credentials.
4. After a tool returns results, summarize clearly and concisely.
5. For destructive actions (send, delete), confirm with the user first.
"""

    @staticmethod
    def _build_system_prompt(available_tools: list[dict]) -> str:
        prompt = LLMService.BASE_SYSTEM_PROMPT
        gmail_tools = [t["name"] for t in available_tools if t.get("server_type") != "_builtin"]
        builtin_tools = [t["name"] for t in available_tools if t.get("server_type") == "_builtin"]

        if gmail_tools:
            prompt += f"\nGmail tools available: {', '.join(gmail_tools)}"
        else:
            prompt += "\nNo Gmail tools connected. If user asks about email, tell them to connect Gmail in MCP Manager."

        if builtin_tools:
            prompt += f"\nBuilt-in tools available: {', '.join(builtin_tools)}"

        if available_tools:
            prompt += "\n\nUse the tools above — do not guess or hallucinate results."
        return prompt

    def __init__(self, provider: str = "anthropic", model: str = None):
        self.provider = provider

        if provider == "anthropic":
            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = model or settings.default_model
        elif provider == "openai":
            self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = model or "gpt-4o"
        elif provider == "groq":
            self._openai = openai.AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
            self.model = settings.groq_model  # always from config, never from DB
        elif provider == "ollama":
            self._openai = openai.AsyncOpenAI(
                base_url=f"{settings.ollama_base_url}/v1",
                api_key="ollama",
            )
            self.model = settings.ollama_model  # always from config, never from DB
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def _convert_tools_for_anthropic(self, tools: list[dict]) -> list[dict]:
        """Convert MCP tool definitions to Anthropic tool format."""
        converted = []
        for tool in tools:
            schema = tool.get("input_schema") or tool.get("inputSchema", {})
            converted.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": schema or {
                    "type": "object",
                    "properties": {},
                },
            })
        return converted

    def _convert_tools_for_openai(self, tools: list[dict]) -> list[dict]:
        """Convert MCP tool definitions to OpenAI function format."""
        converted = []
        for tool in tools:
            schema = tool.get("input_schema") or tool.get("inputSchema", {})
            converted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": schema or {"type": "object", "properties": {}},
                },
            })
        return converted

    async def chat_stream(
        self,
        messages: list[dict],
        available_tools: list[dict],
        execute_tool_fn,
        tool_metadata: dict[str, dict],
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat responses with tool calling support.
        Yields events: {'type': 'text'|'tool_call'|'tool_result'|'done', ...}
        """
        if self.provider == "anthropic":
            async for event in self._anthropic_stream(
                messages, available_tools, execute_tool_fn, tool_metadata
            ):
                yield event
        elif self.provider in ("openai", "groq", "ollama"):
            async for event in self._openai_stream(
                messages, available_tools, execute_tool_fn, tool_metadata
            ):
                yield event

    async def _anthropic_stream(
        self,
        messages: list[dict],
        available_tools: list[dict],
        execute_tool_fn,
        tool_metadata: dict[str, dict],
    ) -> AsyncGenerator[dict, None]:
        """Anthropic Claude streaming with multi-turn tool use."""
        converted_tools = self._convert_tools_for_anthropic(available_tools)
        working_messages = list(messages)
        tool_call_count = 0

        while tool_call_count < settings.max_tool_calls_per_turn:
            stream_kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self._build_system_prompt(available_tools),
                "messages": working_messages,
            }
            if converted_tools:
                stream_kwargs["tools"] = converted_tools

            full_text = ""
            tool_uses = []

            async with self._anthropic.messages.stream(**stream_kwargs) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                full_text += event.delta.text
                                yield {"type": "text", "content": event.delta.text}
                        elif event.type == "content_block_start":
                            if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                                tool_uses.append({
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input": {},
                                })
                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, "partial_json") and tool_uses:
                                tool_uses[-1]["input_raw"] = tool_uses[-1].get("input_raw", "") + event.delta.partial_json

                message = await stream.get_final_message()

            # Parse tool use inputs
            for block in message.content:
                if block.type == "tool_use":
                    tool_uses_final = []
                    tool_uses_final.append({"id": block.id, "name": block.name, "input": block.input})

            if message.stop_reason != "tool_use":
                yield {"type": "done", "stop_reason": message.stop_reason}
                break

            # Execute tools
            tool_results = []
            for block in message.content:
                if block.type != "tool_use":
                    continue

                tool_call_count += 1
                tool_name = block.name
                tool_args = block.input

                yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

                meta = tool_metadata.get(tool_name, {})
                try:
                    result = await execute_tool_fn(
                        tool_name=tool_name,
                        arguments=tool_args,
                        server_type=meta.get("server_type", ""),
                        base_url=meta.get("server_url", ""),
                    )
                    result_str = json.dumps(result)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result_str})
                    yield {"type": "tool_result", "tool": tool_name, "result": result, "success": True}
                except Exception as e:
                    error_str = str(e)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {error_str}", "is_error": True})
                    yield {"type": "tool_result", "tool": tool_name, "result": {"error": error_str}, "success": False}

            # Build next turn messages
            working_messages.append({"role": "assistant", "content": message.content})
            working_messages.append({"role": "user", "content": tool_results})

        if tool_call_count >= settings.max_tool_calls_per_turn:
            yield {"type": "text", "content": "\n[Max tool call limit reached]"}
            yield {"type": "done", "stop_reason": "max_tools"}

    async def _openai_stream(
        self,
        messages: list[dict],
        available_tools: list[dict],
        execute_tool_fn,
        tool_metadata: dict[str, dict],
    ) -> AsyncGenerator[dict, None]:
        """OpenAI streaming with function calling."""
        converted_tools = self._convert_tools_for_openai(available_tools)
        working_messages = [{"role": "system", "content": self._build_system_prompt(available_tools)}] + list(messages)
        tool_call_count = 0

        while tool_call_count < settings.max_tool_calls_per_turn:
            kwargs: dict[str, Any] = {
                "model": self.model or "gpt-4o",
                "messages": working_messages,
                "stream": True,
            }
            if converted_tools:
                kwargs["tools"] = converted_tools
                kwargs["tool_choice"] = "auto"

            collected_tool_calls: dict[int, dict] = {}
            full_text = ""
            finish_reason = None

            try:
                stream = await self._openai.chat.completions.create(**kwargs)

                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    finish_reason = chunk.choices[0].finish_reason

                    if delta.content:
                        full_text += delta.content
                        yield {"type": "text", "content": delta.content}

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in collected_tool_calls:
                                collected_tool_calls[idx] = {"id": tc.id, "name": "", "arguments": ""}
                            if tc.function:
                                if tc.function.name:
                                    collected_tool_calls[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    collected_tool_calls[idx]["arguments"] += tc.function.arguments

            except Exception as e:
                # Groq sometimes fails with "Failed to call a function" when it generates
                # malformed tool-call JSON. Retry once without tools so the user gets an answer.
                if "Failed to call a function" in str(e) or "failed_generation" in str(e):
                    log.warning("Function call generation failed, retrying without tools", error=str(e))
                    fallback_kwargs = {k: v for k, v in kwargs.items() if k not in ("tools", "tool_choice")}
                    fallback_stream = await self._openai.chat.completions.create(**fallback_kwargs)
                    async for chunk in fallback_stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            yield {"type": "text", "content": delta.content}
                    yield {"type": "done", "stop_reason": "stop"}
                    return
                raise

            if finish_reason != "tool_calls" or not collected_tool_calls:
                yield {"type": "done", "stop_reason": finish_reason}
                break

            tool_call_message = {
                "role": "assistant",
                "content": full_text or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in collected_tool_calls.values()
                ],
            }
            working_messages.append(tool_call_message)

            for tc in collected_tool_calls.values():
                tool_call_count += 1
                try:
                    args = json.loads(tc["arguments"])
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "tool": tc["name"], "args": args}

                meta = tool_metadata.get(tc["name"], {})
                try:
                    result = await execute_tool_fn(
                        tool_name=tc["name"],
                        arguments=args,
                        server_type=meta.get("server_type", ""),
                        base_url=meta.get("server_url", ""),
                    )
                    result_str = json.dumps(result)
                    yield {"type": "tool_result", "tool": tc["name"], "result": result, "success": True}
                except Exception as e:
                    result_str = f"Error: {e}"
                    yield {"type": "tool_result", "tool": tc["name"], "result": {"error": str(e)}, "success": False}

                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                })
