"""Tests for the storyboard API module.

This module tests storyboard generation, scene listing, scene editing,
and image regeneration endpoints.

Requirements: 3.3

Note: These tests have been simplified after the database refactoring.
The API now uses database storage instead of file-based storage.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, UserRecord, ProjectRecord, SceneRecord, hash_password, get_db
from backend.api.main import app
from backend.services.tasks import clear_tasks, get_task, TaskStatus
from backend.db.crud.projects import create_project, create_scene


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"

# Global test database session
_test_engine = None
_test_session = None


def get_test_db():
    """Create a test database session."""
    global _test_engine, _test_session
    
    if _test_engine is None:
        _test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(_test_engine)
    
    SessionLocal = sessionmaker(bind=_test_engine)
    session = SessionLocal()
    
    # Create test user if not exists
    existing_user = session.query(UserRecord).filter(UserRecord.username == TEST_USERNAME).first()
    if not existing_user:
        test_user = UserRecord(
            username=TEST_USERNAME,
            password_hash=hash_password(TEST_PASSWORD),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        session.add(test_user)
        session.commit()
    
    try:
        yield session
    finally:
        session.close()


# Apply override
app.dependency_overrides[get_db] = get_test_db

# Test client
client = TestClient(app)


@pytest.fixture
def auth_token():
    """Get authentication token for API requests."""
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_project(auth_headers):
    """Create a sample project for testing."""
    response = client.post(
        "/api/projects",
        headers=auth_headers,
        json={
            "topic": "Python Programming Basics",
            "target_audience": "Beginners",
            "key_points": ["Variables", "Functions"]
        }
    )
    return response.json()["project_id"]


@pytest.fixture(autouse=True)
def cleanup_tasks():
    """Clean up tasks before and after each test."""
    clear_tasks()
    yield
    clear_tasks()


class TestGenerateStoryboardEndpoint:
    """Tests for the storyboard generation endpoint."""
    
    def test_generate_storyboard_returns_task_id(self, auth_headers, sample_project):
        """Test that storyboard generation returns a task ID."""
        response = client.post(
            f"/api/projects/{sample_project}/storyboard/generate",
            headers=auth_headers,
            json={"duration": "10"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0
    
    def test_generate_storyboard_creates_task(self, auth_headers, sample_project):
        """Test that storyboard generation creates a task."""
        response = client.post(
            f"/api/projects/{sample_project}/storyboard/generate",
            headers=auth_headers,
            json={"duration": "10"}
        )
        
        task_id = response.json()["task_id"]
        task = get_task(task_id)
        
        assert task is not None
        assert task.task_type == "storyboard"
    
    def test_generate_storyboard_project_not_found(self, auth_headers):
        """Test storyboard generation with non-existent project."""
        response = client.post(
            "/api/projects/proj_nonexistent/storyboard/generate",
            headers=auth_headers,
            json={"duration": "10"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_generate_storyboard_unauthorized(self, sample_project):
        """Test storyboard generation without authentication."""
        response = client.post(
            f"/api/projects/{sample_project}/storyboard/generate",
            json={"duration": "10"}
        )
        
        assert response.status_code == 401


class TestGetScenesEndpoint:
    """Tests for the scenes list endpoint."""
    
    def test_get_scenes_empty(self, auth_headers, sample_project):
        """Test getting scenes when no storyboard exists."""
        response = client.get(
            f"/api/projects/{sample_project}/scenes",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "scenes" in data
        assert data["scenes"] == []
    
    def test_get_scenes_project_not_found(self, auth_headers):
        """Test getting scenes for non-existent project."""
        response = client.get(
            "/api/projects/proj_nonexistent/scenes",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_get_scenes_unauthorized(self, sample_project):
        """Test getting scenes without authentication."""
        response = client.get(f"/api/projects/{sample_project}/scenes")
        
        assert response.status_code == 401


class TestUpdateSceneEndpoint:
    """Tests for the scene update endpoint."""
    
    def test_update_scene_project_not_found(self, auth_headers):
        """Test updating scene for non-existent project."""
        response = client.put(
            "/api/projects/proj_nonexistent/scenes/scene_001",
            headers=auth_headers,
            json={"description_cn": "Test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_update_scene_not_found(self, auth_headers, sample_project):
        """Test updating non-existent scene."""
        response = client.put(
            f"/api/projects/{sample_project}/scenes/scene_999",
            headers=auth_headers,
            json={"description_cn": "Test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "SCENE_NOT_FOUND"


class TestRegenerateImageEndpoint:
    """Tests for the image regeneration endpoint."""
    
    def test_regenerate_image_project_not_found(self, auth_headers):
        """Test image regeneration for non-existent project."""
        response = client.post(
            "/api/projects/proj_nonexistent/scenes/scene_001/regenerate-image",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_regenerate_image_scene_not_found(self, auth_headers, sample_project):
        """Test image regeneration for non-existent scene."""
        response = client.post(
            f"/api/projects/{sample_project}/scenes/scene_999/regenerate-image",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "SCENE_NOT_FOUND"
    
    def test_regenerate_image_unauthorized(self, sample_project):
        """Test image regeneration without authentication."""
        response = client.post(
            f"/api/projects/{sample_project}/scenes/scene_001/regenerate-image"
        )
        
        assert response.status_code == 401
