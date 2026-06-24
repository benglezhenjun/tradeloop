"""
自选股管理 API（HTTP 层）测试。

service 层在 test_v2_watchlist 已覆盖；这里专门走 TestClient，
验证路由装配、请求体校验、service 错误到 HTTP 状态码的映射（raise_service_error）。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(db):
    from app.api import watchlist as watchlist_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(watchlist_api.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def seed_stock_basic(db, ts_code, name="测试股", industry="银行"):
    db.execute(
        text(
            "INSERT INTO stock_basic (ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:c, :n, :i, 'Main', '20200101', 'L')"
        ),
        {"c": ts_code, "n": name, "i": industry},
    )
    db.commit()


def _create_group(client, name="我的自选"):
    resp = client.post("/api/watchlist/groups", json={"name": name})
    assert resp.status_code == 200
    return resp.json()


# ---- 分组 ----

def test_list_groups_empty(client):
    resp = client.get("/api/watchlist/groups")
    assert resp.status_code == 200
    assert resp.json() == {"groups": []}


def test_create_and_list_group(client):
    created = _create_group(client, "核心池")
    assert created["name"] == "核心池"

    groups = client.get("/api/watchlist/groups").json()["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "核心池"


def test_patch_group(client):
    g = _create_group(client)
    resp = client.patch(f"/api/watchlist/groups/{g['id']}", json={"name": "改名后"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名后"


def test_patch_group_404(client):
    resp = client.patch("/api/watchlist/groups/99999", json={"name": "x"})
    assert resp.status_code == 404


def test_delete_group(client):
    g = _create_group(client)
    assert client.delete(f"/api/watchlist/groups/{g['id']}").status_code == 200
    assert client.delete(f"/api/watchlist/groups/{g['id']}").status_code == 404


# ---- 分组内股票 ----

def test_add_and_get_stock(client, db):
    seed_stock_basic(db, "600000.SH")
    g = _create_group(client)

    resp = client.post(f"/api/watchlist/groups/{g['id']}/stocks", json={"ts_code": "600000.SH", "note": "银行龙头"})
    assert resp.status_code == 200
    assert resp.json()["ts_code"] == "600000.SH"

    stocks = client.get(f"/api/watchlist/groups/{g['id']}/stocks").json()["stocks"]
    assert len(stocks) == 1
    assert stocks[0]["ts_code"] == "600000.SH"


def test_add_unknown_ts_code_maps_to_400(client):
    """service 返回 validation 错误 → raise_service_error → HTTP 400。"""
    g = _create_group(client)
    resp = client.post(f"/api/watchlist/groups/{g['id']}/stocks", json={"ts_code": "000000.SZ"})
    assert resp.status_code == 400
    assert "不存在" in resp.json()["detail"]


def test_add_stock_to_missing_group_maps_to_400(client):
    resp = client.post("/api/watchlist/groups/99999/stocks", json={"ts_code": "600000.SH"})
    assert resp.status_code == 400


def test_get_stocks_missing_group_404(client):
    """分组不存在时 get_group_stocks 返回 None → 路由抛 404。"""
    resp = client.get("/api/watchlist/groups/99999/stocks")
    assert resp.status_code == 404


def test_remove_stock(client, db):
    seed_stock_basic(db, "600000.SH")
    g = _create_group(client)
    client.post(f"/api/watchlist/groups/{g['id']}/stocks", json={"ts_code": "600000.SH"})

    resp = client.delete(f"/api/watchlist/groups/{g['id']}/stocks/600000.SH")
    assert resp.status_code == 200
    # 再次移除 → 404
    assert client.delete(f"/api/watchlist/groups/{g['id']}/stocks/600000.SH").status_code == 404


# ---- 汇总 / 批量 ----

def test_all_stocks_empty(client):
    resp = client.get("/api/watchlist/stocks")
    assert resp.status_code == 200
    assert resp.json() == {"stocks": []}


def test_batch_add(client, db):
    seed_stock_basic(db, "600000.SH")
    seed_stock_basic(db, "000001.SZ")
    g = _create_group(client)

    resp = client.post(
        "/api/watchlist/stocks/batch",
        json={"group_id": g["id"], "ts_codes": ["600000.SH", "000001.SZ"]},
    )
    assert resp.status_code == 200

    stocks = client.get("/api/watchlist/stocks").json()["stocks"]
    assert len(stocks) == 2


def test_batch_add_missing_group_maps_to_400(client):
    resp = client.post("/api/watchlist/stocks/batch", json={"group_id": 99999, "ts_codes": ["600000.SH"]})
    assert resp.status_code == 400
