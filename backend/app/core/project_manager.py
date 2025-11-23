import os
import json
import uuid
from typing import List, Dict, Optional
from app.agents.memory import MemoryManager

PROJECTS_DIR = "./data/projects"

class ProjectManager:
    def __init__(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)

    def create_project(self, name: str, genre: str, description: str) -> Dict:
        project_id = str(uuid.uuid4())
        project_data = {
            "id": project_id,
            "name": name,
            "genre": genre,
            "description": description,
            "created_at": str(uuid.uuid1()), # Simple timestamp
            "status": "active"
        }
        
        self._save_project_meta(project_id, project_data)
        
        # Initialize memory for this project
        MemoryManager(project_id=project_id)
        
        return project_data

    def list_projects(self) -> List[Dict]:
        projects = []
        for filename in os.listdir(PROJECTS_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(PROJECTS_DIR, filename), "r") as f:
                        projects.append(json.load(f))
                except:
                    continue
        return projects

    def get_project(self, project_id: str) -> Optional[Dict]:
        path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None
        
    def delete_project(self, project_id: str):
        path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
        if os.path.exists(path):
            os.remove(path)
            # TODO: Cleanup memory directory as well

    def _save_project_meta(self, project_id: str, data: Dict):
        with open(os.path.join(PROJECTS_DIR, f"{project_id}.json"), "w") as f:
            json.dump(data, f, indent=2)

project_manager = ProjectManager()
