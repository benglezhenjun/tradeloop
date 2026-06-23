"""V8 toplist sync services."""

from __future__ import annotations

import logging
import time

import pandas as pd
import tushare as ts
from sqlalchemy import func

from app.config import BACKFILL_SLEEP, TUSHARE_TOKEN
from app.models import DailyQuote, TopList, TopListDetail


logger = logging.getLogger(__name__)


def _get_api():
    if not TUSHARE_TOKEN:
        raise ValueError("Tushare token 未配置，请先在 config/local.toml 中填写。")
    return ts.pro_api(TUSHARE_TOKEN)


def _value_present(value) -> bool:
    return value is not None and pd.notna(value) and value != ""


def _dedupe_top_list_rows(rows: list[dict]) -> list[dict]:
    deduped: dict[tuple[str | None, str | None, str | None], tuple[int, dict]] = {}
    for row in rows:
        key = (row.get("ts_code"), row.get("trade_date"), row.get("reason"))
        score = sum(_value_present(row.get(field)) for field in row.keys())
        current = deduped.get(key)
        if current is None or score > current[0]:
            deduped[key] = (score, row)
    return [item[1] for item in deduped.values()]


def sync_toplist_daily(db, trade_dates: list[str]) -> dict:
    if not trade_dates:
        return {
            "synced_dates": 0,
            "successful_dates": 0,
            "failed_dates": [],
            "top_list_rows": 0,
            "detail_rows": 0,
        }

    pro = _get_api()
    top_list_rows = 0
    detail_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []

    for idx, trade_date in enumerate(trade_dates):
        try:
            list_df = pro.top_list(trade_date=trade_date)
            time.sleep(BACKFILL_SLEEP)
            detail_df = pro.top_inst(trade_date=trade_date)
            time.sleep(BACKFILL_SLEEP)

            list_rows = []
            if list_df is not None and not list_df.empty:
                for _, row in list_df.iterrows():
                    list_rows.append(
                        {
                            "ts_code": row.get("ts_code"),
                            "trade_date": row.get("trade_date"),
                            "name": row.get("name"),
                            "close": row.get("close"),
                            "pct_change": row.get("pct_change"),
                            "turnover_rate": row.get("turnover_rate"),
                            "amount": row.get("amount"),
                            "l_buy": row.get("l_buy"),
                            "l_sell": row.get("l_sell"),
                            "net_amount": row.get("net_amount"),
                            "net_rate": row.get("net_rate"),
                            "amount_rate": row.get("amount_rate"),
                            "float_values": row.get("float_values"),
                            "reason": row.get("reason"),
                        }
                    )
                list_rows = _dedupe_top_list_rows(list_rows)

            detail_rows_payload = []
            if detail_df is not None and not detail_df.empty:
                for _, row in detail_df.iterrows():
                    detail_rows_payload.append(
                        {
                            "ts_code": row.get("ts_code"),
                            "trade_date": row.get("trade_date"),
                            "exalter": row.get("exalter"),
                            "buy": row.get("buy"),
                            "sell": row.get("sell"),
                            "net_buy": row.get("net_buy"),
                            "side": row.get("side"),
                            "reason": row.get("reason"),
                        }
                    )

            with db.begin():
                db.query(TopList).filter(TopList.trade_date == trade_date).delete()
                db.query(TopListDetail).filter(TopListDetail.trade_date == trade_date).delete()
                if list_rows:
                    db.execute(TopList.__table__.insert(), list_rows)
                if detail_rows_payload:
                    db.execute(TopListDetail.__table__.insert(), detail_rows_payload)
            top_list_rows += len(list_rows)
            detail_rows += len(detail_rows_payload)
            successful_dates += 1

            if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
                logger.info(
                    "[sync][toplist] %s/%s trade_date=%s list_rows=%s detail_rows=%s",
                    idx + 1,
                    len(trade_dates),
                    trade_date,
                    len(list_rows),
                    len(detail_rows_payload),
                )
        except Exception as exc:
            db.rollback()
            failed_dates.append({"trade_date": trade_date, "error": str(exc)})
            logger.exception("[sync][toplist] failed trade_date=%s", trade_date)
            time.sleep(2)

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "top_list_rows": top_list_rows,
        "detail_rows": detail_rows,
    }


def backfill_toplist(db, start_date: str = "20150101") -> dict:
    latest = db.query(func.max(TopList.trade_date)).scalar()
    query = db.query(DailyQuote.trade_date).filter(DailyQuote.trade_date >= start_date)
    if latest:
        query = query.filter(DailyQuote.trade_date > latest)
    trade_dates = [row[0] for row in query.distinct().order_by(DailyQuote.trade_date.asc()).all()]

    total_top_list_rows = 0
    total_detail_rows = 0
    for trade_date in trade_dates:
        result = sync_toplist_daily(db, [trade_date])
        total_top_list_rows += result["top_list_rows"]
        total_detail_rows += result["detail_rows"]

    return {
        "synced_dates": len(trade_dates),
        "top_list_rows": total_top_list_rows,
        "detail_rows": total_detail_rows,
    }
