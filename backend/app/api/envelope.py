"""列表端点统一响应信封。

【约定（见重构计划 3.3）】
- **列表端点**（返回某类领域实体的集合）统一返回 `{"items": [...], "total": N}`。
  `total` 为本次返回的条目数；当前未做服务端分页，故恒等于 `len(items)`，
  保留该字段是为将来引入分页/过滤计数时契约不变。
- 命令/状态端点（`{"status", "message"}`）、健康检查、详情、汇总统计、
  时间序列（行情/情绪历史/市场宽度）、静态目录（条件清单/可用日期）、搜索
  **不属于列表端点**，保留各自专用结构。
- 错误仍走 FastAPI `detail`（见 app/errors.py）。

信封只在 API 路由层构造：service 层返回领域数据，API 负责包装成线上信封。
"""

from typing import Any


def list_envelope(items: list[Any]) -> dict[str, Any]:
    """把一组实体包装为统一列表信封 `{"items", "total"}`。"""
    items = list(items)
    return {"items": items, "total": len(items)}
