"""数据库迁移脚本：添加 active_task 字段

运行方式：
python scripts/migrate_add_active_task.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.models import get_engine


def migrate():
    """添加 active_task_id 和 active_task_type 字段到 projects 表"""
    
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("DESCRIBE projects"))
        columns = [row[0] for row in result]
        
        if 'active_task_id' not in columns:
            print("正在添加 active_task_id 字段...")
            conn.execute(text("""
                ALTER TABLE projects 
                ADD COLUMN active_task_id VARCHAR(64) NULL 
                COMMENT '当前正在执行的任务ID'
                AFTER export_cos_key
            """))
            print("active_task_id 字段添加成功！")
        else:
            print("active_task_id 字段已存在")
        
        if 'active_task_type' not in columns:
            print("正在添加 active_task_type 字段...")
            conn.execute(text("""
                ALTER TABLE projects 
                ADD COLUMN active_task_type VARCHAR(32) NULL 
                COMMENT '当前任务类型: storyboard/audio/export'
                AFTER active_task_id
            """))
            print("active_task_type 字段添加成功！")
        else:
            print("active_task_type 字段已存在")
        
        conn.commit()
        print("迁移完成！")


if __name__ == "__main__":
    migrate()
