# Code Documentation Examples

This document provides examples of the documentation patterns used throughout the LLM Gateway codebase.

## Module-Level Docstrings

### Example: inference_service.py

```python
"""
Inference Service Module

Provides a unified interface for generating responses from any configured LLM provider.

This service acts as a dispatcher that:
  1. Routes requests to the appropriate provider class
  2. Validates that the provider exists
  3. Delegates actual API calls to provider-specific implementations

It does NOT handle error handling or fallback logic—those are managed by
the fallback_router service for resilience.
"""
```

**Pattern**:
- One-line description
- Blank line
- Longer explanation (2-3 sentences)
- Key behaviors or responsibilities
- Note about related modules

---

## Class Docstrings

### Example: FallbackRouter

```python
class FallbackRouter:
    """
    Tries providers in order.  Falls back automatically on failure.

    Parameters
    ----------
    provider_order : list[str]
        Provider names in priority order.
    cooldown : float
        Seconds a tripped circuit stays OPEN before moving to HALF_OPEN.
    max_retries_per_provider : int
        Max retries on 5xx errors before moving to the next provider.
    """
```

**Pattern**:
- Brief one-liner
- Parameters section (numpy-style)
- Notes about behavior and side effects

### Example: CircuitBreaker

```python
class _CircuitBreaker:
    """Per-provider circuit breaker with state machine.
    
    Implements the Circuit Breaker pattern to prevent cascading failures:
      - CLOSED: normal operation, requests proceed
      - OPEN: provider failed/rate-limited, requests are blocked
      - HALF_OPEN: cooldown expired, trying one probe request to recover
    
    Attributes:
        state: Current circuit state (CLOSED, OPEN, or HALF_OPEN)
        cooldown: Seconds to wait before transitioning OPEN → HALF_OPEN
        _opened_at: Timestamp when circuit was last tripped to OPEN
        _failure_count: Count of consecutive failures (used for diagnostics)
    """
```

**Pattern**:
- Brief description
- Implementation details (bullet points)
- Attributes section describing instance variables

---

## Method/Function Docstrings

### Example: Simple Async Method

```python
async def generate(self, prompt: str, model: str = None):
    """Generate a response from the specified provider.
    
    Args:
        prompt: The user's input prompt/query
        provider_name: Name of the provider (case-insensitive)
        model: Optional model name override (provider default used if None)
        
    Returns:
        dict: Provider response with generated text
        
    Raises:
        ValueError: If provider_name is not recognized
        HTTPException: If the provider's API returns an error
    """
```

**Pattern**:
- One-line summary
- Args section (Google-style)
- Returns section with type and description
- Raises section with exception types

### Example: Complex Method with Multiple Paths

```python
async def generate(self, prompt: str, model: str = None) -> dict:
    """Generate response using fallback router with circuit breaker protection.
    
    Tries configured providers in order. If a provider fails or is rate-limited,
    automatically falls back to the next available provider. Uses circuit breaker
    pattern to prevent cascading failures.
    
    Args:
        prompt: The user's input prompt/query
        model: Optional model override (uses provider defaults if not specified)
        
    Returns:
        dict: Response from the first successful provider
        
    Raises:
        HTTPException: If all providers fail or are circuit-open
    """
```

**Pattern**:
- One-liner
- Extended description of behavior
- Args, Returns, Raises sections
- Special note about patterns/algorithms used

---

## Pydantic Model Docstrings

```python
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
```

**Pattern**:
- Class docstring describing purpose
- Attributes section for each field
- Descriptions include defaults where relevant

---

## Inline Code Comments

### For Complex Logic

```python
def _is_rate_limited(status_code: int, detail: str) -> bool:
    """Check if error indicates rate limiting."""
    # Check both HTTP status code (429) and response text for rate-limit keywords
    if status_code == 429:
        return True
    detail_lower = detail.lower()
    return any(kw in detail_lower for kw in _RATE_LIMIT_KEYWORDS)
```

**Pattern**:
- Function docstring explains what
- Inline comments explain why/how for non-obvious logic

### For Non-Obvious Decisions

```python
def record_failure(self) -> None:
    """Record failed request—trip to OPEN state with cooldown timer."""
    self._failure_count += 1
    self.state = CircuitState.OPEN
    # Store timestamp so we know when cooldown expires
    self._opened_at = time.time()
```

**Pattern**:
- Why decisions are made
- Implementation consequences

### For State Machine Transitions

```python
# ── transitions ──────────────────────────────────────

def record_success(self) -> None:
    """Record successful request—reset to CLOSED state."""
    self.state = CircuitState.CLOSED
    self._failure_count = 0
```

**Pattern**:
- Section headers for grouping related methods
- State transitions documented in docstring

---

## Configuration/Settings Docstrings

```python
class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.
    
    All API keys are optional strings (default: empty). Services should validate
    that required API keys are present before use.
    
    Attributes:
        GEMINI_API_KEY: Google Gemini API key
        GROQ_API_KEY: Groq API key
        TOGETHER_API_KEY: Together AI API key
        OPENAI_API_KEY: OpenAI API key
        ANTHROPIC_API_KEY: Anthropic Claude API key
        OPENROUTER_API_KEY: OpenRouter API key (meta-provider for multiple models)
        MISTRAL_API_KEY: Mistral AI API key
        DEEPSEEK_API_KEY: DeepSeek API key
        XAI_API_KEY: xAI/Grok API key
        FRONTEND_URL: CORS allowed origins (default: "*" for all origins)
    """
```

**Pattern**:
- Explain loading mechanism
- Note about validation/defaults
- List all attributes with brief descriptions

---

## Error Handling Documentation

```python
if not settings.GROQ_API_KEY:
    # API key is required for this provider to function
    # Fail early and clearly rather than getting a 401 from the API
    raise HTTPException(
        status_code=400,
        detail="Groq API key not configured. Please add GROQ_API_KEY to your .env file."
    )
```

**Pattern**:
- Comment explains why we raise
- HTTPException includes user-friendly detail message
- Suggests resolution in error message

---

## Algorithm Documentation

### Example: Backoff Calculation

```python
# ── retry loop (5xx only) ───
for attempt in range(1, self.max_retries + 1):
    # ... try provider ...
    
    if _is_server_error(status):
        # Server errors are transient, so we retry with exponential backoff
        if attempt < self.max_retries:
            delay = 0.5 * attempt  # 0.5s, 1.0s, 1.5s...
            await asyncio.sleep(delay)
            continue
        else:
            # Max retries exceeded, move to next provider
            breaker.record_failure()
            break
```

**Pattern**:
- Explain why we use this strategy
- Document the formula (0.5 * attempt)
- Document termination conditions

---

## Best Practices Summary

1. **Module Level**: Explain purpose, key features, related modules
2. **Class Level**: Document state, patterns used, responsibilities
3. **Method Level**: Describe behavior, inputs, outputs, exceptions
4. **Inline Comments**: Explain non-obvious logic, trade-offs, why (not what)
5. **Consistency**: Use same style throughout (Google-style docstrings)
6. **Audience**: Write for future maintainers, not just current readers
7. **Updates**: Keep documentation in sync with code changes

---

## Tools Used

- **Python docstring format**: Google-style (Args, Returns, Raises)
- **Type hints**: Used throughout to clarify types
- **Section headers**: `# ────` style for visual grouping
- **Comments**: For clarifying decision rationale

---

## Related Documentation

- See `DOCUMENTATION.md` for complete API and feature docs
- See `QUICK_REFERENCE.md` for common tasks
- See `ARCHITECTURE.md` for system design
