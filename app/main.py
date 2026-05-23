"""
LLM Gateway - Main Application Module

A unified API gateway for accessing multiple LLM providers (OpenAI, Groq, Anthropic, etc.)
with intelligent fallback routing, circuit breaker protection, and a web-based admin dashboard.

Key Features:
  - Multi-provider support: Groq, Gemini, OpenAI, Anthropic, Together, OpenRouter, Mistral, DeepSeek, xAI
  - Fallback routing with circuit breaker pattern for fault tolerance
  - CORS middleware for frontend integration
  - Admin dashboard for monitoring provider status and circuit health
  - Static file serving for web UI

Configuration:
  - API keys are loaded from .env file via pydantic-settings
  - CORS origins are configurable via FRONTEND_URL setting
  - Server runs on port 5000 by default
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.api.route import router
from app.config.settings import settings

app = FastAPI(
    title="LLM Gateway",
    version="1.0.0",
    description="A unified API gateway for accessing multiple LLM providers with intelligent fallback routing"
)


# ── CORS ──────────────────────────────────────────────────────────────────
# Configure CORS middleware to allow frontend requests from specified origins
origins = [o.strip() for o in settings.FRONTEND_URL.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ──────────────────────────────────────────────────────────
# Mount static directory for serving HTML, CSS, and JS files for the admin dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ── Routes ────────────────────────────────────────────────────────────────
# Include API router with all LLM inference and health check endpoints
app.include_router(router)


@app.get("/")
async def root():
    """Serve the admin dashboard."""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}


if __name__ == "__main__":
    config = uvicorn.Config("main:app", port=5000, log_level="info")
    server = uvicorn.Server(config)
    server.run()