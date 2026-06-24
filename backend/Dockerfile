FROM python:3.12-slim

# 镜像源可配（默认国际源；国内构建可传 PyPI 镜像，见 README Docker 段）：
#   docker compose build 时设置 PIP_INDEX_URL / UV_INDEX_URL 环境变量
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG UV_INDEX_URL=https://pypi.org/simple

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    UV_DEFAULT_INDEX=${UV_INDEX_URL} \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv \
    TRADELOOP_ENABLE_SCHEDULER=0

WORKDIR /app/backend

# 通过 pip 安装 uv（不依赖 ghcr.io，国内更稳）
RUN pip install --no-cache-dir uv

# 先装依赖（利用缓存）
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# 再拷代码 + 配置 + 合成库
# 样例库放 /app/seed（非数据卷挂载点），避免被 compose 的 named volume 遮蔽；
# 运行库 /app/data 由 entrypoint 从 seed 初始化，并可挂 named volume 持久化。
COPY backend /app/backend
COPY config /app/config
COPY data/sample.db /app/seed/sample.db
COPY docker/backend-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && useradd -m appuser \
    && mkdir -p /app/data \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
