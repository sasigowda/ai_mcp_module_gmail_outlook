"use client";

import { useEffect, useRef, useState } from "react";
import { Send, ChevronDown, Zap, Mail, Search, ArrowUp } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { useChatStore, useMCPStore } from "@/lib/store";
import { chat } from "@/lib/api";
import type { StreamEvent } from "@/types";
import { cn } from "@/lib/utils";

interface Props {
  conversationId: string | null;
  onConversationCreated?: (id: string) => void;
}

const SUGGESTIONS = [
  { icon: Mail, label: "Check unread emails", prompt: "What are my unread emails?" },
  { icon: Send, label: "Send an email", prompt: "Send an email to " },
  { icon: Search, label: "Search emails", prompt: "Search my emails for " },
  { icon: Zap, label: "Summarize inbox", prompt: "Give me a summary of my recent emails" },
];

export function ChatInterface({ conversationId, onConversationCreated }: Props) {
  const [input, setInput] = useState("");
  const [isAtBottom, setIsAtBottom] = useState(true);

  // displayId tracks what we're showing — may be "pending" before the real conv exists
  const [displayId, setDisplayId] = useState<string | null>(conversationId);

  const endRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    isStreaming, setStreaming,
    messages, addMessage, appendStream, finalizeStream, migrateMessages,
    activeConversationId,
  } = useChatStore();
  const { servers } = useMCPStore();

  // Sync displayId when parent switches conversation
  useEffect(() => {
    setDisplayId(conversationId ?? activeConversationId);
  }, [conversationId, activeConversationId]);

  const convMessages = displayId ? (messages[displayId] || []) : [];
  const connectedCount = servers.filter((s) => s.is_connected).length;

  // Auto-scroll when new content arrives
  useEffect(() => {
    if (isAtBottom) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [convMessages, isAtBottom]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setIsAtBottom(el.scrollHeight - el.clientHeight - el.scrollTop < 100);
  };

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  };

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || isStreaming) return;

    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setStreaming(true);
    setIsAtBottom(true);

    // Use a stable pending key for new conversations, or the real conv ID
    const existingId = conversationId ?? activeConversationId;
    const pendingKey = existingId ?? `pending_${Date.now()}`;

    // Show user message immediately
    addMessage(pendingKey, {
      id: `user_${Date.now()}`,
      role: "user",
      content: msg,
    });
    setDisplayId(pendingKey);

    try {
      let resolvedId = existingId;

      for await (const event of chat.sendMessageStream({
        message: msg,
        conversation_id: existingId ?? undefined,
      })) {
        if (event.type === "conversation_id") {
          resolvedId = event.id;

          // Migrate pending messages → real conv ID, then switch display
          if (!existingId && pendingKey !== resolvedId) {
            migrateMessages(pendingKey, resolvedId);
          }
          setDisplayId(resolvedId);
          onConversationCreated?.(resolvedId);

        } else if (event.type === "text") {
          appendStream(resolvedId ?? pendingKey, event.content);

        } else if (event.type === "done") {
          finalizeStream(
            resolvedId ?? pendingKey,
            event.message_id ?? `msg_${Date.now()}`,
          );
        }
      }
    } catch (err) {
      const errId = displayId ?? pendingKey;
      addMessage(errId, {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `**Error:** ${err instanceof Error ? err.message : "Something went wrong. Please try again."}`,
      });
    } finally {
      setStreaming(false);
      // Scroll to bottom after response
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const scrollToBottom = () => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
    setIsAtBottom(true);
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* ── Header bar ─────────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-3 px-6 py-3 border-b border-border flex-shrink-0"
        style={{ background: "hsl(222 47% 6%)" }}
      >
        <Zap className="h-3.5 w-3.5" style={{ color: "hsl(var(--primary))" }} />
        <span className="text-xs font-medium text-foreground">Active Session</span>
        <span className="text-border text-xs">·</span>
        <span
          className="text-[10px] font-mono px-1.5 py-0.5 rounded"
          style={{ background: "hsl(var(--primary) / 0.1)", color: "hsl(var(--primary))" }}
        >
          groq / llama-3.3-70b
        </span>
        <span className="text-border text-xs">·</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className={cn("status-dot", connectedCount > 0 ? "connected" : "disconnected")} />
          {connectedCount > 0
            ? `${connectedCount} service${connectedCount > 1 ? "s" : ""} connected`
            : "No services — connect in MCP Manager"}
        </span>
      </div>

      {/* ── Messages area ──────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6"
        style={{ background: "hsl(var(--background))" }}
      >
        {convMessages.length === 0 ? (
          <EmptyState connectedCount={connectedCount} onSuggestion={(s) => { setInput(s); textareaRef.current?.focus(); }} />
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {convMessages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {/* Extra padding so last message isn't hidden behind input */}
            <div className="h-4" />
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* ── Scroll to bottom ───────────────────────────────────────────── */}
      {!isAtBottom && convMessages.length > 0 && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-28 right-6 p-2 rounded-full border border-border shadow-xl transition-all hover:border-primary/30 z-10"
          style={{ background: "hsl(var(--card))" }}
        >
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </button>
      )}

      {/* ── Input area ─────────────────────────────────────────────────── */}
      <div
        className="px-4 py-4 border-t border-border flex-shrink-0"
        style={{ background: "hsl(222 47% 6%)" }}
      >
        <div className="max-w-3xl mx-auto">
          <div className="chat-input-wrapper flex items-end gap-3 px-4 py-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); autoResize(); }}
              onKeyDown={handleKeyDown}
              placeholder={
                connectedCount > 0
                  ? "Ask anything — I can send emails, read your inbox…"
                  : "Connect a service in MCP Manager, then chat here…"
              }
              className="flex-1 bg-transparent resize-none outline-none text-sm text-foreground placeholder:text-muted-foreground/60 min-h-[22px] max-h-[180px] leading-relaxed"
              rows={1}
              disabled={isStreaming}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className={cn(
                "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200",
                input.trim() && !isStreaming ? "opacity-100 cursor-pointer" : "opacity-25 cursor-not-allowed"
              )}
              style={{
                background: input.trim() && !isStreaming
                  ? "linear-gradient(135deg, hsl(var(--primary)), hsl(217 91% 52%))"
                  : "hsl(var(--secondary))",
                boxShadow: input.trim() && !isStreaming ? "0 4px 12px hsl(var(--primary) / 0.35)" : "none",
              }}
            >
              <ArrowUp className="h-4 w-4" style={{ color: "hsl(var(--primary-foreground))" }} />
            </button>
          </div>
          <p className="text-center text-[10px] text-muted-foreground/40 mt-2">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  connectedCount,
  onSuggestion,
}: {
  connectedCount: number;
  onSuggestion: (s: string) => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[420px] text-center px-6 select-none">
      <div
        className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 relative"
        style={{
          background: "linear-gradient(135deg, hsl(217 91% 60% / 0.12), hsl(217 91% 60% / 0.04))",
          border: "1px solid hsl(217 91% 60% / 0.2)",
          boxShadow: "0 0 60px hsl(217 91% 60% / 0.08)",
        }}
      >
        <Zap className="h-9 w-9" style={{ color: "hsl(var(--primary))" }} />
      </div>

      <h2 className="text-2xl font-bold text-foreground mb-2 tracking-tight">ChatbotMCP</h2>
      <p className="text-sm text-muted-foreground max-w-xs mb-8 leading-relaxed">
        {connectedCount > 0
          ? `${connectedCount} service${connectedCount > 1 ? "s" : ""} ready. Ask me anything about your emails.`
          : "Your AI assistant is ready. Connect Gmail in MCP Manager to unlock email capabilities."}
      </p>

      {connectedCount > 0 ? (
        <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
          {SUGGESTIONS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              onClick={() => onSuggestion(prompt)}
              className="group flex items-center gap-2.5 px-4 py-3 rounded-xl text-left text-sm transition-all duration-200"
              style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "hsl(var(--primary) / 0.35)";
                (e.currentTarget as HTMLElement).style.background = "hsl(var(--accent))";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "hsl(var(--border))";
                (e.currentTarget as HTMLElement).style.background = "hsl(var(--card))";
              }}
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: "hsl(var(--primary) / 0.1)" }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: "hsl(var(--primary))" }} />
              </div>
              <span className="text-xs font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                {label}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div
          className="flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm"
          style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
        >
          <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: "hsl(var(--primary) / 0.1)" }}>
            <Zap className="h-3 w-3" style={{ color: "hsl(var(--primary))" }} />
          </div>
          <span className="text-xs text-muted-foreground">
            Go to <strong className="text-foreground">MCP Manager</strong> to connect Gmail
          </span>
        </div>
      )}
    </div>
  );
}
