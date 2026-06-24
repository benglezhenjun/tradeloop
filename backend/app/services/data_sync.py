"""
数据同步服务。

V8 主要改动：
- 历史数据范围改为从固定起始日期开始
- 财务数据改为全字段拉取与动态映射
- 每日同步扩展到资金流向、龙虎榜、指标计算
"""

import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import tushare as ts
from alembic import command
from alembic.config import Config

from app import credentials
from app.config import BACKFILL_SLEEP, HISTORY_START_DATE
from app.database import SessionLocal
from app.models import DailyQuote, StockBasic, StockFinancial
from app.services.market_sentiment import sync_market_sentiment_daily
from app.services.sync_indicator import sync_indicators_daily
from app.services.sync_limit_event import sync_limit_event_daily
from app.services.sync_moneyflow import sync_moneyflow_daily
from app.services.sync_theme_heat import sync_theme_heat_daily
from app.services.sync_toplist import sync_toplist_daily


logger = logging.getLogger(__name__)
_sync_lock = threading.Lock()
_sync_state_lock = threading.Lock()
sync_lock = _sync_lock
_sync_status: str = "idle"
_sync_error: str | None = None
_sync_finished_at: str | None = None


def get_sync_state() -> dict:
    with _sync_state_lock:
        return {
            "status": _sync_status,
            "error": _sync_error,
            "finished_at": _sync_finished_at,
        }


def _set_sync_state(*, status: str, error: str | None = None, finished_at: str | None = None) -> None:
    global _sync_status, _sync_error, _sync_finished_at

    with _sync_state_lock:
        _sync_status = status
        _sync_error = error
        _sync_finished_at = finished_at


def try_start_sync() -> bool:
    acquired = _sync_lock.acquire(blocking=False)
    if not acquired:
        return False

    _set_sync_state(status="running", error=None, finished_at=None)
    try:
        sync_daily()
        _set_sync_state(status="finished", error=None, finished_at=datetime.now().isoformat())
    except Exception as exc:
        _set_sync_state(status="failed", error=str(exc), finished_at=datetime.now().isoformat())
        logger.exception("daily sync failed")
    finally:
        _sync_lock.release()
    return True


def _get_api():
    token = credentials.tushare_token()
    if not token:
        raise ValueError("Tushare token 未配置，请在设置页填写，或在 config/local.toml 中填写 [tushare] token。")
    return ts.pro_api(token)


@contextmanager
def _session_scope():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_tables():
    backend_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


def sync_stock_basic():
    logger.info("sync stock basic start")
    pro = _get_api()
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,name,industry,market,list_date,list_status",
    )
    logger.info("sync stock basic fetched stocks=%s", len(df))

    with _session_scope() as db:
        for _, row in df.iterrows():
            stock = db.get(StockBasic, row["ts_code"])
            if stock:
                stock.name = row["name"]
                stock.industry = row.get("industry")
                stock.market = row.get("market")
                stock.list_date = row.get("list_date")
                stock.list_status = row.get("list_status", "L")
            else:
                db.add(
                    StockBasic(
                        ts_code=row["ts_code"],
                        name=row["name"],
                        industry=row.get("industry"),
                        market=row.get("market"),
                        list_date=row.get("list_date"),
                        list_status=row.get("list_status", "L"),
                    )
                )
        db.commit()
        logger.info("sync stock basic finished")


def sync_daily_quotes(start_date: str, end_date: str):
    logger.info("sync daily quotes start start_date=%s end_date=%s", start_date, end_date)
    pro = _get_api()
    cal = pro.trade_cal(exchange="SSE", start_date=start_date, end_date=end_date, is_open="1")
    trade_dates = sorted(cal["cal_date"].tolist())
    logger.info("sync daily quotes trade_dates=%s", len(trade_dates))

    with _session_scope() as db:
        for idx, date in enumerate(trade_dates):
            try:
                df_daily = pro.daily(trade_date=date)
                time.sleep(BACKFILL_SLEEP)
                df_basic = pro.daily_basic(
                    trade_date=date,
                    fields="ts_code,trade_date,total_mv,turnover_rate",
                )
                time.sleep(BACKFILL_SLEEP)

                if df_daily is None or df_daily.empty:
                    continue

                if df_basic is not None and not df_basic.empty:
                    df = pd.merge(df_daily, df_basic, on=["ts_code", "trade_date"], how="left")
                else:
                    df = df_daily

                rows = []
                for _, row in df.iterrows():
                    rows.append(
                        {
                            "ts_code": row["ts_code"],
                            "trade_date": row["trade_date"],
                            "open": row.get("open"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "close": row.get("close"),
                            "vol": row.get("vol"),
                            "amount": row.get("amount"),
                            "pct_chg": row.get("pct_chg"),
                            "total_mv": row.get("total_mv"),
                            "turnover_rate": row.get("turnover_rate"),
                        }
                    )

                if rows:
                    with db.begin():
                        db.query(DailyQuote).filter(DailyQuote.trade_date == date).delete()
                        db.execute(DailyQuote.__table__.insert(), rows)

                if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
                    logger.info(
                        "sync daily quotes progress current=%s total=%s trade_date=%s",
                        idx + 1,
                        len(trade_dates),
                        date,
                    )
            except Exception:
                logger.exception("sync daily quotes failed trade_date=%s", date)
                db.rollback()
                time.sleep(2)
    return trade_dates


def _filter_financial_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    annual = df[df["end_date"].astype(str).str.endswith("1231")]
    if annual.empty:
        return annual
    return annual.sort_values("ann_date", ascending=False).drop_duplicates(
        subset=["ts_code", "end_date"], keep="first"
    )


def _row_to_financial_payload(row: pd.Series, model_columns: set[str]) -> dict:
    payload = {}
    for column in row.index:
        if column not in model_columns:
            continue
        value = row.get(column)
        if pd.isna(value):
            value = None
        payload[column] = value

    payload["ann_date"] = payload.get("ann_date") or "00000000"
    return payload


def sync_financial_data():
    logger.info("sync financial data start")
    pro = _get_api()

    with _session_scope() as db:
        ts_codes = [row[0] for row in db.query(StockBasic.ts_code).all()]
        logger.info("sync financial data stocks=%s", len(ts_codes))
        total_rows = 0
        model_columns = set(StockFinancial.__table__.columns.keys())
        for idx, code in enumerate(ts_codes):
            try:
                df = pro.fina_indicator(ts_code=code)
                time.sleep(BACKFILL_SLEEP)
                filtered = _filter_financial_rows(df)
                if filtered.empty:
                    continue

                for _, row in filtered.iterrows():
                    payload = _row_to_financial_payload(row, model_columns)
                    key = (payload["ts_code"], payload["ann_date"], payload["end_date"])
                    if db.get(StockFinancial, key):
                        continue
                    db.add(StockFinancial(**payload))
                    total_rows += 1

                if (idx + 1) % 100 == 0:
                    db.commit()
                    logger.info(
                        "sync financial data progress current=%s total=%s rows=%s",
                        idx + 1,
                        len(ts_codes),
                        total_rows,
                    )
            except Exception:
                logger.exception("sync financial data failed ts_code=%s", code)
                db.rollback()
                time.sleep(2)

        db.commit()
        logger.info("sync financial data finished rows=%s", total_rows)


def backfill_financial(db, *, use_lock: bool = True) -> dict:
    acquired = False
    if use_lock:
        acquired = sync_lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("sync task already running")

    try:
        pro = _get_api()
        with db.begin():
            db.query(StockFinancial).delete()

        ts_codes = [row[0] for row in db.query(StockBasic.ts_code).all()]
        model_columns = set(StockFinancial.__table__.columns.keys())
        total_rows = 0
        synced_stocks = 0

        for idx, code in enumerate(ts_codes):
            try:
                df = pro.fina_indicator(ts_code=code)
                time.sleep(BACKFILL_SLEEP)
                filtered = _filter_financial_rows(df)
                if filtered.empty:
                    synced_stocks += 1
                    continue

                for _, row in filtered.iterrows():
                    payload = _row_to_financial_payload(row, model_columns)
                    db.add(StockFinancial(**payload))
                    total_rows += 1

                synced_stocks += 1
                if (idx + 1) % 100 == 0:
                    db.commit()
                    logger.info(
                        "backfill financial progress current=%s total=%s rows=%s",
                        idx + 1,
                        len(ts_codes),
                        total_rows,
                    )
            except Exception:
                logger.exception("backfill financial failed ts_code=%s", code)
                db.rollback()
                time.sleep(2)

        db.commit()
        return {"synced_stocks": synced_stocks, "total_rows": total_rows}
    finally:
        if acquired:
            sync_lock.release()


def sync_daily():
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
    logger.info("daily sync start start_date=%s end_date=%s", start_date, end_date)
    sync_stock_basic()
    trade_dates = sync_daily_quotes(start_date, end_date) or []

    if not isinstance(trade_dates, list):
        trade_dates = []

    with _session_scope() as db:
        if trade_dates:
            sync_moneyflow_daily(db, trade_dates)
            sync_toplist_daily(db, trade_dates)
            sync_limit_event_daily(db, trade_dates)
            sync_theme_heat_daily(db, trade_dates)
            sync_market_sentiment_daily(db, trade_dates)
            sync_indicators_daily(db, trade_dates)
    logger.info("daily sync finished")


def run_full_sync(include_financial: bool = True) -> dict:
    logger.info("full sync start history_start_date=%s include_financial=%s", HISTORY_START_DATE, include_financial)

    init_tables()
    sync_stock_basic()
    end_date = datetime.now().strftime("%Y%m%d")
    sync_daily_quotes(HISTORY_START_DATE, end_date)
    if include_financial:
        sync_financial_data()

    logger.info("full sync finished end_date=%s", end_date)
    return {
        "start_date": HISTORY_START_DATE,
        "end_date": end_date,
        "include_financial": include_financial,
    }


if __name__ == "__main__":
    run_full_sync()
