"""条件：长期均线斜率（MA240）舒缓向上"""

import pandas as pd
from sqlalchemy import text

from app.services.conditions.base import BaseCondition, ParamDef


class MaSlope(BaseCondition):
    code = "ma_slope"
    name = "均线斜率向上且平缓"
    category = "技术"
    description = "MA(N) 的斜率 > 0（向上），且斜率 < 上限（不是陡峭拉升）。策略2用于判断年线是否舒缓向上"
    param_defs = {
        "ma_period": ParamDef(
            label="均线周期（天）",
            type_="int",
            default=240,
            description="一般用240（年线）",
        ),
        "slope_window": ParamDef(
            label="斜率计算窗口（天）",
            type_="int",
            default=20,
            description="用最近N天的均线计算斜率趋势",
        ),
        "slope_max": ParamDef(
            label="斜率上限（每天涨幅%）",
            type_="number",
            default=0.002,
            description="斜率=(最新MA-N天前MA)/(N天前MA)。0.002表示N天内均线涨幅不超过0.2%",
        ),
    }

    def evaluate(self, df: pd.DataFrame, db, params: dict) -> pd.Series:
        ma_period = int(self.get_param(params, "ma_period"))
        slope_window = int(self.get_param(params, "slope_window"))
        slope_max = float(self.get_param(params, "slope_max"))
        trade_date = df["trade_date"].iloc[0]

        # 不按日历日截断，按交易日倒序取，避免长期停牌/长假股被误删（依赖 ix_daily_code_date 索引）
        sql = text("""
            WITH ranked AS (
                SELECT ts_code, trade_date, close,
                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
                FROM daily_quote
                WHERE trade_date <= :trade_date
                  AND close IS NOT NULL
            ),
            ma_current AS (
                SELECT ts_code, AVG(close) as ma_val
                FROM ranked WHERE rn <= :ma_period
                GROUP BY ts_code HAVING COUNT(*) >= :ma_period
            ),
            ma_past AS (
                SELECT ts_code, AVG(close) as ma_val_past
                FROM ranked WHERE rn > :slope_window AND rn <= (:ma_period + :slope_window)
                GROUP BY ts_code HAVING COUNT(*) >= :ma_period
            )
            SELECT c.ts_code, c.ma_val, p.ma_val_past
            FROM ma_current c JOIN ma_past p ON c.ts_code = p.ts_code
        """)
        rows = db.execute(sql, {
            "trade_date": trade_date,
            "ma_period": ma_period,
            "slope_window": slope_window,
        }).fetchall()

        result = {r[0]: (r[1], r[2]) for r in rows}

        def check(ts_code):
            if ts_code not in result:
                return False
            ma_now, ma_past = result[ts_code]
            if ma_past is None or ma_past == 0:
                return False
            slope = (ma_now - ma_past) / ma_past
            return 0 < slope < slope_max

        return df["ts_code"].map(check)


from app.services.conditions import registry  # noqa: E402
registry.register(MaSlope())
