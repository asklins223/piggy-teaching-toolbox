"""Video generation orchestrator module.

This module provides the Orchestrator class that coordinates
the entire video asset generation workflow, from storyboard generation through
final asset export.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from video_generator.config import get_settings
from video_generator.models import (
    AudioConfig,
    CharacterConfig,
    CharacterReference,
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
from video_generator.script_planner import ScriptPlanner
from video_generator.scene_generator import SceneGenerator, ImageGenerationError
from video_generator.audio_generator import AudioGenerator, AudioGenerationError
from video_generator.subtitle_generator import SubtitleGenerator
from video_generator.asset_exporter import AssetExporter, ExportError
from video_generator.storage import StorageManager, ProjectNotFoundError
from video_generator.character_generator import CharacterGenerator, CharacterGenerationError


class OrchestratorError(Exception):
    """Base exception for orchestrator-related errors.
    
    Requirements: 6.4
    """
    def __init__(self, project_id: str, stage: str, reason: str, recoverable: bool = True):
        self.project_id = project_id
        self.stage = stage
        self.reason = reason
        self.recoverable = recoverable
        super().__init__(f"Orchestrator error in project '{project_id}' at stage '{stage}': {reason}")


# Type alias for progress callback
ProgressCallback = Callable[[str, str, int, int], None]
"""Progress callback signature: (stage, message, current, total)"""


class Orchestrator:
    """Orchestrates the complete video asset generation workflow.
    
    This class coordinates all components of the video asset generation pipeline:
    1. Storyboard generation - Creates teaching storyboard from goals
    2. Image generation - Creates scene images using qwen3-vl-plus
    3. Audio generation - Creates narration audio using IndexTTS2
    4. Subtitle generation - Creates bilingual subtitles
    5. Asset export - Packages all assets for external use
    
    The orchestrator supports:
    - Creating new projects with automatic ID generation
    - Running individual stages or the complete workflow
    - Resuming from any checkpoint after interruption
    - Saving state after each stage for recovery
    - Progress callbacks for UI integration
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    
    Example:
        >>> orchestrator = Orchestrator(
        ...     script_planner=planner,
        ...     scene_generator=scene_gen,
        ...     audio_generator=audio_gen,
        ...     subtitle_generator=subtitle_gen,
        ...     asset_exporter=exporter,
        ...     storage_manager=storage
        ... )
        >>> project_id = await orchestrator.create_project(goal)
        >>> storyboard = await orchestrator.generate_storyboard(project_id)
        >>> images = await orchestrator.generate_images(project_id)
        >>> audios = await orchestrator.generate_audios(project_id, audio_config)
        >>> subtitles = await orchestrator.generate_subtitles(project_id)
        >>> package = await orchestrator.export_assets(project_id, output_dir)
    """
    
    def __init__(
        self,
        script_planner: ScriptPlanner,
        scene_generator: SceneGenerator,
        audio_generator: AudioGenerator,
        subtitle_generator: SubtitleGenerator,
        asset_exporter: AssetExporter,
        storage_manager: StorageManager,
    ):
        """Initialize the orchestrator with all required components.
        
        Args:
            script_planner: Component for generating storyboards.
            scene_generator: Component for generating scene images.
            audio_generator: Component for generating audio narration.
            subtitle_generator: Component for generating subtitles.
            asset_exporter: Component for exporting assets.
            storage_manager: Component for project persistence.
        """
        self._script_planner = script_planner
        self._scene_generator = scene_generator
        self._audio_generator = audio_generator
        self._subtitle_generator = subtitle_generator
        self._asset_exporter = asset_exporter
        self._storage_manager = storage_manager

    def _generate_project_id(self) -> str:
        """Generate a unique project ID.
        
        Returns:
            Unique project identifier in format 'proj_XXXXXXXX'.
        """
        return f"proj_{uuid.uuid4().hex[:8]}"
    
    def _notify_progress(
        self,
        callback: Optional[ProgressCallback],
        stage: str,
        message: str,
        current: int,
        total: int
    ) -> None:
        """Send progress notification if callback is provided.
        
        Args:
            callback: Optional progress callback function.
            stage: Current workflow stage.
            message: Progress message.
            current: Current step number.
            total: Total steps in current stage.
        """
        if callback:
            callback(stage, message, current, total)
    
    async def create_project(
        self,
        goal: TeachingGoal,
    ) -> str:
        """Create a new video generation project.
        
        Initializes a new project with the given teaching goal.
        The project is saved to storage in INITIALIZED state.
        
        Args:
            goal: Teaching goal configuration.
            
        Returns:
            The generated project ID.
            
        Requirements: 6.1
        """
        project_id = self._generate_project_id()
        
        # Create initial project state
        state = ProjectState(
            project_id=project_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            status=ProjectStatus.INITIALIZED,
            goal=goal,
            storyboard=None,
            images=[],
            audios=[],
            subtitles=[],
            export_package=None,
        )
        
        # Save initial state
        self._storage_manager.save_project(state)
        
        return project_id
    
    async def generate_storyboard(
        self,
        project_id: str,
        default_duration: SceneDuration = SceneDuration.SHORT,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Storyboard:
        """Generate storyboard from teaching goal.
        
        If characters have been generated, they will be included in the storyboard
        and each scene will reference them.
        
        Args:
            project_id: The project ID.
            default_duration: Default scene duration (5 or 10 seconds).
            on_progress: Optional progress callback.
            
        Returns:
            Generated storyboard.
            
        Raises:
            OrchestratorError: If storyboard generation fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.3
        """
        state = self._storage_manager.load_project(project_id)
        
        try:
            self._notify_progress(
                on_progress,
                "storyboard",
                "Generating storyboard from teaching goal",
                0,
                1
            )
            
            # Pass characters to script planner if available
            characters = state.characters if state.characters else None
            
            storyboard = await self._script_planner.generate_storyboard(
                goal=state.goal,
                characters=characters,
                default_duration=default_duration,
                project_id=project_id
            )
            
            # Update state
            state.storyboard = storyboard
            state.status = ProjectStatus.STORYBOARD_READY
            self._storage_manager.save_project(state)
            
            self._notify_progress(
                on_progress,
                "storyboard",
                f"Storyboard generated with {len(storyboard.scenes)} scenes",
                1,
                1
            )
            
            return storyboard
            
        except Exception as e:
            raise OrchestratorError(
                project_id=project_id,
                stage="storyboard",
                reason=f"Storyboard generation failed: {str(e)}",
                recoverable=True
            )
    
    async def generate_characters(
        self,
        project_id: str,
        character_configs: list[CharacterConfig],
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[CharacterReference]:
        """Generate character reference images.
        
        Args:
            project_id: The project ID.
            character_configs: List of character configurations.
            on_progress: Optional progress callback.
            
        Returns:
            List of generated character references.
            
        Raises:
            OrchestratorError: If character generation fails.
            ProjectNotFoundError: If project doesn't exist.
        """
        state = self._storage_manager.load_project(project_id)
        
        if not character_configs:
            return []
        
        total = len(character_configs)
        
        self._notify_progress(
            on_progress,
            "characters",
            f"Starting character generation ({total} characters)",
            0,
            total
        )
        
        # Get output directory for characters
        output_dir = Path(self._storage_manager.get_resource_path(
            project_id, "characters", ""
        ))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create character generator
        char_generator = CharacterGenerator(output_dir=str(output_dir))
        
        try:
            def char_progress(msg: str, current: int, total_count: int):
                self._notify_progress(
                    on_progress,
                    "characters",
                    msg,
                    current,
                    total_count
                )
            
            characters = await char_generator.generate_characters(
                configs=character_configs,
                on_progress=char_progress
            )
            
            # Update state
            state.characters = characters
            self._storage_manager.save_project(state)
            
            self._notify_progress(
                on_progress,
                "characters",
                f"All {total} characters generated successfully",
                total,
                total
            )
            
            return characters
            
        except CharacterGenerationError as e:
            raise OrchestratorError(
                project_id=project_id,
                stage="characters",
                reason=f"Character generation failed: {e.reason}",
                recoverable=e.retryable
            )
        finally:
            await char_generator.close()
    
    async def generate_images(
        self,
        project_id: str,
        style_reference: Optional[str] = None,
        use_character_refs: bool = True,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[SceneImage]:
        """Generate images for all scenes.
        
        Args:
            project_id: The project ID.
            style_reference: Optional style reference image path.
            use_character_refs: Whether to use character references for consistency.
            on_progress: Optional progress callback.
            
        Returns:
            List of generated scene images.
            
        Raises:
            OrchestratorError: If image generation fails completely.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.3
        """
        state = self._storage_manager.load_project(project_id)
        
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="images",
                reason="No storyboard available for image generation",
                recoverable=False
            )
        
        scenes = state.storyboard.scenes
        total = len(scenes)
        
        # Update status
        state.status = ProjectStatus.IMAGES_GENERATING
        self._storage_manager.save_project(state)
        
        # Get output directory
        output_dir = Path(self._storage_manager.get_resource_path(
            project_id, "images", ""
        ))
        
        # Build character reference dict if available
        character_refs = None
        if use_character_refs and state.characters:
            character_refs = {
                char.character_id: char
                for char in state.characters
            }
            self._notify_progress(
                on_progress,
                "images",
                f"Using {len(character_refs)} character references for consistency",
                0,
                total
            )
        
        self._notify_progress(
            on_progress,
            "images",
            f"Starting image generation ({total} scenes)",
            0,
            total
        )
        
        # Track progress
        progress_count = [0]  # Use list to allow modification in closure
        
        def image_progress(current: int, total_count: int):
            progress_count[0] = current
            self._notify_progress(
                on_progress,
                "images",
                f"Generated image {current}/{total_count}",
                current,
                total_count
            )
        
        # Generate images with character references
        images = await self._scene_generator.generate_images(
            scenes=scenes,
            output_dir=output_dir,
            character_refs=character_refs,
            style_reference=style_reference,
            on_progress=image_progress
        )
        
        # Update state
        state.images = images
        state.status = ProjectStatus.IMAGES_READY
        self._storage_manager.save_project(state)
        
        # Check for failures
        failed_images = [img for img in images if img.status == ResourceStatus.FAILED]
        if failed_images:
            self._notify_progress(
                on_progress,
                "images",
                f"Warning: {len(failed_images)} images failed to generate",
                total - len(failed_images),
                total
            )
        else:
            self._notify_progress(
                on_progress,
                "images",
                f"All {total} images generated successfully",
                total,
                total
            )
        
        return images
    
    async def regenerate_scene_image(
        self,
        project_id: str,
        scene_id: str,
        style_reference: Optional[str] = None,
        use_character_refs: bool = True,
        on_progress: Optional[ProgressCallback] = None,
    ) -> SceneImage:
        """Regenerate image for a single scene.
        
        Args:
            project_id: The project ID.
            scene_id: The scene ID to regenerate.
            style_reference: Optional style reference image path.
            use_character_refs: Whether to use character references.
            on_progress: Optional progress callback.
            
        Returns:
            Regenerated scene image.
            
        Raises:
            OrchestratorError: If regeneration fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.4
        """
        state = self._storage_manager.load_project(project_id)
        
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="images",
                reason="No storyboard available",
                recoverable=False
            )
        
        # Find the scene
        scene = None
        for s in state.storyboard.scenes:
            if s.scene_id == scene_id:
                scene = s
                break
        
        if not scene:
            raise OrchestratorError(
                project_id=project_id,
                stage="images",
                reason=f"Scene {scene_id} not found",
                recoverable=False
            )
        
        self._notify_progress(
            on_progress,
            "images",
            f"Regenerating image for scene {scene_id}",
            0,
            1
        )
        
        # Get output directory
        output_dir = Path(self._storage_manager.get_resource_path(
            project_id, "images", ""
        ))
        
        # Build character reference dict if available
        character_refs = None
        if use_character_refs and state.characters:
            character_refs = {
                char.character_id: char
                for char in state.characters
            }
        
        try:
            # Regenerate image
            new_image = await self._scene_generator.regenerate_image(
                scene=scene,
                output_dir=output_dir,
                character_refs=character_refs,
                style_reference=style_reference
            )
            
            # Update state - replace existing image for this scene
            updated_images = []
            replaced = False
            for img in state.images:
                if img.scene_id == scene_id:
                    updated_images.append(new_image)
                    replaced = True
                else:
                    updated_images.append(img)
            
            if not replaced:
                updated_images.append(new_image)
            
            state.images = updated_images
            self._storage_manager.save_project(state)
            
            self._notify_progress(
                on_progress,
                "images",
                f"Successfully regenerated image for scene {scene_id}",
                1,
                1
            )
            
            return new_image
            
        except ImageGenerationError as e:
            raise OrchestratorError(
                project_id=project_id,
                stage="images",
                reason=f"Image regeneration failed: {e.reason}",
                recoverable=e.retryable
            )
    
    async def update_scene(
        self,
        project_id: str,
        scene_id: str,
        updates: dict,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Scene:
        """Update a scene's content.
        
        Args:
            project_id: The project ID.
            scene_id: The scene ID to update.
            updates: Dictionary of field updates (e.g., description_cn, narration_cn).
            on_progress: Optional progress callback.
            
        Returns:
            Updated scene.
            
        Raises:
            OrchestratorError: If update fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1
        """
        state = self._storage_manager.load_project(project_id)
        
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="update",
                reason="No storyboard available",
                recoverable=False
            )
        
        self._notify_progress(
            on_progress,
            "update",
            f"Updating scene {scene_id}",
            0,
            1
        )
        
        # Find and update the scene
        updated_scene = None
        for i, scene in enumerate(state.storyboard.scenes):
            if scene.scene_id == scene_id:
                # Create updated scene with new values
                scene_dict = scene.model_dump()
                scene_dict.update(updates)
                updated_scene = Scene(**scene_dict)
                state.storyboard.scenes[i] = updated_scene
                break
        
        if not updated_scene:
            raise OrchestratorError(
                project_id=project_id,
                stage="update",
                reason=f"Scene {scene_id} not found",
                recoverable=False
            )
        
        # Save updated state
        self._storage_manager.save_project(state)
        
        self._notify_progress(
            on_progress,
            "update",
            f"Successfully updated scene {scene_id}",
            1,
            1
        )
        
        return updated_scene
    
    async def generate_audios(
        self,
        project_id: str,
        audio_config: Optional[AudioConfig] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[SceneAudio]:
        """Generate audio for all scenes.
        
        Args:
            project_id: The project ID.
            audio_config: Optional audio configuration.
            on_progress: Optional progress callback.
            
        Returns:
            List of generated scene audios.
            
        Raises:
            OrchestratorError: If audio generation fails completely.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.3
        """
        state = self._storage_manager.load_project(project_id)
        
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="audios",
                reason="No storyboard available for audio generation",
                recoverable=False
            )
        
        scenes = state.storyboard.scenes
        total = len(scenes)
        
        # Update status
        state.status = ProjectStatus.AUDIO_GENERATING
        self._storage_manager.save_project(state)
        
        # Get output directory
        output_dir = Path(self._storage_manager.get_resource_path(
            project_id, "audios", ""
        ))
        
        self._notify_progress(
            on_progress,
            "audios",
            f"Starting audio generation ({total} scenes)",
            0,
            total
        )
        
        # Track progress
        def audio_progress(current: int, total_count: int):
            self._notify_progress(
                on_progress,
                "audios",
                f"Generated audio {current}/{total_count}",
                current,
                total_count
            )
        
        # Generate audios
        audios = await self._audio_generator.generate_audios(
            scenes=scenes,
            output_dir=output_dir,
            config=audio_config,
            on_progress=audio_progress
        )
        
        # Merge all audios into combined files
        self._notify_progress(
            on_progress,
            "audios",
            "正在合并音频文件...",
            total,
            total
        )
        
        # Collect successful audio paths (sorted by scene order)
        cn_audio_paths = []
        en_audio_paths = []
        for scene in scenes:
            audio = next((a for a in audios if a.scene_id == scene.scene_id), None)
            if audio and audio.status == ResourceStatus.COMPLETED:
                cn_audio_paths.append(Path(audio.audio_path))
                if audio.audio_path_en:
                    en_audio_paths.append(Path(audio.audio_path_en))
        
        # Merge Chinese audios
        if cn_audio_paths:
            full_cn_path = output_dir / "full_cn.wav"
            try:
                await self._audio_generator.merge_audios(cn_audio_paths, full_cn_path, silence_gap=0.3)
            except Exception as e:
                logger.warning(f"Failed to merge Chinese audios: {e}")
        
        # Merge English audios
        if en_audio_paths:
            full_en_path = output_dir / "full_en.wav"
            try:
                await self._audio_generator.merge_audios(en_audio_paths, full_en_path, silence_gap=0.3)
            except Exception as e:
                logger.warning(f"Failed to merge English audios: {e}")
        
        # Update state
        state.audios = audios
        state.status = ProjectStatus.AUDIO_READY
        self._storage_manager.save_project(state)
        
        # Check for failures
        failed_audios = [aud for aud in audios if aud.status == ResourceStatus.FAILED]
        if failed_audios:
            self._notify_progress(
                on_progress,
                "audios",
                f"Warning: {len(failed_audios)} audios failed to generate",
                total - len(failed_audios),
                total
            )
        else:
            self._notify_progress(
                on_progress,
                "audios",
                f"All {total} audios generated successfully",
                total,
                total
            )
        
        return audios
    
    async def generate_subtitles(
        self,
        project_id: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[SubtitleSegment]:
        """Generate subtitles for all scenes.
        
        Args:
            project_id: The project ID.
            on_progress: Optional progress callback.
            
        Returns:
            List of subtitle segments.
            
        Raises:
            OrchestratorError: If subtitle generation fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.3
        """
        state = self._storage_manager.load_project(project_id)
        
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="subtitles",
                reason="No storyboard available for subtitle generation",
                recoverable=False
            )
        
        scenes = state.storyboard.scenes
        total = len(scenes)
        
        self._notify_progress(
            on_progress,
            "subtitles",
            f"Starting subtitle generation ({total} scenes)",
            0,
            total
        )
        
        # Track progress
        def subtitle_progress(current: int, total_count: int):
            self._notify_progress(
                on_progress,
                "subtitles",
                f"Generated subtitle {current}/{total_count}",
                current,
                total_count
            )
        
        # Generate subtitles
        subtitles = await self._subtitle_generator.generate_all_segments(
            scenes=scenes,
            on_progress=subtitle_progress
        )
        
        # Export subtitle files
        subtitles_dir = self._storage_manager.get_resource_path(
            project_id, "subtitles", ""
        )
        
        self._subtitle_generator.export_combined_srt(
            segments=subtitles,
            output_dir=subtitles_dir
        )
        
        # Update state
        state.subtitles = subtitles
        state.status = ProjectStatus.SUBTITLES_READY
        self._storage_manager.save_project(state)
        
        self._notify_progress(
            on_progress,
            "subtitles",
            f"All {total} subtitles generated successfully",
            total,
            total
        )
        
        return subtitles
    
    async def export_assets(
        self,
        project_id: str,
        output_dir: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ExportPackage:
        """Export all assets for a project.
        
        Args:
            project_id: The project ID.
            output_dir: Optional output directory. If None, uses project export dir.
            on_progress: Optional progress callback.
            
        Returns:
            Export package with paths to all exported files.
            
        Raises:
            OrchestratorError: If export fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.1, 6.5
        """
        state = self._storage_manager.load_project(project_id)
        
        # Validate state
        if not state.storyboard:
            raise OrchestratorError(
                project_id=project_id,
                stage="export",
                reason="No storyboard available for export",
                recoverable=False
            )
        
        if not state.images:
            raise OrchestratorError(
                project_id=project_id,
                stage="export",
                reason="No images available for export",
                recoverable=False
            )
        
        if not state.audios:
            raise OrchestratorError(
                project_id=project_id,
                stage="export",
                reason="No audios available for export",
                recoverable=False
            )
        
        if not state.subtitles:
            raise OrchestratorError(
                project_id=project_id,
                stage="export",
                reason="No subtitles available for export",
                recoverable=False
            )
        
        self._notify_progress(
            on_progress,
            "export",
            "Starting asset export",
            0,
            1
        )
        
        # Determine output directory
        if output_dir is None:
            output_dir = self._storage_manager.get_resource_path(
                project_id, "export", ""
            )
        
        # Get source directory (where images/audios are stored)
        source_dir = str(self._storage_manager._get_project_dir(project_id))
        
        try:
            # Export all assets
            export_package = await self._asset_exporter.export_all(
                project_state=state,
                output_dir=output_dir,
                source_dir=source_dir
            )
            
            # Update state
            state.export_package = export_package
            state.status = ProjectStatus.COMPLETED
            self._storage_manager.save_project(state)
            
            self._notify_progress(
                on_progress,
                "export",
                f"Export complete: {export_package.zip_path}",
                1,
                1
            )
            
            return export_package
            
        except ExportError as e:
            raise OrchestratorError(
                project_id=project_id,
                stage="export",
                reason=f"Export failed: {e.reason}",
                recoverable=True
            )
    
    async def resume(
        self,
        project_id: str,
        audio_config: Optional[AudioConfig] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ProjectState:
        """Resume a previously interrupted project.
        
        Loads the project state and continues from the last saved checkpoint.
        This enables recovery from failures at any stage.
        
        Args:
            project_id: The project ID to resume.
            audio_config: Optional audio config for audio generation stage.
            on_progress: Optional callback for progress updates.
            
        Returns:
            Final project state after resumption.
            
        Raises:
            OrchestratorError: If resumption fails.
            ProjectNotFoundError: If project doesn't exist.
            
        Requirements: 6.2, 6.4
        """
        state = self._storage_manager.load_project(project_id)
        
        self._notify_progress(
            on_progress,
            "resume",
            f"Resuming project from stage: {state.status.value}",
            0,
            1
        )
        
        # If already completed, return the state
        if state.status == ProjectStatus.COMPLETED:
            self._notify_progress(
                on_progress,
                "resume",
                "Project already completed",
                1,
                1
            )
            return state
        
        # Resume from current stage
        if state.status == ProjectStatus.INITIALIZED:
            await self.generate_storyboard(project_id, on_progress=on_progress)
            state = self._storage_manager.load_project(project_id)
        
        if state.status == ProjectStatus.STORYBOARD_READY:
            await self.generate_images(project_id, on_progress=on_progress)
            state = self._storage_manager.load_project(project_id)
        
        if state.status in (ProjectStatus.IMAGES_GENERATING, ProjectStatus.IMAGES_READY):
            # Check if images are complete
            if state.status == ProjectStatus.IMAGES_GENERATING or not state.images:
                await self.generate_images(project_id, on_progress=on_progress)
                state = self._storage_manager.load_project(project_id)
            
            # Move to audio generation
            await self.generate_audios(project_id, audio_config, on_progress=on_progress)
            state = self._storage_manager.load_project(project_id)
        
        if state.status in (ProjectStatus.AUDIO_GENERATING, ProjectStatus.AUDIO_READY):
            # Check if audios are complete
            if state.status == ProjectStatus.AUDIO_GENERATING or not state.audios:
                await self.generate_audios(project_id, audio_config, on_progress=on_progress)
                state = self._storage_manager.load_project(project_id)
            
            # Move to subtitle generation
            await self.generate_subtitles(project_id, on_progress=on_progress)
            state = self._storage_manager.load_project(project_id)
        
        if state.status == ProjectStatus.SUBTITLES_READY:
            await self.export_assets(project_id, on_progress=on_progress)
            state = self._storage_manager.load_project(project_id)
        
        return state
    
    def get_project_status(self, project_id: str) -> ProjectStatus:
        """Get the current status of a project.
        
        Args:
            project_id: The project ID to check.
            
        Returns:
            Current project status.
            
        Raises:
            ProjectNotFoundError: If project doesn't exist.
        """
        state = self._storage_manager.load_project(project_id)
        return state.status
    
    def get_project_state(self, project_id: str) -> ProjectState:
        """Get the complete state of a project.
        
        Args:
            project_id: The project ID to retrieve.
            
        Returns:
            Complete project state.
            
        Raises:
            ProjectNotFoundError: If project doesn't exist.
        """
        return self._storage_manager.load_project(project_id)
