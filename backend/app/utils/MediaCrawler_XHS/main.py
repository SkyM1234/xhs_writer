# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/main.py
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

import sys
import io

# Force UTF-8 encoding for stdout/stderr to prevent encoding errors
# when outputting Chinese characters in non-UTF-8 terminals
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from typing import Optional

import config
from base.base_crawler import AbstractCrawler
from media_platform.xhs import XiaoHongShuCrawler


class CrawlerFactory:
    """爬虫工厂类"""
    
    CRAWLERS: dict[str, type[AbstractCrawler]] = {
        "xhs": XiaoHongShuCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                f"Invalid media platform: {platform!r}. "
                f"Only 'xhs' is supported in ultra minimal version."
            )
        return crawler_class()


crawler: Optional[AbstractCrawler] = None


async def main() -> None:
    """主函数"""
    global crawler

    # 初始化MySQL数据库（如果启用）
    if config.SAVE_DATA_OPTION == "mysql":
        from database.db import init_db
        await init_db(config.SAVE_DATA_OPTION)
        print(f"[Main] {config.SAVE_DATA_OPTION} database initialized successfully!")

    # 创建爬虫实例
    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    
    # 开始爬取
    await crawler.start()

    print("[Main] Crawling completed successfully!")


async def async_cleanup() -> None:
    """异步清理资源"""
    global crawler
    if crawler:
        # 清理 CDP 浏览器
        if getattr(crawler, "cdp_manager", None):
            try:
                await crawler.cdp_manager.cleanup(force=True)
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] Error cleaning up CDP browser: {e}")

        # 清理普通浏览器上下文
        elif getattr(crawler, "browser_context", None):
            try:
                await crawler.browser_context.close()
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] Error closing browser context: {e}")


if __name__ == "__main__":
    from tools.app_runner import run

    def _force_stop() -> None:
        """强制停止浏览器"""
        c = crawler
        if not c:
            return
        cdp_manager = getattr(c, "cdp_manager", None)
        launcher = getattr(cdp_manager, "launcher", None)
        if not launcher:
            return
        try:
            launcher.cleanup()
        except Exception:
            pass

    run(main, async_cleanup, cleanup_timeout_seconds=15.0, on_first_interrupt=_force_stop)
