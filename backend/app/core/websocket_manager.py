"""
WebSocket 连接管理器 - 用于实时推送工作流进度
"""
from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio
from app.core.logger import logger


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # task_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """建立连接"""
        await websocket.accept()
        async with self._lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
        logger.info(f"✅ WebSocket 连接建立: task_id={task_id}, 当前连接数={len(self.active_connections[task_id])}")

    async def disconnect(self, websocket: WebSocket, task_id: str):
        """断开连接"""
        async with self._lock:
            if task_id in self.active_connections:
                self.active_connections[task_id].discard(websocket)
                if len(self.active_connections[task_id]) == 0:
                    del self.active_connections[task_id]
        logger.info(f"❌ WebSocket 连接断开: task_id={task_id}")

    async def send_progress(self, task_id: str, data: dict):
        """发送进度更新到指定任务的所有连接"""
        logger.debug(f"📡 [WebSocket] send_progress: task_id={task_id}, data={data}")

        if task_id not in self.active_connections:
            logger.warning(f"⚠️ [WebSocket] task_id={task_id} 没有活跃连接")
            return

        logger.debug(f"✅ [WebSocket] 找到 {len(self.active_connections[task_id])} 个连接")

        message = json.dumps(data, ensure_ascii=False)
        disconnected = set()

        for connection in self.active_connections[task_id]:
            try:
                await connection.send_text(message)
                logger.debug(f"✅ [WebSocket] 消息已发送")
            except Exception as e:
                logger.error(f"❌ 发送消息失败: {e}")
                disconnected.add(connection)

        # 清理断开的连接
        if disconnected:
            async with self._lock:
                self.active_connections[task_id] -= disconnected

    async def send_node_start(self, task_id: str, node_id: str, node_name: str):
        """发送节点开始执行"""
        logger.info(f"📤 [WebSocket] 发送 node_start: task_id={task_id}, node_id={node_id}, node_name={node_name}")
        await self.send_progress(task_id, {
            "type": "node_start",
            "node_id": node_id,
            "node_name": node_name,
            "status": "running",
            "progress": 0
        })
    
    async def send_node_progress(self, task_id: str, node_id: str, progress: int, message: str = ""):
        """发送节点执行进度"""
        await self.send_progress(task_id, {
            "type": "node_progress",
            "node_id": node_id,
            "status": "running",
            "progress": progress,
            "message": message
        })
    
    async def send_node_complete(self, task_id: str, node_id: str, node_name: str, output: dict = None):
        """发送节点完成"""
        await self.send_progress(task_id, {
            "type": "node_complete",
            "node_id": node_id,
            "node_name": node_name,
            "status": "completed",
            "progress": 100,
            "output": output
        })
    
    async def send_node_error(self, task_id: str, node_id: str, node_name: str, error: str):
        """发送节点错误"""
        await self.send_progress(task_id, {
            "type": "node_error",
            "node_id": node_id,
            "node_name": node_name,
            "status": "error",
            "error": error
        })
    
    async def send_message(self, task_id: str, message: str):
        """发送普通消息"""
        await self.send_progress(task_id, {
            "type": "message",
            "message": message
        })

    async def send_nodes_reset(self, task_id: str, node_ids: list):
        """发送节点重置消息（用于工作流回退）"""
        logger.info(f"📤 [WebSocket] 发送 nodes_reset: task_id={task_id}, node_ids={node_ids}")
        await self.send_progress(task_id, {
            "type": "nodes_reset",
            "node_ids": node_ids,
            "message": "工作流回退，重置后续节点状态"
        })


# 全局单例
ws_manager = ConnectionManager()
