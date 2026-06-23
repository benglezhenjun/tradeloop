"""数据统计和同步相关 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.backfill import get_backfill_state, try_start_backfill
from app.services.screening import get_available_dates, get_data_stats

router = APIRouter(prefix="/api/data", tags=["数据"])


@router.get("/stats")
def data_stats(db: Session = Depends(get_db)):
    """数据库统计：股票数、行情条数、财务条数、最新交易日。"""
    return get_data_stats(db)


@router.get("/dates")
def available_dates(db: Session = Depends(get_db)):
    """获取最近 30 个交易日。"""
    dates = get_available_dates(db)
    return {"dates": dates}


@router.post("/sync/trigger")
def trigger_sync():
    """手动触发每日数据同步。"""
    from app.services.data_sync import get_sync_state, try_start_sync
    import threading

    if get_sync_state()["status"] == "running":
        return {"status": "already_running", "message": "已有同步任务在运行中，请稍后再试"}

    thread = threading.Thread(target=try_start_sync, daemon=True)
    thread.start()
    return {"status": "accepted", "message": "数据同步已在后台启动，请稍后刷新统计数据"}


@router.post("/backfill/trigger")
def trigger_backfill():
    if not try_start_backfill():
        return {"status": "already_running", "message": "已有同步或回填任务在运行中，请稍后再试"}
    return {"status": "started"}


@router.get("/backfill/status")
def backfill_status():
    return get_backfill_state()


@router.get("/sync/status")
def sync_status():
    """查询当前同步状态：idle / running / finished / failed。"""
    from app.services.data_sync import get_sync_state

    return get_sync_state()
