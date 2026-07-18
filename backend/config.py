"""Configuration management module.

Handles environment variable loading and configuration classes for the video generator.
Supports Alibaba Cloud DashScope API and local IndexTTS2 model.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Legacy Configuration Classes (for backward compatibility during migration)
# These will be removed after all components are refactored
# =============================================================================

class OpenAIConfig(BaseSettings):
    """OpenAI API configuration (DEPRECATED - use DashScopeConfig)."""
    
    model_config = SettingsConfigDict(env_prefix="OPENAI_", extra="ignore")
    
    api_key: str = Field(default="", description="OpenAI API key")
    model: str = Field(default="gpt-4", description="LLM model name")
    image_model: str = Field(default="dall-e-3", description="Image generation model")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM response")


class KlingConfig(BaseSettings):
    """Kling AI API configuration (DEPRECATED - will be removed)."""
    
    model_config = SettingsConfigDict(env_prefix="KLING_", extra="ignore")
    
    api_key: str = Field(default="", description="Kling AI API key")
    api_secret: str = Field(default="", description="Kling AI API secret")
    base_url: str = Field(
        default="https://api.klingai.com",
        description="Kling AI API base URL"
    )
    timeout_seconds: int = Field(default=300, description="API request timeout")
    poll_interval_seconds: int = Field(default=5, description="Status polling interval")


class VideoConfig(BaseSettings):
    """Video generation configuration (DEPRECATED - use SceneConfig)."""
    
    model_config = SettingsConfigDict(env_prefix="VIDEO_", extra="ignore")
    
    default_aspect_ratio: str = Field(default="16:9", description="Default aspect ratio")
    default_quality: str = Field(default="standard", description="Default quality level")
    default_fps: int = Field(default=30, description="Default frames per second")
    default_resolution: tuple[int, int] = Field(
        default=(1920, 1080),
        description="Default resolution (width, height)"
    )
    max_scene_duration_seconds: int = Field(
        default=10,
        description="Maximum duration for a single scene"
    )
    default_transition_type: str = Field(
        default="crossfade",
        description="Default transition type"
    )
    default_transition_duration: float = Field(
        default=0.5,
        description="Default transition duration in seconds"
    )


# =============================================================================
# New Configuration Classes
# =============================================================================


class DashScopeConfig(BaseSettings):
    """Alibaba Cloud DashScope API configuration for qwen models."""
    
    model_config = SettingsConfigDict(env_prefix="DASHSCOPE_", extra="ignore")
    
    api_key: str = Field(default="", description="DashScope API key")
    text_model: str = Field(default="qwen-max", description="Text generation model (qwen3-max)")
    image_model: str = Field(default="wan2.6-t2i", description="Image generation model for characters")
    image_edit_model: str = Field(default="qwen-image-edit-plus", description="Image edit model for scenes with character reference")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM response")
    timeout_seconds: int = Field(default=120, description="API request timeout")


class VolcEngineConfig(BaseSettings):
    """火山引擎方舟 API 配置 (Seedream 图片生成)."""
    
    model_config = SettingsConfigDict(env_prefix="ARK_", extra="ignore")
    
    api_key: str = Field(default="", description="火山方舟 API Key")
    base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        description="火山方舟 API 基础 URL"
    )
    # Seedream 4.5 模型 (支持文生图和图文生图)
    model: str = Field(
        default="doubao-seedream-4-5-251128",
        description="Seedream 模型 ID"
    )
    # 图片尺寸 - 使用 16:9 视频画幅，需要至少 2k 分辨率
    image_size: str = Field(
        default="2560x1440",
        description="生成图片尺寸 (推荐 2560x1440 或 3840x2160)"
    )
    # 生成数量
    n: int = Field(default=1, description="每次生成图片数量")
    # 引导系数
    guidance_scale: float = Field(default=5.5, description="引导系数")
    # 是否添加水印
    watermark: bool = Field(default=False, description="是否添加水印")
    timeout_seconds: int = Field(default=120, description="API 请求超时时间")


class IndexTTSConfig(BaseSettings):
    """UCloud Modelverse IndexTTS API configuration."""
    
    model_config = SettingsConfigDict(env_prefix="INDEXTTS_", extra="ignore")
    
    api_key: str = Field(default="", description="Modelverse API key")
    base_url: str = Field(
        default="https://api.modelverse.cn",
        description="Modelverse API base URL"
    )
    model: str = Field(
        default="IndexTeam/IndexTTS-2",
        description="IndexTTS model name"
    )
    voice: str = Field(
        default="jack_cheng",
        description="Default voice ID"
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="Custom voice ID (uspeech:xxxx-xxxx-xxxx-xxxx)"
    )
    default_emotion: str = Field(
        default="平静",
        description="Default emotion text (喜/怒/哀/惧/厌恶/低落/惊喜/平静)"
    )
    emotion_weight: float = Field(
        default=0.6,
        description="Emotion control weight (0.0-1.0), recommended 0.6 for text emotion"
    )
    sample_rate: int = Field(default=24000, description="Audio sample rate")
    gain: float = Field(default=1.0, description="Output volume gain (0-10)")
    interval_silence: int = Field(default=200, description="Silence between sentences (ms)")
    max_text_tokens_per_sentence: int = Field(default=120, description="Max tokens per sentence")
    timeout_seconds: int = Field(default=60, description="API request timeout")


class SceneConfig(BaseSettings):
    """Scene and storyboard configuration."""
    
    model_config = SettingsConfigDict(env_prefix="SCENE_", extra="ignore")
    
    default_duration_seconds: int = Field(
        default=5,
        description="Default scene duration (5 or 10 seconds)"
    )
    max_scenes_per_project: int = Field(
        default=50,
        description="Maximum number of scenes per project"
    )

    image_width: int = Field(default=1024, description="Generated image width")
    image_height: int = Field(default=576, description="Generated image height (16:9)")


class StorageConfig(BaseSettings):
    """Storage and project management configuration."""
    
    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")
    
    base_dir: Path = Field(
        default=Path("./projects"),
        description="Base directory for project storage"
    )
    images_subdir: str = Field(default="images", description="Images subdirectory")
    audios_subdir: str = Field(default="audios", description="Audios subdirectory")
    prompts_subdir: str = Field(default="prompts", description="Video prompts subdirectory")
    subtitles_subdir: str = Field(default="subtitles", description="Subtitles subdirectory")
    export_subdir: str = Field(default="export", description="Export subdirectory")
    project_file: str = Field(default="project.json", description="Project state filename")
    
    # Legacy subdirectories for backward compatibility
    characters_subdir: str = Field(default="characters", description="Legacy characters subdirectory")
    clips_subdir: str = Field(default="clips", description="Legacy clips subdirectory")
    output_subdir: str = Field(default="output", description="Legacy output subdirectory")


class RetryConfig(BaseSettings):
    """Retry mechanism configuration."""
    
    model_config = SettingsConfigDict(env_prefix="RETRY_", extra="ignore")
    
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(default=5.0, description="Initial retry delay")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    max_delay_seconds: float = Field(default=60.0, description="Maximum delay between retries")


class WebConfig(BaseSettings):
    """Gradio Web interface configuration."""
    
    model_config = SettingsConfigDict(env_prefix="WEB_", extra="ignore")
    
    host: str = Field(default="0.0.0.0", description="Web server host")
    port: int = Field(default=7860, description="Web server port")
    share: bool = Field(default=False, description="Create public Gradio link")
    title: str = Field(default="教学视频素材生成器", description="Web interface title")


class Settings(BaseSettings):
    """Main application settings aggregating all configuration sections."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__"
    )
    
    # New configuration sections - load from env file
    dashscope: DashScopeConfig = Field(default_factory=lambda: DashScopeConfig(_env_file=".env"))
    volcengine: VolcEngineConfig = Field(default_factory=lambda: VolcEngineConfig(_env_file=".env"))
    indextts: IndexTTSConfig = Field(default_factory=lambda: IndexTTSConfig(_env_file=".env"))
    scene: SceneConfig = Field(default_factory=lambda: SceneConfig(_env_file=".env"))
    storage: StorageConfig = Field(default_factory=lambda: StorageConfig(_env_file=".env"))
    retry: RetryConfig = Field(default_factory=lambda: RetryConfig(_env_file=".env"))
    web: WebConfig = Field(default_factory=lambda: WebConfig(_env_file=".env"))
    
    # Legacy configuration sections (for backward compatibility)
    openai: OpenAIConfig = Field(default_factory=lambda: OpenAIConfig(_env_file=".env"))
    kling: KlingConfig = Field(default_factory=lambda: KlingConfig(_env_file=".env"))
    video: VideoConfig = Field(default_factory=lambda: VideoConfig(_env_file=".env"))
    
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Settings: The application settings.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment.
    
    Returns:
        Settings: The reloaded application settings.
    """
    global _settings
    _settings = Settings()
    return _settings
