"""条件：扣非归母净利润连续三年增长"""

import pandas as pd
from sqlalchemy import text

from app.services.conditions.base import BaseCondition, ParamDef


class ProfitGrowth(BaseCondition):
    code = "profit_growth"
    name = "扣非净利润连续增长"
    category = "基本面"
    description = "扣非归母净利润连续N年同比增长，且最近一年为正值。策略1的基本面质量条件"
    param_defs = {
        "years": ParamDef(
            label="连续增长年数",
            type_="int",
            default=3,
            description="要求连续几年同比增长。最少2年，通常用3年",
        )
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        years = int(self.get_param(params, "years"))

        # 获取最近 (years+1) 个年报数据
        # 用年报（end_date 以 1231 结尾），取每年最新公告
        sql = text("""
            WITH annual AS (
                SELECT ts_code, end_date, profit_dedt,
                       ROW_NUMBER() OVER (PARTITION BY ts_code, end_date ORDER BY ann_date DESC) as rn
                FROM stock_financial
                WHERE end_date LIKE '%1231'
                  AND profit_dedt IS NOT NULL
            ),
            latest_annual AS (
                SELECT ts_code, end_date, profit_dedt
                FROM annual WHERE rn = 1
            ),
            ranked_annual AS (
                SELECT ts_code, end_date, profit_dedt,
                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY end_date DESC) as yr
                FROM latest_annual
            )
            SELECT ts_code, end_date, profit_dedt
            FROM ranked_annual
            WHERE yr <= :needed_years
            ORDER BY ts_code, end_date ASC
        """)
        rows = db.execute(sql, {"needed_years": years + 1}).fetchall()

        # 按股票分组
        from collections import defaultdict
        stock_profits: dict[str, list[float]] = defaultdict(list)
        for ts_code, end_date, profit in rows:
            stock_profits[ts_code].append(profit)

        def check(ts_code):
            profits = stock_profits.get(ts_code, [])
            if len(profits) < years + 1:
                return False
            # profits 按年份升序排列（最老的在前）
            # 最近一年必须为正
            if profits[-1] <= 0:
                return False
            # 检查连续增长
            for i in range(len(profits) - years, len(profits)):
                if profits[i] <= profits[i - 1]:
                    return False
            return True

        return df["ts_code"].map(check).fillna(False)


from app.services.conditions import registry  # noqa: E402
registry.register(ProfitGrowth())
