"""
Retry mechanism for the video generation system.

This module provides a configurable retry decorator and utilities for
handling transient failures in API calls and other operations.

Requirements: 2.3, 3.4, 6.4
"""

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Type, TypeVar, Union

from .exceptions import (
    RetryExhaustedError,
    ImageGenerationError,
    AudioGenerationError,
    SubtitleGenerationError,
    ExportError,
    VideoGeneratorError,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay_seconds: Initial delay between retries in seconds (default: 5.0)
        exponential_backoff: Whether to use exponential backoff (default: True)
        max_delay_seconds: Maximum delay between retries (default: 60.0)
        retryable_exceptions: Tuple of exception types that should trigger a retry
    """
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    exponential_backoff: bool = True
    max_delay_seconds: float = 60.0
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    
    def get_delay(self, attempt: int) -> float:
        """Calculate the delay for a given retry attempt.
        
        Args:
            attempt: The current attempt number (0-indexed)
            
        Returns:
            The delay in seconds before the next retry
        """
        if self.exponential_backoff:
            delay = self.retry_delay_seconds * (2 ** attempt)
        else:
            delay = self.retry_delay_seconds
        
        return min(delay, self.max_delay_seconds)


def retry(
    config: Optional[RetryConfig] = None,
    *,
    max_retries: Optional[int] = None,
    retry_delay_seconds: Optional[float] = None,
    exponential_backoff: Optional[bool] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable:
    """Decorator for adding retry logic to synchronous functions.
    
    Can be used with a RetryConfig object or individual parameters.
    
    Args:
        config: A RetryConfig object with retry settings
        max_retries: Override max_retries from config
        retry_delay_seconds: Override retry_delay_seconds from config
        exponential_backoff: Override exponential_backoff from config
        retryable_exceptions: Override retryable_exceptions from config
        on_retry: Optional callback called before each retry with (attempt, exception)
        
    Returns:
        A decorator function
        
    Example:
        @retry(max_retries=3, retry_delay_seconds=1.0)
        def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    # Apply overrides
    effective_config = RetryConfig(
        max_retries=max_retries if max_retries is not None else config.max_retries,
        retry_delay_seconds=retry_delay_seconds if retry_delay_seconds is not None else config.retry_delay_seconds,
        exponential_backoff=exponential_backoff if exponential_backoff is not None else config.exponential_backoff,
        max_delay_seconds=config.max_delay_seconds,
        retryable_exceptions=retryable_exceptions if retryable_exceptions is not None else config.retryable_exceptions,
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(effective_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except effective_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < effective_config.max_retries:
                        delay = effective_config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{effective_config.max_retries + 1} "
                            f"failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {effective_config.max_retries + 1} attempts "
                            f"failed for {func.__name__}: {e}"
                        )
            
            raise RetryExhaustedError(
                operation=func.__name__,
                max_retries=effective_config.max_retries,
                last_error=last_exception
            )
        
        return wrapper
    
    return decorator


def async_retry(
    config: Optional[RetryConfig] = None,
    *,
    max_retries: Optional[int] = None,
    retry_delay_seconds: Optional[float] = None,
    exponential_backoff: Optional[bool] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable:
    """Decorator for adding retry logic to async functions.
    
    Can be used with a RetryConfig object or individual parameters.
    
    Args:
        config: A RetryConfig object with retry settings
        max_retries: Override max_retries from config
        retry_delay_seconds: Override retry_delay_seconds from config
        exponential_backoff: Override exponential_backoff from config
        retryable_exceptions: Override retryable_exceptions from config
        on_retry: Optional callback called before each retry with (attempt, exception)
        
    Returns:
        A decorator function
        
    Example:
        @async_retry(max_retries=3, retry_delay_seconds=1.0)
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    # Apply overrides
    effective_config = RetryConfig(
        max_retries=max_retries if max_retries is not None else config.max_retries,
        retry_delay_seconds=retry_delay_seconds if retry_delay_seconds is not None else config.retry_delay_seconds,
        exponential_backoff=exponential_backoff if exponential_backoff is not None else config.exponential_backoff,
        max_delay_seconds=config.max_delay_seconds,
        retryable_exceptions=retryable_exceptions if retryable_exceptions is not None else config.retryable_exceptions,
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(effective_config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except effective_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < effective_config.max_retries:
                        delay = effective_config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{effective_config.max_retries + 1} "
                            f"failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {effective_config.max_retries + 1} attempts "
                            f"failed for {func.__name__}: {e}"
                        )
            
            raise RetryExhaustedError(
                operation=func.__name__,
                max_retries=effective_config.max_retries,
                last_error=last_exception
            )
        
        return wrapper
    
    return decorator


async def retry_async_operation(
    operation: Callable[..., T],
    config: RetryConfig,
    *args,
    operation_name: Optional[str] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs
) -> T:
    """Execute an async operation with retry logic.
    
    This is a utility function for cases where you can't use the decorator.
    
    Args:
        operation: The async function to execute
        config: Retry configuration
        *args: Positional arguments to pass to the operation
        operation_name: Name for logging (defaults to function name)
        on_retry: Optional callback called before each retry
        **kwargs: Keyword arguments to pass to the operation
        
    Returns:
        The result of the operation
        
    Raises:
        RetryExhaustedError: If all retry attempts fail
    """
    name = operation_name or getattr(operation, '__name__', 'unknown')
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await operation(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries + 1} "
                    f"failed for {name}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                if on_retry:
                    on_retry(attempt, e)
                
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_retries + 1} attempts "
                    f"failed for {name}: {e}"
                )
    
    raise RetryExhaustedError(
        operation=name,
        max_retries=config.max_retries,
        last_error=last_exception
    )


def retry_sync_operation(
    operation: Callable[..., T],
    config: RetryConfig,
    *args,
    operation_name: Optional[str] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs
) -> T:
    """Execute a synchronous operation with retry logic.
    
    This is a utility function for cases where you can't use the decorator.
    
    Args:
        operation: The function to execute
        config: Retry configuration
        *args: Positional arguments to pass to the operation
        operation_name: Name for logging (defaults to function name)
        on_retry: Optional callback called before each retry
        **kwargs: Keyword arguments to pass to the operation
        
    Returns:
        The result of the operation
        
    Raises:
        RetryExhaustedError: If all retry attempts fail
    """
    import time
    
    name = operation_name or getattr(operation, '__name__', 'unknown')
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return operation(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries + 1} "
                    f"failed for {name}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                if on_retry:
                    on_retry(attempt, e)
                
                time.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_retries + 1} attempts "
                    f"failed for {name}: {e}"
                )
    
    raise RetryExhaustedError(
        operation=name,
        max_retries=config.max_retries,
        last_error=last_exception
    )


# =============================================================================
# Component-Specific Retry Configurations
# =============================================================================

def get_image_generation_retry_config() -> RetryConfig:
    """Get retry configuration for image generation operations.
    
    Returns:
        RetryConfig: Configuration optimized for image generation.
        
    Requirements: 2.3
    """
    return RetryConfig(
        max_retries=3,
        retry_delay_seconds=5.0,
        exponential_backoff=True,
        max_delay_seconds=60.0,
        retryable_exceptions=(ImageGenerationError, ConnectionError, TimeoutError)
    )


def get_audio_generation_retry_config() -> RetryConfig:
    """Get retry configuration for audio generation operations.
    
    Returns:
        RetryConfig: Configuration optimized for audio generation.
        
    Requirements: 3.4
    """
    return RetryConfig(
        max_retries=3,
        retry_delay_seconds=2.0,
        exponential_backoff=True,
        max_delay_seconds=30.0,
        retryable_exceptions=(AudioGenerationError, ConnectionError, TimeoutError)
    )


def get_subtitle_generation_retry_config() -> RetryConfig:
    """Get retry configuration for subtitle generation operations.
    
    Returns:
        RetryConfig: Configuration optimized for subtitle generation.
    """
    return RetryConfig(
        max_retries=3,
        retry_delay_seconds=2.0,
        exponential_backoff=True,
        max_delay_seconds=30.0,
        retryable_exceptions=(SubtitleGenerationError, ConnectionError, TimeoutError)
    )


def get_export_retry_config() -> RetryConfig:
    """Get retry configuration for export operations.
    
    Returns:
        RetryConfig: Configuration optimized for export operations.
        
    Requirements: 6.4
    """
    return RetryConfig(
        max_retries=2,
        retry_delay_seconds=1.0,
        exponential_backoff=False,
        max_delay_seconds=10.0,
        retryable_exceptions=(ExportError, IOError, OSError)
    )


def get_api_retry_config() -> RetryConfig:
    """Get retry configuration for API calls (DashScope, etc.).
    
    Returns:
        RetryConfig: Configuration optimized for API calls.
    """
    return RetryConfig(
        max_retries=3,
        retry_delay_seconds=5.0,
        exponential_backoff=True,
        max_delay_seconds=60.0,
        retryable_exceptions=(ConnectionError, TimeoutError, VideoGeneratorError)
    )


def is_retryable(error: Exception) -> bool:
    """Check if an error is retryable based on its type and attributes.
    
    Args:
        error: The exception to check.
        
    Returns:
        bool: True if the error should be retried.
    """
    # Check for retryable attribute on custom exceptions
    if hasattr(error, 'retryable'):
        return error.retryable
    
    # Network errors are generally retryable
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    
    # File I/O errors are generally not retryable
    if isinstance(error, (IOError, OSError)):
        return False
    
    # Check for specific error messages that indicate retryable conditions
    error_str = str(error).lower()
    retryable_patterns = [
        'timeout',
        'connection',
        'rate limit',
        'too many requests',
        'service unavailable',
        'internal server error',
        'bad gateway',
        'gateway timeout',
    ]
    
    for pattern in retryable_patterns:
        if pattern in error_str:
            return True
    
    # Default to not retryable for unknown errors
    return False


async def retry_with_fallback(
    primary_operation: Callable[..., T],
    fallback_operation: Callable[..., T],
    config: RetryConfig,
    *args,
    operation_name: Optional[str] = None,
    **kwargs
) -> T:
    """Execute an operation with retry logic and fallback.
    
    First tries the primary operation with retries. If all retries fail,
    attempts the fallback operation once.
    
    Args:
        primary_operation: The primary async function to execute.
        fallback_operation: The fallback async function if primary fails.
        config: Retry configuration for the primary operation.
        *args: Positional arguments to pass to both operations.
        operation_name: Name for logging.
        **kwargs: Keyword arguments to pass to both operations.
        
    Returns:
        The result of either the primary or fallback operation.
        
    Raises:
        RetryExhaustedError: If both primary and fallback operations fail.
    """
    name = operation_name or getattr(primary_operation, '__name__', 'unknown')
    
    try:
        return await retry_async_operation(
            primary_operation,
            config,
            *args,
            operation_name=name,
            **kwargs
        )
    except RetryExhaustedError as primary_error:
        logger.warning(
            f"Primary operation '{name}' failed after retries. "
            f"Attempting fallback..."
        )
        
        try:
            return await fallback_operation(*args, **kwargs)
        except Exception as fallback_error:
            logger.error(
                f"Fallback operation for '{name}' also failed: {fallback_error}"
            )
            # Re-raise the original error with fallback info
            raise RetryExhaustedError(
                operation=f"{name} (with fallback)",
                max_retries=config.max_retries,
                last_error=fallback_error
            )
