"""Styles API module for video style management.

This module provides REST API endpoints for retrieving available video styles.

Requirements: 7.2
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from backend.api.dependencies import get_current_user
from backend.core.style_templates import StyleTemplateManager


router = APIRouter(prefix="/styles", tags=["styles"])


# Response models
class StyleInfo(BaseModel):
    """Style information."""
    id: str = Field(..., description="Style ID")
    name: str = Field(..., description="Style name in Chinese")
    description: str = Field(..., description="Style description")
    icon: Optional[str] = Field(default=None, description="Style icon emoji")


class StyleListResponse(BaseModel):
    """Style list response."""
    styles: list[StyleInfo] = Field(..., description="List of available styles")


@router.get("", response_model=StyleListResponse)
async def get_styles(
    current_user: str = Depends(get_current_user),
) -> StyleListResponse:
    """Get all available video styles.
    
    Returns a list of all preset video styles that can be used when creating
    a project. Each style has a unique ID, display name, description, and icon.
    
    Args:
        current_user: Authenticated user.
        
    Returns:
        StyleListResponse: List of available styles.
        
    Requirements: 7.2
    """
    styles_data = StyleTemplateManager.get_all_styles()
    styles = [
        StyleInfo(
            id=s["id"],
            name=s["name"],
            description=s["description"],
            icon=s.get("icon")
        )
        for s in styles_data
    ]
    return StyleListResponse(styles=styles)
