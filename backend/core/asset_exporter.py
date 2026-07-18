"""Asset exporter module for packaging video generation assets.

This module provides the AssetExporter class for exporting all generated
assets (images, prompts, audio, subtitles) into a complete package with
manifest and ZIP archive.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from video_generator.models import (
    ExportPackage,
    ProjectState,
    Scene,
    SceneAsset,
    SceneAudio,
    SceneImage,
    SubtitleSegment,
)
from video_generator.subtitle_generator import SubtitleGenerator


class ExportError(Exception):
    """Export operation failed.
    
    Attributes:
        reason: The reason for the failure.
        partial_output: Path to any partial output created before failure.
    """
    
    def __init__(self, reason: str, partial_output: Optional[str] = None):
        self.reason = reason
        self.partial_output = partial_output
        message = f"Export failed: {reason}"
        if partial_output:
            message += f" (partial output at: {partial_output})"
        super().__init__(message)


class AssetExporter:
    """Exports all generated assets into a complete package.
    
    This class handles:
    - Exporting individual scene assets (image, prompt, audio, subtitles)
    - Generating manifest JSON with file relationships
    - Creating ZIP archive of all assets
    - Exporting complete Chinese and English subtitle files
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    """
    
    def __init__(self, subtitle_generator: Optional[SubtitleGenerator] = None):
        """Initialize the AssetExporter.
        
        Args:
            subtitle_generator: Optional SubtitleGenerator instance.
                If None, a new instance will be created.
        """
        self._subtitle_generator = subtitle_generator or SubtitleGenerator()
    
    def _ensure_directory(self, path: Path) -> None:
        """Ensure a directory exists.
        
        Args:
            path: Path to the directory.
        """
        path.mkdir(parents=True, exist_ok=True)
    
    def _write_video_prompt(
        self,
        scene: Scene,
        output_dir: Path
    ) -> str:
        """Write scene description to a TXT file (used as image prompt).
        
        Args:
            scene: The scene containing the description.
            output_dir: Directory to write the prompt file.
            
        Returns:
            Path to the created prompt file.
            
        Requirements: 8.2
        """
        prompts_dir = output_dir / "prompts"
        self._ensure_directory(prompts_dir)
        
        prompt_path = prompts_dir / f"{scene.scene_id}.txt"
        # Use description_cn as the image prompt
        prompt_path.write_text(scene.description_cn, encoding="utf-8")
        
        return str(prompt_path)
    
    async def export_scene_assets(
        self,
        scene: Scene,
        image: SceneImage,
        audio: SceneAudio,
        subtitle: SubtitleSegment,
        output_dir: str
    ) -> SceneAsset:
        """Export all assets for a single scene.
        
        Creates copies of the scene's image and audio files in the export
        directory, writes the video prompt to a TXT file, and includes
        subtitle information.
        
        Args:
            scene: The scene to export.
            image: The scene's generated image.
            audio: The scene's generated audio.
            subtitle: The scene's subtitle segment.
            output_dir: Base directory for export.
            
        Returns:
            SceneAsset with paths to all exported files.
            
        Raises:
            ExportError: If export fails.
            
        Requirements: 8.1, 8.2, 8.3
        """
        output_path = Path(output_dir)
        self._ensure_directory(output_path)
        
        try:
            # Write video prompt TXT file
            prompt_path = self._write_video_prompt(scene, output_path)
            
            # Create subtitle segments for both languages
            subtitle_cn = SubtitleSegment(
                scene_id=subtitle.scene_id,
                start_time=subtitle.start_time,
                end_time=subtitle.end_time,
                text_cn=subtitle.text_cn,
                text_en=subtitle.text_en,
            )
            
            subtitle_en = SubtitleSegment(
                scene_id=subtitle.scene_id,
                start_time=subtitle.start_time,
                end_time=subtitle.end_time,
                text_cn=subtitle.text_cn,
                text_en=subtitle.text_en,
            )
            
            return SceneAsset(
                scene_id=scene.scene_id,
                image_path=image.image_path,
                audio_path=audio.audio_path,
                subtitle_cn=subtitle_cn,
                subtitle_en=subtitle_en,
            )
        except Exception as e:
            raise ExportError(
                reason=f"Failed to export scene {scene.scene_id}: {str(e)}",
                partial_output=str(output_path)
            )
    
    def generate_manifest(
        self,
        assets: list[SceneAsset],
        scenes: list[Scene],
        audios: dict[str, SceneAudio],
        output_path: str,
        project_id: str,
        subtitle_cn_path: str,
        subtitle_en_path: str
    ) -> str:
        """Generate a manifest JSON file listing all assets.
        
        Args:
            assets: List of scene assets.
            scenes: List of scenes.
            audios: Dict of scene_id to SceneAudio.
            output_path: Path to write the manifest file.
            project_id: The project identifier.
            subtitle_cn_path: Path to complete Chinese subtitle file.
            subtitle_en_path: Path to complete English subtitle file.
            
        Returns:
            Path to the created manifest file.
        """
        scenes_dict = {s.scene_id: s for s in scenes}
        
        manifest = {
            "project_id": project_id,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "total_scenes": len(assets),
            "subtitle_files": {
                "chinese": "subtitles/full_cn.srt",
                "english": "subtitles/full_en.srt",
            },
            "audio_files": {
                "chinese": "audios/full_cn.wav",
                "english": "audios/full_en.wav",
            },
            "scenes": []
        }
        
        for asset in assets:
            scene = scenes_dict.get(asset.scene_id)
            audio = audios.get(asset.scene_id)
            
            scene_info = {
                "scene_id": asset.scene_id,
                "folder": asset.scene_id,
                "files": {
                    "image": f"{asset.scene_id}/image.png",
                    "prompt": f"{asset.scene_id}/prompt.txt",
                    "audio_cn": f"{asset.scene_id}/audio_cn.wav",
                    "audio_en": f"{asset.scene_id}/audio_en.wav",
                    "subtitle_cn": f"{asset.scene_id}/subtitle_cn.srt",
                    "subtitle_en": f"{asset.scene_id}/subtitle_en.srt",
                },
                "metadata": {
                    "start_time": asset.subtitle_cn.start_time,
                    "end_time": asset.subtitle_cn.end_time,
                    "duration": asset.subtitle_cn.end_time - asset.subtitle_cn.start_time,
                    "text_cn": asset.subtitle_cn.text_cn,
                    "text_en": asset.subtitle_cn.text_en,
                    "prompt": scene.description_cn if scene else "",
                }
            }
            manifest["scenes"].append(scene_info)
        
        output_file = Path(output_path)
        self._ensure_directory(output_file.parent)
        output_file.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return str(output_file)
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _create_scene_subtitle(self, subtitle: SubtitleSegment, language: str) -> str:
        """Create SRT content for a single scene subtitle.
        
        Args:
            subtitle: The subtitle segment.
            language: "cn" or "en".
            
        Returns:
            SRT formatted string.
        """
        text = subtitle.text_cn if language == "cn" else subtitle.text_en
        start = self._format_srt_time(subtitle.start_time)
        end = self._format_srt_time(subtitle.end_time)
        return f"1\n{start} --> {end}\n{text}\n"
    
    def _create_zip_archive(
        self,
        assets: list[SceneAsset],
        scenes: list[Scene],
        audios: dict[str, SceneAudio],
        subtitle_cn_path: str,
        subtitle_en_path: str,
        manifest_path: str,
        output_path: str,
        base_dir: Path,
        source_dir: Optional[Path] = None
    ) -> str:
        """Create a ZIP archive containing all assets organized by scene.
        
        Structure:
        assets.zip/
        ├── manifest.json                    # Summary JSON
        ├── subtitles/
        │   ├── full_cn.srt                 # Complete Chinese subtitles
        │   └── full_en.srt                 # Complete English subtitles
        ├── scene_001/
        │   ├── image.png                   # Scene image
        │   ├── prompt.txt                  # Scene prompt/description
        │   ├── subtitle_cn.srt             # Scene Chinese subtitle
        │   └── subtitle_en.srt             # Scene English subtitle
        ...
        
        Args:
            assets: List of scene assets.
            scenes: List of scenes (for prompt/description).
            audios: Dict of scene_id to SceneAudio.
            subtitle_cn_path: Path to Chinese subtitle file.
            subtitle_en_path: Path to English subtitle file.
            manifest_path: Path to manifest file.
            output_path: Path for the ZIP file.
            base_dir: Base directory for resolving relative paths.
            source_dir: Base directory for source files.
            
        Returns:
            Path to the created ZIP file.
        """
        output_file = Path(output_path)
        self._ensure_directory(output_file.parent)
        
        src_dir = source_dir if source_dir else base_dir
        scenes_dict = {s.scene_id: s for s in scenes}
        
        def resolve_path(file_path: str) -> Path:
            """Resolve file path - try as-is first, then relative to source_dir."""
            p = Path(file_path)
            if p.exists():
                return p
            if src_dir and not str(file_path).startswith("projects/"):
                resolved = src_dir / file_path
                if resolved.exists():
                    return resolved
            return p
        
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest at root
            manifest_file = Path(manifest_path)
            if manifest_file.exists():
                zf.write(manifest_file, "manifest.json")
            
            # Add complete subtitle files
            for subtitle_path, arcname in [
                (subtitle_cn_path, "subtitles/full_cn.srt"),
                (subtitle_en_path, "subtitles/full_en.srt"),
            ]:
                subtitle_file = Path(subtitle_path)
                if not subtitle_file.exists():
                    subtitle_file = base_dir / subtitle_path
                if subtitle_file.exists():
                    zf.write(subtitle_file, arcname)
            
            # Add combined audio files
            audios_dir = src_dir / "audios" if src_dir else base_dir / "audios"
            for audio_name, arcname in [
                ("full_cn.wav", "audios/full_cn.wav"),
                ("full_en.wav", "audios/full_en.wav"),
            ]:
                audio_file = audios_dir / audio_name
                if audio_file.exists():
                    zf.write(audio_file, arcname)
            
            # Add scene folders with assets
            for asset in assets:
                scene_id = asset.scene_id
                scene = scenes_dict.get(scene_id)
                audio = audios.get(scene_id)
                
                # Add image
                image_file = resolve_path(asset.image_path)
                if image_file.exists():
                    zf.write(image_file, f"{scene_id}/image.png")
                
                # Add prompt (scene description)
                if scene:
                    zf.writestr(f"{scene_id}/prompt.txt", scene.description_cn)
                
                # Add scene audio files (CN and EN)
                if audio:
                    # Chinese audio
                    cn_audio_file = resolve_path(audio.audio_path)
                    if cn_audio_file.exists():
                        zf.write(cn_audio_file, f"{scene_id}/audio_cn.wav")
                    
                    # English audio
                    if audio.audio_path_en:
                        en_audio_file = resolve_path(audio.audio_path_en)
                        if en_audio_file.exists():
                            zf.write(en_audio_file, f"{scene_id}/audio_en.wav")
                
                # Add scene subtitles
                if asset.subtitle_cn:
                    cn_srt = self._create_scene_subtitle(asset.subtitle_cn, "cn")
                    zf.writestr(f"{scene_id}/subtitle_cn.srt", cn_srt)
                    
                    en_srt = self._create_scene_subtitle(asset.subtitle_cn, "en")
                    zf.writestr(f"{scene_id}/subtitle_en.srt", en_srt)
        
        return str(output_file)
    
    async def export_all(
        self,
        project_state: ProjectState,
        output_dir: str,
        source_dir: Optional[str] = None
    ) -> ExportPackage:
        """Export all assets for a project and create a ZIP package.
        
        This method:
        1. Exports all scene assets (images, prompts, audio)
        2. Generates complete Chinese and English subtitle files
        3. Creates a manifest JSON
        4. Packages everything into a ZIP archive
        
        Args:
            project_state: The complete project state.
            output_dir: Base directory for export output.
            source_dir: Base directory where source files are located.
                If None, uses output_dir as source.
            
        Returns:
            ExportPackage with paths to all exported files.
            
        Raises:
            ExportError: If export fails.
            
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        """
        output_path = Path(output_dir)
        source_path = Path(source_dir) if source_dir else output_path
        self._ensure_directory(output_path)
        
        project_id = project_state.project_id
        
        try:
            # Validate we have required data
            if not project_state.storyboard:
                raise ExportError("No storyboard available for export")
            
            scenes = project_state.storyboard.scenes
            images = {img.scene_id: img for img in project_state.images}
            audios = {aud.scene_id: aud for aud in project_state.audios}
            subtitles = {sub.scene_id: sub for sub in project_state.subtitles}
            
            # Export scene assets
            assets = []
            for scene in scenes:
                image = images.get(scene.scene_id)
                audio = audios.get(scene.scene_id)
                subtitle = subtitles.get(scene.scene_id)
                
                if not image:
                    raise ExportError(f"Missing image for scene {scene.scene_id}")
                if not audio:
                    raise ExportError(f"Missing audio for scene {scene.scene_id}")
                if not subtitle:
                    raise ExportError(f"Missing subtitle for scene {scene.scene_id}")
                
                asset = await self.export_scene_assets(
                    scene=scene,
                    image=image,
                    audio=audio,
                    subtitle=subtitle,
                    output_dir=output_dir
                )
                assets.append(asset)
            
            # Generate complete subtitle files
            subtitles_dir = output_path / "subtitles"
            self._ensure_directory(subtitles_dir)
            
            cn_file, en_file = self._subtitle_generator.export_combined_srt(
                segments=project_state.subtitles,
                output_dir=str(subtitles_dir)
            )
            
            # Generate manifest
            export_dir = output_path / "export"
            self._ensure_directory(export_dir)
            
            manifest_path = str(export_dir / "manifest.json")
            self.generate_manifest(
                assets=assets,
                scenes=scenes,
                audios=audios,
                output_path=manifest_path,
                project_id=project_id,
                subtitle_cn_path=cn_file.file_path,
                subtitle_en_path=en_file.file_path
            )
            
            # Create ZIP archive - use source_path for finding original files
            zip_path = str(export_dir / "assets.zip")
            self._create_zip_archive(
                assets=assets,
                scenes=scenes,
                audios=audios,
                subtitle_cn_path=cn_file.file_path,
                subtitle_en_path=en_file.file_path,
                manifest_path=manifest_path,
                output_path=zip_path,
                base_dir=output_path,
                source_dir=source_path
            )
            
            return ExportPackage(
                project_id=project_id,
                zip_path=zip_path,
                manifest_path=manifest_path,
                assets=assets,
                subtitle_cn_path=cn_file.file_path,
                subtitle_en_path=en_file.file_path
            )
            
        except ExportError:
            raise
        except Exception as e:
            raise ExportError(
                reason=str(e),
                partial_output=str(output_path)
            )
