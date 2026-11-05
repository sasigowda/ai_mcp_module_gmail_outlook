# ChatbotMCP — Complete Windows Installation & Startup Guide

> **Version:** v1.1.0 — Dark Professional UI Edition
> **Audience:** Developer setting up ChatbotMCP on a Windows 11 laptop for the first time.
> **Time Required:** ~45–60 minutes (most time is OAuth setup)
>
> **UI Note:** ChatbotMCP uses a **dark-only theme** by design — a deep navy professional dashboard inspired by enterprise monitoring tools. There is no light mode. The interface will look dark on first load — this is correct and intentional.

---

## What You Need to Install

There are **two ways** to run this project:

| Method | What to Install | Best For |
|--------|----------------|----------|
| **Docker (Recommended)** | Docker Desktop only | Running the full app quickly |
| **Local Development** | Docker + Node.js + Python | Editing and developing code |

---

## PART A — Install Required Software

### A1. Install Docker Desktop (REQUIRED for both methods)

Docker runs all backend services (database, cache, API servers) inside containers — you do NOT need to install Python, PostgreSQL, or Redis separately.

**Steps:**

1. Open your browser and go to: **https://www.docker.com/products/docker-desktop/**
2. Click **"Download for Windows — AMD64"**
3. Run the installer `Docker Desktop Installer.exe`
4. When asked, keep **"Use WSL 2 instead of Hyper-V"** checked (recommended)
5. Click **Install** → **Close** when done
6. **Restart your computer**
7. After restart, Docker Desktop opens automatically — wait for it to say **"Docker Desktop is running"** (green icon in taskbar)

**Verify Docker works:**
Open PowerShell and run:
```powershell
docker --version
docker compose version
```
You should see version numbers like `Docker version 27.x.x` and `Docker Compose version v2.x.x`

---

### A2. Install Node.js 22 (Required for LOCAL frontend development only)

> Skip this if you are ONLY running via Docker.

1. Go to: **https://nodejs.org/en/download**
2. Download **Node.js 22 LTS — Windows Installer (.msi)**
3. Run the installer — click Next through all defaults
4. Verify in PowerShell:
```powershell
node --version    # Should show v22.x.x
npm --version     # Should show 10.x.x
```

---

### A3. Install Python 3.12 (Required for LOCAL backend/MCP development only)

> Skip this if you are ONLY running via Docker.

**Option 1 — Install via PowerShell (Recommended, no browser needed):**

Open PowerShell and run:
```powershell
winget install Python.Python.3.12
```
Wait for it to finish, then **close PowerShell completely and reopen it** so the PATH updates.

**Option 2 — Install via browser:**
1. Go to: **https://www.python.org/downloads/**
2. Download **Python 3.12.x — Windows installer (64-bit)**
3. Run the installer
4. **IMPORTANT:** On the first screen, check **"Add Python to PATH"** at the bottom before clicking Install
5. Click **Install Now**

**Verify Python installed correctly** (in a fresh PowerShell window):
```powershell
python --version    # Should show Python 3.12.x
pip --version       # Should show pip 24.x.x
```

> **Tip:** If `python` still shows "not found" after installing, try `py --version` instead. If that works, use `py` everywhere `python` is written in this guide.

---

### A4. Install Visual Studio Code (Recommended — Free Code Editor)

1. Go to: **https://code.visualstudio.com/download**
2. Download **Windows x64**
3. Run installer with default settings
4. After install, open VS Code and install these extensions (click Extensions icon on left sidebar):
   - **Python** (by Microsoft)
   - **ESLint** (by Microsoft)
   - **Docker** (by Microsoft)
   - **GitLens** (optional)

---

### A5. Install Git (Recommended)

1. Go to: **https://git-scm.com/download/win**
2. Download and run the installer with default settings
3. Verify:
```powershell
git --version
```

---

## PART B — Get Your API Keys and OAuth Credentials

This is the most important part. You need credentials from three external services.

---

### B1. Get Anthropic (Claude AI) API Key

This powers the AI chatbot brain.

1. Go to: **https://console.anthropic.com/**
2. Sign up or log in
3. Click **API Keys** in the left menu
4. Click **Create Key** → give it a name like "chatbot-mcp"
5. **Copy the key** — it starts with `sk-ant-...`
6. Save it somewhere safe — you'll need it in Step C

> **Cost:** Anthropic charges per API call. For testing, $5 credit is more than enough.

---

### B2. Set Up Google Gmail OAuth

This allows the app to send/read Gmail on behalf of users. **No passwords are stored** — uses Google's secure OAuth2 flow.

**Step B2.1 — Create a Google Cloud Project:**

1. Go to: **https://console.cloud.google.com/**
2. Sign in with your Google account
3. Click the project dropdown at the top → **New Project**
4. Name: `ChatbotMCP` → Click **Create**
5. Make sure your new project is selected in the dropdown

**Step B2.2 — Enable Gmail API:**

1. In the left menu: **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click on it → Click **Enable**

**Step B2.3 — Configure OAuth Consent Screen:**

1. Left menu: **APIs & Services** → **OAuth consent screen**
2. Select **External** → Click **Create**
3. Fill in:
   - App name: `ChatbotMCP`
   - User support email: your email
   - Developer contact email: your email
4. Click **Save and Continue**
5. On Scopes page — click **Add or Remove Scopes**
6. Search and add these scopes:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/userinfo.email`
7. Click **Update** → **Save and Continue**
8. On Test users page — click **Add Users** → add your Gmail address
9. Click **Save and Continue** → **Back to Dashboard**

**Step B2.4 — Create OAuth Credentials:**

1. Left menu: **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth 2.0 Client IDs**
3. Application type: **Web application**
4. Name: `ChatbotMCP Web Client`
5. Under **Authorized redirect URIs** → click **Add URI**:
   - Add: `http://localhost:8001/oauth/gmail/callback`
6. Click **Create**
7. A popup shows your credentials — **Copy both:**
   - **Client ID** (ends with `.apps.googleusercontent.com`)
   - **Client Secret**

---

## PART C — Configure the Project

### C1. Copy the Environment File

Open **PowerShell** and run:

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp
Copy-Item .env.example .env
```

### C2. Generate Secret Keys

You need three unique random keys. Run **each block separately** in PowerShell and copy the output:

**If Python is installed:**
```powershell
# Run once → copy output → this is your SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Run again → copy output → this is your JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Run again → copy output → this is your ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**If Python is NOT installed yet (pure PowerShell):**
```powershell
# Run once → copy output → SECRET_KEY
[System.Convert]::ToBase64String((1..48 | ForEach-Object { [byte](Get-Random -Max 256) }))

# Run again → copy output → JWT_SECRET_KEY
[System.Convert]::ToBase64String((1..48 | ForEach-Object { [byte](Get-Random -Max 256) }))

# Run again → copy output → ENCRYPTION_KEY
[System.Convert]::ToBase64String((1..24 | ForEach-Object { [byte](Get-Random -Max 256) }))
```

Each run produces a different random string — that's correct. Copy each one and keep them ready for the next step.

### C3. Edit the .env File

**Option 1 — Open in VS Code (if installed):**
```powershell
code C:\Users\sasid\Videos\chatbot-mcp\.env
```

**Option 2 — Open in Notepad:**
```powershell
notepad C:\Users\sasid\Videos\chatbot-mcp\.env
```

**Option 3 — Set all values directly in PowerShell** (no editor needed):

Replace the values inside the quotes below with your actual keys/credentials, then run the whole block:

```powershell
$envFile = "C:\Users\sasid\Videos\chatbot-mcp\.env"

# Read the template
$content = Get-Content $envFile -Raw

# Replace placeholders — paste YOUR values inside the quotes
$content = $content -replace 'your-super-secret-key-change-in-production-min-32-chars', 'PASTE_SECRET_KEY_HERE'
$content = $content -replace 'your-jwt-secret-key-change-in-production',               'PASTE_JWT_KEY_HERE'
$content = $content -replace 'your-fernet-encryption-key-base64-encoded',              'PASTE_ENCRYPTION_KEY_HERE'
$content = $content -replace 'sk-ant-your-anthropic-api-key',                          'PASTE_ANTHROPIC_KEY_HERE'
$content = $content -replace 'your-google-client-id.apps.googleusercontent.com',       'PASTE_GOOGLE_CLIENT_ID_HERE'
$content = $content -replace 'your-google-client-secret',                              'PASTE_GOOGLE_SECRET_HERE'

# Save
$content | Set-Content $envFile -Encoding utf8
Write-Host ".env file updated successfully"
```

**What your .env should look like when done:**

```ini
# ─── Application ──────────────────────────────────────────────────────────────
SECRET_KEY=abc123...your-64-char-random-string...
JWT_SECRET_KEY=xyz789...another-64-char-string...
ENCRYPTION_KEY=short32charstring...

# ─── Database (leave as-is for local development) ─────────────────────────────
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=chatbot_secret_change_me
POSTGRES_DB=chatbot_db

# ─── Redis (leave as-is) ──────────────────────────────────────────────────────
REDIS_PASSWORD=redis_secret_change_me

# ─── AI Provider ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=your-anthropic-api-key

# ─── Gmail OAuth ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/oauth/gmail/callback
```

Save the file (`Ctrl+S` in VS Code / Notepad).

---

## PART D — Start the Application (Docker Method)

### D1. Open PowerShell in Project Folder

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp
```

### D2. Build and Start All Services

```powershell
docker compose -f docker/docker-compose.yml up --build -d
```

**What this does:**
- Downloads PostgreSQL, Redis, and Nginx images (~500 MB first time)
- Builds the Python backend and Gmail MCP images
- Builds the Next.js frontend image
- Starts all 6 containers

**First build takes 5–10 minutes.** Subsequent starts take ~30 seconds.

### D3. Wait for All Services to Be Healthy

```powershell
docker compose -f docker/docker-compose.yml ps
```

You should see all services showing **"healthy"** or **"running"**:

```
NAME                    STATUS
chatbot_postgres        running (healthy)
chatbot_redis           running (healthy)
chatbot_backend         running
chatbot_gmail_mcp       running
chatbot_frontend        running
chatbot_nginx           running
```

### D4. Check Logs If Something Fails

```powershell
# See all logs
docker compose -f docker/docker-compose.yml logs -f

# See specific service logs
docker compose -f docker/docker-compose.yml logs backend -f
docker compose -f docker/docker-compose.yml logs gmail-mcp -f
```

---

## PART E — First Time Use

### E1. Open the Application

Open your browser and go to: **http://localhost:3000**

You will land on a **dark login page** with a glowing blue orb at the top — this is intentional. The app has no light mode.

```
┌────────────────────────────────────────┐
│                                        │
│              [Bot Icon]                │
│           ChatbotMCP  v1.1             │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Sign in to your account         │  │
│  │                                  │  │
│  │  EMAIL ________________________  │  │
│  │  PASSWORD _____________________  │  │
│  │                                  │  │
│  │     [ Sign in  →  ]              │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘
  Deep navy (#080e1a) background, blue CTA
```

### E2. Create Your Account

1. Click **"Create one"** link below the login form
2. You'll see the registration page (same dark style)
3. Fill in: your name, email address, and a password (minimum 8 characters)
4. Confirm your password in the second password field
5. Click **"Create account"** — the blue arrow button
6. You'll be automatically logged in and redirected to the chat interface

### E3. Explore the Dark Chat Interface

After login, you land on the main chat page. Here's what you'll see:

```
┌────────────────────────────────────────────────────────────────┐
│ SIDEBAR (260px)           │  CHAT AREA                         │
│                           │                                     │
│ [Bot] ChatbotMCP          │  ● 0 services connected            │
│       AI Command Center   │                                     │
│                           │  ╔══════════════════════════════╗  │
│ [ + New Conversation ]    │  ║                              ║  │
│                           │  ║   [Bot Icon]                 ║  │
│ ─── Navigation ───────    │  ║   Hello! I'm your AI         ║  │
│ 💬 Chat           (active)│  ║   assistant...               ║  │
│ ⊞  MCP Manager   [0]      │  ║                              ║  │
│                           │  ║  ┌────┐ ┌────┐ ┌────┐ ┌────┐║  │
│ ─── Connections ──────    │  ║  │📧  │ │📅  │ │🔍  │ │📨  ║  │
│ (empty until connected)   │  ║  │Email│ │Cal │ │Srch│ │Snd ║  │
│                           │  ║  └────┘ └────┘ └────┘ └────┘║  │
│ ─── Recent Chats ─────    │  ╚══════════════════════════════╝  │
│ No conversations yet      │                                     │
│                           │  ┌──────────────────────────────┐  │
│ ─── User Footer ──────    │  │ Type a message...         [↑] │  │
│ [S] Your Name             │  └──────────────────────────────┘  │
│     your@email.com  [↪]   │                                     │
└───────────────────────────┴─────────────────────────────────────┘
```

Key visual elements:
- **Status bar** at top of chat: shows "● 0 services connected" (grey dot = not connected)
- **4 suggestion tiles** in the empty state (email, calendar, search, send)
- **Sidebar** shows live connection status per MCP server once connected

### E4. Connect Gmail

1. Click **"MCP Manager"** in the left sidebar — or navigate to **http://localhost:3000/dashboard**
2. The MCP Manager dashboard opens (same dark style with a frosted-glass header)
3. You'll see **4 stats cards** at the top: Total Servers / Connected / Healthy / Active Tools
4. Scroll to the **"Add a Connection"** section
5. Click **"Add Gmail"** button
6. The Gmail connector card appears — click **"Connect Account"**
7. A **Google sign-in popup** opens in a new window
8. Sign in with your Google account
9. Review the permissions (read/send/modify Gmail) → Click **Allow**
10. The popup closes automatically
11. The Gmail card updates to show:
    - A **green animated dot** (●) — "Connected" / "Live" status
    - Your Google account email address
    - Stats: number of tools loaded (7 tools)

After connecting, the **sidebar automatically shows Gmail** in the Connections panel with a live green dot.

### E5. See Live Connection Status

After connecting Gmail, your sidebar transforms:

```
┌─────────────────────────────┐
│ [Bot] ChatbotMCP            │
│       AI Command Center     │
│                             │
│ [ + New Conversation ]      │
│                             │
│ ─── Navigation ──────────   │
│ 💬 Chat           (active)  │
│ ⊞  MCP Manager   [1]        │  ← badge shows 1 server
│                             │
│ ─── Connections ──────────  │
│ 📧 Gmail         ● Live     │  ← green animated dot
│                             │
│ ─── Recent Chats ─────────  │
│  (your conversations)       │
└─────────────────────────────┘
```

The status bar in the chat area also updates: **"● 1 service connected"** (green dot).

### E6. Start Chatting!

Go back to the main chat (click **"Open Chat"** button in the dashboard header, or click **"Chat"** in the sidebar). Try these example messages:

```
"What are my unread emails?"
"Send an email to colleague@company.com with subject 'Hello' and body 'This is a test from ChatbotMCP'"
"Search my emails for anything about invoices"
"Summarize my last 5 emails"
```

**What you'll see while the AI works:**

The chat interface shows live tool execution status:

```
┌─────────────────────────────────────────────┐
│ [Bot]                                       │
│                                             │
│  ┌ Tool: list_emails ──────────────────┐   │
│  │ ⟳ Calling...                        │   │  ← amber spinner
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌ Tool: list_emails ──────────────────┐   │
│  │ ✓ Completed in 1.2s                 │   │  ← green check
│  └─────────────────────────────────────┘   │
│                                             │
│  You have 3 unread emails:                 │
│  1. Meeting reminder from John...           │
│  2. Invoice #1234 from Vendor...           │
│  3. Weekly report from Team...█            │  ← blinking cursor
└─────────────────────────────────────────────┘
```

---

## PART F — Local Development Setup (Optional)

Use this if you want to edit code and see changes live.

### Frontend (Next.js)

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp\frontend
npm install
npm run dev
```
Opens at http://localhost:3000 with hot reload.

### Backend (FastAPI)

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs at http://localhost:8000/docs

### Gmail MCP Server

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp\mcp-servers\gmail
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.server:app --reload --port 8001
```

> For local dev, keep Docker running for PostgreSQL and Redis only:
> ```powershell
> docker compose -f docker/docker-compose.yml up postgres redis -d
> ```

---

## PART G — Daily Usage Commands

### Start the App (after first setup)

```powershell
cd C:\Users\sasid\Videos\chatbot-mcp
docker compose -f docker/docker-compose.yml up -d
```

### Stop the App

```powershell
docker compose -f docker/docker-compose.yml down
```

### Stop and Delete All Data (fresh start)

```powershell
docker compose -f docker/docker-compose.yml down -v
```

### Update After Code Changes

```powershell
docker compose -f docker/docker-compose.yml up --build -d
```

---

## PART H — Troubleshooting

### Problem: The app looks completely black / dark — is this a bug?

No — this is correct. ChatbotMCP v1.1 is a **dark-only interface** by design. The entire UI (login, chat, dashboard) uses a deep navy `#080e1a` background. There is no light mode or theme toggle. If you see a dark screen, the app is working correctly.

### Problem: Status dots are not showing green after connecting Gmail

- Wait 5–10 seconds — the health check runs on a delay
- Refresh the page (`F5`) to reload the server list from the API
- If still amber/red: check the Gmail MCP container logs:
```powershell
docker compose -f docker/docker-compose.yml logs gmail-mcp -f
```
- Make sure the OAuth popup didn't get blocked by your browser (allow popups for localhost:3000)

### Problem: Port already in use

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with the number shown)
taskkill /PID <PID> /F
```

### Problem: Docker Desktop not starting

- Open Task Manager → check Docker Desktop process
- Right-click Docker tray icon → Restart
- Make sure Virtualization is enabled in BIOS (most modern PCs have it on)

### Problem: Gmail OAuth error "redirect_uri_mismatch"

- Check that your `.env` has exactly: `GOOGLE_REDIRECT_URI=http://localhost:8001/oauth/gmail/callback`
- In Google Cloud Console, confirm the redirect URI matches exactly (no trailing slash)

### Problem: Backend fails to start (database error)

- PostgreSQL container may not be ready. Wait 30 seconds and try again:
```powershell
docker compose -f docker/docker-compose.yml restart backend
```

### Problem: "ANTHROPIC_API_KEY not set"

- Open `.env` and make sure the key is filled in (not the placeholder text)
- Restart after editing `.env`:
```powershell
docker compose -f docker/docker-compose.yml up -d
```

---

## Service URLs Reference

| Service | URL | Purpose |
|---------|-----|---------|
| **Main App — Chat** | http://localhost:3000 | Dark chat interface with sidebar live status |
| **Main App — MCP Manager** | http://localhost:3000/dashboard | Stats cards, connect Gmail, manage tools |
| Backend API Docs | http://localhost:8000/docs | Interactive API documentation (Swagger UI) |
| Gmail MCP Docs | http://localhost:8001/docs | Gmail MCP server API (7 email tools) |

**Status Indicator Color Guide (visible throughout the UI):**

| Color | Meaning | Where You'll See It |
|-------|---------|---------------------|
| 🟢 Green (animated glow) | Connected and healthy | Sidebar connections panel, MCP Manager card |
| 🟡 Amber (pulsing) | Connected but checking health | Sidebar, MCP Manager card header |
| 🔴 Red (steady) | Disconnected or error | Sidebar, MCP Manager card header |
| ⚪ Grey (static) | Not yet configured | Status bar at top of chat |

---

## Software Installation Checklist

```
SETUP
□ Docker Desktop installed and running (green icon in taskbar)
□ .env file created from .env.example
□ SECRET_KEY filled in (generated)
□ JWT_SECRET_KEY filled in (generated)
□ ENCRYPTION_KEY filled in (generated)
□ ANTHROPIC_API_KEY filled in
□ GOOGLE_CLIENT_ID filled in
□ GOOGLE_CLIENT_SECRET filled in
□ docker compose up --build -d succeeded
□ All containers showing "running" in docker ps

FIRST USE — Dark UI Verification
□ http://localhost:3000 shows dark navy login page (not white/light)
□ Registered account successfully
□ Chat interface loads with "0 services connected" status bar
□ Sidebar shows "No conversations yet" placeholder
□ MCP Manager (/dashboard) shows 4 stats cards at top

CONNECTIONS
□ Gmail connected — green animated dot visible in MCP Manager card
□ Gmail "Live" status visible in sidebar Connections panel
□ Status bar in chat updated to "● 1 service connected" (green dot)

VALIDATION
□ First chat message sent successfully
□ Tool execution cards visible during AI response (amber → green)
□ Conversation appears in sidebar "Recent Chats" section
```
