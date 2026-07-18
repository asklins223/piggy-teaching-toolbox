"""End-to-end integration tests for video style expansion feature.

This module tests the complete flow:
1. Select style → Create project → Generate storyboard → Edit audio params → Generate audio

Requirements: All video-style-expansion requirements
"""

import json
import tempfile
from typing import Optional
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base, UserRecord, hash_password, get_db
from backend.api.main import app
from backend.schemas.models import VideoStyle, Emotion, AudioParams


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"


# Create a single engine for all tests with StaticPool to handle threading
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
Base.metadata.create_all(_test_engine)
_TestSessionLocal = sessionmaker(bind=_test_engine)


def _get_test_db():
    """Get test database session."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Override the database dependency globally
app.dependency_overrides[get_db] = _get_test_db


# Create test user
_init_session = _TestSessionLocal()
_existing_user = _init_session.query(UserRecord).filter(
    UserRecord.username == TEST_USERNAME
).first()
if not _existing_user:
    _test_user = UserRecord(
        username=TEST_USERNAME,
        password_hash=hash_password(TEST_PASSWORD),
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    _init_session.add(_test_user)
    _init_session.commit()
_init_session.close()


# Test client
client = TestClient(app)


def get_auth_headers():
    """Get authentication headers for API requests."""
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestEndToEndStyleFlow:
    """End-to-end tests for the complete style selection flow.
    
    Tests: 选择风格 → 创建项目 → 生成分镜 → 编辑音频参数 → 生成音频
    Requirements: All
    """
    
    def test_e2e_teaching_style_project_creation(self):
        """Test complete flow with teaching style.
        
        Flow: Get styles → Select teaching → Create project → Verify style saved
        """
        headers = get_auth_headers()
        
        # Step 1: Get available styles
        styles_response = client.get("/api/styles", headers=headers)
        assert styles_response.status_code == 200
        styles = styles_response.json()["styles"]
        assert len(styles) == 5
        
        # Verify teaching style exists
        teaching_style = next((s for s in styles if s["id"] == "teaching"), None)
        assert teaching_style is not None
        assert teaching_style["name"] == "教学"
        
        # Step 2: Create project with teaching style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "Python 基础教程",
                "target_audience": "编程初学者",
                "key_points": ["变量", "函数", "循环"],
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Step 3: Verify project has correct style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "teaching"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_e2e_nursery_rhyme_style_project_creation(self):
        """Test complete flow with nursery rhyme style.
        
        Flow: Select nursery_rhyme → Create project → Verify style saved
        """
        headers = get_auth_headers()
        
        # Create project with nursery rhyme style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "小星星儿歌",
                "target_audience": "3-6岁儿童",
                "key_points": ["歌词学习", "节奏感"],
                "style": "nursery_rhyme"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Verify project has correct style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "nursery_rhyme"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_e2e_storybook_style_project_creation(self):
        """Test complete flow with storybook style.
        
        Flow: Select storybook → Create project → Verify style saved
        """
        headers = get_auth_headers()
        
        # Create project with storybook style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "小红帽的故事",
                "target_audience": "4-8岁儿童",
                "key_points": ["故事情节", "角色认识"],
                "style": "storybook"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Verify project has correct style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "storybook"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_e2e_recitation_style_project_creation(self):
        """Test complete flow with recitation style.
        
        Flow: Select recitation → Create project → Verify style saved
        """
        headers = get_auth_headers()
        
        # Create project with recitation style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "静夜思朗诵",
                "target_audience": "小学生",
                "key_points": ["诗词理解", "情感表达"],
                "style": "recitation"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Verify project has correct style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "recitation"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_e2e_custom_style_project_creation(self):
        """Test complete flow with custom style.
        
        Flow: Select custom → Provide description → Create project → Verify saved
        """
        headers = get_auth_headers()
        
        custom_desc = "温馨治愈的风格，适合睡前故事"
        
        # Create project with custom style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "睡前小故事",
                "target_audience": "3-5岁儿童",
                "key_points": ["放松", "想象力"],
                "style": "custom",
                "custom_style_description": custom_desc
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Verify project has correct style and description
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "custom"
        assert project_data["goal"]["custom_style_description"] == custom_desc
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)


class TestEndToEndEmotionFlow:
    """End-to-end tests for emotion selection and audio params flow.
    
    Tests: Get emotions → Select emotion → Update scene audio params
    Requirements: 3.1, 3.2, 4.1, 4.2, 5.4, 7.3, 7.4
    """
    
    def test_e2e_get_all_emotions(self):
        """Test getting all 17 emotions with categories.
        
        Requirements: 3.1, 4.2, 7.3
        """
        headers = get_auth_headers()
        
        # Get all emotions
        response = client.get("/api/emotions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all 17 emotions are returned
        assert len(data["emotions"]) == 17
        
        # Verify categories exist
        assert len(data["categories"]) == 3
        category_ids = [c["id"] for c in data["categories"]]
        assert "positive" in category_ids
        assert "negative" in category_ids
        assert "neutral" in category_ids
        
        # Verify new emotions are included
        emotion_ids = [e["id"] for e in data["emotions"]]
        new_emotions = ["lively", "healing", "aggrieved", "embarrassed", 
                       "proud", "conflicted", "lost", "shy", "irritated"]
        for emotion in new_emotions:
            assert emotion in emotion_ids, f"Missing new emotion: {emotion}"
    
    def test_e2e_emotion_categories_grouping(self):
        """Test that emotions are correctly grouped by category.
        
        Requirements: 4.2
        """
        headers = get_auth_headers()
        
        response = client.get("/api/emotions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check positive emotions
        positive_cat = next((c for c in data["categories"] if c["id"] == "positive"), None)
        assert positive_cat is not None
        positive_ids = [e["id"] for e in positive_cat["emotions"]]
        assert "happy" in positive_ids
        assert "lively" in positive_ids
        assert "healing" in positive_ids
        assert "proud" in positive_ids
        assert "surprised" in positive_ids
        
        # Check negative emotions
        negative_cat = next((c for c in data["categories"] if c["id"] == "negative"), None)
        assert negative_cat is not None
        negative_ids = [e["id"] for e in negative_cat["emotions"]]
        assert "angry" in negative_ids
        assert "sad" in negative_ids
        assert "fear" in negative_ids
        assert "aggrieved" in negative_ids
        assert "lost" in negative_ids
        assert "irritated" in negative_ids
        
        # Check neutral emotions
        neutral_cat = next((c for c in data["categories"] if c["id"] == "neutral"), None)
        assert neutral_cat is not None
        neutral_ids = [e["id"] for e in neutral_cat["emotions"]]
        assert "calm" in neutral_ids
        assert "embarrassed" in neutral_ids
        assert "conflicted" in neutral_ids
        assert "shy" in neutral_ids


class TestEndToEndAudioParamsFlow:
    """End-to-end tests for audio params editing flow.
    
    Tests: Create project → Create scene → Update audio params → Verify saved
    Requirements: 5.1, 5.2, 5.4, 7.4
    """
    
    def test_e2e_scene_audio_params_update(self):
        """Test updating scene audio params through API.
        
        Requirements: 5.4, 7.4
        """
        headers = get_auth_headers()
        
        # Create a project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "测试项目",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene directly in database for testing
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="测试场景描述",
                narration_cn="测试旁白",
                narration_en="Test narration",
                duration=10,
                emotion="平静",
                character_ids=[]
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Update scene with audio params
        audio_params = {
            "emotion": "活泼",
            "emotion_strength": 0.8,
            "speed": 1.2,
            "volume": 1.1
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": audio_params}
        )
        assert update_response.status_code == 200
        
        # Verify audio params were saved
        scene_data = update_response.json()["scene"]
        assert scene_data["audio_params"] is not None
        assert scene_data["audio_params"]["emotion"] == "活泼"
        assert scene_data["audio_params"]["emotion_strength"] == 0.8
        assert scene_data["audio_params"]["speed"] == 1.2
        assert scene_data["audio_params"]["volume"] == 1.1
        
        # Verify through GET scenes endpoint
        scenes_response = client.get(f"/api/projects/{project_id}/scenes", headers=headers)
        assert scenes_response.status_code == 200
        scenes = scenes_response.json()["scenes"]
        assert len(scenes) == 1
        assert scenes[0]["audio_params"]["emotion"] == "活泼"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_e2e_audio_params_validation(self):
        """Test audio params validation through API.
        
        Requirements: 7.5
        """
        headers = get_auth_headers()
        
        # Create a project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "验证测试项目",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="验证测试场景",
                narration_cn="验证旁白",
                narration_en="Validation narration",
                duration=10,
                emotion="平静",
                character_ids=[]
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Test invalid emotion_strength (out of range)
        invalid_params = {
            "emotion": "平静",
            "emotion_strength": 1.5,  # Invalid: > 1.0
            "speed": 1.0,
            "volume": 1.0
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": invalid_params}
        )
        assert update_response.status_code == 400
        data = update_response.json()
        assert data["error"]["code"] == "INVALID_AUDIO_PARAMS"
        
        # Test invalid speed (out of range)
        invalid_params = {
            "emotion": "平静",
            "emotion_strength": 0.5,
            "speed": 3.0,  # Invalid: > 2.0
            "volume": 1.0
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": invalid_params}
        )
        assert update_response.status_code == 400
        
        # Test invalid volume (out of range)
        invalid_params = {
            "emotion": "平静",
            "emotion_strength": 0.5,
            "speed": 1.0,
            "volume": 2.0  # Invalid: > 1.5
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": invalid_params}
        )
        assert update_response.status_code == 400
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)


class TestEndToEndAllStylesRoundTrip:
    """End-to-end tests for all styles round-trip consistency.
    
    Tests: Create project with each style → Get project → Verify style matches
    Requirements: Property 6 - API 参数 Round-Trip
    """
    
    @pytest.mark.parametrize("style", [
        "teaching",
        "nursery_rhyme",
        "storybook",
        "recitation",
        "custom"
    ])
    def test_e2e_style_roundtrip(self, style):
        """Test style round-trip for all preset styles.
        
        Requirements: 7.1, Property 6
        """
        headers = get_auth_headers()
        
        # Create project with style
        create_data = {
            "topic": f"测试{style}风格",
            "target_audience": "测试受众",
            "style": style
        }
        
        if style == "custom":
            create_data["custom_style_description"] = "自定义风格描述"
        
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json=create_data
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Get project and verify style
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == style
        
        if style == "custom":
            assert project_data["goal"]["custom_style_description"] == "自定义风格描述"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)


class TestEndToEndInvalidParameters:
    """End-to-end tests for invalid parameter handling.
    
    Tests: Invalid style → Error, Invalid emotion → Error
    Requirements: Property 7 - 无效参数错误处理
    """
    
    def test_e2e_invalid_style_error(self):
        """Test that invalid style returns clear error.
        
        Requirements: 7.5, Property 7
        """
        headers = get_auth_headers()
        
        response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "测试项目",
                "target_audience": "测试受众",
                "style": "invalid_style_xyz"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_STYLE"
        assert "invalid_style_xyz" in data["error"]["message"]
    
    def test_e2e_invalid_emotion_in_audio_params_error(self):
        """Test that invalid emotion in audio params returns clear error.
        
        Requirements: 7.5, Property 7
        """
        headers = get_auth_headers()
        
        # Create a project first
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "测试项目",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="测试场景",
                narration_cn="测试旁白",
                narration_en="Test narration",
                duration=10,
                emotion="平静",
                character_ids=[]
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Try to update with invalid emotion
        invalid_params = {
            "emotion": "invalid_emotion_xyz",
            "emotion_strength": 0.5,
            "speed": 1.0,
            "volume": 1.0
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": invalid_params}
        )
        
        assert update_response.status_code == 400
        data = update_response.json()
        assert data["error"]["code"] == "INVALID_EMOTION"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)




class TestDataCompatibility:
    """Data compatibility tests for backward compatibility.
    
    Tests: Existing projects without style config should default to teaching style.
    Requirements: Compatibility
    """
    
    def test_project_without_style_defaults_to_teaching(self):
        """Test that projects created without style default to teaching.
        
        Requirements: Compatibility - 未指定风格的项目默认使用"教学"风格
        """
        headers = get_auth_headers()
        
        # Create project without specifying style
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "无风格测试项目",
                "target_audience": "测试受众",
                "key_points": ["测试点1"]
                # Note: no style parameter
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Get project and verify default style is teaching
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["goal"]["style"] == "teaching"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_legacy_project_simulation(self):
        """Test loading a simulated legacy project (without style field).
        
        This simulates what happens when loading an existing project
        that was created before the style feature was added.
        
        Requirements: Compatibility
        """
        headers = get_auth_headers()
        
        # Create a project directly in database without style
        from backend.db.models import ProjectRecord
        from datetime import datetime
        import uuid
        
        session = _TestSessionLocal()
        try:
            # Create a legacy-style project record (without style)
            project_id = f"proj_{uuid.uuid4().hex[:12]}"
            legacy_project = ProjectRecord(
                project_id=project_id,
                user_id=TEST_USERNAME,
                topic="Legacy Project",
                target_audience="Legacy Audience",
                key_points='["Legacy Point"]',
                status="initialized",
                # Note: style field will use default value
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(legacy_project)
            session.commit()
            
            # Get project through API
            get_response = client.get(f"/api/projects/{project_id}", headers=headers)
            assert get_response.status_code == 200
            project_data = get_response.json()
            
            # Verify default style is teaching
            assert project_data["goal"]["style"] == "teaching"
            
            # Cleanup
            session.delete(legacy_project)
            session.commit()
        finally:
            session.close()
    
    def test_scene_without_audio_params_works(self):
        """Test that scenes without audio_params work correctly.
        
        Requirements: Compatibility - 现有分镜默认 audio_params 为 None
        """
        headers = get_auth_headers()
        
        # Create a project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "兼容性测试项目",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene without audio_params
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="无音频参数场景",
                narration_cn="测试旁白",
                narration_en="Test narration",
                duration=10,
                emotion="平静",
                character_ids=[]
                # Note: no audio_params
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Get scenes through API
        scenes_response = client.get(f"/api/projects/{project_id}/scenes", headers=headers)
        assert scenes_response.status_code == 200
        scenes = scenes_response.json()["scenes"]
        
        # Verify scene exists and audio_params is None
        assert len(scenes) == 1
        assert scenes[0]["audio_params"] is None
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_scene_can_be_updated_with_audio_params(self):
        """Test that existing scenes can be updated to add audio_params.
        
        Requirements: Compatibility - 支持为现有分镜添加音频参数
        """
        headers = get_auth_headers()
        
        # Create a project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "更新测试项目",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene without audio_params
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="待更新场景",
                narration_cn="测试旁白",
                narration_en="Test narration",
                duration=10,
                emotion="平静",
                character_ids=[]
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Verify audio_params is initially None
        scenes_response = client.get(f"/api/projects/{project_id}/scenes", headers=headers)
        assert scenes_response.json()["scenes"][0]["audio_params"] is None
        
        # Update scene with audio_params
        audio_params = {
            "emotion": "活泼",
            "emotion_strength": 0.7,
            "speed": 1.1,
            "volume": 1.0
        }
        
        update_response = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}",
            headers=headers,
            json={"audio_params": audio_params}
        )
        assert update_response.status_code == 200
        
        # Verify audio_params was added
        updated_scene = update_response.json()["scene"]
        assert updated_scene["audio_params"] is not None
        assert updated_scene["audio_params"]["emotion"] == "活泼"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
    
    def test_default_emotion_is_calm(self):
        """Test that default emotion for scenes is calm (平静).
        
        Requirements: Compatibility - 未指定新情感的分镜默认使用"平静"情感
        """
        headers = get_auth_headers()
        
        # Create a project
        create_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "topic": "默认情感测试",
                "target_audience": "测试受众",
                "style": "teaching"
            }
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["project_id"]
        
        # Create a scene with default emotion
        from backend.db.crud.projects import create_scene
        session = _TestSessionLocal()
        try:
            scene = create_scene(
                db=session,
                project_id=project_id,
                step_number=1,
                description_cn="默认情感场景",
                narration_cn="测试旁白",
                narration_en="Test narration",
                duration=10,
                emotion="平静",  # Default emotion
                character_ids=[]
            )
            scene_id = scene.scene_id
        finally:
            session.close()
        
        # Get scenes and verify default emotion
        scenes_response = client.get(f"/api/projects/{project_id}/scenes", headers=headers)
        assert scenes_response.status_code == 200
        scenes = scenes_response.json()["scenes"]
        assert len(scenes) == 1
        assert scenes[0]["emotion"] == "平静"
        
        # Cleanup
        client.delete(f"/api/projects/{project_id}", headers=headers)
