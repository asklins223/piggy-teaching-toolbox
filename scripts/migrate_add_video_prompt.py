"""数据库迁移脚本：添加 video_prompt 字段

运行方式：
python scripts/migrate_add_video_prompt.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.models import get_engine


def migrate():
    """添加 video_prompt 字段到 scenes 表"""
    
    engine = get_engine()
    
    # 检查字段是否已存在
    with engine.connect() as conn:
        # 获取表结构
        result = conn.execute(text("DESCRIBE scenes"))
        columns = [row[0] for row in result]
        
        if 'video_prompt' in columns:
            print("video_prompt 字段已存在，跳过迁移")
            return
        
        # 添加 video_prompt 字段
        print("正在添加 video_prompt 字段...")
        conn.execute(text("""
            ALTER TABLE scenes 
            ADD COLUMN video_prompt TEXT NULL 
            COMMENT 'Video generation prompt (运镜、转场)'
            AFTER image_prompt
        """))
        conn.commit()
        print("video_prompt 字段添加成功！")


if __name__ == "__main__":
    migrate()
