"""Tests for the task queue management API module.

This module tests task creation, status retrieval, and state transitions.

**Property 5: 任务状态流转**
**Validates: Requirements 3.3, 3.4, 3.5**
"""

import asyncio
import os
import tempfile

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services.tasks import (
    Task,
    TaskStatus,
    create_task,
    get_task,
    delete_task,
    list_tasks,
    clear_tasks,
    run_task,
    schedule_task,
)


# Test client
client = TestClient(app)


@pytest.fixture
def auth_token():
    """Get authentication token for API requests."""
    response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def clean_tasks():
    """Clean up tasks before and after each test."""
    clear_tasks()
    yield
    clear_tasks()


class TestTaskClass:
    """Tests for the Task class."""
    
    def test_task_initialization(self):
        """Test task is initialized with correct default values."""
        task = Task("test-id", "storyboard")
        
        assert task.task_id == "test-id"
        assert task.task_type == "storyboard"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        assert task.current == 0
        assert task.total == 0
        assert task.message == ""
        assert task.result is None
        assert task.error is None
        assert task.created_at is not None
        assert task.updated_at is not None
    
    def test_task_update_progress(self):
        """Test task progress update."""
        task = Task("test-id", "audio")
        
        task.update_progress(message="Processing", current=5, total=10)
        
        assert task.message == "Processing"
        assert task.current == 5
        assert task.total == 10
        assert task.progress == 50
    
    def test_task_update_progress_explicit(self):
        """Test task progress update with explicit progress value."""
        task = Task("test-id", "export")
        
        task.update_progress(message="Exporting", progress=75)
        
        assert task.message == "Exporting"
        assert task.progress == 75
    
    def test_task_to_dict(self):
        """Test task serialization to dictionary."""
        task = Task("test-id", "storyboard")
        task.update_progress(message="Running", current=3, total=10)
        
        data = task.to_dict()
        
        assert data["task_id"] == "test-id"
        assert data["task_type"] == "storyboard"
        assert data["status"] == "pending"
        assert data["progress"] == 30
        assert data["current"] == 3
        assert data["total"] == 10
        assert data["message"] == "Running"
        assert data["error"] is None


class TestTaskStorage:
    """Tests for task storage functions."""
    
    def test_create_task(self):
        """Test task creation."""
        task = create_task("storyboard")
        
        assert task.task_id is not None
        assert task.task_type == "storyboard"
        assert task.status == TaskStatus.PENDING
    
    def test_get_task_exists(self):
        """Test getting an existing task."""
        created = create_task("audio")
        
        retrieved = get_task(created.task_id)
        
        assert retrieved is not None
        assert retrieved.task_id == created.task_id
        assert retrieved.task_type == "audio"
    
    def test_get_task_not_exists(self):
        """Test getting a non-existent task."""
        result = get_task("nonexistent-id")
        
        assert result is None
    
    def test_delete_task_exists(self):
        """Test deleting an existing task."""
        task = create_task("export")
        
        result = delete_task(task.task_id)
        
        assert result is True
        assert get_task(task.task_id) is None
    
    def test_delete_task_not_exists(self):
        """Test deleting a non-existent task."""
        result = delete_task("nonexistent-id")
        
        assert result is False
    
    def test_list_tasks(self):
        """Test listing all tasks."""
        task1 = create_task("storyboard")
        task2 = create_task("audio")
        task3 = create_task("export")
        
        tasks = list_tasks()
        
        assert len(tasks) == 3
        task_ids = [t.task_id for t in tasks]
        assert task1.task_id in task_ids
        assert task2.task_id in task_ids
        assert task3.task_id in task_ids
    
    def test_clear_tasks(self):
        """Test clearing all tasks."""
        create_task("storyboard")
        create_task("audio")
        
        clear_tasks()
        
        assert len(list_tasks()) == 0


class TestTaskExecution:
    """Tests for task execution functions."""
    
    @pytest.mark.asyncio
    async def test_run_task_success(self):
        """Test successful task execution."""
        task = create_task("test")
        
        async def successful_coro():
            return {"result": "success"}
        
        await run_task(task, successful_coro())
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"result": "success"}
        assert task.error is None
        assert task.progress == 100
    
    @pytest.mark.asyncio
    async def test_run_task_failure(self):
        """Test failed task execution."""
        task = create_task("test")
        
        async def failing_coro():
            raise ValueError("Test error")
        
        await run_task(task, failing_coro())
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error"
        assert task.result is None
    
    @pytest.mark.asyncio
    async def test_task_status_transitions(self):
        """Test task status transitions during execution.
        
        Verifies that task status follows: PENDING -> RUNNING -> COMPLETED/FAILED
        """
        task = create_task("test")
        assert task.status == TaskStatus.PENDING
        
        status_history = []
        
        async def tracking_coro():
            # Record status when coroutine starts
            status_history.append(task.status)
            await asyncio.sleep(0.01)
            return "done"
        
        await run_task(task, tracking_coro())
        
        # Status should have been RUNNING when coroutine executed
        assert TaskStatus.RUNNING in status_history
        # Final status should be COMPLETED
        assert task.status == TaskStatus.COMPLETED


class TestTaskAPIEndpoint:
    """Tests for the task status API endpoint."""
    
    def test_get_task_status_success(self, auth_headers):
        """Test getting task status for existing task."""
        task = create_task("storyboard")
        task.update_progress(message="Processing", current=5, total=10)
        
        response = client.get(f"/api/tasks/{task.task_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task.task_id
        assert data["task_type"] == "storyboard"
        assert data["status"] == "pending"
        assert data["progress"] == 50
        assert data["current"] == 5
        assert data["total"] == 10
        assert data["message"] == "Processing"
    
    def test_get_task_status_not_found(self, auth_headers):
        """Test getting task status for non-existent task."""
        response = client.get("/api/tasks/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "TASK_NOT_FOUND"
    
    def test_get_task_status_unauthorized(self):
        """Test getting task status without authentication."""
        task = create_task("test")
        
        response = client.get(f"/api/tasks/{task.task_id}")
        
        assert response.status_code == 401
    
    def test_get_task_status_completed(self, auth_headers):
        """Test getting status of a completed task."""
        task = create_task("export")
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.result = {"file": "export.zip"}
        
        response = client.get(f"/api/tasks/{task.task_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
    
    def test_get_task_status_failed(self, auth_headers):
        """Test getting status of a failed task."""
        task = create_task("audio")
        task.status = TaskStatus.FAILED
        task.error = "Generation failed"
        
        response = client.get(f"/api/tasks/{task.task_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Generation failed"



class TestPropertyBasedTasks:
    """Property-based tests for task status transitions.
    
    **Feature: langchain-video-generator, Property 5: 任务状态流转**
    **Validates: Requirements 3.3, 3.4, 3.5**
    """
    
    @pytest.mark.asyncio
    @given(
        task_type=st.sampled_from(["storyboard", "audio", "export"]),
        should_succeed=st.booleans(),
        progress_updates=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50),  # message
                st.integers(min_value=0, max_value=100),  # current
                st.integers(min_value=1, max_value=100),  # total
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=100)
    async def test_task_status_flow_property(
        self,
        task_type: str,
        should_succeed: bool,
        progress_updates: list[tuple[str, int, int]],
    ):
        """Property: For any async task, status should flow in order:
        pending -> running -> completed/failed, with no reverse transitions.
        
        *For any* 异步任务，状态应按 pending → running → completed/failed 顺序流转，
        不应出现逆向流转。
        
        **Feature: langchain-video-generator, Property 5: 任务状态流转**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Clear tasks before each test
        clear_tasks()
        
        # Create task
        task = create_task(task_type)
        
        # Track status history
        status_history = [task.status]
        
        # Define valid status transitions
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.RUNNING},
            TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
            TaskStatus.COMPLETED: set(),  # Terminal state
            TaskStatus.FAILED: set(),  # Terminal state
        }
        
        async def test_coro():
            # Record status when coroutine starts (should be RUNNING)
            status_history.append(task.status)
            
            # Apply progress updates
            for message, current, total in progress_updates:
                # Ensure current doesn't exceed total
                actual_current = min(current, total)
                task.update_progress(message=message, current=actual_current, total=total)
                await asyncio.sleep(0.001)
            
            if not should_succeed:
                raise ValueError("Simulated failure")
            
            return {"success": True}
        
        # Run the task
        await run_task(task, test_coro())
        
        # Record final status
        status_history.append(task.status)
        
        # Verify status transitions are valid
        for i in range(len(status_history) - 1):
            current_status = status_history[i]
            next_status = status_history[i + 1]
            
            # Same status is allowed (no transition)
            if current_status == next_status:
                continue
            
            # Verify transition is valid
            assert next_status in valid_transitions[current_status], (
                f"Invalid status transition: {current_status} -> {next_status}. "
                f"Valid transitions from {current_status}: {valid_transitions[current_status]}"
            )
        
        # Verify final state
        if should_succeed:
            assert task.status == TaskStatus.COMPLETED
            assert task.error is None
            assert task.progress == 100
        else:
            assert task.status == TaskStatus.FAILED
            assert task.error is not None
        
        # Verify no reverse transitions occurred
        status_order = {
            TaskStatus.PENDING: 0,
            TaskStatus.RUNNING: 1,
            TaskStatus.COMPLETED: 2,
            TaskStatus.FAILED: 2,
        }
        
        for i in range(len(status_history) - 1):
            current_order = status_order[status_history[i]]
            next_order = status_order[status_history[i + 1]]
            assert next_order >= current_order, (
                f"Reverse status transition detected: {status_history[i]} -> {status_history[i + 1]}"
            )
