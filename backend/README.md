# TradeLoop · 后端

A 股交易辅助系统后端：FastAPI + SQLAlchemy + SQLite + Pandas + Tushare + OpenAI SDK。

## 环境
- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## 快速开始
```bash
cd backend
uv sync                                  # 安装依赖（含 dev 用 --group dev）
# 配置：复制 ../config/local.toml.example 为 ../config/local.toml 并填 token/api_key
uv run uvicorn app.main:app --reload     # 启动；API 文档 http://localhost:8000/docs
```
启动时会自动执行 Alembic 迁移、初始化内置策略与默认配置。

## 测试 / Lint
```bash
uv run python -m pytest tests/ -q
uv run ruff check .
```

## 数据
首次运行库为空，需用 `scripts/seed_demo.py` 生成演示数据，或用自己的 Tushare token 同步真实数据（见仓库根 README 的「数据准备」与 `DATA_LICENSE.md`）。
