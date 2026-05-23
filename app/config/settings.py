"""
Settings and Configuration Module

Loads environment variables from .env file using pydantic-settings.
All API keys for supported LLM providers and application settings are defined here.

Environment Variables:
  - *_API_KEY: API keys for each supported provider (Gemini, Groq, Together, etc.)
  - FRONTEND_URL: CORS-allowed origins for the frontend (comma-separated)

The Settings class is instantiated as a singleton module-level object.
"""

from pydantic_settings import BaseSettings


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

    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    XAI_API_KEY: str = ""

    FRONTEND_URL: str = "*"

    class Config:
        env_file = ".env"


# Global settings singleton
settings = Settings()