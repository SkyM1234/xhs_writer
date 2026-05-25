"""
待处理任务 API 接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database.session import get_session
from app.services.pending_task_service import PendingTaskService
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/pending-tasks", tags=["pending-tasks"])


class PendingTaskResponse(BaseModel):
    """待处理任务响应"""
    id: int
    task_id: str
    task_type: str
    status: str
    keywords: List[str]
    title_candidates: Optional[List[str]] = None
    draft_content: Optional[str] = None
    editor_feedback: Optional[dict] = None
    created_at: int
    updated_at: int


@router.get("/", response_model=List[PendingTaskResponse])
async def list_pending_tasks(
    task_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    列出所有待处理任务
    
    Args:
        task_type: 任务类型过滤（title_selection/human_review）
        limit: 返回数量限制
        offset: 偏移量
    """
    try:
        async with get_session() as session:
            tasks = await PendingTaskService.list_pending_tasks(
                session, task_type=task_type, limit=limit, offset=offset
            )
            return [
                PendingTaskResponse(**task.to_dict())
                for task in tasks
            ]
    except Exception as e:
        logger.error(f"❌ 列出待处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=PendingTaskResponse)
async def get_pending_task(task_id: str):
    """
    获取待处理任务详情
    
    Args:
        task_id: 任务ID
    """
    try:
        async with get_session() as session:
            task = await PendingTaskService.get_pending_task(session, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            return PendingTaskResponse(**task.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取待处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_pending_task(task_id: str):
    """
    删除待处理任务
    
    Args:
        task_id: 任务ID
    """
    try:
        async with get_session() as session:
            deleted = await PendingTaskService.delete_pending_task(session, task_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="任务不存在")
            return {"message": "任务已删除", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除待处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/restore")
async def restore_pending_task(task_id: str):
    """
    从 checkpoint 数据库恢复任务状态

    Args:
        task_id: 任务ID

    Returns:
        恢复的任务状态信息
    """
    try:
        from app.agents.graph import get_checkpointer

        # 获取 checkpointer
        checkpointer = await get_checkpointer()

        # 从 checkpoint 恢复状态
        config = {"configurable": {"thread_id": task_id}}
        checkpoint_tuple = await checkpointer.aget(config)

        if not checkpoint_tuple:
            raise HTTPException(status_code=404, detail="Checkpoint 中未找到任务状态")

        # checkpoint_tuple 是字典，状态数据在 channel_values 中
        logger.info(f"checkpoint_tuple 类型: {type(checkpoint_tuple)}")
        logger.info(f"checkpoint_tuple 键: {list(checkpoint_tuple.keys())}")

        # 直接从 channel_values 获取状态数据
        values = checkpoint_tuple.get('channel_values', {})

        logger.info(f"提取的 values 类型: {type(values)}")
        if isinstance(values, dict):
            logger.info(f"values 包含 {len(values)} 个字段")
            logger.info(f"关键字段: keywords={values.get('keywords')}, status={values.get('status')}")

        return {
            "task_id": task_id,
            "status": values.get("status"),
            "title_candidates": values.get("title_candidates"),
            "draft_content": values.get("draft_content"),
            "editor_feedback": values.get("editor_feedback"),
            "keywords": values.get("keywords"),
            "selected_title": values.get("selected_title"),
            "human_decision": values.get("human_decision"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 恢复任务状态失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
