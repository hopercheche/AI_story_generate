import requests
from bs4 import BeautifulSoup
from app.core.config import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResearcherAgent:
    def __init__(self):
        self.api_key = settings.SCRAPINGDOG_API_KEY
        self.base_url = "https://api.scrapingdog.com/scrape"

    async def search_and_extract(self, query: str) -> Dict[str, Any]:
        """
        Uses ScrapingDog to search for information related to the query.
        """
        if not self.api_key:
            logger.warning("ScrapingDog API Key not found. Skipping research.")
            return {"error": "API Key missing", "data": "No research performed."}

        logger.info(f"Researching topic: {query}")
        
        # Construct a search URL (e.g., Google Search)
        search_url = f"https://www.google.com/search?q={query}"
        
        params = {
            "api_key": self.api_key,
            "url": search_url,
            "dynamic": "false", 
        }

        try:
            response = requests.get(self.base_url, params=params)
            
            if response.status_code == 200:
                # Parse HTML to extract meaningful text
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Break into lines and remove leading/trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # Drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Limit text length to avoid overwhelming LLM
                summary = text[:2000] + "..." if len(text) > 2000 else text
                
                return {
                    "status": "success", 
                    "source": "ScrapingDog",
                    "data": summary
                }
            else:
                logger.error(f"ScrapingDog failed: {response.status_code} - {response.text}")
                return {"status": "error", "message": "Failed to fetch data"}

        except Exception as e:
            logger.error(f"Research error: {e}")
            return {"status": "error", "message": str(e)}

researcher = ResearcherAgent()
