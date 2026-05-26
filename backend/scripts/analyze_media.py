"""
分析小红书笔记的图片/视频并保存到数据库

使用方法：
    python scripts/analyze_media.py --all                    # 分析所有未处理的笔记
    python scripts/analyze_media.py --limit 10               # 分析前10条未处理的笔记
    python scripts/analyze_media.py --note-id xxx            # 分析指定笔记
    python scripts/analyze_media.py --reanalyze              # 重新分析所有笔记（包括已分析的）
"""
import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_
from app.database.session import get_session
from app.database.models import XhsNote
from app.services.vision_analysis_service import vision_analysis_service
from app.core.logger import logger


async def analyze_note_media(note: XhsNote, force: bool = False) -> bool:
    """
    分析单个笔记的图片/视频

    Args:
        note: 笔记对象
        force: 是否强制重新分析

    Returns:
        是否成功
    """
    # 检查是否需要分析
    if not force and note.media_analysis_status == 'completed':
        logger.info(f"⏭️ 笔记 {note.note_id} 已分析过，跳过")
        return True

    # 判断是图文还是视频
    is_video = note.type == 'video' or (note.video_url and note.video_url.strip())
    has_images = note.image_list and note.image_list.strip()

    # 检查是否有媒体内容
    if not is_video and not has_images:
        logger.info(f"⏭️ 笔记 {note.note_id} 无图片/视频，跳过")
        async with get_session() as session:
            stmt = select(XhsNote).where(XhsNote.note_id == note.note_id)
            result = await session.execute(stmt)
            db_note = result.scalar_one_or_none()
            if db_note:
                db_note.media_analysis_status = 'completed'
                db_note.media_description = '[无图片/视频]'
                await session.commit()
        return True

    try:
        # 更新状态为处理中
        async with get_session() as session:
            stmt = select(XhsNote).where(XhsNote.note_id == note.note_id)
            result = await session.execute(stmt)
            db_note = result.scalar_one_or_none()
            if db_note:
                db_note.media_analysis_status = 'processing'
                await session.commit()

        # 构建上下文
        context = f"标题：{note.title}\n描述：{note.desc[:200] if note.desc else ''}"

        description = ""

        # 分析视频
        if is_video and note.video_url:
            logger.info(f"🔄 开始分析笔记 {note.note_id} 的视频...")
            video_desc = await vision_analysis_service.analyze_video_from_url(
                note.video_url,
                context=context
            )
            description = f"[视频内容]: {video_desc}"

        # 分析图片
        if has_images:
            image_urls = [url.strip() for url in note.image_list.split(',') if url.strip()]

            if image_urls:
                logger.info(f"🔄 开始分析笔记 {note.note_id} 的 {len(image_urls)} 张图片...")
                image_desc = await vision_analysis_service.analyze_images_batch(
                    image_urls,
                    context=context,
                    max_images=10
                )

                # 如果既有视频又有图片，合并描述
                if description:
                    description += f"\n\n[配图内容]: {image_desc}"
                else:
                    description = image_desc

        # 生成总结
        logger.info(f"🔄 生成笔记 {note.note_id} 的媒体内容总结...")
        summary = await vision_analysis_service.summarize_media_description(
            description,
            context=context
        )

        # 保存到数据库
        async with get_session() as session:
            stmt = select(XhsNote).where(XhsNote.note_id == note.note_id)
            result = await session.execute(stmt)
            db_note = result.scalar_one_or_none()

            if db_note:
                db_note.media_description = description
                db_note.media_summary = summary
                db_note.media_analysis_status = 'completed'
                await session.commit()
                logger.info(f"✅ 笔记 {note.note_id} 分析完成")
                return True

        return False

    except Exception as e:
        logger.error(f"❌ 笔记 {note.note_id} 分析失败: {str(e)}")

        # 更新状态为失败
        try:
            async with get_session() as session:
                stmt = select(XhsNote).where(XhsNote.note_id == note.note_id)
                result = await session.execute(stmt)
                db_note = result.scalar_one_or_none()
                if db_note:
                    db_note.media_analysis_status = 'failed'
                    db_note.media_description = f'[分析失败: {str(e)}]'
                    await session.commit()
        except Exception as update_error:
            logger.error(f"❌ 更新失败状态时出错: {str(update_error)}")

        return False


async def main():
    parser = argparse.ArgumentParser(description='分析小红书笔记的图片/视频')
    parser.add_argument('--all', action='store_true', help='分析所有未处理的笔记')
    parser.add_argument('--limit', type=int, help='限制分析数量')
    parser.add_argument('--note-id', type=str, help='分析指定笔记ID')
    parser.add_argument('--reanalyze', action='store_true', help='重新分析所有笔记（包括已分析的）')
    
    args = parser.parse_args()
    
    # 查询需要分析的笔记
    async with get_session() as session:
        if args.note_id:
            # 分析指定笔记
            stmt = select(XhsNote).where(XhsNote.note_id == args.note_id)
            result = await session.execute(stmt)
            notes = [result.scalar_one_or_none()]
            if not notes[0]:
                logger.error(f"❌ 未找到笔记 {args.note_id}")
                return
        elif args.reanalyze:
            # 重新分析所有笔记
            stmt = select(XhsNote)
            if args.limit:
                stmt = stmt.limit(args.limit)
            result = await session.execute(stmt)
            notes = result.scalars().all()
        else:
            # 分析未处理的笔记
            stmt = select(XhsNote).where(
                or_(
                    XhsNote.media_analysis_status == 'pending',
                    XhsNote.media_analysis_status == 'failed',
                    XhsNote.media_analysis_status.is_(None)
                )
            )
            if args.limit:
                stmt = stmt.limit(args.limit)
            result = await session.execute(stmt)
            notes = result.scalars().all()
    
    if not notes:
        logger.info("✅ 没有需要分析的笔记")
        return
    
    logger.info(f"📊 共找到 {len(notes)} 条笔记需要分析")
    
    # 逐个分析
    success_count = 0
    for i, note in enumerate(notes, 1):
        logger.info(f"\n[{i}/{len(notes)}] 处理笔记: {note.note_id}")
        if await analyze_note_media(note, force=args.reanalyze):
            success_count += 1
        
        # 避免请求过快
        if i < len(notes):
            await asyncio.sleep(1)
    
    logger.info(f"\n🎉 分析完成！成功: {success_count}/{len(notes)}")


if __name__ == "__main__":
    asyncio.run(main())
