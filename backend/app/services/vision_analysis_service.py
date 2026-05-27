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
        self.vl_model = settings.VL_MODEL  # 从配置读取 VL 模型

        # LLM（用于总结）
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

    def _file_to_data_url(self, file_path: str) -> Optional[str]:
        """
        将本地图片读成 base64 data URL，失败返回 None

        Args:
            file_path: 本地图片文件路径

        Returns:
            data:image/xxx;base64,xxx 字符串，或 None
        """
        try:
            p = Path(file_path)
            if not p.exists():
                return None
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            ext = p.suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')
            return f"data:{mime_type};base64,{image_data}"
        except Exception as e:
            logger.warning(f"⚠️ 读取本地图片失败 {file_path}: {e}")
            return None

    async def _analyze_images_single_call(
        self,
        image_payloads: List[str],
        context: Optional[str] = None,
        media_kind: str = "image",
    ) -> str:
        """
        ★ 核心方法：一次请求把所有图片送给 Qwen-VL，由模型在同一上下文中理解多图

        Args:
            image_payloads: 图片地址列表，元素可以是 http(s) URL 或 data:image/xxx;base64,xxx
            context: 上下文信息（如笔记标题、描述）
            media_kind: "image"（笔记多图）或 "video_frames"（视频抽帧）。
                        视频帧场景下会使用强调时序叙事的 prompt。

        Returns:
            综合描述。格式：
              图片1: ...   或   帧1: ...
              图片2: ...   或   帧2: ...
              ...
              整体观察: ...
        """
        if not image_payloads:
            return ""

        n = len(image_payloads)

        # 根据媒体类型构造不同 prompt
        if media_kind == "video_frames":
            unit = "帧"
            prompt = (
                f"以下是从一个小红书短视频中按时间顺序均匀抽取的 {n} 帧画面，"
                f"请结合多帧之间的连贯关系理解视频内容。\n\n"
                f"请严格按以下格式输出（不要添加额外说明）：\n"
                f"帧1: <对第1帧画面的详细描述，包括主体、场景、动作、色彩、文字信息等>\n"
                f"帧2: <对第2帧画面的详细描述，注意与上一帧的变化>\n"
                f"...\n"
                f"帧{n}: <对第{n}帧画面的详细描述>\n"
                f"整体观察: <综合这{n}帧，概括视频的叙事主线、关键动作、想传达的核心信息与视觉风格>"
            )
        else:
            unit = "图"
            prompt = (
                f"以下是同一篇小红书笔记的 {n} 张配图，请你结合多图上下文进行理解。\n\n"
                f"请严格按以下格式输出（不要添加额外说明）：\n"
                f"图片1: <对第1张图的详细描述，包括主体、场景、色彩、氛围、文字信息等>\n"
                f"图片2: <对第2张图的详细描述>\n"
                f"...\n"
                f"图片{n}: <对第{n}张图的详细描述>\n"
                f"整体观察: <综合这{n}张图，概括笔记想传达的核心信息、视觉风格、叙事逻辑>"
            )

        if context:
            prompt = f"笔记内容：{context}\n\n{prompt}"

        # 构建多图 content：N 个 image_url + 1 个 text
        content_list = [
            {"type": "image_url", "image_url": {"url": url}} for url in image_payloads
        ]
        content_list.append({"type": "text", "text": prompt})

        # 动态分配 max_tokens：每张图 ~400 token，封顶 6000
        max_tokens = min(6000, max(800, 400 * n + 300))

        response = await self.vl_client.chat.completions.create(
            model=self.vl_model,
            messages=[{"role": "user", "content": content_list}],
            max_tokens=max_tokens,
            temperature=0.3
        )

        description = response.choices[0].message.content.strip()
        logger.info(f"✅ 多{unit}一次性分析成功（共 {n} {unit}）")
        return description

    async def analyze_images_batch(
        self,
        image_urls: List[str],
        context: Optional[str] = None,
        max_images: Optional[int] = None
    ) -> str:
        """
        批量分析多张图片并返回综合描述

        ★ 已优化：一次请求把所有图片送入 Qwen-VL，提升上下文理解 & 速度

        Args:
            image_urls: 图片URL列表
            context: 上下文信息
            max_images: 最多分析的图片数量（默认从配置读取 settings.VL_MAX_IMAGES）

        Returns:
            所有图片的综合描述
        """
        if not image_urls:
            return ""

        # 从配置读取默认值
        if max_images is None:
            max_images = settings.VL_MAX_IMAGES

        # 限制分析数量
        urls_to_analyze = image_urls[:max_images]

        try:
            return await self._analyze_images_single_call(urls_to_analyze, context)
        except Exception as e:
            logger.error(f"❌ 多图一次性分析失败，降级到逐张分析: {str(e)}")
            # 降级：旧的逐张循环
            descriptions = []
            for i, url in enumerate(urls_to_analyze, 1):
                desc = await self.analyze_image_from_url(url, context)
                if not desc.startswith("[分析失败"):
                    descriptions.append(f"图片{i}: {desc}")

            if not descriptions:
                return "[所有图片分析失败]"

            return "\n\n".join(descriptions)

    # ===== 视频抽帧分析（绕过视频 base64 10MB 限制） =====

    async def _ensure_local_video_path(
        self,
        video_url: str,
        local_path: Optional[str] = None,
    ):
        """
        确保有一个可读的本地视频文件路径。

        - 如果 local_path 存在，直接返回 (local_path, None)
        - 否则从 video_url 下载到临时文件，返回 (tmp_path, cleanup_callable)

        Returns:
            (path: str, cleanup: Optional[callable])
            cleanup 调用后会删除临时文件；如果没有临时文件则为 None
        """
        # 优先使用已有本地文件
        if local_path and Path(local_path).exists():
            return local_path, None

        # 从 URL 下载到临时文件
        import tempfile
        import aiohttp

        # 从 URL 推断扩展名
        ext = ".mp4"
        for candidate in ('.mp4', '.mov', '.webm', '.avi', '.mkv'):
            if candidate in video_url.lower():
                ext = candidate
                break

        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp_path = tmp.name
        tmp.close()

        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(video_url) as resp:
                resp.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)

        logger.info(f"✅ 视频已下载到临时文件: {tmp_path}")

        def _cleanup():
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"⚠️ 清理临时视频失败 {tmp_path}: {e}")

        return tmp_path, _cleanup

    def _extract_video_frames_as_data_urls(
        self,
        file_path: str,
        num_frames: int,
        jpeg_quality: int = 85,
    ) -> List[str]:
        """
        从本地视频文件按时间均匀抽取 num_frames 帧，编码为 base64 jpeg data url。

        说明：
        - 使用 OpenCV 解码，无需 ffmpeg 二进制
        - 全程在内存中完成，不落盘
        - 软导入 cv2：未安装时抛 ImportError，由调用方决定是否降级

        Args:
            file_path: 本地视频文件路径
            num_frames: 期望抽取的帧数
            jpeg_quality: jpeg 压缩质量（1-100），85 已足够清晰

        Returns:
            data:image/jpeg;base64,xxx 字符串列表（按时间顺序）
            如果视频帧数 < num_frames，会返回所有可读帧
        """
        try:
            import cv2  # 软导入
        except ImportError as e:
            raise ImportError(
                "视频抽帧需要 opencv-python，请安装：pip install opencv-python"
            ) from e

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频: {file_path}")

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames <= 0:
                raise RuntimeError(f"视频帧数无效（{total_frames}）: {file_path}")

            # 计算采样位置：均匀分布在 [0, total_frames-1]
            sample_n = min(num_frames, total_frames)
            if sample_n <= 1:
                indices = [0]
            else:
                step = (total_frames - 1) / (sample_n - 1)
                indices = [int(round(i * step)) for i in range(sample_n)]

            data_urls: List[str] = []
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok or frame is None:
                    logger.warning(f"⚠️ 帧 {idx} 读取失败，跳过")
                    continue
                ok, buf = cv2.imencode('.jpg', frame, encode_params)
                if not ok:
                    logger.warning(f"⚠️ 帧 {idx} 编码失败，跳过")
                    continue
                b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
                data_urls.append(f"data:image/jpeg;base64,{b64}")

            if not data_urls:
                raise RuntimeError("未能成功抽取任何帧")

            logger.info(
                f"✅ 视频抽帧完成: {file_path} "
                f"(总帧数={total_frames}, 抽取={len(data_urls)})"
            )
            return data_urls
        finally:
            cap.release()

    async def analyze_video_by_frames(
        self,
        video_url: str,
        local_path: Optional[str] = None,
        context: Optional[str] = None,
        num_frames: Optional[int] = None,
    ) -> str:
        """
        通过抽帧 + 多图一次性调用 来分析视频，绕过视频 base64 10MB 限制。

        Args:
            video_url: 视频URL
            local_path: 本地视频文件路径（可选）。提供时直接抽帧，否则从URL下载到临时文件
            context: 上下文信息（如笔记标题、描述）
            num_frames: 抽取帧数。默认从 settings.VL_VIDEO_FRAMES 读取

        Returns:
            视频内容的综合描述（按帧 + 整体观察）
        """
        if num_frames is None:
            num_frames = settings.VL_VIDEO_FRAMES
        
        print(f"分析视频 {local_path, video_url}")

        path, cleanup = await self._ensure_local_video_path(video_url, local_path)
        try:
            frame_urls = self._extract_video_frames_as_data_urls(path, num_frames)
            return await self._analyze_images_single_call(
                frame_urls,
                context=context,
                media_kind="video_frames",
            )
        finally:
            if cleanup:
                cleanup()


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
                max_tokens=1000,
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
                max_tokens=1000,
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
        智能分析视频，多级降级，避开视频 base64 10MB 限制。

        ★ 默认策略：抽帧 + 多图一次性调用（受 settings.VL_VIDEO_USE_FRAMES 控制）

        降级顺序：
            1) 抽帧分析（首选）：本地文件直接抽帧；只有 URL 时下载到临时文件后抽帧
               - 不受 10MB 限制，速度快，模型对关键帧理解清晰
               - 失败原因可能：cv2 未安装、视频损坏、下载失败
            2) 原生视频 URL：调用 qwen-vl 视频接口（URL 模式无 10MB 限制，但有时长限制）
            3) 原生视频 base64：本地文件转 base64 上传（最后兜底，可能撞 10MB）

        关闭抽帧（VL_VIDEO_USE_FRAMES=False）时退化为旧的 URL→base64 两级降级。

        Args:
            video_url: 视频URL
            local_path: 本地文件路径（可选）
            context: 上下文信息

        Returns:
            视频描述
        """
        errors = []

        # ===== 降级 1：抽帧分析（默认首选） =====
        if settings.VL_VIDEO_USE_FRAMES:
            try:
                logger.info("🎬 使用抽帧策略分析视频...")
                return await self.analyze_video_by_frames(
                    video_url, local_path=local_path, context=context
                )
            except ImportError as cv2_error:
                # cv2 未安装：跳过抽帧，进入下一级降级
                logger.warning(f"⚠️ 抽帧不可用（{cv2_error}），降级到原生视频接口")
                errors.append(f"frames-import: {cv2_error}")
            except Exception as frame_error:
                logger.warning(f"⚠️ 抽帧分析失败: {frame_error}，降级到原生视频接口")
                errors.append(f"frames: {frame_error}")
        else:
            logger.info("🎬 抽帧已关闭（VL_VIDEO_USE_FRAMES=False），使用原生视频接口")

        # ===== 降级 2：原生视频 URL =====
        try:
            return await self.analyze_video_from_url(video_url, context)
        except Exception as url_error:
            logger.warning(f"⚠️ 视频URL分析失败: {url_error}")
            errors.append(f"url: {url_error}")

        # ===== 降级 3：原生视频 base64（可能撞 10MB） =====
        if local_path and Path(local_path).exists():
            logger.info(f"🔄 最后兜底：本地视频 base64 上传 {local_path}")
            try:
                return await self.analyze_video_from_file(local_path, context)
            except Exception as file_error:
                errors.append(f"file: {file_error}")
                logger.error(f"❌ 本地视频文件分析失败: {file_error}")
        else:
            if local_path:
                logger.warning(f"⚠️ 本地视频文件不存在: {local_path}")
            errors.append("file: 无可用本地文件")

        # 全部失败
        raise Exception("视频分析全部降级路径均失败：" + " | ".join(errors))

    async def analyze_images_batch_with_fallback(
        self,
        image_urls: List[str],
        local_paths: Optional[List[str]] = None,
        context: Optional[str] = None,
        max_images: Optional[int] = None
    ) -> str:
        """
        批量分析多张图片并返回综合描述（带多级降级）

        ★ 已优化：默认一次请求把所有图片送入 Qwen-VL，提升上下文理解 & 速度

        降级顺序：
            1) 一次请求送入所有 URL（最快、上下文最完整）
            2) 一次请求送入所有本地图片（base64）
            3) 旧的逐张循环（每张独立 fallback，最后兜底）

        Args:
            image_urls: 图片URL列表
            local_paths: 本地文件路径列表（可选，与URLs对应）
            context: 上下文信息
            max_images: 最多分析的图片数量（默认从配置读取 settings.VL_MAX_IMAGES）

        Returns:
            所有图片的综合描述
        """
        if not image_urls:
            return ""

        # 从配置读取默认值
        if max_images is None:
            max_images = settings.VL_MAX_IMAGES

        # 限制分析数量
        urls_to_analyze = image_urls[:max_images]
        paths_to_use = (local_paths[:max_images]
                        if local_paths else [None] * len(urls_to_analyze))

        # ===== 降级 1：一次性请求所有 URL =====
        try:
            return await self._analyze_images_single_call(urls_to_analyze, context)
        except Exception as url_error:
            logger.warning(f"⚠️ 多图URL一次性分析失败，尝试本地文件: {str(url_error)}")

        # ===== 降级 2：一次性请求所有本地图片（base64） =====
        # 把所有有效的本地文件转 data url；缺失的本地文件则用对应的 URL 顶上
        mixed_payloads: List[str] = []
        any_local = False
        for url, local in zip(urls_to_analyze, paths_to_use):
            data_url = self._file_to_data_url(local) if local else None
            if data_url:
                mixed_payloads.append(data_url)
                any_local = True
            else:
                mixed_payloads.append(url)  # 没有本地文件，仍用 URL

        if any_local:
            try:
                return await self._analyze_images_single_call(mixed_payloads, context)
            except Exception as local_error:
                logger.warning(f"⚠️ 多图本地一次性分析失败，降级到逐张分析: {str(local_error)}")
        else:
            logger.warning("⚠️ 无可用本地文件，直接进入逐张分析降级")

        # ===== 降级 3：旧的逐张循环（最后兜底） =====
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
