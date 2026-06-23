"""V8 backfill orchestration."""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from app.database import SessionLocal
from app.models import DailyMoneyflow, LimitEventDaily, MarketSentimentDaily, ThemeHeatDaily, TopList, TopListDetail
from app.services.data_sync import backfill_financial, run_full_sync, sync_lock
from app.services.market_sentiment import backfill_market_sentiment
from app.services.sync_indicator import backfill_indicators
from app.services.sync_limit_event import backfill_limit_event
from app.services.sync_moneyflow import backfill_moneyflow
from app.services.sync_theme_heat import backfill_theme_heat
from app.services.sync_toplist import backfill_toplist


logger = logging.getLogger(__name__)
_backfill_lock = threading.Lock()
_backfill_status: str = "idle"
_backfill_error: str | None = None
_backfill_finished_at: str | None = None
_backfill_thread: threading.Thread | None = None


def _log(message: str) -> None:
    logger.info("[backfill %s] %s", datetime.now().isoformat(timespec="seconds"), message)


def _set_backfill_state(
    *,
    status: str,
    error: str | None = None,
    finished_at: str | None = None,
) -> None:
    global _backfill_status, _backfill_error, _backfill_finished_at

    with _backfill_lock:
        _backfill_status = status
        _backfill_error = error
        _backfill_finished_at = finished_at


def get_backfill_state() -> dict:
    with _backfill_lock:
        return {
            "status": _backfill_status,
            "error": _backfill_error,
            "finished_at": _backfill_finished_at,
        }


def _reset_v8_market_tables(db) -> None:
    moneyflow_rows = db.query(DailyMoneyflow).count()
    toplist_rows = db.query(TopList).count()
    toplist_detail_rows = db.query(TopListDetail).count()
    limit_event_rows = db.query(LimitEventDaily).count()
    theme_heat_rows = db.query(ThemeHeatDaily).count()
    market_sentiment_rows = db.query(MarketSentimentDaily).count()
    if (
        moneyflow_rows
        or toplist_rows
        or toplist_detail_rows
        or limit_event_rows
        or theme_heat_rows
        or market_sentiment_rows
    ):
        _log(
            "reset partial V8 tables "
            f"moneyflow={moneyflow_rows} top_list={toplist_rows} "
            f"top_list_detail={toplist_detail_rows} limit_event={limit_event_rows} "
            f"theme_heat={theme_heat_rows} market_sentiment={market_sentiment_rows}"
        )
    db.query(MarketSentimentDaily).delete()
    db.query(ThemeHeatDaily).delete()
    db.query(LimitEventDaily).delete()
    db.query(DailyMoneyflow).delete()
    db.query(TopListDetail).delete()
    db.query(TopList).delete()
    db.commit()


def backfill_all(db) -> dict:
    _log("start daily_quote")
    daily_quote_result = run_full_sync(include_financial=False)
    _log("finish daily_quote")

    _reset_v8_market_tables(db)

    _log("start daily_moneyflow")
    daily_moneyflow_result = backfill_moneyflow(db)
    _log("finish daily_moneyflow")

    _log("start top_list")
    top_list_result = backfill_toplist(db)
    _log("finish top_list")

    _log("start limit_event_daily")
    limit_event_result = backfill_limit_event(db)
    _log("finish limit_event_daily")

    _log("start theme_heat_daily")
    theme_heat_result = backfill_theme_heat(db)
    _log("finish theme_heat_daily")

    _log("start market_sentiment_daily")
    market_sentiment_result = backfill_market_sentiment(db)
    _log("finish market_sentiment_daily")

    _log("start stock_financial")
    stock_financial_result = backfill_financial(db, use_lock=False)
    _log("finish stock_financial")

    _log("start daily_indicator")
    daily_indicator_result = backfill_indicators(db)
    _log("finish daily_indicator")

    return {
        "daily_quote": daily_quote_result,
        "daily_moneyflow": daily_moneyflow_result,
        "top_list": top_list_result,
        "limit_event_daily": limit_event_result,
        "theme_heat_daily": theme_heat_result,
        "market_sentiment_daily": market_sentiment_result,
        "stock_financial": stock_financial_result,
        "daily_indicator": daily_indicator_result,
    }


def _run_backfill_job():
    db = SessionLocal()
    try:
        _set_backfill_state(status="running", error=None, finished_at=None)
        backfill_all(db)
        _set_backfill_state(status="finished", error=None, finished_at=datetime.now().isoformat())
    except Exception as exc:
        _set_backfill_state(status="failed", error=str(exc), finished_at=datetime.now().isoformat())
        _log(f"failed error={exc}")
    finally:
        db.close()
        sync_lock.release()


def try_start_backfill() -> bool:
    global _backfill_thread

    acquired = sync_lock.acquire(blocking=False)
    if not acquired:
        return False

    _set_backfill_state(status="running", error=None, finished_at=None)
    thread = threading.Thread(target=_run_backfill_job, daemon=False, name="v8-backfill")
    try:
        thread.start()
    except Exception:
        _set_backfill_state(status="failed", error="failed to start backfill thread", finished_at=None)
        sync_lock.release()
        raise

    _backfill_thread = thread
    return True
