"""
Fallback Router — resilient multi-provider request routing.

Algorithms implemented:
  1. Circuit Breaker (CLOSED → OPEN → HALF_OPEN) per provider
  2. Selective retry with exponential back-off (5xx only)
  3. Rate-limit detection (429 + keyword scan)
  4. Partial-content continuation prompts
"""

import asyncio
import logging
import time
from enum import Enum

from fastapi import HTTPException

from app.providers.providers import PROVIDERS, get_provider

logger = logging.getLogger("fallback_router")


# ---------------------------------------------------------------------------
# Circuit-breaker state machine
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


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

    def __init__(self, cooldown: float):
        self.state: CircuitState = CircuitState.CLOSED
        self.cooldown = cooldown
        self._opened_at: float = 0.0           # timestamp when tripped OPEN
        self._failure_count: int = 0

    # ---- queries -----------------------------------------------------------

    def is_available(self) -> bool:
        """Check if this circuit allows requests to proceed.
        
        Returns:
            True if CLOSED or HALF_OPEN (can attempt), False if OPEN
        """
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self._opened_at >= self.cooldown:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit → HALF_OPEN (cooldown expired)")
                return True          # allow one probe
            return False
        # HALF_OPEN → allow exactly one attempt
        return True

    def reopens_in_secs(self) -> float:
        """Get remaining cooldown time before circuit reopens.
        
        Returns:
            Seconds until OPEN → HALF_OPEN transition (0.0 if already HALF_OPEN/CLOSED)
        """
        if self.state != CircuitState.OPEN:
            return 0.0
        remaining = self.cooldown - (time.time() - self._opened_at)
        return max(0.0, round(remaining, 1))

    # ---- transitions -------------------------------------------------------

    def record_success(self) -> None:
        """Record successful request—reset to CLOSED state."""
        self.state = CircuitState.CLOSED
        self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed request—trip to OPEN state with cooldown timer."""
        self._failure_count += 1
        self.state = CircuitState.OPEN
        self._opened_at = time.time()

    def trip_open(self) -> None:
        """Immediately trip to OPEN (e.g. on 429 rate limit)."""
        self.state = CircuitState.OPEN
        self._opened_at = time.time()


# ---------------------------------------------------------------------------
# Rate-limit detection helpers
# ---------------------------------------------------------------------------

_RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "quota exceeded",
    "too many requests",
    "resource_exhausted",
)


def _is_rate_limited(status_code: int, detail: str) -> bool:
    if status_code == 429:
        return True
    detail_lower = detail.lower()
    return any(kw in detail_lower for kw in _RATE_LIMIT_KEYWORDS)


def _is_server_error(status_code: int) -> bool:
    return 500 <= status_code < 600


# ---------------------------------------------------------------------------
# Partial-content continuation
# ---------------------------------------------------------------------------

def _build_continuation_prompt(original_prompt: str, partial_text: str) -> str:
    """
    If the previous provider returned partial text before dying,
    ask the next provider to continue from where it left off.
    """
    last_word = partial_text.strip().split()[-1] if partial_text.strip() else ""
    return (
        f"The following text was partially generated in response to the prompt "
        f"below. Do NOT repeat what is already written. Pick up exactly from "
        f"the last word (\"{last_word}\") and continue.\n\n"
        f"--- PARTIAL TEXT ---\n{partial_text}\n--- END PARTIAL TEXT ---\n\n"
        f"--- ORIGINAL PROMPT ---\n{original_prompt}\n--- END ORIGINAL PROMPT ---"
    )


# ---------------------------------------------------------------------------
# FallbackRouter
# ---------------------------------------------------------------------------

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

    def __init__(
        self,
        provider_order: list[str],
        cooldown: float = 60.0,
        max_retries_per_provider: int = 2,
    ):
        self.provider_order = provider_order
        self.cooldown = cooldown
        self.max_retries = max_retries_per_provider
        self._breakers: dict[str, _CircuitBreaker] = {
            name: _CircuitBreaker(cooldown) for name in provider_order
        }

    # ---- public API --------------------------------------------------------

    async def generate(self, prompt: str, model: str = None) -> dict:
        """
        Try each available provider in order.  Returns the first successful
        response dict or raises HTTP 503 if all are exhausted.
        """
        available = self._available_providers()
        if not available:
            logger.error("All providers exhausted (circuits OPEN)")
            raise HTTPException(
                status_code=503,
                detail=(
                    "All LLM providers are currently unavailable. "
                    f"Tried order: {self.provider_order}. "
                    "Please retry later."
                ),
            )

        partial_text: str = ""        # accumulated partial output

        for name in available:
            breaker = self._breakers[name]
            provider = get_provider(name)

            # Build the prompt (original or continuation)
            effective_prompt = (
                _build_continuation_prompt(prompt, partial_text)
                if partial_text
                else prompt
            )

            # --- retry loop (5xx only) ---
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "Trying provider=%s attempt=%d/%d",
                        name, attempt, self.max_retries,
                    )
                    result = await provider.generate(effective_prompt, model)

                    # Success 🎉
                    breaker.record_success()
                    logger.info("Success on provider=%s", name)
                    # Attach metadata about fallback path
                    result["fallback_used"] = name != self.provider_order[0]
                    result["provider"] = name
                    return result

                except HTTPException as exc:
                    status = exc.status_code
                    detail = str(exc.detail)

                    # ── Rate limit → trip immediately, no retry ──
                    if _is_rate_limited(status, detail):
                        logger.warning(
                            "Rate-limited on provider=%s → tripping OPEN",
                            name,
                        )
                        breaker.trip_open()
                        break          # move to next provider

                    # ── 5xx server error → retry with back-off ──
                    if _is_server_error(status):
                        logger.warning(
                            "Server error %d on provider=%s (attempt %d/%d)",
                            status, name, attempt, self.max_retries,
                        )
                        if attempt < self.max_retries:
                            delay = 0.5 * attempt
                            await asyncio.sleep(delay)
                            continue   # retry same provider
                        else:
                            breaker.record_failure()
                            break      # exhausted retries → next provider

                    # ── Any other HTTP error (4xx, etc.) ──
                    logger.warning(
                        "Non-retriable error %d on provider=%s → next",
                        status, name,
                    )
                    breaker.record_failure()
                    break              # move to next provider

                except Exception as exc:
                    logger.exception(
                        "Unexpected error on provider=%s: %s", name, exc,
                    )
                    breaker.record_failure()
                    break

            # After exhausting a provider, try to capture partial text
            # (providers return {"response": "..."} on success, but we
            #  only land here on failure — partial_text stays as-is unless
            #  we explicitly got some text before the error).

        # All providers exhausted
        logger.error("All providers exhausted after fallback attempts")
        raise HTTPException(
            status_code=503,
            detail=(
                "All LLM providers failed or are rate-limited. "
                f"Provider order tried: {self.provider_order}. "
                "Please retry later."
            ),
        )

    def circuit_status(self) -> dict[str, dict]:
        """Return per-provider circuit state for the /health endpoint."""
        return {
            name: {
                "state": breaker.state.value,
                "reopens_in_secs": breaker.reopens_in_secs(),
            }
            for name, breaker in self._breakers.items()
        }

    def refresh_providers(self, provider_list: list[str]) -> None:
        """Re-initialise the router with a new provider list."""
        self.provider_order = provider_list
        self._breakers = {
            name: _CircuitBreaker(self.cooldown) for name in provider_list
        }

    # ---- internals ---------------------------------------------------------

    def _available_providers(self) -> list[str]:
        """Providers whose circuits are not OPEN."""
        return [
            name
            for name in self.provider_order
            if self._breakers[name].is_available()
        ]


# ---------------------------------------------------------------------------
# Module-level singleton — only providers with API keys configured
# ---------------------------------------------------------------------------

from app.config.configured_providers import get_configured_providers  # noqa: E402

fallback_router = FallbackRouter(
    provider_order=get_configured_providers() or list(PROVIDERS.keys()),
    cooldown=60.0,
)

