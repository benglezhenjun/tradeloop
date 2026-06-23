"""个股分析 Agent。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.models import DailyQuote, StockBasic, StockFinancial
from app.services.agents.base import _safe_llm_call
from app.services.indicators import calc_price_stats


def run_stock_agent(db: Session, ts_code: str) -> str:
    stock = db.get(StockBasic, ts_code)
    if not stock:
        return f"> 未找到股票 {ts_code} 的基础信息。"

    quotes = (
        db.query(DailyQuote)
        .filter(DailyQuote.ts_code == ts_code)
        .order_by(DailyQuote.trade_date.desc())
        .limit(60)
        .all()
    )
    if not quotes:
        return f"> **{stock.name}** 暂无行情数据，无法分析。"

    quotes_asc = list(reversed(quotes))
    stats = calc_price_stats(quotes_asc)

    financials = (
        db.query(StockFinancial)
        .filter(StockFinancial.ts_code == ts_code)
        .order_by(StockFinancial.end_date.desc())
        .limit(3)
        .all()
    )

    fin_lines: list[str] = []
    for financial in reversed(financials):
        year = financial.end_date[:4]
        profit = f"{financial.profit_dedt / 1e8:.2f} 亿" if financial.profit_dedt else "N/A"
        revenue = f"{financial.revenue / 1e8:.2f} 亿" if financial.revenue else "N/A"
        fin_lines.append(f"  - {year}年：扣非净利润 {profit}，营收 {revenue}")

    fin_text = "\n".join(fin_lines) if fin_lines else "  - 暂无财务数据"

    prompt = f"""
以下是 **{stock.name}**（{ts_code}，{stock.industry or '未知行业'}）的数据：

**近60日走势**：
- 最新收盘：{stats["latest_close"]:.2f} 元，今日涨跌：{stats["latest_pct"]:+.2f}%
- 近30日累计涨跌：{stats["pct_30d"]:+.2f}%
- 60日最高：{stats["high_60"]:.2f}（当前距高点 {stats["pct_from_high"]:.1f}%）
- 60日最低：{stats["low_60"]:.2f}（当前距低点 +{stats["pct_from_low"]:.1f}%）
- MA20：{stats["ma20"]:.2f}，MA60：{stats["ma60"]:.2f}
- 今日成交额：{stats["latest_amount"] / AMOUNT_UNIT_TO_YI:.1f} 亿，市值：{stats["latest_total_mv"] / MV_UNIT_TO_YI:.0f} 亿

**近3年财务（年报）**：
{fin_text}

请综合分析：
1. 当前技术面所处位置和走势特征
2. 财务层面的基本状况
3. 综合来看值得关注的点（不建议操作）
300 字以内，Markdown 格式。
""".strip()

    return _safe_llm_call(prompt, max_tokens=600)
