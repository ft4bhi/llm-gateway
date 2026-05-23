"""
Groq Provider Module

Implements LLM inference via Groq's API (OpenAI-compatible endpoint).
Groq is known for fast inference on open-source models like Llama.
"""

import httpx
from fastapi import HTTPException
from app.config.settings import settings
from app.config.model_config import DEFAULT_MODELS


class GroqProvider:
    """Groq LLM provider implementation.
    
    Groq API is OpenAI-compatible and uses the standard chat completions format.
    Requires GROQ_API_KEY to be set in environment variables.
    
    Attributes:
        BASE_URL: Groq API endpoint for chat completions
    """
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    async def generate(self, prompt: str, model: str = None):
        """Generate a response from Groq.
        
        Args:
            prompt: User input prompt/query
            model: Model to use (default: llama-3.3-70b-versatile)
            
        Returns:
            dict: Response containing provider name and generated text
            
        Raises:
            HTTPException: 400 if API key not configured
            HTTPException: 504 on timeout (30s)
            HTTPException: Various status codes for API errors
        """
        target_model = model or DEFAULT_MODELS.get("groq")
        if not settings.GROQ_API_KEY:
            raise HTTPException(
                status_code=400,
                detail="Groq API key not configured. Please add GROQ_API_KEY to your .env file."
            )

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload
                )

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = response.text
                
                print(f"[Groq Error] Status: {response.status_code}, Message: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Groq API error: {error_msg}"
                )

            data = response.json()
            text = data["choices"][0]["message"]["content"]

            return {
                "provider": "groq",
                "response": text
            }

        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Groq timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )
