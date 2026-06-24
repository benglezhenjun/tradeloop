from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(db):
    from app.api import dashboard as dashboard_api
    from app.api import data as data_api
    from app.api import kline as kline_api
    from app.database import get_db
    from app.api.system import health_check

    app = FastAPI()
    app.include_router(data_api.router)
    app.include_router(kline_api.router)
    app.include_router(dashboard_api.router, prefix="/api/dashboard")
    app.get("/api/health")(health_check)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code="600000.SH", name="PF Bank", industry="Bank"):
    from app.models import StockBasic

    db.add(
        StockBasic(
            ts_code=ts_code,
            name=name,
            industry=industry,
            market="Main",
            list_date="20200101",
            list_status="L",
        )
    )
    db.commit()


def insert_quotes(db, ts_code="600000.SH", count=3, start="2026-03-01", close_base=10.0):
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
                pct_chg=1.0 + idx,
                total_mv=500000,
                turnover_rate=1.0 + idx * 0.05,
            )
        )
    db.commit()


def test_backfill_status_endpoint_returns_service_state(client):
    expected = {
        "status": "running",
        "error": None,
        "finished_at": "2026-04-07T12:00:00",
    }

    with patch("app.api.data.get_backfill_state", return_value=expected):
        response = client.get("/api/data/backfill/status")

    assert response.status_code == 200
    assert response.json() == expected


def test_dashboard_overview_endpoint_returns_market_snapshot(client, db):
    insert_stock(db, "600000.SH", "PF Bank")
    insert_stock(db, "000001.SZ", "Ping An Bank")
    insert_quotes(db, "600000.SH", count=1, close_base=10.0)
    insert_quotes(db, "000001.SZ", count=1, close_base=8.0)

    response = client.get("/api/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["trade_date"] == "20260301"
    assert response.json()["up_count"] == 2


def test_kline_endpoint_returns_ascending_klines(client, db):
    insert_stock(db)
    insert_quotes(db, count=3)

    response = client.get("/api/kline/600000.SH")

    assert response.status_code == 200
    dates = [item["date"] for item in response.json()["klines"]]
    assert dates == sorted(dates)
    assert len(dates) == 3


def test_health_endpoint_reports_v8_message(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["version"] == "8.0.0"
    assert response.json()["message"] == "A股交易辅助系统 V8 运行中"


def test_api_package_exports_main_routers():
    from app import api

    assert set(api.__all__) == {
        "analysis",
        "dashboard",
        "data",
        "kline",
        "plan",
        "position",
        "review",
        "screening",
        "sentiment",
        "stocks",
        "strategies",
        "trade",
        "user_config",
        "watchlist",
    }


def test_main_app_restricts_cors_methods_and_headers():
    from app.main import app

    cors = next(middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware)

    assert cors.kwargs["allow_methods"] == ["GET", "POST", "PUT", "PATCH", "DELETE"]
    assert cors.kwargs["allow_headers"] == ["Content-Type", "Authorization"]
