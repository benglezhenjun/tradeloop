"""筛选执行 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import raise_service_error
from app.services.screening import run_strategy

router = APIRouter(prefix="/api/screening", tags=["筛选"])


@router.post("/run/{strategy_id}")
def run_screening(
    strategy_id: int,
    trade_date: str | None = None,
    db: Session = Depends(get_db),
):
    """
    运行指定策略

    参数：
        strategy_id: 策略ID
        trade_date: 可选，指定日期（YYYYMMDD），默认用最新交易日
    """
    result = run_strategy(db, strategy_id, trade_date)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/history/{strategy_id}")
def screening_history(strategy_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """获取策略的历史运行记录"""
    rows = db.execute(
        text("""
            SELECT id, strategy_name, trade_date, run_at, result_count, duration_ms
            FROM strategy_run
            WHERE strategy_id = :sid
            ORDER BY run_at DESC
            LIMIT :limit
        """),
        {"sid": strategy_id, "limit": limit},
    ).fetchall()

    return {
        "history": [
            {
                "run_id": r[0],
                "strategy_name": r[1],
                "trade_date": r[2],
                "run_at": r[3],
                "result_count": r[4],
                "duration_ms": r[5],
            }
            for r in rows
        ]
    }


@router.get("/result/{run_id}")
def get_run_result(run_id: int, db: Session = Depends(get_db)):
    """获取某次历史运行的详细结果"""
    import json
    rows = db.execute(
        text("SELECT ts_code, rank, snapshot FROM screening_result WHERE run_id = :rid ORDER BY rank"),
        {"rid": run_id},
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"运行记录 {run_id} 不存在或无结果")

    return {
        "run_id": run_id,
        "candidates": [
            {"ts_code": r[0], "rank": r[1], **json.loads(r[2] or "{}")}
            for r in rows
        ],
    }
