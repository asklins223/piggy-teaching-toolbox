"""Property-based tests for data models.

This module contains property-based tests using Hypothesis to verify
the correctness of data model serialization and deserialization.
"""

import pytest
from hypothesis import given, settings, strategies as st

from backend.schemas.models import (
    AudioConfig,
    CharacterConfig,
    CharacterReference,
    CharacterStyle,
    ClipStatus,
    ComposedVideo,
    Emotion,
    ExportPackage,
    ProjectState,
    ProjectStatus,
    ResourceStatus,
    Scene,
    SceneAsset,
    SceneAudio,
    SceneDuration,
    SceneImage,
    Storyboard,
    SubtitleFile,
    SubtitleSegment,
    TeachingGoal,
    VideoClip,
)


# Hypothesis Strategies

@st.composite
def character_config_strategy(draw):
    """Generate a valid CharacterConfig."""
    return CharacterConfig(
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        description=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        )))
    )


@st.composite
def character_reference_strategy(draw):
    """Generate a valid CharacterReference."""
    return CharacterReference(
        character_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        image_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        image_url=draw(st.one_of(st.none(), st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/:._-'
        ))))
    )


@st.composite
def teaching_goal_strategy(draw):
    """Generate a valid TeachingGoal."""
    return TeachingGoal(
        topic=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        target_audience=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        key_points=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('L', 'N'), whitelist_characters=' _-'
            )),
            min_size=0, max_size=10
        ))
    )


@st.composite
def video_clip_strategy(draw):
    """Generate a valid VideoClip."""
    status = draw(st.sampled_from(list(ClipStatus)))
    error_message = None
    if status == ClipStatus.FAILED:
        error_message = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        )))
    return VideoClip(
        clip_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        file_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        duration_seconds=draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
        status=status,
        error_message=error_message
    )


@st.composite
def composed_video_strategy(draw):
    """Generate a valid ComposedVideo."""
    return ComposedVideo(
        output_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        total_duration_seconds=draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False)),
        clip_count=draw(st.integers(min_value=0, max_value=100))
    )



@st.composite
def scene_strategy(draw):
    """Generate a valid Scene."""
    duration = draw(st.sampled_from(list(SceneDuration)))
    return Scene(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        step_number=draw(st.integers(min_value=1, max_value=100)),
        description_cn=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        narration_cn=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        narration_en=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' ,._-'
        ))),
        duration=duration,
        emotion=draw(st.sampled_from(list(Emotion)))
    )


@st.composite
def storyboard_strategy(draw):
    """Generate a valid Storyboard."""
    scenes = draw(st.lists(scene_strategy(), min_size=0, max_size=5))
    total_duration = sum(s.duration.value for s in scenes)
    return Storyboard(
        project_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        title=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        scenes=scenes,
        total_duration_seconds=total_duration
    )


@st.composite
def scene_image_strategy(draw):
    """Generate a valid SceneImage."""
    status = draw(st.sampled_from(list(ResourceStatus)))
    error_message = None
    if status == ResourceStatus.FAILED:
        error_message = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        )))
    return SceneImage(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        image_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        prompt_used=draw(st.text(min_size=0, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        status=status,
        error_message=error_message
    )


@st.composite
def scene_audio_strategy(draw):
    """Generate a valid SceneAudio."""
    status = draw(st.sampled_from(list(ResourceStatus)))
    error_message = None
    if status == ResourceStatus.FAILED:
        error_message = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        )))
    return SceneAudio(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        audio_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        duration_seconds=draw(st.floats(min_value=0.0, max_value=15.0, allow_nan=False, allow_infinity=False)),
        status=status,
        error_message=error_message
    )


@st.composite
def subtitle_segment_strategy(draw):
    """Generate a valid SubtitleSegment."""
    start_time = draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    end_time = start_time + draw(st.floats(min_value=0.1, max_value=15.0, allow_nan=False, allow_infinity=False))
    return SubtitleSegment(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        start_time=start_time,
        end_time=end_time,
        text_cn=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' _-'
        ))),
        text_en=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters=' ,._-'
        )))
    )


@st.composite
def scene_asset_strategy(draw):
    """Generate a valid SceneAsset."""
    scene_id = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'), whitelist_characters='_-'
    )))
    subtitle_cn = draw(subtitle_segment_strategy())
    subtitle_cn.scene_id = scene_id
    subtitle_en = draw(subtitle_segment_strategy())
    subtitle_en.scene_id = scene_id
    return SceneAsset(
        scene_id=scene_id,
        image_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        audio_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        subtitle_cn=subtitle_cn,
        subtitle_en=subtitle_en
    )


@st.composite
def export_package_strategy(draw):
    """Generate a valid ExportPackage."""
    return ExportPackage(
        project_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        zip_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        manifest_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        assets=draw(st.lists(scene_asset_strategy(), min_size=0, max_size=3)),
        subtitle_cn_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        ))),
        subtitle_en_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='/_-.'
        )))
    )


@st.composite
def project_state_strategy(draw):
    """Generate a valid ProjectState for property testing."""
    status = draw(st.sampled_from(list(ProjectStatus)))
    
    # Generate characters (legacy)
    characters = draw(st.lists(character_reference_strategy(), min_size=0, max_size=3))
    
    # Generate storyboard based on status
    storyboard = None
    if status not in [ProjectStatus.INITIALIZED]:
        storyboard = draw(storyboard_strategy())
    
    # Generate clips (legacy)
    clips = []
    if status in [ProjectStatus.COMPLETED]:
        clips = draw(st.lists(video_clip_strategy(), min_size=0, max_size=5))
    
    # Generate final video (legacy)
    final_video = None
    if status == ProjectStatus.COMPLETED:
        final_video = draw(st.one_of(st.none(), composed_video_strategy()))
    
    # Generate images based on status
    images = []
    if status in [ProjectStatus.IMAGES_GENERATING, ProjectStatus.IMAGES_READY, 
                  ProjectStatus.AUDIO_GENERATING, ProjectStatus.AUDIO_READY,
                  ProjectStatus.SUBTITLES_READY, ProjectStatus.COMPLETED]:
        images = draw(st.lists(scene_image_strategy(), min_size=0, max_size=5))
    
    # Generate audios based on status
    audios = []
    if status in [ProjectStatus.AUDIO_GENERATING, ProjectStatus.AUDIO_READY,
                  ProjectStatus.SUBTITLES_READY, ProjectStatus.COMPLETED]:
        audios = draw(st.lists(scene_audio_strategy(), min_size=0, max_size=5))
    
    # Generate subtitles based on status
    subtitles = []
    if status in [ProjectStatus.SUBTITLES_READY, ProjectStatus.COMPLETED]:
        subtitles = draw(st.lists(subtitle_segment_strategy(), min_size=0, max_size=5))
    
    # Generate export package based on status
    export_package = None
    if status == ProjectStatus.COMPLETED:
        export_package = draw(st.one_of(st.none(), export_package_strategy()))
    
    return ProjectState(
        project_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='_-'
        ))),
        created_at=draw(st.text(min_size=20, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='-:TZ.'
        ))),
        updated_at=draw(st.text(min_size=20, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'), whitelist_characters='-:TZ.'
        ))),
        status=status,
        goal=draw(teaching_goal_strategy()),
        characters=characters,
        clips=clips,
        final_video=final_video,
        storyboard=storyboard,
        images=images,
        audios=audios,
        subtitles=subtitles,
        export_package=export_package
    )


class TestProjectStateRoundTrip:
    """Property-based tests for ProjectState serialization.
    
    Feature: langchain-video-generator, Property 11: 项目状态序列化 Round-Trip
    Validates: Requirements 7.1, 7.2, 7.3
    """

    @given(project_state=project_state_strategy())
    @settings(max_examples=100)
    def test_project_state_json_roundtrip(self, project_state: ProjectState):
        """For any valid ProjectState, serializing to JSON then deserializing
        should produce an equivalent object.
        
        Property 11: 项目状态序列化 Round-Trip
        Validates: Requirements 7.1, 7.2, 7.3
        """
        # Serialize to JSON
        json_str = project_state.to_json()
        
        # Deserialize from JSON
        loaded_state = ProjectState.from_json(json_str)
        
        # Verify equivalence
        assert loaded_state.project_id == project_state.project_id
        assert loaded_state.created_at == project_state.created_at
        assert loaded_state.updated_at == project_state.updated_at
        assert loaded_state.status == project_state.status
        assert loaded_state.goal == project_state.goal
        assert loaded_state.characters == project_state.characters
        assert loaded_state.storyboard == project_state.storyboard
        assert loaded_state.clips == project_state.clips
        assert loaded_state.final_video == project_state.final_video
        assert loaded_state.images == project_state.images
        assert loaded_state.audios == project_state.audios
        assert loaded_state.subtitles == project_state.subtitles
        assert loaded_state.export_package == project_state.export_package
        
        # Full object equality
        assert loaded_state == project_state

    @given(project_state=project_state_strategy())
    @settings(max_examples=100)
    def test_project_state_model_dump_roundtrip(self, project_state: ProjectState):
        """For any valid ProjectState, model_dump then model_validate
        should produce an equivalent object.
        
        Property 11: 项目状态序列化 Round-Trip (dict variant)
        Validates: Requirements 7.1, 7.2, 7.3
        """
        # Serialize to dict
        state_dict = project_state.model_dump()
        
        # Deserialize from dict
        loaded_state = ProjectState.model_validate(state_dict)
        
        # Verify equivalence
        assert loaded_state == project_state
