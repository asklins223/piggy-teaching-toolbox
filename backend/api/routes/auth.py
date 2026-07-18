"""Authentication module for the video generator API.

This module provides JWT-based authentication with login, logout,
and current user endpoints. User data is stored in MySQL database.

Requirements: 3.0
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError

from backend.db.models import get_db, UserRecord, verify_password


# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "video-generator-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

# Security scheme
security = HTTPBearer(auto_error=False)

# Router
router = APIRouter()


# Request/Response models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    token: str
    expires_at: str


class UserResponse(BaseModel):
    """User response model."""
    username: str
    email: Optional[str] = None
    is_admin: bool = False


class LogoutResponse(BaseModel):
    """Logout response model."""
    success: bool


class ErrorResponse(BaseModel):
    """Error response model."""
    error: dict


# Token management
def create_token(username: str) -> tuple[str, datetime]:
    """Create a JWT token for the given username.
    
    Args:
        username: The username to encode in the token.
        
    Returns:
        Tuple of (token string, expiration datetime).
    """
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the username.
    
    Args:
        token: The JWT token to verify.
        
    Returns:
        The username if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except PyJWTError:
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Dependency to get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials from the request.
        
    Returns:
        The authenticated username.
        
    Raises:
        HTTPException: If authentication fails.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing authentication token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username


# API Endpoints
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Login endpoint to authenticate user and get JWT token.
    
    Args:
        request: Login request with username and password.
        db: Database session.
        
    Returns:
        Token response with JWT token and expiration.
        
    Raises:
        HTTPException: If credentials are invalid.
    """
    # Find user in database
    user = db.query(UserRecord).filter(UserRecord.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_DISABLED", "message": "User account is disabled"},
        )
    
    # Create token
    token, expires_at = create_token(request.username)
    
    return TokenResponse(
        token=token,
        expires_at=expires_at.isoformat(),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: str = Depends(get_current_user)
) -> LogoutResponse:
    """Logout endpoint.
    
    Note: Since we use stateless JWT tokens, logout is handled client-side
    by removing the token. This endpoint just validates the token is valid.
    
    Args:
        current_user: The authenticated user (from token).
        
    Returns:
        Success response.
    """
    return LogoutResponse(success=True)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get current authenticated user information.
    
    Args:
        current_user: The authenticated user (from token).
        db: Database session.
        
    Returns:
        User information.
    """
    user = db.query(UserRecord).filter(UserRecord.username == current_user).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        is_admin=user.is_admin
    )
