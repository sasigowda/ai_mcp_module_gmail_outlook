"""
ChatbotMCP Backend
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .api.routes import auth_router, chat_router, mcp_router
from .core.config import settings
from .core.database import engine
from .core.redis_client import close_redis, get_redis
from .models import Base

log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting ChatbotMCP backend", env=settings.app_env)

    # Create tables (use Alembic for production migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify Redis connection
    redis = await get_redis()
    await redis.ping()
    log.info("Redis connected")

    yield

    # Shutdown
    await close_redis()
    await engine.dispose()
    log.info("ChatbotMCP backend stopped")


app = FastAPI(
    title="ChatbotMCP API",
    description="AI Chatbot with MCP (Model Context Protocol) integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Trusted hosts ─────────────────────────────────────────────────────────────
if settings.app_env == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "*.yourdomain.com"])


# ── Global error handlers ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "service": "chatbot-mcp-backend", "version": "1.0.0"}


@app.get("/", tags=["root"])
async def root():
    return {
        "service": "ChatbotMCP API",
        "version": "1.0.0",
        "docs": "/docs",
    }
