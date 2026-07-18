"""Property-based tests for SubtitleGenerator.

This module contains property-based tests using Hypothesis to verify
the correctness of subtitle generation, focusing on timecode precision,
bilingual completeness, and file integrity.

Feature: langchain-video-generator
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, settings, strategies as st

from backend.schemas.models import (
    Scene,
    SceneDuration,
    Emotion,
    SubtitleSegment,
)
from backend.core.generators.subtitle import SubtitleGenerator


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def non_empty_text(min_size=1, max_size=200):
    """Generate text that is non-empty after stripping whitespace."""
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            whitelist_categories=('L', 'N'),
        )),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))
    )


def non_empty_english_text(min_size=1, max_size=200):
    """Generate English text that is non-empty after stripping whitespace."""
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            min_codepoint=48, max_codepoint=122
        ).filter(lambda c: c.isalnum())),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            min_codepoint=32, max_codepoint=126
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
        video_prompt_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        narration_cn=draw(non_empty_text(min_size=1, max_size=200)),
        narration_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        duration=draw(st.sampled_from(SceneDuration)),
        emotion=draw(st.sampled_from(Emotion))
    )


@st.composite
def scenes_list_strategy(draw):
    """Generate a list of valid Scenes."""
    return draw(st.lists(scene_strategy(), min_size=1, max_size=10))


@st.composite
def subtitle_segment_strategy(draw):
    """Generate a valid SubtitleSegment."""
    start_time = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    duration = draw(st.sampled_from([5.0, 10.0]))
    end_time = start_time + duration
    
    return SubtitleSegment(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_-'
        ))),
        start_time=start_time,
        end_time=end_time,
        text_cn=draw(non_empty_text(min_size=1, max_size=200)),
        text_en=draw(non_empty_english_text(min_size=1, max_size=200)),
    )


@st.composite
def subtitle_segments_list_strategy(draw):
    """Generate a list of valid SubtitleSegments with sequential timecodes."""
    count = draw(st.integers(min_value=1, max_value=10))
    segments = []
    current_time = 0.0
    
    for i in range(count):
        duration = draw(st.sampled_from([5.0, 10.0]))
        segment = SubtitleSegment(
            scene_id=f"scene_{i+1:03d}",
            start_time=current_time,
            end_time=current_time + duration,
            text_cn=draw(non_empty_text(min_size=1, max_size=200)),
            text_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        )
        segments.append(segment)
        current_time += duration
    
    return segments


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestSubtitleTimecodeAccuracy:
    """Property-based tests for subtitle timecode accuracy.
    
    Feature: langchain-video-generator, Property 8: 字幕时间码精确性
    Validates: Requirements 4.6
    """

    @given(scenes=scenes_list_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_subtitle_timecode_accuracy(self, scenes: list[Scene]):
        """For any SubtitleSegment, (end_time - start_time) must equal the Scene's duration.
        
        Property 8: 字幕时间码精确性
        Validates: Requirements 4.6
        """
        generator = SubtitleGenerator()
        segments = await generator.generate_all_segments(scenes)
        
        for scene, segment in zip(scenes, segments):
            duration_from_timecode = segment.end_time - segment.start_time
            expected_duration = float(scene.duration.value)
            
            assert abs(duration_from_timecode - expected_duration) < 0.001, (
                f"Scene {scene.scene_id}: timecode duration {duration_from_timecode}s "
                f"does not match scene duration {expected_duration}s"
            )


class TestSubtitleBilingualCompleteness:
    """Property-based tests for subtitle bilingual completeness.
    
    Feature: langchain-video-generator, Property 9: 字幕双语完整性
    Validates: Requirements 4.1, 4.2
    """

    @given(scenes=scenes_list_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_subtitle_bilingual_completeness(self, scenes: list[Scene]):
        """For any SubtitleSegment, both text_cn and text_en must be non-empty.
        
        Property 9: 字幕双语完整性
        Validates: Requirements 4.1, 4.2
        """
        generator = SubtitleGenerator()
        segments = await generator.generate_all_segments(scenes)
        
        for segment in segments:
            # Check Chinese text is non-empty
            assert segment.text_cn and len(segment.text_cn.strip()) > 0, (
                f"Segment {segment.scene_id} has empty Chinese text"
            )
            
            # Check English text is non-empty
            assert segment.text_en and len(segment.text_en.strip()) > 0, (
                f"Segment {segment.scene_id} has empty English text"
            )


class TestSubtitleFileCompleteness:
    """Property-based tests for subtitle file completeness.
    
    Feature: langchain-video-generator, Property 10: 字幕文件完整性
    Validates: Requirements 4.4, 4.5
    """

    @given(segments=subtitle_segments_list_strategy())
    @settings(max_examples=100)
    def test_subtitle_file_completeness(self, segments: list[SubtitleSegment]):
        """For any completed project, export_combined_srt must generate two valid SRT files.
        
        Property 10: 字幕文件完整性
        Validates: Requirements 4.4, 4.5
        """
        generator = SubtitleGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cn_file, en_file = generator.export_combined_srt(segments, tmpdir)
            
            # Check Chinese file exists and is valid
            cn_path = Path(cn_file.file_path)
            assert cn_path.exists(), f"Chinese subtitle file does not exist: {cn_path}"
            assert cn_file.language == "cn", f"Chinese file has wrong language: {cn_file.language}"
            assert cn_file.format == "srt", f"Chinese file has wrong format: {cn_file.format}"
            
            # Check English file exists and is valid
            en_path = Path(en_file.file_path)
            assert en_path.exists(), f"English subtitle file does not exist: {en_path}"
            assert en_file.language == "en", f"English file has wrong language: {en_file.language}"
            assert en_file.format == "srt", f"English file has wrong format: {en_file.format}"
            
            # Check file contents are non-empty
            cn_content = cn_path.read_text(encoding="utf-8")
            assert len(cn_content.strip()) > 0, "Chinese subtitle file is empty"
            
            en_content = en_path.read_text(encoding="utf-8")
            assert len(en_content.strip()) > 0, "English subtitle file is empty"
            
            # Check that both files have the same number of entries
            cn_entries = cn_content.strip().split("\n\n")
            en_entries = en_content.strip().split("\n\n")
            assert len(cn_entries) == len(en_entries) == len(segments), (
                f"Entry count mismatch: CN={len(cn_entries)}, EN={len(en_entries)}, "
                f"expected={len(segments)}"
            )
