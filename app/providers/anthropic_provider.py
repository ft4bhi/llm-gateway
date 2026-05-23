import httpx
from fastapi import HTTPException
from app.config.settings import settings
from app.config.model_config import DEFAULT_MODELS

class AnthropicProvider:
    BASE_URL = "https://api.anthropic.com/v1/messages"

    async def generate(self, prompt: str, model: str = None):
        target_model = model or DEFAULT_MODELS.get("anthropic")
        url = self.BASE_URL

        if not settings.ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=400,
                detail="Anthropic API key not configured. Please add ANTHROPIC_API_KEY to your .env file."
            )

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "max_tokens": 1024,
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
                
                print(f"[Anthropic Error] Status: {response.status_code}, Message: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Anthropic API error: {error_msg}"
                )

            data = response.json()
            text = data["content"][0]["text"]

            return {
                "provider": "anthropic",
                "response": text
            }

        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Anthropic timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )
