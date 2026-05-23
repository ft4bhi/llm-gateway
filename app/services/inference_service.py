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

from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.together_provider import TogetherProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.openrouter_provider import OpenRouterProvider
from app.providers.mistral_provider import MistralProvider
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.xai_provider import xAIProvider


class InferenceService:
    """Service for dispatching inference requests to configured LLM providers.
    
    Uses a match statement to route to the correct provider implementation.
    All provider implementations must have an async generate(prompt, model) method.
    """

    @staticmethod
    async def generate_response(prompt: str, provider_name: str, model: str = None):
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
        match provider_name.lower():
            case "gemini":
                provider = GeminiProvider()
            case "groq":
                provider = GroqProvider()
            case "together":
                provider = TogetherProvider()
            case "openai":
                provider = OpenAIProvider()
            case "anthropic":
                provider = AnthropicProvider()
            case "openrouter":
                provider = OpenRouterProvider()
            case "mistral":
                provider = MistralProvider()
            case "deepseek":
                provider = DeepSeekProvider()
            case "xai":
                provider = xAIProvider()
            case _:
                raise ValueError(f"Unknown provider: {provider_name}")
            
        return await provider.generate(prompt, model)