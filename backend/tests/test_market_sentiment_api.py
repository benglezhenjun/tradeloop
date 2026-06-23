import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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
    from app.api import sentiment as sentiment_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(sentiment_api.router, prefix="/api/dashboard")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_sentiment_snapshot(
    db,
    *,
    trade_date: str,
    max_limit_height: int = 0,
    max_limit_height_count: int = 0,
    max_limit_height_codes: list[str] | None = None,
    limit_up_count: int = 0,
    limit_broken_count: int = 0,
    broken_rate: float = 0.0,
    yday_limit_premium_avg: float = 0.0,
    yday_limit_premium_median: float = 0.0,
    yday_limit_red_rate: float = 0.0,
    yday_limit_sample_count: int = 0,
    high_board_threshold: int = 3,
    high_board_total: int = 0,
    high_board_advanced: int = 0,
    high_board_promotion_rate: float = 0.0,
    main_theme_code: str | None = None,
    main_theme_name: str | None = None,
    main_theme_score: float | None = None,
    main_theme_streak_days: int = 0,
    notes: dict | None = None,
):
    from app.models import MarketSentimentDaily

    db.add(
        MarketSentimentDaily(
            trade_date=trade_date,
            max_limit_height=max_limit_height,
            max_limit_height_count=max_limit_height_count,
            max_limit_height_codes_json=json.dumps(max_limit_height_codes or [], ensure_ascii=False),
            limit_up_count=limit_up_count,
            limit_broken_count=limit_broken_count,
            broken_rate=broken_rate,
            yday_limit_premium_avg=yday_limit_premium_avg,
            yday_limit_premium_median=yday_limit_premium_median,
            yday_limit_red_rate=yday_limit_red_rate,
            yday_limit_sample_count=yday_limit_sample_count,
            high_board_threshold=high_board_threshold,
            high_board_total=high_board_total,
            high_board_advanced=high_board_advanced,
            high_board_promotion_rate=high_board_promotion_rate,
            main_theme_code=main_theme_code,
            main_theme_name=main_theme_name,
            main_theme_score=main_theme_score,
            main_theme_streak_days=main_theme_streak_days,
            notes_json=json.dumps(notes or {}, ensure_ascii=False),
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
    name: str,
):
    from app.models import LimitEventDaily

    db.add(
        LimitEventDaily(
            ts_code=ts_code,
            trade_date=trade_date,
            limit_type=limit_type,
            name=name,
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


def insert_quote(db, *, ts_code: str, trade_date: str, pct_chg: float):
    from app.models import DailyQuote

    db.add(
        DailyQuote(
            ts_code=ts_code,
            trade_date=trade_date,
            open=10.0,
            high=10.2,
            low=9.9,
            close=10.1,
            vol=1000.0,
            amount=100000.0,
            pct_chg=pct_chg,
            total_mv=500000.0,
            turnover_rate=1.0,
        )
    )
    db.commit()


def test_sentiment_summary_returns_latest_snapshot(client, db):
    insert_sentiment_snapshot(
        db,
        trade_date="20260401",
        max_limit_height=3,
        max_limit_height_count=1,
        max_limit_height_codes=["000001.SZ"],
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=120.0,
        main_theme_streak_days=2,
    )
    insert_sentiment_snapshot(
        db,
        trade_date="20260402",
        max_limit_height=4,
        max_limit_height_count=2,
        max_limit_height_codes=["000001.SZ", "000002.SZ"],
        main_theme_code="BK002",
        main_theme_name="算力",
        main_theme_score=140.0,
        main_theme_streak_days=1,
    )

    response = client.get("/api/dashboard/sentiment/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trade_date"] == "20260402"
    assert payload["max_limit_height"] == 4
    assert payload["max_limit_height_codes"] == ["000001.SZ", "000002.SZ"]
    assert payload["main_theme_name"] == "算力"


def test_sentiment_history_returns_recent_points_ascending(client, db):
    for idx, trade_date in enumerate(["20260401", "20260402", "20260403"], start=1):
        insert_sentiment_snapshot(
            db,
            trade_date=trade_date,
            max_limit_height=idx,
            main_theme_code=f"BK{idx:03d}",
            main_theme_name=f"Theme-{idx}",
            main_theme_streak_days=idx,
        )

    response = client.get("/api/dashboard/sentiment/history", params={"days": 2})

    assert response.status_code == 200
    payload = response.json()
    assert [item["trade_date"] for item in payload] == ["20260402", "20260403"]
    assert payload[0]["max_limit_height"] == 2
    assert payload[1]["main_theme_streak_days"] == 3


def test_sentiment_themes_returns_main_theme_history(client, db):
    insert_sentiment_snapshot(
        db,
        trade_date="20260401",
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=120.0,
        main_theme_streak_days=1,
    )
    insert_sentiment_snapshot(
        db,
        trade_date="20260402",
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=130.0,
        main_theme_streak_days=2,
    )

    response = client.get("/api/dashboard/sentiment/themes", params={"days": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "trade_date": "20260401",
            "main_theme_code": "BK001",
            "main_theme_name": "机器人",
            "main_theme_score": 120.0,
            "main_theme_streak_days": 1,
        },
        {
            "trade_date": "20260402",
            "main_theme_code": "BK001",
            "main_theme_name": "机器人",
            "main_theme_score": 130.0,
            "main_theme_streak_days": 2,
        },
    ]


def test_sentiment_detail_returns_samples_and_summary(client, db):
    insert_sentiment_snapshot(
        db,
        trade_date="20260402",
        max_limit_height=4,
        max_limit_height_count=1,
        max_limit_height_codes=["000001.SZ"],
        limit_up_count=1,
        limit_broken_count=1,
        broken_rate=0.5,
        yday_limit_premium_avg=4.0,
        yday_limit_premium_median=4.0,
        yday_limit_red_rate=1.0,
        yday_limit_sample_count=1,
        high_board_threshold=3,
        high_board_total=1,
        high_board_advanced=1,
        high_board_promotion_rate=1.0,
        main_theme_code="BK001",
        main_theme_name="机器人",
        main_theme_score=188.0,
        main_theme_streak_days=3,
        notes={
            "yday_limit_sample_codes": ["000001.SZ"],
            "high_board_candidate_codes": ["000001.SZ"],
            "high_board_advanced_codes": ["000001.SZ"],
        },
    )
    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260401", limit_type="U", limit_times=3, name="高标一")
    insert_limit_event(db, ts_code="000001.SZ", trade_date="20260402", limit_type="U", limit_times=4, name="高标一")
    insert_limit_event(db, ts_code="000002.SZ", trade_date="20260402", limit_type="Z", limit_times=2, name="炸板二")
    insert_theme_heat(db, trade_date="20260402", theme_code="BK001", theme_name="机器人", rank=1, score=188.0)
    insert_theme_heat(db, trade_date="20260402", theme_code="BK002", theme_name="算力", rank=2, score=166.0)
    insert_quote(db, ts_code="000001.SZ", trade_date="20260401", pct_chg=9.9)
    insert_quote(db, ts_code="000001.SZ", trade_date="20260402", pct_chg=4.0)

    response = client.get("/api/dashboard/sentiment/detail/20260402")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["trade_date"] == "20260402"
    assert payload["summary"]["main_theme_name"] == "机器人"
    assert payload["limit_up_samples"][0]["ts_code"] == "000001.SZ"
    assert payload["limit_broken_samples"][0]["ts_code"] == "000002.SZ"
    assert payload["yday_limit_samples"][0]["today_pct_chg"] == pytest.approx(4.0)
    assert payload["high_board_samples"][0]["is_advanced"] is True
    assert payload["theme_leaders"][0]["theme_code"] == "BK001"


def test_sentiment_api_returns_empty_structures_when_no_data(client):
    summary = client.get("/api/dashboard/sentiment/summary")
    history = client.get("/api/dashboard/sentiment/history")
    themes = client.get("/api/dashboard/sentiment/themes")
    detail = client.get("/api/dashboard/sentiment/detail/20260408")

    assert summary.status_code == 200
    assert summary.json()["trade_date"] is None
    assert history.status_code == 200
    assert history.json() == []
    assert themes.status_code == 200
    assert themes.json() == []
    assert detail.status_code == 200
    assert detail.json() == {
        "trade_date": "20260408",
        "summary": None,
        "limit_up_samples": [],
        "limit_broken_samples": [],
        "yday_limit_samples": [],
        "high_board_samples": [],
        "theme_leaders": [],
    }


def test_main_app_registers_sentiment_routes():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/dashboard/sentiment/summary" in paths
    assert "/api/dashboard/sentiment/history" in paths
    assert "/api/dashboard/sentiment/themes" in paths
