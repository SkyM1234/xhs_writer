"""
批量爬取小红书数据脚本

从配置文件读取多个爬取任务，批量执行
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logger import logger
from app.core.config import settings
from app.services.xhs_crawler_service import XhsCrawlerService


def load_config(config_path: str) -> List[Dict]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('tasks', [])
    except Exception as e:
        logger.error(f"❌ 加载配置文件失败: {e}")
        raise


async def run_task(crawler_service: XhsCrawlerService, task: Dict, task_index: int, total_tasks: int):
    """执行单个爬取任务"""
    task_name = task.get('name', f'任务{task_index}')
    
    logger.info("=" * 60)
    logger.info(f"📋 任务 [{task_index}/{total_tasks}]: {task_name}")
    logger.info("=" * 60)
    logger.info(f"📝 关键词: {', '.join(task['keywords'])}")
    
    if task.get('topic_words'):
        logger.info(f"🏷️  话题词: {', '.join(task['topic_words'])}")
    
    logger.info(f"🎯 目标数量: {task.get('count', 20)}")
    logger.info(f"👍 最小点赞数: {task.get('min_likes', 0)}")
    logger.info(f"💬 最小评论数: {task.get('min_comments', 0)}")
    logger.info(f"⭐ 最小收藏数: {task.get('min_favorites', 0)}")
    
    days = task.get('days', 0)
    logger.info(f"📅 时间范围: {'不限制' if days == 0 else f'最近{days}天'}")
    
    try:
        logger.info("🕷️ 开始爬取笔记...")
        new_count = await crawler_service.crawl_notes(
            keywords=task['keywords'],
            topic_words=task.get('topic_words', []),
            min_comments=task.get('min_comments', 0),
            min_likes=task.get('min_likes', 0),
            min_favorites=task.get('min_favorites', 0),
            days=days,
            target_count=task.get('count', 20)
        )

        logger.info(f"✅ 任务完成！新增笔记数: {new_count}")
        logger.info(f"📊 注意：新增笔记的图片/视频已自动分析并生成总结")
        return {'task': task_name, 'success': True, 'new_count': new_count}
        
    except Exception as e:
        logger.error(f"❌ 任务失败: {e}")
        return {'task': task_name, 'success': False, 'error': str(e)}


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量爬取小红书数据')
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='crawl_config.json',
        help='配置文件路径（默认: crawl_config.json）'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=10,
        help='任务间延迟时间（秒），默认: 10'
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        logger.error(f"❌ 配置文件不存在: {config_path}")
        return
    
    tasks = load_config(str(config_path))
    if not tasks:
        logger.error("❌ 配置文件中没有任务")
        return
    
    # 打印总体信息
    logger.info("=" * 60)
    logger.info("🚀 批量爬取脚本启动")
    logger.info("=" * 60)
    logger.info(f"📁 配置文件: {config_path}")
    logger.info(f"📊 任务总数: {len(tasks)}")
    logger.info(f"⏱️  任务间延迟: {args.delay}秒")
    logger.info(f"🗄️  数据库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    logger.info("=" * 60)
    
    # 创建爬虫服务
    crawler_service = XhsCrawlerService()
    
    # 执行任务
    results = []
    for i, task in enumerate(tasks, 1):
        result = await run_task(crawler_service, task, i, len(tasks))
        results.append(result)
        
        # 任务间延迟（最后一个任务不需要延迟）
        if i < len(tasks):
            logger.info(f"⏳ 等待 {args.delay} 秒后执行下一个任务...")
            await asyncio.sleep(args.delay)
    
    # 打印汇总
    logger.info("=" * 60)
    logger.info("📊 批量爬取完成！汇总报告:")
    logger.info("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    total_new_notes = sum(r.get('new_count', 0) for r in results if r['success'])
    
    logger.info(f"✅ 成功任务: {success_count}/{len(tasks)}")
    logger.info(f"📝 新增笔记总数: {total_new_notes}")
    logger.info("")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        if result['success']:
            logger.info(f"{status} {result['task']}: 新增 {result['new_count']} 条")
        else:
            logger.info(f"{status} {result['task']}: {result['error']}")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
