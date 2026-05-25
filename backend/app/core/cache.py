"""
Redis 缓存管理
"""
import json
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.core.config import settings


class RedisCache:
    """Redis 缓存管理器"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """连接 Redis"""
        if self._redis is None:
            self._redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
    
    async def set_task(self, task_id: str, data: Dict[str, Any], expire: int = 3600):
        """
        保存任务状态
        
        Args:
            task_id: 任务ID
            data: 任务数据
            expire: 过期时间（秒），默认1小时
        """
        await self.connect()
        await self._redis.setex(
            f"task:{task_id}",
            expire,
            json.dumps(data, ensure_ascii=False)
        )
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务数据，如果不存在返回 None
        """
        await self.connect()
        data = await self._redis.get(f"task:{task_id}")
        return json.loads(data) if data else None
    
    async def delete_task(self, task_id: str):
        """
        删除任务
        
        Args:
            task_id: 任务ID
        """
        await self.connect()
        await self._redis.delete(f"task:{task_id}")
    
    async def list_tasks(self, pattern: str = "task:*") -> list:
        """
        列出所有任务
        
        Args:
            pattern: 匹配模式
            
        Returns:
            任务ID列表
        """
        await self.connect()
        keys = await self._redis.keys(pattern)
        return [key.replace("task:", "") for key in keys]
    
    async def exists(self, task_id: str) -> bool:
        """
        检查任务是否存在
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否存在
        """
        await self.connect()
        return await self._redis.exists(f"task:{task_id}") > 0
    
    async def set_ttl(self, task_id: str, expire: int):
        """
        设置任务过期时间
        
        Args:
            task_id: 任务ID
            expire: 过期时间（秒）
        """
        await self.connect()
        await self._redis.expire(f"task:{task_id}", expire)


# 全局 Redis 缓存实例
redis_cache = RedisCache()
