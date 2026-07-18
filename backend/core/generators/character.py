"""Character generation module using 火山引擎方舟 Seedream API.

This module provides the CharacterGenerator class for generating character
reference images using Volcengine Seedream model (doubao-seedream-4-5-251128).

Requirements: 1.1, 1.2, 1.3, 1.4
"""

import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Callable, Optional, Protocol

import aiohttp

from backend.config import get_settings
from backend.schemas.models import CharacterConfig, CharacterReference


logger = logging.getLogger(__name__)


class CharacterGenerationError(Exception):
    """Raised when character image generation fails.
    
    Requirements: 1.4
    """
    def __init__(self, character_name: str, reason: str, retryable: bool = True):
        self.character_name = character_name
        self.reason = reason
        self.retryable = retryable
        super().__init__(f"Failed to generate character '{character_name}': {reason}")


class ImageGeneratorProtocol(Protocol):
    """Protocol for image generation backends."""
    
    async def generate_image(
        self, 
        prompt: str, 
        size: str = "1024*1024"
    ) -> bytes:
        """Generate an image from a prompt."""
        ...


class VolcengineImageGenerator:
    """火山引擎方舟 Seedream image generator implementation."""
    
    def __init__(self):
        """Initialize the Volcengine image generator."""
        self._settings = get_settings()
        self._config = self._settings.volcengine
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            )
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def generate_image(
        self, 
        prompt: str, 
        size: str = "1024*1024"
    ) -> bytes:
        """Generate an image using Volcengine Seedream API.
        
        Args:
            prompt: Text description for image generation.
            size: Image size in "width*height" format.
            
        Returns:
            Image data as bytes.
            
        Raises:
            CharacterGenerationError: If API call fails.
        """
        if not self._config.api_key:
            raise CharacterGenerationError(
                character_name="unknown",
                reason="火山方舟 API key not configured (ARK_API_KEY)",
                retryable=False
            )
        
        session = await self._get_session()
        
        # 构建请求体
        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "guidance_scale": self._config.guidance_scale,
            "watermark": self._config.watermark
        }
        
        url = f"{self._config.base_url}/images/generations"
        
        print(f"\n[角色图片生成-豆包] 最终提示词: {prompt}")
        print(f"[角色图片生成-豆包] 尺寸: {size}\n")
        
        try:
            async with session.post(
                url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise CharacterGenerationError(
                        character_name="unknown",
                        reason=f"API error ({response.status}): {error_text}",
                        retryable=response.status >= 500
                    )
                
                result = await response.json()
                return await self._extract_image_from_response(session, result)
                
        except aiohttp.ClientError as e:
            raise CharacterGenerationError(
                character_name="unknown",
                reason=f"Network error: {str(e)}",
                retryable=True
            )
    
    async def _extract_image_from_response(
        self, 
        session: aiohttp.ClientSession, 
        result: dict
    ) -> bytes:
        """Extract image data from API response."""
        data = result.get("data", [])
        if not data:
            raise CharacterGenerationError(
                character_name="unknown",
                reason=f"No image data in response: {result}",
                retryable=False
            )
        
        first_image = data[0]
        
        # 优先使用 base64
        if "b64_json" in first_image:
            return base64.b64decode(first_image["b64_json"])
        
        # 否则下载 URL
        if "url" in first_image:
            return await self._download_image(session, first_image["url"])
        
        raise CharacterGenerationError(
            character_name="unknown",
            reason=f"No image URL or base64 in response: {first_image}",
            retryable=False
        )
    
    async def _download_image(self, session: aiohttp.ClientSession, image_url: str) -> bytes:
        """Download image from URL."""
        async with session.get(image_url) as response:
            if response.status != 200:
                raise CharacterGenerationError(
                    character_name="unknown",
                    reason=f"Failed to download image: HTTP {response.status}",
                    retryable=True
                )
            return await response.read()


class CharacterGenerator:
    """Generates character reference images for video production.
    
    Uses Volcengine Seedream model to generate consistent character images
    that can be used as references for scene generation.
    
    Requirements: 1.1, 1.2, 1.3, 1.4
    """
    
    def __init__(
        self, 
        output_dir: str,
        image_generator: Optional[ImageGeneratorProtocol] = None
    ):
        """Initialize the CharacterGenerator.
        
        Args:
            output_dir: Directory to save generated character images.
            image_generator: Image generation backend. Uses Volcengine if None.
        """
        self._output_dir = Path(output_dir)
        self._image_generator = image_generator or VolcengineImageGenerator()
    
    def _generate_character_id(self) -> str:
        """Generate a unique character ID."""
        return f"char_{uuid.uuid4().hex[:8]}"
    
    def _build_prompt(self, config: CharacterConfig) -> str:
        """Build an image generation prompt from character config."""
        # 添加不要文字的要求
        base_prompt = config.description
        no_text_suffix = "，画面中不要出现任何文字、字母、数字、标题、水印"
        return f"{base_prompt}{no_text_suffix}"
    
    async def generate_character(
        self, 
        config: CharacterConfig,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> CharacterReference:
        """Generate a single character reference image.
        
        Args:
            config: Character configuration with name and description.
            on_progress: Optional callback for progress updates.
            
        Returns:
            CharacterReference: Generated character reference.
            
        Raises:
            CharacterGenerationError: If image generation fails.
        """
        character_id = self._generate_character_id()
        
        if on_progress:
            on_progress(f"Generating character: {config.name}")
        
        prompt = self._build_prompt(config)
        print(f"\n[角色生成] 角色名: {config.name}")
        print(f"[角色生成] 最终提示词: {prompt}\n")
        
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 使用 2k 尺寸，适合角色参考图
            image_data = await self._image_generator.generate_image(prompt, size="2k")
            
            filename = f"{character_id}.png"
            image_path = self._output_dir / filename
            image_path.write_bytes(image_data)
            
            if on_progress:
                on_progress(f"Character '{config.name}' saved to {image_path}")
            
            logger.info(f"Character '{config.name}' generated successfully: {image_path}")
            
            return CharacterReference(
                character_id=character_id,
                name=config.name,
                image_path=str(image_path),
                image_url=None
            )
            
        except CharacterGenerationError:
            raise
        except Exception as e:
            raise CharacterGenerationError(
                character_name=config.name,
                reason=str(e),
                retryable=True
            )
    
    async def generate_characters(
        self, 
        configs: list[CharacterConfig],
        on_progress: Optional[Callable[[str, int, int], None]] = None
    ) -> list[CharacterReference]:
        """Generate multiple character reference images.
        
        Args:
            configs: List of character configurations.
            on_progress: Optional callback (message, current, total).
            
        Returns:
            List of CharacterReference objects.
        """
        results = []
        total = len(configs)
        
        for i, config in enumerate(configs, 1):
            try:
                def progress_wrapper(msg: str):
                    if on_progress:
                        on_progress(msg, i, total)
                
                ref = await self.generate_character(config, progress_wrapper)
                results.append(ref)
                
            except CharacterGenerationError as e:
                logger.error(f"Failed to generate character '{config.name}': {e.reason}")
                if on_progress:
                    on_progress(f"Failed: {config.name} - {e.reason}", i, total)
                raise
        
        return results
    
    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self._image_generator, 'close'):
            await self._image_generator.close()
