import math
import random
import json
from typing import List, Optional, Dict
from app.core.llm import llm_service
from app.agents.memory import MemoryManager
import logging

logger = logging.getLogger(__name__)

class StoryNode:
    def __init__(self, content: str, parent: Optional['StoryNode'] = None, state: Dict = None):
        self.content = content
        self.parent = parent
        self.children: List['StoryNode'] = []
        self.visits = 0
        self.value = 0.0
        # State contains the 'local' view of the plan at this node
        # For planning, state includes: outline, world_setting, chapter_list
        self.state = state or {
            "outline": "", 
            "world_setting": {"characters": {}, "locations": {}, "rules": ""}, 
            "chapter_list": []
        }

    def uct_score(self, exploration_weight: float = 1.41):
        if self.visits == 0:
            return float('inf')
        return (self.value / self.visits) + exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)

    def is_leaf(self):
        return len(self.children) == 0

class MCTSBase:
    def __init__(self, memory_manager: MemoryManager, max_iterations: int = 10, branch_factor: int = 3):
        self.memory = memory_manager
        self.max_iterations = max_iterations
        self.branch_factor = branch_factor
        self.root = None

    async def run_search(self, initial_state: Dict, prompt: str, language: str = "Chinese") -> Dict:
        """
        Runs MCTS to generate a story plan.
        Returns the best state found (outline, world, chapters).
        """
        self.root = StoryNode(content=prompt, state=initial_state)
        current_node = self.root
        
        # For planning, we just do one deep search to generate the initial structure
        # We are not generating a sequence of steps, but refining a single plan
        
        logger.info(f"Starting MCTS Planning in {language}...")
        for _ in range(self.max_iterations):
            node = self._select(current_node)
            if node.visits == 0:
                await self._expand(node, language)
            
            if node.children:
                child = random.choice(node.children)
                score = await self._simulate(child, language)
                self._backpropagate(child, score)
            else:
                score = await self._simulate(node, language)
                self._backpropagate(node, score)
        
        if current_node.children:
            best_child = max(current_node.children, key=lambda n: n.visits)
            return best_child.state
        else:
            return current_node.state

    def _select(self, node: StoryNode) -> StoryNode:
        while not node.is_leaf():
            if not node.children:
                return node
            node = max(node.children, key=lambda n: n.uct_score())
        return node

    def _backpropagate(self, node: StoryNode, score: float):
        while node:
            node.visits += 1
            node.value += score
            node = node.parent

    async def _expand(self, node: StoryNode, language: str):
        raise NotImplementedError

    async def _simulate(self, node: StoryNode, language: str) -> float:
        raise NotImplementedError

class StoryPlanner(MCTSBase):
    """
    Planner for generating the initial Story Bible (Outline, World, Chapters).
    """
    
    async def _expand(self, node: StoryNode, language: str):
        premise = node.content
        
        prompt = f"""
        You are a Master Novelist planning a best-selling book.
        
        Premise: {premise}
        Target Language: {language}
        
        Generate {self.branch_factor} distinct, comprehensive story plans.
        Each plan must include:
        1. Story Outline (The main plot arc).
        2. World Setting (Characters, Locations, Rules).
        3. Chapter List (A list of chapter titles and brief summaries).
        
        Return JSON format:
        {{
            "options": [
                {{
                    "outline": "Detailed outline...",
                    "world_setting": {{
                        "characters": {{ "Name": {{ "desc": "...", "role": "..." }} }},
                        "locations": {{ "Name": {{ "desc": "..." }} }},
                        "rules": "World rules..."
                    }},
                    "chapter_list": [
                        {{ "title": "Chapter 1", "summary": "..." }},
                        {{ "title": "Chapter 2", "summary": "..." }}
                    ]
                }}
            ]
        }}
        """
        response = await llm_service.generate_json(prompt)
        await self._process_expansion_response(node, response)

    async def _process_expansion_response(self, node: StoryNode, response: str):
        try:
            data = json.loads(response)
            for opt in data.get("options", []):
                new_state = {
                    "outline": opt.get("outline", ""),
                    "world_setting": opt.get("world_setting", {}),
                    "chapter_list": opt.get("chapter_list", [])
                }
                # Content of the node is just a label for the path
                child = StoryNode(content="Plan Option", parent=node, state=new_state)
                node.children.append(child)
        except Exception as e:
            logger.error(f"Expansion failed: {e}")

    async def _simulate(self, node: StoryNode, language: str) -> float:
        prompt = f"""
        Critique this story plan for a bestseller.
        Target Language: {language}
        
        Outline: {node.state['outline']}
        Characters: {json.dumps(node.state['world_setting'].get('characters', {}))}
        
        Score 0.0-1.0 on:
        1. Marketability
        2. Character Depth
        3. Plot Logic
        
        Return JSON: {{ "score": 0.8 }}
        """
        response = await llm_service.generate_json(prompt)
        try:
            return float(json.loads(response).get("score", 0.5))
        except:
            return 0.5

    async def refine_plan(self, current_state: Dict, feedback: str, language: str) -> Dict:
        """
        Refines an existing plan based on user feedback.
        """
        prompt = f"""
        You are a Master Novelist refining a story plan based on editor feedback.
        
        Current Plan:
        Outline: {current_state['outline']}
        World: {json.dumps(current_state['world_setting'])}
        Chapters: {json.dumps(current_state['chapter_list'])}
        
        Feedback: {feedback}
        Target Language: {language}
        
        Modify the plan to address the feedback. Keep the rest consistent.
        
        Return JSON:
        {{
            "outline": "Updated outline...",
            "world_setting": {{ ... }},
            "chapter_list": [ ... ]
        }}
        """
        response = await llm_service.generate_json(prompt)
        try:
            return json.loads(response)
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return current_state
