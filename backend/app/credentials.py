"""运行时凭证解析：DB（user_config）覆盖 config（local.toml），前端可改、保存即生效。

为什么要这一层：
`config.py` 的 `TUSHARE_TOKEN` / `LLM_*` 是启动时从 TOML 读成的模块常量，改了要重启。
本层把"有效值"集中起来——DB 里有就用 DB 的（前端可写），否则回退 TOML——并用一个
进程内缓存让保存后**立即生效**，从而避免给 llm / agents 一路加 db 参数。

安全：key 落在本地 DB（`data/stock.db`，已 gitignore，绝不入库），对外只返回打码值。
随仓 `data/sample.db` 为合成库、不含任何真实 key。
"""

from app import config
from app.services import user_config

# 受管理的凭证键 → 各自的 TOML 兜底值（DB 为空时回退）
_TOML_FALLBACK = {
    "tushare_token": lambda: config.TUSHARE_TOKEN,
    "llm_api_key": lambda: config.LLM_API_KEY,
    "llm_base_url": lambda: config.LLM_BASE_URL,
    "llm_model": lambda: config.LLM_MODEL,
}

# 进程内缓存：DB 覆盖值。启动时从 DB 加载，保存时更新——保证不重启即生效。
_overrides: dict[str, str] = {}


def _effective(key: str) -> str:
    value = _overrides.get(key)
    if value:
        return value
    return _TOML_FALLBACK[key]()


def tushare_token() -> str:
    return _effective("tushare_token")


def llm_api_key() -> str:
    return _effective("llm_api_key")


def llm_base_url() -> str:
    return _effective("llm_base_url")


def llm_model() -> str:
    return _effective("llm_model")


def refresh_from_db(db) -> None:
    """启动时把 DB 里已存的凭证加载进进程缓存。"""
    for key in _TOML_FALLBACK:
        value = user_config.get_config(db, key)
        if value:
            _overrides[key] = value


def save(db, values: dict[str, str | None]) -> None:
    """保存前端提交的凭证：只写入非空字段（空字段=不改，避免清掉已存的 key）。"""
    for key, value in values.items():
        if key not in _TOML_FALLBACK:
            continue
        if value is None or not value.strip():
            continue
        user_config.set_config(db, key, value.strip())
        _overrides[key] = value.strip()


def mask(value: str) -> str:
    """打码：只露头 4 尾 4，绝不返回完整 key。"""
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}…{value[-4:]}"


def status() -> dict:
    """对外状态（打码，供前端展示与"是否已配置"判断）。"""
    return {
        "tushare": {
            "configured": bool(tushare_token()),
            "masked": mask(tushare_token()),
        },
        "llm": {
            "configured": bool(llm_api_key()),
            "masked": mask(llm_api_key()),
            "provider": config.LLM_PROVIDER,
            "base_url": llm_base_url(),
            "model": llm_model(),
        },
    }
