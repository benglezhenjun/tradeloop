"""
筛选引擎服务 (V1 重写)

核心逻辑：
1. 拉取指定日期的全市场行情到 DataFrame
2. 按策略中的条件列表逐一过滤（AND 关系）
3. 保存运行记录和结果到数据库
"""

import json
import time
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.errors import build_error
from app.models.strategy import ScreeningResult, Strategy, StrategyCondition, StrategyRun
from app.services.conditions import registry


def get_market_df(db: Session, trade_date: str) -> pd.DataFrame:
    """
    拉取指定日期的全市场行情，返回 DataFrame

    这是所有条件计算的基础数据，一次性拉出来，
    各条件可以在内存中快速过滤，不需要每次查数据库。
    """
    sql = text("""
        SELECT dq.ts_code, dq.trade_date, dq.open, dq.high, dq.low,
               dq.close, dq.amount, dq.vol, dq.total_mv, dq.pct_chg, dq.turnover_rate,
               sb.name, sb.industry, sb.market
        FROM daily_quote dq
        JOIN stock_basic sb ON dq.ts_code = sb.ts_code
        WHERE dq.trade_date = :trade_date
          AND dq.close IS NOT NULL
          AND dq.amount IS NOT NULL
          AND sb.list_status = 'L'
    """)
    rows = db.execute(sql, {"trade_date": trade_date}).mappings().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def run_strategy(db: Session, strategy_id: int, trade_date: str | None = None) -> dict:
    """
    运行指定策略，返回筛选结果

    返回格式：
    {
        "run_id": 123,
        "trade_date": "20241201",
        "strategy_name": "热点追踪",
        "count": 15,
        "duration_ms": 800,
        "candidates": [ {...}, ... ]
    }
    """
    t_start = time.time()

    # 确定筛选日期
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM daily_quote"))
        trade_date = result.scalar()
        if not trade_date:
            return build_error("数据库中没有行情数据，请先同步数据")

    # 查询策略
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return build_error(f"策略 {strategy_id} 不存在")

    # 查询策略的条件列表（按 sort_order 排序）
    sc_list = (
        db.query(StrategyCondition)
        .filter(
            StrategyCondition.strategy_id == strategy_id,
            StrategyCondition.is_enabled == True,  # noqa: E712
        )
        .order_by(StrategyCondition.sort_order)
        .all()
    )

    if not sc_list:
        return build_error(f"策略 {strategy.name} 没有启用的条件")

    # 拉取全市场行情
    df = get_market_df(db, trade_date)
    if df.empty:
        return build_error(f"日期 {trade_date} 没有行情数据")

    # 逐条件过滤（AND 关系）
    mask = pd.Series([True] * len(df), index=df.index)
    for sc in sc_list:
        try:
            condition = registry.get(sc.condition_code)
            params = sc.get_params()
            condition_mask = condition.evaluate(df, db, params)
            mask = mask & condition_mask.reindex(df.index, fill_value=False)
        except Exception as e:
            return build_error(f"条件「{sc.condition_code}」执行出错：{e}")

    result_df = df[mask].copy()
    duration_ms = int((time.time() - t_start) * 1000)

    # 保存运行记录
    run = StrategyRun(
        strategy_id=strategy_id,
        strategy_name=strategy.name,
        trade_date=trade_date,
        result_count=len(result_df),
        duration_ms=duration_ms,
    )
    db.add(run)
    db.flush()  # 拿到 run.id

    # 保存结果快照
    for i, (_, row) in enumerate(result_df.iterrows()):
        snapshot = {
            "close": round(float(row["close"]), 2) if row["close"] else None,
            "amount_yi": round(float(row["amount"]) / AMOUNT_UNIT_TO_YI, 2) if row["amount"] else None,
            "total_mv_yi": round(float(row["total_mv"]) / MV_UNIT_TO_YI, 2) if row["total_mv"] else None,
            "pct_chg": round(float(row["pct_chg"]), 2) if row["pct_chg"] else None,
            "name": row["name"],
            "industry": row["industry"],
        }
        db.add(ScreeningResult(
            run_id=run.id,
            ts_code=row["ts_code"],
            rank=i + 1,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        ))

    db.commit()

    # 整理返回结果
    candidates = []
    for i, (_, row) in enumerate(result_df.iterrows()):
        candidates.append({
            "ts_code": row["ts_code"],
            "name": row["name"],
            "industry": row["industry"] or "未知",
            "close": round(float(row["close"]), 2) if row["close"] else None,
            "amount_yi": round(float(row["amount"]) / AMOUNT_UNIT_TO_YI, 2) if row["amount"] else None,
            "total_mv_yi": round(float(row["total_mv"]) / MV_UNIT_TO_YI, 2) if row["total_mv"] else None,
            "pct_chg": round(float(row["pct_chg"]), 2) if row["pct_chg"] else None,
            "rank": i + 1,
        })

    return {
        "run_id": run.id,
        "trade_date": trade_date,
        "strategy_name": strategy.name,
        "count": len(candidates),
        "duration_ms": duration_ms,
        "candidates": candidates,
    }


def get_available_dates(db: Session, limit: int = 30) -> list[str]:
    result = db.execute(
        text("SELECT DISTINCT trade_date FROM daily_quote ORDER BY trade_date DESC LIMIT :limit"),
        {"limit": limit},
    )
    return list(result.scalars())


def get_data_stats(db: Session) -> dict:
    stock_count = db.execute(text("SELECT COUNT(*) FROM stock_basic")).scalar() or 0
    quote_count = db.execute(text("SELECT COUNT(*) FROM daily_quote")).scalar() or 0
    financial_count = db.execute(text("SELECT COUNT(*) FROM stock_financial")).scalar() or 0
    latest_date = db.execute(text("SELECT MAX(trade_date) FROM daily_quote")).scalar()
    strategy_count = db.execute(text("SELECT COUNT(*) FROM strategy WHERE is_enabled=1")).scalar() or 0
    return {
        "stock_count": stock_count,
        "quote_count": quote_count,
        "financial_count": financial_count,
        "latest_trade_date": latest_date,
        "strategy_count": strategy_count,
    }
