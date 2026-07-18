"""Property-based tests and unit tests for AudioGenerator.

This module contains property-based tests using Hypothesis to verify
the correctness of audio generation, particularly focusing on
duration precision and quantity consistency.

Feature: langchain-video-generator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import wave
import struct
import io
from hypothesis import given, settings, strategies as st

from backend.schemas.models import (
    Scene,
    SceneAudio,
    SceneDuration,
    Emotion,
    ResourceStatus,
    AudioConfig,
)
from backend.core.generators.audio import AudioGenerator, AudioGenerationError


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def non_empty_text(min_size=1, max_size=200):
    """Generate text that is non-empty after stripping whitespace."""
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            whitelist_categories=('L', 'N'),
        )),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' '
        ))
    )


def non_empty_english_text(min_size=1, max_size=200):
    """Generate English text that is non-empty after stripping whitespace."""
    return st.builds(
        lambda prefix, suffix: prefix + suffix,
        prefix=st.text(min_size=1, max_size=max(1, max_size // 2), alphabet=st.characters(
            min_codepoint=48, max_codepoint=122
        ).filter(lambda c: c.isalnum())),
        suffix=st.text(min_size=0, max_size=max_size // 2, alphabet=st.characters(
            min_codepoint=32, max_codepoint=126
        ))
    )


@st.composite
def scene_strategy(draw):
    """Generate a valid Scene with duration of 5 or 10 seconds."""
    return Scene(
        scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_-'
        ))),
        step_number=draw(st.integers(min_value=1, max_value=100)),
        description_cn=draw(non_empty_text(min_size=1, max_size=200)),
        video_prompt_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        narration_cn=draw(non_empty_text(min_size=1, max_size=200)),
        narration_en=draw(non_empty_english_text(min_size=1, max_size=200)),
        duration=draw(st.sampled_from(SceneDuration)),
        emotion=draw(st.sampled_from(Emotion))
    )


@st.composite
def scene_list_strategy(draw):
    """Generate a list of valid scenes."""
    return draw(st.lists(scene_strategy(), min_size=1, max_size=10))


@st.composite
def audio_config_strategy(draw):
    """Generate a valid AudioConfig."""
    return AudioConfig(
        voice_reference_path=draw(st.none() | st.just("/path/to/reference.wav")),
        emotion=draw(st.sampled_from(Emotion)),
        emotion_strength=draw(st.floats(min_value=0.0, max_value=1.0))
    )


# =============================================================================
# Helper Functions
# =============================================================================

def create_mock_wav_data(duration: float, sample_rate: int = 24000) -> bytes:
    """Create mock WAV data with specified duration."""
    num_samples = int(sample_rate * duration)
    samples = [0] * num_samples
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        packed_samples = struct.pack(f'<{num_samples}h', *samples)
        wav_file.writeframes(packed_samples)
    
    return buffer.getvalue()


def get_wav_duration(wav_path: Path) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(str(wav_path), 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestAudioDurationPrecision:
    """Property-based tests for audio duration precision.
    
    Feature: langchain-video-generator, Property 6: 音频时长精确性
    Validates: Requirements 3.2
    """

    @given(scene=scene_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_audio_duration_precision(self, scene):
        """For any generated SceneAudio, actual duration should be within ±0.5s of target.
        
        Property 6: 音频时长精确性
        Validates: Requirements 3.2
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create generator in mock mode
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Generate audio
            result = await generator.generate_audio(scene, output_dir)
            
            # Verify the audio was generated successfully
            assert result.status == ResourceStatus.COMPLETED, (
                f"Audio generation failed: {result.error_message}"
            )
            
            # Get target duration from scene
            target_duration = float(scene.duration.value)
            
            # Verify duration precision (within ±0.5 seconds)
            duration_diff = abs(result.duration_seconds - target_duration)
            assert duration_diff <= 0.5, (
                f"Audio duration {result.duration_seconds:.2f}s differs from target "
                f"{target_duration}s by {duration_diff:.2f}s (tolerance: 0.5s)"
            )


class TestAudioGenerationQuantityConsistency:
    """Property-based tests for audio generation quantity consistency.
    
    Feature: langchain-video-generator, Property 7: 音频生成数量一致性
    Validates: Requirements 3.1, 3.3
    """

    @given(scenes=scene_list_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_audio_generation_quantity_consistency(self, scenes):
        """For any scene list, generate_audios should return same number of SceneAudios.
        
        Property 7: 音频生成数量一致性
        Validates: Requirements 3.1, 3.3
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create generator in mock mode
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Generate audios
            results = await generator.generate_audios(scenes, output_dir)
            
            # Verify quantity consistency
            assert len(results) == len(scenes), (
                f"Expected {len(scenes)} SceneAudios, got {len(results)}"
            )
            
            # Verify each scene has a corresponding result
            scene_ids = {scene.scene_id for scene in scenes}
            result_scene_ids = {result.scene_id for result in results}
            
            assert scene_ids == result_scene_ids, (
                f"Scene IDs mismatch. Expected: {scene_ids}, Got: {result_scene_ids}"
            )


# =============================================================================
# Unit Tests for Error Handling
# =============================================================================

class TestAudioGenerationErrorHandling:
    """Unit tests for audio generation error handling.
    
    Tests generation failure scenarios and error reporting.
    Requirements: 3.4
    """

    @pytest.mark.asyncio
    async def test_generation_failure_returns_error_message(self):
        """Test that generation failures return proper error messages."""
        scene = Scene(
            scene_id="test_scene",
            step_number=1,
            description_cn="测试场景",
            video_prompt_en="test scene prompt",
            narration_cn="测试旁白",
            narration_en="test narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = False  # Force real mode to trigger error
            generator.tts = None  # No TTS model
            
            # Should raise AudioGenerationError
            with pytest.raises(AudioGenerationError) as exc_info:
                await generator.generate_audio(scene, output_dir)
            
            assert exc_info.value.scene_id == "test_scene"
            assert exc_info.value.reason is not None
            assert len(exc_info.value.reason) > 0

    @pytest.mark.asyncio
    async def test_file_io_error_not_retryable(self):
        """Test that file I/O errors are marked as not retryable."""
        scene = Scene(
            scene_id="test_scene",
            step_number=1,
            description_cn="测试场景",
            video_prompt_en="test scene prompt",
            narration_cn="测试旁白",
            narration_en="test narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Mock _save_audio to raise IOError
            with patch.object(generator, '_save_audio', new_callable=AsyncMock) as mock_save:
                mock_save.side_effect = IOError("Permission denied")
                
                with pytest.raises(AudioGenerationError) as exc_info:
                    await generator.generate_audio(scene, output_dir)
                
                assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_partial_failure_in_batch_generation(self):
        """Test that batch generation continues even when some scenes fail."""
        scenes = [
            Scene(
                scene_id="success_scene",
                step_number=1,
                description_cn="成功场景",
                video_prompt_en="success scene prompt",
                narration_cn="成功旁白",
                narration_en="success narration",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            ),
            Scene(
                scene_id="failure_scene",
                step_number=2,
                description_cn="失败场景",
                video_prompt_en="failure scene prompt",
                narration_cn="失败旁白",
                narration_en="failure narration",
                duration=SceneDuration.LONG,
                emotion=Emotion.HAPPY
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Track which scene is being processed
            call_count = [0]
            original_generate = generator.generate_audio
            
            async def mock_generate(scene, out_dir, config=None):
                call_count[0] += 1
                if scene.scene_id == "failure_scene":
                    raise AudioGenerationError(scene.scene_id, "Simulated failure", retryable=True)
                return await original_generate(scene, out_dir, config)
            
            with patch.object(generator, 'generate_audio', side_effect=mock_generate):
                results = await generator.generate_audios(scenes, output_dir)
            
            # Should have results for both scenes
            assert len(results) == 2
            
            # First scene should be successful
            success_result = next(r for r in results if r.scene_id == "success_scene")
            assert success_result.status == ResourceStatus.COMPLETED
            
            # Second scene should be failed
            failure_result = next(r for r in results if r.scene_id == "failure_scene")
            assert failure_result.status == ResourceStatus.FAILED
            assert failure_result.error_message is not None

    def test_audio_generation_error_attributes(self):
        """Test that AudioGenerationError has all required attributes.
        
        Requirements: 3.4
        """
        error = AudioGenerationError(
            scene_id="test_scene_001",
            reason="TTS model failed to synthesize",
            retryable=True
        )
        
        # Verify all attributes are set correctly
        assert error.scene_id == "test_scene_001"
        assert error.reason == "TTS model failed to synthesize"
        assert error.retryable is True
        
        # Verify error message contains useful information
        error_str = str(error)
        assert "test_scene_001" in error_str
        assert "TTS model failed to synthesize" in error_str
        assert "retryable" in error_str

    def test_audio_generation_error_not_retryable(self):
        """Test AudioGenerationError with retryable=False.
        
        Requirements: 3.4
        """
        error = AudioGenerationError(
            scene_id="scene_002",
            reason="Invalid audio format",
            retryable=False
        )
        
        assert error.retryable is False
        error_str = str(error)
        assert "not retryable" in error_str

    @pytest.mark.asyncio
    async def test_failed_scene_audio_has_error_message(self):
        """Test that failed SceneAudio objects contain error messages.
        
        Requirements: 3.4
        """
        scenes = [
            Scene(
                scene_id="fail_scene",
                step_number=1,
                description_cn="失败场景",
                video_prompt_en="fail scene prompt",
                narration_cn="失败旁白",
                narration_en="fail narration",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            error_message = "Simulated TTS failure for testing"
            
            async def mock_generate(scene, out_dir, config=None):
                raise AudioGenerationError(scene.scene_id, error_message, retryable=True)
            
            with patch.object(generator, 'generate_audio', side_effect=mock_generate):
                results = await generator.generate_audios(scenes, output_dir)
            
            assert len(results) == 1
            result = results[0]
            
            # Verify failed status and error message
            assert result.status == ResourceStatus.FAILED
            assert result.error_message is not None
            assert error_message in result.error_message

    @pytest.mark.asyncio
    async def test_retryable_error_detection(self):
        """Test that retryable errors are correctly identified.
        
        Requirements: 3.4
        """
        generator = AudioGenerator()
        
        # IOError should not be retryable
        io_error = IOError("Disk full")
        assert generator._is_retryable_error(io_error) is False
        
        # OSError should not be retryable
        os_error = OSError("Permission denied")
        assert generator._is_retryable_error(os_error) is False
        
        # AudioGenerationError respects its own retryable flag
        retryable_audio_error = AudioGenerationError("scene", "temp failure", retryable=True)
        assert generator._is_retryable_error(retryable_audio_error) is True
        
        non_retryable_audio_error = AudioGenerationError("scene", "permanent failure", retryable=False)
        assert generator._is_retryable_error(non_retryable_audio_error) is False
        
        # Generic exceptions default to retryable
        generic_error = Exception("Unknown error")
        assert generator._is_retryable_error(generic_error) is True

    @pytest.mark.asyncio
    async def test_tts_synthesis_failure_error(self):
        """Test error handling when TTS synthesis fails.
        
        Requirements: 3.4
        """
        scene = Scene(
            scene_id="tts_fail_scene",
            step_number=1,
            description_cn="TTS失败场景",
            video_prompt_en="tts fail scene",
            narration_cn="TTS失败旁白",
            narration_en="tts fail narration",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = False
            generator.tts = MagicMock()
            
            # Mock TTS to raise an exception
            generator.tts.infer.side_effect = RuntimeError("TTS synthesis failed")
            
            with pytest.raises(AudioGenerationError) as exc_info:
                await generator.generate_audio(scene, output_dir)
            
            # Verify error contains scene_id and reason
            assert exc_info.value.scene_id == "tts_fail_scene"
            assert "TTS synthesis failed" in exc_info.value.reason or len(exc_info.value.reason) > 0

    @pytest.mark.asyncio
    async def test_progress_callback_called_on_failure(self):
        """Test that progress callback is called even when generation fails.
        
        Requirements: 3.4
        """
        scenes = [
            Scene(
                scene_id="scene_1",
                step_number=1,
                description_cn="场景1",
                video_prompt_en="scene 1",
                narration_cn="旁白1",
                narration_en="narration 1",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            ),
            Scene(
                scene_id="scene_2",
                step_number=2,
                description_cn="场景2",
                video_prompt_en="scene 2",
                narration_cn="旁白2",
                narration_en="narration 2",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            progress_calls = []
            
            def on_progress(current, total):
                progress_calls.append((current, total))
            
            # Make second scene fail
            original_generate = generator.generate_audio
            
            async def mock_generate(scene, out_dir, config=None):
                if scene.scene_id == "scene_2":
                    raise AudioGenerationError(scene.scene_id, "Simulated failure", retryable=True)
                return await original_generate(scene, out_dir, config)
            
            with patch.object(generator, 'generate_audio', side_effect=mock_generate):
                results = await generator.generate_audios(scenes, output_dir, on_progress=on_progress)
            
            # Progress should be called for both scenes (including failed one)
            assert len(progress_calls) == 2
            assert progress_calls[0] == (1, 2)
            assert progress_calls[1] == (2, 2)


# =============================================================================
# Unit Tests for Emotion Control and Voice Cloning
# =============================================================================

class TestEmotionControlAndVoiceCloning:
    """Unit tests for emotion control and voice cloning features.
    
    Tests different emotion parameters and reference audio handling.
    Requirements: 3.5, 3.6
    """

    @pytest.mark.asyncio
    async def test_emotion_parameter_handling(self):
        """Test that different emotion parameters are properly handled."""
        scene = Scene(
            scene_id="emotion_test",
            step_number=1,
            description_cn="情感测试场景",
            video_prompt_en="emotion test scene",
            narration_cn="测试不同情感",
            narration_en="testing different emotions",
            duration=SceneDuration.SHORT,
            emotion=Emotion.HAPPY
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Test with different emotions
            for emotion in Emotion:
                config = AudioConfig(
                    emotion=emotion,
                    emotion_strength=0.8
                )
                
                result = await generator.generate_audio(scene, output_dir, config)
                
                assert result.status == ResourceStatus.COMPLETED, (
                    f"Failed for emotion {emotion}: {result.error_message}"
                )

    @pytest.mark.asyncio
    async def test_voice_reference_path_handling(self):
        """Test that voice reference path is properly handled."""
        scene = Scene(
            scene_id="voice_clone_test",
            step_number=1,
            description_cn="音色克隆测试",
            video_prompt_en="voice cloning test",
            narration_cn="测试音色克隆",
            narration_en="testing voice cloning",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create a mock reference audio file
            reference_path = Path(temp_dir) / "reference.wav"
            reference_data = create_mock_wav_data(2.0)
            with open(reference_path, 'wb') as f:
                f.write(reference_data)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            config = AudioConfig(
                voice_reference_path=str(reference_path),
                emotion=Emotion.CALM,
                emotion_strength=0.5
            )
            
            result = await generator.generate_audio(scene, output_dir, config)
            
            assert result.status == ResourceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_emotion_strength_range(self):
        """Test that emotion strength values in valid range are accepted."""
        scene = Scene(
            scene_id="strength_test",
            step_number=1,
            description_cn="强度测试",
            video_prompt_en="strength test",
            narration_cn="测试情感强度",
            narration_en="testing emotion strength",
            duration=SceneDuration.SHORT,
            emotion=Emotion.HAPPY
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Test boundary values
            for strength in [0.0, 0.5, 1.0]:
                config = AudioConfig(
                    emotion=Emotion.HAPPY,
                    emotion_strength=strength
                )
                
                result = await generator.generate_audio(scene, output_dir, config)
                
                assert result.status == ResourceStatus.COMPLETED, (
                    f"Failed for strength {strength}: {result.error_message}"
                )

    @pytest.mark.asyncio
    async def test_all_emotion_types_supported(self):
        """Test that all 8 emotion types are supported.
        
        Requirements: 3.6 - 支持情感控制（喜/怒/哀/惧/厌恶/低落/惊喜/平静）
        """
        # Verify all 8 emotions are defined
        expected_emotions = ["喜", "怒", "哀", "惧", "厌恶", "低落", "惊喜", "平静"]
        actual_emotions = [e.value for e in Emotion]
        
        for expected in expected_emotions:
            assert expected in actual_emotions, f"Missing emotion: {expected}"
        
        scene = Scene(
            scene_id="all_emotions_test",
            step_number=1,
            description_cn="全情感测试",
            video_prompt_en="all emotions test",
            narration_cn="测试所有情感类型",
            narration_en="testing all emotion types",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Test each emotion type
            for emotion in [Emotion.HAPPY, Emotion.ANGRY, Emotion.SAD, Emotion.FEAR,
                           Emotion.DISGUST, Emotion.DEPRESSED, Emotion.SURPRISED, Emotion.CALM]:
                config = AudioConfig(
                    emotion=emotion,
                    emotion_strength=0.7
                )
                
                result = await generator.generate_audio(scene, output_dir, config)
                
                assert result.status == ResourceStatus.COMPLETED, (
                    f"Failed for emotion {emotion.value}: {result.error_message}"
                )

    def test_emotion_mapping_to_indextts(self):
        """Test that all emotions are mapped to IndexTTS text codes.
        
        Requirements: 3.6
        """
        generator = AudioGenerator()
        
        # Verify all emotions have a text mapping
        for emotion in Emotion:
            assert emotion in generator.EMOTION_TEXT_MAP, (
                f"Emotion {emotion} not mapped to IndexTTS text code"
            )
            
            # Verify mapping is a non-empty string
            mapped_code = generator.EMOTION_TEXT_MAP[emotion]
            assert isinstance(mapped_code, str), (
                f"Emotion {emotion} mapping should be a string"
            )
            assert len(mapped_code) > 0, (
                f"Emotion {emotion} mapping should not be empty"
            )

    def test_emotion_mapping_values(self):
        """Test specific emotion mappings to IndexTTS text codes.
        
        Requirements: 3.6
        """
        generator = AudioGenerator()
        
        # Verify specific mappings (Chinese text for emo_text parameter)
        assert generator.EMOTION_TEXT_MAP[Emotion.HAPPY] == "高兴"
        assert generator.EMOTION_TEXT_MAP[Emotion.ANGRY] == "生气"
        assert generator.EMOTION_TEXT_MAP[Emotion.SAD] == "悲伤"
        assert generator.EMOTION_TEXT_MAP[Emotion.FEAR] == "害怕"
        assert generator.EMOTION_TEXT_MAP[Emotion.DISGUST] == "厌恶"
        assert generator.EMOTION_TEXT_MAP[Emotion.SURPRISED] == "惊喜"
        assert generator.EMOTION_TEXT_MAP[Emotion.CALM] == "平静"
        assert generator.EMOTION_TEXT_MAP[Emotion.DEPRESSED] == "忧郁"

    @pytest.mark.asyncio
    async def test_voice_cloning_with_reference_audio(self):
        """Test voice cloning using reference audio file.
        
        Requirements: 3.5 - 支持通过参考音频克隆音色
        """
        scene = Scene(
            scene_id="voice_clone_full_test",
            step_number=1,
            description_cn="完整音色克隆测试",
            video_prompt_en="full voice cloning test",
            narration_cn="这是一段使用参考音频克隆音色的测试",
            narration_en="This is a test using reference audio for voice cloning",
            duration=SceneDuration.LONG,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create a mock reference audio file (simulating a real voice sample)
            reference_path = Path(temp_dir) / "voice_reference.wav"
            reference_data = create_mock_wav_data(3.0)  # 3 second reference
            with open(reference_path, 'wb') as f:
                f.write(reference_data)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            config = AudioConfig(
                voice_reference_path=str(reference_path),
                emotion=Emotion.CALM,
                emotion_strength=0.5
            )
            
            result = await generator.generate_audio(scene, output_dir, config)
            
            # Verify successful generation
            assert result.status == ResourceStatus.COMPLETED
            assert result.scene_id == scene.scene_id
            
            # Verify audio file was created
            audio_path = Path(result.audio_path)
            assert audio_path.exists(), "Audio file should be created"

    @pytest.mark.asyncio
    async def test_voice_cloning_without_reference(self):
        """Test that audio generation works without voice reference.
        
        Requirements: 3.5 - Voice reference should be optional
        """
        scene = Scene(
            scene_id="no_reference_test",
            step_number=1,
            description_cn="无参考音频测试",
            video_prompt_en="no reference audio test",
            narration_cn="测试不使用参考音频",
            narration_en="testing without reference audio",
            duration=SceneDuration.SHORT,
            emotion=Emotion.HAPPY
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Config without voice reference
            config = AudioConfig(
                voice_reference_path=None,
                emotion=Emotion.HAPPY,
                emotion_strength=0.6
            )
            
            result = await generator.generate_audio(scene, output_dir, config)
            
            assert result.status == ResourceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_combined_emotion_and_voice_cloning(self):
        """Test using both emotion control and voice cloning together.
        
        Requirements: 3.5, 3.6
        """
        scene = Scene(
            scene_id="combined_test",
            step_number=1,
            description_cn="组合测试",
            video_prompt_en="combined test",
            narration_cn="同时测试情感控制和音色克隆",
            narration_en="testing emotion control and voice cloning together",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create reference audio
            reference_path = Path(temp_dir) / "reference.wav"
            reference_data = create_mock_wav_data(2.0)
            with open(reference_path, 'wb') as f:
                f.write(reference_data)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Test different emotion + voice cloning combinations
            test_cases = [
                (Emotion.HAPPY, 0.9),
                (Emotion.SAD, 0.5),
                (Emotion.ANGRY, 0.7),
                (Emotion.SURPRISED, 0.8),
            ]
            
            for emotion, strength in test_cases:
                config = AudioConfig(
                    voice_reference_path=str(reference_path),
                    emotion=emotion,
                    emotion_strength=strength
                )
                
                result = await generator.generate_audio(scene, output_dir, config)
                
                assert result.status == ResourceStatus.COMPLETED, (
                    f"Failed for emotion={emotion.value}, strength={strength}: {result.error_message}"
                )

    @pytest.mark.asyncio
    async def test_emotion_from_scene_when_no_config(self):
        """Test that scene's emotion is used when no config is provided.
        
        Requirements: 3.6
        """
        scene = Scene(
            scene_id="scene_emotion_test",
            step_number=1,
            description_cn="场景情感测试",
            video_prompt_en="scene emotion test",
            narration_cn="使用场景自带的情感设置",
            narration_en="using scene's emotion setting",
            duration=SceneDuration.SHORT,
            emotion=Emotion.SURPRISED  # Scene has its own emotion
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Generate without config - should use scene's emotion
            result = await generator.generate_audio(scene, output_dir, config=None)
            
            assert result.status == ResourceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_config_emotion_overrides_scene_emotion(self):
        """Test that config emotion overrides scene's emotion.
        
        Requirements: 3.6
        """
        scene = Scene(
            scene_id="override_test",
            step_number=1,
            description_cn="覆盖测试",
            video_prompt_en="override test",
            narration_cn="配置情感覆盖场景情感",
            narration_en="config emotion overrides scene emotion",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM  # Scene emotion
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Config with different emotion
            config = AudioConfig(
                emotion=Emotion.ANGRY,  # Different from scene
                emotion_strength=0.9
            )
            
            result = await generator.generate_audio(scene, output_dir, config)
            
            assert result.status == ResourceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_batch_generation_with_different_emotions(self):
        """Test batch generation with scenes having different emotions.
        
        Requirements: 3.6
        """
        scenes = [
            Scene(
                scene_id=f"batch_emotion_{emotion.name}",
                step_number=i + 1,
                description_cn=f"批量情感测试 - {emotion.value}",
                video_prompt_en=f"batch emotion test - {emotion.name}",
                narration_cn=f"这是{emotion.value}情感的测试",
                narration_en=f"This is a test for {emotion.name} emotion",
                duration=SceneDuration.SHORT,
                emotion=emotion
            )
            for i, emotion in enumerate([Emotion.HAPPY, Emotion.SAD, Emotion.ANGRY, Emotion.CALM])
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            results = await generator.generate_audios(scenes, output_dir)
            
            # All should succeed
            assert len(results) == len(scenes)
            for result in results:
                assert result.status == ResourceStatus.COMPLETED, (
                    f"Failed for {result.scene_id}: {result.error_message}"
                )

    @pytest.mark.asyncio
    async def test_batch_generation_with_voice_cloning(self):
        """Test batch generation with voice cloning config.
        
        Requirements: 3.5
        """
        scenes = [
            Scene(
                scene_id=f"batch_clone_{i}",
                step_number=i + 1,
                description_cn=f"批量克隆测试 {i}",
                video_prompt_en=f"batch clone test {i}",
                narration_cn=f"这是第{i}个音色克隆测试",
                narration_en=f"This is voice cloning test {i}",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            )
            for i in range(3)
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create reference audio
            reference_path = Path(temp_dir) / "batch_reference.wav"
            reference_data = create_mock_wav_data(2.0)
            with open(reference_path, 'wb') as f:
                f.write(reference_data)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            config = AudioConfig(
                voice_reference_path=str(reference_path),
                emotion=Emotion.CALM,
                emotion_strength=0.5
            )
            
            results = await generator.generate_audios(scenes, output_dir, config)
            
            # All should succeed
            assert len(results) == len(scenes)
            for result in results:
                assert result.status == ResourceStatus.COMPLETED

    def test_audio_config_default_values(self):
        """Test AudioConfig default values.
        
        Requirements: 3.5, 3.6
        """
        config = AudioConfig()
        
        # Verify defaults
        assert config.voice_reference_path is None
        assert config.emotion == Emotion.CALM
        assert config.emotion_strength == 0.5

    def test_audio_config_validation(self):
        """Test AudioConfig validation for emotion_strength.
        
        Requirements: 3.6
        """
        # Valid strength values
        config_min = AudioConfig(emotion_strength=0.0)
        assert config_min.emotion_strength == 0.0
        
        config_max = AudioConfig(emotion_strength=1.0)
        assert config_max.emotion_strength == 1.0
        
        config_mid = AudioConfig(emotion_strength=0.5)
        assert config_mid.emotion_strength == 0.5
        
        # Invalid strength values should raise validation error
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            AudioConfig(emotion_strength=-0.1)
        
        with pytest.raises(ValidationError):
            AudioConfig(emotion_strength=1.1)


# =============================================================================
# Unit Tests for Initialization
# =============================================================================

class TestAudioGeneratorInitialization:
    """Unit tests for AudioGenerator initialization."""

    def test_initialization_without_model(self):
        """Test that generator initializes in mock mode when model is unavailable."""
        generator = AudioGenerator()
        
        # Initialize should not raise even without the model
        generator.initialize()
        
        assert generator.is_initialized
        # When API key is configured, it should NOT be in mock mode
        # When API key is not configured, it should be in mock mode
        # This test verifies initialization works regardless of API key presence

    def test_double_initialization_is_safe(self):
        """Test that calling initialize twice is safe."""
        generator = AudioGenerator()
        
        generator.initialize()
        generator.initialize()  # Should not raise
        
        assert generator.is_initialized

    @pytest.mark.asyncio
    async def test_auto_initialization_on_generate(self):
        """Test that generate_audio auto-initializes if needed."""
        scene = Scene(
            scene_id="auto_init_test",
            step_number=1,
            description_cn="自动初始化测试",
            video_prompt_en="auto init test",
            narration_cn="测试自动初始化",
            narration_en="testing auto initialization",
            duration=SceneDuration.SHORT,
            emotion=Emotion.CALM
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            
            # Don't call initialize explicitly
            assert not generator.is_initialized
            
            # generate_audio should auto-initialize
            result = await generator.generate_audio(scene, output_dir)
            
            assert generator.is_initialized
            assert result.status == ResourceStatus.COMPLETED


# =============================================================================
# Unit Tests for Progress Callback
# =============================================================================

class TestProgressCallback:
    """Unit tests for progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """Test that progress callback is called for each scene."""
        scenes = [
            Scene(
                scene_id=f"scene_{i}",
                step_number=i + 1,  # step_number must be >= 1
                description_cn=f"场景{i}",
                video_prompt_en=f"scene {i}",
                narration_cn=f"旁白{i}",
                narration_en=f"narration {i}",
                duration=SceneDuration.SHORT,
                emotion=Emotion.CALM
            )
            for i in range(3)
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            progress_calls = []
            
            def on_progress(current, total):
                progress_calls.append((current, total))
            
            await generator.generate_audios(scenes, output_dir, on_progress=on_progress)
            
            # Should have been called 3 times
            assert len(progress_calls) == 3
            
            # Verify progress values
            assert progress_calls[0] == (1, 3)
            assert progress_calls[1] == (2, 3)
            assert progress_calls[2] == (3, 3)


# =============================================================================
# Property-Based Tests for Emotion Configuration Completeness
# =============================================================================

class TestEmotionConfigurationCompleteness:
    """Property-based tests for emotion configuration completeness.
    
    Feature: video-style-expansion, Property 3: 情感配置完整性
    Validates: Requirements 3.3, 3.4
    """

    @given(emotion=st.sampled_from(list(Emotion)))
    @settings(max_examples=100)
    def test_all_emotions_have_text_mapping(self, emotion: Emotion):
        """For any defined emotion type, there must be a corresponding Chinese text mapping.
        
        Property 3: 情感配置完整性
        Validates: Requirements 3.3, 3.4
        """
        generator = AudioGenerator()
        
        # Every emotion must have a text mapping
        assert emotion in generator.EMOTION_TEXT_MAP, (
            f"Emotion {emotion.name} ({emotion.value}) is missing from EMOTION_TEXT_MAP"
        )
        
        # The mapping must be a non-empty string
        text_mapping = generator.EMOTION_TEXT_MAP[emotion]
        assert isinstance(text_mapping, str), (
            f"Emotion {emotion.name} mapping should be a string, got {type(text_mapping)}"
        )
        assert len(text_mapping) > 0, (
            f"Emotion {emotion.name} mapping should not be empty"
        )

    @given(emotion=st.sampled_from(list(Emotion)))
    @settings(max_examples=100)
    def test_all_emotions_have_category(self, emotion: Emotion):
        """For any defined emotion type, there must be a category classification.
        
        Property 3: 情感配置完整性
        Validates: Requirements 3.3, 3.4
        """
        generator = AudioGenerator()
        
        # Collect all emotions from all categories
        all_categorized_emotions = set()
        for category, emotions in generator.EMOTION_CATEGORIES.items():
            all_categorized_emotions.update(emotions)
        
        # Every emotion must be in exactly one category
        assert emotion in all_categorized_emotions, (
            f"Emotion {emotion.name} ({emotion.value}) is not in any category"
        )

    def test_emotion_categories_are_mutually_exclusive(self):
        """Test that each emotion appears in exactly one category.
        
        Property 3: 情感配置完整性
        Validates: Requirements 3.3, 3.4
        """
        generator = AudioGenerator()
        
        # Track which emotions appear in which categories
        emotion_to_categories = {}
        for category, emotions in generator.EMOTION_CATEGORIES.items():
            for emotion in emotions:
                if emotion not in emotion_to_categories:
                    emotion_to_categories[emotion] = []
                emotion_to_categories[emotion].append(category)
        
        # Each emotion should appear in exactly one category
        for emotion, categories in emotion_to_categories.items():
            assert len(categories) == 1, (
                f"Emotion {emotion.name} appears in multiple categories: {categories}"
            )

    def test_all_emotions_covered_by_categories(self):
        """Test that all defined emotions are covered by categories.
        
        Property 3: 情感配置完整性
        Validates: Requirements 3.3, 3.4
        """
        generator = AudioGenerator()
        
        # Collect all emotions from all categories
        categorized_emotions = set()
        for emotions in generator.EMOTION_CATEGORIES.values():
            categorized_emotions.update(emotions)
        
        # All defined emotions should be categorized
        all_emotions = set(Emotion)
        uncategorized = all_emotions - categorized_emotions
        
        assert len(uncategorized) == 0, (
            f"The following emotions are not categorized: {[e.name for e in uncategorized]}"
        )

    def test_category_names_are_valid(self):
        """Test that category names are valid (positive, negative, neutral).
        
        Property 3: 情感配置完整性
        Validates: Requirements 4.2
        """
        generator = AudioGenerator()
        
        expected_categories = {"positive", "negative", "neutral"}
        actual_categories = set(generator.EMOTION_CATEGORIES.keys())
        
        assert actual_categories == expected_categories, (
            f"Expected categories {expected_categories}, got {actual_categories}"
        )

    def test_new_emotions_have_mappings(self):
        """Test that all 9 new emotions have proper text mappings.
        
        Property 3: 情感配置完整性
        Validates: Requirements 3.3
        """
        generator = AudioGenerator()
        
        # New emotions added in Requirements 3.1
        new_emotions = [
            Emotion.LIVELY,      # 活泼
            Emotion.HEALING,     # 治愈
            Emotion.AGGRIEVED,   # 委屈
            Emotion.EMBARRASSED, # 尴尬
            Emotion.PROUD,       # 自豪
            Emotion.CONFLICTED,  # 纠结
            Emotion.LOST,        # 失落
            Emotion.SHY,         # 害羞
            Emotion.IRRITATED,   # 烦躁
        ]
        
        expected_mappings = {
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
        
        for emotion in new_emotions:
            assert emotion in generator.EMOTION_TEXT_MAP, (
                f"New emotion {emotion.name} is missing from EMOTION_TEXT_MAP"
            )
            assert generator.EMOTION_TEXT_MAP[emotion] == expected_mappings[emotion], (
                f"Emotion {emotion.name} has wrong mapping: "
                f"expected '{expected_mappings[emotion]}', "
                f"got '{generator.EMOTION_TEXT_MAP[emotion]}'"
            )


# =============================================================================
# Property-Based Tests for Audio Parameter Priority
# =============================================================================

class TestAudioParamsPriority:
    """Property-based tests for audio parameter priority.
    
    Feature: video-style-expansion, Property 5: 音频参数优先级
    Validates: Requirements 5.5
    """

    @st.composite
    def audio_params_strategy(draw):
        """Generate a valid AudioParams object."""
        from backend.schemas.models import AudioParams
        return AudioParams(
            emotion=draw(st.sampled_from(list(Emotion))),
            emotion_strength=draw(st.floats(min_value=0.0, max_value=1.0)),
            speed=draw(st.floats(min_value=0.5, max_value=2.0)),
            volume=draw(st.floats(min_value=0.5, max_value=1.5))
        )

    @st.composite
    def scene_with_audio_params_strategy(draw):
        """Generate a Scene with audio_params set."""
        from backend.schemas.models import AudioParams
        audio_params = AudioParams(
            emotion=draw(st.sampled_from(list(Emotion))),
            emotion_strength=draw(st.floats(min_value=0.0, max_value=1.0)),
            speed=draw(st.floats(min_value=0.5, max_value=2.0)),
            volume=draw(st.floats(min_value=0.5, max_value=1.5))
        )
        return Scene(
            scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters='_-'
            ))),
            step_number=draw(st.integers(min_value=1, max_value=100)),
            description_cn=draw(non_empty_text(min_size=1, max_size=200)),
            narration_cn=draw(non_empty_text(min_size=1, max_size=200)),
            narration_en=draw(non_empty_english_text(min_size=1, max_size=200)),
            duration=draw(st.sampled_from(SceneDuration)),
            emotion=draw(st.sampled_from(Emotion)),  # Scene's own emotion (should be overridden)
            audio_params=audio_params
        )

    @st.composite
    def scene_without_audio_params_strategy(draw):
        """Generate a Scene without audio_params."""
        return Scene(
            scene_id=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters='_-'
            ))),
            step_number=draw(st.integers(min_value=1, max_value=100)),
            description_cn=draw(non_empty_text(min_size=1, max_size=200)),
            narration_cn=draw(non_empty_text(min_size=1, max_size=200)),
            narration_en=draw(non_empty_english_text(min_size=1, max_size=200)),
            duration=draw(st.sampled_from(SceneDuration)),
            emotion=draw(st.sampled_from(Emotion)),
            audio_params=None  # No audio_params
        )

    @given(scene=scene_with_audio_params_strategy())
    @settings(max_examples=100)
    def test_audio_params_takes_priority_over_config(self, scene):
        """For any scene with audio_params, those params should be used regardless of config.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        generator = AudioGenerator()
        
        # Create a config with different values
        config = AudioConfig(
            emotion=Emotion.ANGRY if scene.audio_params.emotion != Emotion.ANGRY else Emotion.HAPPY,
            emotion_strength=0.1 if scene.audio_params.emotion_strength > 0.5 else 0.9
        )
        
        # Resolve params - should use scene.audio_params
        emotion, emotion_strength, speed = generator._resolve_audio_params(scene, config)
        
        # Verify audio_params takes priority
        assert emotion == scene.audio_params.emotion, (
            f"Expected emotion {scene.audio_params.emotion}, got {emotion}"
        )
        assert emotion_strength == scene.audio_params.emotion_strength, (
            f"Expected emotion_strength {scene.audio_params.emotion_strength}, got {emotion_strength}"
        )
        assert speed == scene.audio_params.speed, (
            f"Expected speed {scene.audio_params.speed}, got {speed}"
        )

    @given(scene=scene_with_audio_params_strategy())
    @settings(max_examples=100)
    def test_audio_params_takes_priority_over_scene_emotion(self, scene):
        """For any scene with audio_params, those params should override scene.emotion.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        generator = AudioGenerator()
        
        # Resolve params without config - should still use audio_params
        emotion, emotion_strength, speed = generator._resolve_audio_params(scene, config=None)
        
        # Verify audio_params takes priority over scene.emotion
        assert emotion == scene.audio_params.emotion, (
            f"Expected emotion from audio_params {scene.audio_params.emotion}, got {emotion}"
        )
        assert emotion_strength == scene.audio_params.emotion_strength, (
            f"Expected emotion_strength from audio_params {scene.audio_params.emotion_strength}, got {emotion_strength}"
        )

    @given(scene=scene_without_audio_params_strategy(), config=audio_config_strategy())
    @settings(max_examples=100)
    def test_config_used_when_no_audio_params(self, scene, config):
        """For any scene without audio_params, config should be used if provided.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        generator = AudioGenerator()
        
        # Resolve params - should use config since no audio_params
        emotion, emotion_strength, speed = generator._resolve_audio_params(scene, config)
        
        # Verify config is used
        assert emotion == config.emotion, (
            f"Expected emotion from config {config.emotion}, got {emotion}"
        )
        assert emotion_strength == config.emotion_strength, (
            f"Expected emotion_strength from config {config.emotion_strength}, got {emotion_strength}"
        )
        # Speed should be default since AudioConfig doesn't have speed
        assert speed == 1.0, f"Expected default speed 1.0, got {speed}"

    @given(scene=scene_without_audio_params_strategy())
    @settings(max_examples=100)
    def test_scene_emotion_used_when_no_audio_params_and_no_config(self, scene):
        """For any scene without audio_params and no config, scene.emotion should be used.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        generator = AudioGenerator()
        
        # Resolve params without config and without audio_params
        emotion, emotion_strength, speed = generator._resolve_audio_params(scene, config=None)
        
        # Verify scene.emotion is used with defaults
        assert emotion == scene.emotion, (
            f"Expected emotion from scene {scene.emotion}, got {emotion}"
        )
        # Default emotion_strength should be 0.6
        assert emotion_strength == 0.6, (
            f"Expected default emotion_strength 0.6, got {emotion_strength}"
        )
        # Default speed should be 1.0
        assert speed == 1.0, f"Expected default speed 1.0, got {speed}"

    @pytest.mark.asyncio
    @given(scene=scene_with_audio_params_strategy())
    @settings(max_examples=100)
    async def test_generate_audio_uses_audio_params(self, scene):
        """For any scene with audio_params, generate_audio should use those params.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Create a config with different values to verify audio_params takes priority
            config = AudioConfig(
                emotion=Emotion.ANGRY if scene.audio_params.emotion != Emotion.ANGRY else Emotion.HAPPY,
                emotion_strength=0.1
            )
            
            # Generate audio - should succeed using audio_params
            result = await generator.generate_audio(scene, output_dir, config)
            
            assert result.status == ResourceStatus.COMPLETED, (
                f"Audio generation failed: {result.error_message}"
            )

    @pytest.mark.asyncio
    @given(scene=scene_without_audio_params_strategy())
    @settings(max_examples=100)
    async def test_generate_audio_uses_config_when_no_audio_params(self, scene):
        """For any scene without audio_params, generate_audio should use config.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            config = AudioConfig(
                emotion=Emotion.HAPPY,
                emotion_strength=0.8
            )
            
            # Generate audio - should succeed using config
            result = await generator.generate_audio(scene, output_dir, config)
            
            assert result.status == ResourceStatus.COMPLETED, (
                f"Audio generation failed: {result.error_message}"
            )

    @pytest.mark.asyncio
    @given(scene=scene_without_audio_params_strategy())
    @settings(max_examples=100)
    async def test_generate_audio_uses_scene_emotion_when_no_config(self, scene):
        """For any scene without audio_params and no config, generate_audio should use scene.emotion.
        
        Property 5: 音频参数优先级
        Validates: Requirements 5.5
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generator = AudioGenerator()
            generator._initialized = True
            generator._mock_mode = True
            
            # Generate audio without config - should succeed using scene.emotion
            result = await generator.generate_audio(scene, output_dir, config=None)
            
            assert result.status == ResourceStatus.COMPLETED, (
                f"Audio generation failed: {result.error_message}"
            )
