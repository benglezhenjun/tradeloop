"""导出 OpenAPI 契约到 docs/api/openapi.json。

FastAPI 会从现有路由（含 Pydantic 请求体、response_model）自动生成完整的
OpenAPI 3 规范——这是一份机器可读的接口契约：每个端点要传什么、返回什么、
有哪些错误。比"/docs 能打开"更进一步，可用于前端代码生成、契约测试、对接方查阅。

用法：
    cd backend && uv run python scripts/export_openapi.py
CI 可加一步校验它与提交版本一致（接口变了就必须重新导出）。
"""

import json
from pathlib import Path

from app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path_count = len(spec.get("paths", {}))
    print(f"OpenAPI {spec['info']['version']} 已导出：{OUT_PATH}（{path_count} 个路径）")


if __name__ == "__main__":
    main()
