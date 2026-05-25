# -*- coding: utf-8 -*-
# 兼容层：重定向到项目根目录的数据库模块

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]  # backend/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 从项目数据库模块导入
from app.database.db import init_db, init_table_schema

# 为了兼容爬虫内部的日志，导入 tools.utils
from tools import utils

__all__ = ['init_db', 'init_table_schema']
