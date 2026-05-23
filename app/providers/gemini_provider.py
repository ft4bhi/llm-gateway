import httpx
from fastapi import HTTPException

from app.config.settings import settings
from app.config.model_config import DEFAULT_MODELS


class GeminiProvider:

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate(self, prompt: str, model: str = None):
        
        target_model = model or DEFAULT_MODELS.get("gemini")
        url = f"{self.BASE_URL}/{target_model}:generateContent"
        params = {
            "key": settings.GEMINI_API_KEY
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:

            async with httpx.AsyncClient(timeout=30) as client:

                response = await client.post(
                    url,
                    params=params,
                    json=payload
                )

            # Parse Google's error response for better messages
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = response.text

                print(f"[Gemini Error] Status: {response.status_code}, Message: {error_msg}")

                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Gemini API error: {error_msg}"
                )

            data = response.json()

            text = data["candidates"][0]["content"]["parts"][0]["text"]

            return {
                "provider": "gemini",
                "response": text
            }

        except HTTPException:
            raise

        except httpx.TimeoutException:

            raise HTTPException(
                status_code=504,
                detail="Gemini timeout"
            )

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )