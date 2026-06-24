"""
列表端点统一信封契约测试（见重构计划 3.3 与 app/api/envelope.py）。

约定：所有「返回领域实体集合」的列表端点统一返回 `{"items": [...], "total": N}`，
且 `total == len(items)`。本测试是该契约的回归守卫——新增/改动列表端点时，
把它的 GET 路径加进 LIST_ENDPOINTS 即可纳入校验。

时间序列、静态目录、搜索、汇总统计、命令/状态、详情、健康检查不属于列表端点，
不在此校验范围。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


def _build_app(db):
    from app.api import analysis as analysis_api
    from app.api import plan as plan_api
    from app.api import position as position_api
    from app.api import review as review_api
    from app.api import strategies as strategies_api
    from app.api import trade as trade_api
    from app.api import watchlist as watchlist_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(strategies_api.router)
    app.include_router(watchlist_api.router)
    app.include_router(analysis_api.router, prefix="/api/analysis")
    app.include_router(review_api.router, prefix="/api")
    app.include_router(plan_api.router, prefix="/api")
    app.include_router(trade_api.router, prefix="/api")
    app.include_router(position_api.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def client(db):
    return _build_app(db)


# 已统一为 {items,total} 的列表端点 GET 路径（空库即可返回空信封）。
# 随各业务域迁移逐批扩充（见 3.3 分域提交）。
LIST_ENDPOINTS = [
    "/api/strategies",
    "/api/watchlist/groups",
    "/api/watchlist/stocks",
    "/api/analysis/reports",
    "/api/review",
    "/api/review/patterns",
    "/api/plan",
    "/api/trade",
    "/api/position",
]


def _assert_envelope(payload):
    """断言 payload 符合 {items: list, total: int(==len(items))} 契约。"""
    assert isinstance(payload, dict), f"列表端点应返回对象信封，实际：{type(payload)}"
    assert set(payload.keys()) == {"items", "total"}, f"信封键应恰为 items/total，实际：{payload.keys()}"
    assert isinstance(payload["items"], list)
    assert isinstance(payload["total"], int)
    assert payload["total"] == len(payload["items"])


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
def test_list_endpoint_returns_envelope_on_empty_db(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    _assert_envelope(resp.json())


def test_group_stocks_endpoint_returns_envelope(client):
    """分组内股票列表也遵守信封契约（需先建分组）。"""
    created = client.post("/api/watchlist/groups", json={"name": "契约测试组"}).json()
    resp = client.get(f"/api/watchlist/groups/{created['id']}/stocks")
    assert resp.status_code == 200
    _assert_envelope(resp.json())


def test_envelope_total_tracks_item_count(client, db):
    """写入数据后 total 跟随实际条目数。"""
    db.execute(
        text(
            "INSERT INTO strategy (name, is_enabled) VALUES ('S1', 1), ('S2', 1)"
        )
    )
    db.commit()
    body = client.get("/api/strategies").json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
