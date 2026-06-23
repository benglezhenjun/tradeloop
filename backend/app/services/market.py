"""
市场温度服务 (V3)

从现有 DailyQuote + StockBasic 数据计算市场级别统计指标。
不需要新增 Tushare API 调用，不需要新增数据表。

涨停判断规则：
- ts_code 以 688 开头（科创板）或 300/301 开头（创业板）：±20% 阈值
- 其余（主板/北交所等）：±10% 阈值
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI
from app.models import DailyQuote, StockBasic


def _get_latest_trade_date(db: Session) -> str | None:
    """取 daily_quote 中最新的交易日期，无数据则返回 None。"""
    row = db.query(func.max(DailyQuote.trade_date)).scalar()
    return row  # None if table empty


def _is_star_or_gem(ts_code: str) -> bool:
    """判断是否为科创板（688）或创业板（300/301），采用 ±20% 涨跌幅限制。"""
    return ts_code.startswith("688") or ts_code.startswith("300") or ts_code.startswith("301")


def get_market_overview(db: Session, trade_date: str | None = None) -> dict:
    """
    返回指定交易日的市场概览统计。

    trade_date 为 None 时自动取最新交易日。
    无数据时返回全 0 结构，不抛异常。

    返回字段：
        trade_date         : 交易日期（YYYYMMDD），无数据时为 None
        up_count           : 上涨家数
        down_count         : 下跌家数
        flat_count         : 平盘家数
        limit_up_count     : 涨停家数
        limit_down_count   : 跌停家数
        total_amount_yi    : 全市场成交额（亿元）
        avg_pct_chg        : 全市场平均涨跌幅（%）
    """
    empty = {
        "trade_date": None,
        "up_count": 0, "down_count": 0, "flat_count": 0,
        "limit_up_count": 0, "limit_down_count": 0,
        "total_amount_yi": 0.0, "avg_pct_chg": 0.0,
    }

    if trade_date is None:
        trade_date = _get_latest_trade_date(db)
    if trade_date is None:
        return empty

    rows = (
        db.query(DailyQuote.ts_code, DailyQuote.pct_chg, DailyQuote.amount)
        .filter(DailyQuote.trade_date == trade_date)
        .filter(DailyQuote.pct_chg.isnot(None))
        .all()
    )

    if not rows:
        return empty

    up = down = flat = limit_up = limit_down = 0
    total_amount = 0.0
    total_pct = 0.0

    for ts_code, pct_chg, amount in rows:
        # 涨跌平统计
        if pct_chg > 0:
            up += 1
        elif pct_chg < 0:
            down += 1
        else:
            flat += 1

        # 涨跌停统计（按板块区分阈值）
        threshold = 19.9 if _is_star_or_gem(ts_code) else 9.9
        if pct_chg >= threshold:
            limit_up += 1
        elif pct_chg <= -threshold:
            limit_down += 1

        if amount is not None:
            total_amount += amount
        total_pct += pct_chg

    count = len(rows)
    return {
        "trade_date": trade_date,
        "up_count": up,
        "down_count": down,
        "flat_count": flat,
        "limit_up_count": limit_up,
        "limit_down_count": limit_down,
        "total_amount_yi": round(total_amount / AMOUNT_UNIT_TO_YI, 2),
        "avg_pct_chg": round(total_pct / count, 3),
    }


def get_industry_heat(db: Session, trade_date: str | None = None) -> list[dict]:
    """
    返回指定交易日各行业的热度统计，按平均涨跌幅降序排列。

    过滤规则：
    - StockBasic.industry 为 NULL 或空字符串的股票不计入任何行业
    - 某行业无行情数据则不出现在结果里

    每项返回字段：
        industry          : 行业名称
        stock_count       : 该行业今日有行情的股票数
        avg_pct_chg       : 行业平均涨跌幅（%）
        total_amount_yi   : 行业成交额合计（亿元）
        up_count          : 行业内上涨家数
        down_count        : 行业内下跌家数
    """
    if trade_date is None:
        trade_date = _get_latest_trade_date(db)
    if trade_date is None:
        return []

    # 联结查询：当日行情 + 行业信息
    rows = (
        db.query(
            StockBasic.industry,
            DailyQuote.pct_chg,
            DailyQuote.amount,
        )
        .join(DailyQuote, StockBasic.ts_code == DailyQuote.ts_code)
        .filter(DailyQuote.trade_date == trade_date)
        .filter(DailyQuote.pct_chg.isnot(None))
        .filter(StockBasic.industry.isnot(None))
        .filter(StockBasic.industry != "")
        .all()
    )

    if not rows:
        return []

    # 按行业聚合
    industry_data: dict[str, dict] = {}
    for industry, pct_chg, amount in rows:
        if industry not in industry_data:
            industry_data[industry] = {
                "stock_count": 0, "pct_sum": 0.0,
                "amount_sum": 0.0, "up": 0, "down": 0,
            }
        d = industry_data[industry]
        d["stock_count"] += 1
        d["pct_sum"] += pct_chg
        if amount is not None:
            d["amount_sum"] += amount
        if pct_chg > 0:
            d["up"] += 1
        elif pct_chg < 0:
            d["down"] += 1

    result = []
    for industry, d in industry_data.items():
        count = d["stock_count"]
        result.append({
            "industry": industry,
            "stock_count": count,
            "avg_pct_chg": round(d["pct_sum"] / count, 3),
            "total_amount_yi": round(d["amount_sum"] / AMOUNT_UNIT_TO_YI, 2),
            "up_count": d["up"],
            "down_count": d["down"],
        })

    result.sort(key=lambda x: x["avg_pct_chg"], reverse=True)
    return result


def get_breadth_history(db: Session, days: int = 30) -> list[dict]:
    """
    返回最近 N 个交易日的市场宽度统计（上涨/下跌/平盘家数），按日期升序。

    只统计 pct_chg 不为 NULL 的记录。

    每项返回字段：
        trade_date  : 交易日期（YYYYMMDD）
        up_count    : 上涨家数
        down_count  : 下跌家数
        flat_count  : 平盘家数
    """
    # 取最近 days 个不重复交易日
    date_rows = (
        db.query(DailyQuote.trade_date)
        .filter(DailyQuote.pct_chg.isnot(None))
        .distinct()
        .order_by(DailyQuote.trade_date.desc())
        .limit(days)
        .all()
    )

    if not date_rows:
        return []

    trade_dates = sorted([r[0] for r in date_rows])  # 升序

    # 批量查询这些日期的数据
    rows = (
        db.query(DailyQuote.trade_date, DailyQuote.pct_chg)
        .filter(DailyQuote.trade_date.in_(trade_dates))
        .filter(DailyQuote.pct_chg.isnot(None))
        .all()
    )

    # 按日期聚合
    date_stats: dict[str, dict] = {d: {"up": 0, "down": 0, "flat": 0} for d in trade_dates}
    for trade_date, pct_chg in rows:
        s = date_stats[trade_date]
        if pct_chg > 0:
            s["up"] += 1
        elif pct_chg < 0:
            s["down"] += 1
        else:
            s["flat"] += 1

    return [
        {
            "trade_date": d,
            "up_count": date_stats[d]["up"],
            "down_count": date_stats[d]["down"],
            "flat_count": date_stats[d]["flat"],
        }
        for d in trade_dates
    ]
