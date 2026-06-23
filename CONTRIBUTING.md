# 贡献指南 / Contributing

## 开发环境
- 后端：Python 3.12 + [uv](https://docs.astral.sh/uv/)
- 前端：Node ≥ 20.19 + [pnpm](https://pnpm.io) 10

## 后端
```bash
cd backend
uv sync --group dev
uv run uvicorn app.main:app --reload      # 启动，API 文档见 http://localhost:8000/docs
uv run python -m pytest tests/ -q          # 测试
uv run ruff check .                        # lint
```

## 前端
```bash
cd frontend
pnpm install
pnpm dev          # 开发
pnpm type-check   # 类型检查
pnpm build        # 构建
```

## 提交要求
- 提交信息用语义化前缀：`feat: / fix: / refactor: / docs: / test: / chore: / ci:`。
- PR 合并前必须：后端 `pytest` 全绿 + `ruff check` 无错；前端 `type-check` + `build` 通过。
- 敏感信息（token / api_key）只放 `config/local.toml`（已 gitignore），**严禁入库**。
