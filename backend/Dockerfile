FROM python:3.12-slim

# uv（从官方镜像拷二进制；版本可按当时可用微调）
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv \
    TRADELOOP_ENABLE_SCHEDULER=0

WORKDIR /app/backend

# 先装依赖（利用缓存）
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# 再拷代码 + 配置 + 合成库（保持与仓库一致的目录层级：/app/backend, /app/config, /app/data）
COPY backend /app/backend
COPY config /app/config
COPY data/sample.db /app/data/sample.db
COPY docker/backend-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && useradd -m appuser \
    && mkdir -p /app/data \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
