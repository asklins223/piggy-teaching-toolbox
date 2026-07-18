"""Tests for the styles and emotions API modules.

This module tests the styles and emotions API endpoints and property-based testing
for round-trip consistency and error handling.

**Property 6: API 参数 Round-Trip**
**Property 7: 无效参数错误处理**
**Validates: Requirements 7.1, 7.4, 7.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base, UserRecord, hash_password, get_db
from backend.api.main import app
from backend.schemas.models import VideoStyle, Emotion


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"


# Create a single engine for all tests with StaticPool to handle threading
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
Base.metadata.create_all(_test_engine)
_TestSessionLocal = sessionmaker(bind=_test_engine)


def _get_test_db():
    """Get test database session."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Override the database dependency globally
app.dependency_overrides[get_db] = _get_test_db


# Create test user
_init_session = _TestSessionLocal()
_existing_user = _init_session.query(UserRecord).filter(
    UserRecord.username == TEST_USERNAME
).first()
if not _existing_user:
    _test_user = UserRecord(
        username=TEST_USERNAME,
        password_hash=hash_password(TEST_PASSWORD),
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    _init_session.add(_test_user)
    _init_session.commit()
_init_session.close()


# Test client
client = TestClient(app)


def get_auth_headers():
    """Get authentication headers for API requests."""
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestStylesAPI:
    """Tests for the styles API endpoint."""
    
    def test_get_styles_success(self):
        """Test getting all available styles."""
        headers = get_auth_headers()
        response = client.get("/api/styles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert isinstance(data["styles"], list)
        assert len(data["styles"]) == 5  # teaching, nursery_rhyme, storybook, recitation, custom
        
        # Verify all expected styles are present
        style_ids = [s["id"] for s in data["styles"]]
        assert "teaching" in style_ids
        assert "nursery_rhyme" in style_ids
        assert "storybook" in style_ids
        assert "recitation" in style_ids
        assert "custom" in style_ids
    
    def test_get_styles_structure(self):
        """Test that each style has required fields."""
        headers = get_auth_headers()
        response = client.get("/api/styles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for style in data["styles"]:
            assert "id" in style
            assert "name" in style
            assert "description" in style
    
    def test_get_styles_unauthorized(self):
        """Test getting styles without authentication."""
        response = client.get("/api/styles")
        
        assert response.status_code == 401


class TestEmotionsAPI:
    """Tests for the emotions API endpoint."""
    
    def test_get_emotions_success(self):
        """Test getting all available emotions."""
        headers = get_auth_headers()
        response = client.get("/api/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "emotions" in data
        assert "categories" in data
        assert isinstance(data["emotions"], list)
        assert len(data["emotions"]) == 17  # All 17 emotions
    
    def test_get_emotions_categories(self):
        """Test that emotions are properly categorized."""
        headers = get_auth_headers()
        response = client.get("/api/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        category_ids = [c["id"] for c in data["categories"]]
        assert "positive" in category_ids
        assert "negative" in category_ids
        assert "neutral" in category_ids
    
    def test_get_emotions_structure(self):
        """Test that each emotion has required fields."""
        headers = get_auth_headers()
        response = client.get("/api/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for emotion in data["emotions"]:
            assert "id" in emotion
            assert "value" in emotion
            assert "name" in emotion
            assert "category" in emotion
    
    def test_get_emotions_unauthorized(self):
        """Test getting emotions without authentication."""
        response = client.get("/api/emotions")
        
        assert response.status_code == 401


class TestProjectStyleRoundTrip:
    """Tests for project style round-trip consistency.
    
    **Feature: video-style-expansion, Property 6: API 参数 Round-Trip**
    **Validates: Requirements 7.1**
    """
    
    def test_project_style_roundtrip_teaching(self):
        """Test project creation with teaching style."""
        headers = get_auth_headers()
        
        response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience",
                "key_points": ["Point 1"],
                "style": "teaching"
            }
        )
        
        assert response.status_code == 201
        project_id = response.json()["project_id"]
        
        # Get project and verify style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["goal"]["style"] == "teaching"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_project_style_roundtrip_custom(self):
        """Test project creation with custom style."""
        headers = get_auth_headers()
        
        custom_desc = "A fun and engaging style for kids"
        response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience",
                "key_points": ["Point 1"],
                "style": "custom",
                "custom_style_description": custom_desc
            }
        )
        
        assert response.status_code == 201
        project_id = response.json()["project_id"]
        
        # Get project and verify style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["goal"]["style"] == "custom"
        assert data["goal"]["custom_style_description"] == custom_desc
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)


class TestInvalidParameterHandling:
    """Tests for invalid parameter error handling.
    
    **Feature: video-style-expansion, Property 7: 无效参数错误处理**
    **Validates: Requirements 7.5**
    """
    
    def test_invalid_style_error(self):
        """Test that invalid style returns clear error."""
        headers = get_auth_headers()
        
        response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience",
                "style": "invalid_style"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_STYLE"


class TestPropertyBasedStyleRoundTrip:
    """Property-based tests for style round-trip consistency.
    
    **Feature: video-style-expansion, Property 6: API 参数 Round-Trip**
    **Validates: Requirements 7.1, 7.4**
    """
    
    @given(
        style=st.sampled_from([s.value for s in VideoStyle]),
        topic=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        target_audience=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_style_roundtrip_property(
        self,
        style: str,
        topic: str,
        target_audience: str,
    ):
        """Property: For any valid style, creating a project and retrieving it
        should return the same style value.
        
        *For any* 通过 API 创建或更新的项目，风格参数应能正确保存并在后续请求中返回一致的值。
        
        **Feature: video-style-expansion, Property 6: API 参数 Round-Trip**
        **Validates: Requirements 7.1**
        """
        headers = get_auth_headers()
        
        # Create project with style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": topic,
                "target_audience": target_audience,
                "style": style
            }
        )
        
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Get project and verify style round-trip
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["goal"]["style"] == style
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)


class TestPropertyBasedInvalidParams:
    """Property-based tests for invalid parameter handling.
    
    **Feature: video-style-expansion, Property 7: 无效参数错误处理**
    **Validates: Requirements 7.5**
    """
    
    @given(
        invalid_style=st.text(min_size=1, max_size=20).filter(
            lambda x: x.strip() and x not in [s.value for s in VideoStyle]
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_style_error_property(self, invalid_style: str):
        """Property: For any invalid style value, the API should return
        a clear error message.
        
        *For any* 包含无效风格参数的 API 请求，系统应返回明确的错误信息而非静默失败。
        
        **Feature: video-style-expansion, Property 7: 无效参数错误处理**
        **Validates: Requirements 7.5**
        """
        headers = get_auth_headers()
        
        # Try to create project with invalid style
        response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "Test Topic",
                "target_audience": "Test Audience",
                "style": invalid_style
            }
        )
        
        # Should return 400 with INVALID_STYLE error
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_STYLE"
