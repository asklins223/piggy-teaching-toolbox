"""Scene image generation using 火山引擎方舟 Seedream API.

This module provides the SceneGenerator class for generating scene images.
Uses doubao-seedream-4-5-251128 model which supports both:
- Text-to-image (文生图)
- Image-text-to-image (图文生图) with character references

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
import aiohttp

from backend.schemas.models import Scene, SceneImage, ResourceStatus, CharacterReference
from backend.config import get_settings
from backend.core.exceptions import ImageGenerationError


logger = logging.getLogger(__name__)


def encode_image_to_base64(image_path: str) -> str:
    """Encode a local image file to base64 data URI."""
    with open(image_path, "rb") as f:
        image_data = f.read()
    base64_data = base64.b64encode(image_data).decode("utf-8")
    # 判断图片类型
    if image_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif image_path.lower().endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"
    else:
        mime_type = "image/png"
    return f"data:{mime_type};base64,{base64_data}"


class SceneGenerator:
    """Scene image generator using 火山引擎方舟 Seedream API.
    
    Uses doubao-seedream-4-5-251128 model for both:
    1. Text-to-image: When no character references provided
    2. Image-text-to-image: When character references provided,
       maintains character consistency across scenes
    
    Requirements: 2.1, 2.2, 2.3, 2.4
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the scene generator.
        
        Args:
            api_key: 火山方舟 API key. If None, will use config.
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.volcengine.api_key
        
        if not self.api_key:
            raise ValueError("火山方舟 API key is required (ARK_API_KEY)")
        
        self.base_url = self.settings.volcengine.base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_image(
        self, 
        scene: Scene,
        output_dir: Path,
        character_refs: Optional[Dict[str, CharacterReference]] = None,
        style_reference: Optional[str] = None
    ) -> SceneImage:
        """Generate image for a single scene.
        
        Args:
            scene: Scene to generate image for.
            output_dir: Directory to save the generated image.
            character_refs: Dict mapping character_id to CharacterReference.
            style_reference: Optional style reference image path.
            
        Returns:
            SceneImage: Generated scene image metadata.
            
        Raises:
            ImageGenerationError: If image generation fails.
        """
        logger.info(f"Generating image for scene {scene.scene_id}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        image_filename = f"{scene.scene_id}.png"
        image_path = output_dir / image_filename
        
        # 优先使用 image_prompt，如果没有则使用 description_cn
        prompt_to_use = scene.image_prompt if scene.image_prompt else scene.description_cn
        
        scene_image = SceneImage(
            scene_id=scene.scene_id,
            image_path=str(image_path),
            prompt_used=prompt_to_use,
            status=ResourceStatus.GENERATING,
            error_message=None
        )
        
        try:
            # 收集角色参考图
            ref_images = []
            char_names = []
            
            if character_refs and scene.character_ids:
                for char_id in scene.character_ids[:3]:  # 最多3张参考图
                    if char_id in character_refs:
                        ref = character_refs[char_id]
                        ref_images.append(ref.image_path)
                        char_names.append(ref.name)
            
            # 调用 API 生成图片
            image_data = await self._call_seedream_api(
                prompt=prompt_to_use,
                ref_images=ref_images,
                char_names=char_names
            )
            
            await self._save_image(image_data, image_path)
            
            scene_image.status = ResourceStatus.COMPLETED
            logger.info(f"Successfully generated image for scene {scene.scene_id}")
            return scene_image
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to generate image for scene {scene.scene_id}: {error_msg}")
            scene_image.status = ResourceStatus.FAILED
            scene_image.error_message = error_msg
            retryable = self._is_retryable_error(e)
            raise ImageGenerationError(scene.scene_id, error_msg, retryable)

    async def generate_images(
        self, 
        scenes: List[Scene],
        output_dir: Path,
        character_refs: Optional[Dict[str, CharacterReference]] = None,
        style_reference: Optional[str] = None,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[SceneImage]:
        """Generate images for multiple scenes."""
        logger.info(f"Generating images for {len(scenes)} scenes")
        
        results = []
        completed = 0
        
        for scene in scenes:
            try:
                scene_image = await self.generate_image(
                    scene, output_dir, character_refs, style_reference
                )
                results.append(scene_image)
                completed += 1
                
                if on_progress:
                    on_progress(completed, len(scenes))
                    
            except ImageGenerationError as e:
                prompt_to_use = scene.image_prompt if scene.image_prompt else scene.description_cn
                failed_image = SceneImage(
                    scene_id=scene.scene_id,
                    image_path=str(output_dir / f"{scene.scene_id}.png"),
                    prompt_used=prompt_to_use,
                    status=ResourceStatus.FAILED,
                    error_message=e.reason
                )
                results.append(failed_image)
                completed += 1
                
                if on_progress:
                    on_progress(completed, len(scenes))
                
                logger.warning(f"Scene {scene.scene_id} image generation failed: {e.reason}")
        
        logger.info(f"Completed image generation for {len(scenes)} scenes")
        return results
    
    async def regenerate_image(
        self, 
        scene: Scene,
        output_dir: Path,
        character_refs: Optional[Dict[str, CharacterReference]] = None,
        style_reference: Optional[str] = None
    ) -> SceneImage:
        """Regenerate image for a single scene."""
        logger.info(f"Regenerating image for scene {scene.scene_id}")
        
        image_path = output_dir / f"{scene.scene_id}.png"
        if image_path.exists():
            image_path.unlink()
        
        return await self.generate_image(scene, output_dir, character_refs, style_reference)
    
    async def _call_seedream_api(
        self, 
        prompt: str, 
        ref_images: List[str] = None,
        char_names: List[str] = None
    ) -> bytes:
        """Call Seedream API for image generation.
        
        Supports both text-to-image and image-text-to-image.
        
        Args:
            prompt: Text prompt for image generation.
            ref_images: Optional list of reference image paths.
            char_names: Optional list of character names for the references.
            
        Returns:
            bytes: Generated image data.
        """
        config = self.settings.volcengine
        
        # 构建最终 prompt - 完全依赖输入的提示词控制风格
        # 添加不要文字的要求
        no_text_suffix = "，画面中不要出现任何文字、字母、数字、标题、水印"
        
        if ref_images and char_names:
            # 图文生图：添加角色说明
            if len(char_names) == 1:
                char_desc = f"图中的角色是{char_names[0]}，保持角色外观与参考图一致"
            else:
                char_desc = f"图中的角色包括{'、'.join(char_names)}，保持每个角色外观与对应参考图一致"
            final_prompt = f"{prompt}。{char_desc}{no_text_suffix}。"
        else:
            # 纯文生图
            final_prompt = f"{prompt}{no_text_suffix}"
        
        # 构建请求体
        payload = {
            "model": config.model,
            "prompt": final_prompt,
            "size": config.image_size,
            "n": config.n,
            "guidance_scale": config.guidance_scale,
            "watermark": config.watermark
        }
        
        # 如果有参考图，添加到请求中
        if ref_images:
            image_urls = []
            for img_path in ref_images:
                if img_path.startswith(("http://", "https://")):
                    image_urls.append(img_path)
                else:
                    # 本地文件转 base64
                    image_urls.append(encode_image_to_base64(img_path))
            
            # 单图或多图
            if len(image_urls) == 1:
                payload["image"] = image_urls[0]
            else:
                payload["image"] = image_urls
        
        url = f"{self.base_url}/images/generations"
        
        print(f"\n[图片生成] 最终提示词: {final_prompt}")
        if ref_images:
            print(f"[图片生成] 参考图数量: {len(ref_images)}\n")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=config.timeout_seconds)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ImageGenerationError(
                            "unknown", 
                            f"Seedream API error {response.status}: {error_text}",
                            retryable=response.status >= 500
                        )
                    
                    result = await response.json()
                    return await self._extract_image_from_response(session, result)
                        
            except aiohttp.ClientError as e:
                raise ImageGenerationError(
                    "unknown",
                    f"Network error: {str(e)}",
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
            raise ImageGenerationError(
                "unknown",
                f"No image data in response: {result}",
                retryable=False
            )
        
        first_image = data[0]
        
        # 检查是否有 URL
        if "url" in first_image:
            return await self._download_image(session, first_image["url"])
        
        # 检查是否有 base64 数据
        if "b64_json" in first_image:
            return base64.b64decode(first_image["b64_json"])
        
        raise ImageGenerationError(
            "unknown",
            f"No image URL or base64 in response: {result}",
            retryable=False
        )
    
    async def _download_image(self, session: aiohttp.ClientSession, image_url: str) -> bytes:
        """Download image from URL."""
        async with session.get(image_url) as response:
            if response.status != 200:
                raise ImageGenerationError(
                    "unknown",
                    f"Failed to download image: HTTP {response.status}",
                    retryable=True
                )
            return await response.read()
    
    async def _save_image(self, image_data: bytes, image_path: Path) -> None:
        """Save image data to file."""
        try:
            with open(image_path, 'wb') as f:
                f.write(image_data)
        except IOError as e:
            raise ImageGenerationError(
                "unknown",
                f"Failed to save image to {image_path}: {str(e)}",
                retryable=False
            )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        if isinstance(error, ImageGenerationError):
            return error.retryable
        if isinstance(error, (aiohttp.ClientError, asyncio.TimeoutError)):
            return True
        if isinstance(error, (IOError, OSError)):
            return False
        return True
