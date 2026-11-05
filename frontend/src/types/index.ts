export interface User {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  is_admin: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MCPServer {
  id: string;
  name: string;
  server_type: "gmail" | "custom";
  base_url: string;
  description: string | null;
  is_active: boolean;
  is_connected: boolean;
  health_status: "healthy" | "unhealthy" | "unknown";
  created_at: string;
}

export interface MCPTool {
  id: string;
  name: string;
  description: string | null;
  input_schema: Record<string, unknown> | null;
  is_enabled: boolean;
}

export interface Conversation {
  id: string;
  title: string | null;
  llm_provider: string;
  llm_model: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: unknown;
  tool_results?: unknown;
  created_at: string;
}

// Streaming events from the backend
export type StreamEvent =
  | { type: "text"; content: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown> }
  | { type: "tool_result"; tool: string; result: unknown; success: boolean }
  | { type: "done"; stop_reason?: string; message_id?: string }
  | { type: "error"; message: string }
  | { type: "conversation_id"; id: string }
  | { type: "connected"; conversation_id: string }
  | { type: "user_message_saved"; id: string }
  | { type: "message_complete"; id: string };

export interface AuthStatus {
  connected: boolean;
  email: string | null;
  name: string | null;
}

export type LLMProvider = "anthropic" | "openai" | "groq" | "ollama";

export interface SendMessagePayload {
  message: string;
  conversation_id?: string;
  mcp_server_ids?: string[];
  llm_provider?: LLMProvider;
  llm_model?: string;
}
