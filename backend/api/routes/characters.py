"""Character management API module.

This module provides REST API endpoints for character library management
and project character operations.

Requirements: 3.2
"""

import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.core.generators.character import CharacterGenerator, CharacterGenerationError
from backend.config import get_settings
from backend.services import cos_client
from backend.db.models import get_db, CharacterRecord, ProjectRecord
from backend.schemas.models import CharacterConfig
from backend.db.crud.projects import (
    get_project, add_character_to_project, remove_character_from_project,
    get_project_characters as get_project_chars
)


# Router for character library endpoints
router = APIRouter()

# Router for project character endpoints (to be included in projects router)
project_characters_router = APIRouter()


# Predefined character templates for random generation
# 角色模板分类
ANIMAL_TEMPLATES = [
    {"name": "小橘猫", "description": "可爱卡通风格的拟人化橘色猫咪，圆圆的脸蛋，大大的眼睛，穿着蓝色小背带裤，戴着红色小领结，毛发橘黄色带浅色条纹，全身绒毛蓬松柔软，表情活泼可爱，站立姿态"},
    {"name": "白兔老师", "description": "可爱卡通风格的拟人化白色兔子，长长的竖耳朵带粉色内耳，戴金色圆框眼镜，穿深蓝色小西装配红色领结，一只手拿木质教鞭，毛发雪白蓬松，大眼睛温和有神，站立姿态，和蔼可亲的微笑"},
    {"name": "企鹅博士", "description": "可爱卡通风格的拟人化企鹅，黑白相间的羽毛，全身绒毛蓬松柔软，戴银色圆框眼镜，穿白色实验服，手拿试管，表情认真专注，站立姿态"},
    {"name": "小狐狸", "description": "可爱卡通风格的拟人化红色狐狸，尖尖的耳朵，全身绒毛蓬松柔软，蓬松的大尾巴，穿紫色连帽卫衣，表情机灵狡黠，站立姿态"},
]

PLANT_TEMPLATES = [
    {"name": "向日葵君", "description": "可爱卡通风格的拟人化向日葵，金黄色花瓣围绕着笑脸，戴着绿色小帽子，穿黄色背带裤，绿色的手臂和腿，表情阳光灿烂，站立姿态"},
    {"name": "小蘑菇", "description": "可爱卡通风格的拟人化红白斑点蘑菇，圆圆的红色帽子带白色圆点，白色的身体，细细的手臂和腿，戴着绿色小围巾，表情害羞可爱，站立姿态"},
    {"name": "仙人掌先生", "description": "可爱卡通风格的拟人化仙人掌，绿色圆胖身体，头顶开着粉色小花，戴着墨镜和牛仔帽，表情酷酷的，站立姿态"},
    {"name": "竹子小姐", "description": "可爱卡通风格的拟人化竹子，翠绿色修长身体，头顶有竹叶装饰，穿着中式旗袍，表情优雅温和，站立姿态"},
]

FOOD_TEMPLATES = [
    {"name": "面包超人", "description": "可爱卡通风格的拟人化面包，金黄色圆形身体，表面有烘焙纹理，戴着白色厨师帽，穿红色围裙，表情温暖友善，站立姿态"},
    {"name": "草莓公主", "description": "可爱卡通风格的拟人化草莓，红色心形身体带绿色叶子帽，穿粉色蓬蓬裙，表情甜美可爱，站立姿态"},
    {"name": "甜甜圈", "description": "可爱卡通风格的拟人化甜甜圈，棕色圆环身体，表面有彩色糖霜和彩虹糖粒装饰，戴着彩色小帽子，表情开心活泼，站立姿态"},
    {"name": "冰淇淋宝宝", "description": "可爱卡通风格的拟人化冰淇淋，三层不同颜色的球状身体（粉色、白色、绿色），头顶有樱桃装饰，表情清爽可爱，站立姿态"},
]

OBJECT_TEMPLATES = [
    {"name": "铅笔小弟", "description": "可爱卡通风格的拟人化铅笔，黄色六角形身体，头部是粉色橡皮擦，戴着银色金属帽，穿蓝色小马甲，表情认真专注，站立姿态"},
    {"name": "时钟爷爷", "description": "可爱卡通风格的拟人化时钟，圆形白色表盘身体，黑色数字和指针，戴着金色怀表链，穿深蓝色西装，表情慈祥智慧，站立姿态"},
    {"name": "灯泡博士", "description": "可爱卡通风格的拟人化灯泡，透明玻璃球形头部，内有金色灯丝，戴着黑框眼镜，穿白色实验服，表情聪明睿智，站立姿态"},
    {"name": "书本老师", "description": "可爱卡通风格的拟人化书本，厚厚的蓝色封面身体，金色书脊，戴着圆框眼镜，穿学者袍，表情博学温和，站立姿态"},
]

FANTASY_TEMPLATES = [
    {"name": "小星星", "description": "可爱卡通风格的拟人化五角星，金黄色发光身体，头戴银色小皇冠，穿深蓝色星空斗篷，表情梦幻神秘，站立姿态"},
    {"name": "云朵妹妹", "description": "可爱卡通风格的拟人化白云，蓬松柔软的白色身体，戴着彩虹色发带，穿浅蓝色连衣裙，表情温柔飘逸，站立姿态"},
    {"name": "雨滴弟弟", "description": "可爱卡通风格的拟人化雨滴，透明蓝色水滴形身体，戴着深蓝色小帽子，穿雨衣，表情活泼清新，站立姿态"},
    {"name": "彩虹仙子", "description": "可爱卡通风格的拟人化彩虹，七彩弧形身体，头戴水晶皇冠，穿彩虹色长裙，表情优雅魔幻，站立姿态"},
]

# 合并所有模板
CHARACTER_TEMPLATES = ANIMAL_TEMPLATES + PLANT_TEMPLATES + FOOD_TEMPLATES + OBJECT_TEMPLATES + FANTASY_TEMPLATES


# Request/Response models
class CharacterInfo(BaseModel):
    """Character information model."""
    character_id: str
    name: str
    description: str
    image_url: str
    user_id: Optional[str] = None


class CharacterLibraryResponse(BaseModel):
    """Response model for character library list."""
    characters: list[CharacterInfo]


class GenerateCharacterRequest(BaseModel):
    """Request model for generating a new character."""
    name: str = Field(..., min_length=1, max_length=50, description="Character name")
    description: str = Field(..., min_length=1, max_length=500, description="Character description")


class GenerateCharacterResponse(BaseModel):
    """Response model for character generation."""
    character_id: str
    name: str
    image_url: str


class RandomTemplateResponse(BaseModel):
    """Response model for random character template."""
    name: str
    description: str


class AIGenerateIdeaResponse(BaseModel):
    """Response model for AI generated character idea."""
    name: str
    description: str


class AddCharacterToProjectRequest(BaseModel):
    """Request model for adding a character to a project."""
    character_id: str = Field(..., min_length=1, description="Character ID from library")


class AddCharacterToProjectResponse(BaseModel):
    """Response model for adding character to project."""
    success: bool


class ProjectCharactersResponse(BaseModel):
    """Response model for project characters list."""
    characters: list[CharacterInfo]


class DeleteCharacterResponse(BaseModel):
    """Response model for deleting a character."""
    success: bool


# Helper functions
def generate_character_id() -> str:
    """Generate a unique character ID."""
    timestamp = int(datetime.now().timestamp())
    random_suffix = random.randint(1000, 9999)
    return f"char_{timestamp}_{random_suffix}"


# Character Library API Endpoints
@router.get("/library", response_model=CharacterLibraryResponse)
async def get_character_library(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CharacterLibraryResponse:
    """Get list of all characters in the library (shared across all users).
    
    Returns a list of characters with their IDs, names, descriptions, and image URLs.
    """
    records = db.query(CharacterRecord).order_by(
        CharacterRecord.created_at.desc()
    ).all()
    
    characters = [
        CharacterInfo(
            character_id=r.character_id,
            name=r.name,
            description=r.description or "",
            image_url=r.cos_url or "",
            user_id=r.user_id
        )
        for r in records
    ]
    
    return CharacterLibraryResponse(characters=characters)


@router.post("/generate", response_model=GenerateCharacterResponse)
async def generate_character(
    request: GenerateCharacterRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerateCharacterResponse:
    """Generate a new character and add it to the library.
    
    Uses AI to generate a character image based on the provided name and description.
    Stores the image in COS and saves metadata to database.
    """
    import tempfile
    import shutil
    
    # Generate character ID
    character_id = generate_character_id()
    
    # Create character config
    config = CharacterConfig(
        name=request.name,
        description=request.description
    )
    
    # Create temporary directory for generation
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate character image
        generator = CharacterGenerator(output_dir=temp_dir)
        
        try:
            char_ref = await generator.generate_character(config)
            
            # Read the generated image
            image_path = Path(char_ref.image_path)
            image_data = image_path.read_bytes()
            
            # Upload to COS
            cos_result = cos_client.upload_file(
                file_data=image_data,
                filename=f"{character_id}.png",
                folder="characters",
                content_type="image/png"
            )
            
            if not cos_result:
                raise Exception("上传图片到 COS 失败")
            
            cos_url = cos_result["cos_url"]
            cos_key = cos_result["cos_key"]
            
            # Save to database
            record = CharacterRecord(
                character_id=character_id,
                name=request.name,
                description=request.description,
                user_id=current_user,
                cos_url=cos_url,
                cos_key=cos_key,
            )
            db.add(record)
            db.commit()
            
            return GenerateCharacterResponse(
                character_id=character_id,
                name=request.name,
                image_url=cos_url
            )
            
        finally:
            await generator.close()
            
    except CharacterGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CHARACTER_GENERATION_FAILED",
                "message": f"生成角色失败: {e.reason}"
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CHARACTER_GENERATION_FAILED",
                "message": f"生成角色失败: {str(e)}"
            }
        )
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.delete("/{character_id}", response_model=DeleteCharacterResponse)
async def delete_character(
    character_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteCharacterResponse:
    """Delete a character from the library.
    
    Removes the character from database and deletes the image from COS.
    Only the owner can delete their own characters.
    """
    # Find character
    record = db.query(CharacterRecord).filter(
        CharacterRecord.character_id == character_id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CHARACTER_NOT_FOUND",
                "message": f"角色 {character_id} 不存在"
            }
        )
    
    # Check ownership
    if record.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "无权删除此角色"
            }
        )
    
    # Delete from COS
    if record.cos_key:
        try:
            cos_client.delete_file(record.cos_key)
        except Exception:
            pass  # Ignore COS deletion errors
    
    # Delete from database
    db.delete(record)
    db.commit()
    
    return DeleteCharacterResponse(success=True)


@router.get("/random-template", response_model=RandomTemplateResponse)
async def get_random_template(
    current_user: str = Depends(get_current_user),
) -> RandomTemplateResponse:
    """Get a random character template.
    
    Returns a random predefined character template with name and description
    that can be used to generate a new character. Now includes diverse character types.
    """
    # 随机选择不同类型的模板，增加多样性
    template_categories = [ANIMAL_TEMPLATES, PLANT_TEMPLATES, FOOD_TEMPLATES, OBJECT_TEMPLATES, FANTASY_TEMPLATES]
    selected_category = random.choice(template_categories)
    template = random.choice(selected_category)
    
    return RandomTemplateResponse(
        name=template["name"],
        description=template["description"]
    )


@router.post("/ai-generate-idea", response_model=AIGenerateIdeaResponse)
async def ai_generate_character_idea(
    current_user: str = Depends(get_current_user),
) -> AIGenerateIdeaResponse:
    """AI generate a creative character idea.
    
    Uses AI to generate a unique character name and description
    for cartoon-style, cute, and funny characters.
    """
    import dashscope
    from dashscope import Generation
    from backend.config import get_settings
    import logging
    
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # 随机选择角色类型，增加多样性
    character_types = [
        "拟人化的动物（如海洋动物、昆虫、鸟类等）",
        "拟人化的植物（如花朵、树木、蔬菜、水果等）", 
        "拟人化的食物（如甜点、饮品、主食、零食等）",
        "拟人化的日常物品（如文具、家具、电器、玩具等）",
        "拟人化的自然元素（如天气、星球、宝石、元素等）",
        "拟人化的交通工具（如汽车、飞机、船只等）",
        "拟人化的建筑物（如房屋、城堡、桥梁等）"
    ]
    
    selected_type = random.choice(character_types)
    
    prompt = f"""你是一个创意角色设计师，请为教学视频设计一个可爱有趣的卡通角色。

本次设计要求：
角色类型：{selected_type}

设计要求：
1. 风格：可爱、卡通、适合儿童和青少年
2. 性格：有趣、友善、有独特个性
3. 创意：避免常见设计，要有新颖的创意点
4. 教育性：适合在教学视频中出现，能吸引学生注意力

请生成一个独特的角色，严格按照以下格式输出：
角色名称：xxx
角色描述：xxx

注意：
- 角色名称2-4个字，朗朗上口，有趣好记
- 角色描述60-120字，详细描述外观特征，包括：整体风格、主要颜色、服装配饰、面部表情、身体姿态、特殊标识等
- 描述要生动具体，便于AI绘图生成
- 只输出这两行，不要其他内容"""

    try:
        dashscope.api_key = settings.dashscope.api_key
        
        response = Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=500,
            result_format='message'
        )
        
        if response.status_code != 200:
            logger.error(f"DashScope API error: {response.code} - {response.message}")
            raise Exception(f"API error: {response.message}")
        
        content = response.output.choices[0].message.content.strip()
        logger.info(f"AI response: {content}")
        
        # Parse response - try multiple patterns
        name = ""
        description = ""
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Try different patterns
            if '角色名称' in line:
                # Remove prefix and get value
                parts = line.replace('角色名称', '').strip()
                parts = parts.lstrip('：:').strip()
                name = parts
            elif '角色描述' in line:
                parts = line.replace('角色描述', '').strip()
                parts = parts.lstrip('：:').strip()
                description = parts
        
        logger.info(f"Parsed - name: {name}, description: {description[:50] if description else 'empty'}...")
        
        # If we got valid results, return them
        if name and description and len(name) >= 2 and len(description) >= 20:
            return AIGenerateIdeaResponse(name=name, description=description)
        
        # Fallback if parsing fails - 随机选择不同类型的模板
        logger.warning(f"Parsing failed, using fallback. name={name}, desc_len={len(description) if description else 0}")
        
        # 随机选择模板类型，增加多样性
        template_categories = [ANIMAL_TEMPLATES, PLANT_TEMPLATES, FOOD_TEMPLATES, OBJECT_TEMPLATES, FANTASY_TEMPLATES]
        selected_category = random.choice(template_categories)
        template = random.choice(selected_category)
        
        return AIGenerateIdeaResponse(
            name=template["name"],
            description=template["description"]
        )
        
    except Exception as e:
        logger.error(f"AI generate idea error: {str(e)}")
        # Fallback to random template on error - 随机选择不同类型的模板
        template_categories = [ANIMAL_TEMPLATES, PLANT_TEMPLATES, FOOD_TEMPLATES, OBJECT_TEMPLATES, FANTASY_TEMPLATES]
        selected_category = random.choice(template_categories)
        template = random.choice(selected_category)
        
        return AIGenerateIdeaResponse(
            name=template["name"],
            description=template["description"]
        )


# Project Character API Endpoints
@project_characters_router.post("/{project_id}/characters", response_model=AddCharacterToProjectResponse)
async def add_character_to_project_endpoint(
    project_id: str,
    request: AddCharacterToProjectRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AddCharacterToProjectResponse:
    """Add a character from the library to a project."""
    # Check if project exists
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在"
            }
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "无权操作此项目"
            }
        )
    
    # Check if character exists in database
    record = db.query(CharacterRecord).filter(
        CharacterRecord.character_id == request.character_id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CHARACTER_NOT_FOUND",
                "message": f"角色 {request.character_id} 不存在"
            }
        )
    
    # Add character to project
    add_character_to_project(db, project_id, request.character_id)
    
    return AddCharacterToProjectResponse(success=True)


@project_characters_router.get("/{project_id}/characters", response_model=ProjectCharactersResponse)
async def get_project_characters_endpoint(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectCharactersResponse:
    """Get list of characters in a project."""
    # Check if project exists
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在"
            }
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "无权访问此项目"
            }
        )
    
    # Get characters
    records = get_project_chars(db, project_id)
    
    characters = [
        CharacterInfo(
            character_id=r.character_id,
            name=r.name,
            description=r.description or "",
            image_url=r.cos_url or ""
        )
        for r in records
    ]
    
    return ProjectCharactersResponse(characters=characters)


class RemoveCharacterResponse(BaseModel):
    """Response model for removing character from project."""
    success: bool


@project_characters_router.delete("/{project_id}/characters/{character_id}", response_model=RemoveCharacterResponse)
async def remove_character_from_project_endpoint(
    project_id: str,
    character_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemoveCharacterResponse:
    """Remove a character from a project."""
    # Check if project exists
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在"
            }
        )
    
    # Check ownership
    if project.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "无权操作此项目"
            }
        )
    
    # Remove character from project
    remove_character_from_project(db, project_id, character_id)
    
    return RemoveCharacterResponse(success=True)
