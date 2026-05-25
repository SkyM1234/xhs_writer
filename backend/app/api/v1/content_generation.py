"""
内容生成 API 接口
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import uuid4
from pathlib import Path
import json

from app.agents import get_app_async
from app.core.cache import redis_cache
from app.core.websocket_manager import ws_manager
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/content", tags=["content"])

# ===== 全局 app 实例（共享 checkpointer）=====
_app_instance = None

async def init_app_instance():
    """初始化全局 app 实例（在应用启动时调用）"""
    global _app_instance
    if _app_instance is None:
        _app_instance = await get_app_async()
    return _app_instance

async def get_app():
    """获取全局 app 实例（单例模式）"""
    global _app_instance
    if _app_instance is None:
        _app_instance = await get_app_async()
    return _app_instance


# ===== 请求/响应模型 =====

class ContentGenerationRequest(BaseModel):
    """内容生成请求"""
    keywords: List[str] = Field(..., description="主题关键词列表", min_length=1)
    topic_words: List[str] = Field(default_factory=list, description="话题词列表")
    account_persona: str = Field(default="专业分享者", description="账号人设")
    target_count: int = Field(default=10, description="目标采集笔记数量", ge=5, le=50)
    min_comments: int = Field(default=0, description="最小评论数", ge=0)
    min_likes: int = Field(default=0, description="最小点赞数", ge=0)
    min_favorites: int = Field(default=0, description="最小收藏数", ge=0)
    days: int = Field(default=7, description="查询最近几天的数据", ge=1, le=90)


class ContentGenerationResponse(BaseModel):
    """内容生成响应"""
    task_id: str
    status: str
    title_candidates: Optional[List[str]] = None
    draft_content: Optional[str] = None
    editor_feedback: Optional[Dict] = None
    image_prompts: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    image_local_paths: Optional[List[str]] = None
    final_post: Optional[Dict] = None
    messages: List[str] = []
    error: Optional[str] = None


class TitleSelectionRequest(BaseModel):
    """标题选择请求"""
    task_id: str
    selected_title: Optional[str] = Field(None, description="选择的标题，如果为None表示暂缓选择")
    action: str = Field(default="select", description="操作类型: select/postpone")


class HumanReviewRequest(BaseModel):
    """人工审核请求"""
    task_id: str
    decision: str = Field(..., description="审核决策: approve/reject/postpone")
    feedback: Optional[str] = Field(None, description="审核意见")


# ===== API 端点 =====

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 端点 - 实时推送工作流进度
    """
    await ws_manager.connect(websocket, task_id)
    try:
        # 保持连接，等待客户端断开
        while True:
            # 接收客户端消息（心跳检测）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await ws_manager.disconnect(websocket, task_id)


@router.post("/generate/titles", response_model=ContentGenerationResponse)
async def generate_titles(request: ContentGenerationRequest, task_id: Optional[str] = None):
    """
    生成标题候选

    返回3个候选标题供用户选择
    工作流会在copywriter节点前自动中断

    参数:
        request: 内容生成请求
        task_id: 可选的任务ID，如果不提供则自动生成
    """
    try:
        # 如果前端没有提供 task_id，则生成一个
        if not task_id:
            task_id = str(uuid4())

        # 使用全局 app 实例（共享 checkpointer）
        app = await get_app()

        # 初始状态
        initial_state = {
            "keywords": request.keywords,
            "topic_words": request.topic_words,
            "account_persona": request.account_persona,
            "selected_title": None,
            "target_count": request.target_count,
            "min_comments": request.min_comments,
            "min_likes": request.min_likes,
            "min_favorites": request.min_favorites,
            "days": request.days,
            "raw_trends": [],
            "analyzed_templates": [],
            "llm_analysis": None,
            "strategy": None,
            "title_candidates": [],
            "draft_content": None,
            "compliance_report": None,
            "editor_feedback": None,
            "iteration_count": 0,
            "human_decision": None,
            "human_feedback": None,
            "image_prompts": [],
            "image_urls": [],
            "image_local_paths": [],
            "final_post": None,
            "status": "draft",
            "messages": [f"TASK_ID:{task_id}"],  # 注入 task_id 到 messages
            "error": None,
            # 错误管理字段
            "error_detail": None,
            "error_history": [],
            "degraded_nodes": [],
            "retry_count": {}
        }

        config = {"configurable": {"thread_id": task_id}}

        # 执行到标题生成（会在copywriter前自动中断）
        result = await app.ainvoke(initial_state, config)

        # 存储中间结果到 Redis
        await redis_cache.set_task(task_id, {
            "state": result,
            "config": config
        })

        return ContentGenerationResponse(
            task_id=task_id,
            status="waiting_title_selection",
            title_candidates=result.get('title_candidates', []),
            messages=result.get('messages', [])
        )

    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"❌ 生成标题失败: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/continue", response_model=ContentGenerationResponse)
async def continue_generation(request: TitleSelectionRequest):
    """
    选择标题后继续生成完整内容
    使用LangGraph的interrupt恢复机制

    - action: select (选择标题) / postpone (暂缓选择)
    - selected_title: 选择的标题（action=select时必填）
    """
    try:
        # 检查任务是否存在（优先从 Redis 获取，如果不存在则从 checkpoint 恢复）
        task_data = await redis_cache.get_task(request.task_id)

        if not task_data:
            # 从 checkpoint 数据库恢复状态
            logger.info(f"📦 从 checkpoint 恢复任务状态: {request.task_id}")
            from app.agents.graph import get_checkpointer

            checkpointer = await get_checkpointer()
            config = {"configurable": {"thread_id": request.task_id}}
            checkpoint_state = await checkpointer.aget(config)

            if not checkpoint_state:
                raise HTTPException(status_code=404, detail="任务不存在，无法从 checkpoint 恢复")

            # 重建 task_data - checkpoint_tuple 是字典，状态在 channel_values 中
            state_values = checkpoint_state.get('channel_values', {})

            logger.info(f"从 checkpoint 恢复状态，包含 {len(state_values)} 个字段")

            task_data = {
                "config": config,
                "state": state_values
            }

        config = task_data["config"]
        result = task_data.get("state", {})

        # 使用全局 app 实例（共享 checkpointer）
        app = await get_app()

        # 如果是暂缓选择，保存到数据库，不继续执行工作流
        if request.action == 'postpone':
            from app.database.session import get_session
            from app.services.pending_task_service import PendingTaskService

            # 保存到待处理任务表
            async with get_session() as session:
                await PendingTaskService.create_pending_task(
                    session=session,
                    task_id=request.task_id,
                    task_type='title_selection',
                    status='waiting_title_selection',
                    keywords=result.get('keywords', []),
                    title_candidates=result.get('title_candidates', [])
                )

            # 不需要更新 Redis，checkpoint 数据库已经保存了状态
            logger.info(f"⏸️ 标题选择已暂缓，任务已保存到数据库: {request.task_id}")

            return ContentGenerationResponse(
                task_id=request.task_id,
                status="waiting_title_selection",
                title_candidates=result.get('title_candidates'),
                messages=["标题选择已暂缓，可稍后继续"],
            )

        # 验证选择的标题
        if not request.selected_title:
            raise HTTPException(status_code=400, detail="选择标题时必须提供 selected_title")

        # 使用 update_state 更新状态
        await app.aupdate_state(config, {"selected_title": request.selected_title})

        # 继续执行（从中断点恢复，传入 None 表示使用 checkpointer 中的状态）
        result = await app.ainvoke(None, config)

        # 更新存储到 Redis
        await redis_cache.set_task(request.task_id, {
            "state": result,
            "config": config
        })

        # 删除待处理任务（如果存在）
        try:
            from app.database.session import get_session
            from app.services.pending_task_service import PendingTaskService

            async with get_session() as session:
                await PendingTaskService.delete_pending_task(session, request.task_id)
        except Exception as e:
            logger.warning(f"删除待处理任务失败（可能不存在）: {e}")

        return ContentGenerationResponse(
            task_id=request.task_id,
            status=result.get('status', 'unknown'),
            draft_content=result.get('draft_content'),
            editor_feedback=result.get('editor_feedback'),
            image_prompts=result.get('image_prompts'),
            image_urls=result.get('image_urls'),
            image_local_paths=result.get('image_local_paths'),
            final_post=result.get('final_post'),
            messages=result.get('messages', []),
            error=result.get('error')
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"❌ 继续生成失败: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/human-review", response_model=ContentGenerationResponse)
async def human_review(request: HumanReviewRequest):
    """
    人工审核接口

    当内容评分在 80-90 分时，需要人工确认是否通过
    - decision: approve (通过) / reject (不通过) / postpone (暂缓)
    - feedback: 可选的审核意见
    """
    try:
        # 检查任务是否存在（优先从 Redis 获取，如果不存在则从 checkpoint 恢复）
        task_data = await redis_cache.get_task(request.task_id)

        if not task_data:
            # 从 checkpoint 数据库恢复状态
            logger.info(f"📦 从 checkpoint 恢复任务状态: {request.task_id}")
            from app.agents.graph import get_checkpointer

            checkpointer = await get_checkpointer()
            config = {"configurable": {"thread_id": request.task_id}}
            checkpoint_state = await checkpointer.aget(config)

            if not checkpoint_state:
                raise HTTPException(status_code=404, detail="任务不存在，无法从 checkpoint 恢复")

            # 重建 task_data - checkpoint_tuple 是字典，状态在 channel_values 中
            state_values = checkpoint_state.get('channel_values', {})

            logger.info(f"从 checkpoint 恢复状态，包含 {len(state_values)} 个字段")

            task_data = {
                "config": config,
                "state": state_values
            }

        config = task_data["config"]
        result = task_data.get("state", {})

        # 使用全局 app 实例
        app = await get_app()

        # 如果是暂缓审核，保存到数据库，不继续执行工作流
        if request.decision == 'postpone':
            from app.database.session import get_session
            from app.services.pending_task_service import PendingTaskService

            # 保存到待处理任务表
            async with get_session() as session:
                await PendingTaskService.create_pending_task(
                    session=session,
                    task_id=request.task_id,
                    task_type='human_review',
                    status='waiting_human_review',
                    keywords=result.get('keywords', []),
                    draft_content=result.get('draft_content'),
                    editor_feedback=result.get('editor_feedback')
                )

            # 不需要更新 Redis，checkpoint 数据库已经保存了状态
            logger.info(f"⏸️ 人工审核已暂缓，任务已保存到数据库: {request.task_id}")

            return ContentGenerationResponse(
                task_id=request.task_id,
                status="waiting_human_review",
                draft_content=result.get('draft_content'),
                editor_feedback=result.get('editor_feedback'),
                messages=["审核已暂缓，可稍后继续"],
            )

        # 更新人工审核决策（在发送重置消息之前）
        await app.aupdate_state(config, {
            "human_decision": request.decision,
            "human_feedback": request.feedback,  # 保存人工反馈
            "messages": [f"👤 人工审核: {request.decision} - {request.feedback or '无意见'}"]
        })

        # 如果是 reject，发送节点重置消息（在 update_state 之后，ainvoke 之前）
        if request.decision == 'reject':
            from app.core.websocket_manager import ws_manager
            # 重置后续节点：合规检查、终审编辑、人工审核、视觉设计、最终输出
            nodes_to_reset = ['compliance_checker', 'chief_editor', 'human_review', 'visual_designer', 'finalize']
            await ws_manager.send_nodes_reset(request.task_id, nodes_to_reset)
            logger.info(f"📤 人工审核拒绝，发送节点重置消息: {nodes_to_reset}")

        # 继续执行（从 human_review 节点恢复）
        result = await app.ainvoke(None, config)

        # 更新存储到 Redis
        await redis_cache.set_task(request.task_id, {
            "state": result,
            "config": config
        })

        # 删除待处理任务（如果存在）
        try:
            from app.database.session import get_session
            from app.services.pending_task_service import PendingTaskService

            async with get_session() as session:
                await PendingTaskService.delete_pending_task(session, request.task_id)
        except Exception as e:
            logger.warning(f"删除待处理任务失败（可能不存在）: {e}")

        return ContentGenerationResponse(
            task_id=request.task_id,
            status=result.get('status', 'unknown'),
            draft_content=result.get('draft_content'),
            editor_feedback=result.get('editor_feedback'),
            image_prompts=result.get('image_prompts'),
            image_urls=result.get('image_urls'),
            image_local_paths=result.get('image_local_paths'),
            final_post=result.get('final_post'),
            messages=result.get('messages', []),
            error=result.get('error')
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"❌ 人工审核失败: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=ContentGenerationResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态
    """
    task_data = await redis_cache.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = task_data.get("state", task_data)  # 兼容旧格式

    return ContentGenerationResponse(
        task_id=task_id,
        status=result.get('status', 'unknown'),
        title_candidates=result.get('title_candidates'),
        draft_content=result.get('draft_content'),
        editor_feedback=result.get('editor_feedback'),
        image_prompts=result.get('image_prompts'),
        image_urls=result.get('image_urls'),
        image_local_paths=result.get('image_local_paths'),
        final_post=result.get('final_post'),
        messages=result.get('messages', []),
        error=result.get('error')
    )


@router.get("/generate/title-selection-status/{task_id}")
async def get_title_selection_status(task_id: str):
    """
    获取待选择标题任务的详情，用于重新打开标题选择界面
    """
    task_data = await redis_cache.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = task_data.get("state", {})

    if result.get("status") != "waiting_title_selection":
        raise HTTPException(status_code=400, detail="任务不在待选择标题状态")

    return {
        "task_id": task_id,
        "status": "waiting_title_selection",
        "title_candidates": result.get("title_candidates"),
        "messages": result.get("messages", []),
    }


@router.get("/generate/review-status/{task_id}")
async def get_review_status(task_id: str):
    """
    获取待审核任务的详情，用于重新打开审核界面
    """
    task_data = await redis_cache.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = task_data.get("state", {})

    if result.get("status") != "waiting_human_review":
        raise HTTPException(status_code=400, detail="任务不在待审核状态")

    return {
        "task_id": task_id,
        "status": "waiting_human_review",
        "draft_content": result.get("draft_content"),
        "editor_feedback": result.get("editor_feedback"),
        "quality_score": result.get("editor_feedback", {}).get("quality_score"),
        "messages": result.get("messages", []),
    }


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务
    """
    if await redis_cache.exists(task_id):
        await redis_cache.delete_task(task_id)
        return {"message": "任务已删除"}
    else:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/tasks")
async def list_tasks():
    """
    列出所有任务
    """
    task_ids = await redis_cache.list_tasks()
    tasks = []
    for task_id in task_ids:
        task_data = await redis_cache.get_task(task_id)
        if task_data:
            tasks.append({
                "task_id": task_id,
                "status": task_data.get("state", {}).get("status", "unknown")
            })
    return {"tasks": tasks}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "content-generation",
        "version": "1.0.0"
    }


@router.get("/notes")
async def list_notes():
    """
    列出所有生成的笔记

    返回所有笔记的基本信息列表
    """
    try:
        outputs_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs"

        if not outputs_dir.exists():
            return {"notes": []}

        notes = []
        for note_dir in outputs_dir.iterdir():
            if note_dir.is_dir():
                note_file = note_dir / "note.json"
                if note_file.exists():
                    try:
                        with open(note_file, 'r', encoding='utf-8') as f:
                            note_data = json.load(f)

                        # 提取基本信息
                        notes.append({
                            "folder_name": note_dir.name,
                            "title": note_data.get("title", ""),
                            "keywords": note_data.get("keywords", []),
                            "quality_score": note_data.get("quality_score", 0),
                            "image_count": len(note_data.get("image_local_paths", [])),
                            "has_images": len(note_data.get("image_local_paths", [])) > 0
                        })
                    except Exception as e:
                        logger.warning(f"读取笔记失败 {note_dir.name}: {e}")
                        continue

        # 按文件夹名称倒序排列（最新的在前）
        notes.sort(key=lambda x: x["folder_name"], reverse=True)

        return {"notes": notes}

    except Exception as e:
        logger.error(f"列出笔记失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{folder_name}")
async def get_note_detail(folder_name: str):
    """
    获取笔记详情

    参数:
        folder_name: 笔记文件夹名称（例如：考研_abc123）

    返回:
        笔记的完整内容，包括图片的访问路径
    """
    try:
        outputs_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs"
        note_dir = outputs_dir / folder_name

        if not note_dir.exists():
            raise HTTPException(status_code=404, detail="笔记不存在")

        note_file = note_dir / "note.json"
        if not note_file.exists():
            raise HTTPException(status_code=404, detail="笔记文件不存在")

        # 读取笔记内容
        with open(note_file, 'r', encoding='utf-8') as f:
            note_data = json.load(f)

        # 处理图片路径，转换为可访问的 URL
        images_dir = note_dir / "images"
        image_urls = []
        if images_dir.exists():
            for img_file in sorted(images_dir.iterdir()):
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    # 生成相对于 outputs 的路径
                    relative_path = f"{folder_name}/images/{img_file.name}"
                    image_urls.append(f"/outputs/{relative_path}")

        # 构建响应
        response = {
            "folder_name": folder_name,
            "title": note_data.get("title", ""),
            "content": note_data.get("content", ""),
            "tags": note_data.get("tags", []),
            "keywords": note_data.get("keywords", []),
            "quality_score": note_data.get("quality_score", 0),
            "iteration_count": note_data.get("iteration_count", 0),
            "image_prompts": note_data.get("image_prompts", []),
            "image_urls": image_urls,  # 使用本地图片的访问路径
            "online_image_urls": note_data.get("image_urls", [])  # 原始在线 URL
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取笔记详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notes/{folder_name}")
async def delete_note(folder_name: str):
    """
    删除笔记

    参数:
        folder_name: 笔记文件夹名称（例如：考研_abc123）

    返回:
        删除成功的消息
    """
    try:
        import shutil

        outputs_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs"
        note_dir = outputs_dir / folder_name

        if not note_dir.exists():
            raise HTTPException(status_code=404, detail="笔记不存在")

        # 删除整个笔记文件夹
        shutil.rmtree(note_dir)

        logger.info(f"✅ 笔记已删除: {folder_name}")

        return {
            "message": "笔记已删除",
            "folder_name": folder_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除笔记失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
