"""
条件基类和注册器

【学习要点 - 为什么这样设计？】
以前筛选是一个大 SQL，想改参数要改代码，想加条件要改 SQL，
每次都可能引入 Bug。

新设计：
- 每个条件封装成一个类，有明确的参数定义
- 条件注册后，系统自动知道有哪些条件
- 策略 = 条件列表，每个条件有自己的参数值
- 执行时：读取策略 → 找到条件实例 → 传入参数 → 过滤

这样新增条件不影响旧代码，旧条件可以随时修改参数，完全解耦。
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class ParamDef:
    """参数定义：描述一个条件参数的名字、类型、默认值和说明"""

    def __init__(self, label: str, type_: str, default: Any, description: str = ""):
        self.label = label          # 给用户看的名字，如"成交额下限"
        self.type = type_           # 类型：number / int / bool / select
        self.default = default      # 默认值
        self.description = description

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "description": self.description,
        }


class BaseCondition(ABC):
    """
    所有筛选条件的基类

    子类必须实现：
    - code: 条件代码（程序内部用，不重复）
    - name: 条件名称（给用户看）
    - category: 分类（量价/市值/技术/基本面/排名）
    - description: 条件说明
    - param_defs: 参数定义列表
    - evaluate(): 核心执行逻辑
    """

    code: str = ""
    name: str = ""
    category: str = ""
    description: str = ""
    param_defs: dict[str, ParamDef] = {}

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        """
        执行筛选条件，返回布尔 Series（True 表示通过）

        参数：
            df: 包含当日全市场行情的 DataFrame
                必须包含字段：ts_code, trade_date, close, amount, total_mv, pct_chg
            db: 数据库会话（某些条件需要查额外数据，如财务数据）
            params: 本次执行的参数值（覆盖默认值）

        返回：
            pd.Series[bool]，索引与 df 一致，True 表示该股通过此条件
        """

    def get_param(self, params: dict, key: str) -> Any:
        """从 params 中取值，取不到则用默认值"""
        if key in params and params[key] is not None:
            return params[key]
        if key in self.param_defs:
            return self.param_defs[key].default
        raise KeyError(f"条件 {self.code} 没有参数 {key}")

    def schema(self) -> dict:
        """输出条件的完整描述（给前端用）"""
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "params": {k: v.to_dict() for k, v in self.param_defs.items()},
        }


class ConditionRegistry:
    """条件注册器（全局单例）"""

    def __init__(self):
        self._conditions: dict[str, BaseCondition] = {}

    def register(self, condition: BaseCondition):
        """注册一个条件实例"""
        self._conditions[condition.code] = condition

    def get(self, code: str) -> BaseCondition:
        """按 code 获取条件"""
        if code not in self._conditions:
            raise ValueError(f"未知条件：{code}，请检查拼写或是否已注册")
        return self._conditions[code]

    def all(self) -> list[dict]:
        """返回所有条件的描述列表（给前端展示用）"""
        return [c.schema() for c in self._conditions.values()]

    def codes(self) -> list[str]:
        return list(self._conditions.keys())
