"""
V5 交易计划 API 契约测试

覆盖目标：
- user_config 默认值契约
- plan API 状态码语义
- generate 的 ok / manual_fallback / not_found
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
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
def session(engine):
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


@pytest.fixture
def client(session):
    from app.api import plan, user_config
    from app.database import get_db

    app = FastAPI()
    app.include_router(plan.router, prefix="/api")
    app.include_router(user_config.router, prefix="/api")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code="000001.SZ", name="平安银行", industry="银行"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, :industry, '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name, "industry": industry},
    )
    db.commit()


def insert_quotes(db, ts_code="000001.SZ", count=60):
    for i in range(count):
        trade_date = f"202604{(i % 28) + 1:02d}"
        db.execute(
            text(
                "INSERT OR IGNORE INTO daily_quote "
                "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
                "VALUES (:ts_code, :trade_date, 10.0, 10.5, 9.5, :close, 1000, 200000, 0.5, 500000, 1.0)"
            ),
            {"ts_code": ts_code, "trade_date": trade_date, "close": 10.0 + i * 0.02},
        )
    db.commit()


def sample_plan_data():
    return {
        "ts_code": "000001.SZ",
        "stock_name": "平安银行",
        "direction": "buy",
        "target_price": 12.5,
        "stop_loss_price": 11.8,
        "take_profit": [
            {"price": 13.5, "ratio": 0.5, "note": "第一档"},
            {"price": 14.5, "ratio": 0.5, "note": "第二档"},
        ],
        "position_ratio": 0.2,
        "reasoning": "测试计划",
        "source": "manual",
    }


class TestUserConfigApi:
    def test_total_capital_defaults_to_zero(self, client):
        response = client.get("/api/config/total_capital")
        assert response.status_code == 200
        assert response.json() == {"key": "total_capital", "value": "0"}


class TestPlanApi:
    def test_create_returns_201(self, client):
        response = client.post("/api/plan", json=sample_plan_data())
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_create_invalid_direction_returns_422(self, client):
        payload = sample_plan_data()
        payload["direction"] = "hold"

        response = client.post("/api/plan", json=payload)

        assert response.status_code == 422

    def test_create_invalid_source_returns_422(self, client):
        payload = sample_plan_data()
        payload["source"] = "ai"

        response = client.post("/api/plan", json=payload)

        assert response.status_code == 422

    def test_update_nonexistent_returns_404(self, client):
        response = client.put("/api/plan/999", json={"target_price": 13})
        assert response.status_code == 404

    def test_patch_status_nonexistent_returns_404(self, client):
        response = client.patch("/api/plan/999/status", json={"status": "executed"})
        assert response.status_code == 404

    def test_patch_invalid_status_returns_422(self, client):
        create_response = client.post("/api/plan", json=sample_plan_data())
        plan_id = create_response.json()["id"]

        response = client.patch(f"/api/plan/{plan_id}/status", json={"status": "pending"})

        assert response.status_code == 422

    def test_generate_unknown_stock_returns_404(self, client):
        client.put("/api/config/total_capital", json={"value": "500000"})
        response = client.post("/api/plan/generate/999999.SZ")
        assert response.status_code == 404

    @patch("app.services.agents.get_market_overview")
    @patch("app.services.agents.llm.chat")
    def test_generate_parse_failure_returns_manual_fallback(self, mock_chat, mock_market, client, session):
        insert_stock(session)
        insert_quotes(session)
        client.put("/api/config/total_capital", json={"value": "500000"})

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = "不是 JSON"

        response = client.post("/api/plan/generate/000001.SZ")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "manual_fallback"
        assert body["prefill"]["ts_code"] == "000001.SZ"

    @patch("app.services.agents.get_market_overview")
    @patch("app.services.agents.llm.chat")
    def test_generate_success_returns_ok_status(self, mock_chat, mock_market, client, session):
        insert_stock(session)
        insert_quotes(session)
        client.put("/api/config/total_capital", json={"value": "500000"})

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = """
        ```json
        [
          {"tier_label":"aggressive","direction":"buy","target_price":10.5,"stop_loss_price":9.8,"take_profit":[{"price":11.5,"ratio":0.5,"note":"第一档"},{"price":12.5,"ratio":0.5,"note":"第二档"}],"position_ratio":0.35,"reasoning":"激进方案","risk_comment":"波动较大"},
          {"tier_label":"balanced","direction":"buy","target_price":10.2,"stop_loss_price":9.5,"take_profit":[{"price":11.0,"ratio":0.4,"note":"第一档"},{"price":12.0,"ratio":0.6,"note":"第二档"}],"position_ratio":0.25,"reasoning":"稳健方案","risk_comment":"风险中等"},
          {"tier_label":"conservative","direction":"buy","target_price":9.8,"stop_loss_price":9.2,"take_profit":[{"price":10.5,"ratio":1.0,"note":"统一止盈"}],"position_ratio":0.15,"reasoning":"保守方案","risk_comment":"风险较低"}
        ]
        ```
        """

        response = client.post("/api/plan/generate/000001.SZ")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert len(body["plans"]) == 3
