import httpx
from fastapi import HTTPException
from app.config.settings import settings
from app.config.model_config import DEFAULT_MODELS

class OpenRouterProvider:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, prompt: str, model: str = None):
        target_model = model or DEFAULT_MODELS.get("openrouter")
        url = self.BASE_URL

        if not settings.OPENROUTER_API_KEY:
            raise HTTPException(
                status_code=400,
                detail="OpenRouter API key not configured. Please add OPENROUTER_API_KEY to your .env file."
            )

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/abhi/llm-gateway", # Recommended by OpenRouter
            "X-Title": "LLM Gateway",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = response.text
                
                print(f"[OpenRouter Error] Status: {response.status_code}, Message: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenRouter API error: {error_msg}"
                )

            data = response.json()
            text = data["choices"][0]["message"]["content"]

            return {
                "provider": "openrouter",
                "response": text
            }

        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="OpenRouter timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )
