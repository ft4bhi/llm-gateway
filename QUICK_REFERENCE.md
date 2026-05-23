# LLM Gateway - Quick Reference

## Setup

```bash
# Install dependencies
pip install fastapi uvicorn pydantic-settings httpx

# Create .env with API keys
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key
# ... etc

# Run server
uvicorn app.main:app --reload --port 5000
```

## API Endpoints

### Single Provider Request
```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is AI?",
    "provider": "groq",
    "model": "llama-3.3-70b-versatile"
  }'
```

### Fallback Routing Request
```bash
curl -X POST http://localhost:5000/generate-fallback \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing",
    "model": "gpt-4o"
  }'
```

### Health Check
```bash
curl http://localhost:5000/health
```

### Provider Status (Admin)
```bash
curl http://localhost:5000/api/providers
```

## File Guide

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app setup, CORS, static files |
| `api/route.py` | API endpoint definitions |
| `services/inference_service.py` | Provider dispatcher/router |
| `services/fallback_router.py` | Resilience: circuit breaker, retries, fallback |
| `providers/providers.py` | Provider registry |
| `providers/*.py` | Individual provider implementations |
| `config/settings.py` | Load environment variables |
| `config/model_config.py` | Default model per provider |
| `config/configured_providers.py` | Detect available providers |

## Key Concepts

**Circuit Breaker**: Prevents cascading failures
- CLOSED → requests allowed
- OPEN → requests blocked (cooldown: 60s)
- HALF_OPEN → probe attempt after cooldown

**Fallback Strategy**:
1. 429 (rate-limit) → trip OPEN immediately
2. 5xx errors → retry same provider (max 2 times, backoff)
3. 4xx errors → skip to next provider
4. Success → return response

**Provider Order**: Tries configured providers in order, then falls back to all available

## Supported Providers

- Groq (llama models)
- Google Gemini
- OpenAI (GPT series)
- Anthropic (Claude)
- Together AI
- OpenRouter (multi-provider)
- Mistral
- DeepSeek
- xAI (Grok)

## Common Issues

| Issue | Solution |
|-------|----------|
| "Unknown provider" | Add API key to .env |
| All circuits OPEN | Wait 60s or restart server |
| 503 Service Unavailable | All providers failed; retry later |
| Timeout (504) | Request took >30s; try simpler prompt |
| Import errors | Run `pip install -r requirements.txt` |

## Adding a New Provider

1. Create `providers/new_provider.py` with `NewProvider` class
2. Add to `providers/providers.py` PROVIDERS dict
3. Add default model to `config/model_config.py`
4. Add API key setting to `config/settings.py`

Pattern:
```python
class NewProvider:
    BASE_URL = "https://api..."
    async def generate(self, prompt: str, model: str = None):
        # httpx.AsyncClient POST request
        # Return: {"provider": "name", "response": "text"}
```

## Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check circuit status
# GET /health endpoint shows per-provider states

# Check configured providers
# GET /api/providers shows available options
```

## Response Format

```json
{
  "provider": "groq",
  "response": "Generated text response...",
  "fallback_used": false
}
```

On error:
```json
{
  "detail": "Error message here"
}
```

Status codes:
- 200: Success
- 400: Bad request / missing API key
- 503: All providers failed
- 504: Timeout
