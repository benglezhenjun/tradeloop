"""市场情绪 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.market_sentiment import (
    get_sentiment_detail,
    get_sentiment_history,
    get_sentiment_summary,
    get_sentiment_themes,
)


router = APIRouter()


@router.get("/sentiment/summary")
def sentiment_summary(db: Session = Depends(get_db)):
    return get_sentiment_summary(db)


@router.get("/sentiment/history")
def sentiment_history(days: int = 120, db: Session = Depends(get_db)):
    return get_sentiment_history(db, days=days)


@router.get("/sentiment/themes")
def sentiment_themes(days: int = 120, db: Session = Depends(get_db)):
    return get_sentiment_themes(db, days=days)


@router.get("/sentiment/detail/{trade_date}")
def sentiment_detail(trade_date: str, db: Session = Depends(get_db)):
    return get_sentiment_detail(db, trade_date)
