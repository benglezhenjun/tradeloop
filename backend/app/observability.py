"""轻量可观测性：请求 ID + 耗时中间件。

不上 Prometheus 等重型方案（个人项目无必要），只做三件最有用的事：
- 每个请求带一个短 request id（沿用调用方传入的 `X-Request-ID`，否则生成），
  便于把一次请求的多行日志串起来；
- 量每个请求的处理耗时，写回 `X-Process-Time-Ms` 响应头；
- 统一一行结构化访问日志（方法 / 路径 / 状态码 / 耗时 / request id）。

就绪探针 `/api/ready` 见 app/main.py（区别于存活探针 `/api/health`）。
"""

import logging
import time
import uuid

from starlette.requests import Request

logger = logging.getLogger("tradeloop.request")


async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

    logger.info(
        "%s %s -> %s %sms [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response
