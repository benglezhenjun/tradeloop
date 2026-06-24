"""
策略管理 API（HTTP 层）测试。

策略的 service 层逻辑散落在其它测试里覆盖；这里专门走 TestClient，
验证路由装配、请求体校验、404 映射与响应信封，补齐之前缺失的 API 层。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(db):
    from app.api import strategies as strategies_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(strategies_api.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _create(client, name="动量策略", description="测试用"):
    resp = client.post("/api/strategies", json={"name": name, "description": description})
    assert resp.status_code == 200
    return resp.json()


# ---- 列表 / 创建 ----

def test_list_empty(client):
    resp = client.get("/api/strategies")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


def test_create_then_list(client):
    created = _create(client, "策略A")
    assert created["name"] == "策略A"
    assert isinstance(created["id"], int)

    resp = client.get("/api/strategies")
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    row = body["items"][0]
    assert row["name"] == "策略A"
    assert row["condition_count"] == 0
    assert row["is_enabled"] is True


def test_create_requires_name(client):
    """缺少必填 name → FastAPI 422。"""
    resp = client.post("/api/strategies", json={"description": "无名"})
    assert resp.status_code == 422


# ---- 详情 ----

def test_get_detail(client):
    created = _create(client, "策略B")
    resp = client.get(f"/api/strategies/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "策略B"
    assert body["conditions"] == []


def test_get_detail_404(client):
    resp = client.get("/api/strategies/99999")
    assert resp.status_code == 404
    assert "99999" in resp.json()["detail"]


# ---- 更新 / 删除 ----

def test_patch_updates_fields(client):
    created = _create(client, "旧名")
    resp = client.patch(f"/api/strategies/{created['id']}", json={"name": "新名", "is_enabled": False})
    assert resp.status_code == 200

    detail = client.get(f"/api/strategies/{created['id']}").json()
    assert detail["name"] == "新名"
    assert detail["is_enabled"] is False


def test_patch_404(client):
    resp = client.patch("/api/strategies/99999", json={"name": "x"})
    assert resp.status_code == 404


def test_delete(client):
    created = _create(client, "待删")
    resp = client.delete(f"/api/strategies/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "已删除"
    # 二次删除 → 404
    assert client.delete(f"/api/strategies/{created['id']}").status_code == 404


# ---- 条件列表 ----

def test_list_all_conditions(client):
    resp = client.get("/api/strategies/conditions/all")
    assert resp.status_code == 200
    conditions = resp.json()["conditions"]
    assert isinstance(conditions, list)
    assert len(conditions) > 0
    # 每个条件描述至少含 code 字段
    assert all("code" in c for c in conditions)


def test_update_conditions(client, db):
    from app.models.strategy import Condition
    from app.services.conditions import registry

    created = _create(client, "带条件策略")
    code = registry.codes()[0]  # 取一个真实注册的条件
    # strategy_condition.condition_code 外键指向 condition 表，需先落库条件元数据
    db.add(Condition(code=code, name=code, category="测试"))
    db.commit()
    resp = client.put(
        f"/api/strategies/{created['id']}/conditions",
        json={"conditions": [{"condition_code": code, "params": {}, "is_enabled": True, "sort_order": 1}]},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "条件已更新"

    detail = client.get(f"/api/strategies/{created['id']}").json()
    assert len(detail["conditions"]) == 1
    assert detail["conditions"][0]["condition_code"] == code


def test_update_conditions_404(client):
    resp = client.put(
        "/api/strategies/99999/conditions",
        json={"conditions": []},
    )
    assert resp.status_code == 404
