"""
FastAPI 应用入口。

V8 主要变化：
- 新增交易记录与持仓 API
- 启动时继续统一初始化内置策略与默认配置
- /api/health 版本号切换到 V8
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analysis,
    dashboard,
    data,
    kline,
    plan,
    position,
    review,
    screening,
    sentiment,
    stocks,
    strategies,
    trade,
    user_config,
    watchlist,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("正在启动 A股交易辅助系统 V8...")

    from app.services.data_sync import init_tables

    init_tables()

    from app.database import SessionLocal
    from app.services.strategy import init_builtin_strategies
    from app.services.user_config import ensure_default_configs

    db = SessionLocal()
    try:
        init_builtin_strategies(db)
        ensure_default_configs(db)
        logger.info("内置策略与默认配置已初始化")
    finally:
        db.close()

    from app.services.scheduler import start_scheduler

    start_scheduler()
    logger.info("系统启动完成，访问 http://localhost:8000/docs 查看 API 文档。")
    yield

    from app.services.scheduler import stop_scheduler

    stop_scheduler()
    logger.info("系统已关闭")


app = FastAPI(
    title="A股交易辅助系统",
    description="个人交易研究工作台",
    version="8.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(data.router)
app.include_router(strategies.router)
app.include_router(screening.router)
app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(kline.router)
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(sentiment.router, prefix="/api/dashboard")
app.include_router(analysis.router, prefix="/api/analysis")
app.include_router(plan.router, prefix="/api")
app.include_router(trade.router, prefix="/api")
app.include_router(position.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(user_config.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "version": "8.0.0",
        "message": "A股交易辅助系统 V8 运行中",
    }
