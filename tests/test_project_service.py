"""Tests for project service.

Tests the project_service module functions for CRUD operations.
"""

import json
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import (
    Base, CharacterRecord, ProjectRecord, SceneRecord, ProjectCharacterRecord
)
from backend.db.crud.projects import (
    generate_project_id, generate_scene_id,
    create_project, get_project, list_projects, delete_project,
    update_project_status, update_project_storyboard, update_project_export,
    create_scene, get_scene, get_project_scenes, update_scene,
    update_scene_image, update_scene_audio_cn, update_scene_audio_en,
    delete_project_scenes,
    add_character_to_project, remove_character_from_project, get_project_characters,
    project_to_dict, scene_to_dict
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_character(db_session):
    """Create a sample character for testing."""
    char = CharacterRecord(
        character_id="char_test_001",
        name="测试角色",
        description="测试用角色",
        cos_url="https://cos.example.com/char.png"
    )
    db_session.add(char)
    db_session.commit()
    return char


# =============================================================================
# Unit Tests for ID Generation
# =============================================================================

class TestIdGeneration:
    """Tests for ID generation functions."""
    
    def test_generate_project_id_format(self):
        """Test project ID format."""
        project_id = generate_project_id()
        assert project_id.startswith("proj_")
        assert len(project_id) == 13  # "proj_" + 8 hex chars
    
    def test_generate_project_id_unique(self):
        """Test project IDs are unique."""
        ids = [generate_project_id() for _ in range(100)]
        assert len(set(ids)) == 100
    
    def test_generate_scene_id_format(self):
        """Test scene ID format."""
        scene_id = generate_scene_id()
        assert scene_id.startswith("scene_")
        assert len(scene_id) == 14  # "scene_" + 8 hex chars
    
    def test_generate_scene_id_unique(self):
        """Test scene IDs are unique."""
        ids = [generate_scene_id() for _ in range(100)]
        assert len(set(ids)) == 100


# =============================================================================
# Unit Tests for Project CRUD
# =============================================================================

class TestProjectCRUD:
    """Tests for project CRUD operations."""
    
    def test_create_project(self, db_session):
        """Test creating a project."""
        project = create_project(
            db=db_session,
            topic="测试主题",
            target_audience="测试受众",
            key_points=["知识点1", "知识点2"],
            user_id="user_001"
        )
        
        assert project.project_id.startswith("proj_")
        assert project.topic == "测试主题"
        assert project.target_audience == "测试受众"
        assert project.status == "initialized"
        assert project.user_id == "user_001"
        
        # Verify key_points
        key_points = json.loads(project.key_points)
        assert key_points == ["知识点1", "知识点2"]
    
    def test_get_project(self, db_session):
        """Test getting a project by ID."""
        created = create_project(
            db=db_session,
            topic="获取测试",
            target_audience="测试",
            key_points=[]
        )
        
        fetched = get_project(db_session, created.project_id)
        assert fetched is not None
        assert fetched.project_id == created.project_id
        assert fetched.topic == "获取测试"
    
    def test_get_project_not_found(self, db_session):
        """Test getting a non-existent project."""
        result = get_project(db_session, "proj_nonexistent")
        assert result is None
    
    def test_list_projects(self, db_session):
        """Test listing all projects."""
        # Create multiple projects
        for i in range(3):
            create_project(
                db=db_session,
                topic=f"项目{i}",
                target_audience="测试",
                key_points=[]
            )
        
        projects = list_projects(db_session)
        assert len(projects) == 3
    
    def test_list_projects_by_user(self, db_session):
        """Test listing projects filtered by user."""
        create_project(db=db_session, topic="用户1项目", target_audience="", key_points=[], user_id="user_001")
        create_project(db=db_session, topic="用户2项目", target_audience="", key_points=[], user_id="user_002")
        create_project(db=db_session, topic="用户1项目2", target_audience="", key_points=[], user_id="user_001")
        
        user1_projects = list_projects(db_session, user_id="user_001")
        assert len(user1_projects) == 2
    
    def test_update_project_status(self, db_session):
        """Test updating project status."""
        project = create_project(
            db=db_session,
            topic="状态测试",
            target_audience="",
            key_points=[]
        )
        
        result = update_project_status(db_session, project.project_id, "storyboard_ready")
        assert result is True
        
        updated = get_project(db_session, project.project_id)
        assert updated.status == "storyboard_ready"
    
    def test_update_project_storyboard(self, db_session):
        """Test updating project storyboard info."""
        project = create_project(
            db=db_session,
            topic="分镜测试",
            target_audience="",
            key_points=[]
        )
        
        result = update_project_storyboard(
            db_session,
            project.project_id,
            title="测试分镜标题",
            total_duration=120
        )
        assert result is True
        
        updated = get_project(db_session, project.project_id)
        assert updated.storyboard_title == "测试分镜标题"
        assert updated.total_duration == 120
        assert updated.status == "storyboard_ready"
    
    def test_update_project_export(self, db_session):
        """Test updating project export info."""
        project = create_project(
            db=db_session,
            topic="导出测试",
            target_audience="",
            key_points=[]
        )
        
        result = update_project_export(
            db_session,
            project.project_id,
            cos_url="https://cos.example.com/export.zip",
            cos_key="exports/proj_001/export.zip"
        )
        assert result is True
        
        updated = get_project(db_session, project.project_id)
        assert updated.export_cos_url == "https://cos.example.com/export.zip"
        assert updated.status == "completed"
    
    def test_delete_project(self, db_session):
        """Test deleting a project."""
        project = create_project(
            db=db_session,
            topic="删除测试",
            target_audience="",
            key_points=[]
        )
        project_id = project.project_id
        
        # Add some scenes
        create_scene(db_session, project_id, 1, "场景1", "旁白1")
        create_scene(db_session, project_id, 2, "场景2", "旁白2")
        
        result = delete_project(db_session, project_id)
        assert result is True
        
        # Verify project is deleted
        assert get_project(db_session, project_id) is None
        
        # Verify scenes are deleted
        scenes = get_project_scenes(db_session, project_id)
        assert len(scenes) == 0


# =============================================================================
# Unit Tests for Scene CRUD
# =============================================================================

class TestSceneCRUD:
    """Tests for scene CRUD operations."""
    
    def test_create_scene(self, db_session):
        """Test creating a scene."""
        project = create_project(db=db_session, topic="场景测试", target_audience="", key_points=[])
        
        scene = create_scene(
            db=db_session,
            project_id=project.project_id,
            step_number=1,
            description_cn="场景描述",
            narration_cn="中文旁白",
            narration_en="English narration",
            duration=10,
            emotion="喜",
            character_ids=["char_001"]
        )
        
        assert scene.scene_id.startswith("scene_")
        assert scene.project_id == project.project_id
        assert scene.step_number == 1
        assert scene.description_cn == "场景描述"
        assert scene.duration == 10
    
    def test_get_scene(self, db_session):
        """Test getting a scene by ID."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        created = create_scene(db_session, project.project_id, 1, "描述", "旁白")
        
        fetched = get_scene(db_session, created.scene_id)
        assert fetched is not None
        assert fetched.scene_id == created.scene_id
    
    def test_get_project_scenes_ordered(self, db_session):
        """Test getting scenes in order by step_number."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        # Create scenes out of order
        create_scene(db_session, project.project_id, 3, "场景3", "旁白3")
        create_scene(db_session, project.project_id, 1, "场景1", "旁白1")
        create_scene(db_session, project.project_id, 2, "场景2", "旁白2")
        
        scenes = get_project_scenes(db_session, project.project_id)
        assert len(scenes) == 3
        assert scenes[0].step_number == 1
        assert scenes[1].step_number == 2
        assert scenes[2].step_number == 3
    
    def test_update_scene(self, db_session):
        """Test updating scene fields."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        scene = create_scene(db_session, project.project_id, 1, "原描述", "原旁白")
        
        result = update_scene(
            db_session,
            scene.scene_id,
            description_cn="新描述",
            narration_cn="新旁白",
            duration=15
        )
        assert result is True
        
        updated = get_scene(db_session, scene.scene_id)
        assert updated.description_cn == "新描述"
        assert updated.narration_cn == "新旁白"
        assert updated.duration == 15
    
    def test_update_scene_image(self, db_session):
        """Test updating scene image info."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        scene = create_scene(db_session, project.project_id, 1, "描述", "旁白")
        
        result = update_scene_image(
            db_session,
            scene.scene_id,
            status="completed",
            cos_url="https://cos.example.com/image.png",
            cos_key="images/scene.png",
            prompt="生成提示词"
        )
        assert result is True
        
        updated = get_scene(db_session, scene.scene_id)
        assert updated.image_status == "completed"
        assert updated.image_cos_url == "https://cos.example.com/image.png"
        assert updated.image_prompt == "生成提示词"
    
    def test_update_scene_audio(self, db_session):
        """Test updating scene audio info."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        scene = create_scene(db_session, project.project_id, 1, "描述", "旁白")
        
        # Update CN audio
        update_scene_audio_cn(
            db_session, scene.scene_id,
            status="completed",
            cos_url="https://cos.example.com/cn.wav",
            duration_ms=5000
        )
        
        # Update EN audio
        update_scene_audio_en(
            db_session, scene.scene_id,
            status="completed",
            cos_url="https://cos.example.com/en.wav",
            duration_ms=4500
        )
        
        updated = get_scene(db_session, scene.scene_id)
        assert updated.audio_cn_status == "completed"
        assert updated.audio_cn_duration == 5000
        assert updated.audio_en_status == "completed"
        assert updated.audio_en_duration == 4500
    
    def test_delete_project_scenes(self, db_session):
        """Test deleting all scenes for a project."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        for i in range(5):
            create_scene(db_session, project.project_id, i+1, f"场景{i}", f"旁白{i}")
        
        count = delete_project_scenes(db_session, project.project_id)
        assert count == 5
        
        scenes = get_project_scenes(db_session, project.project_id)
        assert len(scenes) == 0


# =============================================================================
# Unit Tests for Project Character Association
# =============================================================================

class TestProjectCharacterAssociation:
    """Tests for project-character association operations."""
    
    def test_add_character_to_project(self, db_session, sample_character):
        """Test adding a character to a project."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        result = add_character_to_project(
            db_session,
            project.project_id,
            sample_character.character_id
        )
        assert result is True
        
        # Verify association exists
        characters = get_project_characters(db_session, project.project_id)
        assert len(characters) == 1
        assert characters[0].character_id == sample_character.character_id
    
    def test_add_character_idempotent(self, db_session, sample_character):
        """Test adding same character twice is idempotent."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        add_character_to_project(db_session, project.project_id, sample_character.character_id)
        add_character_to_project(db_session, project.project_id, sample_character.character_id)
        
        characters = get_project_characters(db_session, project.project_id)
        assert len(characters) == 1
    
    def test_remove_character_from_project(self, db_session, sample_character):
        """Test removing a character from a project."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        add_character_to_project(db_session, project.project_id, sample_character.character_id)
        
        result = remove_character_from_project(
            db_session,
            project.project_id,
            sample_character.character_id
        )
        assert result is True
        
        characters = get_project_characters(db_session, project.project_id)
        assert len(characters) == 0
    
    def test_get_project_characters_empty(self, db_session):
        """Test getting characters for project with no characters."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        characters = get_project_characters(db_session, project.project_id)
        assert len(characters) == 0


# =============================================================================
# Unit Tests for Dict Conversion
# =============================================================================

class TestDictConversion:
    """Tests for converting records to dicts."""
    
    def test_project_to_dict(self, db_session):
        """Test converting project record to dict."""
        project = create_project(
            db=db_session,
            topic="测试主题",
            target_audience="测试受众",
            key_points=["点1", "点2"]
        )
        
        result = project_to_dict(project)
        
        assert result["project_id"] == project.project_id
        assert result["status"] == "initialized"
        assert result["goal"]["topic"] == "测试主题"
        assert result["goal"]["target_audience"] == "测试受众"
        assert result["goal"]["key_points"] == ["点1", "点2"]
    
    def test_scene_to_dict(self, db_session):
        """Test converting scene record to dict."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        scene = create_scene(
            db_session,
            project.project_id,
            step_number=1,
            description_cn="场景描述",
            narration_cn="中文旁白",
            narration_en="English",
            duration=10,
            emotion="喜",
            character_ids=["char_001"]
        )
        
        result = scene_to_dict(scene)
        
        assert result["scene_id"] == scene.scene_id
        assert result["step_number"] == 1
        assert result["description_cn"] == "场景描述"
        assert result["duration"] == 10
        assert result["character_ids"] == ["char_001"]
        assert "image" in result
        assert "audio_cn" in result
        assert "audio_en" in result


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestPropertyBased:
    """Property-based tests using Hypothesis."""
    
    @given(
        topic=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        audience=st.text(min_size=0, max_size=100),
        key_points=st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=5)
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_create_project_properties(self, db_session, topic, audience, key_points):
        """Property: created project has correct data."""
        key_points = [kp for kp in key_points if kp.strip()]
        
        project = create_project(
            db=db_session,
            topic=topic.strip(),
            target_audience=audience,
            key_points=key_points
        )
        
        assert project.topic == topic.strip()
        assert project.target_audience == audience
        assert project.status == "initialized"
        
        loaded_kp = json.loads(project.key_points) if project.key_points else []
        assert loaded_kp == key_points
        
        # Cleanup
        delete_project(db_session, project.project_id)
    
    @given(
        step_number=st.integers(min_value=1, max_value=50),
        duration=st.sampled_from([5, 8, 10, 12, 15])
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_create_scene_properties(self, db_session, step_number, duration):
        """Property: created scene has correct data."""
        project = create_project(db=db_session, topic="测试", target_audience="", key_points=[])
        
        scene = create_scene(
            db=db_session,
            project_id=project.project_id,
            step_number=step_number,
            description_cn="描述",
            narration_cn="旁白",
            duration=duration
        )
        
        assert scene.step_number == step_number
        assert scene.duration == duration
        
        # Cleanup
        delete_project(db_session, project.project_id)
