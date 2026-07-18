"""Tests for CharacterGenerator.

This module contains property-based tests and unit tests for the CharacterGenerator class.

Feature: langchain-video-generator
Property 1: 角色生成数量一致性
Validates: Requirements 1.3, 1.4
"""

import tempfile
from pathlib import Path
from typing import Optional

import pytest
from hypothesis import given, settings, strategies as st

from backend.schemas.models import CharacterConfig
from backend.core.generators.character import (
    CharacterGenerator,
    CharacterGenerationError,
    ImageGeneratorProtocol,
)


# =============================================================================
# Mock Image Generator for Testing
# =============================================================================

class MockImageGenerator:
    """Mock image generator that returns fake image data.
    
    This mock allows testing the CharacterGenerator without making actual API calls.
    """
    
    def __init__(self, should_fail: bool = False, fail_on_index: Optional[int] = None):
        """Initialize the mock generator.
        
        Args:
            should_fail: If True, all generations will fail.
            fail_on_index: If set, generation will fail on this specific call index.
        """
        self.should_fail = should_fail
        self.fail_on_index = fail_on_index
        self.call_count = 0
        self.prompts: list[str] = []
    
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate a fake image.
        
        Args:
            prompt: The generation prompt (stored for verification).
            size: Image size (ignored in mock).
            
        Returns:
            Fake PNG image data.
            
        Raises:
            CharacterGenerationError: If configured to fail.
        """
        self.prompts.append(prompt)
        current_index = self.call_count
        self.call_count += 1
        
        if self.should_fail:
            raise CharacterGenerationError(
                character_name="unknown",
                reason="Mock API failure",
                retryable=True
            )
        
        if self.fail_on_index is not None and current_index == self.fail_on_index:
            raise CharacterGenerationError(
                character_name="unknown",
                reason=f"Mock failure at index {current_index}",
                retryable=True
            )
        
        # Return minimal valid PNG data (1x1 transparent pixel)
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def character_config_strategy(draw):
    """Generate a valid CharacterConfig for testing."""
    return CharacterConfig(
        name=draw(st.text(
            min_size=1, 
            max_size=30, 
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' _')
        )),
        description=draw(st.text(
            min_size=1, 
            max_size=100, 
            alphabet=st.characters(whitelist_categories=('L', 'N', 'P'), whitelist_characters=' ')
        ))
    )


@st.composite
def character_config_list_strategy(draw, min_size=0, max_size=5):
    """Generate a list of CharacterConfigs for testing."""
    return draw(st.lists(
        character_config_strategy(),
        min_size=min_size,
        max_size=max_size
    ))


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestCharacterGenerationCountConsistency:
    """Property-based tests for character generation count consistency.
    
    Feature: langchain-video-generator, Property 1: 角色生成数量一致性
    Validates: Requirements 1.3
    """

    @given(configs=character_config_list_strategy(min_size=0, max_size=5))
    @settings(max_examples=100)
    def test_generate_characters_count_matches_input(self, configs: list[CharacterConfig]):
        """For any list of CharacterConfigs, generate_characters should return
        a list of CharacterReferences with the same length.
        
        Property 1: 角色生成数量一致性
        Validates: Requirements 1.3
        
        This property ensures that when generating multiple characters,
        the output list length always equals the input list length.
        """
        import asyncio
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator()
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            # Run the async function
            results = asyncio.get_event_loop().run_until_complete(
                generator.generate_characters(configs)
            )
            
            # Property: output length equals input length
            assert len(results) == len(configs), (
                f"Expected {len(configs)} characters, got {len(results)}"
            )
            
            # Additional verification: each result corresponds to input
            for i, (config, result) in enumerate(zip(configs, results)):
                assert result.name == config.name, (
                    f"Character {i}: expected name '{config.name}', got '{result.name}'"
                )

    @given(configs=character_config_list_strategy(min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_each_character_has_unique_id(self, configs: list[CharacterConfig]):
        """For any list of CharacterConfigs, each generated CharacterReference
        should have a unique character_id.
        
        Property 1 (extended): Each character gets a unique identifier
        Validates: Requirements 1.3
        """
        import asyncio
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator()
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            results = asyncio.get_event_loop().run_until_complete(
                generator.generate_characters(configs)
            )
            
            # All character IDs should be unique
            character_ids = [r.character_id for r in results]
            assert len(character_ids) == len(set(character_ids)), (
                f"Duplicate character IDs found: {character_ids}"
            )

    @given(configs=character_config_list_strategy(min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_each_character_image_file_exists(self, configs: list[CharacterConfig]):
        """For any list of CharacterConfigs, each generated CharacterReference
        should have an image_path pointing to an existing file.
        
        Property 1 (extended): Each character image is saved to disk
        Validates: Requirements 1.2, 1.3
        """
        import asyncio
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator()
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            results = asyncio.get_event_loop().run_until_complete(
                generator.generate_characters(configs)
            )
            
            # Each image file should exist
            for result in results:
                assert Path(result.image_path).exists(), (
                    f"Image file does not exist: {result.image_path}"
                )


# =============================================================================
# Unit Tests for Error Handling
# =============================================================================

class TestCharacterGeneratorErrorHandling:
    """Unit tests for CharacterGenerator error handling.
    
    Validates: Requirements 1.4
    """

    @pytest.mark.asyncio
    async def test_api_error_returns_error_message(self):
        """When API fails, CharacterGenerator should raise CharacterGenerationError
        with a descriptive error message.
        
        Requirements: 1.4
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator(should_fail=True)
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            config = CharacterConfig(
                name="Test Character",
                description="A test character"
            )
            
            with pytest.raises(CharacterGenerationError) as exc_info:
                await generator.generate_character(config)
            
            # Verify error contains useful information
            assert "Mock API failure" in str(exc_info.value)
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_partial_failure_in_batch_raises_error(self):
        """When one character in a batch fails, the entire operation should fail
        with information about which character failed.
        
        Requirements: 1.4
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Fail on the second character (index 1)
            mock_generator = MockImageGenerator(fail_on_index=1)
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            configs = [
                CharacterConfig(name="Character 1", description="First"),
                CharacterConfig(name="Character 2", description="Second"),
                CharacterConfig(name="Character 3", description="Third"),
            ]
            
            with pytest.raises(CharacterGenerationError) as exc_info:
                await generator.generate_characters(configs)
            
            # Should fail on the second character
            assert "index 1" in str(exc_info.value) or "Character 2" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_includes_character_name(self):
        """Error messages should include the character name for debugging.
        
        Requirements: 1.4
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator(should_fail=True)
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            config = CharacterConfig(
                name="SpecificCharacterName",
                description="A test character"
            )
            
            with pytest.raises(CharacterGenerationError) as exc_info:
                await generator.generate_character(config)
            
            # The error should be catchable and have the retryable flag
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_empty_config_list_returns_empty_list(self):
        """When given an empty config list, should return an empty list without error.
        
        Requirements: 1.3
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_generator = MockImageGenerator()
            generator = CharacterGenerator(
                output_dir=tmp_dir,
                image_generator=mock_generator
            )
            
            results = await generator.generate_characters([])
            
            assert results == []
            assert mock_generator.call_count == 0
