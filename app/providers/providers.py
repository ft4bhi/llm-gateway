"""
Unified provider registry.
Maps provider names to their class instances and exposes a factory function.
"""

from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.together_provider import TogetherProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.openrouter_provider import OpenRouterProvider
from app.providers.mistral_provider import MistralProvider
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.xai_provider import xAIProvider

# Canonical registry – keys are the provider names used across the gateway
PROVIDERS: dict[str, object] = {
    "groq": GroqProvider(),
    "gemini": GeminiProvider(),
    "together": TogetherProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "openrouter": OpenRouterProvider(),
    "mistral": MistralProvider(),
    "deepseek": DeepSeekProvider(),
    "xai": xAIProvider(),
}


def get_provider(name: str):
    """Return a provider instance by name, or raise ValueError."""
    provider = PROVIDERS.get(name.lower())
    if provider is None:
        raise ValueError(
            f"Unknown provider: '{name}'. "
            f"Available: {', '.join(PROVIDERS.keys())}"
        )
    return provider
