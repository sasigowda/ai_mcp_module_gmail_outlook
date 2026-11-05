"use client";

import { useEffect, useState } from "react";
import { Plus, RefreshCw, Activity, Cpu, Zap, Server, CheckCircle2 } from "lucide-react";
import { ConnectionCard } from "./ConnectionCard";
import { Input } from "@/components/ui/input";
import { mcp } from "@/lib/api";
import { useMCPStore } from "@/lib/store";
import { getServerIcon } from "@/lib/utils";

const BUILTIN_SERVERS = [
  {
    server_type: "gmail",
    name: "Gmail",
    base_url: process.env.NEXT_PUBLIC_GMAIL_MCP_URL || "http://localhost:8001",
    description: "Send and manage Gmail with OAuth2",
  },
];

export function MCPManager() {
  const { servers, setServers, addServer } = useMCPStore();
  const [loading, setLoading] = useState(false);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customForm, setCustomForm] = useState({
    name: "", server_type: "custom", base_url: "", description: "",
  });

  const loadServers = async () => {
    setLoading(true);
    try {
      setServers(await mcp.listServers());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadServers(); }, []);

  const addBuiltin = async (config: typeof BUILTIN_SERVERS[0]) => {
    if (servers.some((s) => s.server_type === config.server_type)) return;
    const server = await mcp.createServer(config);
    addServer(server);
  };

  const addCustom = async () => {
    if (!customForm.name || !customForm.base_url) return;
    const server = await mcp.createServer(customForm);
    addServer(server);
    setShowCustomForm(false);
    setCustomForm({ name: "", server_type: "custom", base_url: "", description: "" });
  };

  const connectedCount = servers.filter((s) => s.is_connected).length;
  const healthyCount = servers.filter((s) => s.health_status === "healthy").length;
  const unaddedBuiltins = BUILTIN_SERVERS.filter(
    (b) => !servers.some((s) => s.server_type === b.server_type)
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* ── Stats row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        {[
          { icon: Server, label: "Total Servers", value: servers.length, color: "primary" },
          { icon: Zap, label: "Connected", value: connectedCount, color: "success" },
          { icon: Activity, label: "Healthy", value: healthyCount, color: "success" },
          { icon: Cpu, label: "Tools Available", value: servers.length * 7, color: "primary" },
        ].map(({ icon: Icon, label, value, color }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-muted-foreground font-medium">{label}</p>
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{
                  background: `hsl(var(--${color}) / 0.1)`,
                  border: `1px solid hsl(var(--${color}) / 0.2)`,
                }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: `hsl(var(--${color}))` }} />
              </div>
            </div>
            <p className="text-2xl font-bold text-foreground">{value}</p>
          </div>
        ))}
      </div>

      {/* ── Add built-in integrations ─────────────────────────────────── */}
      {unaddedBuiltins.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Quick Add Integration</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {unaddedBuiltins.map((b) => (
              <button
                key={b.server_type}
                onClick={() => addBuiltin(b)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
                style={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  color: "hsl(var(--muted-foreground))",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "hsl(var(--primary) / 0.4)";
                  e.currentTarget.style.color = "hsl(var(--foreground))";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "hsl(var(--border))";
                  e.currentTarget.style.color = "hsl(var(--muted-foreground))";
                }}
              >
                <span className="text-lg">{getServerIcon(b.server_type)}</span>
                <span>Add {b.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Section header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Connected Services</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {servers.length === 0
              ? "No services added yet"
              : `${connectedCount} of ${servers.length} active`}
          </p>
        </div>
        <button
          onClick={loadServers}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* ── Server cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {servers.map((server) => (
          <ConnectionCard key={server.id} server={server} />
        ))}

        {servers.length === 0 && !loading && (
          <div
            className="col-span-2 rounded-xl border border-dashed p-12 text-center"
            style={{ borderColor: "hsl(var(--border))", background: "hsl(var(--card) / 0.5)" }}
          >
            <Server className="h-8 w-8 text-muted-foreground/30 mx-auto mb-3" />
            <p className="font-medium text-foreground mb-1">No integrations yet</p>
            <p className="text-sm text-muted-foreground">
              Add Gmail above to start connecting your email account
            </p>
          </div>
        )}
      </div>

      {/* ── Add custom server ─────────────────────────────────────────── */}
      {showCustomForm ? (
        <div
          className="rounded-xl p-5"
          style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
        >
          <h3 className="text-sm font-semibold text-foreground mb-4">Add Custom MCP Server</h3>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <Input
              placeholder="Display name"
              value={customForm.name}
              onChange={(e) => setCustomForm((f) => ({ ...f, name: e.target.value }))}
              className="bg-secondary border-border"
            />
            <Input
              placeholder="Type (e.g. slack, notion)"
              value={customForm.server_type}
              onChange={(e) => setCustomForm((f) => ({ ...f, server_type: e.target.value }))}
              className="bg-secondary border-border"
            />
            <Input
              placeholder="Base URL (e.g. http://localhost:8003)"
              value={customForm.base_url}
              onChange={(e) => setCustomForm((f) => ({ ...f, base_url: e.target.value }))}
              className="col-span-2 bg-secondary border-border"
            />
            <Input
              placeholder="Description (optional)"
              value={customForm.description}
              onChange={(e) => setCustomForm((f) => ({ ...f, description: e.target.value }))}
              className="col-span-2 bg-secondary border-border"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={addCustom}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{ background: "hsl(var(--primary))", color: "hsl(var(--primary-foreground))" }}
            >
              Add Server
            </button>
            <button
              onClick={() => setShowCustomForm(false)}
              className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowCustomForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-muted-foreground hover:text-foreground transition-all"
          style={{ border: "1px dashed hsl(var(--border))" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "hsl(var(--primary) / 0.4)";
            e.currentTarget.style.color = "hsl(var(--primary))";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "hsl(var(--border))";
            e.currentTarget.style.color = "";
          }}
        >
          <Plus className="h-4 w-4" />
          Add Custom MCP Server
        </button>
      )}
    </div>
  );
}
