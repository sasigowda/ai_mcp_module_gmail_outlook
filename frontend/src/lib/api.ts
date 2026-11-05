import type {
  AuthTokens, User, MCPServer, MCPTool, Conversation,
  ChatMessage, AuthStatus, SendMessagePayload, StreamEvent,
} from "@/types";

// Use relative path so browser requests go through Next.js rewrites → backend
// In Docker: /api/* → http://backend:8000/api/* (server-side proxy)
// In local dev: /api/* → http://localhost:8000/api/*
const API_BASE = "/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  register: (email: string, password: string, name?: string) =>
    apiFetch<AuthTokens>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    apiFetch<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => apiFetch<User>("/auth/me"),

  logout: () => apiFetch("/auth/logout", { method: "POST" }),

  refresh: (refresh_token: string) =>
    apiFetch<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),
};

// ── MCP Servers ───────────────────────────────────────────────────────────────
export const mcp = {
  listServers: () => apiFetch<MCPServer[]>("/mcp/servers"),

  createServer: (data: { name: string; server_type: string; base_url: string; description?: string }) =>
    apiFetch<MCPServer>("/mcp/servers", { method: "POST", body: JSON.stringify(data) }),

  deleteServer: (id: string) =>
    apiFetch(`/mcp/servers/${id}`, { method: "DELETE" }),

  getTools: (serverId: string, refresh = false) =>
    apiFetch<MCPTool[]>(`/mcp/servers/${serverId}/tools?refresh=${refresh}`),

  toggleTool: (serverId: string, toolId: string, is_enabled: boolean) =>
    apiFetch(`/mcp/servers/${serverId}/tools/${toolId}?is_enabled=${is_enabled}`, { method: "PATCH" }),

  getAuthStatus: (serverId: string) =>
    apiFetch<AuthStatus>(`/mcp/servers/${serverId}/auth/status`),

  getAuthUrl: (serverId: string) =>
    apiFetch<{ auth_url: string; server_type: string }>(`/mcp/servers/${serverId}/auth/url`),

  disconnect: (serverId: string) =>
    apiFetch(`/mcp/servers/${serverId}/auth`, { method: "DELETE" }),

  healthCheck: (serverId: string) =>
    apiFetch(`/mcp/servers/${serverId}/health`),

  executeTool: (tool_name: string, arguments_: Record<string, unknown>, server_id: string) =>
    apiFetch("/mcp/tools/execute", {
      method: "POST",
      body: JSON.stringify({ tool_name, arguments: arguments_, server_id }),
    }),

  getRegistry: () =>
    apiFetch<{ servers: Record<string, unknown>[] }>("/mcp/registry"),
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chat = {
  listConversations: () => apiFetch<Conversation[]>("/chat/conversations"),

  createConversation: (data?: { title?: string; llm_provider?: string; llm_model?: string }) =>
    apiFetch<Conversation>("/chat/conversations", { method: "POST", body: JSON.stringify(data || {}) }),

  getMessages: (convId: string) =>
    apiFetch<ChatMessage[]>(`/chat/conversations/${convId}/messages`),

  deleteConversation: (convId: string) =>
    apiFetch(`/chat/conversations/${convId}`, { method: "DELETE" }),

  async *sendMessageStream(payload: SendMessagePayload): AsyncGenerator<StreamEvent> {
    const token = getToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const resp = await fetch(`${API_BASE}/chat/send`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    if (!resp.body) throw new Error("No response body");

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6)) as StreamEvent;
          } catch {
            // skip malformed events
          }
        }
      }
    }
  },
};

// ── WebSocket chat ────────────────────────────────────────────────────────────
export function createChatWebSocket(convId: string): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${protocol}//${window.location.host}/api/v1/chat/ws/${convId}`);
}
