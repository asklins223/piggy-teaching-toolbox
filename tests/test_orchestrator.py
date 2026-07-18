"""Property-based tests for Orchestrator.

This module contains property-based tests using Hypothesis to verify
the correctness of the orchestrator's workflow execution.

Feature: langchain-video-generator
Properties: 14, 15
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st, assume

from backend.schemas.models import (
    AudioConfig,
    Emotion,
    ExportPackage,
    ProjectState,
    ProjectStatus,
    ResourceStatus,
    Scene,
    SceneAudio,
    SceneImage,
    SceneDuration,
    Storyboard,
    SubtitleSegment,
    TeachingGoal,
)
from backend.services.storage import StorageManager
from backend.core.orchestrator import (
    Orchestrator,
    OrchestratorError,
    ProgressCallback,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

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
        key_points=draw(st.lists(simple_text_strategy(min_size=1, max_size=30), min_size=1, max_size=5))
    )


@st.composite
def scene_strategy(draw, scene_num: int):
    """Generate a valid Scene."""
    duration = draw(st.sampled_from(list(SceneDuration)))
    return Scene(
        scene_id=f"scene_{scene_num:03d}",
        step_number=scene_num,
        description_cn=draw(simple_text_strategy(min_size=1, max_size=100)),
        narration_cn=draw(simple_text_strategy(min_size=1, max_size=100)),
        narration_en=draw(simple_text_strategy(min_size=1, max_size=100)),
        duration=duration,
        emotion=draw(st.sampled_from(list(Emotion)))
    )


@st.composite
def storyboard_strategy(draw, project_id: str, num_scenes: int):
    """Generate a valid Storyboard with specified number of scenes."""
    scenes = [draw(scene_strategy(i + 1)) for i in range(num_scenes)]
    total_duration = sum(s.duration.value for s in scenes)
    return Storyboard(
        project_id=project_id,
        title=draw(simple_text_strategy(min_size=1, max_size=50)),
        scenes=scenes,
        total_duration_seconds=total_duration
    )


# =============================================================================
# Mock Factories
# =============================================================================

def create_mock_script_planner(storyboard: Storyboard):
    """Create a mock ScriptPlanner that returns a predefined storyboard."""
    mock = MagicMock()
    mock.generate_storyboard = AsyncMock(return_value=storyboard)
    mock.refine_scene = AsyncMock()
    mock.translate_narration = AsyncMock(return_value="Translated text")
    return mock


def create_mock_scene_generator(output_dir: Path, scenes: list[Scene]):
    """Create a mock SceneGenerator that creates actual files."""
    mock = MagicMock()
    
    async def mock_generate_images(scenes, output_dir, character_refs=None, style_reference=None, on_progress=None):
        results = []
        images_dir = output_dir
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for i, scene in enumerate(scenes):
            filename = f"{scene.scene_id}.png"
            file_path = images_dir / filename
            file_path.write_bytes(b"fake image data")
            
            results.append(SceneImage(
                scene_id=scene.scene_id,
                image_path=str(file_path),
                prompt_used=scene.description_cn,
                status=ResourceStatus.COMPLETED,
                error_message=None
            ))
            
            if on_progress:
                on_progress(i + 1, len(scenes))
        
        return results
    
    async def mock_regenerate_image(scene, output_dir, character_refs=None, style_reference=None):
        images_dir = output_dir
        images_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{scene.scene_id}.png"
        file_path = images_dir / filename
        file_path.write_bytes(b"fake regenerated image data")
        
        return SceneImage(
            scene_id=scene.scene_id,
            image_path=str(file_path),
            prompt_used=scene.description_cn,
            status=ResourceStatus.COMPLETED,
            error_message=None
        )
    
    mock.generate_images = mock_generate_images
    mock.regenerate_image = mock_regenerate_image
    return mock


def create_mock_audio_generator(output_dir: Path, scenes: list[Scene]):
    """Create a mock AudioGenerator that creates actual files."""
    mock = MagicMock()
    mock._initialized = True
    mock.initialize = MagicMock()
    
    async def mock_generate_audios(scenes, output_dir, config=None, on_progress=None):
        results = []
        audios_dir = output_dir
        audios_dir.mkdir(parents=True, exist_ok=True)
        
        for i, scene in enumerate(scenes):
            filename = f"{scene.scene_id}.wav"
            file_path = audios_dir / filename
            # Create a minimal valid WAV file
            file_path.write_bytes(b"RIFF" + b"\x00" * 40)
            
            results.append(SceneAudio(
                scene_id=scene.scene_id,
                audio_path=str(file_path),
                duration_seconds=float(scene.duration.value),
                status=ResourceStatus.COMPLETED,
                error_message=None
            ))
            
            if on_progress:
                on_progress(i + 1, len(scenes))
        
        return results
    
    mock.generate_audios = mock_generate_audios
    return mock


def create_mock_subtitle_generator():
    """Create a mock SubtitleGenerator."""
    mock = MagicMock()
    
    async def mock_generate_all_segments(scenes, on_progress=None):
        segments = []
        current_time = 0.0
        
        for i, scene in enumerate(scenes):
            segment = SubtitleSegment(
                scene_id=scene.scene_id,
                start_time=current_time,
                end_time=current_time + scene.duration.value,
                text_cn=scene.narration_cn,
                text_en=scene.narration_en
            )
            segments.append(segment)
            current_time += scene.duration.value
            
            if on_progress:
                on_progress(i + 1, len(scenes))
        
        return segments
    
    def mock_export_combined_srt(segments, output_dir):
        from backend.schemas.models import SubtitleFile
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cn_path = output_path / "full_cn.srt"
        en_path = output_path / "full_en.srt"
        cn_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest CN\n", encoding="utf-8")
        en_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest EN\n", encoding="utf-8")
        
        return (
            SubtitleFile(file_path=str(cn_path), language="cn", format="srt"),
            SubtitleFile(file_path=str(en_path), language="en", format="srt")
        )
    
    mock.generate_all_segments = mock_generate_all_segments
    mock.export_combined_srt = mock_export_combined_srt
    return mock


def create_mock_asset_exporter(project_id: str):
    """Create a mock AssetExporter."""
    mock = MagicMock()
    
    async def mock_export_all(project_state, output_dir, source_dir=None):
        from backend.schemas.models import ExportPackage, SceneAsset
        
        output_path = Path(output_dir)
        export_dir = output_path / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock files
        zip_path = export_dir / "assets.zip"
        manifest_path = export_dir / "manifest.json"
        zip_path.write_bytes(b"PK" + b"\x00" * 20)
        manifest_path.write_text('{"project_id": "' + project_id + '"}', encoding="utf-8")
        
        subtitles_dir = output_path / "subtitles"
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        cn_path = subtitles_dir / "full_cn.srt"
        en_path = subtitles_dir / "full_en.srt"
        cn_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest\n", encoding="utf-8")
        en_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest\n", encoding="utf-8")
        
        assets = []
        if project_state.storyboard:
            for scene in project_state.storyboard.scenes:
                # Find matching image and audio
                image = next((img for img in project_state.images if img.scene_id == scene.scene_id), None)
                audio = next((aud for aud in project_state.audios if aud.scene_id == scene.scene_id), None)
                subtitle = next((sub for sub in project_state.subtitles if sub.scene_id == scene.scene_id), None)
                
                if image and audio and subtitle:
                    assets.append(SceneAsset(
                        scene_id=scene.scene_id,
                        image_path=image.image_path,
                        audio_path=audio.audio_path,
                        subtitle_cn=subtitle,
                        subtitle_en=subtitle
                    ))
        
        return ExportPackage(
            project_id=project_id,
            zip_path=str(zip_path),
            manifest_path=str(manifest_path),
            assets=assets,
            subtitle_cn_path=str(cn_path),
            subtitle_en_path=str(en_path)
        )
    
    mock.export_all = mock_export_all
    return mock


# =============================================================================
# Property 14: 断点续传状态一致性
# =============================================================================

class TestCheckpointRecoveryConsistency:
    """Property-based tests for checkpoint recovery consistency.
    
    Feature: langchain-video-generator, Property 14: 断点续传状态一致性
    Validates: Requirements 6.2
    """

    @given(
        goal=teaching_goal_strategy(),
        num_scenes=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_resume_from_any_stage_produces_consistent_result(
        self,
        goal: TeachingGoal,
        num_scenes: int
    ):
        """For any project, resuming from a saved state should produce equivalent final result.
        
        Property 14: 断点续传状态一致性
        Validates: Requirements 6.2
        
        This test verifies that when a project is saved at any stage and then
        resumed, the final output is equivalent to running without interruption.
        """
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                storage = StorageManager(base_dir=str(base_dir))
                
                project_id = "test_resume_proj"
                project_dir = base_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Create a deterministic storyboard
                scenes = [
                    Scene(
                        scene_id=f"scene_{i:03d}",
                        step_number=i + 1,
                        description_cn=f"场景 {i} 描述",
                        narration_cn=f"旁白 {i}",
                        narration_en=f"Narration {i}",
                        duration=SceneDuration.SHORT,
                        emotion=Emotion.CALM
                    )
                    for i in range(num_scenes)
                ]
                storyboard = Storyboard(
                    project_id=project_id,
                    title="Test Video",
                    scenes=scenes,
                    total_duration_seconds=num_scenes * 5
                )
                
                # Create mocks
                script_planner = create_mock_script_planner(storyboard)
                scene_gen = create_mock_scene_generator(project_dir / "images", scenes)
                audio_gen = create_mock_audio_generator(project_dir / "audios", scenes)
                subtitle_gen = create_mock_subtitle_generator()
                asset_exporter = create_mock_asset_exporter(project_id)
                
                # Create orchestrator
                orchestrator = Orchestrator(
                    script_planner=script_planner,
                    scene_generator=scene_gen,
                    audio_generator=audio_gen,
                    subtitle_generator=subtitle_gen,
                    asset_exporter=asset_exporter,
                    storage_manager=storage
                )
                
                # Create project and run complete workflow
                proj_id = await orchestrator.create_project(goal)
                
                # Run each stage manually
                await orchestrator.generate_storyboard(proj_id)
                await orchestrator.generate_images(proj_id)
                await orchestrator.generate_audios(proj_id)
                await orchestrator.generate_subtitles(proj_id)
                await orchestrator.export_assets(proj_id)
                
                # Get final state
                state1 = storage.load_project(proj_id)
                
                # Verify the project completed
                assert state1.status == ProjectStatus.COMPLETED
                assert state1.export_package is not None
                
                # Now test resume on a completed project
                state2 = await orchestrator.resume(proj_id)
                
                # Results should be equivalent
                assert state1.status == state2.status
                assert state1.export_package.project_id == state2.export_package.project_id
        
        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        goal=teaching_goal_strategy(),
        interrupt_stage=st.sampled_from([
            ProjectStatus.INITIALIZED,
            ProjectStatus.STORYBOARD_READY,
            ProjectStatus.IMAGES_READY,
            ProjectStatus.AUDIO_READY,
            ProjectStatus.SUBTITLES_READY
        ])
    )
    @settings(max_examples=100)
    def test_resume_from_intermediate_stage(
        self,
        goal: TeachingGoal,
        interrupt_stage: ProjectStatus
    ):
        """For any intermediate stage, resume should continue from that point.
        
        Property 14: 断点续传状态一致性
        Validates: Requirements 6.2
        
        This test verifies that when a project is manually set to an intermediate
        state and then resumed, it continues from that stage correctly.
        """
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                storage = StorageManager(base_dir=str(base_dir))
                
                project_id = "test_resume_stage_proj"
                project_dir = base_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                
                num_scenes = 2
                
                # Create storyboard
                scenes = [
                    Scene(
                        scene_id=f"scene_{i:03d}",
                        step_number=i + 1,
                        description_cn=f"场景 {i}",
                        narration_cn=f"旁白 {i}",
                        narration_en=f"Narration {i}",
                        duration=SceneDuration.SHORT,
                        emotion=Emotion.CALM
                    )
                    for i in range(num_scenes)
                ]
                storyboard = Storyboard(
                    project_id=project_id,
                    title="Test Video",
                    scenes=scenes,
                    total_duration_seconds=num_scenes * 5
                )
                
                # Build state based on interrupt stage
                saved_storyboard = None
                images = []
                audios = []
                subtitles = []
                
                if interrupt_stage in (
                    ProjectStatus.STORYBOARD_READY,
                    ProjectStatus.IMAGES_READY,
                    ProjectStatus.AUDIO_READY,
                    ProjectStatus.SUBTITLES_READY
                ):
                    saved_storyboard = storyboard
                
                if interrupt_stage in (
                    ProjectStatus.IMAGES_READY,
                    ProjectStatus.AUDIO_READY,
                    ProjectStatus.SUBTITLES_READY
                ):
                    # Create image files
                    images_dir = project_dir / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)
                    for scene in scenes:
                        img_path = images_dir / f"{scene.scene_id}.png"
                        img_path.write_bytes(b"fake image")
                        images.append(SceneImage(
                            scene_id=scene.scene_id,
                            image_path=str(img_path),
                            prompt_used=scene.description_cn,
                            status=ResourceStatus.COMPLETED
                        ))
                
                if interrupt_stage in (
                    ProjectStatus.AUDIO_READY,
                    ProjectStatus.SUBTITLES_READY
                ):
                    # Create audio files
                    audios_dir = project_dir / "audios"
                    audios_dir.mkdir(parents=True, exist_ok=True)
                    for scene in scenes:
                        aud_path = audios_dir / f"{scene.scene_id}.wav"
                        aud_path.write_bytes(b"RIFF" + b"\x00" * 40)
                        audios.append(SceneAudio(
                            scene_id=scene.scene_id,
                            audio_path=str(aud_path),
                            duration_seconds=float(scene.duration.value),
                            status=ResourceStatus.COMPLETED
                        ))
                
                if interrupt_stage == ProjectStatus.SUBTITLES_READY:
                    # Create subtitles
                    current_time = 0.0
                    for scene in scenes:
                        subtitles.append(SubtitleSegment(
                            scene_id=scene.scene_id,
                            start_time=current_time,
                            end_time=current_time + scene.duration.value,
                            text_cn=scene.narration_cn,
                            text_en=scene.narration_en
                        ))
                        current_time += scene.duration.value
                
                state = ProjectState(
                    project_id=project_id,
                    status=interrupt_stage,
                    goal=goal,
                    storyboard=saved_storyboard,
                    images=images,
                    audios=audios,
                    subtitles=subtitles,
                    export_package=None
                )
                storage.save_project(state)
                
                # Create mocks
                script_planner = create_mock_script_planner(storyboard)
                scene_gen = create_mock_scene_generator(project_dir / "images", scenes)
                audio_gen = create_mock_audio_generator(project_dir / "audios", scenes)
                subtitle_gen = create_mock_subtitle_generator()
                asset_exporter = create_mock_asset_exporter(project_id)
                
                # Create orchestrator
                orchestrator = Orchestrator(
                    script_planner=script_planner,
                    scene_generator=scene_gen,
                    audio_generator=audio_gen,
                    subtitle_generator=subtitle_gen,
                    asset_exporter=asset_exporter,
                    storage_manager=storage
                )
                
                # Resume from the intermediate stage
                result = await orchestrator.resume(project_id)
                
                # Verify completion
                assert result.status == ProjectStatus.COMPLETED
                assert result.export_package is not None
        
        asyncio.get_event_loop().run_until_complete(run_test())


# =============================================================================
# Property 15: 进度回调完整性
# =============================================================================

class TestProgressCallbackCompleteness:
    """Property-based tests for progress callback completeness.
    
    Feature: langchain-video-generator, Property 15: 进度回调完整性
    Validates: Requirements 6.3
    """

    @given(
        goal=teaching_goal_strategy(),
        num_scenes=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_progress_callback_called_for_each_scene_images(
        self,
        goal: TeachingGoal,
        num_scenes: int
    ):
        """For any project with N scenes, image progress callback should be called at least N times.
        
        Property 15: 进度回调完整性
        Validates: Requirements 6.3
        
        This test verifies that when running image generation with N scenes,
        the progress callback is invoked at least N times.
        """
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                storage = StorageManager(base_dir=str(base_dir))
                
                project_id = "test_progress_images_proj"
                project_dir = base_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Create storyboard with specified number of scenes
                scenes = [
                    Scene(
                        scene_id=f"scene_{i:03d}",
                        step_number=i + 1,
                        description_cn=f"场景 {i}",
                        
                        narration_cn=f"旁白 {i}",
                        narration_en=f"Narration {i}",
                        duration=SceneDuration.SHORT,
                        emotion=Emotion.CALM
                    )
                    for i in range(num_scenes)
                ]
                storyboard = Storyboard(
                    project_id=project_id,
                    title="Test Video",
                    scenes=scenes,
                    total_duration_seconds=num_scenes * 5
                )
                
                # Create mocks
                script_planner = create_mock_script_planner(storyboard)
                scene_gen = create_mock_scene_generator(project_dir / "images", scenes)
                audio_gen = create_mock_audio_generator(project_dir / "audios", scenes)
                subtitle_gen = create_mock_subtitle_generator()
                asset_exporter = create_mock_asset_exporter(project_id)
                
                # Create orchestrator
                orchestrator = Orchestrator(
                    script_planner=script_planner,
                    scene_generator=scene_gen,
                    audio_generator=audio_gen,
                    subtitle_generator=subtitle_gen,
                    asset_exporter=asset_exporter,
                    storage_manager=storage
                )
                
                # Track progress callbacks
                progress_calls = []
                
                def progress_callback(stage: str, message: str, current: int, total: int):
                    progress_calls.append({
                        "stage": stage,
                        "message": message,
                        "current": current,
                        "total": total
                    })
                
                # Create project and generate storyboard first
                proj_id = await orchestrator.create_project(goal)
                await orchestrator.generate_storyboard(proj_id, on_progress=progress_callback)
                
                # Clear progress calls and generate images
                progress_calls.clear()
                await orchestrator.generate_images(proj_id, on_progress=progress_callback)
                
                # Count image-related progress calls
                image_calls = [c for c in progress_calls if c["stage"] == "images"]
                
                # Should have at least N calls for N scenes
                # (one for each scene being generated, plus start/end messages)
                assert len(image_calls) >= num_scenes, (
                    f"Expected at least {num_scenes} image progress calls, "
                    f"got {len(image_calls)}"
                )
        
        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        goal=teaching_goal_strategy(),
        num_scenes=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_progress_callback_called_for_each_scene_audios(
        self,
        goal: TeachingGoal,
        num_scenes: int
    ):
        """For any project with N scenes, audio progress callback should be called at least N times.
        
        Property 15: 进度回调完整性
        Validates: Requirements 6.3
        
        This test verifies that when running audio generation with N scenes,
        the progress callback is invoked at least N times.
        """
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                storage = StorageManager(base_dir=str(base_dir))
                
                project_id = "test_progress_audios_proj"
                project_dir = base_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Create storyboard with specified number of scenes
                scenes = [
                    Scene(
                        scene_id=f"scene_{i:03d}",
                        step_number=i + 1,
                        description_cn=f"场景 {i}",
                        
                        narration_cn=f"旁白 {i}",
                        narration_en=f"Narration {i}",
                        duration=SceneDuration.SHORT,
                        emotion=Emotion.CALM
                    )
                    for i in range(num_scenes)
                ]
                storyboard = Storyboard(
                    project_id=project_id,
                    title="Test Video",
                    scenes=scenes,
                    total_duration_seconds=num_scenes * 5
                )
                
                # Create mocks
                script_planner = create_mock_script_planner(storyboard)
                scene_gen = create_mock_scene_generator(project_dir / "images", scenes)
                audio_gen = create_mock_audio_generator(project_dir / "audios", scenes)
                subtitle_gen = create_mock_subtitle_generator()
                asset_exporter = create_mock_asset_exporter(project_id)
                
                # Create orchestrator
                orchestrator = Orchestrator(
                    script_planner=script_planner,
                    scene_generator=scene_gen,
                    audio_generator=audio_gen,
                    subtitle_generator=subtitle_gen,
                    asset_exporter=asset_exporter,
                    storage_manager=storage
                )
                
                # Track progress callbacks
                progress_calls = []
                
                def progress_callback(stage: str, message: str, current: int, total: int):
                    progress_calls.append({
                        "stage": stage,
                        "message": message,
                        "current": current,
                        "total": total
                    })
                
                # Create project and run prerequisite stages
                proj_id = await orchestrator.create_project(goal)
                await orchestrator.generate_storyboard(proj_id)
                await orchestrator.generate_images(proj_id)
                
                # Clear progress calls and generate audios
                progress_calls.clear()
                await orchestrator.generate_audios(proj_id, on_progress=progress_callback)
                
                # Count audio-related progress calls
                audio_calls = [c for c in progress_calls if c["stage"] == "audios"]
                
                # Should have at least N calls for N scenes
                assert len(audio_calls) >= num_scenes, (
                    f"Expected at least {num_scenes} audio progress calls, "
                    f"got {len(audio_calls)}"
                )
        
        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        goal=teaching_goal_strategy(),
        num_scenes=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_progress_callback_covers_all_stages(
        self,
        goal: TeachingGoal,
        num_scenes: int
    ):
        """For any complete workflow, progress callback should cover all stages.
        
        Property 15: 进度回调完整性
        Validates: Requirements 6.3
        
        This test verifies that progress callbacks are received for all
        major stages: storyboard, images, audios, subtitles, and export.
        """
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                storage = StorageManager(base_dir=str(base_dir))
                
                project_id = "test_stages_proj"
                project_dir = base_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Create storyboard
                scenes = [
                    Scene(
                        scene_id=f"scene_{i:03d}",
                        step_number=i + 1,
                        description_cn=f"场景 {i}",
                        
                        narration_cn=f"旁白 {i}",
                        narration_en=f"Narration {i}",
                        duration=SceneDuration.SHORT,
                        emotion=Emotion.CALM
                    )
                    for i in range(num_scenes)
                ]
                storyboard = Storyboard(
                    project_id=project_id,
                    title="Test Video",
                    scenes=scenes,
                    total_duration_seconds=num_scenes * 5
                )
                
                # Create mocks
                script_planner = create_mock_script_planner(storyboard)
                scene_gen = create_mock_scene_generator(project_dir / "images", scenes)
                audio_gen = create_mock_audio_generator(project_dir / "audios", scenes)
                subtitle_gen = create_mock_subtitle_generator()
                asset_exporter = create_mock_asset_exporter(project_id)
                
                # Create orchestrator
                orchestrator = Orchestrator(
                    script_planner=script_planner,
                    scene_generator=scene_gen,
                    audio_generator=audio_gen,
                    subtitle_generator=subtitle_gen,
                    asset_exporter=asset_exporter,
                    storage_manager=storage
                )
                
                # Track progress callbacks by stage
                stages_seen = set()
                
                def progress_callback(stage: str, message: str, current: int, total: int):
                    stages_seen.add(stage)
                
                # Create and run complete workflow
                proj_id = await orchestrator.create_project(goal)
                await orchestrator.generate_storyboard(proj_id, on_progress=progress_callback)
                await orchestrator.generate_images(proj_id, on_progress=progress_callback)
                await orchestrator.generate_audios(proj_id, on_progress=progress_callback)
                await orchestrator.generate_subtitles(proj_id, on_progress=progress_callback)
                await orchestrator.export_assets(proj_id, on_progress=progress_callback)
                
                # Verify all major stages were covered
                expected_stages = {"storyboard", "images", "audios", "subtitles", "export"}
                assert expected_stages.issubset(stages_seen), (
                    f"Missing stages: {expected_stages - stages_seen}"
                )
        
        asyncio.get_event_loop().run_until_complete(run_test())
