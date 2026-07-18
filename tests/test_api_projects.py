"""Tests for the project management API module.

This module tests project CRUD operations and property-based testing
for round-trip consistency.

**Property 2: 项目 CRUD Round-Trip**
**Validates: Requirements 3.1**
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, UserRecord, hash_password, get_db
from backend.api.main import app


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"


@pytest.fixture(scope="module")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Create a test database session with test user."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    
    # Create test user if not exists
    existing_user = session.query(UserRecord).filter(
        UserRecord.username == TEST_USERNAME
    ).first()
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
    
    yield session
    session.close()


@pytest.fixture(autouse=True)
def override_db(db_session):
    """Override the database dependency."""
    def get_test_db():
        yield db_session
    
    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()


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
def temp_storage_dir(monkeypatch):
    """Create a temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("STORAGE_BASE_DIR", tmpdir)
        yield tmpdir


class TestProjectListEndpoint:
    """Tests for the project list API endpoint."""
    
    def test_list_projects_empty(self, auth_headers, temp_storage_dir):
        """Test listing projects when none exist."""
        response = client.get("/api/projects", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
    
    def test_list_projects_unauthorized(self):
        """Test listing projects without authentication."""
        response = client.get("/api/projects")
        
        assert response.status_code == 401


class TestProjectCreateEndpoint:
    """Tests for the project creation API endpoint."""
    
    def test_create_project_success(self, auth_headers, temp_storage_dir):
        """Test successful project creation."""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "topic": "Python Programming Basics",
                "target_audience": "Beginners",
                "key_points": ["Variables", "Functions", "Loops"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "project_id" in data
        assert data["project_id"].startswith("proj_")
        assert data["status"] == "initialized"
    
    def test_create_project_minimal(self, auth_headers, temp_storage_dir):
        """Test project creation with minimal required fields."""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "project_id" in data
    
    def test_create_project_missing_topic(self, auth_headers, temp_storage_dir):
        """Test project creation fails without topic."""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "target_audience": "Test Audience"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_project_missing_audience(self, auth_headers, temp_storage_dir):
        """Test project creation fails without target audience."""
        response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "topic": "Test Topic"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_project_unauthorized(self, temp_storage_dir):
        """Test project creation without authentication."""
        response = client.post(
            "/api/projects",
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience"
            }
        )
        
        assert response.status_code == 401


class TestProjectGetEndpoint:
    """Tests for the project get API endpoint."""
    
    def test_get_project_success(self, auth_headers, temp_storage_dir):
        """Test getting a project that exists."""
        # First create a project
        create_response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience",
                "key_points": ["Point 1", "Point 2"]
            }
        )
        project_id = create_response.json()["project_id"]
        
        # Then get it
        response = client.get(f"/api/projects/{project_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["goal"]["topic"] == "Test Topic"
        assert data["goal"]["target_audience"] == "Test Audience"
        assert data["goal"]["key_points"] == ["Point 1", "Point 2"]
        assert data["status"] == "initialized"
    
    def test_get_project_not_found(self, auth_headers, temp_storage_dir):
        """Test getting a project that doesn't exist."""
        response = client.get("/api/projects/proj_nonexistent", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_get_project_unauthorized(self, temp_storage_dir):
        """Test getting a project without authentication."""
        response = client.get("/api/projects/proj_test")
        
        assert response.status_code == 401


class TestProjectDeleteEndpoint:
    """Tests for the project delete API endpoint."""
    
    def test_delete_project_success(self, auth_headers, temp_storage_dir):
        """Test deleting a project that exists."""
        # First create a project
        create_response = client.post(
            "/api/projects",
            headers=auth_headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience"
            }
        )
        project_id = create_response.json()["project_id"]
        
        # Then delete it
        response = client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify it's deleted
        get_response = client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_project_not_found(self, auth_headers, temp_storage_dir):
        """Test deleting a project that doesn't exist."""
        response = client.delete("/api/projects/proj_nonexistent", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_delete_project_unauthorized(self, temp_storage_dir):
        """Test deleting a project without authentication."""
        response = client.delete("/api/projects/proj_test")
        
        assert response.status_code == 401


class TestPropertyBasedProjects:
    """Property-based tests for project CRUD operations.
    
    **Feature: langchain-video-generator, Property 2: 项目 CRUD Round-Trip**
    **Validates: Requirements 3.1**
    """
    
    @given(
        topic=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        target_audience=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        key_points=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_project_crud_roundtrip_property(
        self, 
        topic: str, 
        target_audience: str, 
        key_points: list[str]
    ):
        """Property: For any valid project configuration, creating a project
        and then retrieving it should return the same data.
        
        *For any* 有效的项目配置，创建项目后通过 ID 获取的项目详情应与创建时的数据一致。
        
        **Feature: langchain-video-generator, Property 2: 项目 CRUD Round-Trip**
        **Validates: Requirements 3.1**
        """
        # Get auth token
        login_response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": topic,
                "target_audience": target_audience,
                "key_points": key_points
            }
        )
        
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Get project
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify round-trip consistency
        assert data["project_id"] == project_id
        assert data["goal"]["topic"] == topic
        assert data["goal"]["target_audience"] == target_audience
        assert data["goal"]["key_points"] == key_points
        assert data["status"] == "initialized"
        
        # Clean up - delete the project
        delete_response = client.delete(f"/api/projects/{project_id}", headers=headers)
        assert delete_response.status_code == 200
