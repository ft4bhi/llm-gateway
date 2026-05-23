# LLM Gateway - Complete Documentation

## Overview

**LLM Gateway** is a unified API gateway for accessing multiple Large Language Model (LLM) providers with intelligent fallback routing, circuit breaker protection, and rate-limit awareness. It provides a single endpoint to leverage the strengths of different LLM providers while maintaining high availability through automatic provider failover.

## Key Features

- **Multi-Provider Support**: Access 9+ LLM providers (Groq, Gemini, OpenAI, Anthropic, Together, OpenRouter, Mistral, DeepSeek, xAI)
- **Fallback Routing**: Automatically tries the next provider if one fails or is rate-limited
- **Circuit Breaker Pattern**: Prevents cascading failures with intelligent circuit state management
- **Rate-Limit Detection**: Identifies and trips circuits on 429 errors and rate-limit keywords
- **Exponential Backoff**: Retries server errors (5xx) with intelligent delays
- **Admin Dashboard**: Web UI for monitoring provider status and circuit health
- **CORS Support**: Configurable cross-origin request handling

## Project Structure

```
app/
├── main.py                          # FastAPI application entry point
├── api/
│   └── route.py                     # API endpoint definitions
├── config/
│   ├── settings.py                  # Environment configuration (API keys)
│   ├── model_config.py              # Default models per provider
│   └── configured_providers.py      # Detects which providers are available
├── providers/
│   ├── providers.py                 # Provider registry and factory
│   ├── groq_provider.py             # Groq implementation
│   ├── gemini_provider.py           # Google Gemini implementation
│   ├── openai_provider.py           # OpenAI implementation
│   ├── anthropic_provider.py        # Anthropic Claude implementation
│   ├── together_provider.py         # Together AI implementation
│   ├── openrouter_provider.py       # OpenRouter implementation
│   ├── mistral_provider.py          # Mistral AI implementation
│   ├── deepseek_provider.py         # DeepSeek implementation
│   └── xai_provider.py              # xAI/Grok implementation
├── services/
│   ├── inference_service.py         # Provider dispatcher
│   └── fallback_router.py           # Fallback logic with circuit breaker
└── static/
    ├── index.html                   # Admin dashboard UI
    ├── app.js                       # Frontend JavaScript
    └── style.css                    # Frontend styling
```

## Core Modules

### `app/main.py` - Application Entry Point

The FastAPI application with:
- CORS middleware configuration
- Static file mounting for the admin dashboard
- API router inclusion
- Root endpoint serving the dashboard

**Key Endpoints**:
- `GET /`: Serve admin dashboard (index.html)
- `GET /favicon.ico`: Favicon endpoint

### `app/api/route.py` - API Routes

Defines all public API endpoints:

#### `POST /generate`
Generate response from a single provider.

**Request**:
```json
{
  "prompt": "What is machine learning?",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile"  // optional
}
```

**Response**:
```json
{
  "provider": "groq",
  "response": "Machine learning is a subset of artificial intelligence..."
}
```

#### `POST /generate-fallback`
Generate response with multi-provider fallback.

**Request**:
```json
{
  "prompt": "Explain quantum computing",
  "model": "gpt-4o"  // optional override
}
```

**Response**:
```json
{
  "provider": "groq",
  "response": "Quantum computing is...",
  "fallback_used": false
}
```

#### `GET /health`
Health check with circuit breaker status.

**Response**:
```json
{
  "status": "healthy",
  "circuits": {
    "groq": {"state": "CLOSED", "reopens_in_secs": 0.0},
    "gemini": {"state": "HALF_OPEN", "reopens_in_secs": 0.0},
    "openai": {"state": "OPEN", "reopens_in_secs": 45.3}
  }
}
```

#### `GET /api/providers`
Admin endpoint showing provider configuration.

**Response**:
```json
{
  "configured": ["groq", "openai", "anthropic"],
  "all_providers": ["groq", "gemini", "openai", "anthropic", ...],
  "circuits": { /* circuit status */ },
  "cors_origin": "http://localhost:3000"
}
```

### `app/config/settings.py` - Configuration Management

Uses **pydantic-settings** to load environment variables from `.env` file.

**Environment Variables**:
```bash
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
TOGETHER_API_KEY=your_together_key
OPENROUTER_API_KEY=your_openrouter_key
MISTRAL_API_KEY=your_mistral_key
DEEPSEEK_API_KEY=your_deepseek_key
XAI_API_KEY=your_xai_key
FRONTEND_URL=http://localhost:3000,http://localhost:5173
```

### `app/config/model_config.py` - Default Models

Maps each provider to its default model (used when user doesn't specify one).

Example defaults:
- **Groq**: `llama-3.3-70b-versatile`
- **OpenAI**: `gpt-4o`
- **Anthropic**: `claude-3-5-sonnet-20241022`
- **Gemini**: `gemini-2.0-flash`

### `app/config/configured_providers.py` - Provider Discovery

Dynamically detects which providers are available based on API key configuration.

```python
get_configured_providers()  # Returns: ["groq", "openai", "anthropic"]
```

### `app/services/inference_service.py` - Provider Dispatcher

Routes inference requests to the appropriate provider class. Uses a match statement for provider selection.

```python
await InferenceService.generate_response(
    prompt="Hello!",
    provider_name="groq",
    model="llama-3.3-70b-versatile"
)
```

### `app/services/fallback_router.py` - Resilience & Fallback Logic

The core resilience engine implementing:

#### Circuit Breaker Pattern
Three states per provider:
- **CLOSED**: Normal operation, requests proceed
- **OPEN**: Provider failed/rate-limited, requests blocked
- **HALF_OPEN**: Cooldown expired, trying one probe request

#### Error Handling Strategy
1. **Rate Limit (429)**: Immediately trip circuit OPEN, try next provider
2. **Server Error (5xx)**: Retry same provider with exponential backoff (max 2 attempts)
3. **Client Error (4xx)**: Don't retry, move to next provider
4. **Other Errors**: Log and move to next provider

#### Partial Text Continuation
If a provider partially responds before failing, the router builds a continuation prompt asking the next provider to pick up where the previous one left off.

**Example**:
```
Provider A returns: "Quantum computing uses..."
Provider A fails

Router builds for Provider B:
"The following text was partially generated...
--- PARTIAL TEXT ---
Quantum computing uses...
--- END PARTIAL TEXT ---

--- ORIGINAL PROMPT ---
Explain quantum computing
--- END ORIGINAL PROMPT ---"
```

## Provider Implementation Pattern

All providers implement the same interface:

```python
class ProviderName:
    BASE_URL = "https://api.provider.com/..."
    
    async def generate(self, prompt: str, model: str = None) -> dict:
        """
        Generate a response from the provider.
        
        Args:
            prompt: User input prompt
            model: Optional model override
            
        Returns:
            {"provider": "name", "response": "generated text"}
            
        Raises:
            HTTPException: On API errors
        """
        # Implementation
```

**Key Characteristics**:
- All API calls are async (using httpx.AsyncClient)
- 30-second timeout for all requests
- Proper error handling with HTTPException
- Support for optional model override
- Standardized response format

## Circuit Breaker State Transitions

```
        ┌─────────────┐
        │   CLOSED    │  (normal operation)
        └──────┬──────┘
               │ failure/rate-limit
               ↓
        ┌─────────────┐
        │    OPEN     │  (blocking requests)
        └──────┬──────┘
               │ cooldown expires
               ↓
        ┌──────────────┐
        │  HALF_OPEN   │  (probe attempt)
        └──────┬───────┘
         success│failure
              ↙ ↘
        ┌──────┐ ┌──────┐
        │CLOSED│ │ OPEN │
        └──────┘ └──────┘
```

**Cooldown Default**: 60 seconds

## Fallback Provider Order

The fallback router tries providers in this order by default:
1. Providers with configured API keys (in the order found in config)
2. Falls back to all available providers if none are configured

Example flow with two providers configured:
```
Request → Provider 1 (Groq)
          ↓ fails/rate-limited
          → Provider 2 (OpenAI)
            ↓ fails
            → HTTP 503 "All providers exhausted"
```

## Error Responses

### 400 Bad Request
API key not configured for the requested provider.

### 503 Service Unavailable
All providers exhausted or circuits are OPEN.

```json
{
  "detail": "All LLM providers are currently unavailable. Tried order: [groq, openai]. Please retry later."
}
```

### 504 Gateway Timeout
Request exceeded 30-second timeout.

## Development & Configuration

### Running the Server

```bash
# Install dependencies
pip install fastapi uvicorn pydantic-settings httpx

# Set up .env file
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload --port 5000
```

### Environment Setup

Create `.env` file in project root:
```bash
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
# ... other API keys
FRONTEND_URL=http://localhost:3000
```

### Adding a New Provider

1. Create `app/providers/new_provider.py`:
```python
class NewProvider:
    BASE_URL = "https://api.provider.com/..."
    
    async def generate(self, prompt: str, model: str = None):
        # Implementation following the pattern
        return {"provider": "new_provider", "response": "..."}
```

2. Update `app/providers/providers.py`:
```python
from app.providers.new_provider import NewProvider

PROVIDERS = {
    # ...existing...
    "new_provider": NewProvider(),
}
```

3. Update `app/config/model_config.py`:
```python
DEFAULT_MODELS = {
    # ...existing...
    "new_provider": "default-model-name",
}
```

4. Update `app/config/settings.py`:
```python
NEW_PROVIDER_API_KEY: str = ""
```

## Monitoring & Admin Dashboard

The admin dashboard (`/`) provides:
- List of available providers
- Circuit breaker status for each provider
- Provider health indicators
- CORS configuration

Access at `http://localhost:5000`

## Performance Characteristics

- **Request Timeout**: 30 seconds per provider
- **Circuit Cooldown**: 60 seconds (default)
- **Max Retries**: 2 attempts per provider on 5xx errors
- **Backoff Strategy**: 0.5s, 1.0s exponential delays

## Security Considerations

1. **API Keys**: Never commit `.env` to version control
2. **CORS**: Explicitly configure FRONTEND_URL rather than using "*"
3. **Rate Limiting**: Implement rate limiting at the gateway level for production
4. **Authentication**: Add authentication middleware for sensitive deployments

## Troubleshooting

### All Circuits Show OPEN
- Check API key validity for the provider
- Verify network connectivity
- Wait for cooldown period (60s) or restart to reset circuits

### Partial Responses
- Check provider token limits or rate limits
- Use smaller prompts or enable streaming for large responses

### High Latency
- Check individual provider response times
- Consider adjusting the provider order to faster providers first
- Implement request caching for repeated queries

## Contributing

When adding features:
1. Add docstrings to all classes and public methods
2. Follow existing error handling patterns
3. Test with multiple providers in `.env`
4. Update this documentation

## Architecture Diagram

```
┌─────────────────┐
│   HTTP Client   │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│   FastAPI Application (main.py)    │
│  ┌────────────────────────────────┐ │
│  │  CORS Middleware               │ │
│  └────────────────────────────────┘ │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ↓                     ↓
    ┌─────────┐        ┌──────────────┐
    │/generate│        │/generate-    │
    │         │        │fallback      │
    └────┬────┘        └──────┬───────┘
         │                    │
         ↓                    ↓
  ┌─────────────┐     ┌──────────────────┐
  │Inference    │     │FallbackRouter    │
  │Service      │     │ ┌──────────────┐ │
  │             │     │ │CircuitBreaker│ │
  └────┬────────┘     │ │(per-provider)│ │
       │              │ └──────────────┘ │
       ↓              │ ┌──────────────┐ │
    Provider          │ │Error Handler │ │
    Registry          │ │& Retry Logic │ │
       │              │ └──────────────┘ │
       └─────┬────────┴──────┬───────────┘
             │               │
    ┌────────┴───────────────┴─────────┐
    │                                  │
    ↓                                  ↓
┌─────────────────┐         ┌──────────────────┐
│Provider Classes │         │External LLM APIs │
│  - GroqProvider │         │ (Groq, OpenAI,  │
│  - OpenAIProvider           etc.)           │
│  - etc.         │         │                  │
└─────────────────┘         └──────────────────┘
```

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-23
