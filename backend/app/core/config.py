"""
核心配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "Xiaohongshu-Flow"
    APP_VERSION: str = "1.0.0"
    
    # LLM 配置
    LLM_PROVIDER: str = "deepseek"  # qwen / openai / deepseek
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_EMBEDDING_MODEL: str = "text-embedding-v1"
    LLM_JUDAGE_MODEL: str = "deepseek-v4-pro" # 评分模型
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./xhs_writer.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # MySQL 配置（用于爬虫数据存储）
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "your_password"
    MYSQL_DATABASE: str = "xhs_crawler"
    
    # 图片生成配置
    IMAGE_PROVIDER: str = "qwen"  # qwen / dalle / midjourney
    IMAGE_API_KEY: Optional[str] = None
    IMAGE_MODEL: str = "wanx-v1"  # Qwen 图片生成模型
    IMAGE_SIZE: str = "1024*1024"  # 图片尺寸: 1024*1024, 720*1280, 1280*720
    IMAGE_COUNT: int = 1  # 每次生成图片数量（1-4）

# 全局配置实例
settings = Settings()
