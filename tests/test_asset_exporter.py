"""Property-based tests for AssetExporter.

Feature: langchain-video-generator, Property 13: 导出包完整性
Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import asyncio
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from backend.core.asset_exporter import AssetExporter, ExportError
from backend.schemas.models import (
    Emotion,
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


@st.composite
def simple_id_strategy(draw):
    return draw(st.text(min_size=3, max_size=15,
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_')))


@st.composite
def simple_text_strategy(draw, min_size=1, max_size=50):
    return draw(st.text(min_size=min_size, max_size=max_size,
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' .,!?')))


@st.composite
def english_text_strategy(draw, min_size=5, max_size=100):
    return draw(st.text(min_size=min_size, max_size=max_size,
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))


@st.composite
def teaching_goal_strategy(draw):
    return TeachingGoal(
        topic=draw(simple_text_strategy(min_size=3, max_size=50)),
        target_audience=draw(simple_text_strategy(min_size=3, max_size=30)),
        key_points=draw(st.lists(simple_text_strategy(min_size=3, max_size=30), min_size=1, max_size=3)))


@st.composite
def scene_strategy(draw, scene_id, step_number):
    return Scene(
        scene_id=scene_id,
        step_number=step_number,
        description_cn=draw(simple_text_strategy(min_size=5, max_size=100)),
        narration_cn=draw(simple_text_strategy(min_size=5, max_size=100)),
        narration_en=draw(english_text_strategy(min_size=5, max_size=100)),
        duration=draw(st.sampled_from(list(SceneDuration))),
        emotion=draw(st.sampled_from(list(Emotion))))


@st.composite
def complete_project_state_strategy(draw, project_dir):
    project_id = draw(simple_id_strategy())
    goal = draw(teaching_goal_strategy())
    num_scenes = draw(st.integers(min_value=1, max_value=5))
    
    images_dir = project_dir / "images"
    audios_dir = project_dir / "audios"
    images_dir.mkdir(parents=True, exist_ok=True)
    audios_dir.mkdir(parents=True, exist_ok=True)
    
    scenes, images, audios, subtitles = [], [], [], []
    current_time = 0.0
    
    for i in range(num_scenes):
        scene_id = f"scene_{i:03d}"
        scene = draw(scene_strategy(scene_id, i + 1))
        scenes.append(scene)
        
        image_filename = f"{scene_id}.png"
        (images_dir / image_filename).write_bytes(b"fake PNG image data")
        images.append(SceneImage(scene_id=scene_id, image_path=f"images/{image_filename}",
            prompt_used=scene.description_cn, status=ResourceStatus.COMPLETED, error_message=None))
        
        audio_filename = f"{scene_id}.wav"
        (audios_dir / audio_filename).write_bytes(b"fake WAV audio data")
        audios.append(SceneAudio(scene_id=scene_id, audio_path=f"audios/{audio_filename}",
            duration_seconds=float(scene.duration.value), status=ResourceStatus.COMPLETED, error_message=None))
        
        end_time = current_time + scene.duration.value
        subtitles.append(SubtitleSegment(scene_id=scene_id, start_time=current_time, end_time=end_time,
            text_cn=scene.narration_cn, text_en=scene.narration_en))
        current_time = end_time
    
    storyboard = Storyboard(project_id=project_id, title=draw(simple_text_strategy(min_size=5, max_size=50)),
        scenes=scenes, total_duration_seconds=int(current_time))
    
    return ProjectState(project_id=project_id, status=ProjectStatus.SUBTITLES_READY, goal=goal,
        storyboard=storyboard, images=images, audios=audios, subtitles=subtitles)


class TestExportPackageCompleteness:
    """Property 13: 导出包完整性. Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6"""

    @given(data=st.data())
    @settings(max_examples=100)
    def test_export_package_contains_all_required_files(self, data):
        """For any successful export, the ZIP file must contain all required assets."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_state = data.draw(complete_project_state_strategy(project_dir))
            
            exporter = AssetExporter()
            export_dir = Path(tmp_dir) / "export_output"
            export_package = asyncio.get_event_loop().run_until_complete(
                exporter.export_all(project_state, str(export_dir), source_dir=str(project_dir)))
            
            zip_path = Path(export_package.zip_path)
            assert zip_path.exists(), f"ZIP file should exist at {zip_path}"
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zip_contents = zf.namelist()
                assert "manifest.json" in zip_contents
                assert "subtitles/full_cn.srt" in zip_contents
                assert "subtitles/full_en.srt" in zip_contents
                
                num_scenes = len(project_state.storyboard.scenes)
                for i in range(num_scenes):
                    scene_id = f"scene_{i:03d}"
                    assert f"{scene_id}/image.png" in zip_contents
                    assert f"{scene_id}/prompt.txt" in zip_contents
                    assert f"{scene_id}/subtitle_cn.srt" in zip_contents
                    assert f"{scene_id}/subtitle_en.srt" in zip_contents
                
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                assert manifest["project_id"] == project_state.project_id
                assert manifest["total_scenes"] == num_scenes
                assert len(manifest["scenes"]) == num_scenes

    @given(data=st.data())
    @settings(max_examples=100)
    def test_export_package_manifest_has_correct_structure(self, data):
        """For any successful export, the manifest JSON must have correct structure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_state = data.draw(complete_project_state_strategy(project_dir))
            
            exporter = AssetExporter()
            export_dir = Path(tmp_dir) / "export_output"
            export_package = asyncio.get_event_loop().run_until_complete(
                exporter.export_all(project_state, str(export_dir), source_dir=str(project_dir)))
            
            manifest_path = Path(export_package.manifest_path)
            assert manifest_path.exists()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            
            assert "project_id" in manifest
            assert "exported_at" in manifest
            assert "total_scenes" in manifest
            assert "subtitle_files" in manifest
            assert "scenes" in manifest
            assert "chinese" in manifest["subtitle_files"]
            assert "english" in manifest["subtitle_files"]
            
            for scene_info in manifest["scenes"]:
                assert "scene_id" in scene_info
                assert "folder" in scene_info
                assert "files" in scene_info
                assert "metadata" in scene_info
                files = scene_info["files"]
                assert "image" in files
                assert "prompt" in files
                assert "subtitle_cn" in files
                assert "subtitle_en" in files
                metadata = scene_info["metadata"]
                assert "start_time" in metadata
                assert "end_time" in metadata
                assert "text_cn" in metadata
                assert "text_en" in metadata

    @given(data=st.data())
    @settings(max_examples=100)
    def test_export_package_subtitle_files_are_valid_srt(self, data):
        """For any successful export, subtitle files must be valid SRT format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_state = data.draw(complete_project_state_strategy(project_dir))
            
            exporter = AssetExporter()
            export_dir = Path(tmp_dir) / "export_output"
            export_package = asyncio.get_event_loop().run_until_complete(
                exporter.export_all(project_state, str(export_dir), source_dir=str(project_dir)))
            
            cn_path = Path(export_package.subtitle_cn_path)
            assert cn_path.exists()
            cn_content = cn_path.read_text(encoding="utf-8")
            
            en_path = Path(export_package.subtitle_en_path)
            assert en_path.exists()
            en_content = en_path.read_text(encoding="utf-8")
            
            assert len(cn_content) > 0
            assert len(en_content) > 0
            
            num_scenes = len(project_state.storyboard.scenes)
            assert cn_content.count("-->") == num_scenes
            assert en_content.count("-->") == num_scenes


class TestExportPackageAssets:
    """Tests for individual asset export functionality."""

    @given(data=st.data())
    @settings(max_examples=50)
    def test_export_package_assets_count_matches_scenes(self, data):
        """For any export, the number of assets should match the number of scenes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_state = data.draw(complete_project_state_strategy(project_dir))
            
            exporter = AssetExporter()
            export_dir = Path(tmp_dir) / "export_output"
            export_package = asyncio.get_event_loop().run_until_complete(
                exporter.export_all(project_state, str(export_dir), source_dir=str(project_dir)))
            
            num_scenes = len(project_state.storyboard.scenes)
            assert len(export_package.assets) == num_scenes
            
            for asset in export_package.assets:
                assert asset.image_path
                assert asset.audio_path
                assert asset.subtitle_cn
                assert asset.subtitle_en
