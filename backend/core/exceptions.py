"""
Custom exception classes for the video generation system.

This module defines a hierarchy of exceptions for handling various error
conditions that can occur during the video generation workflow.

Requirements: 2.3, 3.4, 6.4
"""

from typing import Optional


class VideoGeneratorError(Exception):
    """素材生成相关错误的基类 (Base class for video generator errors)"""
    
    def __init__(self, message: str = "Video generator error occurred"):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return self.message


# Keep the old name as an alias for backward compatibility
VideoGenerationError = VideoGeneratorError


class CharacterGenerationError(VideoGeneratorError):
    """角色图片生成失败 (Character image generation failed)
    
    Raised when character reference image generation fails.
    Requirements: 1.4
    """
    
    def __init__(self, character_name: str, reason: str):
        self.character_name = character_name
        self.reason = reason
        message = f"Failed to generate character '{character_name}': {reason}"
        super().__init__(message)


class ScriptPlanningError(VideoGeneratorError):
    """分镜脚本生成失败 (Script/storyboard planning failed)
    
    Raised when the LLM fails to generate or parse the storyboard.
    """
    
    def __init__(self, step: str, reason: str):
        self.step = step
        self.reason = reason
        message = f"Script planning failed at step '{step}': {reason}"
        super().__init__(message)


class ImageGenerationError(VideoGeneratorError):
    """图片生成失败 (Image generation failed)
    
    Raised when a scene image fails to generate.
    Requirements: 2.3
    
    Attributes:
        scene_id: The ID of the scene that failed to generate
        reason: The reason for the failure
        retryable: Whether the operation can be retried
    """
    
    def __init__(self, scene_id: str, reason: str, retryable: bool = True):
        self.scene_id = scene_id
        self.reason = reason
        self.retryable = retryable
        retry_info = " (retryable)" if retryable else " (not retryable)"
        message = f"Failed to generate image for scene '{scene_id}': {reason}{retry_info}"
        super().__init__(message)


class ClipGenerationError(VideoGeneratorError):
    """视频片段生成失败 (Video clip generation failed)
    
    Raised when a video clip fails to generate.
    Requirements: 3.4
    
    Attributes:
        scene_id: The ID of the scene that failed to generate
        reason: The reason for the failure
        retryable: Whether the operation can be retried
    """
    
    def __init__(self, scene_id: str, reason: str, retryable: bool = True):
        self.scene_id = scene_id
        self.reason = reason
        self.retryable = retryable
        retry_info = " (retryable)" if retryable else " (not retryable)"
        message = f"Failed to generate clip for scene '{scene_id}': {reason}{retry_info}"
        super().__init__(message)


class AudioGenerationError(VideoGeneratorError):
    """音频生成失败 (Audio generation failed)
    
    Raised when audio generation fails.
    Requirements: 3.4
    
    Attributes:
        scene_id: The ID of the scene that failed to generate audio
        reason: The reason for the failure
        retryable: Whether the operation can be retried
    """
    
    def __init__(self, scene_id: str, reason: str, retryable: bool = True):
        self.scene_id = scene_id
        self.reason = reason
        self.retryable = retryable
        retry_info = " (retryable)" if retryable else " (not retryable)"
        message = f"Failed to generate audio for scene '{scene_id}': {reason}{retry_info}"
        super().__init__(message)


class SubtitleGenerationError(VideoGeneratorError):
    """字幕生成失败 (Subtitle generation failed)
    
    Raised when subtitle generation fails.
    
    Attributes:
        scene_id: The ID of the scene that failed to generate subtitles
        reason: The reason for the failure
    """
    
    def __init__(self, scene_id: str, reason: str):
        self.scene_id = scene_id
        self.reason = reason
        message = f"Failed to generate subtitle for scene '{scene_id}': {reason}"
        super().__init__(message)


class CompositionError(VideoGeneratorError):
    """视频合成失败 (Video composition failed)
    
    Raised when video composition fails.
    
    Attributes:
        reason: The reason for the failure
        partial_output: Path to any partial output that was created before failure
    """
    
    def __init__(self, reason: str, partial_output: Optional[str] = None):
        self.reason = reason
        self.partial_output = partial_output
        partial_info = f" (partial output at: {partial_output})" if partial_output else ""
        message = f"Video composition failed: {reason}{partial_info}"
        super().__init__(message)


class ExportError(VideoGeneratorError):
    """导出失败 (Export failed)
    
    Raised when asset export fails.
    Requirements: 6.4
    
    Attributes:
        reason: The reason for the failure
        partial_output: Path to any partial output that was created before failure
    """
    
    def __init__(self, reason: str, partial_output: Optional[str] = None):
        self.reason = reason
        self.partial_output = partial_output
        partial_info = f" (partial output at: {partial_output})" if partial_output else ""
        message = f"Export failed: {reason}{partial_info}"
        super().__init__(message)


class ProjectStateError(VideoGeneratorError):
    """项目状态错误 (Project state error)
    
    Raised when there's an issue with project state management.
    
    Attributes:
        project_id: The ID of the project with the state error
        reason: The reason for the error
    """
    
    def __init__(self, project_id: str, reason: str):
        self.project_id = project_id
        self.reason = reason
        message = f"Project state error for '{project_id}': {reason}"
        super().__init__(message)


class StorageError(VideoGeneratorError):
    """存储错误 (Storage error)
    
    Raised when there's an issue with file storage operations.
    
    Attributes:
        path: The path that caused the error
        reason: The reason for the error
    """
    
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        message = f"Storage error at '{path}': {reason}"
        super().__init__(message)


class RetryExhaustedError(VideoGeneratorError):
    """重试次数耗尽 (Retry attempts exhausted)
    
    Raised when all retry attempts have been exhausted.
    Requirements: 2.3, 3.4, 6.4
    
    Attributes:
        operation: The operation that failed
        max_retries: The maximum number of retries attempted
        last_error: The last error that occurred
    """
    
    def __init__(self, operation: str, max_retries: int, last_error: Optional[Exception] = None):
        self.operation = operation
        self.max_retries = max_retries
        self.last_error = last_error
        last_error_info = f" Last error: {last_error}" if last_error else ""
        message = f"Operation '{operation}' failed after {max_retries} retries.{last_error_info}"
        super().__init__(message)
