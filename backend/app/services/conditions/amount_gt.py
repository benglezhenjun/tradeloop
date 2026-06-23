"""条件：当日成交额 > 阈值"""

import pandas as pd

from app.constants import AMOUNT_UNIT_TO_YI
from app.services.conditions.base import BaseCondition, ParamDef


class AmountGt(BaseCondition):
    code = "amount_gt"
    name = "成交额大于阈值"
    category = "量价"
    description = "当日成交额大于指定值，筛选活跃股"
    param_defs = {
        "threshold": ParamDef(
            label="成交额下限（亿元）",
            type_="number",
            default=20,  # 默认 20 亿
            description="单位：亿元。如填 20 表示成交额需超过 20 亿",
        )
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        threshold = self.get_param(params, "threshold")
        # daily_quote.amount 单位是"千元"，除以常量后转为亿元
        return (df["amount"] / AMOUNT_UNIT_TO_YI) > threshold


# 注册到全局注册器
from app.services.conditions import registry  # noqa: E402
registry.register(AmountGt())
