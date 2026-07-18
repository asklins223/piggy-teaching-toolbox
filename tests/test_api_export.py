"""Tests for the export API module.

This module tests export initiation, status checking, and download endpoints.

Requirements: 3.5

Note: These tests have been simplified after the database refactoring.
The API now uses database storage instead of file-based storage.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, UserRecord, hash_password, get_db
from backend.api.main import app
from backend.services.tasks import clear_tasks, get_task


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


class TestExportProjectEndpoint:
    """Tests for the export project endpoint."""
    
    def test_export_project_not_found(self, auth_headers):
        """Test export with non-existent project."""
        response = client.post(
            "/api/projects/proj_nonexistent/export",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_export_no_storyboard(self, auth_headers, sample_project):
        """Test export when no storyboard exists."""
        response = client.post(
            f"/api/projects/{sample_project}/export",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_REQUEST"
    
    def test_export_unauthorized(self, sample_project):
        """Test export without authentication."""
        response = client.post(
            f"/api/projects/{sample_project}/export"
        )
        assert response.status_code == 401


class TestExportStatusEndpoint:
    """Tests for the export status endpoint."""
    
    def test_export_status_no_export(self, auth_headers, sample_project):
        """Test export status when no export exists."""
        response = client.get(
            f"/api/projects/{sample_project}/export/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == sample_project
        assert data["has_export"] is False
    
    def test_export_status_project_not_found(self, auth_headers):
        """Test export status with non-existent project."""
        response = client.get(
            "/api/projects/proj_nonexistent/export/status",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_export_status_unauthorized(self, sample_project):
        """Test export status without authentication."""
        response = client.get(
            f"/api/projects/{sample_project}/export/status"
        )
        assert response.status_code == 401


class TestDownloadExportEndpoint:
    """Tests for the download export endpoint."""
    
    def test_download_export_no_export(self, auth_headers, sample_project):
        """Test downloading when no export exists."""
        response = client.get(
            f"/api/projects/{sample_project}/export/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "EXPORT_NOT_FOUND"
    
    def test_download_export_project_not_found(self, auth_headers):
        """Test downloading from non-existent project."""
        response = client.get(
            "/api/projects/proj_nonexistent/export/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
    
    def test_download_export_unauthorized(self, sample_project):
        """Test downloading without authentication."""
        response = client.get(
            f"/api/projects/{sample_project}/export/download"
        )
        assert response.status_code == 401
