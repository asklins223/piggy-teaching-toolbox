"""Unit tests for the WebInterface class.

Tests the Gradio web interface creation and basic functionality.

Requirements: 5.1
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from backend.web_interface import WebInterface
from backend.core.orchestrator import Orchestrator
from backend.services.storage import StorageManager
from backend.config import WebConfig
from backend.schemas.models import (
    TeachingGoal,
    ProjectState,
    ProjectStatus,
    Storyboard,
    Scene,
    SceneDuration,
    Emotion,
)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.create_project = AsyncMock(return_value="proj_test123")
    orchestrator.generate_storyboard = AsyncMock()
    orchestrator.generate_images = AsyncMock(return_value=[])
    orchestrator.generate_audios = AsyncMock(return_value=[])
    orchestrator.generate_subtitles = AsyncMock(return_value=[])
    orchestrator.export_assets = AsyncMock()
    orchestrator.regenerate_scene_image = AsyncMock()
    orchestrator.update_scene = AsyncMock()
    orchestrator.generate_characters = AsyncMock(return_value=[])
    return orchestrator


@pytest.fixture
def mock_storage_manager(temp_dir):
    """Create a mock storage manager."""
    storage = MagicMock(spec=StorageManager)
    storage.list_projects = MagicMock(return_value=["proj_001", "proj_002"])
    storage.load_project = MagicMock()
    return storage


@pytest.fixture
def web_config():
    """Create a test web configuration."""
    return WebConfig(
        host="127.0.0.1",
        port=7861,
        share=False,
        title="Test Video Generator"
    )


@pytest.fixture
def web_interface(mock_orchestrator, mock_storage_manager, web_config):
    """Create a WebInterface instance for testing."""
    return WebInterface(
        orchestrator=mock_orchestrator,
        storage_manager=mock_storage_manager,
        config=web_config
    )


class TestWebInterfaceCreation:
    """Tests for WebInterface creation and initialization."""
    
    def test_web_interface_initialization(
        self,
        mock_orchestrator,
        mock_storage_manager,
        web_config
    ):
        """Test that WebInterface initializes correctly.
        
        Requirements: 5.1
        """
        interface = WebInterface(
            orchestrator=mock_orchestrator,
            storage_manager=mock_storage_manager,
            config=web_config
        )
        
        assert interface._orchestrator is mock_orchestrator
        assert interface._storage_manager is mock_storage_manager
        assert interface._config is web_config
        assert interface._app is None
        assert interface._progress_messages == []
    
    def test_create_interface_returns_gradio_blocks(self, web_interface):
        """Test that create_interface returns a Gradio Blocks instance.
        
        Requirements: 5.1
        """
        app = web_interface.create_interface()
        
        # Check that app is created
        assert app is not None
        assert web_interface._app is app
        assert web_interface.app is app
    
    def test_create_interface_has_correct_title(self, web_interface, web_config):
        """Test that the interface has the correct title.
        
        Requirements: 5.1
        """
        app = web_interface.create_interface()
        
        # The title is set in the Blocks configuration
        assert app.title == web_config.title


class TestProjectCreation:
    """Tests for project creation functionality."""
    
    def test_create_project_success(self, web_interface, mock_orchestrator):
        """Test successful project creation.
        
        Requirements: 5.1
        """
        project_id, status, next_step, step_bar = web_interface._create_project(
            topic="Python 基础",
            target_audience="初学者",
            key_points="变量, 数据类型"
        )
        
        assert project_id == "proj_test123"
        assert "成功" in status
        assert next_step == 2  # Should go to step 2 (角色设定)
    
    def test_create_project_parses_key_points(self, web_interface, mock_orchestrator):
        """Test that key points are correctly parsed.
        
        Requirements: 5.1
        """
        web_interface._create_project(
            topic="Test Topic",
            target_audience="Test Audience",
            key_points="point1, point2, point3"
        )
        
        # Verify the orchestrator was called
        mock_orchestrator.create_project.assert_called_once()
        call_args = mock_orchestrator.create_project.call_args
        goal = call_args[0][0]  # First positional argument
        
        assert isinstance(goal, TeachingGoal)
        assert goal.topic == "Test Topic"
        assert goal.key_points == ["point1", "point2", "point3"]
    
    def test_create_project_handles_error(self, web_interface, mock_orchestrator):
        """Test error handling during project creation.
        
        Requirements: 5.1
        """
        mock_orchestrator.create_project = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        project_id, status, next_step, step_bar = web_interface._create_project(
            topic="Test",
            target_audience="Test",
            key_points=""
        )
        
        assert project_id == ""
        assert "失败" in status
        assert next_step == 1  # Should stay on step 1
    
    def test_create_project_empty_topic(self, web_interface):
        """Test that empty topic returns error."""
        project_id, status, next_step, step_bar = web_interface._create_project(
            topic="",
            target_audience="Test",
            key_points=""
        )
        
        assert project_id == ""
        assert "请输入教学主题" in status
        assert next_step == 1


class TestProjectLoading:
    """Tests for project loading functionality."""
    
    def test_list_projects(self, web_interface, mock_storage_manager):
        """Test listing available projects."""
        projects = web_interface._list_projects()
        
        assert projects == ["proj_001", "proj_002"]
        mock_storage_manager.list_projects.assert_called_once()
    
    def test_load_project_success(self, web_interface, mock_storage_manager):
        """Test successful project loading."""
        # Setup mock project state
        mock_state = MagicMock(spec=ProjectState)
        mock_state.project_id = "proj_001"
        mock_state.status = ProjectStatus.STORYBOARD_READY
        mock_state.goal = TeachingGoal(
            topic="Test Topic",
            target_audience="Test Audience",
            key_points=["point1"]
        )
        mock_state.storyboard = MagicMock()
        mock_state.storyboard.scenes = [MagicMock()]
        mock_state.images = []
        mock_state.audios = []
        mock_state.characters = []
        
        mock_storage_manager.load_project.return_value = mock_state
        
        project_id, info, status, next_step, step_bar = web_interface._load_project("proj_001")
        
        assert project_id == "proj_001"
        assert "成功" in status
        assert next_step == 4  # Has storyboard, should go to edit step
    
    def test_load_project_not_found(self, web_interface, mock_storage_manager):
        """Test loading a non-existent project."""
        from backend.services.storage import ProjectNotFoundError
        
        mock_storage_manager.load_project.side_effect = ProjectNotFoundError("proj_999")
        
        project_id, info, status, next_step, step_bar = web_interface._load_project("proj_999")
        
        assert project_id == ""
        assert "不存在" in status
        assert next_step == 1
    
    def test_load_project_empty_id(self, web_interface):
        """Test loading with empty project ID."""
        project_id, info, status, next_step, step_bar = web_interface._load_project("")
        
        assert project_id == ""
        assert "请输入项目 ID" in status
        assert next_step == 1


class TestProgressTracking:
    """Tests for progress tracking functionality."""
    
    def test_progress_callback(self, web_interface):
        """Test progress callback updates messages.
        
        Requirements: 5.7
        """
        web_interface._progress_callback("images", "Generating image 1", 1, 5)
        web_interface._progress_callback("images", "Generating image 2", 2, 5)
        
        progress = web_interface._get_progress()
        
        assert "Generating image 1" in progress
        assert "Generating image 2" in progress
    
    def test_progress_limits_messages(self, web_interface):
        """Test that progress limits the number of messages.
        
        Requirements: 5.7
        """
        # Add more than 15 messages
        for i in range(20):
            web_interface._progress_callback("test", f"Message {i}", i, 20)
        
        progress = web_interface._get_progress()
        lines = progress.strip().split("\n")
        
        # Should only show last 15 messages
        assert len(lines) <= 15


class TestSceneOperations:
    """Tests for scene-related operations."""
    
    def test_preview_scene_returns_paths(self, web_interface, mock_storage_manager):
        """Test getting scene preview (image and audio paths).
        
        Requirements: 5.5
        """
        from backend.schemas.models import SceneImage, SceneAudio, ResourceStatus
        
        mock_scene = MagicMock()
        mock_scene.scene_id = "scene_001"
        
        mock_storyboard = MagicMock()
        mock_storyboard.scenes = [mock_scene]
        
        mock_state = MagicMock()
        mock_state.storyboard = mock_storyboard
        mock_state.images = [
            SceneImage(
                scene_id="scene_001",
                image_path="/path/to/image.png",
                prompt_used="test prompt",
                status=ResourceStatus.COMPLETED
            )
        ]
        mock_state.audios = [
            SceneAudio(
                scene_id="scene_001",
                audio_path="/path/to/audio_cn.wav",
                audio_path_en="/path/to/audio_en.wav",
                duration_seconds=5.0,
                status=ResourceStatus.COMPLETED
            )
        ]
        mock_storage_manager.load_project.return_value = mock_state
        
        image_path, audio_cn_path, audio_en_path = web_interface._preview_scene("proj_001", 0)
        
        assert image_path == "/path/to/image.png"
        assert audio_cn_path == "/path/to/audio_cn.wav"
        assert audio_en_path == "/path/to/audio_en.wav"
    
    def test_preview_scene_returns_none_for_missing(
        self,
        web_interface,
        mock_storage_manager
    ):
        """Test getting preview for non-existent scene.
        
        Requirements: 5.5
        """
        mock_state = MagicMock()
        mock_state.storyboard = None
        mock_state.images = []
        mock_state.audios = []
        mock_storage_manager.load_project.return_value = mock_state
        
        image_path, audio_cn_path, audio_en_path = web_interface._preview_scene("proj_001", 0)
        
        assert image_path is None
        assert audio_cn_path is None
        assert audio_en_path is None
    
    def test_preview_scene_invalid_index(self, web_interface):
        """Test preview with invalid scene index."""
        image_path, audio_cn_path, audio_en_path = web_interface._preview_scene("proj_001", -1)
        
        assert image_path is None
        assert audio_cn_path is None
        assert audio_en_path is None
    
    def test_preview_scene_no_project(self, web_interface):
        """Test preview with no project ID."""
        image_path, audio_cn_path, audio_en_path = web_interface._preview_scene("", 0)
        
        assert image_path is None
        assert audio_cn_path is None
        assert audio_en_path is None


class TestCharacterOperations:
    """Tests for character-related operations."""
    
    def test_get_characters(self, web_interface, mock_storage_manager):
        """Test getting character list."""
        from backend.schemas.models import CharacterReference
        
        mock_char = MagicMock()
        mock_char.character_id = "char_001"
        mock_char.name = "小明"
        mock_char.image_path = "/path/to/char.png"
        
        mock_state = MagicMock()
        mock_state.characters = [mock_char]
        mock_storage_manager.load_project.return_value = mock_state
        
        chars = web_interface._get_characters("proj_001")
        
        assert len(chars) == 1
        assert chars[0]["id"] == "char_001"
        assert chars[0]["name"] == "小明"
    
    def test_get_characters_empty(self, web_interface):
        """Test getting characters with no project."""
        chars = web_interface._get_characters("")
        assert chars == []
    
    def test_add_character_success(self, web_interface, mock_orchestrator, mock_storage_manager):
        """Test adding a character."""
        from backend.schemas.models import CharacterReference
        
        mock_char = MagicMock()
        mock_char.character_id = "char_new"
        mock_char.name = "新角色"
        mock_char.image_path = "/path/to/new_char.png"
        
        mock_orchestrator.generate_characters = AsyncMock(return_value=[mock_char])
        
        mock_state = MagicMock()
        mock_state.characters = [mock_char]
        mock_storage_manager.load_project.return_value = mock_state
        
        chars, img_path, status = web_interface._add_character(
            "proj_001", "新角色", "一个测试角色"
        )
        
        assert "成功" in status
        assert img_path == "/path/to/new_char.png"
    
    def test_add_character_empty_name(self, web_interface, mock_storage_manager):
        """Test adding character with empty name."""
        mock_state = MagicMock()
        mock_state.characters = []
        mock_storage_manager.load_project.return_value = mock_state
        
        chars, img_path, status = web_interface._add_character(
            "proj_001", "", "描述"
        )
        
        assert "请输入角色名称" in status
        assert img_path is None


class TestSceneEditing:
    """Tests for scene editing operations."""
    
    def test_update_scene_success(self, web_interface, mock_orchestrator):
        """Test updating a scene."""
        status = web_interface._update_scene(
            "proj_001", "scene_001",
            "新描述", "新旁白", "new prompt"
        )
        
        assert "已更新" in status
        mock_orchestrator.update_scene.assert_called_once()
    
    def test_update_scene_no_changes(self, web_interface):
        """Test updating scene with no changes."""
        status = web_interface._update_scene(
            "proj_001", "scene_001", "", "", ""
        )
        
        assert "没有修改" in status
    
    def test_update_scene_no_project(self, web_interface):
        """Test updating scene with no project."""
        status = web_interface._update_scene(
            "", "scene_001", "desc", "narr", "prompt"
        )
        
        assert "请选择" in status
    
    def test_regenerate_scene_image(self, web_interface, mock_orchestrator):
        """Test regenerating a scene image."""
        from backend.schemas.models import SceneImage, ResourceStatus
        
        mock_image = SceneImage(
            scene_id="scene_001",
            image_path="/path/to/new_image.png",
            prompt_used="test",
            status=ResourceStatus.COMPLETED
        )
        mock_orchestrator.regenerate_scene_image = AsyncMock(return_value=mock_image)
        
        img_path, status = web_interface._regenerate_scene_image("proj_001", "scene_001")
        
        assert img_path == "/path/to/new_image.png"
        assert "已重新生成" in status
