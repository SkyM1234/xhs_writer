"""
FastAPI 后端启动文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.api.v1.content_generation import router as content_router, init_app_instance
from app.api.v1.pending_tasks import router as pending_tasks_router
from app.core.cache import redis_cache
from app.agents import close_checkpointer
from app.core.logger import logger
from app.database.session import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：连接 Redis，初始化数据库表，初始化 LangGraph app（含 AsyncSqliteSaver）
    await redis_cache.connect()
    logger.info("✅ Redis 连接成功")

    # 创建数据库表
    try:
        await create_tables()
        logger.info("✅ 数据库表初始化成功")
    except Exception as e:
        logger.warning(f"⚠️ 数据库表初始化失败（可能已存在）: {e}")

    await init_app_instance()
    logger.info("✅ LangGraph checkpointer 初始化成功")

    yield

    # 关闭时：断开 Redis，关闭 checkpointer
    await redis_cache.close()
    logger.info("✅ Redis 连接已关闭")
    await close_checkpointer()
    logger.info("✅ LangGraph checkpointer 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="小红书内容生成 API",
    description="基于 LangGraph 的小红书内容生成工作流",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(content_router)
app.include_router(pending_tasks_router)

# 挂载静态文件目录（用于访问生成的笔记和图片）
outputs_dir = Path(__file__).parent / "data" / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# 根路径
@app.get("/")
async def root():
    return {
        "message": "小红书内容生成 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 健康检查
@app.get("/health")
async def health():
    return {"status": "healthy"}
