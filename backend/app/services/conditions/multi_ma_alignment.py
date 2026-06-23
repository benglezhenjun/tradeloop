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

        # loose 只需 MA5/10/30/60（60 个交易日即可判定）；strict 才需要到 MA240
        min_rn = 240 if mode == "strict" else 60

        # 扫描窗口保持 480 日历日（足够覆盖 240 个交易日）；最少交易日数由 HAVING 按模式控制
        start_date = (
            datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=480)
        ).strftime("%Y%m%d")

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
                AVG(CASE WHEN rn <= 240 THEN close END) as ma240
            FROM ranked
            GROUP BY ts_code
            HAVING COUNT(CASE WHEN rn <= :min_rn THEN 1 END) >= :min_rn
        """)
        rows = db.execute(
            mas_sql,
            {"trade_date": trade_date, "start_date": start_date, "min_rn": min_rn},
        ).fetchall()
        result = {r[0]: r[1:7] for r in rows}

        def check(ts_code):
            if ts_code not in result:
                return False
            ma5, ma10, ma30, ma60, ma120, ma240 = result[ts_code]
            if mode == "strict":
                if any(v is None for v in [ma5, ma10, ma30, ma60, ma120, ma240]):
                    return False
                return ma5 > ma10 > ma30 > ma60 > ma120 > ma240
            if any(v is None for v in [ma5, ma10, ma30, ma60]):
                return False
            return ma5 > ma60 and ma10 > ma60 and ma30 > ma60

        return df["ts_code"].map(check)


from app.services.conditions import registry  # noqa: E402
registry.register(MultiMaAlignment())
