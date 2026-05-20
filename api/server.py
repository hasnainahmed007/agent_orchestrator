"""REST API server for external integrations."""
import asyncio
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.settings import Config
from core.state_manager import StateManager
from core.cost_tracker import CostTracker
from core.rate_limiter import RateLimiter
from core.project_manager import ProjectManager


logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    """Task submission request."""
    description: str
    project_id: Optional[str] = None
    priority: str = "normal"
    require_approval: Optional[bool] = None


class TaskResponse(BaseModel):
    """Task response."""
    task_id: str
    status: str
    description: str
    created_at: str


class ProjectRequest(BaseModel):
    """Project creation request."""
    name: str
    path: str
    project_type: str = "laravel"
    main_branch: str = "main"
    daily_budget: float = 5.0


class APIKeyAuth:
    """Simple API key authentication."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def __call__(self, x_api_key: str = None):
        if not self.api_key:
            return True
        if not x_api_key or x_api_key != self.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True


class OrchestratorAPI:
    """FastAPI server for agent orchestrator."""
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.app = None
        self.api_key = Config.API_KEY
        if not self.api_key:
            import uuid
            self.api_key = uuid.uuid4().hex
        self.auth = APIKeyAuth(self.api_key)
        
    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("Starting Orchestrator API...")
            yield
            logger.info("Shutting down Orchestrator API...")
        
        self.app = FastAPI(
            title="Agent Orchestrator API",
            description="REST API for multi-agent Laravel development orchestration",
            version="1.0.0",
            lifespan=lifespan
        )
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        
        return self.app
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/")
        async def root():
            """API health check."""
            return {
                "name": "Agent Orchestrator API",
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}
        
        @self.app.post("/tasks", response_model=TaskResponse)
        async def create_task(request: TaskRequest, authenticated: bool = Depends(self.auth)):
            """Submit a new task."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")

            try:
                title = request.description.split('\n')[0][:50]
                task = await self.orchestrator.submit_task(
                    title=title,
                    description=request.description,
                    priority=getattr(request, 'priority', 'normal')
                )

                # Process in background
                asyncio.create_task(self.orchestrator.process_task_with_agent(task.task_id))

                return TaskResponse(
                    task_id=task.task_id,
                    status=task.status.value if hasattr(task.status, 'value') else str(task.status),
                    description=request.description,
                    created_at=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/tasks")
        async def list_tasks(status: Optional[str] = None, authenticated: bool = Depends(self.auth)):
            """List all tasks."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            tasks = self.orchestrator.state.list_tasks(status)
            
            return {
                "tasks": [
                    {
                        "id": task.id,
                        "description": task.description,
                        "status": task.status,
                        "branch": task.branch,
                        "created_at": task.created_at,
                        "completed_at": task.completed_at
                    }
                    for task in tasks
                ],
                "total": len(tasks)
            }
        
        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str, authenticated: bool = Depends(self.auth)):
            """Get task details."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            task = self.orchestrator.state.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status,
                "branch": task.branch,
                "subtasks": task.subtasks,
                "changes_summary": task.changes_summary[:1000],
                "error_message": task.error_message,
                "created_at": task.created_at,
                "completed_at": task.completed_at
            }
        
        @self.app.post("/tasks/{task_id}/approve")
        async def approve_task(task_id: str, authenticated: bool = Depends(self.auth)):
            """Approve and merge a task."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            success = await self.orchestrator.approve_task(task_id)
            
            if success:
                return {"status": "approved", "task_id": task_id}
            else:
                raise HTTPException(status_code=400, detail="Failed to approve task")
        
        @self.app.post("/tasks/{task_id}/reject")
        async def reject_task(task_id: str, authenticated: bool = Depends(self.auth)):
            """Reject and rollback a task."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            success = await self.orchestrator.reject_task(task_id)
            
            if success:
                return {"status": "rejected", "task_id": task_id}
            else:
                raise HTTPException(status_code=400, detail="Failed to reject task")
        
        @self.app.get("/status")
        async def get_status(authenticated: bool = Depends(self.auth)):
            """Get system status."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            stats = self.orchestrator.state.get_stats()
            
            return {
                "status": "running",
                "tasks": stats,
                "project": Config.PROJECT_NAME,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/projects")
        async def list_projects(authenticated: bool = Depends(self.auth)):
            """List all projects."""
            project_manager = ProjectManager(Config.STATE_FILE.parent)
            projects = project_manager.list_projects()
            
            return {
                "projects": [
                    {
                        "project_id": p.project_id,
                        "name": p.name,
                        "path": p.path,
                        "enabled": p.enabled,
                        "active": p.project_id == project_manager.active_project_id
                    }
                    for p in projects
                ],
                "total": len(projects)
            }
        
        @self.app.post("/projects")
        async def create_project(request: ProjectRequest, authenticated: bool = Depends(self.auth)):
            """Add a new project."""
            from core.project_manager import ProjectConfig
            
            project_manager = ProjectManager(Config.STATE_FILE.parent)
            
            project_id = request.name.lower().replace(" ", "-")
            config = ProjectConfig(
                project_id=project_id,
                name=request.name,
                path=request.path,
                project_type=request.project_type,
                main_branch=request.main_branch,
                daily_budget=request.daily_budget
            )
            
            try:
                project_manager.add_project(config)
                return {"status": "created", "project_id": project_id}
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/costs")
        async def get_costs(days: int = 7, authenticated: bool = Depends(self.auth)):
            """Get cost tracking data."""
            cost_tracker = CostTracker(Config.STATE_FILE.parent, Config.DAILY_BUDGET_LIMIT)
            summary = cost_tracker.get_usage_summary(days)
            
            return {
                "period_days": days,
                "total_cost": summary["total_cost"],
                "total_requests": summary["total_requests"],
                "total_tokens": summary["total_tokens"],
                "daily_breakdown": summary["daily_breakdown"],
                "remaining_budget": cost_tracker.get_remaining_budget()
            }
        
        @self.app.get("/logs")
        async def get_logs(count: int = 50, authenticated: bool = Depends(self.auth)):
            """Get recent activity logs."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not initialized")
            
            activities = self.orchestrator.state.get_recent_activities(count)
            
            return {
                "activities": activities,
                "total": len(activities)
            }
        
        @self.app.get("/rate-limits")
        async def get_rate_limits(authenticated: bool = Depends(self.auth)):
            """Get rate limit status."""
            rate_limiter = RateLimiter(Config.STATE_FILE.parent)
            return rate_limiter.get_status()
        
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            """Global exception handler."""
            logger.error(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc)}
            )
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server."""
        import uvicorn
        
        if not self.app:
            self.create_app()
        
        uvicorn.run(self.app, host=host, port=port)
