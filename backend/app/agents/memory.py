import chromadb
from chromadb.config import Settings
import json
import logging
from typing import List, Dict, Any, Optional
import uuid
import os
import shutil

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, project_id: str, persist_dir: str = "./data/memories"):
        self.project_id = project_id
        self.persist_dir = os.path.join(persist_dir, project_id)
        
        # Ensure directory exists
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=os.path.join(self.persist_dir, "chroma"))
        
        self.collection = self.client.get_or_create_collection(name=f"story_{project_id}")
        
        # Structured World State
        self.world_state = {
            "characters": {},  # {name: {desc, status, location, relations, traits, arc}}
            "items": {},       # {name: {desc, owner, location, status}}
            "locations": {},   # {name: {desc, visited, atmosphere}}
            "foreshadowing": [], # List of {id, description, status, created_at_step}
            "plot_points": [], # Chronological list of major events
            "current_step": 0,
            "summary": ""
        }
        
        self.load_state()

    def add_event(self, text: str, metadata: Dict[str, Any] = None):
        """Adds a story event to vector memory and updates state."""
        if metadata is None:
            metadata = {}
        
        metadata["step"] = self.world_state["current_step"]
        metadata["type"] = "event"
        
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
        
        # Update running summary and step
        self.world_state["plot_points"].append({
            "step": self.world_state["current_step"],
            "text": text,
            "metadata": metadata
        })
        self.world_state["current_step"] += 1
        self.save_state()

    def query_context(self, query: str, n_results: int = 5) -> str:
        """Retrieves relevant past events based on semantic similarity."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            if results and results['documents']:
                docs = [doc for sublist in results['documents'] for doc in sublist]
                return "\n".join(docs)
            return ""
        except Exception as e:
            logger.error(f"Memory query failed: {e}")
            return ""

    def update_world_state(self, updates: Dict[str, Any]):
        """
        Updates the structured world state.
        Expected keys: 'characters', 'items', 'locations', 'foreshadowing', 'summary'
        """
        for category in ['characters', 'items', 'locations']:
            if category in updates:
                for name, details in updates[category].items():
                    if name not in self.world_state[category]:
                        self.world_state[category][name] = {}
                    # Deep merge could be better, but simple update for now
                    self.world_state[category][name].update(details)
        
        if 'foreshadowing' in updates:
            for item in updates['foreshadowing']:
                # Handle item being a dict (from MCTS state) or string (from simple updates)
                description = item['description'] if isinstance(item, dict) else item
                
                # Check if already exists to avoid duplicates
                exists = any(f['description'] == description for f in self.world_state['foreshadowing'] if isinstance(f, dict))
                if not exists:
                     new_item = {
                        "id": str(uuid.uuid4()),
                        "description": description,
                        "status": "unresolved",
                        "created_at_step": self.world_state["current_step"]
                    }
                     # If item was a dict, it might have other properties we want to keep? 
                     # For now, just ensuring description is correct is enough to fix the crash.
                     self.world_state['foreshadowing'].append(new_item)
            
        if 'resolved_foreshadowing' in updates:
            for resolved in updates['resolved_foreshadowing']:
                for f in self.world_state['foreshadowing']:
                    if f['description'] == resolved:
                        f['status'] = 'resolved'
                        f['resolved_at_step'] = self.world_state["current_step"]

        if 'summary' in updates:
            self.world_state['summary'] = updates['summary']
            
        self.save_state()

    def get_state_summary(self) -> str:
        """Returns a string representation of the current world state for LLM context."""
        state_str = "Current World State:\n"
        
        if self.world_state['characters']:
            state_str += "Characters:\n"
            for name, info in self.world_state['characters'].items():
                # Format nicely for LLM
                traits = info.get('traits', 'N/A')
                status = info.get('status', 'Unknown')
                state_str += f"  - {name} ({status}): {info.get('desc', '')} [Traits: {traits}]\n"
                
        if self.world_state['locations']:
            state_str += "Locations:\n"
            for name, info in self.world_state['locations'].items():
                state_str += f"  - {name}: {info.get('desc', '')}\n"

        unresolved = [f for f in self.world_state['foreshadowing'] if f['status'] == 'unresolved']
        if unresolved:
            state_str += "Unresolved Mysteries/Foreshadowing:\n"
            for item in unresolved:
                state_str += f"  - {item['description']}\n"
                
        return state_str

    def save_state(self):
        """Persists the JSON world state to disk."""
        try:
            with open(os.path.join(self.persist_dir, "world_state.json"), "w") as f:
                json.dump(self.world_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save world state: {e}")

    def load_state(self):
        """Loads the JSON world state from disk."""
        path = os.path.join(self.persist_dir, "world_state.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.world_state = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load world state: {e}")

    def clear(self):
        """Clears memory for this project."""
        try:
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.get_or_create_collection(self.collection.name)
            self.world_state = {
                "characters": {},
                "items": {},
                "locations": {},
                "foreshadowing": [],
                "plot_points": [],
                "current_step": 0,
                "summary": ""
            }
            self.save_state()
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
