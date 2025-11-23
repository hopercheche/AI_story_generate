from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from app.agents.mcts import StoryPlanner, ChapterGenerator
from app.agents.researcher import researcher
from app.agents.memory import MemoryManager
from app.core.llm import llm_service
from app.core.project_manager import project_manager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Story Generator API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateProjectRequest(BaseModel):
    name: str
    genre: str
    description: str

class GenerateRequest(BaseModel):
    project_id: str
    prompt: str
    mode: str = "plan" # 'plan' or 'chapter'
    iterations: int = 5
    use_research: bool = False

@app.get("/")
async def root():
    return {"message": "AI Story Generator API is running"}

# Project Management Endpoints
@app.post("/api/projects")
async def create_project(request: CreateProjectRequest):
    return project_manager.create_project(request.name, request.genre, request.description)

@app.get("/api/projects")
async def list_projects():
    return project_manager.list_projects()

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.post("/api/generate")
async def generate_story(request: GenerateRequest):
    try:
        project = project_manager.get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        memory = MemoryManager(project_id=request.project_id)
        
        research_context = ""
        if request.use_research:
            logger.info("Performing research...")
            research_result = await researcher.search_and_extract(request.prompt)
            if research_result.get("status") == "success":
                research_context = f"\nResearch Context: {research_result.get('data')}\n"
                memory.add_event(f"Research Findings: {research_result.get('data')}")

        initial_state = memory.world_state
        
        if request.mode == "plan":
            generator = StoryPlanner(memory_manager=memory, max_iterations=request.iterations)
            sequence = await generator.run_search(initial_state, request.prompt + research_context)
        else:
            generator = ChapterGenerator(memory_manager=memory, max_iterations=request.iterations)
            sequence = await generator.run_search(initial_state, request.prompt + research_context)
            
        # Generate full text from the sequence
        full_text = ""
        if sequence:
            writing_prompt = f"""
            Write the content based on these plot points:
            {json.dumps(sequence)}
            
            Genre: {project['genre']}
            Style: Best-selling novel, immersive, show don't tell.
            """
            full_text = await llm_service.generate(writing_prompt)
            
            # Save to memory as a completed event
            memory.add_event(full_text, metadata={"type": "chapter_content"})

        return {
            "sequence": sequence,
            "content": full_text,
            "research": research_context
        }

    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/memory")
async def get_memory_state(project_id: str):
    memory = MemoryManager(project_id=project_id)
    return memory.world_state
