# ChatbotMCP — Architecture

## System Components

### 1. Frontend (Next.js 15)
- **Chat Interface**: Real-time SSE streaming, tool call visualization, conversation history
- **MCP Manager Dashboard**: Add/remove servers, OAuth connect, tool toggle, health monitoring
- **Auth Pages**: Login, register with JWT token management
- **State**: Zustand stores for auth, chat, and MCP server state

### 2. Backend (FastAPI)
- **Auth API** (`/api/v1/auth`): JWT register/login/refresh, user management
- **Chat API** (`/api/v1/chat`): Conversation CRUD, WebSocket + SSE streaming chat
- **MCP API** (`/api/v1/mcp`): Server registry, tool discovery, OAuth proxying
- **LLM Service**: Multi-provider (Anthropic Claude + OpenAI) with tool calling
- **MCP Client**: HTTP-based MCP protocol client for tool discovery and execution

### 3. Gmail MCP Server (FastAPI + MCP SDK)
- Implements MCP over HTTP/SSE transport
- Gmail OAuth2 PKCE flow with Google
- Tools: send_email, list_inbox, search_emails, read_email, reply_email, list_labels, get_attachment_metadata
- Encrypted token storage in-memory (Redis in production)

### 4. Infrastructure
- **PostgreSQL 16**: Users, conversations, messages, MCP servers, tool logs
- **Redis 7**: Session cache, rate limiting, token storage
- **Nginx**: Reverse proxy, rate limiting, security headers

## Data Flow — "Send email to john@example.com"

```
User types: "Send email to john@example.com"
     │
     ▼
Frontend (SSE stream opened)
     │
     ▼
Backend /api/v1/chat/send
  1. Load conversation history from PostgreSQL
  2. Discover tools from connected MCP servers (GET /tools)
  3. Call LLM (Anthropic Claude) with history + available tools
     │
     ▼ LLM returns tool_use: send_email
  4. Execute tool via MCPManager
     │
     ▼
Gmail MCP Server /mcp/messages/ 
  5. Authenticate with Google Credentials
  6. Call Gmail API → Send email
  7. Return {"message_id": "...", "status": "sent"}
     │
     ▼ Back to LLM with tool result
  8. LLM generates natural language response
  9. Stream to frontend: "Email sent successfully to john@example.com!"
    10. Save assistant message to PostgreSQL
```

## MCP Protocol Implementation

Using `mcp==1.3.0` Python SDK with HTTP/SSE transport:

```
GET  /mcp/sse          → Opens SSE stream (MCP session)
POST /mcp/messages/    → Sends JSON-RPC messages
GET  /tools            → Quick tool list endpoint (non-MCP)
POST /mcp/messages/    → tools/call JSON-RPC method
```

Tool schema follows JSON Schema spec:
```json
{
  "name": "send_email",
  "description": "Send an email via Gmail",
  "input_schema": {
    "type": "object",
    "properties": {
      "to": {"type": "string"},
      "subject": {"type": "string"},
      "body": {"type": "string"}
    },
    "required": ["to", "subject", "body"]
  }
}
```

## Security Architecture

### Token Encryption
OAuth tokens encrypted with Fernet (AES-128-CBC + HMAC-SHA256):
```python
key = SHA256(ENCRYPTION_KEY)  # normalize to 32 bytes
fernet = Fernet(base64url(key))
encrypted = fernet.encrypt(access_token.encode())
```

### JWT Strategy
- Access tokens: 30 min expiry, `{"sub": user_id, "type": "access"}`
- Refresh tokens: 7 day expiry, rotation on use
- Algorithm: HS256

### Rate Limiting
- General API: 60 req/min per IP
- Auth endpoints: 5 req/min per IP (via slowapi + nginx)
