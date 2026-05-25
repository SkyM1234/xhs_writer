"""
图片下载工具
"""
import httpx
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, save_dir: str = "data/images"):
        """
        初始化图片下载器

        Args:
            save_dir: 图片保存目录
        """
        self.save_dir = Path(save_dir)
        # 目录会在实际下载时按需创建
    
    async def download_image(
        self,
        url: str,
        filename: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        下载单张图片
        
        Args:
            url: 图片 URL
            filename: 保存的文件名（可选，默认使用时间戳）
            max_retries: 最大重试次数
            
        Returns:
            本地文件路径，失败返回 None
        """
        if not filename:
            # 使用时间戳生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            ext = self._get_extension_from_url(url)
            filename = f"image_{timestamp}{ext}"
        
        filepath = self.save_dir / filename

        # 按需创建目录
        self.save_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # 保存图片
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ 图片下载成功: {filename}")
                    return str(filepath)
                    
            except Exception as e:
                print(f"⚠️ 图片下载失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"❌ 图片下载失败（已重试{max_retries}次）: {url}")
                    return None
    
    async def download_images(
        self,
        urls: List[str],
        prefix: Optional[str] = None,
        target_dir: Optional[str] = None
    ) -> List[str]:
        """
        批量下载图片

        Args:
            urls: 图片 URL 列表
            prefix: 文件名前缀（可选）
            target_dir: 目标保存目录（可选，默认使用 self.save_dir）

        Returns:
            本地文件路径列表
        """
        # 如果指定了目标目录，临时切换保存目录
        original_save_dir = self.save_dir
        if target_dir:
            self.save_dir = Path(target_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)

        try:
            tasks = []
            for i, url in enumerate(urls):
                if prefix:
                    filename = f"{prefix}_{i+1}{self._get_extension_from_url(url)}"
                else:
                    filename = None
                tasks.append(self.download_image(url, filename))

            results = await asyncio.gather(*tasks)
            # 过滤掉失败的下载（None）
            return [path for path in results if path is not None]
        finally:
            # 恢复原始保存目录
            self.save_dir = original_save_dir
    
    def _get_extension_from_url(self, url: str) -> str:
        """
        从 URL 中提取文件扩展名
        
        Args:
            url: 图片 URL
            
        Returns:
            文件扩展名（包含点号）
        """
        # 尝试从 URL 中提取扩展名
        if '.' in url.split('/')[-1]:
            ext = '.' + url.split('.')[-1].split('?')[0]
            # 验证是否是常见的图片格式
            if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                return ext
        
        # 默认使用 .jpg
        return '.jpg'
    
    def get_relative_path(self, filepath: str) -> str:
        """
        获取相对于项目根目录的路径
        
        Args:
            filepath: 绝对路径
            
        Returns:
            相对路径
        """
        try:
            abs_path = Path(filepath).resolve()
            # 返回相对于 backend 目录的路径
            return str(abs_path.relative_to(Path.cwd()))
        except ValueError:
            # 如果无法计算相对路径，返回原路径
            return filepath


# 全局实例
image_downloader = ImageDownloader()

