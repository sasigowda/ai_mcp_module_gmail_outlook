"""
Web search utility using DuckDuckGo (no API key required).
"""

import asyncio
from typing import Any

import structlog

log = structlog.get_logger()

TOOL_DEFINITION = {
    "name": "web_search",
    "description": (
        "Search the internet for current information, facts, news, documentation, "
        "or anything that is not in the user's email. Use this for general questions "
        "like 'what is AWS', 'latest Python version', 'today's news', etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string",
            }
        },
        "required": ["query"],
    },
    "server_type": "_builtin",
    "server_url": "",
    "server_id": "_builtin",
}


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Run a DuckDuckGo text search and return top results."""
    try:
        from duckduckgo_search import DDGS

        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        results = await asyncio.to_thread(_search)

        if not results:
            return {
                "query": query,
                "results": [],
                "note": "No web results found. Please answer from your training knowledge.",
            }

        formatted = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
        return {"query": query, "results": formatted}

    except Exception as e:
        log.warning("Web search failed", query=query, error=str(e))
        return {
            "query": query,
            "results": [],
            "note": "Web search is temporarily unavailable. Please answer this question from your training knowledge instead.",
        }
