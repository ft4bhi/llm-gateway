# LLM Gateway - Architecture Guide

## System Architecture

### High-Level Overview

```
┌─────────────┐
│HTTP Requests│
└──────┬──────┘
       │
       ↓
┌────────────────────────────────┐
│FastAPI Application             │
│├─ CORS Middleware              │
│├─ Static Files (Dashboard)     │
│└─ Route Handler                │
└────────┬───────────────────────┘
         │
         ├─/generate ──────→ InferenceService → Single Provider
         │
         └─/generate-fallback → FallbackRouter ──→ Multi-Provider with Circuit Breaker
         
         /health ──────────→ Circuit Status
         /api/providers ───→ Admin Info
```

## Component Breakdown

### Layer 1: API Gateway (main.py, api/route.py)
- **Responsibility**: HTTP request handling and routing
- **Technologies**: FastAPI, CORS middleware
- **Key Features**:
  - Request validation with Pydantic models
  - CORS configuration from environment
  - Static file serving
  - Health and admin endpoints

### Layer 2: Service Layer (inference_service.py, fallback_router.py)

#### InferenceService
- **Responsibility**: Route to correct provider
- **Pattern**: Dispatcher pattern
- **Behavior**: Single provider, no fallback

#### FallbackRouter
- **Responsibility**: Resilient multi-provider orchestration
- **Patterns**:
  - Circuit Breaker (per-provider state machine)
  - Retry with exponential backoff
  - Rate-limit detection
  - Partial text continuation
- **Key Logic**:
  ```
  For each provider in order:
    While attempt <= max_retries:
      Try provider.generate()
      
      On success → return response
      
      On 429 → trip circuit OPEN, next provider
      
      On 5xx → retry with delay (exponential)
      
      On 4xx → next provider
      
      On other error → next provider
  
  If all providers fail → HTTP 503
  ```

### Layer 3: Provider Layer (providers/)

#### Base Pattern
Each provider implements:
```python
class XyzProvider:
    BASE_URL = "https://api.xyz.com/..."
    
    async def generate(self, prompt: str, model: str = None) -> dict:
        # 1. Validate API key configured
        # 2. Build request headers (auth) and payload
        # 3. POST to provider API with 30s timeout
        # 4. Parse response or raise HTTPException
        # 5. Return {"provider": "xyz", "response": "text"}
```

#### Characteristics
- **Async/await** for non-blocking I/O
- **httpx.AsyncClient** for HTTP
- **30-second timeout** universally applied
- **Standardized error handling** with HTTPException
- **No retry logic** (handled by FallbackRouter)

### Layer 4: Configuration (config/)

#### settings.py
- Loads environment variables
- Validates at instantiation time
- Singleton instance used throughout

#### model_config.py
- Maps provider → default model
- Used as fallback when user doesn't specify

#### configured_providers.py
- Detects which providers have API keys
- Returns list of available providers
- Used to initialize FallbackRouter

### Layer 5: Static Files (static/)
- HTML dashboard
- JavaScript for interactivity
- CSS styling
- Mounted at `/static` route

## Data Flow Examples

### Single Provider Request
```
POST /generate
  ↓
PromptRequest validation
  ↓
InferenceService.generate_response(prompt, provider, model)
  ↓
Match provider name → instantiate provider class
  ↓
Provider.generate(prompt, model_or_default)
  ↓
HTTP POST to provider API
  ↓
Parse response JSON
  ↓
Return {"provider": "...", "response": "..."}
```

### Fallback Request
```
POST /generate-fallback
  ↓
FallbackRequest validation
  ↓
FallbackRouter.generate(prompt, model)
  ↓
Get available_providers (circuits not OPEN)
  ↓
For each provider:
    ↓
    Provider.generate(prompt, model_or_default)
    ↓
    Success? → record_success(), return response
    ↓
    Rate-limited (429)? → trip_open(), try next
    ↓
    Server error (5xx)? → retry with backoff
    ↓
    Other error? → record_failure(), try next
    ↓
All failed? → HTTP 503
```

## Circuit Breaker State Machine

```
CLOSED
  ↓ (on failure)
OPEN [start cooldown timer]
  ↓ (after 60s cooldown)
HALF_OPEN [allow one probe]
  ├─ (success) → CLOSED
  └─ (failure) → OPEN [restart cooldown]
```

**State Behaviors**:
- **CLOSED**: Normal, requests pass through
- **OPEN**: Blocked, return 503 without trying
- **HALF_OPEN**: Probe attempt, one chance to recover

**Trigger Events**:
- Failure (non-retriable or max retries exceeded) → OPEN
- Rate-limit (429) → OPEN (immediate, no backoff)
- Success → CLOSED
- Cooldown expiry → HALF_OPEN (from OPEN)

## Resilience Strategies

### Strategy 1: Rate-Limit Detection
```
If status == 429:
  trip_open() → block future requests immediately
Elif "rate limit" in response_text:
  trip_open() → keyword detection
```

### Strategy 2: Server Error Retry
```
If 500 <= status < 600:
  For attempt in range(1, max_retries + 1):
    Retry with backoff = 0.5 * attempt seconds
    If success → return
    If attempt == max_retries → next provider
```

### Strategy 3: Partial Text Continuation
```
If provider returns partial text before timeout:
  Build new prompt asking to continue from last word
  Next provider.generate(continuation_prompt)
```

## Error Handling Hierarchy

```
Provider.generate()
  ↑
  ├─ HTTPException (400, 429, 500, etc.)
  │  └─ FallbackRouter decides action
  │     ├─ 429 → trip circuit
  │     ├─ 5xx → retry with backoff
  │     └─ other → next provider
  │
  ├─ Timeout exception
  │  └─ Record failure, next provider
  │
  └─ Generic exception
     └─ Log, record failure, next provider

If all providers fail:
  Raise HTTPException(503, "All providers exhausted")
```

## Configuration Injection

```
main.py
  ↓
imports settings
  ↓
FallbackRouter initialized with:
  - provider_order = get_configured_providers()
  - cooldown = 60.0
  - max_retries = 2
```

This allows:
- Changing provider order via .env
- Adjusting cooldown for testing
- Limiting retry attempts

## Performance Characteristics

| Metric | Value | Note |
|--------|-------|------|
| Request Timeout | 30s | Per provider |
| Circuit Cooldown | 60s | OPEN → HALF_OPEN |
| Max Retries | 2 | 5xx errors only |
| Backoff Delay 1 | 0.5s | After 1st failure |
| Backoff Delay 2 | 1.0s | After 2nd failure |
| Concurrent Requests | Unlimited | Limited by event loop |
| Memory per Circuit | ~100 bytes | Small fixed overhead |

## Extensibility Points

### Adding a Provider
1. Create `providers/xyz_provider.py`
2. Implement `XyzProvider.generate()`
3. Register in `providers.py`
4. Add to `model_config.py`
5. Add settings to `settings.py`

### Customizing Fallback Logic
Edit `fallback_router.py`:
- Adjust `cooldown` (line: FallbackRouter init)
- Change `max_retries` (line: FallbackRouter init)
- Modify `_RATE_LIMIT_KEYWORDS` (line: detection)
- Edit `_build_continuation_prompt()` (line: partial text)

### Adjusting Timeouts
- Per-provider: Edit `httpx.AsyncClient(timeout=30)`
- Global: Centralize timeout in settings

## Testing Considerations

### Unit Testing
- Mock httpx.AsyncClient
- Test circuit breaker state transitions
- Verify error classification (429 vs 5xx vs 4xx)

### Integration Testing
- Use real API keys or sandbox environments
- Test provider failover scenarios
- Verify circuit recovery after cooldown

### Load Testing
- Monitor circuit state under high load
- Verify backoff doesn't starve other providers
- Check memory usage with many concurrent requests

## Deployment Considerations

### Production Checklist
- [ ] Set explicit FRONTEND_URL (not "*")
- [ ] Configure API keys as secrets
- [ ] Enable logging/monitoring
- [ ] Set appropriate circuit cooldown
- [ ] Consider reverse proxy (nginx) for rate limiting
- [ ] Add request ID tracing
- [ ] Monitor provider latencies
- [ ] Set up alerts for circuit trips

### Scaling Strategies
- Horizontal: Load balance requests across gateway instances
- Each instance maintains independent circuit breakers
- Consider centralized circuit breaker state for multi-instance deployments

---

This architecture provides:
- **Resilience**: Circuit breakers prevent cascading failures
- **Flexibility**: Easy to add/remove providers
- **Observability**: Circuit status and provider health visible
- **Performance**: Async I/O, optional retries and backoff
- **Maintainability**: Clear separation of concerns
