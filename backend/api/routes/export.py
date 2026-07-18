"""Export API module.

This module provides REST API endpoints for exporting project assets.
Uses COS server-side copy and SCF for ZIP packaging.

Requirements: 3.5
"""

import json
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.services.tasks import Task, create_task, schedule_task
from backend.db.models import get_db, get_session_local, get_scf_config, get_cos_config
from backend.db.crud.projects import (
    get_project, get_project_scenes, update_project_export
)
from backend.services import cos_client


router = APIRouter()


class ExportResponse(BaseModel):
    """Response model for export initiation."""
    task_id: str


class ExportStatusResponse(BaseModel):
    """Response model for export status."""
    project_id: str
    has_export: bool
    download_url: Optional[str] = None
    file_count: Optional[int] = None
    zip_size: Optional[int] = None


@router.post("/{project_id}/export", response_model=ExportResponse)
async def export_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportResponse:
    """Export all assets for a project using COS server-side copy."""
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
    
    scenes = get_project_scenes(db, project_id)
    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "请先生成分镜"},
        )
    
    task = create_task("export")
    
    async def run_export():
        SessionLocal = get_session_local()
        task_db = SessionLocal()
        
        try:
            task.update_progress(message="正在准备导出...", current=0, total=100)
            
            proj = get_project(task_db, project_id)
            scene_records = get_project_scenes(task_db, project_id)
            total_scenes = len(scene_records)
            
            # Export folder path
            export_folder = f"exports/{project_id}"
            exported_files: List[dict] = []
            
            # Track time for subtitles
            current_time_cn = 0.0
            current_time_en = 0.0
            full_srt_cn_entries = []
            full_srt_en_entries = []
            
            # Build manifest
            manifest = {
                "project_id": project_id,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "total_scenes": total_scenes,
                "scenes": []
            }
            
            # Process each scene - use COS copy
            for i, scene in enumerate(scene_records):
                progress = int(10 + (i / total_scenes) * 60)
                task.update_progress(message=f"正在处理分镜 {i+1}/{total_scenes}...", current=progress, total=100)
                
                scene_num = str(i + 1).zfill(3)
                scene_folder = f"{export_folder}/scene_{scene_num}"
                
                # Get durations
                duration_cn = (scene.audio_cn_duration / 1000.0) if scene.audio_cn_duration else (scene.duration or 10)
                duration_en = (scene.audio_en_duration / 1000.0) if scene.audio_en_duration else (scene.duration or 10)
                
                scene_manifest = {
                    "scene_id": f"scene_{scene_num}",
                    "files": {},
                    "metadata": {
                        "duration": duration_cn,
                        "text_cn": scene.narration_cn or "",
                        "text_en": scene.narration_en or "",
                    }
                }
                
                # Copy image
                if scene.image_cos_url:
                    dest_key = f"{scene_folder}/image.png"
                    url = cos_client.copy_object(scene.image_cos_url, dest_key)
                    if url:
                        scene_manifest["files"]["image"] = url
                        exported_files.append({"name": f"scene_{scene_num}/image.png", "url": url, "type": "image"})
                
                # Copy audio CN
                if scene.audio_cn_cos_url:
                    dest_key = f"{scene_folder}/audio_cn.wav"
                    url = cos_client.copy_object(scene.audio_cn_cos_url, dest_key)
                    if url:
                        scene_manifest["files"]["audio_cn"] = url
                        exported_files.append({"name": f"scene_{scene_num}/audio_cn.wav", "url": url, "type": "audio"})
                
                # Copy audio EN
                if scene.audio_en_cos_url:
                    dest_key = f"{scene_folder}/audio_en.wav"
                    url = cos_client.copy_object(scene.audio_en_cos_url, dest_key)
                    if url:
                        scene_manifest["files"]["audio_en"] = url
                        exported_files.append({"name": f"scene_{scene_num}/audio_en.wav", "url": url, "type": "audio"})
                
                # Upload prompt.txt (legacy - image prompt)
                if scene.description_cn:
                    dest_key = f"{scene_folder}/prompt.txt"
                    url = cos_client.upload_text(scene.description_cn, dest_key)
                    if url:
                        scene_manifest["files"]["prompt"] = url
                        exported_files.append({"name": f"scene_{scene_num}/prompt.txt", "url": url, "type": "text"})
                
                # Upload image_prompt.txt (图片生成描述)
                image_prompt_text = scene.image_prompt or scene.description_cn
                if image_prompt_text:
                    dest_key = f"{scene_folder}/image_prompt.txt"
                    url = cos_client.upload_text(image_prompt_text, dest_key)
                    if url:
                        scene_manifest["files"]["image_prompt"] = url
                        exported_files.append({"name": f"scene_{scene_num}/image_prompt.txt", "url": url, "type": "text"})
                
                # Upload video_prompt.txt (视频生成描述)
                if scene.video_prompt:
                    dest_key = f"{scene_folder}/video_prompt.txt"
                    url = cos_client.upload_text(scene.video_prompt, dest_key)
                    if url:
                        scene_manifest["files"]["video_prompt"] = url
                        exported_files.append({"name": f"scene_{scene_num}/video_prompt.txt", "url": url, "type": "text"})
                
                # Generate scene subtitles
                if scene.narration_cn:
                    srt_content = _format_srt_entry(1, 0.0, duration_cn, scene.narration_cn)
                    dest_key = f"{scene_folder}/subtitle_cn.srt"
                    url = cos_client.upload_text(srt_content, dest_key, "text/plain; charset=utf-8")
                    if url:
                        scene_manifest["files"]["subtitle_cn"] = url
                        exported_files.append({"name": f"scene_{scene_num}/subtitle_cn.srt", "url": url, "type": "subtitle"})
                    
                    full_srt_cn_entries.append({
                        "index": i + 1,
                        "start": current_time_cn,
                        "end": current_time_cn + duration_cn,
                        "text": scene.narration_cn
                    })
                
                if scene.narration_en:
                    srt_content = _format_srt_entry(1, 0.0, duration_en, scene.narration_en)
                    dest_key = f"{scene_folder}/subtitle_en.srt"
                    url = cos_client.upload_text(srt_content, dest_key, "text/plain; charset=utf-8")
                    if url:
                        scene_manifest["files"]["subtitle_en"] = url
                        exported_files.append({"name": f"scene_{scene_num}/subtitle_en.srt", "url": url, "type": "subtitle"})
                    
                    full_srt_en_entries.append({
                        "index": i + 1,
                        "start": current_time_en,
                        "end": current_time_en + duration_en,
                        "text": scene.narration_en
                    })
                
                current_time_cn += duration_cn
                current_time_en += duration_en
                manifest["scenes"].append(scene_manifest)
            
            # Generate and upload full subtitles
            task.update_progress(message="正在生成完整字幕...", current=75, total=100)
            
            if full_srt_cn_entries:
                full_srt_cn = _generate_full_srt(full_srt_cn_entries)
                url = cos_client.upload_text(full_srt_cn, f"{export_folder}/full_cn.srt")
                if url:
                    manifest["full_subtitle_cn"] = url
                    exported_files.append({"name": "full_cn.srt", "url": url, "type": "subtitle"})
            
            if full_srt_en_entries:
                full_srt_en = _generate_full_srt(full_srt_en_entries)
                url = cos_client.upload_text(full_srt_en, f"{export_folder}/full_en.srt")
                if url:
                    manifest["full_subtitle_en"] = url
                    exported_files.append({"name": "full_en.srt", "url": url, "type": "subtitle"})
            
            # Copy full audio files
            task.update_progress(message="正在复制完整音频...", current=85, total=100)
            
            if proj.full_audio_cn_cos_url:
                url = cos_client.copy_object(proj.full_audio_cn_cos_url, f"{export_folder}/full_cn.wav")
                if url:
                    manifest["full_audio_cn"] = url
                    exported_files.append({"name": "full_cn.wav", "url": url, "type": "audio"})
            
            if proj.full_audio_en_cos_url:
                url = cos_client.copy_object(proj.full_audio_en_cos_url, f"{export_folder}/full_en.wav")
                if url:
                    manifest["full_audio_en"] = url
                    exported_files.append({"name": "full_en.wav", "url": url, "type": "audio"})
            
            # Upload manifest
            task.update_progress(message="正在生成清单文件...", current=90, total=100)
            
            manifest["files"] = exported_files
            manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
            manifest_url = cos_client.upload_text(manifest_json, f"{export_folder}/manifest.json", "application/json")
            
            if not manifest_url:
                raise Exception("上传清单文件失败，请检查 COS 配置")
            
            # Call SCF to create ZIP
            task.update_progress(message="正在打包 ZIP 文件...", current=95, total=100)
            
            scf_config = get_scf_config()
            cos_config = get_cos_config()
            zip_url = None
            zip_size = 0
            
            print(f"SCF config: zip_url={scf_config.zip_url}")
            print(f"COS config: bucket={cos_config.bucket}, region={cos_config.region}")
            print(f"Export folder: {export_folder}")
            
            if scf_config.zip_url:
                try:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        request_data = {
                            "bucket": cos_config.bucket,
                            "region": cos_config.region,
                            "folder": export_folder,
                            "output_key": f"{export_folder}/export.zip"
                        }
                        print(f"SCF request: {request_data}")
                        
                        resp = await client.post(
                            scf_config.zip_url,
                            json=request_data
                        )
                        print(f"SCF response status: {resp.status_code}")
                        print(f"SCF response body: {resp.text}")
                        
                        if resp.status_code == 200:
                            result = resp.json()
                            if result.get("code") == 0:
                                data = result.get("data", {})
                                zip_url = data.get("zip_url")
                                zip_size = data.get("zip_size", 0)
                                print(f"SCF ZIP created: {zip_url}, size: {zip_size}")
                            else:
                                print(f"SCF ZIP failed: {result.get('message')}")
                        else:
                            print(f"SCF HTTP error: {resp.status_code}")
                except Exception as e:
                    import traceback
                    print(f"SCF ZIP error: {e}")
                    print(traceback.format_exc())
            else:
                print("SCF_ZIP_URL not configured, skipping ZIP creation")
            
            # Update project export info with ZIP URL
            final_url = zip_url or manifest_url
            
            update_project_export(
                task_db,
                project_id,
                cos_url=final_url,
                cos_key=f"{export_folder}/export.zip" if zip_url else f"{export_folder}/manifest.json"
            )
            
            task.update_progress(message="导出完成", current=100, total=100)
            
            return {
                "project_id": project_id,
                "download_url": final_url,
                "file_count": len(exported_files),
                "zip_size": zip_size
            }
            
        finally:
            task_db.close()
    
    schedule_task(task, run_export())
    
    return ExportResponse(task_id=task.task_id)


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_srt_entry(index: int, start: float, end: float, text: str) -> str:
    """Format a single SRT entry."""
    start_tc = _format_srt_time(start)
    end_tc = _format_srt_time(end)
    return f"{index}\n{start_tc} --> {end_tc}\n{text}\n"


def _generate_full_srt(entries: list) -> str:
    """Generate full SRT content from entries."""
    lines = []
    for entry in entries:
        lines.append(str(entry["index"]))
        lines.append(f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}")
        lines.append(entry["text"])
        lines.append("")
    return "\n".join(lines)


@router.get("/{project_id}/export/status", response_model=ExportStatusResponse)
async def get_export_status(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportStatusResponse:
    """Get export status for a project."""
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
    
    has_export = bool(project.export_cos_url)
    
    return ExportStatusResponse(
        project_id=project_id,
        has_export=has_export,
        download_url=project.export_cos_url if has_export else None,
    )


@router.get("/{project_id}/export/download")
async def download_export(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Redirect to export manifest (contains all file URLs)."""
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
    
    if not project.export_cos_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPORT_NOT_FOUND", "message": "请先导出项目"},
        )
    
    return RedirectResponse(url=project.export_cos_url)
