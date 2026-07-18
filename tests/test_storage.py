"""Property-based tests for StorageManager.

This module contains property-based tests using Hypothesis to verify
the correctness of storage operations and resource file integrity.

Feature: langchain-video-generator, Property 12: 资源文件关联完整性
Validates: Requirements 7.4
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from backend.schemas.models import (
    CharacterReference,
    ClipStatus,
    ComposedVideo,
    ProjectState,
    ProjectStatus,
    Scene,
    Storyboard,
    TeachingGoal,
    VideoClip,
    SceneImage,
    SceneAudio,
    SubtitleSegment,
    ExportPackage,
    SceneAsset,
    ResourceStatus,
    SceneDuration,
    Emotion,
)
from backend.services.storage import StorageManager, ProjectNotFoundError


# =============================================================================
# Hypothesis Strategies for Storage Tests
# =============================================================================

@st.composite
def simple_id_strategy(draw):
    """Generate a simple alphanumeric ID."""
    return draw(st.text(
        min_size=1, 
        max_size=20, 
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_')
    ))


@st.composite
def simple_text_strategy(draw, min_size=1, max_size=50):
    """Generate simple text without special characters."""
    return draw(st.text(
        min_size=min_size, 
        max_size=max_size, 
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P'), whitelist_characters=' ')
    ))


@st.composite
def teaching_goal_strategy(draw):
    """Generate a valid TeachingGoal."""
    return TeachingGoal(
        topic=draw(simple_text_strategy(min_size=1, max_size=50)),
        target_audience=draw(simple_text_strategy(min_size=1, max_size=30)),
        key_points=draw(st.lists(simple_text_strategy(min_size=1, max_size=30), min_size=0, max_size=5))
    )


@st.composite
def scene_image_with_file_strategy(draw, project_dir: Path):
    """Generate a SceneImage with an actual file created."""
    scene_id = draw(simple_id_strategy())
    
    # Create the actual file
    filename = f"{scene_id}.png"
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    file_path = images_dir / filename
    file_path.write_bytes(b"fake image data")
    
    return SceneImage(
        scene_id=scene_id,
        image_path=f"images/{filename}",
        prompt_used=draw(simple_text_strategy(min_size=1, max_size=100)),
        status=ResourceStatus.COMPLETED,
        error_message=None
    )


@st.composite
def scene_audio_with_file_strategy(draw, project_dir: Path):
    """Generate a SceneAudio with an actual file created."""
    scene_id = draw(simple_id_strategy())
    
    # Create the actual file
    filename = f"{scene_id}.wav"
    audios_dir = project_dir / "audios"
    audios_dir.mkdir(parents=True, exist_ok=True)
    file_path = audios_dir / filename
    file_path.write_bytes(b"fake audio data")
    
    return SceneAudio(
        scene_id=scene_id,
        audio_path=f"audios/{filename}",
        duration_seconds=draw(st.floats(min_value=4.5, max_value=10.5, allow_nan=False, allow_infinity=False)),
        status=ResourceStatus.COMPLETED,
        error_message=None
    )


@st.composite
def export_package_with_files_strategy(draw, project_dir: Path, project_id: str):
    """Generate an ExportPackage with actual files created."""
    # Create export directory
    export_dir = project_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Create ZIP file
    zip_filename = "assets.zip"
    (export_dir / zip_filename).write_bytes(b"fake zip data")
    
    # Create manifest file
    manifest_filename = "manifest.json"
    (export_dir / manifest_filename).write_bytes(b'{"fake": "manifest"}')
    
    # Create subtitle files
    subtitles_dir = project_dir / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    (subtitles_dir / "full_cn.srt").write_bytes(b"fake chinese subtitles")
    (subtitles_dir / "full_en.srt").write_bytes(b"fake english subtitles")
    
    # Create scene assets
    num_assets = draw(st.integers(min_value=1, max_value=3))
    assets = []
    for i in range(num_assets):
        scene_id = f"scene_{i:03d}"
        
        # Create image file
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / f"{scene_id}.png").write_bytes(b"fake scene image")
        
        # Create audio file
        audios_dir = project_dir / "audios"
        audios_dir.mkdir(parents=True, exist_ok=True)
        (audios_dir / f"{scene_id}.wav").write_bytes(b"fake scene audio")
        
        assets.append(SceneAsset(
            scene_id=scene_id,
            image_path=f"images/{scene_id}.png",
            audio_path=f"audios/{scene_id}.wav",
            subtitle_cn=SubtitleSegment(
                scene_id=scene_id,
                start_time=float(i * 5),
                end_time=float((i + 1) * 5),
                text_cn=f"中文字幕 {i}",
                text_en=f"English subtitle {i}"
            ),
            subtitle_en=SubtitleSegment(
                scene_id=scene_id,
                start_time=float(i * 5),
                end_time=float((i + 1) * 5),
                text_cn=f"中文字幕 {i}",
                text_en=f"English subtitle {i}"
            )
        ))
    
    return ExportPackage(
        project_id=project_id,
        zip_path=f"export/{zip_filename}",
        manifest_path=f"export/{manifest_filename}",
        assets=assets,
        subtitle_cn_path="subtitles/full_cn.srt",
        subtitle_en_path="subtitles/full_en.srt"
    )


@st.composite
def character_reference_with_file_strategy(draw, project_dir: Path):
    """Generate a CharacterReference with an actual file created."""
    char_id = draw(simple_id_strategy())
    name = draw(simple_text_strategy(min_size=1, max_size=30))
    
    # Create the actual file
    filename = f"{char_id}.png"
    chars_dir = project_dir / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)
    file_path = chars_dir / filename
    file_path.write_bytes(b"fake image data")
    
    return CharacterReference(
        character_id=char_id,
        name=name,
        image_path=f"characters/{filename}",
        image_url=None
    )


@st.composite
def video_clip_with_file_strategy(draw, project_dir: Path, scene_id: str):
    """Generate a VideoClip with an actual file created."""
    clip_id = draw(simple_id_strategy())
    
    # Create the actual file
    filename = f"{clip_id}.mp4"
    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    file_path = clips_dir / filename
    file_path.write_bytes(b"fake video data")
    
    return VideoClip(
        clip_id=clip_id,
        scene_id=scene_id,
        file_path=f"clips/{filename}",
        duration_seconds=draw(st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
        status=ClipStatus.COMPLETED,
        error_message=None
    )


@st.composite
def composed_video_with_file_strategy(draw, project_dir: Path):
    """Generate a ComposedVideo with an actual file created."""
    # Create the actual file
    filename = "final.mp4"
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / filename
    file_path.write_bytes(b"fake final video data")
    
    return ComposedVideo(
        output_path=f"output/{filename}",
        total_duration_seconds=draw(st.floats(min_value=1.0, max_value=300.0, allow_nan=False, allow_infinity=False)),
        clip_count=draw(st.integers(min_value=1, max_value=20))
    )


# =============================================================================
# Property-Based Tests for Resource File Integrity
# =============================================================================

class TestResourceFileIntegrity:
    """Property-based tests for resource file association integrity.
    
    Feature: langchain-video-generator, Property 12: 资源文件关联完整性
    Validates: Requirements 7.4
    """

    @given(
        project_id=simple_id_strategy(),
        goal=teaching_goal_strategy(),
        num_images=st.integers(min_value=0, max_value=3),
        num_audios=st.integers(min_value=0, max_value=3),
        include_export=st.booleans()
    )
    @settings(max_examples=100)
    def test_saved_project_resources_exist(
        self, 
        project_id: str, 
        goal: TeachingGoal,
        num_images: int,
        num_audios: int,
        include_export: bool
    ):
        """For any saved ProjectState, all referenced resource paths should point to existing files.
        
        Property 12: 资源文件关联完整性
        Validates: Requirements 7.4
        
        This test verifies that when a project is saved with resource references,
        and those resources actually exist on disk, the verify_resource_integrity
        method correctly identifies all resources as valid.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = StorageManager(base_dir=tmp_dir)
            project_dir = Path(tmp_dir) / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Create scene images with actual files
            images = []
            for i in range(num_images):
                scene_id = f"scene_{i:03d}"
                filename = f"{scene_id}.png"
                images_dir = project_dir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                (images_dir / filename).write_bytes(b"fake image")
                images.append(SceneImage(
                    scene_id=scene_id,
                    image_path=f"images/{filename}",
                    prompt_used=f"Test prompt for scene {i}",
                    status=ResourceStatus.COMPLETED,
                    error_message=None
                ))
            
            # Create scene audios with actual files
            audios = []
            for i in range(num_audios):
                scene_id = f"scene_{i:03d}"
                filename = f"{scene_id}.wav"
                audios_dir = project_dir / "audios"
                audios_dir.mkdir(parents=True, exist_ok=True)
                (audios_dir / filename).write_bytes(b"fake audio")
                audios.append(SceneAudio(
                    scene_id=scene_id,
                    audio_path=f"audios/{filename}",
                    duration_seconds=5.0,
                    status=ResourceStatus.COMPLETED,
                    error_message=None
                ))
            
            # Create export package with actual files
            export_package = None
            if include_export:
                export_dir = project_dir / "export"
                export_dir.mkdir(parents=True, exist_ok=True)
                subtitles_dir = project_dir / "subtitles"
                subtitles_dir.mkdir(parents=True, exist_ok=True)
                
                # Create export files
                (export_dir / "assets.zip").write_bytes(b"fake zip")
                (export_dir / "manifest.json").write_bytes(b'{"fake": "manifest"}')
                (subtitles_dir / "full_cn.srt").write_bytes(b"fake cn srt")
                (subtitles_dir / "full_en.srt").write_bytes(b"fake en srt")
                
                # Create scene asset files
                assets = []
                for i in range(min(num_images, num_audios)):
                    scene_id = f"scene_{i:03d}"
                    
                    assets.append(SceneAsset(
                        scene_id=scene_id,
                        image_path=f"images/{scene_id}.png",
                        audio_path=f"audios/{scene_id}.wav",
                        subtitle_cn=SubtitleSegment(
                            scene_id=scene_id,
                            start_time=float(i * 5),
                            end_time=float((i + 1) * 5),
                            text_cn=f"中文字幕 {i}",
                            text_en=f"English subtitle {i}"
                        ),
                        subtitle_en=SubtitleSegment(
                            scene_id=scene_id,
                            start_time=float(i * 5),
                            end_time=float((i + 1) * 5),
                            text_cn=f"中文字幕 {i}",
                            text_en=f"English subtitle {i}"
                        )
                    ))
                
                export_package = ExportPackage(
                    project_id=project_id,
                    zip_path="export/assets.zip",
                    manifest_path="export/manifest.json",
                    assets=assets,
                    subtitle_cn_path="subtitles/full_cn.srt",
                    subtitle_en_path="subtitles/full_en.srt"
                )
            
            # Determine status based on what we have
            if export_package:
                status = ProjectStatus.COMPLETED
            elif audios:
                status = ProjectStatus.AUDIO_READY
            elif images:
                status = ProjectStatus.IMAGES_READY
            else:
                status = ProjectStatus.INITIALIZED
            
            # Create project state
            state = ProjectState(
                project_id=project_id,
                status=status,
                goal=goal,
                images=images,
                audios=audios,
                export_package=export_package
            )
            
            # Save the project
            manager.save_project(state)
            
            # Verify resource integrity
            result = manager.verify_resource_integrity(state)
            
            # All resources should be valid (no missing)
            assert len(result["missing"]) == 0, f"Missing resources: {result['missing']}"
            
            # Count expected valid resources
            expected_valid_count = num_images + num_audios
            if include_export:
                # ZIP, manifest, 2 subtitle files, plus scene assets (image, audio per asset)
                num_assets = min(num_images, num_audios)
                expected_valid_count += 4 + (num_assets * 2)  # 4 export files + 2 files per asset (no video_prompt_path)
            
            assert len(result["valid"]) == expected_valid_count, f"Expected {expected_valid_count} valid resources, got {len(result['valid'])}: {result['valid']}"

    @given(
        project_id=simple_id_strategy(),
        goal=teaching_goal_strategy()
    )
    @settings(max_examples=100)
    def test_missing_resources_detected(
        self, 
        project_id: str, 
        goal: TeachingGoal
    ):
        """For any ProjectState with missing resource files, verify_resource_integrity should detect them.
        
        Property 12: 资源文件关联完整性 (negative case)
        Validates: Requirements 7.4
        
        This test verifies that when a project references resources that don't exist,
        the verify_resource_integrity method correctly identifies them as missing.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = StorageManager(base_dir=tmp_dir)
            
            # Create project state with references to non-existent files
            images = [
                SceneImage(
                    scene_id="missing_scene",
                    image_path="images/nonexistent.png",
                    prompt_used="Test prompt",
                    status=ResourceStatus.COMPLETED,
                    error_message=None
                )
            ]
            
            audios = [
                SceneAudio(
                    scene_id="missing_scene",
                    audio_path="audios/nonexistent.wav",
                    duration_seconds=5.0,
                    status=ResourceStatus.COMPLETED,
                    error_message=None
                )
            ]
            
            state = ProjectState(
                project_id=project_id,
                status=ProjectStatus.AUDIO_READY,
                goal=goal,
                images=images,
                audios=audios
            )
            
            # Save the project (creates directory structure but not resource files)
            manager.save_project(state)
            
            # Verify resource integrity
            result = manager.verify_resource_integrity(state)
            
            # Should detect missing resources
            assert len(result["missing"]) == 2, f"Expected 2 missing, got: {result['missing']}"
            assert len(result["valid"]) == 0


class TestStorageManagerRoundTrip:
    """Tests for StorageManager save/load round-trip functionality."""

    @given(
        project_id=simple_id_strategy(),
        goal=teaching_goal_strategy()
    )
    @settings(max_examples=100)
    def test_save_load_roundtrip(self, project_id: str, goal: TeachingGoal):
        """For any valid ProjectState, save then load should produce equivalent state.
        
        This complements Property 11 by testing the StorageManager's file-based
        serialization rather than just the model's JSON methods.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = StorageManager(base_dir=tmp_dir)
            
            # Create a simple project state
            state = ProjectState(
                project_id=project_id,
                status=ProjectStatus.INITIALIZED,
                goal=goal
            )
            
            # Save the project
            manager.save_project(state)
            
            # Load the project
            loaded_state = manager.load_project(project_id)
            
            # Verify equivalence (excluding updated_at which changes on save)
            assert loaded_state.project_id == state.project_id
            assert loaded_state.status == state.status
            assert loaded_state.goal == state.goal
            assert loaded_state.images == state.images
            assert loaded_state.audios == state.audios
            assert loaded_state.export_package == state.export_package
