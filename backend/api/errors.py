"""Unified error handling for the API.

This module provides standardized error responses and exception handlers
for the FastAPI application.

Requirements: 6
"""

from typing import Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.core.exceptions import (
    VideoGeneratorError,
    CharacterGenerationError,
    ScriptPlanningError,
    ImageGenerationError,
    AudioGenerationError,
    SubtitleGenerationError,
    ExportError,
    ProjectStateError,
    StorageError,
    RetryExhaustedError,
)
from backend.services.storage import ProjectNotFoundError


class ErrorDetail(BaseModel):
    """Standard error detail model."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: ErrorDetail


# Error code mapping
ERROR_CODES = {
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "PROJECT_NOT_FOUND": 404,
    "SCENE_NOT_FOUND": 404,
    "CHARACTER_NOT_FOUND": 404,
    "TASK_NOT_FOUND": 404,
    "RESOURCE_NOT_FOUND": 404,
    "INVALID_REQUEST": 400,
    "VALIDATION_ERROR": 422,
    "GENERATION_FAILED": 500,
    "AI_ERROR": 500,
    "EXPORT_FAILED": 500,
    "STORAGE_ERROR": 500,
    "INTERNAL_ERROR": 500,
}


def create_error_response(code: str, message: str, status_code: Optional[int] = None) -> JSONResponse:
    """Create a standardized error response.
    
    Args:
        code: Error code (e.g., "PROJECT_NOT_FOUND")
        message: Human-readable error message
        status_code: HTTP status code (auto-determined from code if not provided)
        
    Returns:
        JSONResponse with standardized error format
    """
    if status_code is None:
        status_code = ERROR_CODES.get(code, 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )


def raise_http_error(code: str, message: str, status_code: Optional[int] = None) -> None:
    """Raise an HTTPException with standardized error format.
    
    Args:
        code: Error code (e.g., "PROJECT_NOT_FOUND")
        message: Human-readable error message
        status_code: HTTP status code (auto-determined from code if not provided)
        
    Raises:
        HTTPException with standardized detail format
    """
    if status_code is None:
        status_code = ERROR_CODES.get(code, 500)
    
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message}
    )


async def video_generator_error_handler(request: Request, exc: VideoGeneratorError) -> JSONResponse:
    """Handle VideoGeneratorError exceptions.
    
    Args:
        request: The incoming request
        exc: The VideoGeneratorError exception
        
    Returns:
        Standardized error response
    """
    # Map specific exception types to error codes
    if isinstance(exc, CharacterGenerationError):
        return create_error_response(
            "CHARACTER_GENERATION_FAILED",
            f"角色生成失败: {exc.reason}",
            500
        )
    elif isinstance(exc, ScriptPlanningError):
        return create_error_response(
            "SCRIPT_PLANNING_FAILED",
            f"分镜脚本生成失败: {exc.reason}",
            500
        )
    elif isinstance(exc, ImageGenerationError):
        return create_error_response(
            "IMAGE_GENERATION_FAILED",
            f"图片生成失败: {exc.reason}",
            500
        )
    elif isinstance(exc, AudioGenerationError):
        return create_error_response(
            "AUDIO_GENERATION_FAILED",
            f"音频生成失败: {exc.reason}",
            500
        )
    elif isinstance(exc, SubtitleGenerationError):
        return create_error_response(
            "SUBTITLE_GENERATION_FAILED",
            f"字幕生成失败: {exc.reason}",
            500
        )
    elif isinstance(exc, ExportError):
        return create_error_response(
            "EXPORT_FAILED",
            f"导出失败: {exc.reason}",
            500
        )
    elif isinstance(exc, ProjectStateError):
        return create_error_response(
            "PROJECT_STATE_ERROR",
            f"项目状态错误: {exc.reason}",
            400
        )
    elif isinstance(exc, StorageError):
        return create_error_response(
            "STORAGE_ERROR",
            f"存储错误: {exc.reason}",
            500
        )
    elif isinstance(exc, RetryExhaustedError):
        return create_error_response(
            "RETRY_EXHAUSTED",
            f"操作重试次数已耗尽: {exc.operation}",
            500
        )
    else:
        return create_error_response(
            "GENERATION_FAILED",
            str(exc),
            500
        )


async def project_not_found_handler(request: Request, exc: ProjectNotFoundError) -> JSONResponse:
    """Handle ProjectNotFoundError exceptions.
    
    Args:
        request: The incoming request
        exc: The ProjectNotFoundError exception
        
    Returns:
        Standardized error response
    """
    return create_error_response(
        "PROJECT_NOT_FOUND",
        str(exc),
        404
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with standardized format.
    
    Args:
        request: The incoming request
        exc: The HTTPException
        
    Returns:
        Standardized error response
    """
    # If detail is already in our format, use it
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    
    # Otherwise, create a generic error response
    code = "INTERNAL_ERROR"
    if exc.status_code == 400:
        code = "INVALID_REQUEST"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "RESOURCE_NOT_FOUND"
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"
    
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation errors with standardized format.
    
    Args:
        request: The incoming request
        exc: The validation exception
        
    Returns:
        Standardized error response
    """
    from fastapi.exceptions import RequestValidationError
    
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        # Format validation errors into a readable message
        messages = []
        for error in errors:
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            msg = error.get("msg", "验证错误")
            messages.append(f"{loc}: {msg}")
        
        return create_error_response(
            "VALIDATION_ERROR",
            "; ".join(messages),
            422
        )
    
    return create_error_response(
        "VALIDATION_ERROR",
        str(exc),
        422
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standardized format.
    
    Args:
        request: The incoming request
        exc: The exception
        
    Returns:
        Standardized error response
    """
    # Log the error for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.exception(f"Unexpected error: {exc}")
    
    return create_error_response(
        "INTERNAL_ERROR",
        "服务器内部错误，请稍后重试",
        500
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.
    
    Args:
        app: The FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError
    
    # Register custom exception handlers
    app.add_exception_handler(VideoGeneratorError, video_generator_error_handler)
    app.add_exception_handler(ProjectNotFoundError, project_not_found_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Catch-all for unexpected exceptions (only in production)
    # In development, let errors propagate for better debugging
    import os
    if os.getenv("ENVIRONMENT", "development") == "production":
        app.add_exception_handler(Exception, generic_exception_handler)
