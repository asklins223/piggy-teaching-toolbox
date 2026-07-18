"""Style template management for video generation.

This module provides style-specific prompt templates for different video styles,
enabling the ScriptPlanner to generate content tailored to each style.

支持新的场景描述格式：
- image_prompt: 图片生成描述（构图、光线、色调等）
- video_prompt: 视频生成描述（运镜、转场等）

Requirements: 2.1-2.5, 6.1
"""

from backend.schemas.models import VideoStyle


# 通用的场景描述格式说明
SCENE_FORMAT_GUIDE = """
### 场景描述格式（重要！）

#### image_prompt（图片生成描述）
用于AI图片生成，需要包含：
- 角色：动作、表情、位置、服装细节
- 构图：景别（特写/中景/全景）、视角（平视/俯视/仰视）
- 环境：背景、道具、物品
- 光线：光源方向、明暗对比、光线质感
- 色调：整体色彩氛围、主色调
- 风格：卡通/写实/扁平化/水彩等
至少80字，越详细越好。

#### video_prompt（视频生成描述）
用于视频生成，需要包含：
- 运镜：推（zoom in）/拉（zoom out）/摇（pan）/移（dolly）/跟（follow）/升（crane up）/降（crane down）
- 镜头速度：快速/缓慢/匀速
- 画面动态：角色动作、物体运动、环境变化
- 转场建议：淡入淡出/切换/滑动/溶解等
- 特效：粒子/光效/模糊等（可选）
至少50字。

### 旁白长度控制（根据时长，按 2.5-3.5 字/秒估算）
- 5秒：12-18字
- 8秒：20-28字
- 10秒：25-35字
- 12秒：30-42字
- 15秒：38-52字
"""


# 通用的输出格式说明
OUTPUT_FORMAT = """
## 输出格式
请以 JSON 格式回复，结构如下：
{{
    "title": "视频标题",
    "scenes": [
        {{
            "image_prompt": "详细的图片生成描述，包括角色、构图、环境、光线、色调等，至少80字",
            "video_prompt": "详细的视频生成描述，包括运镜、镜头速度、画面动态、转场等，至少50字",
            "narration_cn": "中文旁白（根据时长控制字数）",
            "narration_en": "English narration",
            "duration_seconds": 10,
            "emotion": "平静",
            "character_ids": ["char_xxx"],
            "audio_params": {{
                "emotion": "平静",
                "emotion_strength": 0.6,
                "speed": 1.0,
                "volume": 1.0
            }}
        }}
    ]
}}

请创建分镜脚本："""


# =============================================================================
# Teaching Style Template (教学风格)
# =============================================================================

TEACHING_TEMPLATE = """你是一位专业的儿童教学内容创作专家，擅长制作引人入胜、内容丰富的教学视频。

你的任务是根据以下信息为教学视频创建**详细、完整、连贯**的分镜脚本：

## 教学目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键知识点：{key_points}

{characters_section}

## 核心要求

### 1. 教学风格特点
- **知识点讲解**：清晰、准确、循序渐进
- **互动问答**：适时提问，引导思考
- **实践演示**：通过示例加深理解
- **总结回顾**：强化记忆，巩固学习

### 2. 内容完整性（最重要！）
- **必须详细展开每个知识点**，不能跳跃或省略
- 每个知识点至少需要2-3个分镜来充分讲解
- 内容要有**起承转合**：开场引入 → 逐个知识点讲解 → 实践/互动 → 总结回顾
- 分镜之间要有**自然的过渡**，不能突然跳转

### 3. 分镜数量和时长
- 分镜数量根据内容需要灵活调整，通常需要 **5-20 个分镜**
- 每个分镜时长根据内容复杂度选择：**5秒、8秒、10秒、12秒或15秒**
- **时长要有变化**，不要所有分镜都用同一个时长

### 4. 双语旁白
- 每个分镜必须同时包含**中文旁白**和**英文旁白**
- 英文旁白不是简单翻译，要自然流畅
- 旁白要具体、生动，不能太笼统
""" + SCENE_FORMAT_GUIDE + OUTPUT_FORMAT


# =============================================================================
# Nursery Rhyme Style Template (儿歌风格)
# =============================================================================

NURSERY_RHYME_TEMPLATE = """你是一位专业的儿童内容创作专家，擅长创作儿歌类视频内容。

**重要说明**：当前系统使用语音朗读（TTS）技术，不支持唱歌。儿歌内容将以**活泼、有节奏感的朗读方式**呈现。

你的任务是根据以下信息为儿歌视频创建**活泼、有韵律、易记忆**的分镜脚本：

## 内容目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键内容：{key_points}

{characters_section}

## 核心要求

### 1. 儿歌风格特点
- **韵律节奏**：语言要有节奏感，朗朗上口
- **重复记忆**：关键词句适当重复，便于记忆
- **欢快氛围**：整体基调活泼、欢快
- **简单易懂**：用词简单，适合儿童理解
- **动作配合**：描述可配合动作的场景

### 2. 内容结构
- 开场：活泼的引入，吸引注意力
- 主体：分段呈现儿歌内容，每段有重复的节奏
- 互动：加入拍手、跺脚等动作提示
- 结尾：欢快的收尾，可以重复主题句

### 3. 分镜数量和时长
- 分镜数量根据儿歌长度调整，通常 **5-15 个分镜**
- 每个分镜时长：**5秒、8秒、10秒、12秒或15秒**
- 节奏感强的部分用较短时长
""" + SCENE_FORMAT_GUIDE + OUTPUT_FORMAT


# =============================================================================
# Storybook Style Template (读绘本/故事风格)
# =============================================================================

STORYBOOK_TEMPLATE = """你是一位专业的儿童故事创作专家，擅长绘本和故事类视频内容。

你的任务是根据以下信息为故事视频创建**引人入胜、情感丰富、画面感强**的分镜脚本：

## 故事目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键内容：{key_points}

{characters_section}

## 核心要求

### 1. 故事风格特点
- **故事情节**：有起承转合，情节引人入胜
- **角色对话**：生动的角色对话，展现性格
- **情感起伏**：情感变化丰富，引起共鸣
- **画面感强**：场景描述具体，便于想象
- **寓意深刻**：故事蕴含教育意义

### 2. 内容结构
- 开场：设定场景，介绍主角
- 发展：展开故事情节，制造悬念
- 高潮：情节转折，情感高峰
- 结局：圆满收尾，点明寓意

### 3. 分镜数量和时长
- 分镜数量根据故事长度调整，通常 **5-20 个分镜**
- 每个分镜时长：**5秒、8秒、10秒、12秒或15秒**
- 对话场景用较短时长，情感场景可以稍长
""" + SCENE_FORMAT_GUIDE + OUTPUT_FORMAT


# =============================================================================
# Recitation Style Template (朗诵风格)
# =============================================================================

RECITATION_TEMPLATE = """你是一位专业的朗诵内容创作专家，擅长诗歌和散文朗诵类视频内容。

你的任务是根据以下信息为朗诵视频创建**情感真挚、意境优美、节奏分明**的分镜脚本：

## 朗诵目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键内容：{key_points}

{characters_section}

## 核心要求

### 1. 朗诵风格特点
- **情感表达**：情感真挚，感染力强
- **节奏把控**：语速变化，抑扬顿挫
- **意境营造**：画面优美，意境深远
- **语言优美**：用词考究，富有文采
- **停顿留白**：适当停顿，给予想象空间

### 2. 内容结构
- 开篇：营造氛围，引入主题
- 展开：层层递进，情感渐浓
- 高潮：情感迸发，意境升华
- 收尾：余韵悠长，引人回味

### 3. 分镜数量和时长
- 分镜数量根据内容长度调整，通常 **5-15 个分镜**
- 每个分镜时长：**5秒、8秒、10秒、12秒或15秒**
- 情感高潮处可以用较长时长
""" + SCENE_FORMAT_GUIDE + OUTPUT_FORMAT


# =============================================================================
# Custom Style Template (自定义风格)
# =============================================================================

CUSTOM_TEMPLATE = """你是一位专业的视频内容创作专家，能够根据用户需求创作各种风格的视频内容。

用户希望创作的风格是：**{custom_style_description}**

请根据用户描述的风格特点，创作符合该风格的分镜脚本。

## 内容目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键内容：{key_points}

{characters_section}

## 核心要求

### 1. 风格适配
- 仔细理解用户描述的风格特点
- 在内容、语言、节奏上体现该风格
- 保持风格的一致性

### 2. 内容完整性
- 内容要完整，有清晰的结构
- 分镜之间要有自然的过渡
- 确保所有关键内容都被覆盖

### 3. 分镜数量和时长
- 分镜数量根据内容需要灵活调整
- 每个分镜时长：**5秒、8秒、10秒、12秒或15秒**
- 根据风格特点调整节奏
""" + SCENE_FORMAT_GUIDE + OUTPUT_FORMAT


# =============================================================================
# Style Template Manager
# =============================================================================

class StyleTemplateManager:
    """风格模板管理器
    
    管理和提供不同视频风格的提示词模板。
    """
    
    TEMPLATES = {
        VideoStyle.TEACHING: TEACHING_TEMPLATE,
        VideoStyle.NURSERY_RHYME: NURSERY_RHYME_TEMPLATE,
        VideoStyle.STORYBOOK: STORYBOOK_TEMPLATE,
        VideoStyle.RECITATION: RECITATION_TEMPLATE,
        VideoStyle.CUSTOM: CUSTOM_TEMPLATE,
    }
    
    STYLE_INFO = [
        {"id": "teaching", "name": "教学", "description": "知识讲解、循序渐进、互动问答", "icon": "📚"},
        {"id": "nursery_rhyme", "name": "儿歌", "description": "韵律节奏、欢快活泼、重复记忆", "icon": "🎵"},
        {"id": "storybook", "name": "读绘本/故事", "description": "故事情节、角色对话、情感起伏", "icon": "📖"},
        {"id": "recitation", "name": "朗诵", "description": "情感表达、节奏把控、意境营造", "icon": "🎭"},
        {"id": "custom", "name": "自定义", "description": "自由定义风格，AI根据描述调整", "icon": "✨"},
    ]
    
    @classmethod
    def get_template(cls, style: VideoStyle) -> str:
        """获取指定风格的提示词模板"""
        return cls.TEMPLATES.get(style, cls.TEMPLATES[VideoStyle.TEACHING])
    
    @classmethod
    def get_all_styles(cls) -> list[dict]:
        """获取所有可用风格列表"""
        return cls.STYLE_INFO.copy()
    
    @classmethod
    def get_style_by_id(cls, style_id: str) -> dict | None:
        """根据ID获取风格信息"""
        for style_info in cls.STYLE_INFO:
            if style_info["id"] == style_id:
                return style_info.copy()
        return None
    
    @classmethod
    def is_valid_style(cls, style_id: str) -> bool:
        """检查风格ID是否有效"""
        return any(s["id"] == style_id for s in cls.STYLE_INFO)
