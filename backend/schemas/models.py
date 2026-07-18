"""Core data models for the video generator.

This module defines all Pydantic models used throughout the video generation pipeline,
including teaching goals, scenes, storyboards, images, audio, subtitles, and project state.

Requirements: 7.1, 7.2
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SceneDuration(int, Enum):
    """Scene duration options (5, 8, 10, 12, or 15 seconds).
    
    LLM will choose appropriate duration based on content complexity.
    """
    VERY_SHORT = 5   # 5秒 - 简单展示、过渡
    SHORT = 8        # 8秒 - 简短讲解
    MEDIUM = 10      # 10秒 - 标准讲解
    LONG = 12        # 12秒 - 详细讲解
    VERY_LONG = 15   # 15秒 - 复杂内容、互动环节


class CharacterStyle(str, Enum):
    """Supported character visual styles."""
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ANIME = "anime"


class ResourceStatus(str, Enum):
    """Resource generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectStatus(str, Enum):
    """Project workflow status."""
    INITIALIZED = "initialized"
    STORYBOARD_READY = "storyboard_ready"
    IMAGES_GENERATING = "images_generating"
    IMAGES_READY = "images_ready"
    AUDIO_GENERATING = "audio_generating"
    AUDIO_READY = "audio_ready"
    SUBTITLES_READY = "subtitles_ready"
    COMPLETED = "completed"


class Emotion(str, Enum):
    """Supported emotions for audio generation."""
    # 现有情感
    HAPPY = "喜"
    ANGRY = "怒"
    SAD = "哀"
    FEAR = "惧"
    DISGUST = "厌恶"
    DEPRESSED = "低落"
    SURPRISED = "惊喜"
    CALM = "平静"
    # 新增情感 (Requirements: 3.1)
    LIVELY = "活泼"
    HEALING = "治愈"
    AGGRIEVED = "委屈"
    EMBARRASSED = "尴尬"
    PROUD = "自豪"
    CONFLICTED = "纠结"
    LOST = "失落"
    SHY = "害羞"
    IRRITATED = "烦躁"


class VideoStyle(str, Enum):
    """视频风格类型 (Requirements: 1.1, 2.1-2.5)"""
    TEACHING = "teaching"           # 教学
    NURSERY_RHYME = "nursery_rhyme" # 儿歌
    STORYBOOK = "storybook"         # 读绘本/故事
    RECITATION = "recitation"       # 朗诵
    CUSTOM = "custom"               # 自定义


class AudioParams(BaseModel):
    """分镜音频生成参数 (Requirements: 5.2)
    
    Attributes:
        emotion: 情感类型
        emotion_strength: 情感强度 (0.0-1.0)
        speed: 语速 (0.5-2.0)
        volume: 音量 (0.5-1.5)
    """
    emotion: Emotion = Field(default=Emotion.CALM, description="情感类型")
    emotion_strength: float = Field(default=0.6, ge=0.0, le=1.0, description="情感强度")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    volume: float = Field(default=1.0, ge=0.5, le=1.5, description="音量")

    model_config = {"frozen": False}


# =============================================================================
# Legacy Models (for backward compatibility during refactoring)
# =============================================================================

class CharacterConfig(BaseModel):
    """Legacy character configuration model."""
    name: str
    description: str


class CharacterReference(BaseModel):
    """Legacy character reference model."""
    character_id: str
    name: str
    image_path: str
    image_url: Optional[str] = None


class AspectRatio(str, Enum):
    """Legacy aspect ratio enum."""
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class VideoQuality(str, Enum):
    """Legacy video quality enum."""
    STANDARD = "standard"
    HIGH = "high"


class ClipStatus(str, Enum):
    """Legacy clip status enum."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoClip(BaseModel):
    """Legacy video clip model."""
    clip_id: str
    scene_id: str
    file_path: str
    duration_seconds: float
    status: ClipStatus = ClipStatus.PENDING
    error_message: Optional[str] = None


class ComposedVideo(BaseModel):
    """Legacy composed video model."""
    output_path: str
    total_duration_seconds: float
    clip_count: int


class CompositionConfig(BaseModel):
    """Legacy composition config model."""
    output_path: str
    quality: str = "high"


class OutputFormat(str, Enum):
    """Legacy output format enum."""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"


class TransitionType(str, Enum):
    """Legacy transition type enum."""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"


# =============================================================================
# Teaching Goal and Scene Models
# =============================================================================

class TeachingGoal(BaseModel):
    """Teaching content configuration.
    
    Attributes:
        topic: Main teaching topic.
        target_audience: Intended audience description.
        key_points: List of key concepts to cover.
        style: 视频风格 (Requirements: 1.4)
        custom_style_description: 自定义风格描述 (Requirements: 1.4)
    """
    topic: str = Field(..., min_length=1, description="Teaching topic")
    target_audience: str = Field(..., min_length=1, description="Target audience")
    key_points: list[str] = Field(default_factory=list, description="Key concepts to cover")
    # 新增字段 (Requirements: 1.4, 5.1)
    style: VideoStyle = Field(default=VideoStyle.TEACHING, description="视频风格")
    custom_style_description: Optional[str] = Field(default=None, description="自定义风格描述")

    model_config = {"frozen": False}


class Scene(BaseModel):
    """A single scene in the storyboard.
    
    Attributes:
        scene_id: Unique identifier for the scene.
        step_number: Sequential step number.
        description_cn: Chinese scene description (legacy, for backward compatibility).
        image_prompt: 图片生成描述，用于AI图片生成，包含构图、光线、色调等专业词汇
        video_prompt: 视频生成描述，用于视频生成，包含运镜、转场等专业词汇
        narration_cn: Chinese narration text.
        narration_en: English narration text.
        duration: Scene duration (5, 8, 10, 12, or 15 seconds).
        character_ids: List of character IDs appearing in this scene.
        audio_params: 音频生成参数 (Requirements: 5.1)
    """
    scene_id: str = Field(..., min_length=1, description="Unique scene ID")
    step_number: int = Field(..., ge=1, description="Sequential step number")
    description_cn: str = Field(..., min_length=1, description="Chinese scene description (legacy)")
    # 新增：拆分场景描述为图片和视频两部分
    image_prompt: str = Field(default="", description="图片生成描述，包含构图、光线、色调等")
    video_prompt: str = Field(default="", description="视频生成描述，包含运镜、转场等")
    narration_cn: str = Field(..., min_length=1, description="Chinese narration")
    narration_en: str = Field(default="", description="English narration")
    duration: SceneDuration = Field(default=SceneDuration.MEDIUM, description="Duration (5/8/10/12/15 seconds)")
    character_ids: list[str] = Field(default_factory=list, description="Character IDs in this scene (max 3)")
    # 新增字段 (Requirements: 5.1)
    audio_params: Optional[AudioParams] = Field(default=None, description="音频生成参数")

    model_config = {"frozen": False}


class Storyboard(BaseModel):
    """Complete storyboard for a teaching video.
    
    Attributes:
        project_id: Associated project ID.
        title: Video title.
        scenes: List of scenes in order.
        total_duration_seconds: Total duration of all scenes.
    """
    project_id: str = Field(..., min_length=1, description="Project ID")
    title: str = Field(..., min_length=1, description="Video title")
    scenes: list[Scene] = Field(default_factory=list, description="Ordered list of scenes")
    total_duration_seconds: int = Field(default=0, ge=0, description="Total duration")

    model_config = {"frozen": False}


# =============================================================================
# Resource Models (Images, Audio, Subtitles)
# =============================================================================

class SceneImage(BaseModel):
    """A generated scene image.
    
    Attributes:
        scene_id: Associated scene ID.
        image_path: Local path to the image file.
        prompt_used: The prompt used for generation.
        status: Generation status.
        error_message: Error message if generation failed.
    """
    scene_id: str = Field(..., min_length=1, description="Associated scene ID")
    image_path: str = Field(..., description="Path to image file")
    prompt_used: str = Field(default="", description="Prompt used for generation")
    status: ResourceStatus = Field(default=ResourceStatus.PENDING, description="Generation status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    model_config = {"frozen": False}


class SceneAudio(BaseModel):
    """A generated scene audio.
    
    Attributes:
        scene_id: Associated scene ID.
        audio_path: Local path to the Chinese audio file.
        audio_path_en: Local path to the English audio file.
        duration_seconds: Actual audio duration (Chinese).
        duration_seconds_en: Actual audio duration (English).
        status: Generation status.
        error_message: Error message if generation failed.
    """
    scene_id: str = Field(..., min_length=1, description="Associated scene ID")
    audio_path: str = Field(..., description="Path to Chinese audio file")
    audio_path_en: Optional[str] = Field(default=None, description="Path to English audio file")
    duration_seconds: float = Field(default=0.0, ge=0, description="Chinese audio duration")
    duration_seconds_en: float = Field(default=0.0, ge=0, description="English audio duration")
    status: ResourceStatus = Field(default=ResourceStatus.PENDING, description="Generation status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    model_config = {"frozen": False}


class SubtitleSegment(BaseModel):
    """A subtitle segment for a scene.
    
    Attributes:
        scene_id: Associated scene ID.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        text_cn: Chinese subtitle text.
        text_en: English subtitle text.
    """
    scene_id: str = Field(..., min_length=1, description="Associated scene ID")
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    text_cn: str = Field(..., min_length=1, description="Chinese subtitle text")
    text_en: str = Field(..., min_length=1, description="English subtitle text")

    model_config = {"frozen": False}


class SubtitleFile(BaseModel):
    """A generated subtitle file.
    
    Attributes:
        file_path: Path to the subtitle file.
        language: Language code ("cn" or "en").
        format: Subtitle format (e.g., "srt").
    """
    file_path: str = Field(..., description="Path to subtitle file")
    language: str = Field(..., pattern="^(cn|en)$", description="Language code")
    format: str = Field(default="srt", description="Subtitle format")

    model_config = {"frozen": False}


# =============================================================================
# Export Models
# =============================================================================

class SceneAsset(BaseModel):
    """Complete assets for a single scene.
    
    Attributes:
        scene_id: Associated scene ID.
        image_path: Path to scene image.
        audio_path: Path to audio file.
        subtitle_cn: Chinese subtitle segment.
        subtitle_en: English subtitle segment.
    """
    scene_id: str = Field(..., min_length=1, description="Associated scene ID")
    image_path: str = Field(..., description="Path to image file")
    audio_path: str = Field(..., description="Path to audio file")
    subtitle_cn: SubtitleSegment = Field(..., description="Chinese subtitle")
    subtitle_en: SubtitleSegment = Field(..., description="English subtitle")

    model_config = {"frozen": False}


class ExportPackage(BaseModel):
    """Complete export package for a project.
    
    Attributes:
        project_id: Associated project ID.
        zip_path: Path to the ZIP archive.
        manifest_path: Path to the manifest JSON file.
        assets: List of scene assets.
        subtitle_cn_path: Path to complete Chinese subtitle file.
        subtitle_en_path: Path to complete English subtitle file.
    """
    project_id: str = Field(..., min_length=1, description="Project ID")
    zip_path: str = Field(..., description="Path to ZIP archive")
    manifest_path: str = Field(..., description="Path to manifest JSON")
    assets: list[SceneAsset] = Field(default_factory=list, description="Scene assets")
    subtitle_cn_path: str = Field(..., description="Path to Chinese subtitle file")
    subtitle_en_path: str = Field(..., description="Path to English subtitle file")

    model_config = {"frozen": False}


# =============================================================================
# Project State Model
# =============================================================================

class ProjectState(BaseModel):
    """Complete project state for persistence and recovery.
    
    This model represents the entire state of a video generation project,
    enabling save/load functionality and checkpoint recovery.
    
    Attributes:
        project_id: Unique project identifier.
        created_at: Project creation timestamp (ISO format).
        updated_at: Last update timestamp (ISO format).
        status: Current project status.
        goal: Teaching goal configuration.
        storyboard: Generated storyboard (if available).
        images: List of generated scene images.
        audios: List of generated scene audios.
        subtitles: List of subtitle segments.
        export_package: Export package (if completed).
    
    Requirements: 7.1, 7.2, 7.3
    """
    project_id: str = Field(..., min_length=1, description="Unique project ID")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Creation timestamp (ISO format)"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Last update timestamp (ISO format)"
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.INITIALIZED, 
        description="Project status"
    )
    goal: TeachingGoal = Field(..., description="Teaching goal")
    storyboard: Optional[Storyboard] = Field(default=None, description="Storyboard")
    images: list[SceneImage] = Field(default_factory=list, description="Scene images")
    audios: list[SceneAudio] = Field(default_factory=list, description="Scene audios")
    subtitles: list[SubtitleSegment] = Field(default_factory=list, description="Subtitles")
    export_package: Optional[ExportPackage] = Field(default=None, description="Export package")

    # Legacy fields for backward compatibility
    characters: list[CharacterReference] = Field(default_factory=list, description="Legacy characters")
    clips: list[VideoClip] = Field(default_factory=list, description="Legacy clips")
    final_video: Optional[ComposedVideo] = Field(default=None, description="Legacy final video")

    model_config = {"frozen": False}

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def to_json(self) -> str:
        """Serialize project state to JSON string.
        
        Returns:
            JSON string representation of the project state.
        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ProjectState":
        """Deserialize project state from JSON string.
        
        Args:
            json_str: JSON string representation.
            
        Returns:
            ProjectState instance.
        """
        return cls.model_validate_json(json_str)


# =============================================================================
# Audio Configuration Model
# =============================================================================

class AudioConfig(BaseModel):
    """Configuration for audio generation.
    
    Attributes:
        voice_reference_path: Optional path to voice reference audio.
        emotion: Emotion for the audio.
        emotion_strength: Emotion strength (0.0-1.0).
    """
    voice_reference_path: Optional[str] = Field(default=None, description="Voice reference audio path")
    emotion: Emotion = Field(default=Emotion.CALM, description="Emotion")
    emotion_strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Emotion strength")

    model_config = {"frozen": False}
