"""Emotions API module for audio emotion management.

This module provides REST API endpoints for retrieving available emotions
and their categories for audio generation.

Requirements: 7.3
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from backend.api.dependencies import get_current_user
from backend.schemas.models import Emotion
from backend.core.generators.audio import AudioGenerator


router = APIRouter(prefix="/emotions", tags=["emotions"])


# Response models
class EmotionInfo(BaseModel):
    """Emotion information."""
    id: str = Field(..., description="Emotion ID (lowercase enum name)")
    value: str = Field(..., description="Emotion value (Chinese character)")
    name: str = Field(..., description="Emotion display name in Chinese")
    category: str = Field(..., description="Emotion category: positive, negative, or neutral")


class EmotionCategoryInfo(BaseModel):
    """Emotion category information."""
    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category display name in Chinese")
    emotions: list[EmotionInfo] = Field(..., description="Emotions in this category")


class EmotionListResponse(BaseModel):
    """Emotion list response."""
    emotions: list[EmotionInfo] = Field(..., description="List of all emotions")
    categories: list[EmotionCategoryInfo] = Field(..., description="Emotions grouped by category")


def _get_emotion_category(emotion: Emotion) -> str:
    """Get the category for an emotion.
    
    Args:
        emotion: The emotion to categorize.
        
    Returns:
        Category string: "positive", "negative", or "neutral".
    """
    for category, emotions in AudioGenerator.EMOTION_CATEGORIES.items():
        if emotion in emotions:
            return category
    return "neutral"


# Category display names
CATEGORY_NAMES = {
    "positive": "积极情感",
    "negative": "消极情感",
    "neutral": "中性情感",
}


@router.get("", response_model=EmotionListResponse)
async def get_emotions(
    current_user: str = Depends(get_current_user),
) -> EmotionListResponse:
    """Get all available emotions with their categories.
    
    Returns a list of all 17 emotions that can be used for audio generation,
    along with their categories (positive, negative, neutral) for UI grouping.
    
    Args:
        current_user: Authenticated user.
        
    Returns:
        EmotionListResponse: List of emotions and categorized groups.
        
    Requirements: 7.3
    """
    # Build flat list of all emotions
    all_emotions = []
    for emotion in Emotion:
        category = _get_emotion_category(emotion)
        emotion_info = EmotionInfo(
            id=emotion.name.lower(),
            value=emotion.value,
            name=AudioGenerator.EMOTION_TEXT_MAP.get(emotion, emotion.value),
            category=category
        )
        all_emotions.append(emotion_info)
    
    # Build categorized list
    categories = []
    for category_id in ["positive", "negative", "neutral"]:
        category_emotions = [e for e in all_emotions if e.category == category_id]
        if category_emotions:
            categories.append(EmotionCategoryInfo(
                id=category_id,
                name=CATEGORY_NAMES.get(category_id, category_id),
                emotions=category_emotions
            ))
    
    return EmotionListResponse(
        emotions=all_emotions,
        categories=categories
    )
