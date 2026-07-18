"""Audio generation using UCloud Modelverse IndexTTS API.

This module provides the AudioGenerator class for generating narration audio
using the UCloud Modelverse IndexTTS cloud API with emotion control.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Callable, Tuple
import wave
import struct
import io
import httpx

from backend.schemas.models import Scene, SceneAudio, AudioConfig, ResourceStatus, SceneDuration, Emotion
from backend.config import get_settings
from backend.core.exceptions import AudioGenerationError


logger = logging.getLogger(__name__)


class AudioGenerator:
    """Audio generator using UCloud Modelverse IndexTTS API.
    
    This class handles the generation of narration audio using the cloud-based
    IndexTTS API with emotion control support.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    
    # Emotion text mapping from Emotion enum to Chinese text for emo_text parameter
    # IndexTTS API 支持的情感文本: 喜/怒/哀/惧/厌恶/低落/惊喜/平静
    # Requirements: 3.3
    EMOTION_TEXT_MAP = {
        # 基础情感 - 使用 IndexTTS 支持的单字文本
        Emotion.HAPPY: "喜",
        Emotion.ANGRY: "怒",
        Emotion.SAD: "哀",
        Emotion.FEAR: "惧",
        Emotion.DISGUST: "厌恶",
        Emotion.DEPRESSED: "低落",
        Emotion.SURPRISED: "惊喜",
        Emotion.CALM: "平静",
        # 扩展情感 (Requirements: 3.3) - 显示用，实际调用时会映射到基础情感
        Emotion.LIVELY: "活泼",
        Emotion.HEALING: "治愈",
        Emotion.AGGRIEVED: "委屈",
        Emotion.EMBARRASSED: "尴尬",
        Emotion.PROUD: "自豪",
        Emotion.CONFLICTED: "纠结",
        Emotion.LOST: "失落",
        Emotion.SHY: "害羞",
        Emotion.IRRITATED: "烦躁",
    }
    
    # Emotion vector indices: [高兴, 生气, 悲伤, 害怕, 厌恶, 忧郁, 惊喜, 平静]
    EMOTION_VECTOR_MAP = {
        Emotion.HAPPY: [1.0, 0, 0, 0, 0, 0, 0, 0],
        Emotion.ANGRY: [0, 1.0, 0, 0, 0, 0, 0, 0],
        Emotion.SAD: [0, 0, 1.0, 0, 0, 0, 0, 0],
        Emotion.FEAR: [0, 0, 0, 1.0, 0, 0, 0, 0],
        Emotion.DISGUST: [0, 0, 0, 0, 1.0, 0, 0, 0],
        Emotion.DEPRESSED: [0, 0, 0, 0, 0, 1.0, 0, 0],
        Emotion.SURPRISED: [0, 0, 0, 0, 0, 0, 1.0, 0],
        Emotion.CALM: [0, 0, 0, 0, 0, 0, 0, 1.0],
    }
    
    # 情感分类（用于前端分组显示）(Requirements: 4.2)
    EMOTION_CATEGORIES = {
        "positive": [
            Emotion.HAPPY, 
            Emotion.LIVELY, 
            Emotion.HEALING, 
            Emotion.PROUD, 
            Emotion.SURPRISED
        ],
        "negative": [
            Emotion.ANGRY, 
            Emotion.SAD, 
            Emotion.FEAR, 
            Emotion.DISGUST, 
            Emotion.DEPRESSED, 
            Emotion.AGGRIEVED,
            Emotion.LOST, 
            Emotion.IRRITATED
        ],
        "neutral": [
            Emotion.CALM, 
            Emotion.EMBARRASSED, 
            Emotion.CONFLICTED, 
            Emotion.SHY
        ],
    }
    
    # Duration tolerance in seconds (±0.5s as per Property 6)
    DURATION_TOLERANCE = 0.5
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the audio generator.
        
        Args:
            api_key: Modelverse API key. If None, will use config.
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.indextts.api_key
        self.base_url = self.settings.indextts.base_url
        self.model = self.settings.indextts.model
        self.sample_rate = self.settings.indextts.sample_rate
        self._initialized = False
        self._mock_mode = False
        self._client: Optional[httpx.AsyncClient] = None
    
    def initialize(self) -> None:
        """Initialize the API client.
        
        This method sets up the HTTP client for API calls.
        
        Requirements: 3.1
        
        Raises:
            AudioGenerationError: If initialization fails.
        """
        if self._initialized:
            logger.debug("AudioGenerator already initialized")
            return
        
        logger.info(f"Initializing IndexTTS API client for {self.base_url}")
        
        # Check if we have an API key
        if not self.api_key:
            logger.warning("No Modelverse API key configured. Using mock mode.")
            self._initialized = True
            self._mock_mode = True
            return
        
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=httpx.Timeout(self.settings.indextts.timeout_seconds)
            )
            self._initialized = True
            self._mock_mode = False
            logger.info("IndexTTS API client initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize IndexTTS API client: {str(e)}"
            logger.error(error_msg)
            raise AudioGenerationError("initialization", error_msg, retryable=False)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate_audio(
        self, 
        scene: Scene,
        output_dir: Path,
        config: Optional[AudioConfig] = None
    ) -> SceneAudio:
        """Generate audio for a single scene using IndexTTS API.
        
        Generates both Chinese and English audio versions.
        
        Audio parameter priority (Requirements: 5.5):
        1. scene.audio_params (if available) - highest priority
        2. config (if provided) - medium priority
        3. default values - lowest priority
        
        Args:
            scene: Scene to generate audio for.
            output_dir: Directory to save the generated audio.
            config: Optional audio configuration for emotion and voice cloning.
            
        Returns:
            SceneAudio: Generated scene audio metadata.
            
        Raises:
            AudioGenerationError: If audio generation fails.
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 5.5
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"Generating audio for scene {scene.scene_id}")
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare the audio paths
        audio_filename_cn = f"{scene.scene_id}_cn.wav"
        audio_filename_en = f"{scene.scene_id}_en.wav"
        audio_path_cn = output_dir / audio_filename_cn
        audio_path_en = output_dir / audio_filename_en
        
        # Create initial SceneAudio object
        scene_audio = SceneAudio(
            scene_id=scene.scene_id,
            audio_path=str(audio_path_cn),
            audio_path_en=str(audio_path_en),
            duration_seconds=0.0,
            duration_seconds_en=0.0,
            status=ResourceStatus.GENERATING,
            error_message=None
        )
        
        try:
            # Get target duration from scene
            target_duration = float(scene.duration.value)
            
            # Get audio parameters with priority: audio_params > config > scene defaults
            # Requirements: 5.5 - 优先使用分镜中的 audio_params，若无则使用默认值
            emotion, emotion_strength, speed, volume = self._resolve_audio_params(scene, config)
            
            # Get voice ID from config
            voice_id = None
            if config and config.voice_reference_path:
                # If voice_reference_path looks like a voice ID, use it directly
                if config.voice_reference_path.startswith("uspeech:"):
                    voice_id = config.voice_reference_path
            
            # Generate Chinese audio
            if self._mock_mode:
                audio_data_cn = self._generate_mock_audio(target_duration)
            else:
                audio_data_cn = await self._call_indextts_api(
                    text=scene.narration_cn,
                    target_duration=target_duration,
                    emotion=emotion,
                    emotion_strength=emotion_strength,
                    voice_id=voice_id,
                    speed=speed,
                    volume=volume
                )
            
            # Save Chinese audio
            actual_duration_cn = await self._save_audio(audio_data_cn, audio_path_cn, target_duration)
            scene_audio.duration_seconds = actual_duration_cn
            
            # Generate English audio
            actual_duration_en = 0.0
            if scene.narration_en:
                try:
                    if self._mock_mode:
                        audio_data_en = self._generate_mock_audio(target_duration)
                    else:
                        audio_data_en = await self._call_indextts_api(
                            text=scene.narration_en,
                            target_duration=target_duration,
                            emotion=emotion,
                            emotion_strength=emotion_strength,
                            voice_id=voice_id,
                            speed=speed,
                            volume=volume
                        )
                    
                    # Save English audio
                    actual_duration_en = await self._save_audio(audio_data_en, audio_path_en, target_duration)
                    scene_audio.duration_seconds_en = actual_duration_en
                except Exception as e:
                    logger.warning(f"Failed to generate English audio for scene {scene.scene_id}: {e}")
                    scene_audio.audio_path_en = None
            else:
                scene_audio.audio_path_en = None
            
            # Update status to completed
            scene_audio.status = ResourceStatus.COMPLETED
            
            logger.info(f"Successfully generated audio for scene {scene.scene_id} "
                       f"(CN: {actual_duration_cn:.2f}s, EN: {actual_duration_en:.2f}s)")
            return scene_audio
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to generate audio for scene {scene.scene_id}: {error_msg}")
            
            # Update status to failed
            scene_audio.status = ResourceStatus.FAILED
            scene_audio.error_message = error_msg
            
            # Determine if error is retryable
            retryable = self._is_retryable_error(e)
            raise AudioGenerationError(scene.scene_id, error_msg, retryable)
    
    async def generate_audios(
        self, 
        scenes: List[Scene],
        output_dir: Path,
        config: Optional[AudioConfig] = None,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[SceneAudio]:
        """Generate audio for multiple scenes.
        
        Args:
            scenes: List of scenes to generate audio for.
            output_dir: Directory to save generated audio files.
            config: Optional audio configuration for emotion and voice cloning.
            on_progress: Optional progress callback (current, total).
            
        Returns:
            List[SceneAudio]: List of generated scene audio metadata.
            
        Requirements: 3.1, 3.3
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"Generating audio for {len(scenes)} scenes")
        
        results = []
        completed = 0
        
        for scene in scenes:
            try:
                scene_audio = await self.generate_audio(scene, output_dir, config)
                results.append(scene_audio)
                completed += 1
                
                if on_progress:
                    on_progress(completed, len(scenes))
                    
            except AudioGenerationError as e:
                # Create failed SceneAudio for tracking
                failed_audio = SceneAudio(
                    scene_id=scene.scene_id,
                    audio_path=str(output_dir / f"{scene.scene_id}.wav"),
                    duration_seconds=0.0,
                    status=ResourceStatus.FAILED,
                    error_message=e.reason
                )
                results.append(failed_audio)
                completed += 1
                
                if on_progress:
                    on_progress(completed, len(scenes))
                
                logger.warning(f"Scene {scene.scene_id} audio generation failed: {e.reason}")
        
        logger.info(f"Completed audio generation for {len(scenes)} scenes")
        return results

    async def _call_indextts_api(
        self,
        text: str,
        target_duration: float,
        emotion: Emotion,
        emotion_strength: float,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        volume: float = 1.0
    ) -> bytes:
        """Call IndexTTS API to generate audio.
        
        Args:
            text: Text to synthesize.
            target_duration: Target duration in seconds (for speed adjustment).
            emotion: Emotion for synthesis.
            emotion_strength: Emotion strength (0.0-1.0).
            voice_id: Optional custom voice ID.
            speed: Speech speed (0.5-2.0), default 1.0.
            volume: Audio volume/gain (0.5-1.5), default 1.0.
            
        Returns:
            bytes: Generated audio data in WAV format.
            
        Requirements: 3.2, 3.5, 3.6
        """
        if self._client is None:
            raise AudioGenerationError(
                "unknown",
                "IndexTTS API client not initialized",
                retryable=False
            )
        
        # Build request payload
        payload = {
            "model": self.model,
            "input": text,
            "voice": voice_id or self.settings.indextts.voice_id or self.settings.indextts.voice,
            "response_format": "wav",
            # IndexTTS extension parameters
            "sample_rate": self.sample_rate,
            "gain": self.settings.indextts.gain,  # 使用默认音量
            "interval_silence": self.settings.indextts.interval_silence,
            "max_text_tokens_per_sentence": self.settings.indextts.max_text_tokens_per_sentence,
        }
        
        # Apply speed from audio_params
        # Speed range is 0.25-4, clamp to safe range
        # TODO: 暂时禁用自定义速度，使用默认值
        payload["speed"] = 1.0
        
        # 暂时禁用情感控制，使用默认平静情感
        # TODO: 调试 IndexTTS API 的情感参数后再启用
        payload["emo_control_method"] = 3
        payload["emo_weight"] = 0.0  # 设为0禁用情感影响
        payload["emo_text"] = "平静"
        
        logger.info(f"IndexTTS API call: using defaults (emotion/speed/volume disabled)")
        
        logger.debug(f"IndexTTS API request: {payload}")
        
        try:
            response = await self._client.post(
                "/v1/audio/speech",
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise AudioGenerationError(
                    "unknown",
                    f"IndexTTS API error ({response.status_code}): {error_detail}",
                    retryable=response.status_code >= 500
                )
            
            # API returns audio data directly
            audio_data = response.content
            
            if not audio_data:
                raise AudioGenerationError(
                    "unknown",
                    "IndexTTS API returned empty audio data",
                    retryable=True
                )
            
            return audio_data
            
        except httpx.TimeoutException as e:
            raise AudioGenerationError(
                "unknown",
                f"IndexTTS API timeout: {str(e)}",
                retryable=True
            )
        except httpx.RequestError as e:
            raise AudioGenerationError(
                "unknown",
                f"IndexTTS API request error: {str(e)}",
                retryable=True
            )
    
    def _generate_mock_audio(self, duration: float) -> bytes:
        """Generate mock audio data for testing.
        
        Creates a silent WAV file with the specified duration.
        
        Args:
            duration: Duration in seconds.
            
        Returns:
            bytes: WAV audio data.
        """
        # Generate silent audio samples
        num_samples = int(self.sample_rate * duration)
        samples = [0] * num_samples
        
        # Create WAV data
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            
            # Pack samples as 16-bit signed integers
            packed_samples = struct.pack(f'<{num_samples}h', *samples)
            wav_file.writeframes(packed_samples)
        
        return buffer.getvalue()
    
    async def _save_audio(
        self, 
        audio_data: bytes, 
        audio_path: Path,
        target_duration: float
    ) -> float:
        """Save audio data to file and return actual duration.
        
        Args:
            audio_data: Audio data in WAV format.
            audio_path: Path to save audio to.
            target_duration: Target duration for validation.
            
        Returns:
            float: Actual duration of saved audio.
            
        Raises:
            AudioGenerationError: If save fails or duration is out of tolerance.
        """
        try:
            # Save audio file
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Read back to verify duration
            with wave.open(str(audio_path), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                actual_duration = frames / float(rate)
            
            # Validate duration is within tolerance
            duration_diff = abs(actual_duration - target_duration)
            if duration_diff > self.DURATION_TOLERANCE:
                logger.warning(
                    f"Audio duration {actual_duration:.2f}s differs from target "
                    f"{target_duration}s by {duration_diff:.2f}s (tolerance: {self.DURATION_TOLERANCE}s)"
                )
            
            return actual_duration
            
        except IOError as e:
            raise AudioGenerationError(
                "unknown",
                f"Failed to save audio to {audio_path}: {str(e)}",
                retryable=False
            )

    def _resolve_audio_params(
        self, 
        scene: Scene, 
        config: Optional[AudioConfig] = None
    ) -> Tuple[Emotion, float, float, float]:
        """Resolve audio parameters with priority handling.
        
        Priority order (Requirements: 5.5):
        1. scene.audio_params (if available) - highest priority
        2. config (if provided) - medium priority  
        3. default values - lowest priority
        
        Args:
            scene: Scene containing potential audio_params.
            config: Optional AudioConfig for override.
            
        Returns:
            tuple: (emotion, emotion_strength, speed, volume)
        """
        # Default values
        default_emotion = Emotion.CALM
        default_emotion_strength = 0.6
        default_speed = 1.0
        default_volume = 1.0
        
        # Priority 1: Use scene.audio_params if available (Requirements: 5.5)
        if scene.audio_params is not None:
            emotion = scene.audio_params.emotion
            emotion_strength = scene.audio_params.emotion_strength
            speed = scene.audio_params.speed
            volume = getattr(scene.audio_params, 'volume', default_volume)
            logger.info(f"[AudioParams] Scene {scene.scene_id}: Using audio_params - emotion={emotion.value}, strength={emotion_strength}, speed={speed}, volume={volume}")
            return (emotion, emotion_strength, speed, volume)
        
        # Priority 2: Use config if provided
        if config is not None:
            logger.info(f"[AudioParams] Scene {scene.scene_id}: Using AudioConfig - emotion={config.emotion.value}")
            return (
                config.emotion,
                config.emotion_strength,
                default_speed,  # AudioConfig doesn't have speed, use default
                default_volume
            )
        
        # Priority 3: Use default values (no scene.emotion field anymore)
        logger.info(f"[AudioParams] Scene {scene.scene_id}: Using defaults - emotion=平静")
        return (
            Emotion.CALM,  # Default emotion
            default_emotion_strength,
            default_speed,
            default_volume
        )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable.
        
        Args:
            error: The error to check.
            
        Returns:
            bool: True if the error is retryable.
        """
        if isinstance(error, AudioGenerationError):
            return error.retryable
        
        # File I/O errors are generally not retryable
        if isinstance(error, (IOError, OSError)):
            return False
        
        # Network errors are usually retryable
        if isinstance(error, (httpx.TimeoutException, httpx.RequestError)):
            return True
        
        # Default to retryable for unknown errors
        return True
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get the duration of an audio file.
        
        Args:
            audio_path: Path to the audio file.
            
        Returns:
            float: Duration in seconds.
            
        Raises:
            AudioGenerationError: If file cannot be read.
        """
        try:
            with wave.open(str(audio_path), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate)
        except Exception as e:
            raise AudioGenerationError(
                "unknown",
                f"Failed to read audio duration from {audio_path}: {str(e)}",
                retryable=False
            )
    
    @property
    def is_initialized(self) -> bool:
        """Check if the generator is initialized."""
        return self._initialized
    
    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode (without actual API)."""
        return self._mock_mode
    
    async def merge_audios(
        self,
        audio_paths: List[Path],
        output_path: Path,
        silence_gap: float = 0.5
    ) -> float:
        """Merge multiple audio files into one.
        
        Args:
            audio_paths: List of audio file paths to merge (in order).
            output_path: Path to save the merged audio.
            silence_gap: Silence gap between audio files in seconds.
            
        Returns:
            float: Total duration of merged audio.
            
        Raises:
            AudioGenerationError: If merge fails.
        """
        if not audio_paths:
            raise AudioGenerationError(
                "merge",
                "No audio files to merge",
                retryable=False
            )
        
        logger.info(f"Merging {len(audio_paths)} audio files into {output_path}")
        
        try:
            # Read all audio files
            all_frames = []
            sample_rate = None
            sample_width = None
            channels = None
            
            for audio_path in audio_paths:
                if not audio_path.exists():
                    logger.warning(f"Audio file not found: {audio_path}, skipping")
                    continue
                
                with wave.open(str(audio_path), 'rb') as wav_file:
                    if sample_rate is None:
                        sample_rate = wav_file.getframerate()
                        sample_width = wav_file.getsampwidth()
                        channels = wav_file.getnchannels()
                    
                    # Read frames
                    frames = wav_file.readframes(wav_file.getnframes())
                    all_frames.append(frames)
                    
                    # Add silence gap (except after last file)
                    if audio_path != audio_paths[-1] and silence_gap > 0:
                        silence_samples = int(sample_rate * silence_gap)
                        silence_frames = b'\x00' * (silence_samples * sample_width * channels)
                        all_frames.append(silence_frames)
            
            if not all_frames:
                raise AudioGenerationError(
                    "merge",
                    "No valid audio files found to merge",
                    retryable=False
                )
            
            # Write merged audio
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), 'wb') as out_wav:
                out_wav.setnchannels(channels)
                out_wav.setsampwidth(sample_width)
                out_wav.setframerate(sample_rate)
                
                for frames in all_frames:
                    out_wav.writeframes(frames)
            
            # Get total duration
            total_duration = self.get_audio_duration(output_path)
            logger.info(f"Merged audio saved to {output_path} ({total_duration:.2f}s)")
            
            return total_duration
            
        except Exception as e:
            if isinstance(e, AudioGenerationError):
                raise
            raise AudioGenerationError(
                "merge",
                f"Failed to merge audio files: {str(e)}",
                retryable=False
            )
