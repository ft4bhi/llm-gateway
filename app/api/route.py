"""
API Routes Module

Defines all FastAPI endpoints for the LLM Gateway:
  - /generate: Single provider inference with optional model override
  - /generate-fallback: Multi-provider with fallback routing and circuit breaker
  - /health: Health check endpoint with circuit breaker status
  - /api/providers: Admin endpoint showing configured providers and circuit status

Request/Response Models:
  - PromptRequest: prompt, provider name, optional model override
  - FallbackRequest: prompt and optional model for fallback routing
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.inference_service import InferenceService
from app.services.fallback_router import fallback_router
from app.config.configured_providers import get_configured_providers
from app.config.settings import settings
from app.providers.providers import PROVIDERS

router = APIRouter()


class PromptRequest(BaseModel):
    """Request model for single-provider inference.
    
    Attributes:
        prompt: The user's input prompt/query
        provider: LLM provider name (default: "groq")
        model: Optional model override (uses provider's default if not specified)
    """
    prompt: str
    provider: str = "groq"
    model: str = None


class FallbackRequest(BaseModel):
    """Request model for multi-provider inference with fallback routing.
    
    Attributes:
        prompt: The user's input prompt/query
        model: Optional model override (uses provider defaults if not specified)
    """
    prompt: str
    model: str = None


@router.post("/generate")
async def generate(req: PromptRequest):
    """Generate a response using a single specified provider.
    
    Args:
        req: PromptRequest containing prompt, provider, and optional model
        
    Returns:
        dict: Provider response with generated text content
        
    Raises:
        HTTPException: If provider is unknown or API key is not configured
    """
    response = await InferenceService.generate_response(req.prompt, req.provider, req.model)
    return response


@router.post("/generate-fallback")
async def generate_fallback(req: FallbackRequest):
    """Generate response using fallback router with circuit breaker protection.
    
    Tries configured providers in order. If a provider fails or is rate-limited,
    automatically falls back to the next available provider. Uses circuit breaker
    pattern to prevent cascading failures.
    
    Args:
        req: FallbackRequest containing prompt and optional model
        
    Returns:
        dict: Response from the first successful provider
        
    Raises:
        HTTPException: If all providers fail or are circuit-open
    """
    response = await fallback_router.generate(req.prompt, req.model)
    return response


@router.get("/health")
async def health():
    """Health check endpoint with circuit breaker status.
    
    Returns:
        dict: Server status and per-provider circuit breaker states
    """
    return {
        "status": "healthy",
        "circuits": fallback_router.circuit_status(),
    }


@router.get("/api/providers")
async def api_providers():
    """Admin endpoint for provider configuration and status.
    
    Returns which providers have API keys configured, the full list of available
    providers, current circuit breaker states, and CORS configuration.
    
    Returns:
        dict: Configuration and status information for all providers
    """
    configured = get_configured_providers()
    all_providers = list(PROVIDERS.keys())
    return {
        "configured": configured,
        "all_providers": all_providers,
        "circuits": fallback_router.circuit_status(),
        "cors_origin": settings.FRONTEND_URL,
    }

