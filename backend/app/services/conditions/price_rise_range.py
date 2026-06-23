"""条件：区间内曾经大涨（最高价 vs 最低价）"""

import pandas as pd
from sqlalchemy import text

from app.services.conditions.base import BaseCondition, ParamDef


class PriceRiseRange(BaseCondition):
    code = "price_rise_range"
    name = "区间内曾大涨"
    category = "技术"
    description = "近N个交易日内（最高价 - 最低价）/ 最低价 >= 目标涨幅。策略2用于确认该股已经历过一波行情"
    param_defs = {
        "days": ParamDef(
            label="统计天数",
            type_="int",
            default=240,
            description="统计最近N个交易日内的最高价和最低价",
        ),
        "min_rise": ParamDef(
            label="最小涨幅",
            type_="number",
            default=0.5,
            description="(最高-最低)/最低 的最小值。0.5表示区间内曾涨过50%",
        ),
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        days = int(self.get_param(params, "days"))
        min_rise = float(self.get_param(params, "min_rise"))
        trade_date = df["trade_date"].iloc[0]

        sql = text("""
            SELECT ts_code,
                   MAX(high) as period_high,
                   MIN(low) as period_low
            FROM (
                SELECT ts_code, high, low,
                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
                FROM daily_quote
                WHERE trade_date <= :trade_date
                  AND high IS NOT NULL AND low IS NOT NULL AND low > 0
            )
            WHERE rn <= :days
            GROUP BY ts_code
            HAVING COUNT(*) >= :days
        """)
        rows = db.execute(sql, {"trade_date": trade_date, "days": days}).fetchall()
        result = {r[0]: (r[1], r[2]) for r in rows}

        def check(ts_code):
            if ts_code not in result:
                return False
            high, low = result[ts_code]
            if low is None or low == 0:
                return False
            return (high - low) / low >= min_rise

        return df["ts_code"].map(check)


from app.services.conditions import registry  # noqa: E402
registry.register(PriceRiseRange())
