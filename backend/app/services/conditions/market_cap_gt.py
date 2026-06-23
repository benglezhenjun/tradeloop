"""条件：总市值 > 阈值"""

import pandas as pd

from app.constants import MV_UNIT_TO_YI
from app.services.conditions.base import BaseCondition, ParamDef


class MarketCapGt(BaseCondition):
    code = "market_cap_gt"
    name = "总市值大于阈值"
    category = "市值"
    description = "当日总市值大于指定值，过滤小盘股"
    param_defs = {
        "threshold": ParamDef(
            label="市值下限（亿元）",
            type_="number",
            default=100,  # 默认 100 亿
            description="单位：亿元。如填 100 表示总市值需超过 100 亿",
        )
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        threshold = self.get_param(params, "threshold")
        # daily_quote.total_mv 单位是"万元"，除以常量后转为亿元
        return (df["total_mv"] / MV_UNIT_TO_YI) > threshold


from app.services.conditions import registry  # noqa: E402
registry.register(MarketCapGt())
