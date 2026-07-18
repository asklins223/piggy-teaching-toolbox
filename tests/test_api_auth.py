"""Tests for the authentication API module.

This module tests JWT token generation, verification, and API endpoints.

**Property 1: 认证 Token 有效性**
**Validates: Requirements 3.0**
"""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.routes.auth import (
    create_token,
    verify_token,
    TOKEN_EXPIRE_DAYS,
)
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


class TestTokenGeneration:
    """Tests for token generation functionality."""
    
    def test_create_token_returns_valid_token(self):
        """Test that create_token returns a non-empty token string."""
        token, expires_at = create_token("testuser")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_returns_future_expiration(self):
        """Test that token expiration is in the future."""
        token, expires_at = create_token("testuser")
        
        assert expires_at > datetime.now(timezone.utc)
    
    def test_create_token_expiration_is_30_days(self):
        """Test that token expires in approximately 30 days."""
        before = datetime.now(timezone.utc)
        token, expires_at = create_token("testuser")
        after = datetime.now(timezone.utc)
        
        expected_min = before + timedelta(days=TOKEN_EXPIRE_DAYS)
        expected_max = after + timedelta(days=TOKEN_EXPIRE_DAYS)
        
        assert expected_min <= expires_at <= expected_max


class TestTokenVerification:
    """Tests for token verification functionality."""
    
    def test_verify_valid_token(self):
        """Test that a valid token can be verified."""
        token, _ = create_token("testuser")
        
        username = verify_token(token)
        
        assert username == "testuser"
    
    def test_verify_invalid_token(self):
        """Test that an invalid token returns None."""
        result = verify_token("invalid-token")
        
        assert result is None
    
    def test_verify_empty_token(self):
        """Test that an empty token returns None."""
        result = verify_token("")
        
        assert result is None
    
    def test_verify_malformed_token(self):
        """Test that a malformed token returns None."""
        result = verify_token("not.a.valid.jwt.token")
        
        assert result is None


class TestLoginEndpoint:
    """Tests for the login API endpoint."""
    
    def test_login_success(self, db_session):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert len(data["token"]) > 0
    
    def test_login_invalid_username(self, db_session):
        """Test login failure with invalid username."""
        response = client.post(
            "/api/auth/login",
            json={"username": "wronguser", "password": TEST_PASSWORD}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == "INVALID_CREDENTIALS"
    
    def test_login_invalid_password(self, db_session):
        """Test login failure with invalid password."""
        response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == "INVALID_CREDENTIALS"
    
    def test_login_missing_fields(self, db_session):
        """Test login failure with missing fields."""
        response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME}
        )
        
        assert response.status_code == 422  # Validation error


class TestLogoutEndpoint:
    """Tests for the logout API endpoint."""
    
    def test_logout_success(self, db_session):
        """Test successful logout with valid token."""
        # First login to get a token
        login_response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        token = login_response.json()["token"]
        
        # Then logout
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_logout_without_token(self, db_session):
        """Test logout failure without token."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 401


class TestMeEndpoint:
    """Tests for the /me API endpoint."""
    
    def test_get_me_success(self, db_session):
        """Test getting current user with valid token."""
        # First login to get a token
        login_response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        token = login_response.json()["token"]
        
        # Then get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == TEST_USERNAME
    
    def test_get_me_without_token(self, db_session):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_get_me_with_invalid_token(self, db_session):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


class TestPropertyBasedAuth:
    """Property-based tests for authentication.
    
    **Feature: langchain-video-generator, Property 1: 认证 Token 有效性**
    **Validates: Requirements 3.0**
    """
    
    @given(username=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @settings(max_examples=100)
    def test_token_roundtrip_property(self, username: str):
        """Property: For any valid username, creating a token and verifying it
        should return the same username.
        
        *For any* 有效的用户名，登录后返回的 token 应能通过验证，且在 30 天内有效。
        
        **Feature: langchain-video-generator, Property 1: 认证 Token 有效性**
        **Validates: Requirements 3.0**
        """
        # Create token for the username
        token, expires_at = create_token(username)
        
        # Verify the token returns the same username
        verified_username = verify_token(token)
        
        assert verified_username == username
        
        # Verify expiration is within 30 days
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(days=TOKEN_EXPIRE_DAYS)
        
        # Allow 1 minute tolerance for test execution time
        assert expires_at <= expected_expiry + timedelta(minutes=1)
        assert expires_at >= now + timedelta(days=TOKEN_EXPIRE_DAYS - 1)
