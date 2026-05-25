# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
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

# ==================== 基础配置 ====================

PLATFORM = "xhs"  # 平台

# 是否使用海外版小红书 (rednote.com)
# 开启后 API 走 webapi.rednote.com，cookie 域使用 .rednote.com
XHS_INTERNATIONAL = False

# ==================== 搜索配置 ====================

# 搜索关键词，多个关键词用英文逗号分隔
KEYWORDS = "生活技巧"

# ==================== 登录配置 ====================

# 登录方式: qrcode（二维码扫码）或 cookie（Cookie登录）
LOGIN_TYPE = "qrcode"

# Cookie 字符串（使用 cookie 登录时需要填写）
COOKIES = ""

# ==================== 爬取配置 ====================

# 爬取类型: search（关键词搜索）
CRAWLER_TYPE = "search"

# 是否显示浏览器窗口
# True: 无头模式（不显示浏览器）
# False: 显示浏览器（推荐，方便调试和手动验证）
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP 模式配置（推荐）====================
# CDP 模式使用本地 Chrome/Edge 浏览器，反检测能力更强

# 是否启用 CDP 模式
ENABLE_CDP_MODE = True

# CDP 调试端口
CDP_DEBUG_PORT = 11767

# 自定义浏览器路径（可选，留空自动检测）
# Windows 示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS 示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

# CDP 模式是否使用无头模式
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 60

# 是否连接已打开的浏览器（推荐）
# 需要在 Chrome 中开启远程调试：chrome://inspect/#remote-debugging
CDP_CONNECT_EXISTING = True

# 程序结束时是否自动关闭浏览器
AUTO_CLOSE_BROWSER = True

# ==================== 数据保存配置 ====================

# 数据保存格式: csv | json | jsonl | mysql
# csv | json | jsonl 只做爬虫测试，不保存到数据库
# 当使用爬虫作为agent时，强制选择 mysql 保存到数据库，service/xhs_crawler_service.py 中设置了：config.SAVE_DATA_OPTION = "mysql"
SAVE_DATA_OPTION = "jsonl"

# 数据保存路径（留空使用默认路径 data/）
SAVE_DATA_PATH = ""

# 浏览器缓存目录
USER_DATA_DIR = "%s_user_data_dir"  # %s 会被替换为平台名称

# ==================== 爬取控制 ====================

# 从第几页开始爬取
START_PAGE = 1

# 最多爬取多少页
CRAWLER_MAX_PAGES_COUNT = 20

# 最多爬取多少个笔记
CRAWLER_MAX_NOTES_COUNT = 1

# 并发爬取数量（建议设为1，避免被限流）
MAX_CONCURRENCY_NUM = 1

# 是否下载图片/视频
ENABLE_GET_MEIDAS = False

# 是否爬取评论
ENABLE_GET_COMMENTS = True

# 每个笔记最多爬取多少条一级评论
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 是否爬取二级评论
ENABLE_GET_SUB_COMMENTS = False

# 爬取间隔时间（秒）
CRAWLER_MAX_SLEEP_SEC = 2

# ==================== 小红书专属配置 ====================

# 导入小红书专属配置
from .xhs_config import *
