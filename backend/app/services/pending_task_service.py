"""
待处理任务服务
"""
import json
import time
from typing import List, Optional, Dict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PendingTask
from app.core.logger import logger


class PendingTaskService:
    """待处理任务服务"""
    
    @staticmethod
    async def create_pending_task(
        session: AsyncSession,
        task_id: str,
        task_type: str,
        status: str,
        keywords: List[str] = None,
        title_candidates: List[str] = None,
        draft_content: str = None,
        editor_feedback: Dict = None
    ) -> PendingTask:
        """
        创建待处理任务
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            task_type: 任务类型（title_selection/human_review）
            status: 任务状态
            keywords: 关键词列表
            title_candidates: 标题候选列表
            draft_content: 草稿内容
            editor_feedback: 编辑反馈
        """
        now = int(time.time() * 1000)
        
        pending_task = PendingTask(
            task_id=task_id,
            task_type=task_type,
            status=status,
            keywords=json.dumps(keywords or [], ensure_ascii=False),
            title_candidates=json.dumps(title_candidates or [], ensure_ascii=False),
            draft_content=draft_content,
            editor_feedback=json.dumps(editor_feedback, ensure_ascii=False) if editor_feedback else None,
            created_at=now,
            updated_at=now
        )
        
        session.add(pending_task)
        await session.commit()
        await session.refresh(pending_task)
        
        logger.info(f"✅ 创建待处理任务: {task_id}, 类型: {task_type}")
        return pending_task
    
    @staticmethod
    async def get_pending_task(session: AsyncSession, task_id: str) -> Optional[PendingTask]:
        """获取待处理任务"""
        result = await session.execute(
            select(PendingTask).where(PendingTask.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_pending_tasks(
        session: AsyncSession,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PendingTask]:
        """
        列出待处理任务
        
        Args:
            session: 数据库会话
            task_type: 任务类型过滤（可选）
            limit: 返回数量限制
            offset: 偏移量
        """
        query = select(PendingTask).order_by(PendingTask.created_at.desc())
        
        if task_type:
            query = query.where(PendingTask.task_type == task_type)
        
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def delete_pending_task(session: AsyncSession, task_id: str) -> bool:
        """删除待处理任务"""
        result = await session.execute(
            delete(PendingTask).where(PendingTask.task_id == task_id)
        )
        await session.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"🗑️ 删除待处理任务: {task_id}")
        return deleted
    
    @staticmethod
    async def update_pending_task(
        session: AsyncSession,
        task_id: str,
        **kwargs
    ) -> Optional[PendingTask]:
        """更新待处理任务"""
        pending_task = await PendingTaskService.get_pending_task(session, task_id)
        if not pending_task:
            return None
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(pending_task, key):
                if key in ['keywords', 'title_candidates'] and isinstance(value, list):
                    setattr(pending_task, key, json.dumps(value, ensure_ascii=False))
                elif key == 'editor_feedback' and isinstance(value, dict):
                    setattr(pending_task, key, json.dumps(value, ensure_ascii=False))
                else:
                    setattr(pending_task, key, value)
        
        pending_task.updated_at = int(time.time() * 1000)
        
        await session.commit()
        await session.refresh(pending_task)
        
        logger.info(f"📝 更新待处理任务: {task_id}")
        return pending_task
