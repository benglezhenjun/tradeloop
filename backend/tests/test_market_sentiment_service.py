import json

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


def insert_quote(db, ts_code: str, trade_date: str, pct_chg: float):
    from app.models import DailyQuote

    db.add(
        DailyQuote(
            ts_code=ts_code,
            trade_date=trade_date,
            open=10.0,
            high=10.3,
            low=9.8,
            close=10.1,
            vol=1000.0,
            amount=100000.0,
            pct_chg=pct_chg,
            total_mv=500000.0,
            turnover_rate=1.0,
        )
    )
    db.commit()


def insert_limit_event(
    db,
    *,
    ts_code: str,
    trade_date: str,
    limit_type: str,
    limit_times: int,
    name: str | None = None,
):
    from app.models import LimitEventDaily

    db.add(
        LimitEventDaily(
            ts_code=ts_code,
            trade_date=trade_date,
            limit_type=limit_type,
            name=name or ts_code,
            limit_times=limit_times,
            up_stat=f"{limit_times}/{limit_times}",
            source="test",
        )
    )
    db.commit()


def insert_theme_heat(
    db,
    *,
    trade_date: str,
    theme_code: str,
    theme_name: str,
    rank: int,
    score: float,
):
    from app.models import ThemeHeatDaily

    db.add(
        ThemeHeatDaily(
            trade_date=trade_date,
            theme_code=theme_code,
            theme_name=theme_name,
            rank=rank,
            score=score,
            source="test",
        )
    )
    db.commit()


def insert_sentiment_snapshot(
    db,
    *,
    trade_date: str,
    main_theme_code: str | None,
    main_theme_name: str | None,
    main_theme_score: float | None,
    main_theme_streak_days: int,
):
    from app.models import MarketSentimentDaily

    db.add(
        MarketSentimentDaily(
            trade_date=trade_date,
            main_theme_code=main_theme_code,
            main_theme_name=main_theme_name,
            main_theme_score=main_theme_score,
            main_theme_streak_days=main_theme_streak_days,
            notes_json="{}",
        )
    )
    db.commit()


def test_calculate_max_limit_height_returns_highest_board_summary():
    from app.models import LimitEventDaily
    from app.services.market_sentiment import calculate_max_limit_height

    rows = [
        LimitEventDaily(ts_code="000001.SZ", trade_date="20260408", limit_type="U", limit_times=4),
        LimitEventDaily(ts_code="000002.SZ", trade_date="20260408", limit_type="U", limit_times=4),
        LimitEventDaily(ts_code="000003.SZ", trade_date="20260408", limit_type="U", limit_times=2),
    ]

    result = calculate_max_limit_height(rows)

    assert result == {
        "max_limit_height": 4,
        "max_limit_height_count": 2,
        "max_limit_height_codes": ["000001.SZ", "000002.SZ"],
    }


def test_calculate_max_limit_height_returns_zero_when_empty():
    from app.services.market_sentiment import calculate_max_limit_height

    result = calculate_max_limit_height([])

    assert result == {
        "max_limit_height": 0,
        "max_limit_height_count": 0,
        "max_limit_height_codes": [],
    }


def test_calculate_broken_rate_handles_zero_denominator():
    from app.services.market_sentiment import calculate_broken_rate

    assert calculate_broken_rate(limit_up_count=0, limit_broken_count=0) == 0.0


def test_calculate_yday_limit_premium_uses_previous_limit_pool(db):
    from app.services.market_sentiment import calculate_yday_limit_premium

    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260401", limit_type="U", limit_times=2)
    insert_limit_event(db, ts_code="000002.SZ", trade_date="20260401", limit_type="U", limit_times=1)
    insert_quote(db, "000001.SZ", "20260401", 9.9)
    insert_quote(db, "000002.SZ", "20260401", 9.9)
    insert_quote(db, "000001.SZ", "20260402", 5.0)
    insert_quote(db, "000002.SZ", "20260402", -2.0)

    result = calculate_yday_limit_premium(db, "20260402")

    assert result["yday_limit_premium_avg"] == pytest.approx(1.5)
    assert result["yday_limit_premium_median"] == pytest.approx(1.5)
    assert result["yday_limit_red_rate"] == pytest.approx(0.5)
    assert result["yday_limit_sample_count"] == 2
    assert result["sample_codes"] == ["000001.SZ", "000002.SZ"]


def test_calculate_high_board_promotion_rate_counts_exact_advances(db):
    from app.services.market_sentiment import calculate_high_board_promotion_rate

    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260401", limit_type="U", limit_times=3)
    insert_limit_event(db, ts_code="000002.SZ", trade_date="20260401", limit_type="U", limit_times=4)
    insert_limit_event(db, ts_code="000003.SZ", trade_date="20260401", limit_type="U", limit_times=2)
    insert_quote(db, "000001.SZ", "20260401", 9.9)
    insert_quote(db, "000002.SZ", "20260401", 9.9)
    insert_quote(db, "000003.SZ", "20260401", 9.9)
    insert_quote(db, "000001.SZ", "20260402", 9.9)
    insert_quote(db, "000002.SZ", "20260402", 3.0)
    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260402", limit_type="U", limit_times=4)
    insert_limit_event(db, ts_code="000002.SZ", trade_date="20260402", limit_type="U", limit_times=4)

    result = calculate_high_board_promotion_rate(db, "20260402", threshold=3)

    assert result["high_board_threshold"] == 3
    assert result["high_board_total"] == 2
    assert result["high_board_advanced"] == 1
    assert result["high_board_promotion_rate"] == pytest.approx(0.5)
    assert result["candidate_codes"] == ["000001.SZ", "000002.SZ"]
    assert result["advanced_codes"] == ["000001.SZ"]


def test_calculate_main_theme_streak_reuses_previous_snapshot(db):
    from app.services.market_sentiment import calculate_main_theme_streak

    insert_sentiment_snapshot(
        db,
        trade_date="20260401",
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=120.0,
        main_theme_streak_days=2,
    )
    insert_quote(db, "000001.SZ", "20260401", 1.0)
    insert_quote(db, "000001.SZ", "20260402", 2.0)
    insert_theme_heat(
        db,
        trade_date="20260402",
        theme_code="BK001",
        theme_name="机器人",
        rank=1,
        score=150.0,
    )
    insert_theme_heat(
        db,
        trade_date="20260402",
        theme_code="BK002",
        theme_name="算力",
        rank=2,
        score=99.0,
    )

    result = calculate_main_theme_streak(db, "20260402")

    assert result == {
        "main_theme_code": "BK001",
        "main_theme_name": "机器人",
        "main_theme_score": 150.0,
        "main_theme_streak_days": 3,
    }


def test_save_market_sentiment_snapshot_persists_computed_row(db):
    from app.models import MarketSentimentDaily
    from app.services.market_sentiment import save_market_sentiment_snapshot

    insert_sentiment_snapshot(
        db,
        trade_date="20260401",
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=100.0,
        main_theme_streak_days=2,
    )
    insert_quote(db, "000001.SZ", "20260401", 9.9)
    insert_quote(db, "000002.SZ", "20260401", 9.9)
    insert_quote(db, "000001.SZ", "20260402", 4.0)
    insert_quote(db, "000002.SZ", "20260402", -1.5)
    insert_quote(db, "000003.SZ", "20260402", 9.9)
    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260401", limit_type="U", limit_times=3, name="高标一")
    insert_limit_event(db, ts_code="000002.SZ", trade_date="20260401", limit_type="U", limit_times=1, name="首板二")
    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260402", limit_type="U", limit_times=4, name="高标一")
    insert_limit_event(db, ts_code="000003.SZ", trade_date="20260402", limit_type="U", limit_times=4, name="高标三")
    insert_limit_event(db, ts_code="000004.SZ", trade_date="20260402", limit_type="Z", limit_times=2, name="炸板四")
    insert_theme_heat(db, trade_date="20260402", theme_code="BK001", theme_name="机器人", rank=1, score=180.0)
    insert_theme_heat(db, trade_date="20260402", theme_code="BK002", theme_name="算力", rank=2, score=120.0)

    payload = save_market_sentiment_snapshot(db, "20260402")
    row = db.get(MarketSentimentDaily, "20260402")
    notes = json.loads(row.notes_json)

    assert payload["trade_date"] == "20260402"
    assert row is not None
    assert row.max_limit_height == 4
    assert row.max_limit_height_count == 2
    assert json.loads(row.max_limit_height_codes_json) == ["000001.SZ", "000003.SZ"]
    assert row.limit_up_count == 2
    assert row.limit_broken_count == 1
    assert row.broken_rate == pytest.approx(1 / 3)
    assert row.yday_limit_premium_avg == pytest.approx(1.25)
    assert row.yday_limit_premium_median == pytest.approx(1.25)
    assert row.yday_limit_red_rate == pytest.approx(0.5)
    assert row.yday_limit_sample_count == 2
    assert row.high_board_threshold == 3
    assert row.high_board_total == 1
    assert row.high_board_advanced == 1
    assert row.high_board_promotion_rate == pytest.approx(1.0)
    assert row.main_theme_code == "BK001"
    assert row.main_theme_name == "机器人"
    assert row.main_theme_score == pytest.approx(180.0)
    assert row.main_theme_streak_days == 3
    assert notes["high_board_advanced_codes"] == ["000001.SZ"]


def test_backfill_market_sentiment_includes_dates_from_raw_sentiment_tables(db):
    from app.models import MarketSentimentDaily
    from app.services.market_sentiment import backfill_market_sentiment

    insert_quote(db, "000001.SZ", "20260401", 1.0)
    insert_limit_event(
        db,
        ts_code="000001.SZ",
        trade_date="20260402",
        limit_type="U",
        limit_times=2,
        name="情绪样本",
    )
    insert_theme_heat(
        db,
        trade_date="20260402",
        theme_code="BK001",
        theme_name="机器人",
        rank=1,
        score=150.0,
    )

    result = backfill_market_sentiment(db, start_date="20260401")

    assert result["failed_dates"] == []
    assert result["successful_dates"] == 2
    assert result["synced_dates"] == 2
    assert db.query(MarketSentimentDaily).count() == 2
    assert db.get(MarketSentimentDaily, "20260402") is not None
