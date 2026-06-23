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
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    from app.api import position, trade, user_config
    from app.database import get_db

    app = FastAPI()
    app.include_router(trade.router, prefix="/api")
    app.include_router(position.router, prefix="/api")
    app.include_router(user_config.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code: str, name: str):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, '银行', '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name},
    )
    db.commit()


def insert_quote(db, ts_code: str, trade_date: str, close: float):
    db.execute(
        text(
            "INSERT OR IGNORE INTO daily_quote "
            "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
            "VALUES (:ts_code, :trade_date, :close, :close, :close, :close, 1000, 200000, 0.5, 500000, 1.0)"
        ),
        {"ts_code": ts_code, "trade_date": trade_date, "close": close},
    )
    db.commit()


def trade_payload(**overrides):
    payload = {
        "ts_code": "600000.SH",
        "stock_name": "浦发银行",
        "direction": "buy",
        "price": 10.0,
        "quantity": 100,
        "trade_date": "2026-04-06",
        "fee": 0.0,
        "note": "测试记录",
    }
    payload.update(overrides)
    return payload


class TestPositionApi:
    def test_list_positions_filters_by_status(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        insert_stock(db, "600001.SH", "邯郸钢铁")
        insert_quote(db, "600000.SH", "20260406", 11.0)
        insert_quote(db, "600001.SH", "20260406", 9.0)

        client.post("/api/trade", json=trade_payload(ts_code="600000.SH", stock_name="浦发银行"))
        client.post("/api/trade", json=trade_payload(ts_code="600001.SH", stock_name="邯郸钢铁"))
        client.post(
            "/api/trade",
            json=trade_payload(
                ts_code="600001.SH",
                stock_name="邯郸钢铁",
                direction="sell",
                quantity=100,
                price=9.0,
            ),
        )

        holding = client.get("/api/position", params={"status": "holding"})
        closed = client.get("/api/position", params={"status": "closed"})

        assert holding.status_code == 200
        assert closed.status_code == 200
        assert len(holding.json()["positions"]) == 1
        assert holding.json()["positions"][0]["ts_code"] == "600000.SH"
        assert len(closed.json()["positions"]) == 1
        assert closed.json()["positions"][0]["ts_code"] == "600001.SH"

    def test_position_summary_uses_latest_quote(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        insert_quote(db, "600000.SH", "20260405", 10.5)
        insert_quote(db, "600000.SH", "20260406", 11.0)
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))

        response = client.get("/api/position/summary")

        assert response.status_code == 200
        summary = response.json()
        assert summary["total_market_value"] == pytest.approx(1100.0, rel=1e-6)
        assert summary["total_cost"] == pytest.approx(1000.0, rel=1e-6)
        assert summary["total_unrealized_pnl"] == pytest.approx(100.0, rel=1e-6)
        assert summary["position_count"] == 1

    def test_position_detail_contains_trade_history(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        insert_quote(db, "600000.SH", "20260406", 11.0)
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))
        client.post("/api/trade", json=trade_payload(price=12.0, quantity=100, fee=0.0))

        response = client.get("/api/position/600000.SH")

        assert response.status_code == 200
        body = response.json()
        assert body["position"]["ts_code"] == "600000.SH"
        assert len(body["trades"]) == 2
        assert body["position"]["market_value"] == pytest.approx(2200.0, rel=1e-6)

    def test_recalculate_position_matches_current_state(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        insert_quote(db, "600000.SH", "20260406", 11.0)
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))
        client.post("/api/trade", json=trade_payload(price=12.0, quantity=100, fee=0.0))
        client.post("/api/trade", json=trade_payload(direction="sell", price=13.0, quantity=50, fee=0.0))

        before = client.get("/api/position/600000.SH")
        recalc = client.post("/api/position/600000.SH/recalc")
        after = client.get("/api/position/600000.SH")

        assert before.status_code == 200
        assert recalc.status_code == 200
        assert after.status_code == 200
        assert after.json()["position"]["total_quantity"] == before.json()["position"]["total_quantity"]
        assert after.json()["position"]["realized_pnl"] == pytest.approx(
            before.json()["position"]["realized_pnl"],
            rel=1e-6,
        )
