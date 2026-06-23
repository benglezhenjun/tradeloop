"""
事件总线（V1 版本：桩实现）

V1 阶段只做占位，V5 开始正式使用。
模块间通过事件解耦，不需要直接 import 对方。

支持的事件（V5+ 会实际用到）：
- screening.completed: 筛选完成
- analysis.completed: 分析报告生成完成
- trade.executed: 交易记录创建
- data.synced: 数据同步完成
"""

from collections import defaultdict
from typing import Callable

_subscribers: dict[str, list[Callable]] = defaultdict(list)


def subscribe(event: str, handler: Callable):
    """订阅事件"""
    _subscribers[event].append(handler)


def publish(event: str, payload: dict = None):
    """发布事件，触发所有订阅者"""
    for handler in _subscribers.get(event, []):
        try:
            handler(payload or {})
        except Exception as e:
            print(f"[事件总线] 处理事件 {event} 时出错：{e}")
