"""条件：当日成交额排名全市场前 N"""

import pandas as pd

from app.services.conditions.base import BaseCondition, ParamDef


class AmountRank(BaseCondition):
    code = "amount_rank"
    name = "成交额排名前N"
    category = "排名"
    description = "当日成交额在全市场降序排名前 N，确保选的是今天最活跃的股票"
    param_defs = {
        "top_n": ParamDef(
            label="排名前N",
            type_="int",
            default=100,
            description="如填100，则只保留今日成交额全市场前100名",
        )
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        top_n = int(self.get_param(params, "top_n"))
        # rank(ascending=False) 让最大值排第1
        ranks = df["amount"].rank(ascending=False, method="min")
        return ranks <= top_n


from app.services.conditions import registry  # noqa: E402
registry.register(AmountRank())
