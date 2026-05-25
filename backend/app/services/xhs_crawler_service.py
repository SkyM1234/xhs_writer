"""
小红书爬虫服务封装
"""
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta

# 将 MediaCrawler_XHS 添加到模块搜索路径
# 路径: backend/app/utils/MediaCrawler_XHS
CRAWLER_DIR = Path(__file__).parent.parent / "utils" / "MediaCrawler_XHS"
if str(CRAWLER_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWLER_DIR))

from sqlalchemy import select, and_, or_

# 导入项目数据库模块（不再从 MediaCrawler 导入）
from app.database.session import get_session
from app.database.models import XhsNote


class XhsCrawlerService:
    """小红书爬虫服务"""
    
    def __init__(self):
        self.crawler = None
    
    async def get_recent_notes_from_db(
        self,
        keywords: List[str],
        topic_words: List[str],
        min_comments: int = 0,
        min_likes: int = 0,
        min_favorites: int = 0,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict]:
        """
        从数据库中查询近期的相关笔记
        
        Args:
            keywords: 搜索关键词列表
            topic_words: 话题词列表（标题/正文需包含其中之一）
            min_comments: 最小评论数
            min_likes: 最小点赞数
            min_favorites: 最小收藏数
            days: 查询最近几天的数据
            limit: 返回数量限制
            
        Returns:
            笔记列表
        """
        # 计算时间戳（毫秒）
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        async with get_session() as session:
            if not session:
                return []
            
            # 构建查询条件
            conditions = [
                XhsNote.last_update_time >= cutoff_time
            ]
            
            # 关键词条件（source_keyword 字段）
            if keywords:
                keyword_conditions = [
                    XhsNote.source_keyword.like(f"%{kw}%") for kw in keywords
                ]
                conditions.append(or_(*keyword_conditions))
            
            # 话题词条件（标题或描述包含）
            if topic_words:
                topic_conditions = []
                for word in topic_words:
                    topic_conditions.append(or_(
                        XhsNote.title.like(f"%{word}%"),
                        XhsNote.desc.like(f"%{word}%")
                    ))
                conditions.append(or_(*topic_conditions))
            
            # 使用数值字段进行数据库层面的筛选
            if min_comments > 0:
                conditions.append(XhsNote.comment_count_num >= min_comments)
            if min_likes > 0:
                conditions.append(XhsNote.liked_count_num >= min_likes)
            if min_favorites > 0:
                conditions.append(XhsNote.collected_count_num >= min_favorites)
            
            # 执行查询
            stmt = select(XhsNote).where(and_(*conditions)).order_by(
                XhsNote.last_update_time.desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            notes = result.scalars().all()
            
            # 转换为字典格式
            return [self._note_to_dict(note) for note in notes]
    
    def _note_to_dict(self, note: XhsNote) -> Dict:
        """将数据库模型转换为字典"""
        return {
            "note_id": note.note_id,
            "title": note.title,
            "content": note.desc,
            "likes": self._parse_count(note.liked_count),
            "favorites": self._parse_count(note.collected_count),
            "comments": self._parse_count(note.comment_count),
            "tags": note.tag_list.split(',') if note.tag_list else [],
            "author": note.nickname,
            "publish_time": note.time,
            "url": note.note_url,
            "content_type": note.type,
            "keyword_used": note.source_keyword,
            "last_update_time": note.last_update_time
        }
    
    def _parse_count(self, count_str: str) -> int:
        """
        解析互动数字符串，支持中文单位
        例如: "1.4万" -> 14000, "1234" -> 1234
        """
        if not count_str:
            return 0
        
        count_str = str(count_str).strip()
        
        try:
            # 处理带"万"的情况
            if '万+' in count_str:
                num_str = count_str.replace('万+', '').strip()
                return int(float(num_str) * 10000)
        
            elif '万' in count_str:
                num_str = count_str.replace('万', '').strip()
                return int(float(num_str) * 10000)
            
            # 处理带"千"的情况
            elif '千' in count_str:
                num_str = count_str.replace('千', '').strip()
                return int(float(num_str) * 1000)
            
            # 处理带"k"或"K"的情况
            elif 'k' in count_str.lower():
                num_str = count_str.lower().replace('k', '').strip()
                return int(float(num_str) * 1000)
            
            # 处理纯数字
            else:
                return int(float(count_str))
        
        except (ValueError, AttributeError):
            # 解析失败返回0
            return 0
    
    async def crawl_notes(
        self,
        keywords: List[str],
        topic_words: List[str] = None,
        min_comments: int = 0,
        min_likes: int = 0,
        min_favorites: int = 0,
        days: int = 0,
        target_count: int = 20
    ) -> int:
        """
        启动爬虫爬取笔记

        Args:
            keywords: 搜索关键词列表
            topic_words: 话题词列表（标题/正文需包含其中之一）
            min_comments: 最小评论数
            min_likes: 最小点赞数
            min_favorites: 最小收藏数
            days: 时间范围（天数），0表示不限制
            target_count: 目标爬取数量

        Returns:
            实际新增的笔记数量（不包括已存在但更新的笔记）

        Note:
            - 所有过滤条件都在爬虫端实时应用，只保存符合条件的笔记
            - 如果笔记已存在，只会更新互动数据，不计入新增数量
            - 爬虫会自动翻页直到达到目标数量或没有更多数据
            - 返回值是真实新增到数据库的笔记数量
        """
        if topic_words is None:
            topic_words = []

        import config
        from media_platform.xhs import XiaoHongShuCrawler
        from tools import utils
        
        # 设置爬虫配置
        original_save_data_option = config.SAVE_DATA_OPTION
        original_keywords = config.KEYWORDS
        original_max_count = config.CRAWLER_MAX_NOTES_COUNT
        original_topic_words = getattr(config, 'TOPIC_WORDS', [])
        original_min_comments = getattr(config, 'MIN_COMMENTS', 0)
        original_min_likes = getattr(config, 'MIN_LIKES', 0)
        original_min_favorites = getattr(config, 'MIN_FAVORITES', 0)
        original_days = getattr(config, 'DAYS', 0)
        
        try:
            # 更新配置
            config.SAVE_DATA_OPTION = "mysql"
            config.KEYWORDS = ",".join(keywords)
            config.TOPIC_WORDS = topic_words if topic_words else []
            config.MIN_COMMENTS = min_comments
            config.MIN_LIKES = min_likes
            config.MIN_FAVORITES = min_favorites
            config.DAYS = days      
            config.CRAWLER_MAX_NOTES_COUNT = target_count
            
            # 记录过滤配置
            utils.logger.info(f"[XhsCrawlerService] Crawler config: keywords={keywords}, topic_words={topic_words}, min_comments={min_comments}, min_likes={min_likes}, min_favorites={min_favorites}, days={days}")
            
            # 初始化数据库
            if config.SAVE_DATA_OPTION == "mysql":
                from database.db import init_db
                await init_db(config.SAVE_DATA_OPTION)

            # 创建爬虫实例
            crawler = XiaoHongShuCrawler()
            
            # 记录爬取前的笔记ID集合
            before_note_ids = await self._get_note_ids_in_db(keywords)
            
            # 执行爬取（爬虫内部只对新增笔记计数，会自动翻页直到达到目标数量）
            await crawler.start()
            
            # 清理资源
            await self._cleanup_crawler(crawler)
            
            # 记录爬取后的笔记ID集合
            after_note_ids = await self._get_note_ids_in_db(keywords)
            
            # 计算新增的笔记数量（新ID - 旧ID）
            new_note_ids = after_note_ids - before_note_ids
            return len(new_note_ids)
            
        finally:
            # 恢复原始配置
            config.SAVE_DATA_OPTION = original_save_data_option
            config.KEYWORDS = original_keywords
            config.CRAWLER_MAX_NOTES_COUNT = original_max_count
            config.TOPIC_WORDS = original_topic_words
            config.MIN_COMMENTS = original_min_comments
            config.MIN_LIKES = original_min_likes
            config.MIN_FAVORITES = original_min_favorites
            config.DAYS = original_days
    
    async def _get_note_ids_in_db(self, keywords: List[str]) -> set:
        """获取数据库中符合关键词的笔记ID集合"""
        async with get_session() as session:
            if not session:
                return set()
            
            conditions = []
            if keywords:
                keyword_conditions = [
                    XhsNote.source_keyword.like(f"%{kw}%") for kw in keywords
                ]
                conditions.append(or_(*keyword_conditions))
            
            if conditions:
                stmt = select(XhsNote.note_id).where(and_(*conditions))
            else:
                stmt = select(XhsNote.note_id)
            
            result = await session.execute(stmt)
            return set(result.scalars().all())
    
    async def _cleanup_crawler(self, crawler):
        """清理爬虫资源"""
        try:
            if hasattr(crawler, "cdp_manager") and crawler.cdp_manager:
                await crawler.cdp_manager.cleanup(force=True)
            elif hasattr(crawler, "browser_context") and crawler.browser_context:
                await crawler.browser_context.close()
        except Exception as e:
            error_msg = str(e).lower()
            if "closed" not in error_msg and "disconnected" not in error_msg:
                print(f"[XhsCrawlerService] Error cleaning up crawler: {e}")


# 全局服务实例
xhs_crawler_service = XhsCrawlerService()
