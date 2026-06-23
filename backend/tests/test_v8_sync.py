from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    import app.models  # noqa: F401
    from app.database import Base

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    from app.api import data as data_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(data_api.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code="600000.SH", name="PF Bank"):
    from app.models import StockBasic

    db.add(
        StockBasic(
            ts_code=ts_code,
            name=name,
            industry="Bank",
            market="Main",
            list_date="20200101",
            list_status="L",
        )
    )
    db.commit()


def insert_quotes(db, ts_code="600000.SH", count=30, start="2026-03-01"):
    from app.models import DailyQuote

    start_date = datetime.strptime(start, "%Y-%m-%d")
    for idx in range(count):
        trade_date = (start_date + timedelta(days=idx)).strftime("%Y%m%d")
        close = 10.0 + idx
        db.add(
            DailyQuote(
                ts_code=ts_code,
                trade_date=trade_date,
                open=close - 0.2,
                high=close + 0.3,
                low=close - 0.4,
                close=close,
                vol=1000 + idx * 10,
                amount=200000 + idx * 100,
                pct_chg=0.5,
                total_mv=500000,
                turnover_rate=1.0 + idx * 0.05,
            )
        )
    db.commit()


class FakeFinancialPro:
    def fina_indicator(self, **kwargs):
        ts_code = kwargs["ts_code"]
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "ann_date": "20260401",
                    "end_date": "20251231",
                    "profit_dedt": 110.0,
                    "revenue": 220.0,
                    "eps": 1.5,
                    "gross_margin": 32.0,
                },
                {
                    "ts_code": ts_code,
                    "ann_date": "20260301",
                    "end_date": "20251231",
                    "profit_dedt": 100.0,
                    "revenue": 200.0,
                    "eps": 1.2,
                    "gross_margin": 30.0,
                },
                {
                    "ts_code": ts_code,
                    "ann_date": "20260201",
                    "end_date": "20250930",
                    "profit_dedt": 90.0,
                    "revenue": 180.0,
                    "eps": 1.0,
                    "gross_margin": 28.0,
                },
            ]
        )


class FakeMoneyflowPro:
    def moneyflow(self, trade_date, fields):
        assert "buy_sm_amount" in fields
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "net_mf_amount": 10.0,
                    "net_mf_vol": 2.0,
                    "buy_elg_amount": 20.0,
                    "buy_lg_amount": 10.0,
                    "sell_elg_amount": 5.0,
                    "sell_lg_amount": 3.0,
                    "buy_sm_amount": 6.0,
                    "sell_sm_amount": 2.0,
                    "buy_md_amount": 4.0,
                    "sell_md_amount": 1.0,
                }
            ]
        )


class FakeMoneyflowPartialFailurePro:
    def moneyflow(self, trade_date, fields):
        if trade_date == "20260408":
            raise RuntimeError("moneyflow unavailable")
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "net_mf_amount": 10.0,
                    "net_mf_vol": 2.0,
                    "buy_elg_amount": 20.0,
                    "buy_lg_amount": 10.0,
                    "sell_elg_amount": 5.0,
                    "sell_lg_amount": 3.0,
                    "buy_sm_amount": 6.0,
                    "sell_sm_amount": 2.0,
                    "buy_md_amount": 4.0,
                    "sell_md_amount": 1.0,
                }
            ]
        )


class FakeTopListPro:
    def top_list(self, trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": "PF Bank",
                    "close": 12.3,
                    "pct_change": 3.2,
                    "turnover_rate": 4.1,
                    "amount": 80000.0,
                    "l_buy": 1200.0,
                    "l_sell": 500.0,
                    "net_amount": 700.0,
                    "net_rate": 0.5,
                    "amount_rate": 0.1,
                    "float_values": 600000.0,
                    "reason": "deviation",
                }
            ]
        )

    def top_inst(self, trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "exalter": "Institution",
                    "buy": 300.0,
                    "sell": 50.0,
                    "net_buy": 250.0,
                    "side": "buy",
                    "reason": "deviation",
                }
            ]
        )


class FakeTopListDuplicatePro:
    def top_list(self, trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": "PF Bank",
                    "close": 12.3,
                    "pct_change": 3.2,
                    "turnover_rate": 4.1,
                    "amount": 80000.0,
                    "l_buy": 1200.0,
                    "l_sell": 500.0,
                    "net_amount": 700.0,
                    "net_rate": 0.5,
                    "amount_rate": 0.1,
                    "float_values": None,
                    "reason": "deviation",
                },
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": "PF Bank",
                    "close": 12.3,
                    "pct_change": 3.2,
                    "turnover_rate": 4.1,
                    "amount": 80000.0,
                    "l_buy": 1200.0,
                    "l_sell": 500.0,
                    "net_amount": 700.0,
                    "net_rate": 0.5,
                    "amount_rate": 0.1,
                    "float_values": 600000.0,
                    "reason": "deviation",
                },
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": "PF Bank",
                    "close": 12.3,
                    "pct_change": 3.2,
                    "turnover_rate": 4.1,
                    "amount": 80000.0,
                    "l_buy": 1200.0,
                    "l_sell": 500.0,
                    "net_amount": 700.0,
                    "net_rate": 0.5,
                    "amount_rate": 0.1,
                    "float_values": 600000.0,
                    "reason": "deviation",
                },
            ]
        )

    def top_inst(self, trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "exalter": "Institution",
                    "buy": 300.0,
                    "sell": 50.0,
                    "net_buy": 250.0,
                    "side": "buy",
                    "reason": "deviation",
                }
            ]
        )


class FakeTopListPartialFailurePro(FakeTopListPro):
    def top_list(self, trade_date):
        if trade_date == "20260408":
            raise RuntimeError("toplist unavailable")
        return super().top_list(trade_date)


def test_sync_financial_data_maps_full_fields_and_keeps_annual_reports(db):
    from app.models import StockFinancial
    from app.services.data_sync import sync_financial_data

    insert_stock(db)

    with patch("app.services.data_sync.SessionLocal", return_value=db), patch(
        "app.services.data_sync._get_api", return_value=FakeFinancialPro()
    ), patch("app.services.data_sync.time.sleep", return_value=None):
        sync_financial_data()

    rows = db.query(StockFinancial).all()
    assert len(rows) == 1
    assert rows[0].ann_date == "20260401"
    assert rows[0].profit_dedt == 110.0
    assert rows[0].eps == 1.5
    assert rows[0].gross_margin == 32.0


def test_sync_moneyflow_daily_replaces_existing_trade_date_rows(db):
    from app.models import DailyMoneyflow
    from app.services.sync_moneyflow import sync_moneyflow_daily

    db.add(
        DailyMoneyflow(
            ts_code="600000.SH",
            trade_date="20260407",
            net_mf_amount=1.0,
            net_mf_vol=1.0,
            net_amount=1.0,
            buy_elg_amount=1.0,
            buy_lg_amount=1.0,
        )
    )
    db.commit()

    with patch("app.services.sync_moneyflow.ts.pro_api", return_value=FakeMoneyflowPro()), patch(
        "app.services.sync_moneyflow.time.sleep", return_value=None
    ):
        result = sync_moneyflow_daily(db, ["20260407"])

    rows = db.query(DailyMoneyflow).all()
    assert result["synced_dates"] == 1
    assert result["successful_dates"] == 1
    assert result["failed_dates"] == []
    assert result["total_rows"] == 1
    assert len(rows) == 1
    assert rows[0].net_amount == pytest.approx(29.0)


def test_sync_moneyflow_daily_reports_failed_dates(db):
    from app.services.sync_moneyflow import sync_moneyflow_daily

    with patch("app.services.sync_moneyflow.ts.pro_api", return_value=FakeMoneyflowPartialFailurePro()), patch(
        "app.services.sync_moneyflow.time.sleep", return_value=None
    ):
        result = sync_moneyflow_daily(db, ["20260407", "20260408"])

    assert result["synced_dates"] == 2
    assert result["successful_dates"] == 1
    assert result["total_rows"] == 1
    assert len(result["failed_dates"]) == 1
    assert result["failed_dates"][0]["trade_date"] == "20260408"


def test_backfill_financial_requires_sync_lock_when_called_directly(db):
    from app.services import data_sync

    insert_stock(db)

    acquired = data_sync.sync_lock.acquire(blocking=False)
    assert acquired is True
    try:
        with patch("app.services.data_sync._get_api", return_value=FakeFinancialPro()), patch(
            "app.services.data_sync.time.sleep", return_value=None
        ):
            with pytest.raises(RuntimeError, match="already running"):
                data_sync.backfill_financial(db)
    finally:
        data_sync.sync_lock.release()


def test_sync_toplist_daily_replaces_existing_trade_date_rows(db):
    from app.models import TopList, TopListDetail
    from app.services.sync_toplist import sync_toplist_daily

    db.add(TopList(ts_code="600000.SH", trade_date="20260407", reason="old"))
    db.add(TopListDetail(ts_code="600000.SH", trade_date="20260407", reason="old"))
    db.commit()

    with patch("app.services.sync_toplist.ts.pro_api", return_value=FakeTopListPro()), patch(
        "app.services.sync_toplist.time.sleep", return_value=None
    ):
        result = sync_toplist_daily(db, ["20260407"])

    assert result == {
        "synced_dates": 1,
        "successful_dates": 1,
        "failed_dates": [],
        "top_list_rows": 1,
        "detail_rows": 1,
    }
    assert db.query(TopList).count() == 1
    assert db.query(TopListDetail).count() == 1
    assert db.query(TopList).one().reason == "deviation"


def test_sync_toplist_daily_deduplicates_same_reason_and_keeps_more_complete_row(db):
    from app.models import TopList
    from app.services.sync_toplist import sync_toplist_daily

    with patch("app.services.sync_toplist.ts.pro_api", return_value=FakeTopListDuplicatePro()), patch(
        "app.services.sync_toplist.time.sleep", return_value=None
    ):
        result = sync_toplist_daily(db, ["20260407"])

    rows = db.query(TopList).all()
    assert result == {
        "synced_dates": 1,
        "successful_dates": 1,
        "failed_dates": [],
        "top_list_rows": 1,
        "detail_rows": 1,
    }
    assert len(rows) == 1
    assert rows[0].reason == "deviation"
    assert rows[0].float_values == 600000.0


def test_sync_toplist_daily_reports_failed_dates(db):
    from app.services.sync_toplist import sync_toplist_daily

    with patch("app.services.sync_toplist.ts.pro_api", return_value=FakeTopListPartialFailurePro()), patch(
        "app.services.sync_toplist.time.sleep", return_value=None
    ):
        result = sync_toplist_daily(db, ["20260407", "20260408"])

    assert result["synced_dates"] == 2
    assert result["successful_dates"] == 1
    assert result["top_list_rows"] == 1
    assert result["detail_rows"] == 1
    assert len(result["failed_dates"]) == 1
    assert result["failed_dates"][0]["trade_date"] == "20260408"


def test_sync_indicators_daily_calculates_and_inserts_rows(db):
    from app.models import DailyIndicator
    from app.services.sync_indicator import sync_indicators_daily

    insert_stock(db)
    insert_quotes(db, count=30)
    target_date = (datetime.strptime("2026-03-01", "%Y-%m-%d") + timedelta(days=29)).strftime(
        "%Y%m%d"
    )

    result = sync_indicators_daily(db, [target_date])

    row = db.get(DailyIndicator, ("600000.SH", target_date))
    assert result == {"synced_dates": 1, "total_rows": 1}
    assert row is not None
    assert row.ma5 is not None
    assert row.macd_dif is not None


def test_sync_daily_calls_v8_steps_in_order():
    from app.services import data_sync

    calls: list[str] = []

    def record(name):
        def _inner(*args, **kwargs):
            calls.append(name)
            return ["20260407"] if name == "daily_quotes" else {"status": "ok"}

        return _inner

    class DummySession:
        def close(self):
            return None

    with patch.object(data_sync, "SessionLocal", return_value=DummySession()), patch.object(
        data_sync, "sync_stock_basic", record("stock_basic")
    ), patch.object(
        data_sync, "sync_daily_quotes", record("daily_quotes")
    ), patch.object(data_sync, "sync_moneyflow_daily", record("moneyflow")), patch.object(
        data_sync, "sync_toplist_daily", record("toplist")
    ), patch.object(data_sync, "sync_limit_event_daily", record("limit_event")), patch.object(
        data_sync, "sync_theme_heat_daily", record("theme_heat")
    ), patch.object(data_sync, "sync_market_sentiment_daily", record("market_sentiment")), patch.object(
        data_sync, "sync_indicators_daily", record("indicator")
    ), patch.object(
        data_sync, "sync_financial_data", side_effect=AssertionError("sync_financial_data should not run in sync_daily")
    ):
        data_sync.sync_daily()

    assert calls == [
        "stock_basic",
        "daily_quotes",
        "moneyflow",
        "toplist",
        "limit_event",
        "theme_heat",
        "market_sentiment",
        "indicator",
    ]


def test_backfill_helpers_do_not_error_on_empty_db(db):
    from app.services.sync_indicator import backfill_indicators
    from app.services.sync_moneyflow import backfill_moneyflow
    from app.services.sync_toplist import backfill_toplist

    assert backfill_moneyflow(db) == {"synced_dates": 0, "total_rows": 0}
    assert backfill_toplist(db) == {"synced_dates": 0, "top_list_rows": 0, "detail_rows": 0}
    assert backfill_indicators(db) == {"synced_stocks": 0, "total_rows": 0}


def test_backfill_all_resets_partial_recent_v8_tables_before_full_replay(db):
    from app.models import DailyMoneyflow, TopList
    from app.services.backfill import backfill_all

    db.add(
        DailyMoneyflow(
            ts_code="600000.SH",
            trade_date="20260403",
            net_mf_amount=1.0,
            net_mf_vol=1.0,
            net_amount=1.0,
            buy_elg_amount=1.0,
            buy_lg_amount=1.0,
        )
    )
    db.add(TopList(ts_code="600000.SH", trade_date="20260403", reason="recent-only"))
    db.commit()

    calls: list[tuple[str, int, int]] = []

    def fake_run_full_sync(*args, **kwargs):
        return {"quotes": 1}

    def fake_moneyflow(db_session, *args, **kwargs):
        calls.append(
            (
                "moneyflow",
                db_session.query(DailyMoneyflow).count(),
                db_session.query(DailyMoneyflow.trade_date).distinct().count(),
            )
        )
        return {"moneyflow": 1}

    def fake_toplist(db_session, *args, **kwargs):
        calls.append(
            (
                "toplist",
                db_session.query(TopList).count(),
                db_session.query(TopList.trade_date).distinct().count(),
            )
        )
        return {"toplist": 1}

    with patch("app.services.backfill.run_full_sync", fake_run_full_sync), patch(
        "app.services.backfill.backfill_moneyflow", fake_moneyflow
    ), patch("app.services.backfill.backfill_toplist", fake_toplist), patch(
        "app.services.backfill.backfill_financial", return_value={"financial": 1}
    ), patch("app.services.backfill.backfill_indicators", return_value={"indicator": 1}):
        result = backfill_all(db)

    assert ("moneyflow", 0, 0) in calls
    assert ("toplist", 0, 0) in calls
    assert result["daily_quote"] == {"quotes": 1}


def test_backfill_all_runs_stages_in_order(db):
    from app.services.backfill import backfill_all

    calls: list[str] = []

    def record(name, result):
        def _inner(*args, **kwargs):
            calls.append(name)
            return result

        return _inner

    with patch("app.services.backfill.run_full_sync", record("quotes", {"quotes": 1})), patch(
        "app.services.backfill.backfill_moneyflow", record("moneyflow", {"moneyflow": 1})
    ), patch("app.services.backfill.backfill_toplist", record("toplist", {"toplist": 1})), patch(
        "app.services.backfill.backfill_financial", record("financial", {"financial": 1})
    ), patch("app.services.backfill.backfill_indicators", record("indicator", {"indicator": 1})):
        result = backfill_all(db)

    assert calls == ["quotes", "moneyflow", "toplist", "financial", "indicator"]
    assert result["daily_quote"] == {"quotes": 1}
    assert result["daily_indicator"] == {"indicator": 1}


def test_daily_sync_job_swallows_start_errors():
    from app.services.scheduler import _daily_sync_job

    with patch("app.services.data_sync.try_start_sync", side_effect=RuntimeError("boom")):
        _daily_sync_job()


def test_backfill_trigger_returns_started(client):
    with patch("app.api.data.try_start_backfill", return_value=True):
        response = client.post("/api/data/backfill/trigger")

    assert response.status_code == 200
    assert response.json() == {"status": "started"}
