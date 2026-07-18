"""TTS API module for IndexTTS2 testing.

This module provides REST API endpoints for testing IndexTTS2 voice synthesis.
"""

import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.config import get_settings
from backend.db.models import get_db, VoiceRecord
from backend.services import cos_client


router = APIRouter(prefix="/tts", tags=["TTS"])


# Request/Response models
class TTSRequest(BaseModel):
    """TTS generation request."""
    text: str = Field(..., description="Text to synthesize")
    voice: str = Field(default="jack_cheng", description="Voice ID")
    emotion: Optional[str] = Field(default="calm", description="Emotion type")
    emotion_strength: Optional[float] = Field(default=0.6, ge=0.0, le=1.0, description="Emotion weight (emo_weight)")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed, range 0.25-4")
    gain: Optional[float] = Field(default=1.0, ge=0.1, le=10.0, description="Volume gain, range 0.1-10")
    sample_rate: Optional[int] = Field(default=22050, description="Sample rate: 16000, 22050, 24000")
    response_format: Optional[str] = Field(default="mp3")
    seed: Optional[int] = Field(default=-1)
    interval_silence: Optional[int] = Field(default=200, ge=0, le=2000, description="Silence between sentences in ms")
    max_text_tokens_per_sentence: Optional[int] = Field(default=120, ge=50, le=500, description="Max tokens per sentence")
    emo_random: Optional[bool] = Field(default=False, description="Enable emotion randomness")


class VoiceInfo(BaseModel):
    """Voice information."""
    id: str
    name: str
    preview_url: Optional[str] = None


class VoiceListResponse(BaseModel):
    """Voice list response."""
    list: list[VoiceInfo]


class UploadVoiceResponse(BaseModel):
    """Upload voice response."""
    id: str
    name: str


# Temporary directory for generated audio
_temp_dir = Path(tempfile.mkdtemp(prefix="tts_api_"))


@router.post("/generate")
async def generate_tts(
    request: TTSRequest,
    current_user: str = Depends(get_current_user),
) -> FileResponse:
    """Generate TTS audio.
    
    Args:
        request: TTS generation parameters.
        current_user: Authenticated user.
        
    Returns:
        Generated audio file.
    """
    settings = get_settings()
    
    if not settings.indextts or not settings.indextts.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TTS_NOT_CONFIGURED", "message": "IndexTTS API key not configured"}
        )
    
    # Map emotion to Chinese text for emo_text
    emotion_text_map = {
        "calm": "平静", "happy": "高兴", "angry": "生气",
        "sad": "悲伤", "surprised": "惊喜", "disgust": "厌恶", "fear": "恐惧",
    }
    emo_text = emotion_text_map.get(request.emotion or "calm", "平静")
    
    try:
        async with httpx.AsyncClient(
            base_url=settings.indextts.base_url,
            headers={"Authorization": f"Bearer {settings.indextts.api_key}"},
            timeout=httpx.Timeout(120.0)
        ) as client:
            payload = {
                "model": settings.indextts.model,
                "input": request.text.strip(),
                "voice": request.voice,
                "response_format": request.response_format or "mp3",
            }
            
            # Speed (0.25-4)
            if request.speed and request.speed != 1.0:
                payload["speed"] = request.speed
            
            # Gain (volume, 0.1-10)
            if request.gain and request.gain != 1.0:
                payload["gain"] = request.gain
            
            # Sample rate
            if request.sample_rate:
                payload["sample_rate"] = request.sample_rate
            
            # Emotion control using text method (emo_control_method=3)
            if emo_text != "平静" or (request.emotion_strength and request.emotion_strength > 0):
                payload["emo_control_method"] = 3
                payload["emo_text"] = emo_text
                payload["emo_weight"] = request.emotion_strength or 0.6
            
            # Emotion randomness
            if request.emo_random:
                payload["emo_random"] = True
            
            # Sentence control
            if request.interval_silence and request.interval_silence != 200:
                payload["interval_silence"] = request.interval_silence
            if request.max_text_tokens_per_sentence and request.max_text_tokens_per_sentence != 120:
                payload["max_text_tokens_per_sentence"] = request.max_text_tokens_per_sentence
            
            # Seed
            if request.seed and request.seed != -1:
                payload["seed"] = request.seed
            
            response = await client.post("/v1/audio/speech", json=payload)
            
            if response.status_code == 200:
                ext = request.response_format if request.response_format in ["mp3", "wav", "flac", "opus"] else "mp3"
                audio_path = _temp_dir / f"tts_{int(time.time() * 1000)}.{ext}"
                audio_path.write_bytes(response.content)
                
                media_type_map = {
                    "mp3": "audio/mpeg",
                    "wav": "audio/wav",
                    "flac": "audio/flac",
                    "opus": "audio/opus",
                }
                
                return FileResponse(
                    path=str(audio_path),
                    media_type=media_type_map.get(ext, "audio/mpeg"),
                    filename=f"tts_output.{ext}"
                )
            else:
                error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "TTS_GENERATION_FAILED", "message": f"TTS generation failed: {error_msg}"}
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "TTS_TIMEOUT", "message": "TTS generation timed out"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TTS_ERROR", "message": str(e)}
        )


@router.get("/voices", response_model=VoiceListResponse)
async def get_voices(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceListResponse:
    """Get available voices (only current user's custom voices).
    
    Args:
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        List of available voices for current user.
    """
    settings = get_settings()
    
    if not settings.indextts or not settings.indextts.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TTS_NOT_CONFIGURED", "message": "IndexTTS API key not configured"}
        )
    
    # Get local voice records from database (only current user's voices)
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
                        id=voice_id,
                        name=name,
                        preview_url=preview_url
                    ))
                return VoiceListResponse(list=voices)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "VOICE_LIST_FAILED", "message": f"Failed to get voice list: {response.status_code}"}
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "VOICE_LIST_ERROR", "message": str(e)}
        )


@router.get("/voices/{voice_id}/preview")
async def get_voice_preview(
    voice_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Get voice preview audio (proxy from COS).
    
    Args:
        voice_id: The voice ID.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Audio file response.
    """
    # Find voice record (only current user's voice)
    record = db.query(VoiceRecord).filter(
        VoiceRecord.voice_id == voice_id,
        VoiceRecord.user_id == current_user
    ).first()
    
    if not record or not record.cos_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREVIEW_NOT_FOUND", "message": "预览音频不存在"}
        )
    
    try:
        # Fetch from COS
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(record.cos_url)
            
            if response.status_code == 200:
                # Save to temp file and return
                ext = Path(record.cos_key).suffix if record.cos_key else ".mp3"
                audio_path = _temp_dir / f"preview_{voice_id}{ext}"
                audio_path.write_bytes(response.content)
                
                content_type = "audio/mpeg"
                if ext == ".wav":
                    content_type = "audio/wav"
                elif ext == ".flac":
                    content_type = "audio/flac"
                
                return FileResponse(
                    path=str(audio_path),
                    media_type=content_type,
                    filename=f"preview{ext}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "PREVIEW_NOT_FOUND", "message": "预览音频获取失败"}
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PREVIEW_ERROR", "message": str(e)}
        )


@router.post("/voices/upload", response_model=UploadVoiceResponse)
async def upload_voice(
    file: UploadFile = File(...),
    name: str = Form(...),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadVoiceResponse:
    """Upload custom voice.
    
    Args:
        file: Audio file (WAV/MP3, 5-30 seconds).
        name: Voice name.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Uploaded voice info.
    """
    settings = get_settings()
    
    if not settings.indextts or not settings.indextts.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TTS_NOT_CONFIGURED", "message": "IndexTTS API key not configured"}
        )
    
    # Validate file type
    if file.content_type not in ["audio/wav", "audio/mpeg", "audio/mp3"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FILE_TYPE", "message": "Only WAV/MP3 files are supported"}
        )
    
    try:
        audio_data = await file.read()
        file_size = len(audio_data)
        
        # 1. Upload to IndexTTS API
        async with httpx.AsyncClient(
            base_url=settings.indextts.base_url,
            headers={"Authorization": f"Bearer {settings.indextts.api_key}"},
            timeout=httpx.Timeout(60.0)
        ) as client:
            files = {"speaker_file": (file.filename, audio_data, file.content_type)}
            data = {"name": name, "model": settings.indextts.model}
            
            response = await client.post("/v1/audio/voice/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                voice_id = result.get("id", "")
                if not voice_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail={"code": "UPLOAD_FAILED", "message": "No voice ID returned"}
                    )
                
                # 2. Upload to COS
                cos_result = cos_client.upload_file(
                    file_data=audio_data,
                    filename=file.filename or "voice.mp3",
                    folder="voices",
                    content_type=file.content_type or "audio/mpeg"
                )
                
                # 3. Save to database
                try:
                    voice_record = VoiceRecord(
                        voice_id=voice_id,
                        name=name,
                        user_id=current_user,
                        cos_url=cos_result.get("cos_url") if cos_result else None,
                        cos_key=cos_result.get("cos_key") if cos_result else None,
                        original_filename=file.filename,
                        file_size=file_size,
                    )
                    db.add(voice_record)
                    db.commit()
                except Exception as e:
                    print(f"Database save warning: {e}")
                    db.rollback()
                
                return UploadVoiceResponse(id=voice_id, name=name)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "UPLOAD_FAILED", "message": f"Upload failed: {response.text[:200]}"}
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "UPLOAD_ERROR", "message": str(e)}
        )


class DeleteVoiceResponse(BaseModel):
    """Delete voice response."""
    success: bool
    message: str


@router.delete("/voices/{voice_id}", response_model=DeleteVoiceResponse)
async def delete_voice(
    voice_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteVoiceResponse:
    """Delete a custom voice.
    
    Args:
        voice_id: The voice ID to delete.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Delete result.
    """
    settings = get_settings()
    
    if not settings.indextts or not settings.indextts.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TTS_NOT_CONFIGURED", "message": "IndexTTS API key not configured"}
        )
    
    try:
        # 1. Delete from IndexTTS API
        async with httpx.AsyncClient(
            base_url=settings.indextts.base_url,
            headers={"Authorization": f"Bearer {settings.indextts.api_key}"},
            timeout=httpx.Timeout(30.0)
        ) as client:
            # API uses POST /v1/audio/voice/delete with JSON body
            response = await client.post(
                "/v1/audio/voice/delete",
                json={"id": voice_id}
            )
            
            if response.status_code == 200:
                # 2. Delete from COS and database
                try:
                    record = db.query(VoiceRecord).filter(
                        VoiceRecord.voice_id == voice_id,
                        VoiceRecord.user_id == current_user
                    ).first()
                    if record:
                        # Delete from COS
                        if record.cos_key:
                            cos_client.delete_file(record.cos_key)
                        # Delete from database
                        db.delete(record)
                        db.commit()
                except Exception as e:
                    print(f"Database/COS cleanup warning: {e}")
                    db.rollback()
                
                return DeleteVoiceResponse(success=True, message="音色删除成功")
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "VOICE_NOT_FOUND", "message": "音色不存在"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "DELETE_FAILED", "message": f"删除失败: {response.text[:200]}"}
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DELETE_ERROR", "message": str(e)}
        )
