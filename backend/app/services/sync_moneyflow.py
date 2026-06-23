"""V8 moneyflow sync services."""

from __future__ import annotations

import logging
import time

import tushare as ts
from sqlalchemy import func

from app.config import BACKFILL_SLEEP, TUSHARE_TOKEN
from app.models import DailyMoneyflow, DailyQuote


logger = logging.getLogger(__name__)


def _get_api():
    if not TUSHARE_TOKEN:
        raise ValueError("Tushare token 未配置，请先在 config/local.toml 中填写。")
    return ts.pro_api(TUSHARE_TOKEN)


def _compute_net_amount(row) -> float:
    return (
        (row.get("buy_sm_amount") or 0)
        + (row.get("buy_md_amount") or 0)
        + (row.get("buy_lg_amount") or 0)
        + (row.get("buy_elg_amount") or 0)
        - (row.get("sell_sm_amount") or 0)
        - (row.get("sell_md_amount") or 0)
        - (row.get("sell_lg_amount") or 0)
        - (row.get("sell_elg_amount") or 0)
    )


def sync_moneyflow_daily(db, trade_dates: list[str]) -> dict:
    if not trade_dates:
        return {"synced_dates": 0, "successful_dates": 0, "failed_dates": [], "total_rows": 0}

    pro = _get_api()
    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []

    for idx, trade_date in enumerate(trade_dates):
        try:
            df = pro.moneyflow(
                trade_date=trade_date,
                fields=(
                    "ts_code,trade_date,net_mf_amount,net_mf_vol,buy_elg_amount,buy_lg_amount,"
                    "sell_elg_amount,sell_lg_amount,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount"
                ),
            )
            time.sleep(BACKFILL_SLEEP)

            rows = []
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    rows.append(
                        {
                            "ts_code": row["ts_code"],
                            "trade_date": row["trade_date"],
                            "net_mf_amount": row.get("net_mf_amount"),
                            "net_mf_vol": row.get("net_mf_vol"),
                            "net_amount": _compute_net_amount(row),
                            "buy_elg_amount": row.get("buy_elg_amount"),
                            "buy_lg_amount": row.get("buy_lg_amount"),
                        }
                    )

            with db.begin():
                db.query(DailyMoneyflow).filter(DailyMoneyflow.trade_date == trade_date).delete()
                if rows:
                    db.execute(DailyMoneyflow.__table__.insert(), rows)

            successful_dates += 1
            total_rows += len(rows)

            if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
                logger.info(
                    "[sync][moneyflow] %s/%s trade_date=%s rows=%s",
                    idx + 1,
                    len(trade_dates),
                    trade_date,
                    len(rows),
                )
        except Exception as exc:
            db.rollback()
            failed_dates.append({"trade_date": trade_date, "error": str(exc)})
            logger.exception("[sync][moneyflow] failed trade_date=%s", trade_date)
            time.sleep(2)

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }


def backfill_moneyflow(db, start_date: str = "20150101") -> dict:
    latest = db.query(func.max(DailyMoneyflow.trade_date)).scalar()
    query = db.query(DailyQuote.trade_date).filter(DailyQuote.trade_date >= start_date)
    if latest:
        query = query.filter(DailyQuote.trade_date > latest)
    trade_dates = [row[0] for row in query.distinct().order_by(DailyQuote.trade_date.asc()).all()]

    total_rows = 0
    for trade_date in trade_dates:
        result = sync_moneyflow_daily(db, [trade_date])
        total_rows += result["total_rows"]

    return {"synced_dates": len(trade_dates), "total_rows": total_rows}
