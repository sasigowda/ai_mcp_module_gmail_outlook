"use client";

import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Wrench, CheckCircle2, XCircle, Loader2, Bot, User } from "lucide-react";
import type { ChatMessageLocal } from "@/lib/store";
import type { StreamEvent } from "@/types";

interface Props {
  message: ChatMessageLocal;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 w-full mb-6 group", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
          isUser
            ? "bg-primary/20 border border-primary/30"
            : "bg-accent border border-border"
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-primary" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </div>

      <div className={cn("flex flex-col gap-2 max-w-[78%]", isUser && "items-end")}>
        {/* Tool call/result cards — shown before the text response */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="flex flex-col gap-1.5 w-full">
            {(message.tool_calls as StreamEvent[]).map((event, i) => (
              <ToolEventCard key={i} event={event} />
            ))}
          </div>
        )}

        {/* Message content */}
        {message.content && (
          <div className={isUser ? "chat-bubble-user" : "chat-bubble-assistant"}>
            {isUser ? (
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
            ) : (
              <div className="prose-dark">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
                {message.isStreaming && <BlinkCursor />}
              </div>
            )}
          </div>
        )}

        {/* Streaming placeholder when no content yet */}
        {message.isStreaming && !message.content && (
          <div className="chat-bubble-assistant flex items-center gap-2">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>
    </div>
  );
}

function ToolEventCard({ event }: { event: StreamEvent }) {
  if (event.type === "tool_call") {
    return (
      <div className="tool-card tool-card-calling w-full">
        <div className="tool-card-header">
          <div className="flex items-center gap-1.5" style={{ color: "hsl(var(--primary))" }}>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span className="font-semibold text-xs">Calling tool</span>
          </div>
          <span
            className="ml-auto font-mono text-xs px-2 py-0.5 rounded"
            style={{ background: "hsl(var(--primary) / 0.1)", color: "hsl(var(--primary))" }}
          >
            {event.tool}
          </span>
        </div>
        {event.args && Object.keys(event.args).length > 0 && (
          <div className="tool-card-body">
            <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(event.args, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  }

  if (event.type === "tool_result") {
    const success = (event as { success: boolean }).success;
    return (
      <div className={cn("tool-card", success ? "tool-card-success" : "tool-card-error")}>
        <div className="tool-card-header">
          <div
            className="flex items-center gap-1.5"
            style={{ color: success ? "hsl(var(--success))" : "hsl(var(--destructive))" }}
          >
            {success ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <XCircle className="h-3.5 w-3.5" />
            )}
            <span className="font-semibold text-xs">{success ? "Tool completed" : "Tool failed"}</span>
          </div>
          <span
            className="ml-auto font-mono text-xs px-2 py-0.5 rounded"
            style={{
              background: success
                ? "hsl(var(--success) / 0.1)"
                : "hsl(var(--destructive) / 0.1)",
              color: success ? "hsl(var(--success))" : "hsl(var(--destructive))",
            }}
          >
            {(event as { tool: string }).tool}
          </span>
        </div>
        <div className="tool-card-body">
          <pre className="whitespace-pre-wrap text-xs">
            {JSON.stringify((event as { result: unknown }).result, null, 2)}
          </pre>
        </div>
      </div>
    );
  }

  return null;
}

function BlinkCursor() {
  return (
    <span
      className="inline-block w-0.5 h-4 ml-0.5 align-middle rounded-full animate-pulse"
      style={{ background: "hsl(var(--primary))" }}
    />
  );
}
