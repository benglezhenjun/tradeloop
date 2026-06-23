"""个股信息 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.database import get_db

router = APIRouter(prefix="/api/stocks", tags=["个股"])


@router.get("/search")
def search_stocks(q: str = "", limit: int = 10, db: Session = Depends(get_db)):
    """按代码或名称模糊搜索股票（给"添加自选"弹窗用）"""
    if not q or len(q.strip()) == 0:
        return {"stocks": []}
    keyword = f"%{q.strip()}%"
    rows = db.execute(
        text("""
            SELECT ts_code, name, industry FROM stock_basic
            WHERE (ts_code LIKE :kw OR name LIKE :kw) AND list_status = 'L'
            LIMIT :lim
        """),
        {"kw": keyword, "lim": limit},
    ).mappings().all()
    return {
        "stocks": [
            {"ts_code": row["ts_code"], "name": row["name"], "industry": row["industry"]}
            for row in rows
        ]
    }


@router.get("/{ts_code}")
def get_stock_info(ts_code: str, db: Session = Depends(get_db)):
    """获取单只股票基本信息 + 最近 5 日行情"""
    basic = db.execute(
        text("SELECT ts_code, name, industry, market, list_date FROM stock_basic WHERE ts_code = :code"),
        {"code": ts_code},
    ).mappings().fetchone()

    if not basic:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code}")

    recent = db.execute(
        text("""
            SELECT trade_date, close, amount, total_mv, pct_chg
            FROM daily_quote WHERE ts_code = :code
            ORDER BY trade_date DESC LIMIT 5
        """),
        {"code": ts_code},
    ).mappings().all()

    return {
        "basic": {
            "ts_code": basic["ts_code"],
            "name": basic["name"],
            "industry": basic["industry"],
            "market": basic["market"],
            "list_date": basic["list_date"],
        },
        "recent_quotes": [
            {
                "trade_date": row["trade_date"],
                "close": round(row["close"], 2) if row["close"] else None,
                "amount_yi": round(row["amount"] / AMOUNT_UNIT_TO_YI, 2) if row["amount"] else None,
                "total_mv_yi": round(row["total_mv"] / MV_UNIT_TO_YI, 2) if row["total_mv"] else None,
                "pct_chg": round(row["pct_chg"], 2) if row["pct_chg"] else None,
            }
            for row in recent
        ],
    }
