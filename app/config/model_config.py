"""
Model Configuration Module

Defines default LLM models for each provider.

When a user doesn't specify a model in their request, these defaults are used.
Each provider has its own optimal model selection based on performance/cost tradeoffs.
"""

# Default model configuration for each provider
DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "together": "meta-llama/Llama-3-8b-chat-hf",
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "openrouter": "anthropic/claude-3-haiku",
    "mistral": "mistral-large-latest",
    "deepseek": "deepseek-chat",
    "xai": "grok-beta"
}
