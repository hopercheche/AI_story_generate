
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM Settings
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    
    # ScrapingDog Settings
    SCRAPINGDOG_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
