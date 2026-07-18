"""FastAPI application entry point.

This module creates and configures the FastAPI application with CORS,
routes, and static file serving.

Requirements: 2.1, 6
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes.auth import router as auth_router
from backend.api.routes.projects import router as projects_router
from backend.api.routes.characters import router as characters_router
from backend.api.routes.characters import project_characters_router
from backend.services.tasks import router as tasks_router
from backend.api.routes.storyboard import router as storyboard_router
from backend.api.routes.audio import router as voices_router
from backend.api.routes.audio import project_audio_router
from backend.api.routes.export import router as export_router
from backend.api.routes.tts import router as tts_router
from backend.api.routes.styles import router as styles_router
from backend.api.routes.emotions import router as emotions_router
from backend.api.errors import register_exception_handlers


# Directory paths
projects_dir = Path(os.getenv("STORAGE_BASE_DIR", "./projects"))
character_library_dir = Path("./character_library")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler."""
    # Startup: Ensure directories exist
    projects_dir.mkdir(parents=True, exist_ok=True)
    character_library_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown: cleanup if needed
    pass


# Create FastAPI application
app = FastAPI(
    title="Video Generator API",
    description="教学视频素材生成器 REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# Register exception handlers for unified error responses
register_exception_handlers(app)

# CORS configuration - allow frontend cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(characters_router, prefix="/api/characters", tags=["characters"])
app.include_router(project_characters_router, prefix="/api/projects", tags=["project-characters"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(storyboard_router, prefix="/api/projects", tags=["storyboard"])
app.include_router(voices_router, prefix="/api/voices", tags=["voices"])
app.include_router(project_audio_router, prefix="/api/projects", tags=["audio"])
app.include_router(export_router, prefix="/api/projects", tags=["export"])
app.include_router(tts_router, prefix="/api", tags=["tts"])
app.include_router(styles_router, prefix="/api", tags=["styles"])
app.include_router(emotions_router, prefix="/api", tags=["emotions"])


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Mount static files for project resources
# Projects directory for images, audios, etc.
if projects_dir.exists():
    app.mount(
        "/api/static/projects",
        StaticFiles(directory=str(projects_dir)),
        name="projects_static"
    )

# Character library directory
if character_library_dir.exists():
    app.mount(
        "/api/static/characters",
        StaticFiles(directory=str(character_library_dir)),
        name="characters_static"
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "video-generator-api"}
