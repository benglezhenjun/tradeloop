"""
仪表盘 API (V3)

提供三个市场温度端点，均为只读、无必填参数。
无数据时返回空结构，不返回 500。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.market import get_breadth_history, get_industry_heat, get_market_overview

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """当日市场概览。"""
    return get_market_overview(db)


@router.get("/industry_heat")
def industry_heat(db: Session = Depends(get_db)):
    """当日行业热度排行。"""
    return get_industry_heat(db)


@router.get("/breadth")
def breadth(days: int = 30, db: Session = Depends(get_db)):
    """近 N 日市场宽度。"""
    return get_breadth_history(db, days=days)
