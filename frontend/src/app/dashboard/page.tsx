"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MessageSquare, Bot } from "lucide-react";
import { MCPManager } from "@/components/dashboard/MCPManager";
import { useAuthStore } from "@/lib/store";
import { auth } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const { accessToken, setUser } = useAuthStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      if (!accessToken) { router.push("/auth/login"); return; }
      try {
        setUser(await auth.me());
      } catch {
        router.push("/auth/login");
        return;
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  if (loading) {
    return (
      <div
        className="flex items-center justify-center h-screen"
        style={{ background: "hsl(var(--background))" }}
      >
        <div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin"
             style={{ borderColor: "hsl(var(--primary)) transparent transparent" }} />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "hsl(var(--background))" }}>
      {/* ── Top navigation bar ───────────────────────────────────────── */}
      <header
        className="sticky top-0 z-20 flex items-center justify-between px-6 py-4 border-b border-border"
        style={{ background: "hsl(220 39% 7% / 0.95)", backdropFilter: "blur(10px)" }}
      >
        <div className="flex items-center gap-4">
          {/* Brand */}
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "hsl(var(--primary) / 0.15)", border: "1px solid hsl(var(--primary) / 0.3)" }}
            >
              <Bot className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />
            </div>
            <span className="text-sm font-semibold text-foreground">ChatbotMCP</span>
          </div>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>/</span>
            <span className="text-foreground font-medium">MCP Manager</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/">
            <button
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Chat
            </button>
          </Link>
          <Link href="/">
            <button
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              style={{ background: "hsl(var(--primary))", color: "hsl(var(--primary-foreground))" }}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Open Chat
            </button>
          </Link>
        </div>
      </header>

      {/* ── Page content ──────────────────────────────────────────────── */}
      <div className="py-6">
        {/* Dashboard header */}
        <div className="max-w-4xl mx-auto px-6 mb-6">
          <h1 className="text-2xl font-bold text-foreground">MCP Manager</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connect email and calendar services so your AI can act on your behalf
          </p>
        </div>

        <MCPManager />
      </div>
    </div>
  );
}
