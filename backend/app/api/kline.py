"""K线数据 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import kline as kline_svc

router = APIRouter(prefix="/api/kline", tags=["K线"])


@router.get("/{ts_code}")
def get_kline(
    ts_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """
    获取K线数据（OHLCV）

    - 不传日期参数：返回最近 180 个交易日
    - 传 start_date / end_date：返回指定范围
    """
    result = kline_svc.get_kline(db, ts_code, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code}")
    return result
