"""Audio generation and voice management API module.

This module provides REST API endpoints for voice listing, audio generation,
and audio file retrieval.

Requirements: 3.4
"""

import io
import json
import wave
from typing import Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.services.tasks import Task, create_task, schedule_task
from backend.config import get_settings
from backend.db.models import get_db, SceneRecord
from backend.db.crud.projects import (
    get_project, get_project_scenes, update_project_status,
    update_scene_audio_cn, update_scene_audio_en
)
from backend.services import cos_client


# Router for voice endpoints
router = APIRouter()

# Router for project audio endpoints (mounted under /api/projects)
project_audio_router = APIRouter()


async def merge_audio_files(audio_urls: list[str], silence_gap: float = 0.3) -> Tuple[Optional[bytes], float]:
    """Merge multiple audio files from URLs into one.
    
    Args:
        audio_urls: List of audio file URLs to merge.
        silence_gap: Silence gap between audio files in seconds.
        
    Returns:
        Tuple of (merged audio bytes, total duration in seconds).
    """
    if not audio_urls:
        return None, 0.0
    
    all_frames = []
    sample_rate = None
    sample_width = None
    channels = None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, url in enumerate(audio_urls):
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    print(f"Failed to download audio from {url}: {response.status_code}")
                    continue
                
                audio_data = response.content
                
                # Parse WAV data
                with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                    if sample_rate is None:
                        sample_rate = wav_file.getframerate()
                        sample_width = wav_file.getsampwidth()
                        channels = wav_file.getnchannels()
                    
                    frames = wav_file.readframes(wav_file.getnframes())
                    all_frames.append(frames)
                    
                    # Add silence gap (except after last file)
                    if i < len(audio_urls) - 1 and silence_gap > 0:
                        silence_samples = int(sample_rate * silence_gap)
                        silence_frames = b'\x00' * (silence_samples * sample_width * channels)
                        all_frames.append(silence_frames)
                        
            except Exception as e:
                print(f"Error processing audio from {url}: {e}")
                continue
    
    if not all_frames or sample_rate is None:
        return None, 0.0
    
    # Write merged audio
    output_buffer = io.BytesIO()
    with wave.open(output_buffer, 'wb') as out_wav:
        out_wav.setnchannels(channels)
        out_wav.setsampwidth(sample_width)
        out_wav.setframerate(sample_rate)
        
        for frames in all_frames:
            out_wav.writeframes(frames)
    
    merged_data = output_buffer.getvalue()
    
    # Calculate total duration
    with wave.open(io.BytesIO(merged_data), 'rb') as wav_file:
        total_frames = wav_file.getnframes()
        total_duration = total_frames / float(wav_file.getframerate())
    
    return merged_data, total_duration


# Request/Response models
class VoiceInfo(BaseModel):
    """Voice information model."""
    voice_id: str
    name: str
    preview_url: Optional[str] = None


class VoicesListResponse(BaseModel):
    """Response model for voices list."""
    voices: list[VoiceInfo]


class GenerateAudioRequest(BaseModel):
    """Request model for audio generation."""
    voice_id: Optional[str] = Field(
        default=None,
        description="Voice ID to use for generation"
    )


class GenerateAudioResponse(BaseModel):
    """Response model for audio generation."""
    task_id: str


class SceneAudioResponse(BaseModel):
    """Response model for scene audio."""
    scene_id: str
    audio_cn_url: Optional[str] = None
    audio_en_url: Optional[str] = None
    duration_cn: Optional[float] = None
    duration_en: Optional[float] = None


class FullAudioResponse(BaseModel):
    """Response model for full project audio."""
    full_cn_url: Optional[str] = None
    full_en_url: Optional[str] = None


# API Endpoints - Voices
@router.get("", response_model=VoicesListResponse)
async def get_voices(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoicesListResponse:
    """Get list of available voices from IndexTTS API."""
    import httpx
    from backend.db.models import VoiceRecord
    
    settings = get_settings()
    
    if not settings.indextts or not settings.indextts.api_key:
        return VoicesListResponse(voices=[])
    
    # Get local voice records from database (only current user's custom voices)
    local_voices: dict[str, VoiceRecord] = {}
    try:
        records = db.query(VoiceRecord).filter(VoiceRecord.user_id == current_user).all()
        for r in records:
            local_voices[r.voice_id] = r
    except Exception as e:
        print(f"Database query warning: {e}")
    
    try:
        async with httpx.AsyncClient(
            base_url=settings.indextts.base_url,
            headers={"Authorization": f"Bearer {settings.indextts.api_key}"},
            timeout=httpx.Timeout(30.0)
        ) as client:
            response = await client.get("/v1/audio/voice/list")
            
            if response.status_code == 200:
                data = response.json()
                voices = []
                for v in data.get("list", []):
                    voice_id = v.get("id", "")
                    
                    # Only show voices that belong to current user
                    if voice_id not in local_voices:
                        continue
                    
                    local_record = local_voices[voice_id]
                    name = local_record.name or v.get("name", voice_id)
                    # Use direct COS URL (ensure COS bucket has CORS configured)
                    preview_url = local_record.cos_url or v.get("preview_url") or v.get("audio_url")
                    
                    voices.append(VoiceInfo(
                        voice_id=voice_id,
                        name=name,
                        preview_url=preview_url
                    ))
                return VoicesListResponse(voices=voices)
            else:
                print(f"IndexTTS API error: {response.status_code}")
                return VoicesListResponse(voices=[])
    except Exception as e:
        print(f"Failed to fetch voices from IndexTTS: {e}")
        return VoicesListResponse(voices=[])


# API Endpoints - Project Audio
@project_audio_router.post("/{project_id}/audio/generate", response_model=GenerateAudioResponse)
async def generate_audio(
    project_id: str,
    request: GenerateAudioRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerateAudioResponse:
    """Generate audio for all scenes in a project."""
    from backend.db.crud.projects import get_project_active_task, set_project_active_task, clear_project_active_task
    from backend.services.tasks import get_task, TaskStatus
    
    # Verify project exists
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"},
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权操作此项目"},
        )
    
    # 检查是否有正在进行的任务
    active_task = get_project_active_task(db, project_id)
    if active_task:
        existing_task = get_task(active_task["task_id"])
        if existing_task and existing_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TASK_IN_PROGRESS",
                    "message": f"项目有正在进行的{active_task['task_type']}任务",
                    "task_id": active_task["task_id"],
                    "task_type": active_task["task_type"]
                },
            )
        else:
            clear_project_active_task(db, project_id)
    
    # Verify scenes exist
    scenes = get_project_scenes(db, project_id)
    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "请先生成分镜"},
        )
    
    # Create task
    task = create_task("audio")
    
    # 记录活跃任务
    set_project_active_task(db, project_id, task.task_id, "audio")
    
    # Define the async generation function
    async def run_generation():
        from backend.db.models import get_session_local
        from backend.core.generators.audio import AudioGenerator
        from backend.schemas.models import Scene as SceneModel, SceneDuration, Emotion, AudioConfig
        from backend.db.crud.projects import clear_project_active_task
        import tempfile
        from pathlib import Path
        import json
        
        settings = get_settings()
        
        SessionLocal = get_session_local()
        task_db = SessionLocal()
        
        try:
            task.update_progress(message="正在生成音频...", current=0, total=1)
            
            # Get scenes
            scene_records = get_project_scenes(task_db, project_id)
            total = len(scene_records)
            
            # Initialize audio generator
            audio_generator = AudioGenerator(
                api_key=settings.indextts.api_key if settings.indextts else ""
            )
            
            # Create temp dir for audio files
            temp_dir = Path(tempfile.mkdtemp())
            
            # Create audio config with voice reference
            audio_config = None
            if request.voice_id:
                audio_config = AudioConfig(
                    voice_reference_path=request.voice_id
                )
            
            for i, scene_record in enumerate(scene_records):
                task.update_progress(
                    message=f"正在生成第 {i+1}/{total} 个音频...",
                    current=i,
                    total=total
                )
                
                print(f"Processing scene {scene_record.scene_id} ({i+1}/{total})")
                print(f"  - narration_cn: {scene_record.narration_cn[:50] if scene_record.narration_cn else 'None'}...")
                print(f"  - narration_en: {scene_record.narration_en[:50] if scene_record.narration_en else 'None'}...")
                
                try:
                    # Convert DB record to Scene model
                    char_ids = []
                    if scene_record.character_ids:
                        try:
                            char_ids = json.loads(scene_record.character_ids)
                        except:
                            pass
                    
                    # Parse audio_params to get emotion, fallback to CALM
                    scene_emotion = Emotion.CALM
                    if scene_record.audio_params:
                        try:
                            audio_params_dict = json.loads(scene_record.audio_params)
                            emotion_str = audio_params_dict.get("emotion", "calm")
                            # Map emotion string to Emotion enum
                            emotion_map = {
                                "happy": Emotion.HAPPY,
                                "angry": Emotion.ANGRY,
                                "sad": Emotion.SAD,
                                "fear": Emotion.FEAR,
                                "disgust": Emotion.DISGUST,
                                "depressed": Emotion.DEPRESSED,
                                "surprised": Emotion.SURPRISED,
                                "calm": Emotion.CALM,
                                "lively": Emotion.LIVELY,
                                "healing": Emotion.HEALING,
                                "aggrieved": Emotion.AGGRIEVED,
                                "embarrassed": Emotion.EMBARRASSED,
                                "proud": Emotion.PROUD,
                                "conflicted": Emotion.CONFLICTED,
                                "lost": Emotion.LOST,
                                "shy": Emotion.SHY,
                                "irritated": Emotion.IRRITATED,
                            }
                            scene_emotion = emotion_map.get(emotion_str, Emotion.CALM)
                        except (json.JSONDecodeError, KeyError):
                            scene_emotion = Emotion.CALM
                    
                    # Parse audio_params
                    audio_params = None
                    if scene_record.audio_params:
                        try:
                            audio_params_dict = json.loads(scene_record.audio_params)
                            from backend.schemas.models import AudioParams
                            
                            # 将字符串 emotion 转换为 Emotion 枚举
                            emotion_str = audio_params_dict.get("emotion", "calm")
                            emotion_map = {
                                "happy": Emotion.HAPPY, "喜": Emotion.HAPPY,
                                "angry": Emotion.ANGRY, "怒": Emotion.ANGRY,
                                "sad": Emotion.SAD, "哀": Emotion.SAD,
                                "fear": Emotion.FEAR, "惧": Emotion.FEAR,
                                "disgust": Emotion.DISGUST, "厌恶": Emotion.DISGUST,
                                "depressed": Emotion.DEPRESSED, "低落": Emotion.DEPRESSED,
                                "surprised": Emotion.SURPRISED, "惊喜": Emotion.SURPRISED,
                                "calm": Emotion.CALM, "平静": Emotion.CALM,
                                "lively": Emotion.LIVELY, "活泼": Emotion.LIVELY,
                                "healing": Emotion.HEALING, "治愈": Emotion.HEALING,
                                "aggrieved": Emotion.AGGRIEVED, "委屈": Emotion.AGGRIEVED,
                                "embarrassed": Emotion.EMBARRASSED, "尴尬": Emotion.EMBARRASSED,
                                "proud": Emotion.PROUD, "自豪": Emotion.PROUD,
                                "conflicted": Emotion.CONFLICTED, "纠结": Emotion.CONFLICTED,
                                "lost": Emotion.LOST, "失落": Emotion.LOST,
                                "shy": Emotion.SHY, "害羞": Emotion.SHY,
                                "irritated": Emotion.IRRITATED, "烦躁": Emotion.IRRITATED,
                            }
                            emotion_enum = emotion_map.get(emotion_str, Emotion.CALM)
                            
                            audio_params = AudioParams(
                                emotion=emotion_enum,
                                emotion_strength=audio_params_dict.get("emotion_strength", 0.6),
                                speed=audio_params_dict.get("speed", 1.0),
                                volume=audio_params_dict.get("volume", 1.0)
                            )
                            print(f"[Audio] Scene {scene_record.scene_id} audio_params: emotion={emotion_enum.value}, strength={audio_params.emotion_strength}, speed={audio_params.speed}")
                        except (json.JSONDecodeError, TypeError, ValueError) as e:
                            print(f"[Audio] Failed to parse audio_params for scene {scene_record.scene_id}: {e}")
                            audio_params = None
                    
                    scene_model = SceneModel(
                        scene_id=scene_record.scene_id,
                        step_number=scene_record.step_number,
                        description_cn=scene_record.description_cn or "",
                        image_prompt=scene_record.image_prompt or scene_record.description_cn or "",
                        video_prompt=scene_record.video_prompt or "",
                        narration_cn=scene_record.narration_cn or "",
                        narration_en=scene_record.narration_en or "",
                        duration=SceneDuration(scene_record.duration) if scene_record.duration in [5,8,10,12,15] else SceneDuration.MEDIUM,
                        character_ids=char_ids,
                        audio_params=audio_params
                    )
                    
                    # Debug: 确认 scene_model 中的 audio_params
                    if scene_model.audio_params:
                        print(f"[Audio] scene_model.audio_params: emotion={scene_model.audio_params.emotion}, type={type(scene_model.audio_params.emotion)}")
                    else:
                        print(f"[Audio] scene_model.audio_params is None!")
                    
                    # Generate audio using AudioGenerator
                    scene_audio = await audio_generator.generate_audio(
                        scene=scene_model,
                        output_dir=temp_dir,
                        config=audio_config
                    )
                    
                    # Upload Chinese audio to COS
                    if scene_audio.audio_path:
                        audio_path_cn = Path(scene_audio.audio_path)
                        if audio_path_cn.exists():
                            audio_data_cn = audio_path_cn.read_bytes()
                            
                            cos_result = cos_client.upload_file(
                                file_data=audio_data_cn,
                                filename=f"{scene_record.scene_id}_cn.wav",
                                folder=f"projects/{project_id}/audios",
                                content_type="audio/wav"
                            )
                            
                            if cos_result:
                                duration_ms = int(scene_audio.duration_seconds * 1000)
                                update_scene_audio_cn(
                                    task_db,
                                    scene_record.scene_id,
                                    status="completed",
                                    cos_url=cos_result["cos_url"],
                                    cos_key=cos_result["cos_key"],
                                    duration_ms=duration_ms
                                )
                    
                    # Upload English audio to COS
                    if scene_audio.audio_path_en:
                        audio_path_en = Path(scene_audio.audio_path_en)
                        if audio_path_en.exists():
                            audio_data_en = audio_path_en.read_bytes()
                            
                            cos_result = cos_client.upload_file(
                                file_data=audio_data_en,
                                filename=f"{scene_record.scene_id}_en.wav",
                                folder=f"projects/{project_id}/audios",
                                content_type="audio/wav"
                            )
                            
                            if cos_result:
                                duration_ms = int(scene_audio.duration_seconds_en * 1000)
                                update_scene_audio_en(
                                    task_db,
                                    scene_record.scene_id,
                                    status="completed",
                                    cos_url=cos_result["cos_url"],
                                    cos_key=cos_result["cos_key"],
                                    duration_ms=duration_ms
                                )
                            
                except Exception as e:
                    import traceback
                    error_msg = f"Audio generation error for scene {scene_record.scene_id}: {e}"
                    print(error_msg)
                    print(traceback.format_exc())
                    update_scene_audio_cn(task_db, scene_record.scene_id, status="failed")
                    update_scene_audio_en(task_db, scene_record.scene_id, status="failed")
            
            # Close audio generator
            try:
                await audio_generator.close()
            except Exception as e:
                print(f"Error closing audio generator: {e}")
            
            # Merge all scene audios into full audio
            task.update_progress(message="正在合并完整音频...", current=total, total=total + 1)
            
            try:
                from backend.db.crud.projects import update_project_full_audio
                
                # Get all scene audio paths
                scene_records_updated = get_project_scenes(task_db, project_id)
                cn_audio_paths = []
                en_audio_paths = []
                
                for sr in scene_records_updated:
                    if sr.audio_cn_cos_url:
                        cn_audio_paths.append(sr.audio_cn_cos_url)
                    if sr.audio_en_cos_url:
                        en_audio_paths.append(sr.audio_en_cos_url)
                
                # Merge CN audios
                if cn_audio_paths:
                    full_cn_data, full_cn_duration = await merge_audio_files(cn_audio_paths)
                    if full_cn_data:
                        cos_result = cos_client.upload_file(
                            file_data=full_cn_data,
                            filename="full_cn.wav",
                            folder=f"projects/{project_id}/audios",
                            content_type="audio/wav"
                        )
                        if cos_result:
                            update_project_full_audio(
                                task_db,
                                project_id,
                                cn_cos_url=cos_result["cos_url"],
                                cn_cos_key=cos_result["cos_key"],
                                cn_duration_ms=int(full_cn_duration * 1000)
                            )
                
                # Merge EN audios
                if en_audio_paths:
                    full_en_data, full_en_duration = await merge_audio_files(en_audio_paths)
                    if full_en_data:
                        cos_result = cos_client.upload_file(
                            file_data=full_en_data,
                            filename="full_en.wav",
                            folder=f"projects/{project_id}/audios",
                            content_type="audio/wav"
                        )
                        if cos_result:
                            update_project_full_audio(
                                task_db,
                                project_id,
                                en_cos_url=cos_result["cos_url"],
                                en_cos_key=cos_result["cos_key"],
                                en_duration_ms=int(full_en_duration * 1000)
                            )
                
                print(f"Full audio merged successfully for project {project_id}")
            except Exception as e:
                print(f"Error merging full audio: {e}")
                import traceback
                print(traceback.format_exc())
            
            # Update project status
            update_project_status(task_db, project_id, "audio_ready")
            
            # 清除活跃任务
            clear_project_active_task(task_db, project_id)
            
            task.update_progress(message="音频生成完成", current=total + 1, total=total + 1)
            
            return {"project_id": project_id}
            
        except Exception as e:
            import traceback
            error_msg = f"Audio generation task failed: {e}"
            print(error_msg)
            print(traceback.format_exc())
            # 失败时也清除活跃任务
            try:
                clear_project_active_task(task_db, project_id)
            except:
                pass
            task.update_progress(message=f"生成失败: {str(e)}", current=0, total=1)
            raise
        finally:
            task_db.close()
    
    # Schedule the task
    schedule_task(task, run_generation())
    
    return GenerateAudioResponse(task_id=task.task_id)


@project_audio_router.get("/{project_id}/scenes/{scene_id}/audio", response_model=SceneAudioResponse)
async def get_scene_audio(
    project_id: str,
    scene_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SceneAudioResponse:
    """Get audio URLs for a specific scene."""
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"},
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权访问此项目"},
        )
    
    # Find scene
    scene = db.query(SceneRecord).filter(
        SceneRecord.scene_id == scene_id,
        SceneRecord.project_id == project_id
    ).first()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCENE_NOT_FOUND", "message": f"场景 {scene_id} 不存在"},
        )
    
    # Return direct COS URLs (ensure COS bucket has CORS configured)
    return SceneAudioResponse(
        scene_id=scene_id,
        audio_cn_url=scene.audio_cn_cos_url,
        audio_en_url=scene.audio_en_cos_url,
        duration_cn=scene.audio_cn_duration / 1000 if scene.audio_cn_duration else None,
        duration_en=scene.audio_en_duration / 1000 if scene.audio_en_duration else None,
    )


@project_audio_router.get("/{project_id}/audio/full", response_model=FullAudioResponse)
async def get_full_audio(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullAudioResponse:
    """Get full merged audio URLs for a project."""
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"},
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权访问此项目"},
        )
    
    # Return direct COS URLs (ensure COS bucket has CORS configured)
    return FullAudioResponse(
        full_cn_url=project.full_audio_cn_cos_url,
        full_en_url=project.full_audio_en_cos_url
    )


@project_audio_router.get("/{project_id}/audio/full/{lang}/stream")
async def stream_full_audio(
    project_id: str,
    lang: str,
    db: Session = Depends(get_db),
):
    """Stream full audio file (proxy to avoid CORS). No auth required for direct URL access."""
    from fastapi.responses import StreamingResponse
    
    if lang not in ("cn", "en"):
        raise HTTPException(status_code=400, detail="Invalid language")
    
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    cos_url = project.full_audio_cn_cos_url if lang == "cn" else project.full_audio_en_cos_url
    if not cos_url:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    async def stream_audio():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", cos_url) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk
    
    return StreamingResponse(stream_audio(), media_type="audio/wav")


@project_audio_router.get("/{project_id}/scenes/{scene_id}/audio/{lang}/stream")
async def stream_scene_audio(
    project_id: str,
    scene_id: str,
    lang: str,
    db: Session = Depends(get_db),
):
    """Stream scene audio file (proxy to avoid CORS). No auth required for direct URL access."""
    from fastapi.responses import StreamingResponse
    
    if lang not in ("cn", "en"):
        raise HTTPException(status_code=400, detail="Invalid language")
    
    scene = db.query(SceneRecord).filter(
        SceneRecord.scene_id == scene_id,
        SceneRecord.project_id == project_id
    ).first()
    
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    cos_url = scene.audio_cn_cos_url if lang == "cn" else scene.audio_en_cos_url
    if not cos_url:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    async def stream_audio():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", cos_url) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk
    
    return StreamingResponse(stream_audio(), media_type="audio/wav")
