"""条件：均线多头排列"""

from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text

from app.services.conditions.base import BaseCondition, ParamDef


class MultiMaAlignment(BaseCondition):
    code = "multi_ma_alignment"
    name = "均线多头排列"
    category = "技术"
    description = "短期均线在长期均线之上。支持两种模式：严格（MA5>MA10>MA30>MA60>MA120>MA240）或宽松（MA5/MA10/MA30 均在 MA60 之上）"
    param_defs = {
        "mode": ParamDef(
            label="模式",
            type_="select",
            default="loose",
            description="strict=严格排序，loose=宽松（短均在MA60上方）",
        )
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        mode = self.get_param(params, "mode")
        trade_date = df["trade_date"].iloc[0]

        if mode == "strict":
            periods = [5, 10, 30, 60, 120, 240]
        else:
            periods = [5, 10, 30, 60]

        # 一次性查出所有需要的均线
        period_list = ",".join(str(p) for p in periods)
        sql = text(f"""
            SELECT ts_code, period, ma_val FROM (
                SELECT ts_code,
                       :p5 as period,
                       AVG(CASE WHEN rn <= :p5 THEN close END) as ma_val
                FROM (
                    SELECT ts_code, close,
                           ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
                    FROM daily_quote
                    WHERE trade_date <= :trade_date AND close IS NOT NULL
                )
                GROUP BY ts_code HAVING COUNT(CASE WHEN rn <= :p5 THEN 1 END) >= :p5
            )
        """)

        # 只扫描 MA240 * 2 倍日历天数，避免全表扫描
        start_date = (
            datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=480)
        ).strftime("%Y%m%d")

        # 简化：直接查所有均线，减少代码复杂度
        mas_sql = text("""
            WITH ranked AS (
                SELECT ts_code, close,
                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
                FROM daily_quote
                WHERE trade_date <= :trade_date
                  AND trade_date >= :start_date
                  AND close IS NOT NULL
            )
            SELECT ts_code,
                AVG(CASE WHEN rn <= 5 THEN close END)   as ma5,
                AVG(CASE WHEN rn <= 10 THEN close END)  as ma10,
                AVG(CASE WHEN rn <= 30 THEN close END)  as ma30,
                AVG(CASE WHEN rn <= 60 THEN close END)  as ma60,
                AVG(CASE WHEN rn <= 120 THEN close END) as ma120,
                AVG(CASE WHEN rn <= 240 THEN close END) as ma240,
                COUNT(CASE WHEN rn <= 240 THEN 1 END)   as cnt
            FROM ranked
            GROUP BY ts_code
            HAVING cnt >= 240
        """)
        rows = db.execute(mas_sql, {"trade_date": trade_date, "start_date": start_date}).fetchall()
        # ts_code, ma5, ma10, ma30, ma60, ma120, ma240, cnt — 只取前6个MA值
        result = {r[0]: r[1:7] for r in rows}

        def check(ts_code):
            if ts_code not in result:
                return False
            ma5, ma10, ma30, ma60, ma120, ma240 = result[ts_code]
            if any(v is None for v in [ma5, ma10, ma30, ma60, ma120, ma240]):
                return False
            if mode == "strict":
                return ma5 > ma10 > ma30 > ma60 > ma120 > ma240
            else:  # loose
                return ma5 > ma60 and ma10 > ma60 and ma30 > ma60

        return df["ts_code"].map(check)


from app.services.conditions import registry  # noqa: E402
registry.register(MultiMaAlignment())
