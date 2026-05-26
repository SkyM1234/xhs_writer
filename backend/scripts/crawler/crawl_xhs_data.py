"""
小红书数据爬取脚本

独立运行的爬虫脚本，用于爬取小红书笔记数据到数据库
支持命令行参数配置关键词、过滤条件等
"""
import asyncio
import argparse
import sys
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logger import logger
from app.core.config import settings
from app.services.xhs_crawler_service import XhsCrawlerService


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='小红书数据爬取脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础爬取
  python crawl_xhs_data.py -k "Python编程,机器学习"
  
  # 带过滤条件
  python crawl_xhs_data.py -k "Python编程" -t "教程,入门" --min-likes 100 --min-comments 10
  
  # 指定数量和时间范围
  python crawl_xhs_data.py -k "AI绘画" -n 50 --days 30
        """
    )
    
    # 必需参数
    parser.add_argument(
        '-k', '--keywords',
        type=str,
        required=True,
        help='搜索关键词，多个关键词用逗号分隔，例如: "Python编程,机器学习"'
    )
    
    # 可选参数
    parser.add_argument(
        '-t', '--topic-words',
        type=str,
        default='',
        help='话题词，标题或正文需包含其中之一，多个用逗号分隔'
    )
    
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=20,
        help='目标爬取数量（默认: 20）'
    )
    
    parser.add_argument(
        '--min-likes',
        type=int,
        default=0,
        help='最小点赞数（默认: 0）'
    )
    
    parser.add_argument(
        '--min-comments',
        type=int,
        default=0,
        help='最小评论数（默认: 0）'
    )
    
    parser.add_argument(
        '--min-favorites',
        type=int,
        default=0,
        help='最小收藏数（默认: 0）'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=0,
        help='时间范围（天数），0表示不限制（默认: 0）'
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 处理关键词
    keywords = [kw.strip() for kw in args.keywords.split(',') if kw.strip()]
    if not keywords:
        logger.error("❌ 关键词不能为空")
        return
    
    # 处理话题词
    topic_words = [tw.strip() for tw in args.topic_words.split(',') if tw.strip()] if args.topic_words else []
    
    # 打印配置信息
    logger.info("=" * 60)
    logger.info("🚀 小红书数据爬取脚本启动")
    logger.info("=" * 60)
    logger.info(f"📝 搜索关键词: {', '.join(keywords)}")
    if topic_words:
        logger.info(f"🏷️  话题词: {', '.join(topic_words)}")
    logger.info(f"🎯 目标数量: {args.count}")
    logger.info(f"👍 最小点赞数: {args.min_likes}")
    logger.info(f"💬 最小评论数: {args.min_comments}")
    logger.info(f"⭐ 最小收藏数: {args.min_favorites}")
    logger.info(f"📅 时间范围: {'不限制' if args.days == 0 else f'最近{args.days}天'}")
    logger.info(f"🗄️  数据库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    logger.info("=" * 60)
    
    # 创建爬虫服务
    crawler_service = XhsCrawlerService()
    
    try:
        # 执行爬取
        logger.info("🕷️ 开始爬取数据...")
        new_count = await crawler_service.crawl_notes(
            keywords=keywords,
            topic_words=topic_words,
            min_comments=args.min_comments,
            min_likes=args.min_likes,
            min_favorites=args.min_favorites,
            days=args.days,
            target_count=args.count
        )

        logger.info("=" * 60)
        logger.info(f"✅ 爬取完成！新增笔记数: {new_count}")
        logger.info(f"📊 注意：新增笔记的图片/视频已自动分析并生成总结")
        logger.info(f"💡 提示：数据库字段 media_summary 包含精简总结（100字内）")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("⚠️ 用户中断爬取")
    except Exception as e:
        logger.error(f"❌ 爬取失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
