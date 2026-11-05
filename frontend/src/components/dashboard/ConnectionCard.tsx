"use client";

import { useState } from "react";
import {
  ExternalLink, Trash2, RefreshCw, Unplug, Wrench,
  Shield, CheckCircle2, XCircle,
} from "lucide-react";
import { mcp } from "@/lib/api";
import { useMCPStore } from "@/lib/store";
import { cn, getServerIcon } from "@/lib/utils";
import type { MCPServer, AuthStatus, MCPTool } from "@/types";

interface Props { server: MCPServer; }

export function ConnectionCard({ server }: Props) {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const { updateServer, removeServer } = useMCPStore();

  const refreshStatus = async () => {
    setLoading(true);
    try {
      const status = await mcp.getAuthStatus(server.id);
      setAuthStatus(status);
      updateServer(server.id, { is_connected: status.connected });
      if (status.connected) {
        await mcp.healthCheck(server.id);
        updateServer(server.id, { health_status: "healthy", is_connected: true });
        const toolList = await mcp.getTools(server.id, true);
        setTools(toolList);
      } else {
        updateServer(server.id, { health_status: "unknown", is_connected: false });
      }
    } catch {
      updateServer(server.id, { health_status: "unhealthy" });
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    try {
      const { auth_url } = await mcp.getAuthUrl(server.id);
      const popup = window.open(auth_url, "oauth", "width=520,height=720,scrollbars=yes");
      const handler = (e: MessageEvent) => {
        if (e.data?.type === "GMAIL_AUTH_SUCCESS") {
          window.removeEventListener("message", handler);
          popup?.close();
          refreshStatus();
        }
      };
      window.addEventListener("message", handler);
      const interval = setInterval(() => {
        if (popup?.closed) {
          clearInterval(interval);
          window.removeEventListener("message", handler);
          setTimeout(refreshStatus, 500);
        }
      }, 800);
    } catch (err) {
      console.error("Auth failed:", err);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm(`Disconnect ${server.name}?`)) return;
    setLoading(true);
    try {
      await mcp.disconnect(server.id);
      setAuthStatus({ connected: false, email: null, name: null });
      setTools([]);
      updateServer(server.id, { is_connected: false, health_status: "unknown" });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Permanently remove ${server.name}?`)) return;
    await mcp.deleteServer(server.id);
    removeServer(server.id);
  };

  const toggleTool = async (toolId: string, currentEnabled: boolean) => {
    await mcp.toggleTool(server.id, toolId, !currentEnabled);
    setTools((prev) => prev.map((t) => t.id === toolId ? { ...t, is_enabled: !currentEnabled } : t));
  };

  const isConnected = server.is_connected;
  const health = server.health_status;
  const statusLabel = isConnected
    ? health === "healthy" ? "Connected" : health === "unhealthy" ? "Error" : "Checking…"
    : "Not connected";
  const statusDotClass = isConnected
    ? health === "healthy" ? "connected" : health === "unhealthy" ? "unhealthy" : "checking"
    : "disconnected";

  return (
    <div
      className="rounded-2xl overflow-hidden transition-all duration-300"
      style={{
        background: "hsl(var(--card))",
        border: `1px solid ${isConnected ? "hsl(var(--success) / 0.2)" : "hsl(var(--border))"}`,
        boxShadow: isConnected
          ? "0 0 0 1px hsl(var(--success) / 0.08), 0 8px 32px hsl(0 0% 0% / 0.15)"
          : "0 4px 16px hsl(0 0% 0% / 0.12)",
      }}
    >
      {/* Connected accent bar */}
      {isConnected && (
        <div
          className="h-0.5 w-full"
          style={{ background: "linear-gradient(90deg, transparent, hsl(var(--success) / 0.6), transparent)" }}
        />
      )}

      {/* ── Card header ─────────────────────────────────────────────── */}
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Service icon */}
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl flex-shrink-0"
            style={{
              background: "hsl(var(--secondary))",
              border: "1px solid hsl(var(--border))",
            }}
          >
            {getServerIcon(server.server_type)}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground text-sm mb-0.5">{server.name}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{server.description}</p>
            {authStatus?.connected && authStatus.email && (
              <div className="flex items-center gap-1.5 mt-2">
                <Shield className="h-3 w-3 flex-shrink-0" style={{ color: "hsl(var(--success))" }} />
                <span className="text-xs font-medium truncate" style={{ color: "hsl(var(--success))" }}>
                  {authStatus.email}
                </span>
              </div>
            )}
          </div>

          {/* Status */}
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <div className="flex items-center gap-1.5">
              <span className={cn("status-dot", statusDotClass)} />
              <span className={cn("text-xs font-medium", isConnected ? "text-foreground" : "text-muted-foreground")}>
                {statusLabel}
              </span>
            </div>
            {tools.length > 0 && (
              <span className="badge-primary">{tools.length} tools</span>
            )}
          </div>
        </div>

        {/* Stats row when connected */}
        {isConnected && (
          <div
            className="mt-4 pt-4 grid grid-cols-3 gap-3"
            style={{ borderTop: "1px solid hsl(var(--border))" }}
          >
            <StatCell
              label="Health"
              value={health === "healthy" ? "Healthy" : "Unknown"}
              good={health === "healthy"}
              icon={health === "healthy" ? CheckCircle2 : XCircle}
            />
            <StatCell label="Tools" value={tools.length > 0 ? String(tools.length) : "—"} />
            <StatCell label="Auth" value="OAuth 2.0" good />
          </div>
        )}
      </div>

      {/* ── Actions bar ─────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-2 px-5 py-3"
        style={{ background: "hsl(var(--secondary))", borderTop: "1px solid hsl(var(--border))" }}
      >
        {isConnected ? (
          <>
            <button
              onClick={() => { setShowTools((v) => !v); if (!tools.length) refreshStatus(); }}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Wrench className="h-3.5 w-3.5" />
              {showTools ? "Hide tools" : "View tools"}
            </button>
            <span className="text-border mx-1">·</span>
            <button
              onClick={handleDisconnect}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors"
            >
              <Unplug className="h-3.5 w-3.5" />
              Disconnect
            </button>
          </>
        ) : (
          <button
            onClick={handleConnect}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs font-semibold transition-colors"
            style={{ color: "hsl(var(--primary))" }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Connect Account
          </button>
        )}

        <div className="ml-auto flex items-center gap-1">
          <IconBtn onClick={refreshStatus} loading={loading} title="Refresh status">
            <RefreshCw className="h-3.5 w-3.5" />
          </IconBtn>
          <IconBtn onClick={handleDelete} title="Remove server" danger>
            <Trash2 className="h-3.5 w-3.5" />
          </IconBtn>
        </div>
      </div>

      {/* ── Tool list ────────────────────────────────────────────────── */}
      {showTools && tools.length > 0 && (
        <div style={{ borderTop: "1px solid hsl(var(--border))" }}>
          <div className="px-5 py-4">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-3">
              Available Tools ({tools.length})
            </p>
            <div className="space-y-1.5">
              {tools.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-center justify-between py-2 px-3 rounded-xl"
                  style={{ background: "hsl(var(--secondary))", border: "1px solid hsl(var(--border) / 0.5)" }}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className={cn("status-dot", tool.is_enabled ? "connected" : "disconnected")} />
                    <span className="text-xs font-mono text-foreground truncate">{tool.name}</span>
                  </div>
                  <button
                    onClick={() => toggleTool(tool.id, tool.is_enabled)}
                    className="text-xs font-medium ml-3 flex-shrink-0 transition-colors"
                    style={{ color: tool.is_enabled ? "hsl(var(--muted-foreground))" : "hsl(var(--primary))" }}
                  >
                    {tool.is_enabled ? "Disable" : "Enable"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCell({
  label, value, good, icon: Icon,
}: {
  label: string; value: string; good?: boolean; icon?: React.ElementType;
}) {
  const color = good === true
    ? "hsl(var(--success))"
    : good === false ? "hsl(var(--destructive))"
    : "hsl(var(--foreground))";

  return (
    <div className="text-center">
      <p className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wide">{label}</p>
      <div className="flex items-center justify-center gap-1">
        {Icon && <Icon className="h-3 w-3" style={{ color }} />}
        <p className="text-xs font-semibold" style={{ color }}>{value}</p>
      </div>
    </div>
  );
}

function IconBtn({
  onClick, children, loading, title, danger,
}: {
  onClick: () => void; children: React.ReactNode; loading?: boolean; title?: string; danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      title={title}
      className={cn(
        "p-1.5 rounded-lg text-muted-foreground transition-all duration-150",
        danger ? "hover:text-destructive hover:bg-destructive/10" : "hover:text-foreground hover:bg-accent"
      )}
    >
      {loading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : children}
    </button>
  );
}
