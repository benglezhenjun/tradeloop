"""
K线数据查询服务

从 daily_quote 表读取 OHLCV 数据，供前端 ECharts 绘图用。
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI


def get_kline(db: Session, ts_code: str, start_date: str | None = None, end_date: str | None = None) -> dict | None:
    """
    获取某只股票的K线数据。

    参数：
        ts_code: 股票代码，如 "000001.SZ"
        start_date: 起始日期 YYYYMMDD（可选，默认往前推180个交易日）
        end_date: 结束日期 YYYYMMDD（可选，默认最新交易日）

    返回：
        {ts_code, name, industry, klines: [{date, open, high, low, close, vol, amount_yi, pct_chg}, ...]}
    """
    # 查股票基本信息
    basic = db.execute(
        text("SELECT ts_code, name, industry FROM stock_basic WHERE ts_code = :code"),
        {"code": ts_code},
    ).mappings().fetchone()

    if not basic:
        return None

    # 构建日期过滤条件
    conditions = ["ts_code = :code"]
    params: dict = {"code": ts_code}

    if start_date:
        conditions.append("trade_date >= :start")
        params["start"] = start_date

    if end_date:
        conditions.append("trade_date <= :end")
        params["end"] = end_date

    # 如果没指定起始日期，默认取最近 180 条
    limit_clause = "" if start_date else "LIMIT 180"
    where = " AND ".join(conditions)

    inner_sql = f"""
        SELECT trade_date, open, high, low, close, vol, amount, pct_chg
        FROM daily_quote
        WHERE {where}
        ORDER BY trade_date {"DESC" if not start_date else "ASC"}
        {limit_clause}
    """
    sql = text(f"""
        SELECT trade_date, open, high, low, close, vol, amount, pct_chg
        FROM ({inner_sql}) AS quote_rows
        ORDER BY trade_date ASC
    """)

    rows = db.execute(sql, params).mappings().all()

    klines = [
        {
            "date": r["trade_date"],
            "open": round(r["open"], 2) if r["open"] else None,
            "high": round(r["high"], 2) if r["high"] else None,
            "low": round(r["low"], 2) if r["low"] else None,
            "close": round(r["close"], 2) if r["close"] else None,
            "vol": round(r["vol"], 2) if r["vol"] else None,
            "amount_yi": round(r["amount"] / AMOUNT_UNIT_TO_YI, 2) if r["amount"] else None,
            "pct_chg": round(r["pct_chg"], 2) if r["pct_chg"] else None,
        }
        for r in rows
    ]

    return {
        "ts_code": basic["ts_code"],
        "name": basic["name"],
        "industry": basic["industry"],
        "klines": klines,
    }
