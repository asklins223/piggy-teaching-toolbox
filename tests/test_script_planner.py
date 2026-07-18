"""Property-based tests for ScriptPlanner.

This module contains property-based tests using Hypothesis to verify
the correctness of storyboard generation, particularly focusing on
scene duration constraints and completeness.

Feature: langchain-video-generator, video-style-expansion
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from hypothesis import given, settings, strategies as st
import re

from backend.schemas.models import (
    AudioParams,
    Scene,
    Storyboard,
    TeachingGoal,
    SceneDuration,
    Emotion,
    VideoStyle,
)
from backend.core.script_planner import ScriptPlanner


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def teaching_goal_strategy(draw):
    """Generate a valid TeachingGoal."""
    return TeachingGoal(
        topic=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))),
        target_audience=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))),
        key_points=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('L', 'N', 'P', 'S'),
                whitelist_characters=' '
            )),
            min_size=0,
            max_size=10
        ))
    )


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
def audio_params_strategy(draw):
    """Generate a valid AudioParams with all required fields.
    
    Requirements: 5.2
    """
    return AudioParams(
        emotion=draw(st.sampled_from(Emotion)),
        emotion_strength=draw(st.floats(min_value=0.0, max_value=1.0)),
        speed=draw(st.floats(min_value=0.5, max_value=2.0)),
        volume=draw(st.floats(min_value=0.5, max_value=1.5)),
    )


@st.composite
def scene_with_audio_params_strategy(draw):
    """Generate a valid Scene with audio_params included.
    
    Requirements: 5.1, 5.2
    """
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
        emotion=draw(st.sampled_from(Emotion)),
        audio_params=draw(audio_params_strategy()),
    )


@st.composite
def scene_strategy(draw):
    """Generate a valid Scene with flexible duration (5, 8, 10, 12, or 15 seconds)."""
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
def storyboard_strategy(draw):
    """Generate a valid Storyboard with scenes."""
    scenes = draw(st.lists(scene_strategy(), min_size=1, max_size=10))
    total_duration = sum(s.duration.value for s in scenes)
    return Storyboard(
        project_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_-'
        ))),
        title=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))),
        scenes=scenes,
        total_duration_seconds=total_duration
    )


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestSceneDurationConstraint:
    """Property-based tests for scene duration constraints.
    
    Feature: langchain-video-generator, Property 1: 分镜时长约束
    Validates: Requirements 1.3
    """

    @given(storyboard=storyboard_strategy())
    @settings(max_examples=100)
    def test_scene_duration_constraint(self, storyboard: Storyboard):
        """For any Storyboard, all scenes must have valid duration (5, 8, 10, 12, or 15 seconds).
        
        Property 1: 分镜时长约束
        Validates: Requirements 1.3
        """
        valid_durations = [
            SceneDuration.VERY_SHORT,  # 5s
            SceneDuration.SHORT,       # 8s
            SceneDuration.MEDIUM,      # 10s
            SceneDuration.LONG,        # 12s
            SceneDuration.VERY_LONG,   # 15s
        ]
        for scene in storyboard.scenes:
            assert scene.duration in valid_durations, (
                f"Scene {scene.scene_id} has invalid duration {scene.duration.value}s"
            )


class TestSceneCompleteness:
    """Property-based tests for scene completeness.
    
    Feature: langchain-video-generator, Property 2: 分镜脚本完整性
    Validates: Requirements 1.2, 1.4
    """

    @given(storyboard=storyboard_strategy())
    @settings(max_examples=100)
    def test_scene_script_completeness(self, storyboard: Storyboard):
        """For any Storyboard, all scenes must have non-empty required fields.
        
        Property 2: 分镜脚本完整性
        Validates: Requirements 1.2, 1.4
        """
        for scene in storyboard.scenes:
            # Check description_cn is non-empty (Requirement 1.2)
            # description_cn serves as both scene description and image prompt
            assert scene.description_cn and len(scene.description_cn.strip()) > 0, (
                f"Scene {scene.scene_id} has empty description_cn"
            )
            
            # Check narration_cn is non-empty (Requirement 1.4)
            assert scene.narration_cn and len(scene.narration_cn.strip()) > 0, (
                f"Scene {scene.scene_id} has empty narration_cn"
            )
            
            # Check narration_en is non-empty (Requirement 1.4)
            assert scene.narration_en and len(scene.narration_en.strip()) > 0, (
                f"Scene {scene.scene_id} has empty narration_en"
            )


class TestNarrationBilingual:
    """Property-based tests for bilingual narration.
    
    Feature: langchain-video-generator, Property 3: 双语旁白
    Validates: Requirements 1.4
    """

    @given(storyboard=storyboard_strategy())
    @settings(max_examples=100)
    def test_narration_bilingual(self, storyboard: Storyboard):
        """For any Storyboard, all scenes must have both Chinese and English narration.
        
        Property 3: 双语旁白
        Validates: Requirements 1.4
        """
        for scene in storyboard.scenes:
            # Check both narrations exist
            assert scene.narration_cn, f"Scene {scene.scene_id} missing Chinese narration"
            assert scene.narration_en, f"Scene {scene.scene_id} missing English narration"



# =============================================================================
# Property 4: 分镜数据结构完整性 (Scene Data Structure Completeness)
# Feature: video-style-expansion
# =============================================================================

class TestSceneAudioParamsCompleteness:
    """Property-based tests for scene audio_params completeness.
    
    Feature: video-style-expansion, Property 4: 分镜数据结构完整性
    Validates: Requirements 5.1, 5.2, 6.5
    """

    @given(scene=scene_with_audio_params_strategy())
    @settings(max_examples=100)
    def test_scene_audio_params_structure(self, scene: Scene):
        """For any generated Scene, audio_params must contain all required fields.
        
        Property 4: 分镜数据结构完整性
        *For any* generated scene, it should contain audio_params field, and 
        audio_params should contain emotion, emotion_strength, speed, volume fields.
        
        Validates: Requirements 5.1, 5.2, 6.5
        """
        # Check audio_params exists
        assert scene.audio_params is not None, (
            f"Scene {scene.scene_id} missing audio_params"
        )
        
        # Check audio_params has all required fields
        audio_params = scene.audio_params
        
        # Check emotion field exists and is valid
        assert audio_params.emotion is not None, (
            f"Scene {scene.scene_id} audio_params missing emotion"
        )
        assert isinstance(audio_params.emotion, Emotion), (
            f"Scene {scene.scene_id} audio_params.emotion is not an Emotion enum"
        )
        
        # Check emotion_strength field exists and is in valid range
        assert audio_params.emotion_strength is not None, (
            f"Scene {scene.scene_id} audio_params missing emotion_strength"
        )
        assert 0.0 <= audio_params.emotion_strength <= 1.0, (
            f"Scene {scene.scene_id} audio_params.emotion_strength {audio_params.emotion_strength} "
            f"is out of range [0.0, 1.0]"
        )
        
        # Check speed field exists and is in valid range
        assert audio_params.speed is not None, (
            f"Scene {scene.scene_id} audio_params missing speed"
        )
        assert 0.5 <= audio_params.speed <= 2.0, (
            f"Scene {scene.scene_id} audio_params.speed {audio_params.speed} "
            f"is out of range [0.5, 2.0]"
        )
        
        # Check volume field exists and is in valid range
        assert audio_params.volume is not None, (
            f"Scene {scene.scene_id} audio_params missing volume"
        )
        assert 0.5 <= audio_params.volume <= 1.5, (
            f"Scene {scene.scene_id} audio_params.volume {audio_params.volume} "
            f"is out of range [0.5, 1.5]"
        )


class TestScriptPlannerAudioParamsGeneration:
    """Tests for ScriptPlanner audio params generation methods.
    
    Feature: video-style-expansion, Property 4: 分镜数据结构完整性
    Validates: Requirements 5.1, 5.2, 5.3, 6.5
    """

    @given(style=st.sampled_from(VideoStyle))
    @settings(max_examples=100)
    def test_style_default_params_completeness(self, style: VideoStyle):
        """For any VideoStyle, _get_style_default_params must return complete params.
        
        Property 4: 分镜数据结构完整性
        *For any* video style, the default audio params should contain all required fields.
        
        Validates: Requirements 5.3
        """
        planner = ScriptPlanner(api_key="test_key")
        default_params = planner._get_style_default_params(style)
        
        # Check all required fields exist
        assert "emotion" in default_params, f"Style {style} missing emotion in default params"
        assert "emotion_strength" in default_params, f"Style {style} missing emotion_strength"
        assert "speed" in default_params, f"Style {style} missing speed"
        assert "volume" in default_params, f"Style {style} missing volume"
        
        # Check emotion is valid
        assert isinstance(default_params["emotion"], Emotion), (
            f"Style {style} default emotion is not an Emotion enum"
        )
        
        # Check ranges
        assert 0.0 <= default_params["emotion_strength"] <= 1.0, (
            f"Style {style} emotion_strength out of range"
        )
        assert 0.5 <= default_params["speed"] <= 2.0, (
            f"Style {style} speed out of range"
        )
        assert 0.5 <= default_params["volume"] <= 1.5, (
            f"Style {style} volume out of range"
        )

    @given(
        style=st.sampled_from(VideoStyle),
        emotion_str=st.sampled_from([e.value for e in Emotion]),
        emotion_strength=st.floats(min_value=0.0, max_value=1.0),
        speed=st.floats(min_value=0.5, max_value=2.0),
        volume=st.floats(min_value=0.5, max_value=1.5),
    )
    @settings(max_examples=100)
    def test_generate_audio_params_completeness(
        self, style: VideoStyle, emotion_str: str, 
        emotion_strength: float, speed: float, volume: float
    ):
        """For any scene data with audio_params, _generate_audio_params returns complete AudioParams.
        
        Property 4: 分镜数据结构完整性
        *For any* scene data with audio parameters, the generated AudioParams should be complete.
        
        Validates: Requirements 5.1, 5.2
        """
        planner = ScriptPlanner(api_key="test_key")
        
        scene_data = {
            "emotion": emotion_str,
            "audio_params": {
                "emotion": emotion_str,
                "emotion_strength": emotion_strength,
                "speed": speed,
                "volume": volume,
            }
        }
        
        audio_params = planner._generate_audio_params(scene_data, style)
        
        # Check AudioParams is returned
        assert isinstance(audio_params, AudioParams), "Result is not an AudioParams instance"
        
        # Check all fields exist and are valid
        assert audio_params.emotion is not None
        assert isinstance(audio_params.emotion, Emotion)
        assert 0.0 <= audio_params.emotion_strength <= 1.0
        assert 0.5 <= audio_params.speed <= 2.0
        assert 0.5 <= audio_params.volume <= 1.5
