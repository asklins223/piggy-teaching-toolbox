"""Database configuration and models.

This module provides MySQL database connection and ORM models.
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=3306, description="Database port")
    user: str = Field(default="root", description="Database user")
    password: str = Field(default="", description="Database password")
    database: str = Field(default="video_generator", description="Database name")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset=utf8mb4"


class COSConfig(BaseSettings):
    """Tencent Cloud COS configuration."""
    
    model_config = SettingsConfigDict(env_prefix="COS_", extra="ignore")
    
    secret_id: str = Field(default="", description="COS Secret ID")
    secret_key: str = Field(default="", description="COS Secret Key")
    bucket: str = Field(default="", description="COS Bucket name")
    region: str = Field(default="ap-guangzhou", description="COS Region")
    
    @property
    def base_url(self) -> str:
        """Get COS base URL."""
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com"


class SCFConfig(BaseSettings):
    """Tencent Cloud SCF (Serverless Cloud Function) configuration."""
    
    model_config = SettingsConfigDict(env_prefix="SCF_", extra="ignore")
    
    zip_url: str = Field(default="", description="SCF ZIP exporter API URL")


# Load configs
_db_config: Optional[DatabaseConfig] = None
_cos_config: Optional[COSConfig] = None
_scf_config: Optional[SCFConfig] = None


def get_db_config() -> DatabaseConfig:
    """Get database config."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig(_env_file=".env")
    return _db_config


def get_cos_config() -> COSConfig:
    """Get COS config."""
    global _cos_config
    if _cos_config is None:
        _cos_config = COSConfig(_env_file=".env")
    return _cos_config


def get_scf_config() -> SCFConfig:
    """Get SCF config."""
    global _scf_config
    if _scf_config is None:
        _scf_config = SCFConfig(_env_file=".env")
    return _scf_config


# SQLAlchemy setup
Base = declarative_base()
_engine = None
_SessionLocal = None


def get_engine():
    """Get database engine."""
    global _engine
    if _engine is None:
        config = get_db_config()
        _engine = create_engine(
            config.url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
    return _engine


def get_session_local():
    """Get session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Session:
    """Get database session (dependency)."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=get_engine())


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


# Models
class UserRecord(Base):
    """User record model."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), unique=True, nullable=False, index=True, comment="Username")
    password_hash = Column(String(256), nullable=False, comment="Password hash")
    email = Column(String(256), nullable=True, comment="Email")
    is_active = Column(Boolean, default=True, comment="Is active")
    is_admin = Column(Boolean, default=False, comment="Is admin")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated time")


class VoiceRecord(Base):
    """Voice record model for storing custom voice info."""
    
    __tablename__ = "voices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    voice_id = Column(String(128), unique=True, nullable=False, index=True, comment="IndexTTS voice ID")
    name = Column(String(128), nullable=False, comment="Voice name")
    user_id = Column(String(64), nullable=True, index=True, comment="User ID")
    cos_url = Column(Text, nullable=True, comment="COS file URL")
    cos_key = Column(String(256), nullable=True, comment="COS object key")
    original_filename = Column(String(256), nullable=True, comment="Original filename")
    file_size = Column(Integer, nullable=True, comment="File size in bytes")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated time")


class CharacterRecord(Base):
    """Character record model for storing character library info."""
    
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(String(64), unique=True, nullable=False, index=True, comment="Character ID")
    name = Column(String(128), nullable=False, comment="Character name")
    description = Column(Text, nullable=True, comment="Character description")
    user_id = Column(String(64), nullable=True, index=True, comment="User ID who created")
    cos_url = Column(Text, nullable=True, comment="COS image URL")
    cos_key = Column(String(256), nullable=True, comment="COS object key")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated time")


class ProjectRecord(Base):
    """Project record model."""
    
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), unique=True, nullable=False, index=True, comment="Project ID")
    user_id = Column(String(64), nullable=True, index=True, comment="User ID who created")
    status = Column(String(32), default="initialized", comment="Project status")
    # Teaching goal
    topic = Column(String(256), nullable=False, comment="Teaching topic")
    target_audience = Column(String(256), nullable=True, comment="Target audience")
    key_points = Column(Text, nullable=True, comment="Key points (JSON array)")
    # Video style (Requirements: 7.1)
    style = Column(String(32), default="teaching", comment="Video style")
    custom_style_description = Column(Text, nullable=True, comment="Custom style description")
    # Storyboard
    storyboard_title = Column(String(256), nullable=True, comment="Storyboard title")
    total_duration = Column(Integer, default=0, comment="Total duration in seconds")
    # Full audio
    full_audio_cn_cos_url = Column(Text, nullable=True, comment="Full CN audio COS URL")
    full_audio_cn_cos_key = Column(String(256), nullable=True, comment="Full CN audio COS key")
    full_audio_cn_duration = Column(Integer, default=0, comment="Full CN audio duration in ms")
    full_audio_en_cos_url = Column(Text, nullable=True, comment="Full EN audio COS URL")
    full_audio_en_cos_key = Column(String(256), nullable=True, comment="Full EN audio COS key")
    full_audio_en_duration = Column(Integer, default=0, comment="Full EN audio duration in ms")
    # Export
    export_cos_url = Column(Text, nullable=True, comment="Export ZIP COS URL")
    export_cos_key = Column(String(256), nullable=True, comment="Export ZIP COS key")
    # Active task tracking (防止重复提交)
    active_task_id = Column(String(64), nullable=True, comment="当前正在执行的任务ID")
    active_task_type = Column(String(32), nullable=True, comment="当前任务类型: storyboard/audio/export")
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated time")


class SceneRecord(Base):
    """Scene record model for storyboard scenes."""
    
    __tablename__ = "scenes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(String(64), unique=True, nullable=False, index=True, comment="Scene ID")
    project_id = Column(String(64), nullable=False, index=True, comment="Project ID")
    step_number = Column(Integer, nullable=False, comment="Step number")
    # Content
    description_cn = Column(Text, nullable=True, comment="Chinese description (legacy)")
    narration_cn = Column(Text, nullable=True, comment="Chinese narration")
    narration_en = Column(Text, nullable=True, comment="English narration")
    duration = Column(Integer, default=10, comment="Duration in seconds")
    character_ids = Column(Text, nullable=True, comment="Character IDs (JSON array)")
    # Audio params (Requirements: 7.4)
    audio_params = Column(Text, nullable=True, comment="Audio params (JSON object)")
    # Image - 新增 video_prompt 字段
    image_status = Column(String(32), default="pending", comment="Image generation status")
    image_cos_url = Column(Text, nullable=True, comment="Image COS URL")
    image_cos_key = Column(String(256), nullable=True, comment="Image COS key")
    image_prompt = Column(Text, nullable=True, comment="Image generation prompt (构图、光线、色调)")
    video_prompt = Column(Text, nullable=True, comment="Video generation prompt (运镜、转场)")
    # Audio CN
    audio_cn_status = Column(String(32), default="pending", comment="CN audio status")
    audio_cn_cos_url = Column(Text, nullable=True, comment="CN audio COS URL")
    audio_cn_cos_key = Column(String(256), nullable=True, comment="CN audio COS key")
    audio_cn_duration = Column(Integer, default=0, comment="CN audio duration in ms")
    # Audio EN
    audio_en_status = Column(String(32), default="pending", comment="EN audio status")
    audio_en_cos_url = Column(Text, nullable=True, comment="EN audio COS URL")
    audio_en_cos_key = Column(String(256), nullable=True, comment="EN audio COS key")
    audio_en_duration = Column(Integer, default=0, comment="EN audio duration in ms")
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated time")


class ProjectCharacterRecord(Base):
    """Project-Character association model."""
    
    __tablename__ = "project_characters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), nullable=False, index=True, comment="Project ID")
    character_id = Column(String(64), nullable=False, index=True, comment="Character ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created time")
