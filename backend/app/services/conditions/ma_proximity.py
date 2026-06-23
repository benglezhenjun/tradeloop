"""条件：收盘价在均线上方，且偏离不超过阈值"""

import pandas as pd
from sqlalchemy import text

from app.services.conditions.base import BaseCondition, ParamDef


class MaProximity(BaseCondition):
    code = "ma_proximity"
    name = "价格在均线上方且偏离有限"
    category = "技术"
    description = "收盘价在 MA(N) 上方，且偏离度 < 上限。确保既在均线支撑之上，又没涨太多"
    param_defs = {
        "ma_period": ParamDef(
            label="均线周期（天）",
            type_="int",
            default=20,
            description="如20表示MA20，即最近20个交易日平均收盘价",
        ),
        "deviation_max": ParamDef(
            label="最大偏离度",
            type_="number",
            default=0.06,
            description="(close-MA)/MA 的上限。0.06表示偏离不超过6%",
        ),
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        ma_period = int(self.get_param(params, "ma_period"))
        deviation_max = float(self.get_param(params, "deviation_max"))
        trade_date = df["trade_date"].iloc[0]

        # 取每只股票最近 ma_period 个【交易日】均值；不按日历日截断，
        # 否则长期停牌/长假的股票会因窗口内交易日不足被误删
        sql = text("""
            SELECT ts_code, AVG(close) as ma_val
            FROM (
                SELECT ts_code, close,
                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
                FROM daily_quote
                WHERE trade_date <= :trade_date
                  AND close IS NOT NULL
            )
            WHERE rn <= :period
            GROUP BY ts_code
            HAVING COUNT(*) >= :period
        """)
        rows = db.execute(sql, {"trade_date": trade_date, "period": ma_period}).fetchall()
        ma_map = {r[0]: r[1] for r in rows}

        ma_series = df["ts_code"].map(ma_map)
        deviation = (df["close"] - ma_series) / ma_series
        return (deviation > 0) & (deviation < deviation_max)


from app.services.conditions import registry  # noqa: E402
registry.register(MaProximity())
