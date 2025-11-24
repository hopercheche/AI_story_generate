from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from app.agents.mcts import StoryPlanner
from app.agents.writer import LinearWriter
from app.agents.memory import MemoryManager
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

# --- Request Models ---
class CreateProjectRequest(BaseModel):
    name: str
    genre: str
    description: str
    language: str = "Chinese"

class PlanRequest(BaseModel):
    project_id: str
    premise: str = ""
    feedback: str = ""
    current_state: Optional[Dict] = None

class ChapterRequest(BaseModel):
    project_id: str
    chapter_index: int
    feedback: str = ""
    current_content: str = ""

# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "AI Story Generator API is running"}

# Project Management
@app.post("/api/projects")
async def create_project(request: CreateProjectRequest):
    return project_manager.create_project(request.name, request.genre, request.description, request.language)

@app.get("/api/projects")
async def list_projects():
    return project_manager.list_projects()

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    project_manager.delete_project(project_id)
    return {"status": "success"}

@app.get("/api/projects/{project_id}/memory")
async def get_memory_state(project_id: str):
    memory = MemoryManager(project_id=project_id)
    return memory.world_state

# --- Planning Phase (MCTS) ---

@app.post("/api/plan/generate")
async def generate_plan(request: PlanRequest):
    """Generates initial Story Bible using MCTS."""
    project = project_manager.get_project(request.project_id)
    memory = MemoryManager(project_id=request.project_id)
    planner = StoryPlanner(memory_manager=memory)
    
    # Use premise from request or project description
    premise = request.premise or project['description']
    
    plan = await planner.run_search(
        initial_state=memory.world_state, 
        prompt=premise,
        language=project.get('language', 'Chinese')
    )
    return plan

@app.post("/api/plan/refine")
async def refine_plan(request: PlanRequest):
    """Refines the plan based on user feedback."""
    project = project_manager.get_project(request.project_id)
    memory = MemoryManager(project_id=request.project_id)
    planner = StoryPlanner(memory_manager=memory)
    
    if not request.current_state:
        raise HTTPException(status_code=400, detail="Current state required for refinement")
        
    refined_plan = await planner.refine_plan(
        current_state=request.current_state,
        feedback=request.feedback,
        language=project.get('language', 'Chinese')
    )
    return refined_plan

@app.post("/api/plan/confirm")
async def confirm_plan(request: PlanRequest):
    """Saves the confirmed plan to memory and updates project status."""
    if not request.current_state:
        raise HTTPException(status_code=400, detail="Plan state required")
        
    memory = MemoryManager(project_id=request.project_id)
    
    # Save World Setting to Memory
    memory.update_world_state(request.current_state['world_setting'])
    
    # Save Outline and Chapter List as special events/metadata
    memory.add_event("Story Plan Confirmed", metadata={
        "type": "plan_confirmed",
        "outline": request.current_state['outline'],
        "chapter_list": request.current_state['chapter_list']
    })
    
    # Update project status to 'writing'
    project = project_manager.get_project(request.project_id)
    project['status'] = 'writing'
    project['chapter_list'] = request.current_state['chapter_list']
    project_manager._save_project_meta(request.project_id, project)
    
    return {"status": "success"}

# --- Writing Phase (Linear) ---

@app.post("/api/chapter/generate")
async def generate_chapter(request: ChapterRequest):
    """Generates a chapter using Linear Writer."""
    project = project_manager.get_project(request.project_id)
    memory = MemoryManager(project_id=request.project_id)
    writer = LinearWriter(memory_manager=memory)
    
    chapters = project.get('chapter_list', [])
    if request.chapter_index >= len(chapters):
        raise HTTPException(status_code=404, detail="Chapter index out of range")
        
    chapter_info = chapters[request.chapter_index]
    
    # Get previous summary
    prev_summary = memory.world_state.get('summary', 'Start of story.')
    
    content = await writer.write_chapter(
        chapter_title=chapter_info['title'],
        chapter_summary=chapter_info['summary'],
        world_setting=memory.world_state,
        previous_summary=prev_summary,
        language=project.get('language', 'Chinese')
    )
    
    return {"content": content}

@app.post("/api/chapter/refine")
async def refine_chapter(request: ChapterRequest):
    """Rewrites a chapter based on feedback."""
    project = project_manager.get_project(request.project_id)
    memory = MemoryManager(project_id=request.project_id)
    writer = LinearWriter(memory_manager=memory)
    
    content = await writer.rewrite_chapter(
        current_content=request.current_content,
        feedback=request.feedback,
        world_setting=memory.world_state,
        language=project.get('language', 'Chinese')
    )
    
    return {"content": content}

@app.post("/api/chapter/approve")
async def approve_chapter(request: ChapterRequest):
    """Saves approved chapter to memory."""
    memory = MemoryManager(project_id=request.project_id)
    project = project_manager.get_project(request.project_id)
    
    chapters = project.get('chapter_list', [])
    chapter_title = chapters[request.chapter_index]['title']
    
    # Add to memory
    memory.add_event(request.current_content, metadata={
        "type": "chapter_content",
        "title": chapter_title,
        "index": request.chapter_index
    })
    
    # Update summary (simple append for now, could be LLM summarized)
    current_summary = memory.world_state.get('summary', '')
    new_summary = current_summary + f"\n[Chapter {request.chapter_index + 1}]: {chapter_title} happened."
    memory.update_world_state({"summary": new_summary})
    
    return {"status": "success"}

# --- Export ---

@app.get("/api/export/{project_id}")
async def export_book(project_id: str):
    """Compiles all approved chapters into a file."""
    memory = MemoryManager(project_id=project_id)
    
    # Fetch all chapter events
    # Note: In a real app, we might query by type. For now, we'll just scan plot_points
    # A better way would be to store chapters in a separate list in project meta or memory
    
    # Re-querying from Chroma or using plot_points if they store full text?
    # memory.add_event stores in plot_points too.
    
    full_text = f"# Story Export\n\n"
    
    for point in memory.world_state['plot_points']:
        if point['metadata'].get('type') == 'chapter_content':
            title = point['metadata'].get('title', 'Chapter')
            full_text += f"## {title}\n\n{point['text']}\n\n"
            
    return Response(content=full_text, media_type="text/plain", headers={
        "Content-Disposition": f"attachment; filename=story_{project_id}.txt"
    })
