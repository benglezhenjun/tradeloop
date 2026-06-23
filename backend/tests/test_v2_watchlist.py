"""
V2 watchlist feature tests.
"""

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


def seed_stock_basic(db, ts_code: str, name: str = "Test Stock", industry: str = "Bank") -> None:
    db.execute(
        text(
            """
            INSERT INTO stock_basic (ts_code, name, industry, market, list_date, list_status)
            VALUES (:ts_code, :name, :industry, 'Main', '20200101', 'L')
            """
        ),
        {"ts_code": ts_code, "name": name, "industry": industry},
    )
    db.commit()


def seed_daily_quote(
    db,
    ts_code: str,
    trade_date: str,
    close: float,
    amount: float = 100000.0,
    pct_chg: float = 1.23,
    total_mv: float = 1000000.0,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO daily_quote (
                ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate
            )
            VALUES (
                :ts_code, :trade_date, :open, :high, :low, :close, :vol, :amount, :pct_chg, :total_mv, :turnover_rate
            )
            """
        ),
        {
            "ts_code": ts_code,
            "trade_date": trade_date,
            "open": close - 1,
            "high": close + 1,
            "low": close - 2,
            "close": close,
            "vol": 1000.0,
            "amount": amount,
            "pct_chg": pct_chg,
            "total_mv": total_mv,
            "turnover_rate": 1.0,
        },
    )
    db.commit()


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)

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
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_group(db):
    from app.services.watchlist import create_group, list_groups

    result = create_group(db, "Focus", "Best stocks")
    assert result["name"] == "Focus"
    assert result["id"] is not None

    groups = list_groups(db)
    assert len(groups) == 1
    assert groups[0]["stock_count"] == 0


def test_update_group(db):
    from app.services.watchlist import create_group, update_group

    g = create_group(db, "Old Name")
    result = update_group(db, g["id"], name="New Name")
    assert result["name"] == "New Name"


def test_delete_group(db):
    from app.services.watchlist import create_group, delete_group, list_groups

    g = create_group(db, "Temp")
    assert delete_group(db, g["id"]) is True
    assert len(list_groups(db)) == 0


def test_delete_nonexistent_group(db):
    from app.services.watchlist import delete_group

    assert delete_group(db, 999) is False


def test_add_and_remove_stock(db):
    from app.services.watchlist import create_group, add_stock, remove_stock

    seed_stock_basic(db, "000001.SZ")
    g = create_group(db, "Test Group")
    result = add_stock(db, g["id"], "000001.SZ", "Bank leader")
    assert result["ts_code"] == "000001.SZ"

    assert remove_stock(db, g["id"], "000001.SZ") is True
    assert remove_stock(db, g["id"], "000001.SZ") is False


def test_duplicate_stock_returns_error(db):
    from app.services.watchlist import create_group, add_stock

    seed_stock_basic(db, "000001.SZ")
    g = create_group(db, "Test Group")
    add_stock(db, g["id"], "000001.SZ")
    result = add_stock(db, g["id"], "000001.SZ")
    assert "error" in result
    assert "000001.SZ" in result["error"]


def test_cascade_delete(db):
    from app.services.watchlist import create_group, add_stock, delete_group

    seed_stock_basic(db, "000001.SZ")
    seed_stock_basic(db, "600036.SH")
    g = create_group(db, "Temp Group")
    add_stock(db, g["id"], "000001.SZ")
    add_stock(db, g["id"], "600036.SH")

    count = db.execute(text("SELECT COUNT(*) FROM watchlist_stock WHERE group_id = :gid"), {"gid": g["id"]}).scalar()
    assert count == 2

    delete_group(db, g["id"])

    count = db.execute(text("SELECT COUNT(*) FROM watchlist_stock WHERE group_id = :gid"), {"gid": g["id"]}).scalar()
    assert count == 0


def test_add_to_nonexistent_group(db):
    from app.services.watchlist import add_stock

    seed_stock_basic(db, "000001.SZ")
    result = add_stock(db, 999, "000001.SZ")
    assert "error" in result


def test_add_stock_rejects_unknown_ts_code(db):
    from app.services.watchlist import create_group, add_stock

    g = create_group(db, "Test Group")
    result = add_stock(db, g["id"], "FAKE.CODE")
    assert "error" in result
    assert "FAKE.CODE" in result["error"]


def test_add_stock_strips_ts_code_whitespace(db):
    from app.services.watchlist import create_group, add_stock

    seed_stock_basic(db, "000001.SZ")
    g = create_group(db, "Trim Group")
    result = add_stock(db, g["id"], "000001.SZ ")
    assert result["ts_code"] == "000001.SZ"


def test_batch_add_keeps_valid_rows_and_reports_invalid_codes(db):
    from app.services.watchlist import create_group, add_stock, batch_add_stocks

    seed_stock_basic(db, "000001.SZ")
    seed_stock_basic(db, "600036.SH")
    seed_stock_basic(db, "000002.SZ")

    g = create_group(db, "Batch Group")
    add_stock(db, g["id"], "000001.SZ")

    result = batch_add_stocks(db, g["id"], ["600036.SH", "600036.SH", "000001.SZ", "FAKE.CODE", "000002.SZ"])
    assert result["added"] == 2
    assert result["skipped_existing"] == 1
    assert result["skipped_invalid"] == 1
    assert result["skipped"] == 2
    assert result["invalid_codes"] == ["FAKE.CODE"]

    rows = db.execute(
        text("SELECT ts_code FROM watchlist_stock WHERE group_id = :gid ORDER BY id"),
        {"gid": g["id"]},
    ).fetchall()
    assert [row[0] for row in rows] == ["000001.SZ", "600036.SH", "000002.SZ"]


def test_group_stocks_use_each_stock_latest_quote(db):
    from app.services.watchlist import create_group, add_stock, get_group_stocks

    seed_stock_basic(db, "000001.SZ")
    seed_stock_basic(db, "600036.SH")
    seed_daily_quote(db, "000001.SZ", "20260102", 10.5, pct_chg=1.1)
    seed_daily_quote(db, "000001.SZ", "20260103", 11.5, pct_chg=2.2)
    seed_daily_quote(db, "600036.SH", "20260101", 20.5, pct_chg=3.3)

    g = create_group(db, "Latest Quotes")
    add_stock(db, g["id"], "000001.SZ")
    add_stock(db, g["id"], "600036.SH")

    stocks = get_group_stocks(db, g["id"])
    assert {s["ts_code"] for s in stocks} == {"000001.SZ", "600036.SH"}
    assert {s["ts_code"]: s["close"] for s in stocks} == {"000001.SZ": 11.5, "600036.SH": 20.5}


def test_all_stocks_use_each_stock_latest_quote(db):
    from app.services.watchlist import create_group, add_stock, get_all_stocks

    seed_stock_basic(db, "000001.SZ")
    seed_stock_basic(db, "600036.SH")
    seed_daily_quote(db, "000001.SZ", "20260102", 10.5, pct_chg=1.1)
    seed_daily_quote(db, "000001.SZ", "20260103", 11.5, pct_chg=2.2)
    seed_daily_quote(db, "600036.SH", "20260101", 20.5, pct_chg=3.3)

    g = create_group(db, "Latest Quotes")
    add_stock(db, g["id"], "000001.SZ")
    add_stock(db, g["id"], "600036.SH")

    stocks = get_all_stocks(db)
    assert {s["ts_code"] for s in stocks} == {"000001.SZ", "600036.SH"}
    assert {s["ts_code"]: s["close"] for s in stocks} == {"000001.SZ": 11.5, "600036.SH": 20.5}
