"""交易记录 API。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import raise_service_error
from app.services import trade as trade_service

router = APIRouter()


class TradeCreate(BaseModel):
    ts_code: str
    stock_name: str
    direction: Literal["buy", "sell"]
    price: float
    quantity: int
    trade_date: str
    trade_time: str | None = None
    fee: float | None = None
    note: str | None = None
    plan_id: int | None = None


@router.post("/trade", status_code=201)
def create_trade(body: TradeCreate, db: Session = Depends(get_db)):
    result = trade_service.create_trade(db, body.model_dump())
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/trade")
def list_trades(
    ts_code: str | None = Query(None),
    direction: Literal["buy", "sell"] | None = Query(None),
    db: Session = Depends(get_db),
):
    result = trade_service.list_trades(db, ts_code=ts_code, direction=direction)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/trade/{trade_id}")
def get_trade_detail(trade_id: int, db: Session = Depends(get_db)):
    result = trade_service.get_trade_detail(db, trade_id)
    if result is None:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    return result


@router.delete("/trade/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    result = trade_service.delete_trade(db, trade_id)
    if "error" in result:
        raise_service_error(result)
    return result
