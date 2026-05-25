"""
Qwen 图片生成服务 (wanx-v1)
"""
import asyncio
import httpx
from typing import List, Dict, Optional
import os
from app.core.logger import logger


class ImageGenerationService:
    """图片生成服务"""

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        self.model = "wanx-v1"
        
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        size: str = "1024*1024",
        n: int = 1,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> List[str]:
        """
        生成图片
        
        Args:
            prompt: 图片描述提示词
            negative_prompt: 负面提示词（不希望出现的内容）
            size: 图片尺寸，支持 "1024*1024", "720*1280", "1280*720"
            n: 生成图片数量（1-4）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            图片 URL 列表
        """
        if not self.api_key:
            raise ValueError("未配置 IMAGE_API_KEY 或 LLM_API_KEY")
        
        last_exception = None
        current_delay = retry_delay
        
        for attempt in range(max_retries):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable"  # 启用异步模式
                }
                
                payload = {
                    "model": self.model,
                    "input": {
                        "prompt": prompt
                    },
                    "parameters": {
                        "size": size,
                        "n": n
                    }
                }
                
                # 添加负面提示词
                if negative_prompt:
                    payload["input"]["negative_prompt"] = negative_prompt
                
                logger.info(f"\n🎨 调用 Qwen 图片生成 API (尝试 {attempt + 1}/{max_retries})")
                logger.info(f"   提示词: {prompt}")
                logger.info(f"   尺寸: {size}, 数量: {n}")
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    # 提交任务
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # 检查响应
                    if result.get("output") and result["output"].get("task_status") == "SUCCEEDED":
                        # 同步模式：直接返回结果
                        image_urls = [item["url"] for item in result["output"]["results"]]
                        logger.info(f"✅ 图片生成成功: {len(image_urls)} 张")
                        return image_urls

                    elif result.get("output") and result["output"].get("task_id"):
                        # 异步模式：需要轮询任务状态
                        task_id = result["output"]["task_id"]
                        logger.info(f"   任务ID: {task_id}，开始轮询...")

                        image_urls = await self._poll_task_status(task_id, headers)
                        logger.info(f"✅ 图片生成成功: {len(image_urls)} 张")
                        return image_urls
                    
                    else:
                        # 请求失败
                        error_msg = result.get("message", "未知错误")
                        raise Exception(f"图片生成失败: {error_msg}")
                
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                logger.warning(f"⚠️ 图片生成失败 (尝试 {attempt + 1}/{max_retries}): {error_type} - {str(e)}")

                if attempt < max_retries - 1:
                    logger.info(f"   等待 {current_delay:.1f}秒后重试...")
                    await asyncio.sleep(current_delay)
                    current_delay *= 2  # 指数退避
                else:
                    logger.error(f"   已达到最大重试次数，放弃重试")
        
        # 所有重试都失败
        raise Exception(f"图片生成失败（已重试{max_retries}次）: {str(last_exception)}")
    
    async def _poll_task_status(
        self,
        task_id: str,
        headers: Dict[str, str],
        max_wait: int = 120,
        poll_interval: float = 2.0
    ) -> List[str]:
        """
        轮询任务状态
        
        Args:
            task_id: 任务ID
            headers: 请求头
            max_wait: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            图片 URL 列表
        """
        query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        elapsed = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
                response = await client.get(query_url, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                task_status = result.get("output", {}).get("task_status")
                
                if task_status == "SUCCEEDED":
                    # 任务成功
                    image_urls = [item["url"] for item in result["output"]["results"]]
                    return image_urls
                
                elif task_status == "FAILED":
                    # 任务失败
                    error_msg = result.get("output", {}).get("message", "未知错误")
                    raise Exception(f"图片生成任务失败: {error_msg}")
                
                elif task_status in ["PENDING", "RUNNING"]:
                    # 任务进行中
                    logger.debug(f"   任务状态: {task_status}，继续等待...")
                    continue
                
                else:
                    # 未知状态
                    raise Exception(f"未知任务状态: {task_status}")
        
        raise Exception(f"图片生成超时（等待{max_wait}秒）")


# 全局实例
image_generation_service = ImageGenerationService()

