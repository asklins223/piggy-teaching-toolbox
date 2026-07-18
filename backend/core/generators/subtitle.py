"""Subtitle generator module for creating bilingual subtitles.

This module generates Chinese and English subtitle files (SRT format)
for teaching video scenes, with precise timecode alignment.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from typing import Optional, Callable
from pathlib import Path

from backend.schemas.models import (
    Scene,
    SubtitleSegment,
    SubtitleFile,
)


class SubtitleGenerator:
    """Generates bilingual subtitle files for teaching videos.
    
    This class creates Chinese and English subtitle segments for each scene,
    with precise timecode alignment based on scene durations.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    
    def __init__(self):
        """Initialize the subtitle generator."""
        pass
    
    async def generate_segment(
        self,
        scene: Scene,
        start_time: float
    ) -> SubtitleSegment:
        """Generate a subtitle segment for a single scene.
        
        Creates a subtitle segment with Chinese and English text,
        with timecodes based on the scene's start time and duration.
        
        Args:
            scene: The scene to generate subtitles for.
            start_time: Start time in seconds for this segment.
            
        Returns:
            SubtitleSegment with bilingual text and timecodes.
            
        Requirements: 4.1, 4.2, 4.3, 4.6
        """
        end_time = start_time + scene.duration.value
        
        return SubtitleSegment(
            scene_id=scene.scene_id,
            start_time=start_time,
            end_time=end_time,
            text_cn=scene.narration_cn,
            text_en=scene.narration_en,
        )
    
    async def generate_all_segments(
        self,
        scenes: list[Scene],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> list[SubtitleSegment]:
        """Generate subtitle segments for all scenes.
        
        Creates subtitle segments for each scene in sequence,
        with cumulative timecodes.
        
        Args:
            scenes: List of scenes to generate subtitles for.
            on_progress: Optional callback for progress updates (current, total).
            
        Returns:
            List of SubtitleSegments in order.
            
        Requirements: 4.1, 4.2, 4.3, 4.6
        """
        segments = []
        current_time = 0.0
        
        for idx, scene in enumerate(scenes):
            segment = await self.generate_segment(scene, current_time)
            segments.append(segment)
            current_time += scene.duration.value
            
            if on_progress:
                on_progress(idx + 1, len(scenes))
        
        return segments
    
    def _format_timecode(self, seconds: float) -> str:
        """Format seconds as SRT timecode (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds.
            
        Returns:
            Formatted timecode string.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_srt_entry(
        self,
        index: int,
        start_time: float,
        end_time: float,
        text: str
    ) -> str:
        """Format a single SRT entry.
        
        Args:
            index: Subtitle index (1-based).
            start_time: Start time in seconds.
            end_time: End time in seconds.
            text: Subtitle text.
            
        Returns:
            Formatted SRT entry string.
        """
        start_tc = self._format_timecode(start_time)
        end_tc = self._format_timecode(end_time)
        
        return f"{index}\n{start_tc} --> {end_tc}\n{text}\n"
    
    def export_srt(
        self,
        segments: list[SubtitleSegment],
        language: str,
        output_path: str
    ) -> SubtitleFile:
        """Export subtitle segments to an SRT file.
        
        Args:
            segments: List of subtitle segments.
            language: Language code ("cn" or "en").
            output_path: Path to write the SRT file.
            
        Returns:
            SubtitleFile with file metadata.
            
        Raises:
            ValueError: If language is not "cn" or "en".
            
        Requirements: 4.4, 4.5
        """
        if language not in ("cn", "en"):
            raise ValueError(f"Language must be 'cn' or 'en', got '{language}'")
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build SRT content
        srt_entries = []
        for idx, segment in enumerate(segments, start=1):
            text = segment.text_cn if language == "cn" else segment.text_en
            entry = self._format_srt_entry(
                index=idx,
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=text
            )
            srt_entries.append(entry)
        
        # Write to file
        srt_content = "\n".join(srt_entries)
        output_file.write_text(srt_content, encoding="utf-8")
        
        return SubtitleFile(
            file_path=str(output_path),
            language=language,
            format="srt"
        )
    
    def export_combined_srt(
        self,
        segments: list[SubtitleSegment],
        output_dir: str
    ) -> tuple[SubtitleFile, SubtitleFile]:
        """Export complete Chinese and English subtitle files.
        
        Creates two SRT files: one for Chinese and one for English,
        containing all subtitle segments.
        
        Args:
            segments: List of subtitle segments.
            output_dir: Directory to write the SRT files.
            
        Returns:
            Tuple of (Chinese SubtitleFile, English SubtitleFile).
            
        Requirements: 4.4, 4.5
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Export Chinese subtitles
        cn_path = output_path / "full_cn.srt"
        cn_file = self.export_srt(segments, "cn", str(cn_path))
        
        # Export English subtitles
        en_path = output_path / "full_en.srt"
        en_file = self.export_srt(segments, "en", str(en_path))
        
        return (cn_file, en_file)
    
    def export_scene_srt(
        self,
        segment: SubtitleSegment,
        output_dir: str
    ) -> tuple[SubtitleFile, SubtitleFile]:
        """Export individual scene subtitle files.
        
        Creates two SRT files for a single scene: one Chinese, one English.
        The timecodes are relative to the scene (starting at 0).
        
        Args:
            segment: The subtitle segment to export.
            output_dir: Directory to write the SRT files.
            
        Returns:
            Tuple of (Chinese SubtitleFile, English SubtitleFile).
            
        Requirements: 4.3
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create a segment with relative timecodes (starting at 0)
        relative_segment = SubtitleSegment(
            scene_id=segment.scene_id,
            start_time=0.0,
            end_time=segment.end_time - segment.start_time,
            text_cn=segment.text_cn,
            text_en=segment.text_en,
        )
        
        # Export Chinese subtitle
        cn_path = output_path / f"{segment.scene_id}_cn.srt"
        cn_file = self.export_srt([relative_segment], "cn", str(cn_path))
        
        # Export English subtitle
        en_path = output_path / f"{segment.scene_id}_en.srt"
        en_file = self.export_srt([relative_segment], "en", str(en_path))
        
        return (cn_file, en_file)
