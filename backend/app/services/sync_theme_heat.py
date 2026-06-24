"""市场情绪原始题材热度同步。"""

from __future__ import annotations

import logging
import time

import pandas as pd
import tushare as ts
from sqlalchemy import func

from app import credentials
from app.config import BACKFILL_SLEEP
from app.models import DailyQuote, ThemeHeatDaily


logger = logging.getLogger(__name__)
THEME_HEAT_FIELDS = "trade_date,data_type,ts_code,ts_name,rank,concept,rank_reason,hot,rank_time"
THEME_HEAT_MARKET = "概念板块"


def _get_api():
    token = credentials.tushare_token()
    if not token:
        raise ValueError("Tushare token 未配置，请在设置页填写，或在 config/local.toml 中填写 [tushare] token。")
    return ts.pro_api(token)


def _normalize_value(value):
    if value is None or pd.isna(value):
        return None
    return value


def _compute_theme_score(row) -> float:
    hot = row.get("hot")
    if hot is not None and not pd.isna(hot):
        return float(hot)
    rank = int(row.get("rank") or 0)
    return float(max(0, 100 - rank))


def _rank_time_key(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _dedupe_theme_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    ranked = df.copy()
    if "rank_time" in ranked.columns:
        ranked["_rank_time_key"] = ranked["rank_time"].map(_rank_time_key)
    else:
        ranked["_rank_time_key"] = ""
    if "hot" in ranked.columns:
        ranked["_hot_key"] = ranked["hot"].fillna(0)
    else:
        ranked["_hot_key"] = 0
    ranked = ranked.sort_values(
        by=["trade_date", "ts_code", "_rank_time_key", "_hot_key"],
        ascending=[True, True, False, False],
    )
    ranked = ranked.drop_duplicates(subset=["trade_date", "ts_code"], keep="first")
    return ranked.drop(columns=["_rank_time_key", "_hot_key"], errors="ignore")


def sync_theme_heat_daily(db, trade_dates: list[str]) -> dict:
    if not trade_dates:
        return {"synced_dates": 0, "successful_dates": 0, "failed_dates": [], "total_rows": 0}

    pro = _get_api()
    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []

    for idx, trade_date in enumerate(trade_dates):
        try:
            df = pro.ths_hot(
                trade_date=trade_date,
                market=THEME_HEAT_MARKET,
                is_new="N",
                fields=THEME_HEAT_FIELDS,
            )
            time.sleep(BACKFILL_SLEEP)

            rows = []
            if df is not None and not df.empty:
                df = _dedupe_theme_rows(df)
                for _, row in df.iterrows():
                    rows.append(
                        {
                            "trade_date": row.get("trade_date"),
                            "theme_code": row.get("ts_code") or row.get("theme_code"),
                            "theme_name": _normalize_value(row.get("ts_name") or row.get("theme_name")),
                            "rank": _normalize_value(row.get("rank")),
                            "up_nums": None,
                            "cons_nums": None,
                            "up_stat": _normalize_value(row.get("rank_reason")),
                            "score": _compute_theme_score(row),
                            "source": "tushare.ths_hot.concept",
                        }
                    )

            db.query(ThemeHeatDaily).filter(ThemeHeatDaily.trade_date == trade_date).delete()
            if rows:
                db.execute(ThemeHeatDaily.__table__.insert(), rows)
            db.commit()

            successful_dates += 1
            total_rows += len(rows)

            if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
                logger.info(
                    "[sync][theme_heat] %s/%s trade_date=%s rows=%s",
                    idx + 1,
                    len(trade_dates),
                    trade_date,
                    len(rows),
                )
        except Exception as exc:
            db.rollback()
            failed_dates.append({"trade_date": trade_date, "error": str(exc)})
            logger.exception("[sync][theme_heat] failed trade_date=%s", trade_date)
            time.sleep(2)

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }


def backfill_theme_heat(db, start_date: str = "20150101") -> dict:
    latest = db.query(func.max(ThemeHeatDaily.trade_date)).scalar()
    query = db.query(DailyQuote.trade_date).filter(DailyQuote.trade_date >= start_date)
    if latest:
        query = query.filter(DailyQuote.trade_date > latest)
    trade_dates = [row[0] for row in query.distinct().order_by(DailyQuote.trade_date.asc()).all()]
    db.commit()

    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []
    for trade_date in trade_dates:
        result = sync_theme_heat_daily(db, [trade_date])
        total_rows += result["total_rows"]
        successful_dates += result["successful_dates"]
        failed_dates.extend(result["failed_dates"])

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }
