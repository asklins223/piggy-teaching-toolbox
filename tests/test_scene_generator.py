"""Property-based tests for SceneGenerator.

This module contains property-based tests using Hypothesis to verify
the correctness of scene image generation, particularly focusing on
quantity consistency and file path validity.

Feature: langchain-video-generator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil
from hypothesis import given, settings, strategies as st

from backend.schemas.models import (
    Scene,
    SceneImage,
    SceneDuration,
    Emotion,
    ResourceStatus,
)
from backend.core.generators.scene import SceneGenerator, ImageGenerationError


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def non_empty_text(min_size=1, max_size=200):
    """Generate text that is non-empty after stripping whitespace.
    
    Ensures at least one non-whitespace character is present.
    """
    # Generate text with at least one letter/number, then optionally add more
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            whitelist_categories=('L', 'N'),  # Letters and numbers only for prefix
        )),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))
    )


def non_empty_english_text(min_size=1, max_size=200):
    """Generate English text that is non-empty after stripping whitespace.
    
    Ensures at least one non-whitespace ASCII character is present.
    """
    # Generate text with at least one ASCII letter/number, then optionally add more
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            min_codepoint=48, max_codepoint=122  # ASCII letters and numbers
        ).filter(lambda c: c.isalnum())),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            min_codepoint=32, max_codepoint=126  # ASCII printable characters
        ))
    )


@st.composite
def scene_strategy(draw):
    """Generate a valid Scene with duration of 5 or 10 seconds."""
    return Scene(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_-'
        ))),
        step_number=draw(st.integers(min_value=1, max_value=100)),
        description_cn=draw(non_empty_text(min_size=1, max_size=200)),
        
        narration_cn=draw(non_empty_text(min_size=1, max_size=200)),
        narration_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        duration=draw(st.sampled_from(SceneDuration)),
        emotion=draw(st.sampled_from(Emotion))
    )


@st.composite
def scene_list_strategy(draw):
    """Generate a list of valid scenes."""
    return draw(st.lists(scene_strategy(), min_size=1, max_size=10))


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestImageGenerationQuantityConsistency:
    """Property-based tests for image generation quantity consistency.
    
    Feature: langchain-video-generator, Property 4: 图片生成数量一致性
    Validates: Requirements 2.1
    """

    @given(scenes=scene_list_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_image_generation_quantity_consistency(self, scenes):
        """For any scene list, generate_images should return same number of SceneImages.
        
        Property 4: 图片生成数量一致性
        Validates: Requirements 2.1
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock the SceneGenerator to avoid actual API calls
            generator = SceneGenerator(api_key="test_key")
            
            # Mock the API call to return successful results
            mock_image_data = b"fake_image_data"
            
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                with patch.object(generator, '_save_image', new_callable=AsyncMock) as mock_save:
                    mock_api.return_value = mock_image_data
                    mock_save.return_value = None
                    
                    # Generate images
                    results = await generator.generate_images(scenes, output_dir)
                    
                    # Verify quantity consistency
                    assert len(results) == len(scenes), (
                        f"Expected {len(scenes)} SceneImages, got {len(results)}"
                    )
                    
                    # Verify each scene has a corresponding result
                    scene_ids = {scene.scene_id for scene in scenes}
                    result_scene_ids = {result.scene_id for result in results}
                    
                    assert scene_ids == result_scene_ids, (
                        f"Scene IDs mismatch. Expected: {scene_ids}, Got: {result_scene_ids}"
                    )


class TestImageFilePathValidity:
    """Property-based tests for image file path validity.
    
    Feature: langchain-video-generator, Property 5: 图片文件路径有效性
    Validates: Requirements 2.2
    """

    @given(scenes=scene_list_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_image_file_path_validity(self, scenes):
        """For any successfully generated SceneImage, the image_path should point to an existing file.
        
        Property 5: 图片文件路径有效性
        Validates: Requirements 2.2
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock the SceneGenerator to avoid actual API calls
            generator = SceneGenerator(api_key="test_key")
            
            # Mock the API call to return successful results
            mock_image_data = b"fake_image_data"
            
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                mock_api.return_value = mock_image_data
                
                # Generate images
                results = await generator.generate_images(scenes, output_dir)
                
                # Check file path validity for completed images
                for result in results:
                    if result.status == ResourceStatus.COMPLETED:
                        image_path = Path(result.image_path)
                        
                        # Verify the file exists
                        assert image_path.exists(), (
                            f"Image file does not exist at path: {result.image_path}"
                        )
                        
                        # Verify it's a file (not a directory)
                        assert image_path.is_file(), (
                            f"Path is not a file: {result.image_path}"
                        )
                        
                        # Verify the file has content
                        assert image_path.stat().st_size > 0, (
                            f"Image file is empty: {result.image_path}"
                        )


# =============================================================================
# Unit Tests for Error Handling
# =============================================================================

class TestImageGenerationErrorHandling:
    """Unit tests for image generation error handling.
    
    Tests API error conditions and retry behavior.
    Requirements: 2.3
    """

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test that API errors are properly handled and reported."""
        scene = Scene(
            scene_id="test_scene",
            step_number=1,
            description_cn="测试场景",
            
            narration_cn="测试旁白",
            narration_en="test narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = SceneGenerator(api_key="test_key")
            
            # Mock API to raise an exception
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                mock_api.side_effect = Exception("API Error")
                
                # Should raise ImageGenerationError
                with pytest.raises(ImageGenerationError) as exc_info:
                    await generator.generate_image(scene, output_dir)
                
                assert exc_info.value.scene_id == "test_scene"
                assert "API Error" in exc_info.value.reason
                assert exc_info.value.retryable is True  # Default for unknown errors

    @pytest.mark.asyncio
    async def test_network_error_retryable(self):
        """Test that network errors are marked as retryable."""
        scene = Scene(
            scene_id="test_scene",
            step_number=1,
            description_cn="测试场景",
            
            narration_cn="测试旁白",
            narration_en="test narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = SceneGenerator(api_key="test_key")
            
            # Mock API to raise a network error
            import aiohttp
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                mock_api.side_effect = aiohttp.ClientError("Network error")
                
                # Should raise ImageGenerationError with retryable=True
                with pytest.raises(ImageGenerationError) as exc_info:
                    await generator.generate_image(scene, output_dir)
                
                assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_file_io_error_not_retryable(self):
        """Test that file I/O errors are marked as not retryable."""
        scene = Scene(
            scene_id="test_scene",
            step_number=1,
            description_cn="测试场景",
            
            narration_cn="测试旁白",
            narration_en="test narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = SceneGenerator(api_key="test_key")
            
            # Mock successful API call but failing file save
            mock_image_data = b"fake_image_data"
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                with patch.object(generator, '_save_image', new_callable=AsyncMock) as mock_save:
                    mock_api.return_value = mock_image_data
                    mock_save.side_effect = IOError("Permission denied")
                    
                    # Should raise ImageGenerationError with retryable=False
                    with pytest.raises(ImageGenerationError) as exc_info:
                        await generator.generate_image(scene, output_dir)
                    
                    assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_partial_failure_in_batch_generation(self):
        """Test that batch generation continues even when some scenes fail."""
        scenes = [
            Scene(
                scene_id="success_scene",
                step_number=1,
                description_cn="success 成功场景",
                narration_cn="成功旁白",
                narration_en="success narration",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            ),
            Scene(
                scene_id="failure_scene",
                step_number=2,
                description_cn="failure 失败场景",
                narration_cn="失败旁白",
                narration_en="failure narration",
                duration=SceneDuration.LONG,
                emotion=Emotion.HAPPY
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = SceneGenerator(api_key="test_key")
            
            # Mock API to succeed for first scene, fail for second
            mock_image_data = b"fake_image_data"
            
            def mock_api_side_effect(prompt, ref_images=None, char_names=None):
                if "success" in prompt:
                    return mock_image_data
                else:
                    raise Exception("API Error for failure scene")
            
            with patch.object(generator, '_call_seedream_api', new_callable=AsyncMock) as mock_api:
                with patch.object(generator, '_save_image', new_callable=AsyncMock) as mock_save:
                    mock_api.side_effect = mock_api_side_effect
                    mock_save.return_value = None
                    
                    # Generate images - should not raise exception
                    results = await generator.generate_images(scenes, output_dir)
                    
                    # Should have results for both scenes
                    assert len(results) == 2
                    
                    # First scene should be successful
                    success_result = next(r for r in results if r.scene_id == "success_scene")
                    assert success_result.status == ResourceStatus.COMPLETED
                    
                    # Second scene should be failed
                    failure_result = next(r for r in results if r.scene_id == "failure_scene")
                    assert failure_result.status == ResourceStatus.FAILED
                    assert failure_result.error_message is not None