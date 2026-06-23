from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
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


def insert_stock(db, ts_code, name):
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


def insert_quotes(db, ts_code, count=5, start="2026-03-01", close_base=10.0):
    from app.models import DailyQuote

    start_date = datetime.strptime(start, "%Y-%m-%d")
    for idx in range(count):
        trade_date = (start_date + timedelta(days=idx)).strftime("%Y%m%d")
        close = close_base + idx
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


def test_backfill_indicators_raises_when_indicator_rows_length_mismatches_quotes(db):
    from app.services.sync_indicator import backfill_indicators

    insert_stock(db, "600000.SH", "PF Bank")
    insert_quotes(db, "600000.SH", count=5)

    def fake_calculate_stock_indicators(quotes, prev_state=None):
        return ([{"ma5": float(idx)} for idx in range(len(quotes) - 1)], {})

    with patch("app.services.sync_indicator.calculate_stock_indicators", fake_calculate_stock_indicators):
        with pytest.raises(ValueError):
            backfill_indicators(db)


def test_sync_indicators_daily_skips_single_stock_failures_and_keeps_processing(db):
    from app.models import DailyIndicator
    from app.services.sync_indicator import sync_indicators_daily

    insert_stock(db, "600000.SH", "PF Bank")
    insert_stock(db, "000001.SZ", "Test Bank")
    insert_quotes(db, "600000.SH", count=5, close_base=10.0)
    insert_quotes(db, "000001.SZ", count=5, close_base=20.0)

    target_date = (datetime.strptime("2026-03-01", "%Y-%m-%d") + timedelta(days=4)).strftime(
        "%Y%m%d"
    )

    def fake_calculate_stock_indicators(quotes, prev_state=None):
        if quotes[0]["close"] >= 20.0:
            raise RuntimeError("single stock failure")
        return ([{"ma5": 5.0} for _ in quotes], {})

    with patch("app.services.sync_indicator.calculate_stock_indicators", fake_calculate_stock_indicators):
        result = sync_indicators_daily(db, [target_date])

    rows = db.query(DailyIndicator).order_by(DailyIndicator.ts_code).all()
    assert result == {"synced_dates": 1, "total_rows": 1}
    assert len(rows) == 1
    assert rows[0].ts_code == "600000.SH"
    assert rows[0].trade_date == target_date


def test_sync_indicators_daily_reraises_database_errors_and_stops_batch(db):
    from app.services.sync_indicator import sync_indicators_daily

    insert_stock(db, "600000.SH", "PF Bank")
    insert_stock(db, "000001.SZ", "Test Bank")
    insert_quotes(db, "600000.SH", count=5, close_base=10.0)
    insert_quotes(db, "000001.SZ", count=5, close_base=20.0)

    target_date = (datetime.strptime("2026-03-01", "%Y-%m-%d") + timedelta(days=4)).strftime(
        "%Y%m%d"
    )
    call_count = 0

    def fake_calculate_stock_indicators(quotes, prev_state=None):
        nonlocal call_count
        call_count += 1
        raise OperationalError("SELECT 1", {}, RuntimeError("db down"))

    with patch("app.services.sync_indicator.calculate_stock_indicators", fake_calculate_stock_indicators):
        with pytest.raises(OperationalError):
            sync_indicators_daily(db, [target_date])

    assert call_count == 1


def test_sync_indicators_daily_keeps_existing_rows_when_no_new_rows_generated(db):
    from app.models import DailyIndicator
    from app.services.sync_indicator import sync_indicators_daily

    insert_stock(db, "600000.SH", "PF Bank")
    insert_quotes(db, "600000.SH", count=5, close_base=10.0)

    target_date = (datetime.strptime("2026-03-01", "%Y-%m-%d") + timedelta(days=4)).strftime(
        "%Y%m%d"
    )
    db.add(DailyIndicator(ts_code="600000.SH", trade_date=target_date, ma5=3.0))
    db.commit()

    def fake_calculate_stock_indicators(quotes, prev_state=None):
        raise RuntimeError("all stocks failed")

    with patch("app.services.sync_indicator.calculate_stock_indicators", fake_calculate_stock_indicators):
        result = sync_indicators_daily(db, [target_date])

    row = db.get(DailyIndicator, ("600000.SH", target_date))
    assert result == {"synced_dates": 1, "total_rows": 0}
    assert row is not None
    assert row.ma5 == pytest.approx(3.0)
