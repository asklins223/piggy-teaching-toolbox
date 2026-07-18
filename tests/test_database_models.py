"""Tests for database models.

Tests the database models including ProjectRecord, SceneRecord, 
CharacterRecord, and ProjectCharacterRecord.
"""

import json
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import (
    Base, UserRecord, VoiceRecord, CharacterRecord,
    ProjectRecord, SceneRecord, ProjectCharacterRecord,
    hash_password, verify_password
)


# Test database setup
@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# =============================================================================
# Unit Tests for Database Models
# =============================================================================

class TestUserRecord:
    """Tests for UserRecord model."""
    
    def test_create_user(self, db_session):
        """Test creating a user record."""
        user = UserRecord(
            username="testuser",
            password_hash=hash_password("password123"),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_admin is False
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "secure_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestCharacterRecord:
    """Tests for CharacterRecord model."""
    
    def test_create_character(self, db_session):
        """Test creating a character record."""
        char = CharacterRecord(
            character_id="char_123456_7890",
            name="小橘猫",
            description="可爱的橘色猫咪",
            user_id="user_001",
            cos_url="https://cos.example.com/char.png",
            cos_key="characters/char_123456_7890.png"
        )
        db_session.add(char)
        db_session.commit()
        
        assert char.id is not None
        assert char.character_id == "char_123456_7890"
        assert char.name == "小橘猫"
        assert char.cos_url == "https://cos.example.com/char.png"
    
    def test_character_unique_id(self, db_session):
        """Test that character_id must be unique."""
        char1 = CharacterRecord(
            character_id="char_unique_001",
            name="角色1"
        )
        db_session.add(char1)
        db_session.commit()
        
        char2 = CharacterRecord(
            character_id="char_unique_001",  # Same ID
            name="角色2"
        )
        db_session.add(char2)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestProjectRecord:
    """Tests for ProjectRecord model."""
    
    def test_create_project(self, db_session):
        """Test creating a project record."""
        key_points = ["知识点1", "知识点2", "知识点3"]
        
        project = ProjectRecord(
            project_id="proj_abc12345",
            user_id="user_001",
            status="initialized",
            topic="小学英语：动物词汇",
            target_audience="小学3年级学生",
            key_points=json.dumps(key_points, ensure_ascii=False)
        )
        db_session.add(project)
        db_session.commit()
        
        assert project.id is not None
        assert project.project_id == "proj_abc12345"
        assert project.topic == "小学英语：动物词汇"
        assert project.status == "initialized"
        
        # Verify key_points JSON
        loaded_points = json.loads(project.key_points)
        assert loaded_points == key_points
    
    def test_project_status_update(self, db_session):
        """Test updating project status."""
        project = ProjectRecord(
            project_id="proj_status_test",
            topic="测试主题",
            status="initialized"
        )
        db_session.add(project)
        db_session.commit()
        
        # Update status
        project.status = "storyboard_ready"
        project.storyboard_title = "测试分镜"
        project.total_duration = 60
        db_session.commit()
        
        # Reload and verify
        db_session.refresh(project)
        assert project.status == "storyboard_ready"
        assert project.storyboard_title == "测试分镜"
        assert project.total_duration == 60


class TestSceneRecord:
    """Tests for SceneRecord model."""
    
    def test_create_scene(self, db_session):
        """Test creating a scene record."""
        scene = SceneRecord(
            scene_id="scene_001",
            project_id="proj_001",
            step_number=1,
            description_cn="一只可爱的小猫在草地上玩耍",
            narration_cn="今天我们来学习动物词汇",
            narration_en="Today we will learn animal vocabulary",
            duration=10,
            emotion="喜",
            character_ids=json.dumps(["char_001", "char_002"])
        )
        db_session.add(scene)
        db_session.commit()
        
        assert scene.id is not None
        assert scene.scene_id == "scene_001"
        assert scene.step_number == 1
        assert scene.duration == 10
        
        # Verify character_ids JSON
        char_ids = json.loads(scene.character_ids)
        assert char_ids == ["char_001", "char_002"]
    
    def test_scene_image_update(self, db_session):
        """Test updating scene image info."""
        scene = SceneRecord(
            scene_id="scene_img_test",
            project_id="proj_001",
            step_number=1,
            description_cn="测试场景"
        )
        db_session.add(scene)
        db_session.commit()
        
        # Update image info
        scene.image_status = "completed"
        scene.image_cos_url = "https://cos.example.com/scene.png"
        scene.image_cos_key = "projects/proj_001/images/scene_img_test.png"
        db_session.commit()
        
        db_session.refresh(scene)
        assert scene.image_status == "completed"
        assert scene.image_cos_url == "https://cos.example.com/scene.png"
    
    def test_scene_audio_update(self, db_session):
        """Test updating scene audio info."""
        scene = SceneRecord(
            scene_id="scene_audio_test",
            project_id="proj_001",
            step_number=1,
            description_cn="测试场景"
        )
        db_session.add(scene)
        db_session.commit()
        
        # Update audio info
        scene.audio_cn_status = "completed"
        scene.audio_cn_cos_url = "https://cos.example.com/audio_cn.wav"
        scene.audio_cn_duration = 5000  # 5 seconds in ms
        scene.audio_en_status = "completed"
        scene.audio_en_cos_url = "https://cos.example.com/audio_en.wav"
        scene.audio_en_duration = 4500
        db_session.commit()
        
        db_session.refresh(scene)
        assert scene.audio_cn_status == "completed"
        assert scene.audio_cn_duration == 5000
        assert scene.audio_en_duration == 4500


class TestProjectCharacterRecord:
    """Tests for ProjectCharacterRecord model."""
    
    def test_create_association(self, db_session):
        """Test creating project-character association."""
        assoc = ProjectCharacterRecord(
            project_id="proj_001",
            character_id="char_001"
        )
        db_session.add(assoc)
        db_session.commit()
        
        assert assoc.id is not None
        assert assoc.project_id == "proj_001"
        assert assoc.character_id == "char_001"
    
    def test_multiple_characters_per_project(self, db_session):
        """Test adding multiple characters to a project."""
        for i in range(3):
            assoc = ProjectCharacterRecord(
                project_id="proj_multi",
                character_id=f"char_{i:03d}"
            )
            db_session.add(assoc)
        db_session.commit()
        
        # Query associations
        assocs = db_session.query(ProjectCharacterRecord).filter(
            ProjectCharacterRecord.project_id == "proj_multi"
        ).all()
        
        assert len(assocs) == 3


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestPropertyBased:
    """Property-based tests using Hypothesis."""
    
    @given(
        username=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        password=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=20)
    def test_password_hash_properties(self, username, password):
        """Property: password hashing is deterministic and verifiable."""
        hashed = hash_password(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Same password should produce same hash
        assert hash_password(password) == hashed
        
        # Verification should work
        assert verify_password(password, hashed) is True
    
    @given(
        topic=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        audience=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        key_points=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10)
    )
    @settings(max_examples=20)
    def test_project_key_points_json_roundtrip(self, topic, audience, key_points):
        """Property: key_points JSON serialization is reversible."""
        # Filter out empty strings
        key_points = [kp for kp in key_points if kp.strip()]
        
        # Serialize
        json_str = json.dumps(key_points, ensure_ascii=False)
        
        # Deserialize
        loaded = json.loads(json_str)
        
        assert loaded == key_points
    
    @given(
        character_ids=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=5, max_size=20),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_scene_character_ids_json_roundtrip(self, character_ids):
        """Property: character_ids JSON serialization is reversible."""
        json_str = json.dumps(character_ids)
        loaded = json.loads(json_str)
        assert loaded == character_ids
    
    @given(
        duration=st.integers(min_value=5, max_value=15),
        step_number=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=20)
    def test_scene_duration_constraints(self, duration, step_number):
        """Property: scene duration and step_number are within valid ranges."""
        assert 5 <= duration <= 15
        assert step_number >= 1
    
    @given(
        status=st.sampled_from([
            "initialized", "storyboard_ready", "images_ready",
            "audio_ready", "subtitles_ready", "completed"
        ])
    )
    @settings(max_examples=10)
    def test_project_status_valid_values(self, status):
        """Property: project status is one of the valid values."""
        valid_statuses = {
            "initialized", "storyboard_ready", "images_ready",
            "audio_ready", "subtitles_ready", "completed"
        }
        assert status in valid_statuses
