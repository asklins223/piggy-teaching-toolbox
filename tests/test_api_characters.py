"""Tests for the character management API module.

This module tests character library operations and project character management.

**Property 3: 角色库一致性**
**Validates: Requirements 3.2**

Note: These tests have been simplified after the database refactoring.
The API now uses database storage instead of file-based storage.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import (
    Base, UserRecord, CharacterRecord, hash_password, get_db
)
from backend.api.main import app


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"

# Global test database
_test_engine = None


def get_test_db():
    """Create a test database session."""
    global _test_engine
    
    if _test_engine is None:
        _test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(_test_engine)
    
    SessionLocal = sessionmaker(bind=_test_engine)
    session = SessionLocal()
    
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
    
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = get_test_db
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
            "topic": "Test Topic",
            "target_audience": "Test Audience"
        }
    )
    return response.json()["project_id"]


class TestCharacterLibraryEndpoint:
    """Tests for the character library list API endpoint."""
    
    def test_get_library_returns_list(self, auth_headers):
        """Test getting character library returns a list."""
        response = client.get("/api/characters/library", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert isinstance(data["characters"], list)
    
    def test_get_library_unauthorized(self):
        """Test getting character library without authentication."""
        response = client.get("/api/characters/library")
        assert response.status_code == 401


class TestRandomTemplateEndpoint:
    """Tests for the random character template API endpoint."""
    
    def test_get_random_template(self, auth_headers):
        """Test getting a random character template."""
        response = client.get(
            "/api/characters/random-template",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "description" in data
        assert len(data["name"]) > 0
        assert len(data["description"]) > 0
    
    def test_get_random_template_unauthorized(self):
        """Test getting random template without authentication."""
        response = client.get("/api/characters/random-template")
        assert response.status_code == 401


class TestProjectCharactersEndpoint:
    """Tests for the project characters API endpoints."""
    
    def test_get_project_characters_empty(self, auth_headers, sample_project):
        """Test getting project characters when none added."""
        response = client.get(
            f"/api/projects/{sample_project}/characters",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) == 0
    
    def test_add_nonexistent_character_to_project(
        self, auth_headers, sample_project
    ):
        """Test adding a character that doesn't exist to a project."""
        response = client.post(
            f"/api/projects/{sample_project}/characters",
            headers=auth_headers,
            json={"character_id": "char_nonexistent"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "CHARACTER_NOT_FOUND"
    
    def test_add_character_to_nonexistent_project(self, auth_headers):
        """Test adding character to a project that doesn't exist."""
        response = client.post(
            "/api/projects/proj_nonexistent/characters",
            headers=auth_headers,
            json={"character_id": "char_test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_get_project_characters_unauthorized(self, sample_project):
        """Test getting project characters without authentication."""
        response = client.get(f"/api/projects/{sample_project}/characters")
        assert response.status_code == 401
    
    def test_add_character_unauthorized(self, sample_project):
        """Test adding character without authentication."""
        response = client.post(
            f"/api/projects/{sample_project}/characters",
            json={"character_id": "char_test"}
        )
        assert response.status_code == 401


class TestDeleteCharacterFromProject:
    """Tests for removing characters from projects."""
    
    def test_delete_character_project_not_found(self, auth_headers):
        """Test deleting character from non-existent project."""
        response = client.delete(
            "/api/projects/proj_nonexistent/characters/char_test",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_delete_character_unauthorized(self, sample_project):
        """Test deleting character without authentication."""
        response = client.delete(
            f"/api/projects/{sample_project}/characters/char_test"
        )
        assert response.status_code == 401
