"""
视觉分析服务 - 使用 Qwen VL 模型分析图片/视频
"""
import os
import base64
from pathlib import Path
from typing import List, Optional, Dict
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import logger


class VisionAnalysisService:
    """视觉分析服务"""

    def __init__(self):
        """初始化 Qwen VL 客户端和 DeepSeek 客户端"""
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key:
            raise ValueError("未设置 QWEN_API_KEY 环境变量")

        # Qwen VL 客户端（用于图片/视频分析）
        self.vl_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.vl_model = "qwen-vl-max-latest"  # 使用最新的 Qwen VL 模型

        # DeepSeek 客户端（用于总结）
        self.provider = settings.LLM_PROVIDER
        if self.provider == "qwen":
            self.llm_client = AsyncOpenAI(
                api_key=os.environ.get("QWEN_API_KEY"),
                base_url=settings.LLM_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        elif self.provider == "deepseek":
            self.llm_client = AsyncOpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                base_url=settings.LLM_BASE_URL or "https://api.deepseek.com"
            )
        elif self.provider == "openai":
            self.llm_client = AsyncOpenAI(
                # api_key=settings.LLM_API_KEY, # 从环境变量获取获取 API 密钥
                base_url=settings.LLM_BASE_URL
            )
        else:
            self.llm_client = None
            logger.warning("⚠️ 未设置 LLM_API_KEY，总结功能将不可用")
    
    async def analyze_image_from_url(self, image_url: str, context: Optional[str] = None) -> str:
        """
        分析图片URL并返回文字描述
        
        Args:
            image_url: 图片URL
            context: 上下文信息（如笔记标题、描述）
            
        Returns:
            图片的文字描述
        """
        try:
            # 构建提示词
            prompt = "请详细描述这张图片的内容，包括：主要物体、场景、颜色、氛围、文字信息等。"
            if context:
                prompt = f"这是一篇小红书笔记的配图。笔记内容：{context}\n\n{prompt}"

            # 调用 Qwen VL API
            response = await self.vl_client.chat.completions.create(
                model=self.vl_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"✅ 图片分析成功: {image_url[:50]}...")
            return description
            
        except Exception as e:
            logger.error(f"❌ 图片分析失败 {image_url}: {str(e)}")
            return f"[分析失败: {str(e)}]"
    
    async def analyze_image_from_file(self, file_path: str, context: Optional[str] = None) -> str:
        """
        分析本地图片文件并返回文字描述
        
        Args:
            file_path: 本地图片文件路径
            context: 上下文信息（如笔记标题、描述）
            
        Returns:
            图片的文字描述
        """
        try:
            # 读取图片并转换为 base64
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 获取文件扩展名
            ext = Path(file_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')
            
            # 构建 data URL
            image_url = f"data:{mime_type};base64,{image_data}"
            
            # 构建提示词
            prompt = "请详细描述这张图片的内容，包括：主要物体、场景、颜色、氛围、文字信息等。"
            if context:
                prompt = f"这是一篇小红书笔记的配图。笔记内容：{context}\n\n{prompt}"

            # 调用 Qwen VL API
            response = await self.vl_client.chat.completions.create(
                model=self.vl_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"✅ 本地图片分析成功: {file_path}")
            return description
            
        except Exception as e:
            logger.error(f"❌ 本地图片分析失败 {file_path}: {str(e)}")
            return f"[分析失败: {str(e)}]"
    
    async def analyze_images_batch(
        self,
        image_urls: List[str],
        context: Optional[str] = None,
        max_images: int = 10
    ) -> str:
        """
        批量分析多张图片并返回综合描述

        Args:
            image_urls: 图片URL列表
            context: 上下文信息
            max_images: 最多分析的图片数量

        Returns:
            所有图片的综合描述
        """
        if not image_urls:
            return ""

        # 限制分析数量
        urls_to_analyze = image_urls[:max_images]

        descriptions = []
        for i, url in enumerate(urls_to_analyze, 1):
            desc = await self.analyze_image_from_url(url, context)
            if not desc.startswith("[分析失败"):
                descriptions.append(f"图片{i}: {desc}")

        if not descriptions:
            return "[所有图片分析失败]"

        return "\n\n".join(descriptions)

    async def analyze_video_from_url(self, video_url: str, context: Optional[str] = None) -> str:
        """
        分析视频URL并返回文字描述

        Args:
            video_url: 视频URL
            context: 上下文信息（如笔记标题、描述）

        Returns:
            视频的文字描述
        """
        try:
            # 构建提示词
            prompt = "请详细描述这个视频的内容，包括：主要场景、人物动作、氛围、关键信息等。"
            if context:
                prompt = f"这是一篇小红书笔记的视频。笔记内容：{context}\n\n{prompt}"

            # 调用 Qwen VL API（视频分析）
            response = await self.vl_client.chat.completions.create(
                model=self.vl_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "video", "video": video_url},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=800,  # 视频描述可能更长
                temperature=0.3
            )

            description = response.choices[0].message.content.strip()
            logger.info(f"✅ 视频分析成功: {video_url[:50]}...")
            return description

        except Exception as e:
            logger.error(f"❌ 视频分析失败 {video_url}: {str(e)}")
            return f"[视频分析失败: {str(e)}]"

    async def analyze_video_from_file(self, file_path: str, context: Optional[str] = None) -> str:
        """
        分析本地视频文件并返回文字描述

        Args:
            file_path: 本地视频文件路径
            context: 上下文信息

        Returns:
            视频的文字描述
        """
        try:
            # 读取视频并转换为 base64
            with open(file_path, 'rb') as f:
                video_data = base64.b64encode(f.read()).decode('utf-8')

            # 获取文件扩展名
            ext = Path(file_path).suffix.lower()
            mime_type = {
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.webm': 'video/webm'
            }.get(ext, 'video/mp4')

            # 构建 data URL
            video_url = f"data:{mime_type};base64,{video_data}"

            # 构建提示词
            prompt = "请详细描述这个视频的内容，包括：主要场景、人物动作、氛围、关键信息等。"
            if context:
                prompt = f"这是一篇小红书笔记的视频。笔记内容：{context}\n\n{prompt}"

            # 调用 Qwen VL API
            response = await self.vl_client.chat.completions.create(
                model=self.vl_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "video", "video": video_url},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )

            description = response.choices[0].message.content.strip()
            logger.info(f"✅ 本地视频分析成功: {file_path}")
            return description

        except Exception as e:
            logger.error(f"❌ 本地视频分析失败 {file_path}: {str(e)}")
            return f"[视频分析失败: {str(e)}]"

    async def analyze_image_with_fallback(
        self,
        image_url: str,
        local_path: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        智能分析图片：优先URL，失败时降级到本地文件

        Args:
            image_url: 图片URL
            local_path: 本地文件路径（可选）
            context: 上下文信息

        Returns:
            图片描述
        """
        # 优先尝试URL
        try:
            return await self.analyze_image_from_url(image_url, context)
        except Exception as url_error:
            logger.warning(f"⚠️ URL分析失败: {str(url_error)}")

            # 降级到本地文件
            if local_path and Path(local_path).exists():
                logger.info(f"🔄 降级使用本地文件: {local_path}")
                try:
                    return await self.analyze_image_from_file(local_path, context)
                except Exception as file_error:
                    logger.error(f"❌ 本地文件分析也失败: {str(file_error)}")
                    raise Exception(f"URL和本地文件都分析失败: URL={str(url_error)}, File={str(file_error)}")
            else:
                if local_path:
                    logger.warning(f"⚠️ 本地文件不存在: {local_path}")
                raise Exception(f"URL分析失败且无可用本地文件: {str(url_error)}")

    async def analyze_video_with_fallback(
        self,
        video_url: str,
        local_path: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        智能分析视频：优先URL，失败时降级到本地文件

        Args:
            video_url: 视频URL
            local_path: 本地文件路径（可选）
            context: 上下文信息

        Returns:
            视频描述
        """
        # 优先尝试URL
        try:
            return await self.analyze_video_from_url(video_url, context)
        except Exception as url_error:
            logger.warning(f"⚠️ 视频URL分析失败: {str(url_error)}")

            # 降级到本地文件
            if local_path and Path(local_path).exists():
                logger.info(f"🔄 降级使用本地视频文件: {local_path}")
                try:
                    return await self.analyze_video_from_file(local_path, context)
                except Exception as file_error:
                    logger.error(f"❌ 本地视频文件分析也失败: {str(file_error)}")
                    raise Exception(f"URL和本地文件都分析失败: URL={str(url_error)}, File={str(file_error)}")
            else:
                if local_path:
                    logger.warning(f"⚠️ 本地视频文件不存在: {local_path}")
                raise Exception(f"视频URL分析失败且无可用本地文件: {str(url_error)}")

    async def analyze_images_batch_with_fallback(
        self,
        image_urls: List[str],
        local_paths: Optional[List[str]] = None,
        context: Optional[str] = None,
        max_images: int = 9
    ) -> str:
        """
        批量分析多张图片并返回综合描述（带保底逻辑）

        Args:
            image_urls: 图片URL列表
            local_paths: 本地文件路径列表（可选，与URLs对应）
            context: 上下文信息
            max_images: 最多分析的图片数量

        Returns:
            所有图片的综合描述
        """
        if not image_urls:
            return ""

        # 限制分析数量
        urls_to_analyze = image_urls[:max_images]
        paths_to_use = local_paths[:max_images] if local_paths else [None] * len(urls_to_analyze)

        descriptions = []
        for i, (url, local_path) in enumerate(zip(urls_to_analyze, paths_to_use), 1):
            try:
                desc = await self.analyze_image_with_fallback(url, local_path, context)
                if not desc.startswith("[分析失败"):
                    descriptions.append(f"图片{i}: {desc}")
            except Exception as e:
                logger.error(f"❌ 图片{i}分析失败: {str(e)}")
                descriptions.append(f"图片{i}: [分析失败]")

        if not descriptions:
            return "[所有图片分析失败]"

        return "\n\n".join(descriptions)

    async def summarize_media_description(self, description: str, context: Optional[str] = None) -> str:
        """
        使用 DeepSeek 总结图片/视频描述

        Args:
            description: 详细的图片/视频描述
            context: 上下文信息（如笔记标题、描述）

        Returns:
            精简的总结
        """
        if not self.llm_client:
            logger.warning("⚠️ LLM 客户端未初始化，跳过总结")
            return description[:500] + "..." if len(description) > 500 else description

        try:
            # 构建总结提示词
            prompt = f"""请将以下图片/视频的详细描述总结为简洁的一段话（200字以内），保留关键信息：

详细描述：
{description}
"""
            if context:
                prompt = f"""笔记内容：{context}

{prompt}"""

            # 调用 API
            response = await self.llm_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"✅ 媒体描述总结成功")
            return summary

        except Exception as e:
            logger.error(f"❌ 媒体描述总结失败: {str(e)}")
            # 失败时返回截断的原描述
            return description[:500] + "..." if len(description) > 500 else description


# 全局服务实例
vision_analysis_service = VisionAnalysisService()
