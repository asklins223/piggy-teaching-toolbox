"""Script planner module for generating teaching storyboards.

This module uses DashScope (Alibaba Cloud) with qwen3-max to convert teaching goals into
structured storyboards with scenes that can be used for video generation.

支持两阶段生成：
1. 生成分镜大纲（简短流程）
2. 逐个详细补充每个分镜内容

Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 5.1, 5.3, 6.1, 6.2, 6.3, 6.5
"""

import uuid
import json
from typing import Optional, List
import dashscope
from dashscope import Generation

from backend.schemas.models import (
    AudioParams,
    CharacterReference,
    Scene,
    Storyboard,
    TeachingGoal,
    SceneDuration,
    Emotion,
    VideoStyle,
)
from backend.core.style_templates import StyleTemplateManager


# 旁白字数参考（根据时长，按 2.5-3.5 字/秒估算）
NARRATION_LENGTH_GUIDE = {
    5: "12-18字",   # 5秒：简短
    8: "20-28字",   # 8秒：简短讲解
    10: "25-35字",  # 10秒：标准讲解
    12: "30-42字",  # 12秒：详细讲解
    15: "38-52字",  # 15秒：复杂内容
}


# 第一阶段：生成分镜大纲
OUTLINE_PROMPT_TEMPLATE = """你是一位专业的儿童教学内容创作专家。

请根据以下信息，为教学视频创建一个**简短的分镜大纲**：

## 教学目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键知识点：{key_points}

## 角色设定
{characters_description}

## 要求
1. 创建 5-20 个分镜的大纲
2. 每个分镜只需要：简短标题（5-10字）+ 时长（5/8/10/12/15秒）
3. 内容要有起承转合：开场引入 → 逐个知识点讲解 → 实践/互动 → 总结回顾
4. 时长要有变化，根据内容复杂度选择

## 输出格式
请以 JSON 格式回复：
{{
    "title": "视频标题",
    "outline": [
        {{"title": "开场欢迎", "duration": 8}},
        {{"title": "介绍苹果", "duration": 10}},
        ...
    ]
}}

请创建分镜大纲："""


# 第二阶段：详细补充单个分镜
DETAIL_SCENE_PROMPT_TEMPLATE = """你是一位专业的儿童教学内容创作专家。

请根据以下信息，为这个分镜创建**详细内容**：

## 视频信息
- 主题：{topic}
- 目标受众：{target_audience}
- 视频风格：{style}

## 角色设定
{characters_description}

## 当前分镜
- 分镜序号：{step_number}/{total_steps}
- 分镜标题：{scene_title}
- 时长：{duration}秒
- 上一个分镜：{prev_scene}
- 下一个分镜：{next_scene}

## 旁白长度要求
根据{duration}秒时长，旁白应控制在 **{narration_length}** 左右。

## 输出要求

### 1. 图片生成描述 (image_prompt)
用于AI图片生成，需要包含：
- 角色：动作、表情、位置、服装
- 构图：景别（特写/中景/全景）、视角（平视/俯视/仰视）
- 环境：背景、道具、物品
- 光线：光源方向、明暗对比
- 色调：整体色彩氛围
- 风格：卡通/写实/扁平化等
至少80字，越详细越好。

### 2. 视频生成描述 (video_prompt)
用于视频生成，需要包含：
- 运镜：推/拉/摇/移/跟/升/降/甩
- 镜头速度：快速/缓慢/匀速
- 画面动态：角色动作、物体运动
- 转场建议：淡入淡出/切换/滑动等
- 特效：粒子/光效/模糊等（可选）
至少50字。

### 3. 旁白
- 中文旁白：生动具体，符合目标受众
- 英文旁白：自然流畅，不是简单翻译

## 输出格式
请以 JSON 格式回复：
{{
    "image_prompt": "详细的图片生成描述...",
    "video_prompt": "详细的视频生成描述...",
    "narration_cn": "中文旁白",
    "narration_en": "English narration",
    "emotion": "平静",
    "character_ids": ["char_xxx"],
    "audio_params": {{
        "emotion": "calm",
        "emotion_strength": 0.6,
        "speed": 1.0,
        "volume": 1.0
    }}
}}

请创建详细分镜内容："""


# 兼容旧版：一次性生成所有分镜（保留原有功能）
STORYBOARD_PROMPT_TEMPLATE = """你是一位专业的儿童教学内容创作专家，擅长制作引人入胜、内容丰富的教学视频。

你的任务是根据以下信息为教学视频创建**详细、完整、连贯**的分镜脚本：

## 教学目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键知识点：{key_points}

## 角色设定
{characters_description}

## 核心要求

### 1. 内容完整性（最重要！）
- **必须详细展开每个知识点**，不能跳跃或省略
- 每个知识点至少需要2-3个分镜来充分讲解
- 内容要有**起承转合**：开场引入 → 逐个知识点讲解 → 实践/互动 → 总结回顾
- 分镜之间要有**自然的过渡**，不能突然跳转

### 2. 分镜数量和时长
- 分镜数量根据内容需要灵活调整，通常需要 **10-20 个分镜**
- 每个分镜时长根据内容复杂度选择：**5秒、8秒、10秒、12秒或15秒**
- **时长要有变化**，不要所有分镜都用同一个时长

### 3. 旁白长度控制（重要！）
根据分镜时长控制旁白字数：
- 5秒：15-25字
- 8秒：25-40字
- 10秒：35-50字
- 12秒：45-65字
- 15秒：55-80字

### 4. 场景描述（拆分为图片和视频两部分）

#### image_prompt（图片生成描述）
用于AI图片生成，需要包含：
- 角色：动作、表情、位置、服装
- 构图：景别（特写/中景/全景）、视角
- 环境：背景、道具、物品
- 光线：光源方向、明暗对比
- 色调：整体色彩氛围
至少80字。

#### video_prompt（视频生成描述）
用于视频生成，需要包含：
- 运镜：推/拉/摇/移/跟/升/降
- 镜头速度：快速/缓慢/匀速
- 画面动态：角色动作、物体运动
- 转场建议：淡入淡出/切换等
至少50字。

## 输出格式
请以 JSON 格式回复：
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
                "emotion": "calm",
                "emotion_strength": 0.6,
                "speed": 1.0,
                "volume": 1.0
            }}
        }}
    ]
}}

请创建分镜脚本："""


# 无角色版本
STORYBOARD_PROMPT_NO_CHARS_TEMPLATE = """你是一位专业的儿童教学内容创作专家。

请根据以下信息为教学视频创建分镜脚本：

## 教学目标
- 主题：{topic}
- 目标受众：{target_audience}
- 关键知识点：{key_points}

## 要求
1. 分镜数量：10-20个
2. 时长选择：5/8/10/12/15秒
3. 旁白长度根据时长控制（5秒15-25字，10秒35-50字，15秒55-80字）
4. 场景描述拆分为 image_prompt 和 video_prompt

## 输出格式
{{
    "title": "视频标题",
    "scenes": [
        {{
            "image_prompt": "图片生成描述（构图、光线、色调等）",
            "video_prompt": "视频生成描述（运镜、转场等）",
            "narration_cn": "中文旁白",
            "narration_en": "English narration",
            "duration_seconds": 10,
            "emotion": "平静",
            "audio_params": {{"emotion": "calm", "emotion_strength": 0.6, "speed": 1.0, "volume": 1.0}}
        }}
    ]
}}

请创建分镜脚本："""


REFINE_SCENE_PROMPT_TEMPLATE = """你是一位专业的教学内容创作专家。

你需要根据反馈优化一个分镜。

## 当前分镜
- 图片描述：{image_prompt}
- 视频描述：{video_prompt}
- 中文旁白：{narration_cn}
- 英文旁白：{narration_en}
- 时长：{duration_seconds} 秒
- 情感：{emotion}

## 反馈
{feedback}

## 旁白长度要求
根据{duration_seconds}秒时长，旁白应控制在 **{narration_length}** 左右。

## 输出格式
请以 JSON 格式回复：
{{
    "image_prompt": "优化后的图片生成描述",
    "video_prompt": "优化后的视频生成描述",
    "narration_cn": "优化后的中文旁白",
    "narration_en": "Optimized English narration",
    "duration_seconds": {duration_seconds},
    "emotion": "平静",
    "audio_params": {{
        "emotion": "calm",
        "emotion_strength": 0.6,
        "speed": 1.0,
        "volume": 1.0
    }}
}}

请提供优化后的分镜："""


TRANSLATE_PROMPT_TEMPLATE = """请将以下中文旁白翻译为自然流畅的英文：

中文旁白：{narration_cn}

要求：
1. 保持教学内容的准确性
2. 使用自然流畅的英文表达
3. 适合目标受众理解
4. 保持原文的语调和风格

请直接回复英文翻译，不需要其他格式："""


class ScriptPlanner:
    """Generates teaching storyboards using DashScope qwen3-max.
    
    支持两种生成模式：
    1. 一次性生成：generate_storyboard() - 一次生成所有分镜
    2. 分步生成：generate_outline() + generate_scene_detail() - 先大纲后详情
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 5.1, 5.3, 6.1, 6.2, 6.3, 6.5
    """
    
    def __init__(self, api_key: str):
        """Initialize the script planner."""
        self.api_key = api_key
        dashscope.api_key = api_key
        self.style_manager = StyleTemplateManager()
    
    async def _call_qwen(self, prompt: str) -> str:
        """Call qwen3-max model with the given prompt."""
        import asyncio
        
        def _sync_call():
            response = Generation.call(
                model='qwen-max',
                prompt=prompt,
                temperature=0.7,
                max_tokens=4096
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                raise Exception(f"DashScope API error: {response.message}")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)
    
    def _format_key_points(self, key_points: list[str]) -> str:
        """Format key points for the prompt."""
        if not key_points:
            return "无特定关键点"
        return "、".join(key_points)
    
    def _get_narration_length(self, duration: int) -> str:
        """获取旁白长度建议"""
        return NARRATION_LENGTH_GUIDE.get(duration, "35-50字")
    
    def _get_style_default_params(self, style: VideoStyle) -> dict:
        """获取风格默认音频参数"""
        defaults = {
            VideoStyle.TEACHING: {"emotion": Emotion.CALM, "emotion_strength": 0.5, "speed": 1.0, "volume": 1.0},
            VideoStyle.NURSERY_RHYME: {"emotion": Emotion.LIVELY, "emotion_strength": 0.8, "speed": 1.1, "volume": 1.1},
            VideoStyle.STORYBOOK: {"emotion": Emotion.CALM, "emotion_strength": 0.6, "speed": 0.95, "volume": 1.0},
            VideoStyle.RECITATION: {"emotion": Emotion.CALM, "emotion_strength": 0.7, "speed": 0.9, "volume": 1.0},
            VideoStyle.CUSTOM: {"emotion": Emotion.CALM, "emotion_strength": 0.6, "speed": 1.0, "volume": 1.0},
        }
        return defaults.get(style, defaults[VideoStyle.TEACHING])

    
    def _generate_audio_params(self, scene_data: dict, style: VideoStyle) -> AudioParams:
        """根据分镜内容和风格生成音频参数"""
        default_params = self._get_style_default_params(style)
        ai_audio_params = scene_data.get("audio_params", {})
        
        # Parse emotion
        emotion = default_params["emotion"]
        if ai_audio_params.get("emotion"):
            emotion_str = ai_audio_params["emotion"]
            for e in Emotion:
                if e.value == emotion_str:
                    emotion = e
                    break
        elif scene_data.get("emotion"):
            emotion_str = scene_data["emotion"]
            for e in Emotion:
                if e.value == emotion_str:
                    emotion = e
                    break
        
        emotion_strength = ai_audio_params.get("emotion_strength", default_params["emotion_strength"])
        speed = ai_audio_params.get("speed", default_params["speed"])
        volume = ai_audio_params.get("volume", default_params["volume"])
        
        # Clamp values
        emotion_strength = max(0.0, min(1.0, float(emotion_strength)))
        speed = max(0.5, min(2.0, float(speed)))
        volume = max(0.5, min(1.5, float(volume)))
        
        return AudioParams(emotion=emotion, emotion_strength=emotion_strength, speed=speed, volume=volume)
    
    async def generate_outline(
        self,
        goal: TeachingGoal,
        characters: Optional[List[CharacterReference]] = None,
    ) -> dict:
        """第一阶段：生成分镜大纲
        
        Returns:
            包含 title 和 outline 的字典，outline 是分镜标题和时长的列表
        """
        # Build characters section
        characters_section = ""
        if characters and len(characters) > 0:
            chars_desc_lines = ["以下是视频中的角色："]
            for char in characters:
                chars_desc_lines.append(f"- {char.name} (ID: {char.character_id})")
            characters_section = "\n".join(chars_desc_lines)
        
        prompt = OUTLINE_PROMPT_TEMPLATE.format(
            topic=goal.topic,
            target_audience=goal.target_audience,
            key_points=self._format_key_points(goal.key_points),
            characters_description=characters_section,
        )
        
        response_text = await self._call_qwen(prompt)
        
        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception(f"Failed to parse outline response: {response_text}")
        
        return result

    
    async def generate_scene_detail(
        self,
        goal: TeachingGoal,
        outline: list[dict],
        scene_index: int,
        characters: Optional[List[CharacterReference]] = None,
    ) -> dict:
        """第二阶段：详细补充单个分镜
        
        Args:
            goal: 教学目标
            outline: 分镜大纲列表
            scene_index: 当前分镜索引（从0开始）
            characters: 角色列表
            
        Returns:
            包含详细分镜内容的字典
        """
        current_scene = outline[scene_index]
        duration = current_scene.get("duration", 10)
        
        # Build characters section
        characters_section = ""
        if characters and len(characters) > 0:
            chars_desc_lines = ["以下是视频中的角色："]
            for char in characters:
                chars_desc_lines.append(f"- {char.name} (ID: {char.character_id})")
            characters_section = "\n".join(chars_desc_lines)
        
        # Get prev/next scene info
        prev_scene = outline[scene_index - 1]["title"] if scene_index > 0 else "无（这是第一个分镜）"
        next_scene = outline[scene_index + 1]["title"] if scene_index < len(outline) - 1 else "无（这是最后一个分镜）"
        
        prompt = DETAIL_SCENE_PROMPT_TEMPLATE.format(
            topic=goal.topic,
            target_audience=goal.target_audience,
            style=goal.style.value if goal.style else "teaching",
            characters_description=characters_section,
            step_number=scene_index + 1,
            total_steps=len(outline),
            scene_title=current_scene["title"],
            duration=duration,
            prev_scene=prev_scene,
            next_scene=next_scene,
            narration_length=self._get_narration_length(duration),
        )
        
        response_text = await self._call_qwen(prompt)
        
        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception(f"Failed to parse scene detail response: {response_text}")
        
        # Add duration from outline
        result["duration_seconds"] = duration
        return result

    
    def _parse_scenes(
        self,
        scenes_data: list[dict],
        default_char_ids: list[str],
        characters: Optional[List[CharacterReference]],
        default_duration: SceneDuration,
        style: VideoStyle
    ) -> list[Scene]:
        """解析分镜数据并生成Scene列表"""
        valid_durations = {5, 8, 10, 12, 15}
        duration_map = {
            5: SceneDuration.VERY_SHORT,
            8: SceneDuration.SHORT,
            10: SceneDuration.MEDIUM,
            12: SceneDuration.LONG,
            15: SceneDuration.VERY_LONG,
        }
        
        scenes = []
        for idx, scene_data in enumerate(scenes_data, start=1):
            # Parse duration
            duration_seconds = scene_data.get("duration_seconds", default_duration.value)
            if duration_seconds not in valid_durations:
                duration_seconds = min(valid_durations, key=lambda x: abs(x - duration_seconds))
            duration = duration_map[duration_seconds]
            
            # Parse emotion
            emotion_str = scene_data.get("emotion", "平静")
            emotion = Emotion.CALM
            for e in Emotion:
                if e.value == emotion_str:
                    emotion = e
                    break
            
            # Get character IDs
            scene_char_ids = scene_data.get("character_ids", default_char_ids)
            if characters:
                valid_ids = {c.character_id for c in characters}
                scene_char_ids = [cid for cid in scene_char_ids if cid in valid_ids]
                if not scene_char_ids:
                    scene_char_ids = default_char_ids
            
            # Get prompts - 支持新旧两种格式
            image_prompt = scene_data.get("image_prompt", "")
            video_prompt = scene_data.get("video_prompt", "")
            description_cn = scene_data.get("description_cn", "")
            
            # 兼容旧格式：如果没有新字段，使用 description_cn
            if not image_prompt and description_cn:
                image_prompt = description_cn
            if not description_cn and image_prompt:
                description_cn = image_prompt
            
            # Generate audio params
            audio_params = self._generate_audio_params(scene_data, style)
            
            scene = Scene(
                scene_id=f"scene_{idx:03d}",
                step_number=idx,
                description_cn=description_cn or image_prompt,
                image_prompt=image_prompt,
                video_prompt=video_prompt,
                narration_cn=scene_data.get("narration_cn", ""),
                narration_en=scene_data.get("narration_en", ""),
                duration=duration,
                character_ids=scene_char_ids,
                audio_params=audio_params,
            )
            scenes.append(scene)
        
        return scenes

    
    async def generate_storyboard(
        self,
        goal: TeachingGoal,
        characters: Optional[List[CharacterReference]] = None,
        default_duration: SceneDuration = SceneDuration.SHORT,
        project_id: Optional[str] = None
    ) -> Storyboard:
        """一次性生成完整分镜脚本（兼容旧版）"""
        if project_id is None:
            project_id = f"proj_{uuid.uuid4().hex[:8]}"
        
        # Build characters section
        characters_section = ""
        if characters and len(characters) > 0:
            chars_desc_lines = ["## 角色设定", "以下是视频中的角色："]
            for char in characters:
                chars_desc_lines.append(f"- {char.name} (ID: {char.character_id})")
            characters_section = "\n".join(chars_desc_lines)
        
        # Get style template
        style = goal.style if goal.style else VideoStyle.TEACHING
        template = self.style_manager.get_template(style)
        
        # Format prompt
        if style == VideoStyle.CUSTOM and goal.custom_style_description:
            prompt = template.format(
                topic=goal.topic,
                target_audience=goal.target_audience,
                key_points=self._format_key_points(goal.key_points),
                characters_section=characters_section,
                custom_style_description=goal.custom_style_description,
            )
        else:
            prompt = template.format(
                topic=goal.topic,
                target_audience=goal.target_audience,
                key_points=self._format_key_points(goal.key_points),
                characters_section=characters_section,
            )
        
        response_text = await self._call_qwen(prompt)
        
        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception(f"Failed to parse JSON response: {response_text}")
        
        default_char_ids = [c.character_id for c in (characters or [])]
        scenes = self._parse_scenes(result["scenes"], default_char_ids, characters, default_duration, style)
        total_duration = sum(s.duration.value for s in scenes)
        
        return Storyboard(
            project_id=project_id,
            title=result["title"],
            scenes=scenes,
            total_duration_seconds=total_duration,
        )

    
    async def generate_storyboard_stepwise(
        self,
        goal: TeachingGoal,
        characters: Optional[List[CharacterReference]] = None,
        default_duration: SceneDuration = SceneDuration.SHORT,
        project_id: Optional[str] = None,
        on_progress: Optional[callable] = None
    ) -> Storyboard:
        """分步生成分镜脚本（先大纲后详情）
        
        Args:
            goal: 教学目标
            characters: 角色列表
            default_duration: 默认时长
            project_id: 项目ID
            on_progress: 进度回调函数 (current, total, message)
        """
        if project_id is None:
            project_id = f"proj_{uuid.uuid4().hex[:8]}"
        
        style = goal.style if goal.style else VideoStyle.TEACHING
        
        # 第一阶段：生成大纲
        if on_progress:
            on_progress(0, 100, "正在生成分镜大纲...")
        
        outline_result = await self.generate_outline(goal, characters)
        title = outline_result.get("title", goal.topic)
        outline = outline_result.get("outline", [])
        
        if not outline:
            raise Exception("生成大纲失败：没有分镜")
        
        total_scenes = len(outline)
        if on_progress:
            on_progress(10, 100, f"大纲生成完成，共 {total_scenes} 个分镜")
        
        # 第二阶段：逐个生成详细内容
        scenes_data = []
        for i, scene_outline in enumerate(outline):
            if on_progress:
                progress = 10 + int((i / total_scenes) * 80)
                on_progress(progress, 100, f"正在生成分镜 {i+1}/{total_scenes}: {scene_outline['title']}")
            
            scene_detail = await self.generate_scene_detail(goal, outline, i, characters)
            scene_detail["duration_seconds"] = scene_outline.get("duration", 10)
            scenes_data.append(scene_detail)
        
        # 解析为 Scene 对象
        default_char_ids = [c.character_id for c in (characters or [])]
        scenes = self._parse_scenes(scenes_data, default_char_ids, characters, default_duration, style)
        total_duration = sum(s.duration.value for s in scenes)
        
        if on_progress:
            on_progress(100, 100, "分镜生成完成")
        
        return Storyboard(
            project_id=project_id,
            title=title,
            scenes=scenes,
            total_duration_seconds=total_duration,
        )

    
    async def refine_scene(self, scene: Scene, feedback: str) -> Scene:
        """Refine a single scene based on feedback."""
        emotion_value = "平静"
        if scene.audio_params and scene.audio_params.emotion:
            emotion_value = scene.audio_params.emotion.value
        
        prompt = REFINE_SCENE_PROMPT_TEMPLATE.format(
            image_prompt=scene.image_prompt or scene.description_cn,
            video_prompt=scene.video_prompt or "",
            narration_cn=scene.narration_cn,
            narration_en=scene.narration_en,
            duration_seconds=scene.duration.value,
            emotion=emotion_value,
            feedback=feedback,
            narration_length=self._get_narration_length(scene.duration.value),
        )
        
        response_text = await self._call_qwen(prompt)
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception(f"Failed to parse JSON response: {response_text}")
        
        # Parse duration
        valid_durations = {5, 8, 10, 12, 15}
        duration_map = {5: SceneDuration.VERY_SHORT, 8: SceneDuration.SHORT, 10: SceneDuration.MEDIUM, 12: SceneDuration.LONG, 15: SceneDuration.VERY_LONG}
        duration_seconds = result.get("duration_seconds", scene.duration.value)
        if duration_seconds not in valid_durations:
            duration_seconds = min(valid_durations, key=lambda x: abs(x - duration_seconds))
        duration = duration_map[duration_seconds]
        
        # Parse emotion
        current_emotion = scene.audio_params.emotion if scene.audio_params else Emotion.CALM
        emotion_str = result.get("emotion", current_emotion.value)
        emotion = current_emotion
        for e in Emotion:
            if e.value == emotion_str:
                emotion = e
                break
        
        # Get prompts
        image_prompt = result.get("image_prompt", scene.image_prompt)
        video_prompt = result.get("video_prompt", scene.video_prompt)
        narration_en = result.get("narration_en", "")
        if not narration_en:
            narration_en = await self.translate_narration(result.get("narration_cn", scene.narration_cn))
        
        # Update audio params
        audio_params = scene.audio_params
        if audio_params:
            audio_params = AudioParams(emotion=emotion, emotion_strength=audio_params.emotion_strength, speed=audio_params.speed, volume=audio_params.volume)
        else:
            audio_params = self._generate_audio_params(result, VideoStyle.TEACHING)
        
        return Scene(
            scene_id=scene.scene_id,
            step_number=scene.step_number,
            description_cn=image_prompt,
            image_prompt=image_prompt,
            video_prompt=video_prompt,
            narration_cn=result.get("narration_cn", scene.narration_cn),
            narration_en=narration_en,
            duration=duration,
            character_ids=scene.character_ids,
            audio_params=audio_params,
        )
    
    async def translate_narration(self, narration_cn: str) -> str:
        """Translate Chinese narration to English."""
        prompt = TRANSLATE_PROMPT_TEMPLATE.format(narration_cn=narration_cn)
        response_text = await self._call_qwen(prompt)
        return response_text.strip()
