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
    from app.api import plan, position, trade, user_config
    from app.database import get_db

    app = FastAPI()
    app.include_router(plan.router, prefix="/api")
    app.include_router(trade.router, prefix="/api")
    app.include_router(position.router, prefix="/api")
    app.include_router(user_config.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code: str, name: str, market: str = "主板"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, '银行', :market, '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name, "market": market},
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


def create_plan(client: TestClient, ts_code: str, stock_name: str) -> int:
    response = client.post(
        "/api/plan",
        json={
            "ts_code": ts_code,
            "stock_name": stock_name,
            "direction": "buy",
            "target_price": 10.0,
            "stop_loss_price": 9.5,
            "take_profit": [{"price": 11.0, "ratio": 1.0, "note": "全部"}],
            "position_ratio": 0.2,
            "reasoning": "测试计划",
            "source": "manual",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


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


class TestTradeApi:
    def test_create_buy_trade_creates_position(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")

        response = client.post("/api/trade", json=trade_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["trade"]["amount"] == 1000.0
        assert body["position"]["total_quantity"] == 100
        assert body["position"]["status"] == "holding"

    def test_buy_trade_without_fee_uses_default_config(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")

        response = client.post("/api/trade", json=trade_payload(fee=None))

        assert response.status_code == 201
        assert response.json()["trade"]["fee"] == pytest.approx(0.27, rel=1e-6)

    def test_add_position_updates_avg_cost(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=10.0))

        response = client.post("/api/trade", json=trade_payload(price=20.0, quantity=100, fee=0.0))

        assert response.status_code == 201
        assert response.json()["position"]["avg_cost"] == pytest.approx(15.05, rel=1e-6)

    def test_sell_trade_updates_realized_pnl(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))

        response = client.post(
            "/api/trade",
            json=trade_payload(direction="sell", price=12.0, quantity=40, fee=10.0),
        )

        assert response.status_code == 201
        assert response.json()["position"]["realized_pnl"] == pytest.approx(70.0, rel=1e-6)
        assert response.json()["position"]["total_quantity"] == 60

    def test_close_and_reopen_position(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))

        sell_response = client.post(
            "/api/trade",
            json=trade_payload(direction="sell", price=11.0, quantity=100, fee=0.0),
        )
        assert sell_response.status_code == 201
        assert sell_response.json()["position"]["status"] == "closed"

        buy_response = client.post("/api/trade", json=trade_payload(price=9.5, quantity=100, fee=0.0))
        assert buy_response.status_code == 201
        assert buy_response.json()["position"]["status"] == "holding"
        assert buy_response.json()["position"]["total_quantity"] == 100

    def test_sell_more_than_position_returns_400(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))

        response = client.post(
            "/api/trade",
            json=trade_payload(direction="sell", price=12.0, quantity=101, fee=0.0),
        )

        assert response.status_code == 400

    def test_buy_trade_with_plan_marks_plan_executed(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        plan_id = create_plan(client, "600000.SH", "浦发银行")

        response = client.post("/api/trade", json=trade_payload(plan_id=plan_id))

        assert response.status_code == 201
        plan_response = client.get(f"/api/plan/{plan_id}")
        assert plan_response.status_code == 200
        assert plan_response.json()["status"] == "executed"

    def test_delete_trade_recalculates_position(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")
        first = client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0))
        second = client.post("/api/trade", json=trade_payload(price=12.0, quantity=100, fee=0.0))
        assert first.status_code == 201
        assert second.status_code == 201

        response = client.delete(f"/api/trade/{second.json()['trade']['id']}")

        assert response.status_code == 200
        position_response = client.get("/api/position/600000.SH")
        assert position_response.status_code == 200
        assert position_response.json()["position"]["total_quantity"] == 100
        assert position_response.json()["position"]["avg_cost"] == pytest.approx(10.0, rel=1e-6)

    def test_invalid_trade_payload_returns_400_or_422(self, client, db):
        insert_stock(db, "600000.SH", "浦发银行")

        zero_price = client.post("/api/trade", json=trade_payload(price=0.0))
        zero_quantity = client.post("/api/trade", json=trade_payload(quantity=0))
        invalid_direction = client.post("/api/trade", json=trade_payload(direction="hold"))

        assert zero_price.status_code == 400
        assert zero_quantity.status_code == 400
        assert invalid_direction.status_code == 422
