"""市场情绪原始涨停/炸板事件同步。"""

from __future__ import annotations

import logging
import time

import pandas as pd
import tushare as ts
from sqlalchemy import func

from app import credentials
from app.config import BACKFILL_SLEEP
from app.models import DailyQuote, LimitEventDaily


logger = logging.getLogger(__name__)
LIMIT_EVENT_FIELDS = (
    "ts_code,trade_date,name,limit,limit_times,up_stat,first_time,last_time,open_times,fd_amount"
)


def _get_api():
    token = credentials.tushare_token()
    if not token:
        raise ValueError("Tushare token 未配置，请在设置页填写，或在 config/local.toml 中填写 [tushare] token。")
    return ts.pro_api(token)


def _normalize_value(value):
    if value is None or pd.isna(value):
        return None
    return value


def sync_limit_event_daily(db, trade_dates: list[str]) -> dict:
    if not trade_dates:
        return {"synced_dates": 0, "successful_dates": 0, "failed_dates": [], "total_rows": 0}

    pro = _get_api()
    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []

    for idx, trade_date in enumerate(trade_dates):
        try:
            df = pro.limit_list_d(trade_date=trade_date, fields=LIMIT_EVENT_FIELDS)
            time.sleep(BACKFILL_SLEEP)

            rows = []
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    rows.append(
                        {
                            "ts_code": row.get("ts_code"),
                            "trade_date": row.get("trade_date"),
                            "name": _normalize_value(row.get("name")),
                            "limit_type": row.get("limit_type") or row.get("limit"),
                            "limit_times": _normalize_value(row.get("limit_times")),
                            "up_stat": _normalize_value(row.get("up_stat")),
                            "first_time": _normalize_value(row.get("first_time")),
                            "last_time": _normalize_value(row.get("last_time")),
                            "open_num": _normalize_value(row.get("open_num") or row.get("open_times")),
                            "fd_amount": _normalize_value(row.get("fd_amount")),
                            "source": "tushare.limit_list_d",
                        }
                    )

            db.query(LimitEventDaily).filter(LimitEventDaily.trade_date == trade_date).delete()
            if rows:
                db.execute(LimitEventDaily.__table__.insert(), rows)
            db.commit()

            successful_dates += 1
            total_rows += len(rows)

            if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
                logger.info(
                    "[sync][limit_event] %s/%s trade_date=%s rows=%s",
                    idx + 1,
                    len(trade_dates),
                    trade_date,
                    len(rows),
                )
        except Exception as exc:
            db.rollback()
            failed_dates.append({"trade_date": trade_date, "error": str(exc)})
            logger.exception("[sync][limit_event] failed trade_date=%s", trade_date)
            time.sleep(2)

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }


def backfill_limit_event(db, start_date: str = "20150101") -> dict:
    latest = db.query(func.max(LimitEventDaily.trade_date)).scalar()
    query = db.query(DailyQuote.trade_date).filter(DailyQuote.trade_date >= start_date)
    if latest:
        query = query.filter(DailyQuote.trade_date > latest)
    trade_dates = [row[0] for row in query.distinct().order_by(DailyQuote.trade_date.asc()).all()]
    db.commit()

    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []
    for trade_date in trade_dates:
        result = sync_limit_event_daily(db, [trade_date])
        total_rows += result["total_rows"]
        successful_dates += result["successful_dates"]
        failed_dates.extend(result["failed_dates"])

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }
