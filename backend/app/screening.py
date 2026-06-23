"""
筛选引擎模块

【学习要点】
- 这是 MVP 的核心业务逻辑：从全市场中筛选出符合条件的股票
- MVP 阶段直接硬编码策略 1 的前 4 个条件，后续会重构为可配置的条件引擎
- 所有计算都在本地 SQLite 上完成，不再调用 Tushare API

筛选逻辑（策略 1 的前 4 个条件，AND 关系）：
1. 成交额 > 20 亿
2. 收盘价在 MA20 上方，且偏离 < 6%
3. 总市值 > 100 亿
4. 当日成交额排名全市场前 100
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def run_screening(db: Session, trade_date: str | None = None) -> list[dict]:
    """
    运行筛选策略

    参数��
        db: 数据库会话
        trade_date: 筛选日期（YYYYMMDD），默认取数据库中最新的交易日

    返回：
        符合条件的股票列表，每个元素是一个字典

    【学习要点 - 为什么用原生 SQL 而不是 ORM？】
    这里涉及复杂的聚合计算（MA20、排名等），用 ORM 写会非常啰嗦。
    实际项目中，简单的 CRUD 用 ORM，复杂查询用原生 SQL，这是很常见的做法。
    """

    # 如果没指定日期，取数据库中最新的交易日
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM daily_quote"))
        trade_date = result.scalar()
        if not trade_date:
            return []

    print(f"筛选日期：{trade_date}")

    # ============================================================
    # 核心 SQL：一次查询完成所有筛选条件
    #
    # 【学习要点 - SQL 的 WITH 子句（CTE, 公共表表达式）】
    # WITH 子句让你可以把复杂查询拆成多个"临时表"，一步一步算：
    # 1. latest_quotes: 取最新交易日的行情
    # 2. ma20_calc: 计算每只股票的 MA20（最近 20 个交易日的平均收盘价）
    # 3. ranked: 把行情和 MA20 合并，并计算成交额排名
    # 4. 最终 SELECT: 应用所有筛选条件
    # ============================================================

    sql = text("""
    WITH
    -- 第一步：取指定日期的全市场行情
    latest_quotes AS (
        SELECT
            dq.ts_code,
            dq.trade_date,
            dq.close,
            dq.amount,
            dq.total_mv,
            dq.pct_chg
        FROM daily_quote dq
        WHERE dq.trade_date = :trade_date
          AND dq.close IS NOT NULL
          AND dq.amount IS NOT NULL
    ),

    -- 第二步：计算 MA20（最近 20 个交易日的平均收盘价）
    -- 【学习要点】这里用子查询实现 MA 计算
    -- 对于每只股票，找到 <= 指定日期的最近 20 个交易日，取平均收盘价
    ma20_calc AS (
        SELECT
            ts_code,
            AVG(close) as ma20,
            COUNT(*) as day_count
        FROM (
            SELECT ts_code, close, trade_date,
                   ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
            FROM daily_quote
            WHERE trade_date <= :trade_date
              AND close IS NOT NULL
        )
        WHERE rn <= 20
        GROUP BY ts_code
        HAVING day_count >= 20  -- 至少要有 20 天数据才计算 MA20
    ),

    -- 第三步：合并数据，并计算成交额排名
    ranked AS (
        SELECT
            lq.ts_code,
            lq.trade_date,
            lq.close,
            lq.amount,
            lq.total_mv,
            lq.pct_chg,
            m.ma20,
            -- 偏离度 = (收盘价 - MA20) / MA20
            (lq.close - m.ma20) / m.ma20 as ma20_deviation,
            -- 成交额排名（降序，最大的排第 1）
            ROW_NUMBER() OVER (ORDER BY lq.amount DESC) as amount_rank
        FROM latest_quotes lq
        JOIN ma20_calc m ON lq.ts_code = m.ts_code
    )

    -- 第四步：应用筛选条件
    SELECT
        r.ts_code,
        sb.name,
        sb.industry,
        r.close,
        r.amount / 10 as amount_wan,     -- 千元 → 万元
        r.total_mv,                       -- 万元
        r.pct_chg,
        r.ma20,
        ROUND(r.ma20_deviation * 100, 2) as deviation_pct,  -- 转为百分比
        r.amount_rank
    FROM ranked r
    JOIN stock_basic sb ON r.ts_code = sb.ts_code
    WHERE
        -- 条件 1：成交额 > 20 亿（amount 单位是千元，20亿 = 200万千元）
        r.amount > 2000000

        -- 条件 2：收盘价在 MA20 上方，偏离 < 6%
        AND r.ma20_deviation > 0
        AND r.ma20_deviation < 0.06

        -- 条件 3：总市值 > 100 亿（total_mv 单位是万元，100亿 = 100万万元 = 1000000）
        AND r.total_mv > 1000000

        -- 条件 4：成交额排名前 100
        AND r.amount_rank <= 100

    ORDER BY r.amount_rank ASC
    """)

    result = db.execute(sql, {"trade_date": trade_date})
    rows = result.fetchall()

    # 将结果转为字典列表
    candidates = []
    for row in rows:
        candidates.append(
            {
                "ts_code": row[0],
                "name": row[1],
                "industry": row[2] or "未知",
                "close": round(row[3], 2) if row[3] else None,
                "amount_yi": round(row[4] / 10000, 2) if row[4] else None,  # 万元 → 亿元
                "total_mv_yi": round(row[5] / 10000, 2) if row[5] else None,  # 万元 → 亿元
                "pct_chg": round(row[6], 2) if row[6] else None,
                "ma20": round(row[7], 2) if row[7] else None,
                "deviation_pct": row[8],  # 已在 SQL 中 round
                "amount_rank": row[9],
            }
        )

    print(f"筛选结果：{len(candidates)} 只股票")
    return candidates


def get_available_dates(db: Session, limit: int = 30) -> list[str]:
    """
    获取数据库中可用的交易日期列表（最近 N 个）

    用途：前端下拉框展示可选日期
    """
    result = db.execute(
        text(
            "SELECT DISTINCT trade_date FROM daily_quote "
            "ORDER BY trade_date DESC LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [row[0] for row in result.fetchall()]


def get_data_stats(db: Session) -> dict:
    """
    获取数据库统计信息

    用途：前端展示当前数据状态，帮助你确认数据导入是否正常
    """
    stock_count = db.execute(text("SELECT COUNT(*) FROM stock_basic")).scalar()
    quote_count = db.execute(text("SELECT COUNT(*) FROM daily_quote")).scalar()
    financial_count = db.execute(text("SELECT COUNT(*) FROM stock_financial")).scalar()
    latest_date = db.execute(text("SELECT MAX(trade_date) FROM daily_quote")).scalar()

    return {
        "stock_count": stock_count or 0,
        "quote_count": quote_count or 0,
        "financial_count": financial_count or 0,
        "latest_trade_date": latest_date,
    }
