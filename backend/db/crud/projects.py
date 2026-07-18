"""Project service for database operations.

This module provides service functions for project CRUD operations using database.
"""

import json
import random
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.db.models import (
    ProjectRecord, SceneRecord, ProjectCharacterRecord, CharacterRecord
)


def generate_project_id() -> str:
    """Generate a unique project ID."""
    return f"proj_{uuid.uuid4().hex[:8]}"


def generate_scene_id() -> str:
    """Generate a unique scene ID."""
    return f"scene_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Project CRUD
# =============================================================================

def create_project(
    db: Session,
    topic: str,
    target_audience: str,
    key_points: list[str],
    user_id: Optional[str] = None,
    style: str = "teaching",
    custom_style_description: Optional[str] = None
) -> ProjectRecord:
    """Create a new project."""
    project_id = generate_project_id()
    
    record = ProjectRecord(
        project_id=project_id,
        user_id=user_id,
        status="initialized",
        topic=topic,
        target_audience=target_audience,
        key_points=json.dumps(key_points, ensure_ascii=False) if key_points else "[]",
        style=style,
        custom_style_description=custom_style_description,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_project(db: Session, project_id: str) -> Optional[ProjectRecord]:
    """Get project by ID."""
    return db.query(ProjectRecord).filter(
        ProjectRecord.project_id == project_id
    ).first()


def list_projects(db: Session, user_id: Optional[str] = None) -> list[ProjectRecord]:
    """List all projects, optionally filtered by user."""
    query = db.query(ProjectRecord)
    if user_id:
        query = query.filter(ProjectRecord.user_id == user_id)
    return query.order_by(ProjectRecord.created_at.desc()).all()


def update_project_status(db: Session, project_id: str, status: str) -> bool:
    """Update project status."""
    record = get_project(db, project_id)
    if not record:
        return False
    record.status = status
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_project_storyboard(
    db: Session,
    project_id: str,
    title: str,
    total_duration: int
) -> bool:
    """Update project storyboard info."""
    record = get_project(db, project_id)
    if not record:
        return False
    record.storyboard_title = title
    record.total_duration = total_duration
    record.status = "storyboard_ready"
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_project_export(
    db: Session,
    project_id: str,
    cos_url: str,
    cos_key: str
) -> bool:
    """Update project export info."""
    record = get_project(db, project_id)
    if not record:
        return False
    record.export_cos_url = cos_url
    record.export_cos_key = cos_key
    record.status = "completed"
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def set_project_active_task(
    db: Session,
    project_id: str,
    task_id: str,
    task_type: str
) -> bool:
    """设置项目的活跃任务"""
    record = get_project(db, project_id)
    if not record:
        return False
    record.active_task_id = task_id
    record.active_task_type = task_type
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def clear_project_active_task(db: Session, project_id: str) -> bool:
    """清除项目的活跃任务"""
    record = get_project(db, project_id)
    if not record:
        return False
    record.active_task_id = None
    record.active_task_type = None
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def get_project_active_task(db: Session, project_id: str) -> Optional[dict]:
    """获取项目的活跃任务信息"""
    record = get_project(db, project_id)
    if not record or not record.active_task_id:
        return None
    return {
        "task_id": record.active_task_id,
        "task_type": record.active_task_type
    }


def delete_project(db: Session, project_id: str) -> bool:
    """Delete project and all related data."""
    # Delete scenes
    db.query(SceneRecord).filter(SceneRecord.project_id == project_id).delete()
    # Delete project characters
    db.query(ProjectCharacterRecord).filter(
        ProjectCharacterRecord.project_id == project_id
    ).delete()
    # Delete project
    result = db.query(ProjectRecord).filter(
        ProjectRecord.project_id == project_id
    ).delete()
    db.commit()
    return result > 0


# =============================================================================
# Scene CRUD
# =============================================================================

def create_scene(
    db: Session,
    project_id: str,
    step_number: int,
    description_cn: str,
    narration_cn: str,
    narration_en: str = "",
    duration: int = 10,
    character_ids: list[str] = None,
    audio_params: dict = None,
    image_prompt: str = "",
    video_prompt: str = ""
) -> SceneRecord:
    """Create a new scene."""
    scene_id = generate_scene_id()
    
    record = SceneRecord(
        scene_id=scene_id,
        project_id=project_id,
        step_number=step_number,
        description_cn=description_cn,
        narration_cn=narration_cn,
        narration_en=narration_en,
        duration=duration,
        character_ids=json.dumps(character_ids or [], ensure_ascii=False),
        audio_params=json.dumps(audio_params, ensure_ascii=False) if audio_params else None,
        image_prompt=image_prompt or description_cn,  # 兼容：默认使用 description_cn
        video_prompt=video_prompt,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_scene(db: Session, scene_id: str) -> Optional[SceneRecord]:
    """Get scene by ID."""
    return db.query(SceneRecord).filter(SceneRecord.scene_id == scene_id).first()


def get_project_scenes(db: Session, project_id: str) -> list[SceneRecord]:
    """Get all scenes for a project."""
    return db.query(SceneRecord).filter(
        SceneRecord.project_id == project_id
    ).order_by(SceneRecord.step_number).all()


def update_scene(
    db: Session,
    scene_id: str,
    **kwargs
) -> bool:
    """Update scene fields."""
    record = get_scene(db, scene_id)
    if not record:
        return False
    
    for key, value in kwargs.items():
        if hasattr(record, key):
            setattr(record, key, value)
    
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_scene_image(
    db: Session,
    scene_id: str,
    status: str,
    cos_url: str = None,
    cos_key: str = None,
    prompt: str = None
) -> bool:
    """Update scene image info."""
    record = get_scene(db, scene_id)
    if not record:
        return False
    
    record.image_status = status
    if cos_url:
        record.image_cos_url = cos_url
    if cos_key:
        record.image_cos_key = cos_key
    if prompt:
        record.image_prompt = prompt
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_scene_audio_cn(
    db: Session,
    scene_id: str,
    status: str,
    cos_url: str = None,
    cos_key: str = None,
    duration_ms: int = None
) -> bool:
    """Update scene Chinese audio info."""
    record = get_scene(db, scene_id)
    if not record:
        return False
    
    record.audio_cn_status = status
    if cos_url:
        record.audio_cn_cos_url = cos_url
    if cos_key:
        record.audio_cn_cos_key = cos_key
    if duration_ms is not None:
        record.audio_cn_duration = duration_ms
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_scene_audio_en(
    db: Session,
    scene_id: str,
    status: str,
    cos_url: str = None,
    cos_key: str = None,
    duration_ms: int = None
) -> bool:
    """Update scene English audio info."""
    record = get_scene(db, scene_id)
    if not record:
        return False
    
    record.audio_en_status = status
    if cos_url:
        record.audio_en_cos_url = cos_url
    if cos_key:
        record.audio_en_cos_key = cos_key
    if duration_ms is not None:
        record.audio_en_duration = duration_ms
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_project_full_audio(
    db: Session,
    project_id: str,
    cn_cos_url: str = None,
    cn_cos_key: str = None,
    cn_duration_ms: int = None,
    en_cos_url: str = None,
    en_cos_key: str = None,
    en_duration_ms: int = None
) -> bool:
    """Update project full audio info."""
    record = get_project(db, project_id)
    if not record:
        return False
    
    if cn_cos_url:
        record.full_audio_cn_cos_url = cn_cos_url
    if cn_cos_key:
        record.full_audio_cn_cos_key = cn_cos_key
    if cn_duration_ms is not None:
        record.full_audio_cn_duration = cn_duration_ms
    if en_cos_url:
        record.full_audio_en_cos_url = en_cos_url
    if en_cos_key:
        record.full_audio_en_cos_key = en_cos_key
    if en_duration_ms is not None:
        record.full_audio_en_duration = en_duration_ms
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def delete_project_scenes(db: Session, project_id: str) -> int:
    """Delete all scenes for a project."""
    result = db.query(SceneRecord).filter(
        SceneRecord.project_id == project_id
    ).delete()
    db.commit()
    return result


# =============================================================================
# Project Character CRUD
# =============================================================================

def add_character_to_project(
    db: Session,
    project_id: str,
    character_id: str
) -> bool:
    """Add a character to a project."""
    # Check if already exists
    existing = db.query(ProjectCharacterRecord).filter(
        ProjectCharacterRecord.project_id == project_id,
        ProjectCharacterRecord.character_id == character_id
    ).first()
    
    if existing:
        return True
    
    record = ProjectCharacterRecord(
        project_id=project_id,
        character_id=character_id
    )
    db.add(record)
    db.commit()
    return True


def remove_character_from_project(
    db: Session,
    project_id: str,
    character_id: str
) -> bool:
    """Remove a character from a project."""
    result = db.query(ProjectCharacterRecord).filter(
        ProjectCharacterRecord.project_id == project_id,
        ProjectCharacterRecord.character_id == character_id
    ).delete()
    db.commit()
    return result > 0


def get_project_characters(
    db: Session,
    project_id: str
) -> list[CharacterRecord]:
    """Get all characters for a project."""
    # Get character IDs
    associations = db.query(ProjectCharacterRecord).filter(
        ProjectCharacterRecord.project_id == project_id
    ).all()
    
    character_ids = [a.character_id for a in associations]
    
    if not character_ids:
        return []
    
    # Get character records
    return db.query(CharacterRecord).filter(
        CharacterRecord.character_id.in_(character_ids)
    ).all()


# =============================================================================
# Helper functions for API responses
# =============================================================================

def project_to_dict(record: ProjectRecord, scenes: list[SceneRecord] = None) -> dict:
    """Convert project record to API response dict."""
    key_points = []
    if record.key_points:
        try:
            key_points = json.loads(record.key_points)
        except json.JSONDecodeError:
            pass
    
    result = {
        "project_id": record.project_id,
        "status": record.status,
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else "",
        "updated_at": record.updated_at.isoformat() + "Z" if record.updated_at else "",
        "goal": {
            "topic": record.topic,
            "target_audience": record.target_audience or "",
            "key_points": key_points,
            "style": record.style or "teaching",
            "custom_style_description": record.custom_style_description
        }
    }
    
    # Add storyboard if available
    if record.storyboard_title and scenes:
        result["storyboard"] = {
            "title": record.storyboard_title,
            "total_duration_seconds": record.total_duration,
            "scenes": [scene_to_dict(s) for s in scenes]
        }
    
    # Add export if available
    if record.export_cos_url:
        result["export"] = {
            "cos_url": record.export_cos_url,
            "cos_key": record.export_cos_key
        }
    
    return result


def scene_to_dict(record: SceneRecord) -> dict:
    """Convert scene record to API response dict."""
    character_ids = []
    if record.character_ids:
        try:
            character_ids = json.loads(record.character_ids)
        except json.JSONDecodeError:
            pass
    
    # Parse audio_params if available
    audio_params = None
    if record.audio_params:
        try:
            audio_params = json.loads(record.audio_params)
        except json.JSONDecodeError:
            pass
    
    return {
        "scene_id": record.scene_id,
        "step_number": record.step_number,
        "description_cn": record.description_cn or "",
        # 新增：拆分场景描述
        "image_prompt": record.image_prompt or record.description_cn or "",
        "video_prompt": record.video_prompt or "",
        "narration_cn": record.narration_cn or "",
        "narration_en": record.narration_en or "",
        "duration": record.duration,
        "character_ids": character_ids,
        "audio_params": audio_params,
        "image": {
            "status": record.image_status,
            "url": record.image_cos_url,
            "prompt": record.image_prompt
        },
        "audio_cn": {
            "status": record.audio_cn_status,
            "url": record.audio_cn_cos_url,
            "duration_ms": record.audio_cn_duration
        },
        "audio_en": {
            "status": record.audio_en_status,
            "url": record.audio_en_cos_url,
            "duration_ms": record.audio_en_duration
        }
    }
