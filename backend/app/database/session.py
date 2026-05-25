"""
数据库会话管理
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import Optional

from .models import Base
from app.core.config import settings

# 引擎缓存
_engines = {}


async def create_database_if_not_exists(db_type: str):
    """创建数据库（如果不存在）"""
    if db_type == "mysql":
        # 连接到 MySQL 服务器（不指定数据库）
        server_url = (
            f"mysql+asyncmy://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
            f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}"
        )
        engine = create_async_engine(server_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(
                text(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}")
            )
        await engine.dispose()
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def get_async_engine(db_type: str = "mysql"):
    """获取异步数据库引擎"""
    if db_type in _engines:
        return _engines[db_type]

    if db_type == "mysql":
        db_url = (
            f"mysql+asyncmy://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
            f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        )
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    _engines[db_type] = engine
    return engine


async def create_tables(db_type: str = "mysql"):
    """创建数据库表"""
    await create_database_if_not_exists(db_type)
    engine = get_async_engine(db_type)
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session(db_type: str = "mysql"):
    """获取异步数据库会话"""
    engine = get_async_engine(db_type)
    if not engine:
        yield None
        return
    
    AsyncSessionFactory = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()


async def close_engines():
    """关闭所有数据库引擎"""
    for engine in _engines.values():
        await engine.dispose()
    _engines.clear()
