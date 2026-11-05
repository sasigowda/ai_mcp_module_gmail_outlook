# ChatbotMCP — Complete Setup Guide

## Prerequisites

- Docker Desktop (Windows)
- Node.js 22+ (for local dev)
- Python 3.12+ (for local dev)
- Google Cloud account (for Gmail)

---

## Step 1 — Environment Configuration

```bash
cd C:\Users\sasid\Videos\chatbot-mcp
copy .env.example .env
```

Edit `.env` with your values:

### Generate Secret Keys (PowerShell)
```powershell
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate ENCRYPTION_KEY (must be consistent across all services)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 2 — Google Gmail OAuth Setup

### 2.1 Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Create new project: "ChatbotMCP"
3. Enable **Gmail API**: APIs & Services → Library → Gmail API → Enable

### 2.2 Create OAuth 2.0 Credentials
1. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
2. Application type: **Web application**
3. Name: "ChatbotMCP"
4. Authorized redirect URIs:
   - `http://localhost:8001/oauth/gmail/callback`
5. Copy **Client ID** and **Client Secret** to `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

### 2.3 Configure OAuth Consent Screen
1. OAuth consent screen → External → Create
2. Add scopes: Gmail API (send, read, modify)
3. Add test users while in development

---

## Step 3 — LLM API Keys

### Anthropic (Recommended)
```
ANTHROPIC_API_KEY=sk-ant-...
```
Get at: https://console.anthropic.com

### OpenAI (Optional)
```
OPENAI_API_KEY=sk-...
```
Get at: https://platform.openai.com

---

## Step 4 — Docker Deployment

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp

# Start all services
docker compose -f docker/docker-compose.yml up -d

# Check logs
docker compose -f docker/docker-compose.yml logs -f

# Check status
docker compose -f docker/docker-compose.yml ps
```

Services started:
| Service | Port | URL |
|---------|------|-----|
| Frontend (Next.js) | 3000 | http://localhost:3000 |
| Backend (FastAPI) | 8000 | http://localhost:8000/docs |
| Gmail MCP | 8001 | http://localhost:8001/docs |
| PostgreSQL | 5432 | - |
| Redis | 6379 | - |
| Nginx | 80 | http://localhost |

---

## Step 5 — Local Development Setup

### Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000
```

### Gmail MCP Server
```powershell
cd mcp-servers/gmail
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

uvicorn src.server:app --reload --port 8001
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

---

## Step 6 — First Use

1. Open http://localhost:3000 — you'll see the dark navy login page
2. Register an account
3. Go to **MCP Manager** in the sidebar
4. Click **Add Gmail** → **Connect Account**
5. OAuth popup opens → sign in with Google → grant permissions
6. Green animated dot appears — Gmail is live
7. Return to chat → ask: *"What are my unread emails?"*

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Browser                           │
└──────────────────────┬──────────────────────┬───────────────────┘
                       │                      │
              HTTP/WS  │           OAuth popup│
                       ▼                      │
┌──────────────────────────────────┐           │
│         Nginx (Port 80)          │           │
└───┬──────────────┬───────────────┘           │
    │              │                           │
    ▼              ▼                           │
┌────────┐  ┌────────────┐                    │
│Next.js │  │ FastAPI     │                    │
│Frontend│  │ Backend    │                    │
│:3000   │  │ :8000      │                    │
└────────┘  └─────┬──────┘                    │
                  │ MCP HTTP                  │
                  │                           │
             ┌────▼────┐                      │
             │  Gmail  │                      │
             │   MCP   │                      │
             │  :8001  │                      │
             └────┬────┘                      │
                  │ OAuth                     │
                  ▼                           │
             Google API  ◄────────────────────┘
```

---

## Security Checklist

- [x] OAuth2 only — no plaintext passwords stored
- [x] Tokens encrypted with Fernet symmetric encryption at rest
- [x] JWT for API auth with short expiry (30 min access tokens)
- [x] Refresh token rotation
- [x] Rate limiting on all endpoints
- [x] CORS restricted to known origins
- [x] Input validation on all routes
- [x] SQL injection protection via SQLAlchemy ORM
- [x] XSS prevention via Next.js escaping
- [x] CSRF protection via SameSite cookies + auth headers
- [x] Audit logging for all tool executions
- [x] Non-root Docker containers
- [x] Token directory has restricted permissions (700)

---

## Adding New MCP Connectors

To add an Outlook MCP server in the future:

1. Copy `mcp-servers/gmail/` → `mcp-servers/outlook/`
2. Implement Microsoft OAuth (MSAL) in `src/auth/oauth.py`
3. Create tools in `src/tools/`
4. Build Microsoft Graph API client in `src/outlook_client.py`
5. Add to `docker-compose.yml` on port 8002
6. Add to frontend `BUILTIN_SERVERS` in `MCPManager.tsx`

Supported future connectors: Outlook/Microsoft 365, Slack, Notion, Jira, Google Drive, GitHub
