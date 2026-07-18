"""Task queue management module.

This module provides an in-memory task queue for managing long-running
asynchronous tasks such as storyboard generation, audio generation, and export.

Requirements: 3.3, 3.4, 3.5
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user


# Router
router = APIRouter()


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    """Represents an asynchronous task.
    
    Attributes:
        task_id: Unique identifier for the task.
        task_type: Type of task (e.g., "storyboard", "audio", "export").
        status: Current execution status.
        progress: Progress percentage (0-100).
        current: Current step number.
        total: Total number of steps.
        message: Human-readable status message.
        result: Task result when completed.
        error: Error message if task failed.
        created_at: Task creation timestamp.
        updated_at: Last update timestamp.
    """
    
    def __init__(self, task_id: str, task_type: str):
        """Initialize a new task.
        
        Args:
            task_id: Unique identifier for the task.
            task_type: Type of task being executed.
        """
        self.task_id = task_id
        self.task_type = task_type
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.current = 0
        self.total = 0
        self.message = ""
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = self.created_at
    
    def update_progress(
        self,
        message: str = "",
        current: int = 0,
        total: int = 0,
        progress: Optional[int] = None,
    ) -> None:
        """Update task progress.
        
        Args:
            message: Status message to display.
            current: Current step number.
            total: Total number of steps.
            progress: Progress percentage (calculated from current/total if not provided).
        """
        self.message = message
        self.current = current
        self.total = total
        if progress is not None:
            self.progress = progress
        elif total > 0:
            self.progress = int(current / total * 100)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> dict:
        """Convert task to dictionary representation.
        
        Returns:
            Dictionary with task information.
        """
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Global task storage (in-memory)
_tasks: Dict[str, Task] = {}


def create_task(task_type: str) -> Task:
    """Create a new task and add it to the task store.
    
    Args:
        task_type: Type of task being created.
        
    Returns:
        The newly created Task instance.
    """
    task_id = str(uuid.uuid4())
    task = Task(task_id, task_type)
    _tasks[task_id] = task
    return task


def get_task(task_id: str) -> Optional[Task]:
    """Get a task by ID.
    
    Args:
        task_id: The task ID to look up.
        
    Returns:
        The Task instance if found, None otherwise.
    """
    return _tasks.get(task_id)


def delete_task(task_id: str) -> bool:
    """Delete a task from the store.
    
    Args:
        task_id: The task ID to delete.
        
    Returns:
        True if task was deleted, False if not found.
    """
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def list_tasks() -> list[Task]:
    """List all tasks.
    
    Returns:
        List of all Task instances.
    """
    return list(_tasks.values())


def clear_tasks() -> None:
    """Clear all tasks from the store.
    
    Useful for testing.
    """
    _tasks.clear()


async def run_task(
    task: Task,
    coro: Coroutine[Any, Any, Any],
) -> None:
    """Execute a task asynchronously.
    
    This function runs the provided coroutine and updates the task status
    based on the result. The task status transitions from PENDING to RUNNING,
    then to either COMPLETED or FAILED.
    
    Args:
        task: The task to execute.
        coro: The coroutine to run.
    """
    print(f"[Task {task.task_id}] Starting execution")
    task.status = TaskStatus.RUNNING
    task.updated_at = datetime.utcnow().isoformat() + "Z"
    
    try:
        print(f"[Task {task.task_id}] Running coroutine")
        result = await coro
        print(f"[Task {task.task_id}] Completed successfully")
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.progress = 100
    except Exception as e:
        print(f"[Task {task.task_id}] Failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        task.status = TaskStatus.FAILED
        task.error = str(e)
    finally:
        task.updated_at = datetime.utcnow().isoformat() + "Z"
        print(f"[Task {task.task_id}] Final status: {task.status.value}")


def schedule_task(
    task: Task,
    coro: Coroutine[Any, Any, Any],
) -> None:
    """Schedule a task to run in the background.
    
    This function creates an asyncio task to run the coroutine without
    blocking the current execution.
    
    Args:
        task: The task to schedule.
        coro: The coroutine to run.
    """
    asyncio.create_task(run_task(task, coro))


# Response models
class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    task_type: str
    status: str
    progress: int = Field(ge=0, le=100)
    current: int = Field(ge=0)
    total: int = Field(ge=0)
    message: str
    error: Optional[str] = None
    created_at: str
    updated_at: str


# API Endpoints
@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: str = Depends(get_current_user),
) -> TaskStatusResponse:
    """Get task status by ID.
    
    Returns the current status and progress of an asynchronous task.
    
    Args:
        task_id: The task ID to query.
        current_user: The authenticated user.
        
    Returns:
        Task status information.
        
    Raises:
        HTTPException: If task not found.
    """
    task = get_task(task_id)
    
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task with ID {task_id} not found"},
        )
    
    return TaskStatusResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        status=task.status.value,
        progress=task.progress,
        current=task.current,
        total=task.total,
        message=task.message,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
