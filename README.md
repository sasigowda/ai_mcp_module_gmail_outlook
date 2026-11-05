# ChatbotMCP

Production-ready AI chatbot platform with MCP (Model Context Protocol) integration for Gmail and Outlook.

## Features

- **AI Chat** — Streaming responses with Claude (Anthropic) or GPT-4o (OpenAI)
- **Gmail Integration** — Send, read, search, reply to emails via OAuth2
- **Outlook Integration** — Full Outlook/Microsoft 365 email + Calendar access
- **MCP Manager GUI** — Web dashboard to add/remove/monitor MCP connections
- **Tool Calling** — LLM dynamically discovers and executes MCP tools
- **Conversation History** — Persistent multi-turn conversations
- **Secure OAuth** — No passwords stored; Google + Microsoft OAuth2 popups

## Quick Start

```powershell
# 1. Clone / navigate to project
cd C:\Users\sasid\Videos\chatbot-mcp

# 2. Configure environment
copy .env.example .env
# Edit .env with your API keys and OAuth credentials

# 3. Start everything
docker compose -f docker/docker-compose.yml up -d

# 4. Open app
start http://localhost:3000
```

## Project Structure

```
chatbot-mcp/
├── frontend/               # Next.js 15 + Tailwind + ShadCN
├── backend/                # FastAPI + SQLAlchemy + JWT auth
├── mcp-servers/
│   ├── gmail/             # Gmail MCP server (Python)
│   └── outlook/           # Outlook MCP server (Python)
├── database/              # PostgreSQL schema
├── docker/                # Docker Compose + Nginx config
└── docs/                  # Architecture + setup guide
```

## Documentation

- [Setup Guide](docs/SETUP.md) — Step-by-step OAuth, Docker, local dev
- [Architecture](docs/ARCHITECTURE.md) — System design, data flow, security

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, Tailwind CSS, Zustand |
| Backend | Python 3.12, FastAPI, SQLAlchemy async |
| MCP | Python `mcp` SDK 1.3, HTTP/SSE transport |
| Gmail | Google API Client, OAuth2 |
| Outlook | MSAL, Microsoft Graph API |
| LLM | Anthropic Claude API, OpenAI API |
| Database | PostgreSQL 16, Redis 7 |
| Infra | Docker, Docker Compose, Nginx |

## Example Interactions

```
User: "Send an email to manager@company.com with subject 'Weekly Report'"
Bot: "I'll send that email now. What should the body say?"
User: "Write: Project is on track. Deliverable by Friday."
Bot: ✅ Email sent to manager@company.com
     Subject: Weekly Report
     Message delivered successfully.

User: "Check my unread emails"
Bot: You have 3 unread emails:
     1. From: alice@example.com — "Re: Meeting tomorrow"
     2. From: noreply@github.com — "New pull request"
     3. From: team@slack.com — "Weekly digest"

User: "What's on my calendar today?"
Bot: You have 2 events today:
     • 10:00 AM — Team standup (30 min)
     • 2:00 PM — Product review with client (1 hr, Teams link attached)
```
