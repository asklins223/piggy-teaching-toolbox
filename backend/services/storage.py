"""Storage management module for project persistence.

This module provides the StorageManager class for saving and loading project state,
managing project directory structure, and handling resource file associations.

Requirements: 7.1, 7.2, 7.3, 7.4
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import StorageConfig, get_settings
from backend.schemas.models import ProjectState


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class ProjectNotFoundError(StorageError):
    """Raised when a project cannot be found."""
    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project not found: {project_id}")


class StorageManager:
    """Manages project state persistence and resource file organization.
    
    This class handles:
    - Creating project directory structures
    - Saving and loading project state as JSON
    - Managing resource file paths (images, audios, prompts, subtitles, export)
    - Maintaining associations between project data and resource files
    
    Directory structure:
        {base_dir}/
        └── {project_id}/
            ├── project.json          # Project state
            ├── images/               # Scene images
            │   ├── scene_001.png
            │   └── scene_002.png
            ├── audios/               # Scene audio files
            │   ├── scene_001.wav
            │   └── scene_002.wav
            ├── prompts/              # Video generation prompts
            │   ├── scene_001.txt
            │   └── scene_002.txt
            ├── subtitles/            # Subtitle files
            │   ├── scene_001_cn.srt
            │   ├── scene_001_en.srt
            │   ├── full_cn.srt
            │   └── full_en.srt
            └── export/               # Export packages
                ├── manifest.json
                └── assets.zip
    
    Requirements: 7.1, 7.2, 7.3, 7.4
    """
    
    def __init__(self, base_dir: Optional[str] = None, config: Optional[StorageConfig] = None):
        """Initialize the StorageManager.
        
        Args:
            base_dir: Base directory for project storage. If None, uses config.
            config: Storage configuration. If None, uses global settings.
        """
        if config is None:
            config = get_settings().storage
        
        self._config = config
        self._base_dir = Path(base_dir) if base_dir else config.base_dir
    
    @property
    def base_dir(self) -> Path:
        """Get the base directory for project storage."""
        return self._base_dir
    
    def _get_project_dir(self, project_id: str) -> Path:
        """Get the directory path for a project.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            Path to the project directory.
        """
        return self._base_dir / project_id
    
    def _get_project_file(self, project_id: str) -> Path:
        """Get the path to the project state file.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            Path to the project.json file.
        """
        return self._get_project_dir(project_id) / self._config.project_file
    
    def _ensure_project_structure(self, project_id: str) -> Path:
        """Create the project directory structure if it doesn't exist.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            Path to the project directory.
        """
        project_dir = self._get_project_dir(project_id)
        
        # Create main project directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for new structure
        (project_dir / self._config.images_subdir).mkdir(exist_ok=True)
        (project_dir / self._config.audios_subdir).mkdir(exist_ok=True)
        (project_dir / self._config.prompts_subdir).mkdir(exist_ok=True)
        (project_dir / self._config.subtitles_subdir).mkdir(exist_ok=True)
        (project_dir / self._config.export_subdir).mkdir(exist_ok=True)
        
        # Create legacy subdirectories for backward compatibility
        (project_dir / "characters").mkdir(exist_ok=True)
        (project_dir / "clips").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)
        
        return project_dir
    
    def save_project(self, state: ProjectState) -> str:
        """Save project state to JSON file.
        
        Creates the project directory structure if it doesn't exist,
        updates the timestamp, and writes the state to project.json.
        
        Args:
            state: The project state to save.
            
        Returns:
            Path to the saved project file.
            
        Requirements: 7.1, 7.2
        """
        # Ensure directory structure exists
        self._ensure_project_structure(state.project_id)
        
        # Update timestamp
        state.update_timestamp()
        
        # Get project file path
        project_file = self._get_project_file(state.project_id)
        
        # Write state to JSON
        project_file.write_text(state.to_json(), encoding="utf-8")
        
        return str(project_file)
    
    def load_project(self, project_id: str) -> ProjectState:
        """Load project state from JSON file.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            The loaded project state.
            
        Raises:
            ProjectNotFoundError: If the project doesn't exist.
            
        Requirements: 7.3
        """
        project_file = self._get_project_file(project_id)
        
        if not project_file.exists():
            raise ProjectNotFoundError(project_id)
        
        json_str = project_file.read_text(encoding="utf-8")
        return ProjectState.from_json(json_str)
    
    def get_resource_path(
        self, 
        project_id: str, 
        resource_type: str, 
        filename: str
    ) -> str:
        """Get the full path for a resource file.
        
        Args:
            project_id: The project identifier.
            resource_type: Type of resource ("images", "audios", "prompts", "subtitles", "export").
            filename: The resource filename.
            
        Returns:
            Full path to the resource file.
            
        Raises:
            ValueError: If resource_type is invalid.
            
        Requirements: 7.4
        """
        type_to_subdir = {
            "images": self._config.images_subdir,
            "audios": self._config.audios_subdir,
            "prompts": self._config.prompts_subdir,
            "subtitles": self._config.subtitles_subdir,
            "export": self._config.export_subdir,
            # Legacy support
            "characters": "characters",
            "clips": "clips",
            "output": "output",
        }
        
        if resource_type not in type_to_subdir:
            raise ValueError(
                f"Invalid resource type: {resource_type}. "
                f"Must be one of: {list(type_to_subdir.keys())}"
            )
        
        subdir = type_to_subdir[resource_type]
        return str(self._get_project_dir(project_id) / subdir / filename)
    
    def project_exists(self, project_id: str) -> bool:
        """Check if a project exists.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            True if the project exists, False otherwise.
        """
        return self._get_project_file(project_id).exists()
    
    def list_projects(self) -> list[str]:
        """List all project IDs in the storage directory.
        
        Returns:
            List of project IDs.
        """
        if not self._base_dir.exists():
            return []
        
        projects = []
        for item in self._base_dir.iterdir():
            if item.is_dir():
                project_file = item / self._config.project_file
                if project_file.exists():
                    projects.append(item.name)
        
        return sorted(projects)
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its resources.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            True if the project was deleted, False if it didn't exist.
        """
        import shutil
        
        project_dir = self._get_project_dir(project_id)
        
        if not project_dir.exists():
            return False
        
        shutil.rmtree(project_dir)
        return True
    
    def get_project_resources(self, project_id: str) -> dict[str, list[str]]:
        """Get all resource files for a project.
        
        Args:
            project_id: The project identifier.
            
        Returns:
            Dictionary mapping resource types to lists of file paths.
        """
        project_dir = self._get_project_dir(project_id)
        
        resources = {
            "images": [],
            "audios": [],
            "prompts": [],
            "subtitles": [],
            "export": [],
            # Legacy support
            "characters": [],
            "clips": [],
            "output": [],
        }
        
        type_to_subdir = {
            "images": self._config.images_subdir,
            "audios": self._config.audios_subdir,
            "prompts": self._config.prompts_subdir,
            "subtitles": self._config.subtitles_subdir,
            "export": self._config.export_subdir,
            # Legacy support
            "characters": "characters",
            "clips": "clips",
            "output": "output",
        }
        
        for resource_type, subdir in type_to_subdir.items():
            subdir_path = project_dir / subdir
            if subdir_path.exists():
                resources[resource_type] = [
                    str(f) for f in subdir_path.iterdir() if f.is_file()
                ]
        
        return resources
    
    def verify_resource_integrity(self, state: ProjectState) -> dict[str, list[str]]:
        """Verify that all referenced resources exist.
        
        Checks that all resource paths referenced in the project state
        point to existing files.
        
        Args:
            state: The project state to verify.
            
        Returns:
            Dictionary with "missing" and "valid" lists of resource paths.
            
        Requirements: 7.4
        """
        missing = []
        valid = []
        
        project_dir = self._get_project_dir(state.project_id)
        
        # Check scene images
        for image in state.images:
            # Handle both absolute and relative paths
            if os.path.isabs(image.image_path):
                path = Path(image.image_path)
            else:
                path = project_dir / image.image_path
            
            if path.exists():
                valid.append(str(path))
            else:
                missing.append(str(path))
        
        # Check scene audios
        for audio in state.audios:
            if audio.status.value == "completed":
                if os.path.isabs(audio.audio_path):
                    path = Path(audio.audio_path)
                else:
                    path = project_dir / audio.audio_path
                
                if path.exists():
                    valid.append(str(path))
                else:
                    missing.append(str(path))
        
        # Check export package
        if state.export_package:
            # Check ZIP file
            if os.path.isabs(state.export_package.zip_path):
                zip_path = Path(state.export_package.zip_path)
            else:
                zip_path = project_dir / state.export_package.zip_path
            
            if zip_path.exists():
                valid.append(str(zip_path))
            else:
                missing.append(str(zip_path))
            
            # Check manifest file
            if os.path.isabs(state.export_package.manifest_path):
                manifest_path = Path(state.export_package.manifest_path)
            else:
                manifest_path = project_dir / state.export_package.manifest_path
            
            if manifest_path.exists():
                valid.append(str(manifest_path))
            else:
                missing.append(str(manifest_path))
            
            # Check subtitle files
            for subtitle_path in [state.export_package.subtitle_cn_path, state.export_package.subtitle_en_path]:
                if os.path.isabs(subtitle_path):
                    path = Path(subtitle_path)
                else:
                    path = project_dir / subtitle_path
                
                if path.exists():
                    valid.append(str(path))
                else:
                    missing.append(str(path))
            
            # Check scene assets
            for asset in state.export_package.assets:
                for asset_path in [asset.image_path, asset.audio_path]:
                    if os.path.isabs(asset_path):
                        path = Path(asset_path)
                    else:
                        path = project_dir / asset_path
                    
                    if path.exists():
                        valid.append(str(path))
                    else:
                        missing.append(str(path))
        
        # Legacy support: Check character images
        for char in state.characters:
            # Handle both absolute and relative paths
            if os.path.isabs(char.image_path):
                path = Path(char.image_path)
            else:
                path = project_dir / char.image_path
            
            if path.exists():
                valid.append(str(path))
            else:
                missing.append(str(path))
        
        # Legacy support: Check video clips
        for clip in state.clips:
            if clip.status.value == "completed":
                if os.path.isabs(clip.file_path):
                    path = Path(clip.file_path)
                else:
                    path = project_dir / clip.file_path
                
                if path.exists():
                    valid.append(str(path))
                else:
                    missing.append(str(path))
        
        # Legacy support: Check final video
        if state.final_video:
            if os.path.isabs(state.final_video.output_path):
                path = Path(state.final_video.output_path)
            else:
                path = project_dir / state.final_video.output_path
            
            if path.exists():
                valid.append(str(path))
            else:
                missing.append(str(path))
        
        return {"missing": missing, "valid": valid}
