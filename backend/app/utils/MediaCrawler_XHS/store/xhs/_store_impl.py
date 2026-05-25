# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/xhs/_store_impl.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# @Author  : persist1@126.com
# @Time    : 2025/9/5 19:34
# @Desc    : Xiaohongshu storage implementation class

import json
from typing import List, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import XhsNote, XhsNoteComment, XhsCreator

from tools.async_file_writer import AsyncFileWriter
from tools.time_util import get_current_timestamp
from var import crawler_type_var


def parse_count_to_int(count_str: str) -> int:
    """
    解析互动数字符串为整数
    例如: "1.4万" -> 14000, "1234" -> 1234, "1.4万+" -> 14000
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
        return 0


class XhsCsvStoreImplement(AbstractStore):
    """CSV file storage implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="xhs", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict) -> bool:
        """Store content data to csv file"""
        await self.writer.write_to_csv(item_type="contents", item=content_item)
        return True  # File storage always assumes new content

    async def store_comment(self, comment_item: Dict):
        """Store comment data to csv file"""
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator_item: Dict):
        """Store creator data to csv file"""
        pass

    def flush(self):
        pass


class XhsJsonStoreImplement(AbstractStore):
    """JSON file storage implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="xhs", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict) -> bool:
        """Store content data to json file"""
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)
        return True  # File storage always assumes new content

    async def store_comment(self, comment_item: Dict):
        """Store comment data to json file"""
        await self.writer.write_single_item_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator_item: Dict):
        """Store creator data to json file"""
        pass

    def flush(self):
        pass


class XhsJsonlStoreImplement(AbstractStore):
    """JSONL file storage implementation (Recommended)"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="xhs", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict) -> bool:
        """Store content data to jsonl file"""
        await self.writer.write_to_jsonl(item_type="contents", item=content_item)
        return True  # File storage always assumes new content

    async def store_comment(self, comment_item: Dict):
        """Store comment data to jsonl file"""
        await self.writer.write_to_jsonl(item_type="comments", item=comment_item)

    async def store_creator(self, creator_item: Dict):
        """Store creator data to jsonl file"""
        pass

    def flush(self):
        pass


class XhsDbStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def store_content(self, content_item: Dict) -> bool:
        """
        Store content to database
        
        Returns:
            bool: True if new content was added, False if existing content was updated
        """
        note_id = content_item.get("note_id")
        if not note_id:
            return False
        async with get_session() as session:
            if await self.content_is_exist(session, note_id):
                await self.update_content(session, content_item)
                return False  # Existing note, updated
            else:
                await self.add_content(session, content_item)
                return True  # New note, added

    async def add_content(self, session: AsyncSession, content_item: Dict):
        add_ts = int(get_current_timestamp())
        last_modify_ts = int(get_current_timestamp())

        # image_list and tag_list are already comma-separated strings from store/__init__.py
        image_list = content_item.get("image_list")
        tag_list = content_item.get("tag_list")

        # Parse count strings to integers
        liked_count_str = str(content_item.get("liked_count"))
        collected_count_str = str(content_item.get("collected_count"))
        comment_count_str = str(content_item.get("comment_count"))
        share_count_str = str(content_item.get("share_count"))

        note = XhsNote(
            user_id=content_item.get("user_id"),
            nickname=content_item.get("nickname"),
            avatar=content_item.get("avatar"),
            ip_location=content_item.get("ip_location"),
            add_ts=add_ts,
            last_modify_ts=last_modify_ts,
            note_id=content_item.get("note_id"),
            type=content_item.get("type"),
            title=content_item.get("title"),
            desc=content_item.get("desc"),
            video_url=content_item.get("video_url"),
            time=content_item.get("time"),
            last_update_time=content_item.get("last_update_time"),
            liked_count=liked_count_str,
            collected_count=collected_count_str,
            comment_count=comment_count_str,
            share_count=share_count_str,
            liked_count_num=parse_count_to_int(liked_count_str),
            collected_count_num=parse_count_to_int(collected_count_str),
            comment_count_num=parse_count_to_int(comment_count_str),
            share_count_num=parse_count_to_int(share_count_str),
            image_list=image_list if isinstance(image_list, str) else str(image_list),
            tag_list=tag_list if isinstance(tag_list, str) else str(tag_list),
            note_url=content_item.get("note_url"),
            source_keyword=content_item.get("source_keyword", ""),
            xsec_token=content_item.get("xsec_token", "")
        )
        session.add(note)

    async def update_content(self, session: AsyncSession, content_item: Dict):
        note_id = content_item.get("note_id")
        last_modify_ts = int(get_current_timestamp())

        liked_count_str = str(content_item.get("liked_count"))
        collected_count_str = str(content_item.get("collected_count"))
        comment_count_str = str(content_item.get("comment_count"))
        share_count_str = str(content_item.get("share_count"))

        update_data = {
            "last_modify_ts": last_modify_ts,
            "liked_count": liked_count_str,
            "collected_count": collected_count_str,
            "comment_count": comment_count_str,
            "share_count": share_count_str,
            "liked_count_num": parse_count_to_int(liked_count_str),
            "collected_count_num": parse_count_to_int(collected_count_str),
            "comment_count_num": parse_count_to_int(comment_count_str),
            "share_count_num": parse_count_to_int(share_count_str),
            "last_update_time": content_item.get("last_update_time"),
        }
        stmt = update(XhsNote).where(XhsNote.note_id == note_id).values(**update_data)
        await session.execute(stmt)

    async def content_is_exist(self, session: AsyncSession, note_id: str) -> bool:
        stmt = select(XhsNote).where(XhsNote.note_id == note_id)
        result = await session.execute(stmt)
        return result.first() is not None

    async def store_comment(self, comment_item: Dict):
        if not comment_item:
            return
        async with get_session() as session:
            comment_id = comment_item.get("comment_id")
            if not comment_id:
                return
            if await self.comment_is_exist(session, comment_id):
                await self.update_comment(session, comment_item)
            else:
                await self.add_comment(session, comment_item)

    async def add_comment(self, session: AsyncSession, comment_item: Dict):
        add_ts = int(get_current_timestamp())
        last_modify_ts = int(get_current_timestamp())
        
        # pictures is already a comma-separated string from store/__init__.py
        pictures = comment_item.get("pictures")
        
        comment = XhsNoteComment(
            user_id=comment_item.get("user_id"),
            nickname=comment_item.get("nickname"),
            avatar=comment_item.get("avatar"),
            ip_location=comment_item.get("ip_location"),
            add_ts=add_ts,
            last_modify_ts=last_modify_ts,
            comment_id=comment_item.get("comment_id"),
            create_time=comment_item.get("create_time"),
            note_id=comment_item.get("note_id"),
            content=comment_item.get("content"),
            sub_comment_count=int(comment_item.get("sub_comment_count", 0) or 0),
            pictures=pictures if isinstance(pictures, str) else str(pictures),
            parent_comment_id=str(comment_item.get("parent_comment_id", "")),
            like_count=str(comment_item.get("like_count"))
        )
        session.add(comment)

    async def update_comment(self, session: AsyncSession, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        last_modify_ts = int(get_current_timestamp())
        update_data = {
            "last_modify_ts": last_modify_ts,
            "like_count": str(comment_item.get("like_count")),
            "sub_comment_count": int(comment_item.get("sub_comment_count", 0) or 0),
        }
        stmt = update(XhsNoteComment).where(XhsNoteComment.comment_id == comment_id).values(**update_data)
        await session.execute(stmt)

    async def comment_is_exist(self, session: AsyncSession, comment_id: str) -> bool:
        stmt = select(XhsNoteComment).where(XhsNoteComment.comment_id == comment_id)
        result = await session.execute(stmt)
        return result.first() is not None

    async def store_creator(self, creator_item: Dict):
        user_id = creator_item.get("user_id")
        if not user_id:
            return
        async with get_session() as session:
            if await self.creator_is_exist(session, user_id):
                await self.update_creator(session, creator_item)
            else:
                await self.add_creator(session, creator_item)

    async def add_creator(self, session: AsyncSession, creator_item: Dict):
        add_ts = int(get_current_timestamp())
        last_modify_ts = int(get_current_timestamp())

        # tag_list might be a JSON string from store/__init__.py
        tag_list = creator_item.get("tag_list")

        follows_str = str(creator_item.get("follows"))
        fans_str = str(creator_item.get("fans"))
        interaction_str = str(creator_item.get("interaction"))

        creator = XhsCreator(
            user_id=creator_item.get("user_id"),
            nickname=creator_item.get("nickname"),
            avatar=creator_item.get("avatar"),
            ip_location=creator_item.get("ip_location"),
            add_ts=add_ts,
            last_modify_ts=last_modify_ts,
            desc=creator_item.get("desc"),
            gender=creator_item.get("gender"),
            follows=follows_str,
            fans=fans_str,
            interaction=interaction_str,
            follows_num=parse_count_to_int(follows_str),
            fans_num=parse_count_to_int(fans_str),
            interaction_num=parse_count_to_int(interaction_str),
            tag_list=tag_list if isinstance(tag_list, str) else json.dumps(tag_list)
        )
        session.add(creator)

    async def update_creator(self, session: AsyncSession, creator_item: Dict):
        user_id = creator_item.get("user_id")
        last_modify_ts = int(get_current_timestamp())

        # tag_list might be a JSON string from store/__init__.py
        tag_list = creator_item.get("tag_list")

        follows_str = str(creator_item.get("follows"))
        fans_str = str(creator_item.get("fans"))
        interaction_str = str(creator_item.get("interaction"))

        update_data = {
            "last_modify_ts": last_modify_ts,
            "nickname": creator_item.get("nickname"),
            "avatar": creator_item.get("avatar"),
            "desc": creator_item.get("desc"),
            "follows": follows_str,
            "fans": fans_str,
            "interaction": interaction_str,
            "follows_num": parse_count_to_int(follows_str),
            "fans_num": parse_count_to_int(fans_str),
            "interaction_num": parse_count_to_int(interaction_str),
            "tag_list": tag_list if isinstance(tag_list, str) else json.dumps(tag_list)
        }
        stmt = update(XhsCreator).where(XhsCreator.user_id == user_id).values(**update_data)
        await session.execute(stmt)

    async def creator_is_exist(self, session: AsyncSession, user_id: str) -> bool:
        stmt = select(XhsCreator).where(XhsCreator.user_id == user_id)
        result = await session.execute(stmt)
        return result.first() is not None

    async def get_all_content(self) -> List[Dict]:
        async with get_session() as session:
            stmt = select(XhsNote)
            result = await session.execute(stmt)
            return [item.__dict__ for item in result.scalars().all()]

    async def get_all_comments(self) -> List[Dict]:
        async with get_session() as session:
            stmt = select(XhsNoteComment)
            result = await session.execute(stmt)
            return [item.__dict__ for item in result.scalars().all()]