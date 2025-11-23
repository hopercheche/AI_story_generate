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
        # State contains the 'local' view of the world at this node
        self.state = state or {"summary": "", "characters": {}, "foreshadowing": []}

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

    async def run_search(self, initial_state: Dict, prompt: str, steps: int = 5) -> List[str]:
        self.root = StoryNode(content=prompt, state=initial_state)
        current_node = self.root
        sequence = []
        
        for i in range(steps):
            logger.info(f"MCTS Step {i+1}/{steps}")
            for _ in range(self.max_iterations):
                node = self._select(current_node)
                if not self._is_terminal(node):
                    if node.visits == 0:
                        await self._expand(node)
                    
                    if node.children:
                        child = random.choice(node.children)
                        score = await self._simulate(child)
                        self._backpropagate(child, score)
                    else:
                        score = await self._simulate(node)
                        self._backpropagate(node, score)
            
            if current_node.children:
                best_child = max(current_node.children, key=lambda n: n.visits)
                current_node = best_child
                sequence.append(current_node.content)
                
                # Commit to memory
                self.memory.add_event(current_node.content, metadata={"type": "plot_point"})
                self.memory.update_world_state(current_node.state)
            else:
                break
                
        return sequence

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

    def _is_terminal(self, node: StoryNode):
        return False
        
    async def _expand(self, node: StoryNode):
        raise NotImplementedError

    async def _simulate(self, node: StoryNode) -> float:
        raise NotImplementedError

class StoryPlanner(MCTSBase):
    """High-level planner for the entire story arc."""
    
    async def _expand(self, node: StoryNode):
        memory_context = self.memory.get_state_summary()
        
        prompt = f"""
        You are a Master Novelist planning a best-selling book.
        
        Current Story Arc: {node.state.get('summary')}
        Last Major Event: {node.content}
        
        {memory_context}
        
        Generate {self.branch_factor} distinct, high-level plot directions for the NEXT MAJOR PHASE of the story.
        Focus on broad strokes, major twists, and character arcs.
        
        Return JSON:
        {{
            "options": [
                {{
                    "text": "Description of the next major phase...",
                    "new_characters": {{ "Name": {{ "desc": "...", "status": "alive", "traits": "..." }} }},
                    "new_foreshadowing": ["Mystery of X"],
                    "resolved_foreshadowing": []
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
                text = opt.get("text", "")
                
                # Merge state
                new_summary = (node.state.get("summary") or "") + " -> " + text
                new_chars = node.state.get("characters", {}).copy()
                if "new_characters" in opt:
                    new_chars.update(opt["new_characters"])
                
                new_foreshadowing = node.state.get("foreshadowing", []).copy()
                if "new_foreshadowing" in opt:
                    # Simple list of dicts for state
                    for f in opt["new_foreshadowing"]:
                        new_foreshadowing.append({"description": f, "status": "unresolved"})
                        
                if "resolved_foreshadowing" in opt:
                    for r in opt["resolved_foreshadowing"]:
                        for f in new_foreshadowing:
                            if f['description'] == r:
                                f['status'] = 'resolved'

                new_state = {
                    "summary": new_summary,
                    "characters": new_chars,
                    "foreshadowing": new_foreshadowing
                }
                
                child = StoryNode(content=text, parent=node, state=new_state)
                node.children.append(child)
        except Exception as e:
            logger.error(f"Expansion failed: {e}")

    async def _simulate(self, node: StoryNode) -> float:
        prompt = f"""
        Critique this story arc for a bestseller.
        
        Arc: {node.content}
        Context: {node.state.get('summary')}
        
        Score 0.0-1.0 on:
        1. Originality
        2. Emotional Stakes
        3. Pacing
        
        Return JSON: {{ "score": 0.8 }}
        """
        response = await llm_service.generate_json(prompt)
        try:
            return float(json.loads(response).get("score", 0.5))
        except:
            return 0.5

class ChapterGenerator(MCTSBase):
    """Detailed generator for specific scenes/chapters."""
    
    async def _expand(self, node: StoryNode):
        memory_context = self.memory.get_state_summary()
        recent_events = self.memory.query_context(node.content)
        
        prompt = f"""
        You are a Scene Director. Plan the next scene in detail.
        
        Current Scene Context: {node.state.get('summary')}
        Last Action: {node.content}
        
        {memory_context}
        
        Relevant Past:
        {recent_events}
        
        Generate {self.branch_factor} options for the NEXT SCENE ACTION/BEAT.
        Focus on dialogue, sensory details, and immediate conflict.
        
        Return JSON:
        {{
            "options": [
                {{
                    "text": "Specific action or dialogue...",
                    "character_updates": {{ "Name": {{ "location": "...", "status": "..." }} }}
                }}
            ]
        }}
        """
        response = await llm_service.generate_json(prompt)
        try:
            data = json.loads(response)
            for opt in data.get("options", []):
                text = opt.get("text", "")
                
                # Update state lightly for scenes
                new_summary = (node.state.get("summary") or "") + "\n" + text
                new_chars = node.state.get("characters", {}).copy()
                if "character_updates" in opt:
                    for name, updates in opt["character_updates"].items():
                        if name in new_chars:
                            new_chars[name].update(updates)
                
                new_state = {
                    "summary": new_summary,
                    "characters": new_chars,
                    "foreshadowing": node.state.get("foreshadowing", [])
                }
                
                child = StoryNode(content=text, parent=node, state=new_state)
                node.children.append(child)
        except Exception as e:
            logger.error(f"Chapter expansion failed: {e}")

    async def _simulate(self, node: StoryNode) -> float:
        prompt = f"""
        Rate this scene beat for engagement and flow.
        
        Beat: {node.content}
        Context: {node.state.get('summary')}
        
        Score 0.0-1.0. Return JSON: {{ "score": 0.8 }}
        """
        response = await llm_service.generate_json(prompt)
        try:
            return float(json.loads(response).get("score", 0.5))
        except:
            return 0.5
