"""持仓 API。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.envelope import list_envelope
from app.database import get_db
from app.errors import raise_service_error
from app.services import position as position_service
from app.services.trade_contract import format_position

router = APIRouter()


@router.get("/position")
def list_positions(
    status: Literal["holding", "closed"] | None = Query(None),
    db: Session = Depends(get_db),
):
    result = position_service.list_positions(db, status=status)
    if "error" in result:
        raise_service_error(result)
    return list_envelope(result["positions"])


@router.get("/position/summary")
def get_position_summary(db: Session = Depends(get_db)):
    return position_service.get_position_summary(db)


@router.post("/position/{ts_code}/recalc")
def recalculate_position(ts_code: str, db: Session = Depends(get_db)):
    result = position_service.recalculate_position(db, ts_code)
    if isinstance(result, dict) and "error" in result:
        raise_service_error(result)
    return {"position": None if result is None else format_position(result)}


@router.get("/position/{ts_code}")
def get_position_detail(ts_code: str, db: Session = Depends(get_db)):
    result = position_service.get_position_detail(db, ts_code)
    if result is None:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return result
