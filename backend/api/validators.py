"""API parameter validators for video style expansion.

This module provides validation functions for style and emotion parameters.

Requirements: 7.5
"""

from fastapi import HTTPException, status

from backend.schemas.models import VideoStyle, Emotion
from backend.core.style_templates import StyleTemplateManager


def validate_style(style: str) -> VideoStyle:
    """Validate and convert style parameter to VideoStyle enum.
    
    Args:
        style: Style string to validate.
        
    Returns:
        VideoStyle enum value.
        
    Raises:
        HTTPException: If style is invalid.
        
    Requirements: 7.5
    """
    try:
        return VideoStyle(style)
    except ValueError:
        valid_styles = [s.value for s in VideoStyle]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STYLE",
                "message": f"无效的视频风格: {style}。有效值: {', '.join(valid_styles)}"
            }
        )


def validate_emotion(emotion: str) -> Emotion:
    """Validate and convert emotion parameter to Emotion enum.
    
    Args:
        emotion: Emotion string to validate (can be enum name or value).
        
    Returns:
        Emotion enum value.
        
    Raises:
        HTTPException: If emotion is invalid.
        
    Requirements: 7.5
    """
    # Try to match by value (Chinese character)
    for e in Emotion:
        if e.value == emotion:
            return e
    
    # Try to match by name (uppercase)
    try:
        return Emotion[emotion.upper()]
    except KeyError:
        pass
    
    # Try to match by lowercase name
    for e in Emotion:
        if e.name.lower() == emotion.lower():
            return e
    
    valid_emotions = [f"{e.name.lower()} ({e.value})" for e in Emotion]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "INVALID_EMOTION",
            "message": f"无效的情感类型: {emotion}。有效值: {', '.join(valid_emotions)}"
        }
    )


def validate_audio_params(audio_params: dict) -> dict:
    """Validate audio parameters.
    
    Args:
        audio_params: Audio parameters dict to validate.
        
    Returns:
        Validated audio parameters dict.
        
    Raises:
        HTTPException: If any parameter is invalid.
        
    Requirements: 7.5
    """
    if not audio_params:
        return audio_params
    
    validated = {}
    
    # Validate emotion if present
    if "emotion" in audio_params:
        emotion = audio_params["emotion"]
        if isinstance(emotion, str):
            validated_emotion = validate_emotion(emotion)
            # 保存英文小写 ID，而不是中文值，以便前端能正确匹配
            validated["emotion"] = validated_emotion.name.lower()
        else:
            validated["emotion"] = emotion
    
    # Validate emotion_strength (0.0-1.0)
    if "emotion_strength" in audio_params:
        strength = audio_params["emotion_strength"]
        if not isinstance(strength, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "emotion_strength 必须是数字"
                }
            )
        if strength < 0.0 or strength > 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "emotion_strength 必须在 0.0-1.0 之间"
                }
            )
        validated["emotion_strength"] = float(strength)
    
    # Validate speed (0.5-2.0)
    if "speed" in audio_params:
        speed = audio_params["speed"]
        if not isinstance(speed, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "speed 必须是数字"
                }
            )
        if speed < 0.5 or speed > 2.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "speed 必须在 0.5-2.0 之间"
                }
            )
        validated["speed"] = float(speed)
    
    # Validate volume (0.5-1.5)
    if "volume" in audio_params:
        volume = audio_params["volume"]
        if not isinstance(volume, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "volume 必须是数字"
                }
            )
        if volume < 0.5 or volume > 1.5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AUDIO_PARAMS",
                    "message": "volume 必须在 0.5-1.5 之间"
                }
            )
        validated["volume"] = float(volume)
    
    return validated
