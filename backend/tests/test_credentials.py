"""API 密钥（凭证）管理测试：DB 覆盖 TOML、保存即生效、打码、联网校验端点。"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_overrides():
    """每个用例前后清空进程内凭证缓存，避免相互污染。"""
    from app import credentials

    credentials._overrides.clear()
    yield
    credentials._overrides.clear()


@pytest.fixture
def client(db):
    from app.api import credentials as credentials_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(credentials_api.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ---- 凭证解析层 ----

def test_db_override_beats_toml(db, monkeypatch):
    from app import config, credentials

    monkeypatch.setattr(config, "TUSHARE_TOKEN", "toml-token")
    assert credentials.tushare_token() == "toml-token"  # DB 空 → 回退 TOML

    credentials.save(db, {"tushare_token": "db-token"})
    assert credentials.tushare_token() == "db-token"  # DB 有 → 覆盖 TOML


def test_save_ignores_empty_fields(db):
    from app import credentials

    credentials.save(db, {"llm_api_key": "real-key"})
    credentials.save(db, {"llm_api_key": "   "})  # 空白不应清掉已存的 key
    assert credentials.llm_api_key() == "real-key"


def test_refresh_from_db_loads_saved(db):
    from app import credentials

    credentials.save(db, {"tushare_token": "persisted"})
    credentials._overrides.clear()  # 模拟重启：进程缓存丢失
    credentials.refresh_from_db(db)  # 应从 DB 重新载入
    assert credentials.tushare_token() == "persisted"


def test_mask_never_leaks_full_key():
    from app import credentials

    assert credentials.mask("a11a1234567890f7c2") == "a11a…f7c2"
    assert credentials.mask("short") == "•••••"
    assert credentials.mask("") == ""


def test_llm_is_configured_follows_credentials(db, monkeypatch):
    from app import config, credentials
    from app.services import llm

    monkeypatch.setattr(config, "LLM_API_KEY", "")
    assert llm.is_configured() is False

    credentials.save(db, {"llm_api_key": "sk-xxx"})
    assert llm.is_configured() is True


# ---- API ----

def test_get_status_is_masked(client, db):
    from app import credentials

    credentials.save(db, {"tushare_token": "a11a1234567890f7c2", "llm_api_key": "sk-abcdefgh"})
    body = client.get("/api/credentials").json()
    assert body["tushare"]["configured"] is True
    assert body["tushare"]["masked"] == "a11a…f7c2"
    assert "a11a1234567890f7c2" not in str(body)  # 完整 key 绝不出现


def test_put_saves_and_takes_effect(client):
    resp = client.put("/api/credentials", json={"tushare_token": "新token1234"})
    assert resp.status_code == 200
    assert resp.json()["tushare"]["configured"] is True

    from app import credentials

    assert credentials.tushare_token() == "新token1234"


def test_check_endpoint_reports_per_credential(client):
    with (
        patch("app.api.credentials._check_tushare", return_value={"ok": True}),
        patch("app.api.credentials._check_llm", return_value={"ok": False, "reason": "未配置"}),
    ):
        body = client.post("/api/credentials/check").json()
    assert body["tushare"]["ok"] is True
    assert body["llm"]["ok"] is False
    assert body["llm"]["reason"] == "未配置"
