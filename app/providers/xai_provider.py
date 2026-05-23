import httpx
from fastapi import HTTPException
from app.config.settings import settings
from app.config.model_config import DEFAULT_MODELS

class xAIProvider:
    BASE_URL = "https://api.x.ai/v1/chat/completions"

    async def generate(self, prompt: str, model: str = None):
        target_model = model or DEFAULT_MODELS.get("xai")
        if not settings.XAI_API_KEY:
            raise HTTPException(
                status_code=400,
                detail="xAI API key not configured. Please add XAI_API_KEY to your .env file."
            )

        headers = {
            "Authorization": f"Bearer {settings.XAI_API_KEY}",
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
                
                print(f"[xAI Error] Status: {response.status_code}, Message: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"xAI API error: {error_msg}"
                )

            data = response.json()
            text = data["choices"][0]["message"]["content"]

            return {
                "provider": "xai",
                "response": text
            }

        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="xAI timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )
