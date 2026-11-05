"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus, MessageSquare, LayoutDashboard, LogOut,
  Bot, ChevronRight, Sparkles,
} from "lucide-react";
import { useChatStore, useAuthStore, useMCPStore } from "@/lib/store";
import { chat, auth, mcp } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { getServerIcon } from "@/lib/utils";

interface Props {
  activeConvId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
}

export function Sidebar({ activeConvId, onSelectConversation, onNewConversation }: Props) {
  const { conversations, setConversations } = useChatStore();
  const { user, logout } = useAuthStore();
  const { servers, setServers } = useMCPStore();
  const [pathname, setPathname] = useState("/");

  useEffect(() => {
    setPathname(window.location.pathname);
    chat.listConversations().then(setConversations).catch(() => {});
    mcp.listServers().then(setServers).catch(() => {});
  }, []);

  const handleLogout = async () => {
    try { await auth.logout(); } catch {}
    logout();
    window.location.href = "/auth/login";
  };

  const connectedServers = servers.filter((s) => s.is_connected);
  const initials = user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "?";

  return (
    <aside
      className="flex flex-col h-full flex-shrink-0 border-r border-border relative"
      style={{
        background: "linear-gradient(180deg, hsl(222 47% 6%) 0%, hsl(224 71% 4%) 100%)",
        width: "var(--sidebar-w)",
      }}
    >
      {/* Subtle top glow accent */}
      <div
        className="absolute top-0 left-0 right-0 h-px opacity-60"
        style={{ background: "linear-gradient(90deg, transparent, hsl(var(--primary) / 0.5), transparent)" }}
      />

      {/* ── Brand header ───────────────────────────────────────────────── */}
      <div className="px-4 pt-5 pb-4 border-b border-border">
        <div className="flex items-center gap-3 mb-5">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{
              background: "linear-gradient(135deg, hsl(217 91% 60% / 0.2), hsl(217 91% 60% / 0.05))",
              border: "1px solid hsl(217 91% 60% / 0.3)",
              boxShadow: "0 0 20px hsl(217 91% 60% / 0.1)",
            }}
          >
            <Bot className="h-4.5 w-4.5" style={{ color: "hsl(var(--primary))" }} />
          </div>
          <div>
            <p className="text-sm font-bold text-foreground tracking-tight leading-none">ChatbotMCP</p>
            <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
              <Sparkles className="h-2.5 w-2.5" style={{ color: "hsl(var(--primary))" }} />
              AI Command Center
            </p>
          </div>
        </div>

        <button
          onClick={onNewConversation}
          className="btn-primary-glow w-full flex items-center justify-center gap-2 px-3 py-2.5"
          style={{
            color: "hsl(var(--primary-foreground))",
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          <span className="text-sm font-semibold">New Conversation</span>
        </button>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────────── */}
      <div className="px-3 py-3 border-b border-border space-y-0.5">
        <Link href="/" className={cn("nav-item", pathname === "/" && "active")}>
          <MessageSquare className="h-4 w-4 flex-shrink-0" />
          <span>Chat</span>
        </Link>
        <Link href="/dashboard" className={cn("nav-item", pathname.startsWith("/dashboard") && "active")}>
          <LayoutDashboard className="h-4 w-4 flex-shrink-0" />
          <span>MCP Manager</span>
          {servers.length > 0 && (
            <span className="ml-auto badge-primary">{servers.length}</span>
          )}
        </Link>
      </div>

      {/* ── Connected services ─────────────────────────────────────────── */}
      {servers.length > 0 && (
        <div className="px-3 py-3 border-b border-border">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-1 mb-2">
            Live Services
          </p>
          <div className="space-y-0.5">
            {servers.map((server) => (
              <Link
                key={server.id}
                href="/dashboard"
                className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-accent/80 transition-colors group"
              >
                <span className="text-sm leading-none">{getServerIcon(server.server_type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate">{server.name}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={cn(
                    "status-dot",
                    server.is_connected
                      ? server.health_status === "healthy" ? "connected" : "checking"
                      : "disconnected"
                  )} />
                  <span className="text-[10px] text-muted-foreground">
                    {server.is_connected ? "Live" : "Off"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Conversation list ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-1 mb-2">
          Recent Chats
        </p>

        {conversations.length === 0 ? (
          <div className="px-2 py-8 text-center">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
              style={{ background: "hsl(var(--secondary))", border: "1px solid hsl(var(--border))" }}
            >
              <MessageSquare className="h-4 w-4 text-muted-foreground opacity-40" />
            </div>
            <p className="text-xs text-muted-foreground">No conversations yet</p>
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">Start one above</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={cn(
                  "w-full text-left flex items-start gap-2 px-2 py-2 rounded-lg text-sm transition-all duration-150 group",
                  activeConvId === conv.id
                    ? "bg-accent border border-border/80 text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                )}
              >
                <MessageSquare className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 opacity-50" />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-xs font-medium leading-snug">
                    {conv.title || "New conversation"}
                  </p>
                  <p className="text-[10px] opacity-40 mt-0.5">{formatDate(conv.updated_at)}</p>
                </div>
                {activeConvId === conv.id && (
                  <ChevronRight className="h-3 w-3 flex-shrink-0 mt-0.5" style={{ color: "hsl(var(--primary))" }} />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── User footer ───────────────────────────────────────────────── */}
      <div
        className="px-3 py-3 border-t border-border"
        style={{ background: "hsl(222 47% 5%)" }}
      >
        <div className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-accent/60 transition-colors group">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{
              background: "linear-gradient(135deg, hsl(var(--primary) / 0.25), hsl(var(--primary) / 0.1))",
              color: "hsl(var(--primary))",
              border: "1px solid hsl(var(--primary) / 0.3)",
            }}
          >
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground truncate">{user?.name || "User"}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100"
            title="Sign out"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
