from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL

    async def generate(self, prompt: str, system_prompt: str = "You are a helpful assistant.", temperature: float = 0.7) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return f"Error generating text: {str(e)}"

    async def generate_json(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """Forces JSON output if supported or requests it in prompt"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt + "\nRespond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
             # Fallback for models that don't support response_format
            logger.warning(f"JSON mode failed or not supported, retrying normally: {e}")
            return await self.generate(prompt + "\nRespond in valid JSON format.", system_prompt)

llm_service = LLMService()
