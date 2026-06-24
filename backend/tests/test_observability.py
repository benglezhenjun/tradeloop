"""可观测性与系统探针测试：请求 ID / 耗时头、health 存活、ready 就绪。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(db):
    from app.api import system as system_api
    from app.database import get_db
    from app.observability import request_context_middleware

    app = FastAPI()
    app.middleware("http")(request_context_middleware)
    app.include_router(system_api.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_quote(db):
    db.execute(
        text(
            "INSERT INTO daily_quote (ts_code, trade_date, close) VALUES ('600000.SH', '20260624', 10.0)"
        )
    )
    db.commit()


# ---- 中间件：请求 ID + 耗时 ----

def test_response_carries_request_id_and_process_time(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")  # 自动生成
    assert "X-Process-Time-Ms" in resp.headers
    float(resp.headers["X-Process-Time-Ms"])  # 可解析为数字


def test_request_id_is_propagated_when_provided(client):
    resp = client.get("/api/health", headers={"X-Request-ID": "trace-abc-123"})
    assert resp.headers["X-Request-ID"] == "trace-abc-123"


# ---- 存活探针 ----

def test_health_is_liveness_only(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["version"] == "8.0.0"


# ---- 就绪探针 ----

def test_ready_returns_503_when_no_data(client):
    """空库（无行情）→ 未就绪 503。"""
    resp = client.get("/api/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "no_data"


def test_ready_returns_200_when_data_present(client, db):
    _seed_quote(db)
    resp = client.get("/api/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["quote_count"] == 1
