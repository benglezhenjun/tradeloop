"""
配置管理模块 (V1 重写)

读取顺序：config/default.toml → config/local.toml（覆盖默认值）
local.toml 不入 Git，用于存放 token 等私密信息。

【学习要点 - 为什么要把配置分成两个文件？】
- default.toml：公开配置，提交到 Git，团队/新机器可以直接用
- local.toml：私密配置，不提交 Git，每台机器自己填
- 这样换一台电脑只需：git clone → 复制数据库 → 填写 local.toml
"""

import tomllib
from pathlib import Path

# 项目根目录（stock-assistant/）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_config() -> dict:
    """读取并合并两个配置文件"""
    config = {}

    # 1. 读取默认配置
    default_path = PROJECT_ROOT / "config" / "default.toml"
    if default_path.exists():
        with open(default_path, "rb") as f:
            config = tomllib.load(f)

    # 2. 读取本地覆盖配置（local.toml 不存在也没关系）
    local_path = PROJECT_ROOT / "config" / "local.toml"
    if local_path.exists():
        with open(local_path, "rb") as f:
            local = tomllib.load(f)
        # 深度合并：local 的值覆盖 default 的值
        for section, values in local.items():
            if section in config and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values

    return config


# 启动时加载一次，全局复用
_config = _load_config()

# ---- 对外暴露的配置项 ----

# 数据库
_db_path = PROJECT_ROOT / _config.get("database", {}).get("path", "data/stock.db")
DATABASE_PATH = _db_path
DATABASE_URL = f"sqlite:///{_db_path}"

# Tushare
TUSHARE_TOKEN: str = _config.get("tushare", {}).get("token", "")

# 调度器
SCHEDULER_HOUR: int = _config.get("scheduler", {}).get("daily_sync_hour", 15)
SCHEDULER_MINUTE: int = _config.get("scheduler", {}).get("daily_sync_minute", 35)

# 筛选默认参数
SCREENING = _config.get("screening", {})

# 数据历史范围
HISTORY_START_DATE: str = _config.get("data", {}).get("history_start_date", "20140101")
BACKFILL_SLEEP: float = _config.get("data", {}).get("backfill_sleep", 0.35)

# LLM
_llm = _config.get("llm", {})
LLM_PROVIDER: str = _llm.get("provider", "deepseek")
LLM_BASE_URL: str = _llm.get("base_url", "https://api.deepseek.com")
LLM_API_KEY: str = _llm.get("api_key", "")
LLM_MODEL: str = _llm.get("model", "deepseek-chat")
