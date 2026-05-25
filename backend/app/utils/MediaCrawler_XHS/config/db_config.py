# -*- coding: utf-8 -*-
"""
数据库配置文件（兼容层）
从项目配置中读取数据库配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]  # backend/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import settings

# MySQL 数据库配置（从项目配置读取）
mysql_db_config = {
    "host": settings.MYSQL_HOST,
    "port": settings.MYSQL_PORT,
    "user": settings.MYSQL_USER,
    "password": settings.MYSQL_PASSWORD,
    "db_name": settings.MYSQL_DATABASE,
}
