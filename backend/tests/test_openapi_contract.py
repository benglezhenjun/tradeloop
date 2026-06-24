"""OpenAPI 契约测试。

守住两件事：
1. 规范能生成、关键路径在册、typed 端点有响应 schema；
2. 仓库里提交的 docs/api/openapi.json 与当前代码一致——接口改了却忘了重新
   导出，就会在这里失败，提示运行 scripts/export_openapi.py。
"""

import json
from pathlib import Path

import pytest

OPENAPI_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "api" / "openapi.json"


@pytest.fixture(scope="module")
def spec():
    from app.main import app

    return app.openapi()


def test_spec_generates_with_core_paths(spec):
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["version"] == "8.0.0"
    paths = spec["paths"]
    for path in [
        "/api/health",
        "/api/ready",
        "/api/strategies",
        "/api/watchlist/groups",
        "/api/plan",
        "/api/trade",
        "/api/position",
    ]:
        assert path in paths, f"OpenAPI 缺少路径 {path}"


def test_health_has_typed_response_schema(spec):
    """health 端点带 response_model → OpenAPI 里有具体响应 schema 引用。"""
    get_op = spec["paths"]["/api/health"]["get"]
    schema = get_op["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in schema or schema.get("type") == "object"


def test_committed_openapi_is_up_to_date(spec):
    """提交的 openapi.json 必须与代码生成的一致（防止接口漂移）。"""
    assert OPENAPI_PATH.exists(), "缺少 docs/api/openapi.json，请运行 scripts/export_openapi.py"
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == spec, (
        "docs/api/openapi.json 与当前接口不一致，请运行： "
        "cd backend && uv run python scripts/export_openapi.py"
    )
