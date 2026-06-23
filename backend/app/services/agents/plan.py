"""交易计划生成 Agent。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.errors import build_error
from app.models import DailyQuote, StockBasic, StockFinancial
from app.services.agents.base import _PLAN_SYSTEM_PROMPT, _extract_first_json_payload, _safe_llm_call
from app.services.price_stats import calc_price_stats
from app.services.plan_contract import build_manual_fallback, validate_plan_payload


def run_plan_agent(db: Session, ts_code: str, total_capital: float) -> dict:
    stock = db.get(StockBasic, ts_code)
    if not stock:
        return build_error(f"未找到股票 {ts_code}", "not_found")

    quotes = (
        db.query(DailyQuote)
        .filter(DailyQuote.ts_code == ts_code)
        .order_by(DailyQuote.trade_date.desc())
        .limit(60)
        .all()
    )
    if not quotes:
        return build_error(f"{stock.name} 暂无行情数据", "validation")

    quotes_asc = list(reversed(quotes))
    stats = calc_price_stats(quotes_asc)

    try:
        financials = (
            db.query(StockFinancial)
            .filter(StockFinancial.ts_code == ts_code)
            .order_by(StockFinancial.end_date.desc())
            .limit(1)
            .all()
        )
        fin_text = "暂无财务数据"
        if financials:
            financial = financials[0]
            parts: list[str] = []
            if financial.revenue is not None:
                parts.append(f"营收 {financial.revenue / 1e8:.1f} 亿")
            if financial.profit_dedt is not None:
                parts.append(f"扣非净利 {financial.profit_dedt / 1e8:.1f} 亿")
            if parts:
                fin_text = f"{financial.end_date[:4]}年报：" + "，".join(parts)

        from app.services import agents as agents_pkg

        market = agents_pkg.get_market_overview(db)
        market_text = "暂无市场数据"
        if market.get("trade_date"):
            market_text = (
                f"上涨{market['up_count']}家/下跌{market['down_count']}家，"
                f"成交额{market['total_amount_yi']:.0f}亿，"
                f"均涨跌{market['avg_pct_chg']:+.2f}%"
            )

        prompt = f"""根据以下数据，为 **{stock.name}**（{ts_code}，{stock.industry or '未知行业'}）生成三套交易方案。

## 股票数据
- 最新收盘：{stats["latest_close"]:.2f} 元，今日涨跌：{stats["latest_pct"]:+.2f}%
- 近30日涨跌：{stats["pct_30d"]:+.2f}%
- 60日最高/最低：{stats["high_60"]:.2f} / {stats["low_60"]:.2f}
- MA5：{stats["ma5"]:.2f}，MA20：{stats["ma20"]:.2f}，MA60：{stats["ma60"]:.2f}
- 近5日均成交额：{stats["avg_amount_5d"] / AMOUNT_UNIT_TO_YI:.1f} 亿，市值：{stats["latest_total_mv"] / MV_UNIT_TO_YI:.0f} 亿
- 财务：{fin_text}

## 市场环境
{market_text}

## 用户资金
总资金：{total_capital:.0f} 元

## 输出要求
生成 JSON 数组，包含三个对象，分别代表"激进"、"稳健"、"保守"方案。
每个对象必须包含以下字段：
- "tier_label": "aggressive" 或 "balanced" 或 "conservative"
- "direction": "buy" 或 "sell"
- "target_price": 数字（目标入场价）
- "stop_loss_price": 数字（止损价）
- "take_profit": 数组，每项有 "price"(数字), "ratio"(数字,所有ratio之和=1.0), "note"(字符串)
- "position_ratio": 数字（占总资金比例，0到0.4之间）
- "reasoning": 字符串（入场理由，100字以内）
- "risk_comment": 字符串（风险评估，50字以内）

仅输出 JSON 数组，不要输出其他任何内容。"""

        response = _safe_llm_call(prompt, max_tokens=2000, system_prompt=_PLAN_SYSTEM_PROMPT)
        if response.startswith("> ⚠️ 该部分分析生成失败："):
            return build_error(response.removeprefix("> ⚠️ 该部分分析生成失败：").strip(), "upstream")

        text = _extract_first_json_payload(response.strip())
        plans = json.loads(text)
        if not isinstance(plans, list) or len(plans) != 3:
            return build_manual_fallback(
                ts_code=ts_code,
                stock_name=stock.name,
                message="LLM 返回格式异常：预期 3 套方案，请手动创建",
                raw_response=response,
            )

        normalized_plans: list[dict] = []
        for index, plan in enumerate(plans, start=1):
            if not isinstance(plan, dict):
                return build_manual_fallback(
                    ts_code=ts_code,
                    stock_name=stock.name,
                    message=f"第{index}套方案格式错误，请手动创建",
                    raw_response=response,
                )

            candidate = {**plan, "ts_code": ts_code, "stock_name": stock.name}
            normalized, err = validate_plan_payload(candidate, require_identity=True, require_source=False)
            if err:
                return build_manual_fallback(
                    ts_code=ts_code,
                    stock_name=stock.name,
                    message=f"LLM 方案校验失败：{err}，请手动创建",
                    raw_response=response,
                )
            if normalized is None:
                return build_manual_fallback(
                    ts_code=ts_code,
                    stock_name=stock.name,
                    message=f"第{index}套方案内部校验异常，请手动创建",
                    raw_response=response,
                )

            normalized_plans.append(
                {
                    "ts_code": normalized["ts_code"],
                    "stock_name": normalized["stock_name"],
                    "tier_label": normalized["tier_label"],
                    "direction": normalized["direction"],
                    "target_price": normalized["target_price"],
                    "stop_loss_price": normalized["stop_loss_price"],
                    "take_profit": normalized["take_profit"],
                    "position_ratio": normalized["position_ratio"],
                    "reasoning": normalized["reasoning"],
                    "risk_comment": normalized["risk_comment"] or "",
                }
            )

        return {"status": "ok", "plans": normalized_plans}

    except json.JSONDecodeError:
        return build_manual_fallback(
            ts_code=ts_code,
            stock_name=stock.name,
            message="LLM 返回的内容无法解析为 JSON，请手动创建",
            raw_response=response,
        )
    except ValueError as exc:
        return build_error(str(exc), "validation")
    except Exception as exc:
        return build_error(f"方案生成失败：{exc}", "upstream")
