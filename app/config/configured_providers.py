"""
Discover which providers have API keys configured in .env.
"""

from app.config.settings import settings

# Maps Settings field names → provider registry names
_KEY_TO_PROVIDER: dict[str, str] = {
    "GEMINI_API_KEY": "gemini",
    "GROQ_API_KEY": "groq",
    "TOGETHER_API_KEY": "together",
    "OPENAI_API_KEY": "openai",
    "ANTHROPIC_API_KEY": "anthropic",
    "OPENROUTER_API_KEY": "openrouter",
    "MISTRAL_API_KEY": "mistral",
    "DEEPSEEK_API_KEY": "deepseek",
    "XAI_API_KEY": "xai",
}


def get_configured_providers() -> list[str]:
    """Return provider names whose API key is non-empty in the environment."""
    return [
        provider
        for key, provider in _KEY_TO_PROVIDER.items()
        if getattr(settings, key, "").strip()
    ]
