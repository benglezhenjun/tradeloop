"""
条件注册引擎

【核心设计思想】
每一个筛选条件是一个独立的 Python 类。
新增条件 = 新建一个文件 + 继承 BaseCondition + 调用 register()。
不需要修改任何已有代码。

用法示例：
    from app.services.conditions import registry

    # 获取所有可用条件
    all_conditions = registry.all()

    # 执行某个条件
    condition = registry.get("amount_gt")
    passed_codes = condition.evaluate(df, params={"threshold": 2e9})
"""

from app.services.conditions.base import BaseCondition, ConditionRegistry

# 全局注册器（单例）
registry = ConditionRegistry()

# 导入所有条件，触发自动注册
from app.services.conditions import (  # noqa: E402, F401
    amount_gt,
    market_cap_gt,
    amount_rank,
    ma_proximity,
    ma_slope,
    price_rise_range,
    multi_ma_alignment,
    profit_growth,
)

__all__ = ["registry", "BaseCondition"]
