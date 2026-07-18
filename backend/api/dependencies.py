"""API dependencies module.

This module provides common dependencies for FastAPI endpoints,
including authentication and service instances.

Requirements: 3.0
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.api.routes.auth import verify_token


# Security scheme for protected endpoints
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Dependency to get the current authenticated user.
    
    Use this dependency to protect API endpoints that require authentication.
    
    Example:
        @router.get("/protected")
        async def protected_endpoint(user: str = Depends(get_current_user)):
            return {"user": user}
    
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


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Dependency to optionally get the current user.
    
    Use this for endpoints that work with or without authentication.
    
    Args:
        credentials: HTTP Bearer credentials from the request.
        
    Returns:
        The authenticated username if valid token provided, None otherwise.
    """
    if credentials is None:
        return None
    
    return verify_token(credentials.credentials)
