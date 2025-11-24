import json
import logging
from typing import Dict, List, Any
from app.core.llm import llm_service
from app.agents.memory import MemoryManager

logger = logging.getLogger(__name__)

class LinearWriter:
    """
    Fast, linear chapter generator using LLM and Long-term Memory.
    Does NOT use MCTS.
    """
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def write_chapter(self, 
                          chapter_title: str, 
                          chapter_summary: str, 
                          world_setting: Dict, 
                          previous_summary: str,
                          language: str) -> str:
        
        # 1. Retrieve relevant memory
        context_query = f"{chapter_title}: {chapter_summary}"
        relevant_memories = self.memory.query_context(context_query)
        
        # 2. Construct Prompt
        prompt = f"""
        You are a best-selling novelist writing a chapter.
        
        Target Language: {language}
        
        Title: {chapter_title}
        Summary: {chapter_summary}
        
        World Setting:
        - Characters: {json.dumps(world_setting.get('characters', {}), ensure_ascii=False)}
        - Locations: {json.dumps(world_setting.get('locations', {}), ensure_ascii=False)}
        
        Previous Context:
        {previous_summary}
        
        Relevant Past Events:
        {relevant_memories}
        
        Task:
        Write the full content of this chapter. 
        - Focus on pacing, dialogue, and sensory details.
        - Maintain character consistency based on the World Setting.
        - Ensure logical continuity with Previous Context.
        
        Output only the story content.
        """
        
        # 3. Generate
        content = await llm_service.generate(prompt)
        return content

    async def rewrite_chapter(self, 
                            current_content: str, 
                            feedback: str, 
                            world_setting: Dict,
                            language: str) -> str:
        
        prompt = f"""
        You are an editor rewriting a chapter based on feedback.
        
        Target Language: {language}
        
        Current Draft:
        {current_content}
        
        World Context:
        {json.dumps(world_setting.get('characters', {}), ensure_ascii=False)}
        
        Feedback: {feedback}
        
        Task:
        Rewrite the chapter to address the feedback while maintaining quality and consistency.
        Output only the new story content.
        """
        
        content = await llm_service.generate(prompt)
        return content
