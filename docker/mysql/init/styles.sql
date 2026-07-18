-- 为 projects 表添加视频风格相关字段
ALTER TABLE projects 
ADD COLUMN style VARCHAR(32) DEFAULT 'teaching' COMMENT 'Video style',
ADD COLUMN custom_style_description TEXT NULL COMMENT 'Custom style description';

-- 为 scenes 表添加音频参数字段
ALTER TABLE scenes 
ADD COLUMN audio_params TEXT NULL COMMENT 'Audio params (JSON object)';

-- 为现有项目设置默认风格
UPDATE projects SET style = 'teaching' WHERE style IS NULL;

-- 创建索引提高查询性能
CREATE INDEX idx_projects_style ON projects(style);

-- 验证结果
SELECT 'Database update completed' as status;
SELECT style, COUNT(*) as count FROM projects GROUP BY style;

-- 移除 scenes 表的 emotion 字段
ALTER TABLE scenes DROP COLUMN emotion;
