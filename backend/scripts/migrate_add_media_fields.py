"""
数据库迁移脚本 - 添加图片/视频分析字段

为 xhs_note 表添加以下字段：
- media_description: 图片/视频的文字描述（VL模型生成）
- media_summary: 图片/视频内容总结（LLM生成）
- media_analysis_status: 媒体分析状态（pending/processing/completed/failed）
- local_media_path: 本地媒体文件路径（JSON格式，用于保底逻辑）

使用方法：
    python scripts/migrate_add_media_fields.py
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database.session import get_async_engine
from app.core.logger import logger


async def migrate():
    """执行数据库迁移"""
    engine = get_async_engine()
    
    try:
        async with engine.begin() as conn:
            # 检查 media_description 字段
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'xhs_note'
                AND COLUMN_NAME = 'media_description'
            """))
            row = result.fetchone()
            
            if row and row[0] > 0:
                logger.info("✅ 字段 media_description 已存在，跳过迁移")
            else:
                logger.info("🔄 添加字段 media_description...")
                await conn.execute(text("""
                    ALTER TABLE xhs_note
                    ADD COLUMN media_description TEXT COMMENT '图片/视频的文字描述（VL模型生成）'
                """))
                logger.info("✅ 字段 media_description 添加成功")
            
            # 检查 media_analysis_status 字段
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'xhs_note'
                AND COLUMN_NAME = 'media_analysis_status'
            """))
            row = result.fetchone()
            
            if row and row[0] > 0:
                logger.info("✅ 字段 media_analysis_status 已存在，跳过迁移")
            else:
                logger.info("🔄 添加字段 media_analysis_status...")
                await conn.execute(text("""
                    ALTER TABLE xhs_note
                    ADD COLUMN media_analysis_status VARCHAR(50) DEFAULT 'pending' 
                    COMMENT '媒体分析状态: pending/processing/completed/failed'
                """))
                logger.info("✅ 字段 media_analysis_status 添加成功")
            
            # 检查 media_summary 字段
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'xhs_note'
                AND COLUMN_NAME = 'media_summary'
            """))
            row = result.fetchone()
            
            if row and row[0] > 0:
                logger.info("✅ 字段 media_summary 已存在，跳过迁移")
            else:
                logger.info("🔄 添加字段 media_summary...")
                await conn.execute(text("""
                    ALTER TABLE xhs_note
                    ADD COLUMN media_summary TEXT COMMENT '图片/视频内容总结（LLM生成）'
                """))
                logger.info("✅ 字段 media_summary 添加成功")
            
            # 检查 local_media_path 字段
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'xhs_note'
                AND COLUMN_NAME = 'local_media_path'
            """))
            row = result.fetchone()
            
            if row and row[0] > 0:
                logger.info("✅ 字段 local_media_path 已存在，跳过迁移")
            else:
                logger.info("🔄 添加字段 local_media_path...")
                await conn.execute(text("""
                    ALTER TABLE xhs_note
                    ADD COLUMN local_media_path TEXT COMMENT '本地媒体文件路径（JSON格式）'
                """))
                logger.info("✅ 字段 local_media_path 添加成功")
            
            # 为现有数据设置默认状态
            logger.info("🔄 更新现有数据的默认状态...")
            await conn.execute(text("""
                UPDATE xhs_note
                SET media_analysis_status = 'pending'
                WHERE media_analysis_status IS NULL
            """))
            
            logger.info("🎉 数据库迁移完成！")
            
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {str(e)}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
