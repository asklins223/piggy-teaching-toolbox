"""Project management API module.

This module provides REST API endpoints for project CRUD operations.
Uses database for storage instead of file system.

Requirements: 3.1, 4.1
"""

import json
import random
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.api.validators import validate_style
from backend.config import get_settings
from backend.db.models import get_db, ProjectRecord, CharacterRecord
from backend.db.crud.projects import (
    create_project, get_project, list_projects, delete_project,
    get_project_scenes, get_project_characters,
    project_to_dict, scene_to_dict
)


# Router
router = APIRouter()


# Request/Response models
class CreateProjectRequest(BaseModel):
    """Request model for creating a project."""
    topic: str = Field(..., min_length=1, description="Teaching topic")
    target_audience: str = Field(..., min_length=1, description="Target audience")
    key_points: list[str] = Field(default_factory=list, description="Key concepts to cover")
    # Video style (Requirements: 7.1)
    style: str = Field(default="teaching", description="Video style: teaching, nursery_rhyme, storybook, recitation, custom")
    custom_style_description: Optional[str] = Field(default=None, description="Custom style description (required when style is 'custom')")


class ProjectSummary(BaseModel):
    """Summary model for project list."""
    project_id: str
    topic: str
    status: str
    created_at: str
    style: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Response model for project list."""
    projects: list[ProjectSummary]


class CreateProjectResponse(BaseModel):
    """Response model for project creation."""
    project_id: str
    status: str


class DeleteProjectResponse(BaseModel):
    """Response model for project deletion."""
    success: bool


class OptimizeTopicRequest(BaseModel):
    """Request model for AI topic optimization."""
    topic: str = Field(..., min_length=1, description="Topic to optimize")


class OptimizeTopicResponse(BaseModel):
    """Response model for AI topic optimization."""
    optimized_topic: str
    message: str


class SuggestKeyPointsRequest(BaseModel):
    """Request model for AI key points suggestion."""
    topic: str = Field(..., min_length=1, description="Teaching topic")
    target_audience: str = Field(default="", description="Target audience")


class SuggestKeyPointsResponse(BaseModel):
    """Response model for AI key points suggestion."""
    key_points: list[str]
    message: str


class SuggestAudienceRequest(BaseModel):
    """Request model for AI audience suggestion."""
    topic: str = Field(..., min_length=1, description="Teaching topic")


class SuggestAudienceResponse(BaseModel):
    """Response model for AI audience suggestion."""
    target_audience: str


class RandomTopicResponse(BaseModel):
    """Response model for AI random topic generation."""
    topic: str
    target_audience: str
    key_points: list[str]


# AI Helper Functions
def _call_ai_assist(prompt: str, temperature: float = 0.7) -> str:
    """Call AI for assistance generation."""
    import dashscope
    from dashscope import Generation
    
    settings = get_settings()
    dashscope.api_key = settings.dashscope.api_key
    
    response = Generation.call(
        model='qwen-max',
        prompt=prompt,
        temperature=temperature,
        max_tokens=2048
    )
    
    if response.status_code == 200:
        return response.output.text
    else:
        raise Exception(f"AI call failed: {response.message}")


# API Endpoints
@router.get("", response_model=ProjectListResponse)
async def list_all_projects(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    """Get list of all projects for current user."""
    records = list_projects(db, user_id=current_user)
    
    projects = [
        ProjectSummary(
            project_id=r.project_id,
            topic=r.topic,
            status=r.status,
            created_at=r.created_at.isoformat() + "Z" if r.created_at else "",
            style=r.style
        )
        for r in records
    ]
    
    return ProjectListResponse(projects=projects)


@router.post("", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    request: CreateProjectRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateProjectResponse:
    """Create a new project."""
    # Validate style parameter (Requirements: 7.5)
    validate_style(request.style)
    
    record = create_project(
        db=db,
        topic=request.topic,
        target_audience=request.target_audience,
        key_points=request.key_points,
        user_id=current_user,
        style=request.style,
        custom_style_description=request.custom_style_description
    )
    
    return CreateProjectResponse(
        project_id=record.project_id,
        status=record.status
    )


@router.get("/{project_id}")
async def get_project_detail(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get project details."""
    record = get_project(db, project_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"}
        )
    
    # Check ownership
    if record.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权访问此项目"}
        )
    
    # Get scenes
    scenes = get_project_scenes(db, project_id)
    
    # Get characters
    characters = get_project_characters(db, project_id)
    
    result = project_to_dict(record, scenes)
    
    # Add characters
    result["characters"] = [
        {
            "character_id": c.character_id,
            "name": c.name,
            "image_url": c.cos_url
        }
        for c in characters
    ]
    
    # Add images/audios arrays for frontend compatibility
    result["images"] = []
    result["audios"] = []
    result["subtitles"] = []
    
    for scene in scenes:
        if scene.image_cos_url:
            result["images"].append({
                "scene_id": scene.scene_id,
                "path": scene.image_cos_url,
                "status": scene.image_status
            })
        if scene.audio_cn_cos_url:
            result["audios"].append({
                "scene_id": scene.scene_id,
                "audio_path": scene.audio_cn_cos_url,
                "audio_path_en": scene.audio_en_cos_url,
                "status": scene.audio_cn_status,
                "duration_seconds": scene.audio_cn_duration / 1000 if scene.audio_cn_duration else 0,
                "duration_seconds_en": scene.audio_en_duration / 1000 if scene.audio_en_duration else 0
            })
    
    return result


class ActiveTaskResponse(BaseModel):
    """Response model for active task query."""
    has_active_task: bool
    task_id: Optional[str] = None
    task_type: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None


@router.get("/{project_id}/active-task", response_model=ActiveTaskResponse)
async def get_project_active_task_endpoint(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActiveTaskResponse:
    """获取项目当前正在进行的任务"""
    from backend.db.crud.projects import get_project_active_task, clear_project_active_task
    from backend.services.tasks import get_task, TaskStatus
    
    record = get_project(db, project_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"}
        )
    
    if record.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权访问此项目"}
        )
    
    active_task_info = get_project_active_task(db, project_id)
    
    if not active_task_info:
        return ActiveTaskResponse(has_active_task=False)
    
    # 检查任务是否还存在且在运行
    task = get_task(active_task_info["task_id"])
    
    if not task:
        # 任务不存在了，清除记录
        clear_project_active_task(db, project_id)
        return ActiveTaskResponse(has_active_task=False)
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        # 任务已完成或失败，清除记录
        clear_project_active_task(db, project_id)
        return ActiveTaskResponse(
            has_active_task=False,
            task_id=task.task_id,
            task_type=active_task_info["task_type"],
            status=task.status.value,
            progress=task.progress,
            message=task.message
        )
    
    # 任务正在进行中
    return ActiveTaskResponse(
        has_active_task=True,
        task_id=task.task_id,
        task_type=active_task_info["task_type"],
        status=task.status.value,
        progress=task.progress,
        message=task.message
    )


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project_by_id(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteProjectResponse:
    """Delete a project."""
    record = get_project(db, project_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"项目 {project_id} 不存在"}
        )
    
    # Check ownership
    if record.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "无权删除此项目"}
        )
    
    # TODO: Delete COS files (images, audios, export)
    
    delete_project(db, project_id)
    
    return DeleteProjectResponse(success=True)


# AI Optimization Endpoints
@router.post("/ai/optimize-topic", response_model=OptimizeTopicResponse)
async def optimize_topic(
    request: OptimizeTopicRequest,
    current_user: str = Depends(get_current_user),
) -> OptimizeTopicResponse:
    """AI optimize teaching topic."""
    topic = request.topic.strip()
    if not topic:
        return OptimizeTopicResponse(optimized_topic=topic, message="请先输入主题")
    
    try:
        prompt = f"""作为教育内容策划专家，请优化这个教学视频主题。

原始主题：{topic}

优化策略：
1. 分析主题的核心教学价值，提炼最吸引人的学习点
2. 加入具体的学习场景或应用方向（如"生活中的XX"、"XX实战"）
3. 如果主题过于宽泛，聚焦到一个可在5-10分钟视频内讲清楚的子话题
4. 使用能激发学习兴趣的表达方式

示例：
- "英语" → "10个厨房用品的英语表达与趣味记忆法"
- "Python" → "用Python自动整理桌面文件"
- "历史" → "三国演义中的5个经典谋略故事"

直接输出优化后的主题（15-25字）："""
        
        result = _call_ai_assist(prompt)
        optimized = result.strip().strip('"').strip("'")
        return OptimizeTopicResponse(
            optimized_topic=optimized,
            message=f"AI 建议：{optimized}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_ERROR", "message": f"优化失败: {str(e)}"}
        )


@router.post("/ai/suggest-keypoints", response_model=SuggestKeyPointsResponse)
async def suggest_keypoints(
    request: SuggestKeyPointsRequest,
    current_user: str = Depends(get_current_user),
) -> SuggestKeyPointsResponse:
    """AI suggest key points for teaching topic."""
    topic = request.topic.strip()
    if not topic:
        return SuggestKeyPointsResponse(key_points=[], message="请先输入主题")
    
    try:
        audience_text = request.target_audience.strip() if request.target_audience else "通用受众"
        prompt = f"""为教学视频「{topic}」设计知识点大纲，目标受众：{audience_text}

设计原则：
1. 遵循"引入→基础→核心→应用→总结"的教学逻辑
2. 每个知识点要能独立成为一个教学片段（1-2分钟）
3. 知识点之间要有递进关系，前一个是后一个的基础
4. 最后一个知识点要有实践或应用价值

输出格式：用中文逗号分隔，5-7个知识点
示例：什么是变量, 变量的命名规则, 常见数据类型, 变量赋值操作, 变量在计算中的应用, 综合练习

直接输出知识点列表："""
        
        result = _call_ai_assist(prompt)
        keypoints_str = result.strip()
        key_points = [kp.strip() for kp in re.split(r'[,，]', keypoints_str) if kp.strip()]
        
        return SuggestKeyPointsResponse(
            key_points=key_points,
            message="AI 推荐的知识点已生成"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_ERROR", "message": f"推荐失败: {str(e)}"}
        )


@router.post("/ai/suggest-audience", response_model=SuggestAudienceResponse)
async def suggest_audience(
    request: SuggestAudienceRequest,
    current_user: str = Depends(get_current_user),
) -> SuggestAudienceResponse:
    """AI suggest target audience for teaching topic."""
    topic = request.topic.strip()
    if not topic:
        return SuggestAudienceResponse(target_audience="")
    
    try:
        prompt = f"""分析教学主题「{topic}」，推荐最精准的目标受众。

分析维度：
1. 这个主题需要什么前置知识？（决定受众的知识基础）
2. 学完后能解决什么问题？（决定受众的需求场景）
3. 内容的难度和深度适合谁？（决定受众的认知水平）

输出要求：
- 明确年龄段或学习阶段（如：小学3-6年级、编程零基础者）
- 可以补充具体特征（如：对XX感兴趣的、想要学习XX的）
- 控制在15字以内

示例：
- "Python入门" → "编程零基础的大学生或职场新人"
- "小学英语单词" → "小学1-3年级学生"
- "投资理财" → "有稳定收入的职场人士"

直接输出目标受众："""
        
        result = _call_ai_assist(prompt)
        audience = result.strip().strip('"').strip("'")
        return SuggestAudienceResponse(target_audience=audience)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_ERROR", "message": f"推荐失败: {str(e)}"}
        )


class RandomTopicRequest(BaseModel):
    """Request model for AI random topic generation."""
    style: Optional[str] = "teaching"
    custom_style_description: Optional[str] = None


@router.post("/ai/random-topic", response_model=RandomTopicResponse)
async def generate_random_topic(
    request: RandomTopicRequest = RandomTopicRequest(),
    current_user: str = Depends(get_current_user),
) -> RandomTopicResponse:
    """AI generate random teaching topic based on video style."""
    
    # 根据风格选择不同的主题类型和年龄段
    if request.style == "nursery_rhyme":
        # 儿歌风格 - 英语儿歌教学
        grade_options = [
            ("幼儿园小班", "3-4岁儿童"),
            ("幼儿园中班", "4-5岁儿童"),
            ("幼儿园大班", "5-6岁儿童"),
            ("小学1-2年级", "6-8岁儿童"),
        ]
        topic_types = [
            "英语数字儿歌（One, Two, Three...）",
            "英语字母儿歌（ABC Song学习）",
            "英语颜色儿歌（Red, Yellow, Blue等基础颜色）",
            "英语动物儿歌（动物名称和叫声的英语表达）",
            "英语身体部位儿歌（Head, Shoulders, Knees and Toes）",
            "英语家庭成员儿歌（Family Song - Father, Mother等）",
            "英语交通工具儿歌（Car, Bus, Train等）",
            "英语水果儿歌（Apple, Banana, Orange等）",
            "英语天气儿歌（Sunny, Rainy, Snowy等）",
            "英语节日儿歌（Christmas, New Year等节日英语）",
        ]
    elif request.style == "storybook":
        # 读绘本/故事风格 - 英语故事教学
        grade_options = [
            ("幼儿园大班", "5-6岁儿童"),
            ("小学1-2年级", "6-8岁儿童"),
            ("小学3-4年级", "8-10岁儿童"),
            ("小学5-6年级", "10-12岁儿童"),
        ]
        topic_types = [
            "经典英语童话故事（Three Little Pigs, Little Red Riding Hood等）",
            "英语寓言故事（The Tortoise and the Hare等）",
            "英语绘本阅读（Pete the Cat, Brown Bear等经典绘本）",
            "英语科普故事（动物习性的英语表达）",
            "英语品德故事（关于诚实、友善的英语故事）",
            "英语冒险故事（小探险家的英语表达）",
            "英语友谊故事（朋友间的英语对话）",
            "英语环保故事（保护地球的英语词汇）",
            "英语文化故事（西方文化背景故事）",
            "英语节日故事（Christmas, Halloween等节日故事）",
        ]
    elif request.style == "recitation":
        # 朗诵风格 - 英语诗歌朗诵教学
        grade_options = [
            ("小学3-4年级", "8-10岁儿童"),
            ("小学5-6年级", "10-12岁儿童"),
            ("初一", "12-13岁学生"),
            ("初二", "13-14岁学生"),
            ("初三", "14-15岁学生"),
        ]
        topic_types = [
            "经典英语诗歌朗诵（Twinkle Twinkle Little Star等）",
            "英语童谣朗诵（Mother Goose Rhymes）",
            "英语散文朗诵（简单的英语美文）",
            "英语爱国诗歌朗诵（关于国家的英语表达）",
            "英语励志诗歌朗诵（激励性的英语诗歌）",
            "英语自然诗歌朗诵（描写自然的英语词汇）",
            "英语情感诗歌朗诵（表达情感的英语句式）",
            "英语友谊诗歌朗诵（友情相关的英语表达）",
            "英语季节诗歌朗诵（四季的英语描述）",
            "英语节日诗歌朗诵（节日相关的英语诗歌）",
        ]
    elif request.style == "custom" and request.custom_style_description:
        # 自定义风格 - 仍以英语教学为主
        grade_options = [
            ("小学1-2年级", "6-8岁儿童"),
            ("小学3-4年级", "8-10岁儿童"),
            ("小学5-6年级", "10-12岁儿童"),
            ("初中", "12-15岁学生"),
        ]
        topic_types = [f"符合'{request.custom_style_description}'风格的英语教学内容"]
    else:
        # 默认教学风格 - 传统英语教学
        grade_options = [
            ("小学1-2年级", "6-8岁儿童"),
            ("小学3-4年级", "8-10岁儿童"),
            ("小学5-6年级", "10-12岁儿童"),
            ("初一", "12-13岁学生"),
            ("初二", "13-14岁学生"),
            ("初三", "14-15岁学生"),
            ("高一", "15-16岁学生"),
            ("高二", "16-17岁学生"),
            ("高三", "17-18岁学生"),
        ]
        topic_types = [
            "词汇学习（如动物、食物、职业、运动、节日等具体场景词汇）",
            "语法知识（如时态、句型、从句、语态等）",
            "口语表达（如日常对话、情景交际、自我介绍等）",
            "英语歌曲赏析与学习",
            "英语动画/电影片段学习",
            "英美文化知识（如节日、习俗、名人等）",
            "英语绘本/故事阅读",
            "趣味英语游戏与活动",
            "英语写作技巧",
            "英语听力训练",
            "自然拼读/音标学习",
            "英语谚语/俚语学习",
        ]
    
    grade, age_desc = random.choice(grade_options)
    topic_type = random.choice(topic_types)
    
    # 根据风格生成不同的提示词
    style_descriptions = {
        "teaching": "教学风格：知识讲解、循序渐进、互动问答",
        "nursery_rhyme": "儿歌风格：韵律节奏、重复记忆、欢快氛围，以活泼的语音朗读方式呈现",
        "storybook": "读绘本/故事风格：故事情节、角色对话、情感起伏",
        "recitation": "朗诵风格：情感表达、节奏把控、意境营造",
        "custom": f"自定义风格：{request.custom_style_description}" if request.custom_style_description else "自定义风格"
    }
    
    style_desc = style_descriptions.get(request.style, style_descriptions["teaching"])
    
    try:
        prompt = f"""你是一位创意英语教育专家，请为{grade}（{age_desc}）的学生生成一个关于"{topic_type}"的具体英语教学主题。

视频风格要求：{style_desc}

重要要求：
1. 所有内容必须用中文回复，包括主题和知识点
2. 主题必须是英语教学相关，适合该年龄段和视频风格
3. 不要太宽泛，要有明确的英语学习内容
4. 适合制作3-5分钟的英语教学视频
5. 知识点要符合该年级的英语水平和选择的视频风格
6. 知识点用中文描述，涉及的英语单词用括号标注

示例格式：
- 教学风格示例："趣味动物园：学习10个常见动物的英语名称"
- 儿歌风格示例："英语数字儿歌：1-10的英语表达和韵律"
- 故事风格示例："三只小猪英语故事：学习房屋材料词汇"
- 朗诵风格示例："Twinkle Twinkle Little Star：英语童谣朗诵与词汇学习"

请按以下 JSON 格式返回（不要其他内容，全部用中文）：
{{
  "topic": "中文主题名称（必须包含英语教学内容）",
  "target_audience": "{grade}学生",
  "key_points": ["中文知识点1（包含英语词汇）", "中文知识点2（包含英语词汇）", "中文知识点3（包含英语词汇）", "中文知识点4（包含英语词汇）"]
}}"""
        
        result = _call_ai_assist(prompt, temperature=0.95)
        result_text = result.strip()
        
        # Parse JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()
        
        data = json.loads(result_text)
        
        return RandomTopicResponse(
            topic=data.get("topic", ""),
            target_audience=data.get("target_audience", f"{grade}学生"),
            key_points=data.get("key_points", [])
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_ERROR", "message": "AI 返回格式错误，请重试"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_ERROR", "message": f"生成失败: {str(e)}"}
        )
