"""系统探针：存活 (health) 与就绪 (ready)。"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import APP_VERSION
from app.database import get_db

router = APIRouter(tags=["系统"])


@router.get("/api/health")
def health_check():
    """存活探针：进程是否在运行（不查数据库）。"""
    return {
        "status": "ok",
        "version": APP_VERSION,
        "message": "A股交易辅助系统 V8 运行中",
    }


@router.get("/api/ready")
def readiness_check(db: Session = Depends(get_db)):
    """就绪探针：数据库可达且已有行情数据时才算就绪（否则 503）。

    与 /api/health 区分：health 只看进程存活，ready 看能否真正对外提供服务，
    适合容器编排的 readiness probe 与"先导数据再放流量"的场景。
    """
    try:
        db.execute(text("SELECT 1"))
        quote_count = db.execute(text("SELECT COUNT(*) FROM daily_quote")).scalar() or 0
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "version": APP_VERSION, "reason": str(exc)},
        )

    ready = quote_count > 0
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "no_data",
            "version": APP_VERSION,
            "quote_count": quote_count,
        },
    )
