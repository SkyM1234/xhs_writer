"""
数据库初始化
"""
import logging

from .session import create_tables

logger = logging.getLogger(__name__)


async def init_table_schema(db_type: str):
    """
    初始化数据库表结构
    
    Args:
        db_type: 数据库类型，目前支持 'mysql'
    """
    logger.info(f"[init_table_schema] 开始初始化 {db_type} 表结构...")
    await create_tables(db_type)
    logger.info(f"[init_table_schema] {db_type} 表结构初始化成功")


async def init_db(db_type: str = "mysql"):
    """
    初始化数据库
    
    Args:
        db_type: 数据库类型，默认 'mysql'
    """
    await init_table_schema(db_type)


async def close_db():
    """关闭数据库连接"""
    from .session import close_engines
    await close_engines()
