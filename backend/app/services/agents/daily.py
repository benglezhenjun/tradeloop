"""日报相关 Agents。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.models import DailyQuote, ScreeningResult, StockBasic, StrategyRun, WatchlistStock
from app.services.agents.base import _ERROR_PREFIX, _safe_llm_call
from app.services.market import get_industry_heat, get_market_overview


def run_market_agent(db: Session) -> str:
    data = get_market_overview(db)

    if data["trade_date"] is None:
        return "> 暂无行情数据，无法进行市场分析。"

    prompt = f"""
以下是 {data["trade_date"]} 的 A 股市场数据：
- 上涨 {data["up_count"]} 家，下跌 {data["down_count"]} 家，平盘 {data["flat_count"]} 家
- 涨停 {data["limit_up_count"]} 家，跌停 {data["limit_down_count"]} 家
- 全市场成交额 {data["total_amount_yi"]:.0f} 亿元
- 全市场平均涨跌幅 {data["avg_pct_chg"]:+.2f}%

请分析今日市场整体环境，200 字以内，包含：
1. 市场情绪判断（偏多/偏空/震荡）及依据
2. 成交量特征（放量/缩量/平稳）
3. 一个值得关注的信号或风险提示
""".strip()

    return _safe_llm_call(prompt, max_tokens=400)


def run_industry_agent(db: Session) -> str:
    heat = get_industry_heat(db)

    if not heat:
        return "> 暂无行业数据，无法进行行业分析。"

    top5 = heat[:5]
    bottom5 = heat[-5:] if len(heat) >= 5 else heat
    total_amount = sum(item["total_amount_yi"] for item in heat)

    top_lines = "\n".join(
        f"  - {item['industry']}：平均涨幅 {item['avg_pct_chg']:+.2f}%，成交额 {item['total_amount_yi']:.0f} 亿"
        for item in top5
    )
    bottom_lines = "\n".join(
        f"  - {item['industry']}：平均涨幅 {item['avg_pct_chg']:+.2f}%，成交额 {item['total_amount_yi']:.0f} 亿"
        for item in reversed(bottom5)
    )

    prompt = f"""
今日 A 股行业表现（共 {len(heat)} 个行业，全市场成交额 {total_amount:.0f} 亿元）：

涨幅居前：
{top_lines}

跌幅居前：
{bottom_lines}

请分析：
1. 今日资金主要流向哪些板块？有何特征？
2. 弱势板块的可能原因
3. 是否存在明显的板块轮动信号？
250 字以内，Markdown 格式。
""".strip()

    return _safe_llm_call(prompt, max_tokens=500)


def run_watchlist_agent(db: Session) -> str:
    codes = [row[0] for row in db.query(WatchlistStock.ts_code).distinct().all()]
    if not codes:
        return "> 自选股列表为空，跳过自选股分析。"

    latest_date = db.query(func.max(DailyQuote.trade_date)).scalar()
    if not latest_date:
        return "> 暂无行情数据，无法分析自选股。"

    stock_summaries: list[str] = []
    for ts_code in codes[:20]:
        rows = (
            db.query(DailyQuote.trade_date, DailyQuote.close, DailyQuote.pct_chg, DailyQuote.amount, DailyQuote.vol)
            .filter(DailyQuote.ts_code == ts_code)
            .order_by(DailyQuote.trade_date.desc())
            .limit(5)
            .all()
        )
        if not rows:
            continue

        stock = db.get(StockBasic, ts_code)
        name = stock.name if stock else ts_code
        latest = rows[0]
        pct_5d = sum(row.pct_chg for row in rows if row.pct_chg is not None)
        amount_values = [row.amount for row in rows if row.amount]
        avg_amount = sum(amount_values) / len(amount_values) if amount_values else 0

        stock_summaries.append(
            f"- **{name}**（{ts_code}）：最新收盘 {latest.close:.2f}，"
            f"今日涨跌 {latest.pct_chg:+.2f}%，近5日累计 {pct_5d:+.2f}%，"
            f"近5日均成交额 {avg_amount / AMOUNT_UNIT_TO_YI:.1f} 亿"
        )

    if not stock_summaries:
        return "> 自选股暂无近期行情数据。"

    prompt = f"""
以下是我的自选股近 5 个交易日的数据摘要：

{chr(10).join(stock_summaries)}

请对每只股票给出 1-2 句简评，指出其走势特征（强势/弱势/震荡/放量/缩量等），
不需要给出买卖建议。Markdown 格式，用列表展示。
""".strip()

    return _safe_llm_call(prompt, max_tokens=800)


def run_screening_agent(db: Session) -> str:
    run = db.query(StrategyRun).order_by(StrategyRun.run_at.desc()).first()
    if not run:
        return "> 尚无策略筛选记录，跳过筛选结果分析。"

    results = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.run_id == run.id)
        .order_by(ScreeningResult.rank)
        .limit(20)
        .all()
    )
    if not results:
        return "> 最近一次筛选结果为空。"

    lines: list[str] = []
    for result in results:
        stock = db.get(StockBasic, result.ts_code)
        name = stock.name if stock else result.ts_code
        snapshot = result.get_snapshot()
        pct = snapshot.get("pct_chg")
        amount = snapshot.get("amount")
        mv = snapshot.get("total_mv")

        parts = [f"**{name}**（{result.ts_code}）"]
        if pct is not None:
            parts.append(f"涨跌 {pct:+.2f}%")
        if amount is not None:
            parts.append(f"成交额 {amount / AMOUNT_UNIT_TO_YI:.1f} 亿")
        if mv is not None:
            parts.append(f"市值 {mv / MV_UNIT_TO_YI:.0f} 亿")
        lines.append("- " + "，".join(parts))

    run_at = run.run_at.strftime("%Y-%m-%d %H:%M") if run.run_at else "未知"
    prompt = f"""
策略「{run.strategy_name}」在 {run.trade_date or "未知"} 筛选出以下 {len(results)} 只股票（运行于 {run_at}）：

{chr(10).join(lines)}

请分析：
1. 这批入选股票有哪些共同特征（行业、规模、量价特征等）？
2. 整体质量评价
3. 是否有值得特别关注的个股？（仅描述特征，不建议操作）
250 字以内，Markdown 格式。
""".strip()

    return _safe_llm_call(prompt, max_tokens=500)


def run_report_agent(sections: dict[str, str]) -> str:
    today = datetime.now().strftime("%Y年%m月%d日")
    valid_sections = {key: value for key, value in sections.items() if not value.startswith(_ERROR_PREFIX)}
    if not valid_sections:
        return "> 所有分析部分均生成失败，无法生成日报。"

    section_labels = {
        "market": "市场环境",
        "industry": "行业热度",
        "watchlist": "自选股动态",
        "screening": "筛选策略回顾",
    }
    summaries = "\n\n".join(f"**{section_labels.get(key, key)}**：\n{value}" for key, value in valid_sections.items())

    prompt = f"""
以下是今日（{today}）各模块的分析摘要：

{summaries}

请基于以上信息，生成一份简洁的每日投研日报，结构如下：
1. **今日市场总结**（2-3句）
2. **核心关注点**（3条要点，bullet格式）
3. **明日展望**（1-2句，基于今日数据推断，不预测涨跌）

200 字以内，Markdown 格式。
""".strip()

    return _safe_llm_call(prompt, max_tokens=500)
