"""Tests for the audio API module."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, UserRecord, hash_password, get_db
from backend.api.main import app
from backend.services.tasks import clear_tasks


TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    """Create a session factory for the test database."""
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="module")
def setup_test_user(test_session_factory):
    """Create a test user in the database."""
    session = test_session_factory()
    test_user = UserRecord(
        username=TEST_USERNAME,
        password_hash=hash_password(TEST_PASSWORD),
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    session.add(test_user)
    session.commit()
    session.close()


@pytest.fixture(scope="module")
def client(test_session_factory, setup_test_user):
    """Create a test client with database override."""
    def get_test_db():
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
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
def sample_project(client, auth_headers):
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


class TestGetVoicesEndpoint:
    def test_get_voices_returns_list(self, client, auth_headers):
        response = client.get("/api/voices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)

    def test_get_voices_unauthorized(self, client):
        response = client.get("/api/voices")
        assert response.status_code == 401


class TestGenerateAudioEndpoint:
    def test_generate_audio_project_not_found(self, client, auth_headers):
        response = client.post(
            "/api/projects/proj_nonexistent/audio/generate",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_generate_audio_no_storyboard(self, client, auth_headers, sample_project):
        response = client.post(
            f"/api/projects/{sample_project}/audio/generate",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_REQUEST"

    def test_generate_audio_unauthorized(self, client, sample_project):
        response = client.post(
            f"/api/projects/{sample_project}/audio/generate",
            json={}
        )
        assert response.status_code == 401


class TestGetSceneAudioEndpoint:
    def test_get_scene_audio_project_not_found(self, client, auth_headers):
        response = client.get(
            "/api/projects/proj_nonexistent/scenes/scene_001/audio",
            headers=auth_headers
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_get_scene_audio_unauthorized(self, client, sample_project):
        response = client.get(
            f"/api/projects/{sample_project}/scenes/scene_001/audio"
        )
        assert response.status_code == 401
