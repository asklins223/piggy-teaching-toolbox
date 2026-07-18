"""Storyboard generation and management API module.

This module provides REST API endpoints for storyboard generation,
scene listing, scene editing, and image regeneration.

Requirements: 3.3
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.api.validators import validate_audio_params
from backend.services.tasks import Task, create_task, schedule_task
from backend.config import get_settings
from backend.db.models import get_db, SceneRecord
from backend.db.crud.projects import (
    get_project, get_project_scenes, update_project_storyboard,
    update_project_status, create_scene, update_scene, update_scene_image,
    delete_project_scenes, scene_to_dict
)
from backend.services import cos_client


# Router for storyboard endpoints under /api/projects/{project_id}
router = APIRouter()


# Request/Response models
class GenerateStoryboardRequest(BaseModel):
    """Request model for storyboard generation."""
    duration: str = Field(
        default="10",
        description="Default scene duration (5, 8, 10, 12, or 15 seconds)"
    )
    stepwise: bool = Field(
        default=False,
        description="是否使用分步生成模式（先大纲后详情）"
    )


class GenerateStoryboardResponse(BaseModel):
    """Response model for storyboard generation."""
    task_id: str


class SceneResponse(BaseModel):
    """Response model for a single scene."""
    scene_id: str
    step_number: int
    description_cn: str
    # 新增：拆分场景描述
    image_prompt: str = ""
    video_prompt: str = ""
    narration_cn: str
    narration_en: str
    duration: int
    image_url: Optional[str] = None
    character_ids: list[str] = Field(default_factory=list)
    # Audio params (Requirements: 7.4)
    audio_params: Optional[dict] = Field(default=None, description="Audio generation parameters")


class ScenesListResponse(BaseModel):
    """Response model for scenes list."""
    scenes: list[SceneResponse]


class UpdateSceneRequest(BaseModel):
    """Request model for updating a scene."""
    description_cn: Optional[str] = None
    # 新增：拆分场景描述
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    narration_cn: Optional[str] = None
    narration_en: Optional[str] = None
    duration: Optional[int] = None
    # Audio params (Requirements: 7.4)
    audio_params: Optional[dict] = Field(default=None, description="Audio generation parameters")


class UpdateSceneResponse(BaseModel):
    """Response model for scene update."""
    scene: SceneResponse


class RegenerateImageResponse(BaseModel):
    """Response model for image regeneration."""
    task_id: str


def _scene_record_to_response(record: SceneRecord) -> SceneResponse:
    """Convert a SceneRecord to SceneResponse."""
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
    
    return SceneResponse(
        scene_id=record.scene_id,
        step_number=record.step_number,
        description_cn=record.description_cn or "",
        image_prompt=record.image_prompt or record.description_cn or "",
        video_prompt=record.video_prompt or "",
        narration_cn=record.narration_cn or "",
        narration_en=record.narration_en or "",
        duration=record.duration,
        image_url=record.image_cos_url,
        character_ids=character_ids,
        audio_params=audio_params,
    )


# API Endpoints
@router.post("/{project_id}/storyboard/generate", response_model=GenerateStoryboardResponse)
async def generate_storyboard(
    project_id: str,
    request: GenerateStoryboardRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerateStoryboardResponse:
    """Generate storyboard script and images for a project."""
    from backend.db.crud.projects import get_project_active_task, set_project_active_task, clear_project_active_task
    
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
        # 检查任务是否还在运行
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
            # 任务已完成或失败，清除记录
            clear_project_active_task(db, project_id)
    
    # Create task
    task = create_task("storyboard")
    
    # 记录活跃任务
    set_project_active_task(db, project_id, task.task_id, "storyboard")
    
    # Define the async generation function
    async def run_generation():
        print(f"[Storyboard Generation] Starting for project {project_id}")
        from backend.db.models import get_session_local
        from backend.core.script_planner import ScriptPlanner
        from backend.core.generators.scene import SceneGenerator
        from backend.schemas.models import TeachingGoal, VideoStyle
        from backend.db.crud.projects import clear_project_active_task
        
        settings = get_settings()
        
        # Create new db session for async task
        SessionLocal = get_session_local()
        task_db = SessionLocal()
        
        try:
            print(f"[Storyboard Generation] Getting project data")
            # Get project again in task context
            proj = get_project(task_db, project_id)
            if not proj:
                raise Exception("项目不存在")
            
            print(f"[Storyboard Generation] Project found: {proj.topic}")
            
            # Parse key points
            key_points = []
            if proj.key_points:
                try:
                    key_points = json.loads(proj.key_points)
                except json.JSONDecodeError:
                    pass
            
            # Parse style from project
            style = VideoStyle.TEACHING  # default
            if proj.style:
                try:
                    style = VideoStyle(proj.style)
                except ValueError:
                    # If invalid style, use default
                    style = VideoStyle.TEACHING
            
            # Create teaching goal with style information
            goal = TeachingGoal(
                topic=proj.topic,
                target_audience=proj.target_audience or "",
                key_points=key_points,
                style=style,  # 添加风格信息
                custom_style_description=proj.custom_style_description  # 添加自定义风格描述
            )
            
            # Get characters for the project
            from backend.db.crud.projects import get_project_characters
            from backend.schemas.models import CharacterReference
            db_characters = get_project_characters(task_db, project_id)
            # Convert to CharacterReference objects
            characters = [
                CharacterReference(
                    character_id=c.character_id,
                    name=c.name,
                    image_path=c.cos_url or "",
                    image_url=c.cos_url
                )
                for c in db_characters
            ]
            
            # Step 1: Generate storyboard script
            task.update_progress(message="正在分析教学内容...", progress=1)
            
            from backend.schemas.models import SceneDuration
            
            script_planner = ScriptPlanner(api_key=settings.dashscope.api_key)
            duration_int = int(request.duration) if request.duration.isdigit() else 10
            
            # Map int to SceneDuration enum
            duration_map = {5: SceneDuration.VERY_SHORT, 8: SceneDuration.SHORT, 10: SceneDuration.MEDIUM, 12: SceneDuration.LONG, 15: SceneDuration.VERY_LONG}
            default_duration = duration_map.get(duration_int, SceneDuration.MEDIUM)
            
            task.update_progress(message="正在生成分镜脚本...", progress=10)
            
            # 根据 stepwise 参数选择生成模式
            if request.stepwise:
                # 分步生成模式：先大纲后详情
                def on_stepwise_progress(current, total, message):
                    # 将分步生成的进度映射到 10-30%
                    progress = 10 + int((current / total) * 20)
                    task.update_progress(message=message, progress=progress)
                
                storyboard = await script_planner.generate_storyboard_stepwise(
                    goal=goal,
                    characters=characters if characters else None,
                    default_duration=default_duration,
                    on_progress=on_stepwise_progress
                )
            else:
                # 一次性生成模式（原有逻辑）
                storyboard = await script_planner.generate_storyboard(
                    goal=goal,
                    characters=characters if characters else None,
                    default_duration=default_duration
                )
            
            task.update_progress(message="分镜脚本生成完成", progress=30)
            
            # Delete existing scenes
            delete_project_scenes(task_db, project_id)
            
            task.update_progress(message="正在保存分镜数据...", progress=35)
            
            # Save scenes to database
            for i, scene in enumerate(storyboard.scenes):
                # Convert AudioParams to dict for storage
                audio_params_dict = None
                if scene.audio_params:
                    audio_params_dict = {
                        "emotion": scene.audio_params.emotion.value,
                        "emotion_strength": scene.audio_params.emotion_strength,
                        "speed": scene.audio_params.speed,
                        "volume": scene.audio_params.volume,
                    }
                
                create_scene(
                    db=task_db,
                    project_id=project_id,
                    step_number=scene.step_number,
                    description_cn=scene.description_cn,
                    narration_cn=scene.narration_cn,
                    narration_en=scene.narration_en,
                    duration=scene.duration.value if hasattr(scene.duration, 'value') else scene.duration,
                    character_ids=scene.character_ids,
                    audio_params=audio_params_dict,
                    image_prompt=scene.image_prompt or scene.description_cn,
                    video_prompt=scene.video_prompt or ""
                )
                
                # Update progress for each scene saved
                progress = 35 + (i + 1) * 5 // len(storyboard.scenes)
                task.update_progress(message=f"保存分镜 {i+1}/{len(storyboard.scenes)}", progress=progress)
            
            # Update project storyboard info
            total_duration = sum(
                s.duration.value if hasattr(s.duration, 'value') else s.duration
                for s in storyboard.scenes
            )
            update_project_storyboard(
                task_db, project_id, storyboard.title, total_duration
            )
            
            task.update_progress(message="分镜脚本保存完成，开始生成图片...", progress=40)
            
            # Step 2: Generate images for each scene
            
            from backend.core.generators.scene import SceneGenerator
            from backend.schemas.models import Scene as SceneModel, SceneDuration, Emotion
            import tempfile
            from pathlib import Path
            
            scene_generator = SceneGenerator()  # Uses volcengine config
            scenes = get_project_scenes(task_db, project_id)
            
            # Build character refs dict
            character_refs = {
                c.character_id: CharacterReference(
                    character_id=c.character_id,
                    name=c.name,
                    image_path=c.cos_url or "",
                    image_url=c.cos_url
                )
                for c in db_characters
            } if db_characters else {}
            
            # Create temp dir for images
            temp_dir = Path(tempfile.mkdtemp())
            
            for i, scene_record in enumerate(scenes):
                # Calculate progress: 40-95% for image generation
                base_progress = 40
                image_progress_range = 55  # 95 - 40
                current_progress = base_progress + (i * image_progress_range // len(scenes))
                
                task.update_progress(
                    message=f"正在生成第 {i+1}/{len(scenes)} 张分镜图片...",
                    progress=current_progress
                )
                
                try:
                    # Convert DB record to Scene model
                    char_ids = []
                    if scene_record.character_ids:
                        try:
                            char_ids = json.loads(scene_record.character_ids)
                        except:
                            pass
                    
                    scene_model = SceneModel(
                        scene_id=scene_record.scene_id,
                        step_number=scene_record.step_number,
                        description_cn=scene_record.description_cn or "",
                        image_prompt=scene_record.image_prompt or scene_record.description_cn or "",
                        video_prompt=scene_record.video_prompt or "",
                        narration_cn=scene_record.narration_cn or "",
                        narration_en=scene_record.narration_en or "",
                        duration=SceneDuration(scene_record.duration) if scene_record.duration in [5,8,10,12,15] else SceneDuration.MEDIUM,
                        character_ids=char_ids
                    )
                    
                    # Generate image
                    scene_image = await scene_generator.generate_image(
                        scene=scene_model,
                        output_dir=temp_dir,
                        character_refs=character_refs if character_refs else None
                    )
                    
                    # Read generated image and upload to COS
                    image_path = Path(scene_image.image_path)
                    if image_path.exists():
                        image_data = image_path.read_bytes()
                        
                        # Upload to COS
                        cos_result = cos_client.upload_file(
                            file_data=image_data,
                            filename=f"{scene_record.scene_id}.png",
                            folder=f"projects/{project_id}/images",
                            content_type="image/png"
                        )
                        
                        if cos_result:
                            update_scene_image(
                                task_db,
                                scene_record.scene_id,
                                status="completed",
                                cos_url=cos_result["cos_url"],
                                cos_key=cos_result["cos_key"],
                                prompt=scene_record.image_prompt or scene_record.description_cn
                            )
                            # Update progress after successful upload
                            upload_progress = base_progress + ((i + 1) * image_progress_range // len(scenes))
                            task.update_progress(
                                message=f"第 {i+1}/{len(scenes)} 张图片生成完成",
                                progress=upload_progress
                            )
                        else:
                            update_scene_image(
                                task_db,
                                scene_record.scene_id,
                                status="failed"
                            )
                    else:
                        update_scene_image(
                            task_db,
                            scene_record.scene_id,
                            status="failed"
                        )
                except Exception as e:
                    print(f"Image generation error: {e}")
                    update_scene_image(
                        task_db,
                        scene_record.scene_id,
                        status="failed"
                    )
                    # Still update progress even if failed
                    error_progress = base_progress + ((i + 1) * image_progress_range // len(scenes))
                    task.update_progress(
                        message=f"第 {i+1}/{len(scenes)} 张图片生成失败",
                        progress=error_progress
                    )
            
            # Update project status
            task.update_progress(message="正在更新项目状态...", progress=95)
            update_project_status(task_db, project_id, "images_ready")
            
            # 清除活跃任务
            clear_project_active_task(task_db, project_id)
            
            task.update_progress(message="分镜生成完成！", progress=100)
            
            return {"project_id": project_id}
            
        finally:
            task_db.close()
    
    # Schedule the task
    schedule_task(task, run_generation())
    
    return GenerateStoryboardResponse(task_id=task.task_id)


@router.get("/{project_id}/scenes", response_model=ScenesListResponse)
async def get_scenes(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScenesListResponse:
    """Get list of scenes for a project."""
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
    
    scenes = get_project_scenes(db, project_id)
    
    return ScenesListResponse(
        scenes=[_scene_record_to_response(s) for s in scenes]
    )


@router.put("/{project_id}/scenes/{scene_id}", response_model=UpdateSceneResponse)
async def update_scene_endpoint(
    project_id: str,
    scene_id: str,
    request: UpdateSceneRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UpdateSceneResponse:
    """Update a scene's content."""
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
    
    # Find the scene
    scene = db.query(SceneRecord).filter(
        SceneRecord.scene_id == scene_id,
        SceneRecord.project_id == project_id
    ).first()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCENE_NOT_FOUND", "message": f"场景 {scene_id} 不存在"},
        )
    
    # Build updates dict from request
    updates = request.model_dump(exclude_unset=True)
    
    # Validate and serialize audio_params to JSON string if present (Requirements: 7.5)
    if "audio_params" in updates and updates["audio_params"] is not None:
        validated_params = validate_audio_params(updates["audio_params"])
        updates["audio_params"] = json.dumps(validated_params, ensure_ascii=False)
    
    # Update the scene
    if updates:
        update_scene(db, scene_id, **updates)
        db.refresh(scene)
    
    return UpdateSceneResponse(scene=_scene_record_to_response(scene))


@router.post("/{project_id}/scenes/{scene_id}/regenerate-image", response_model=RegenerateImageResponse)
async def regenerate_scene_image(
    project_id: str,
    scene_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegenerateImageResponse:
    """Regenerate the image for a specific scene."""
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
    
    # Find the scene
    scene = db.query(SceneRecord).filter(
        SceneRecord.scene_id == scene_id,
        SceneRecord.project_id == project_id
    ).first()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCENE_NOT_FOUND", "message": f"场景 {scene_id} 不存在"},
        )
    
    # Create task
    task = create_task("regenerate_image")
    
    # Define the async regeneration function
    async def run_regeneration():
        from backend.db.models import get_session_local
        from backend.core.generators.scene import SceneGenerator
        
        settings = get_settings()
        
        SessionLocal = get_session_local()
        task_db = SessionLocal()
        
        try:
            task.update_progress(message=f"正在重新生成场景图片...", current=0, total=1)
            
            # Get scene
            scene_record = task_db.query(SceneRecord).filter(
                SceneRecord.scene_id == scene_id
            ).first()
            
            if not scene_record:
                raise Exception("场景不存在")
            
            # Get characters
            from backend.db.crud.projects import get_project_characters
            from backend.schemas.models import CharacterReference, Scene as SceneModel, SceneDuration, Emotion
            import tempfile
            from pathlib import Path
            
            db_characters = get_project_characters(task_db, project_id)
            character_refs = {
                c.character_id: CharacterReference(
                    character_id=c.character_id,
                    name=c.name,
                    image_path=c.cos_url or "",
                    image_url=c.cos_url
                )
                for c in db_characters
            } if db_characters else {}
            
            # Convert DB record to Scene model
            char_ids = []
            if scene_record.character_ids:
                try:
                    char_ids = json.loads(scene_record.character_ids)
                except:
                    pass
            
            scene_model = SceneModel(
                scene_id=scene_record.scene_id,
                step_number=scene_record.step_number,
                description_cn=scene_record.description_cn or "",
                image_prompt=scene_record.image_prompt or scene_record.description_cn or "",
                video_prompt=scene_record.video_prompt or "",
                narration_cn=scene_record.narration_cn or "",
                narration_en=scene_record.narration_en or "",
                duration=SceneDuration(scene_record.duration) if scene_record.duration in [5,8,10,12,15] else SceneDuration.MEDIUM,
                character_ids=char_ids
            )
            
            # Generate image
            scene_generator = SceneGenerator()  # Uses volcengine config
            temp_dir = Path(tempfile.mkdtemp())
            
            scene_image = await scene_generator.generate_image(
                scene=scene_model,
                output_dir=temp_dir,
                character_refs=character_refs if character_refs else None
            )
            
            # Read generated image
            image_path = Path(scene_image.image_path)
            if not image_path.exists():
                raise Exception("图片生成失败")
            
            image_data = image_path.read_bytes()
            
            # Delete old COS file if exists
            if scene_record.image_cos_key:
                cos_client.delete_file(scene_record.image_cos_key)
            
            # Upload to COS
            cos_result = cos_client.upload_file(
                file_data=image_data,
                filename=f"{scene_id}.png",
                folder=f"projects/{project_id}/images",
                content_type="image/png"
            )
            
            if cos_result:
                update_scene_image(
                    task_db,
                    scene_id,
                    status="completed",
                    cos_url=cos_result["cos_url"],
                    cos_key=cos_result["cos_key"],
                    prompt=scene_record.image_prompt or scene_record.description_cn
                )
            else:
                raise Exception("上传图片失败")
            
            task.update_progress(message="图片重新生成完成", current=1, total=1)
            
            return {"project_id": project_id, "scene_id": scene_id}
            
        finally:
            task_db.close()
    
    # Schedule the task
    schedule_task(task, run_regeneration())
    
    return RegenerateImageResponse(task_id=task.task_id)
