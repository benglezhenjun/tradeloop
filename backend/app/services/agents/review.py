from __future__ import annotations

import json
from statistics import pstdev

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models.review import TradeReview
from app.services import review as review_service
from app.services.agents.base import _extract_first_json_payload, _safe_llm_call
from app.services.review_contract import REVIEW_DIMENSIONS, calculate_overall_score, validate_scores

_REVIEW_SYSTEM_PROMPT = (
    "你是一个 A 股交易复盘助手。根据提供的交易数据进行专业复盘分析。"
    "严格按要求的 JSON 格式输出。"
)

_REVIEW_OUTPUT_SCHEMA = """{
  "scores": {
    "entry_timing": 1,
    "exit_timing": 1,
    "stop_loss": 1,
    "take_profit": 1,
    "position_sizing": 1,
    "holding_period": 1,
    "discipline": 1,
    "risk_reward": 1
  },
  "analysis": "字符串，概括本次交易复盘结论",
  "improvement": "字符串，给出后续改进建议"
}"""

_PATTERN_OUTPUT_SCHEMA = """[
  {
    "pattern_type": "strength 或 weakness",
    "title": "模式标题",
    "description": "模式说明",
    "dimension": "可选，对应维度代码",
    "evidence_ids": [1, 2]
  }
]"""


def _format_plan_text(plan: dict | None) -> str:
    if plan is None:
        return "无关联交易计划，为手动交易"

    take_profit = plan.get("take_profit") or []
    take_profit_text = "；".join(
        f"{item.get('price')}元 / 比例{item.get('ratio')}"
        for item in take_profit
        if isinstance(item, dict)
    )
    return (
        f"方向：{plan.get('direction')}；目标价：{plan.get('target_price')}；"
        f"止损价：{plan.get('stop_loss_price')}；止盈梯度：{take_profit_text or '无'}；"
        f"仓位比例：{plan.get('position_ratio')}"
    )


def _format_trades_timeline(trades: list[dict]) -> str:
    return "\n".join(
        (
            f"- {trade['trade_date']} {trade['direction']} "
            f"价格={trade['price']} 数量={trade['quantity']} 金额={trade['amount']} 费用={trade['fee']}"
        )
        for trade in trades
    )


def _format_quotes_summary(quotes: list[dict]) -> str:
    if not quotes:
        return "无行情数据"
    return "\n".join(
        (
            f"- {quote['trade_date']} 开={quote['open']} 收={quote['close']} 高={quote['high']} "
            f"低={quote['low']} 成交额={quote['amount']}"
        )
        for quote in quotes
    )


def _load_json_payload(text: str) -> dict | list | None:
    try:
        return json.loads(_extract_first_json_payload(text))
    except json.JSONDecodeError:
        return None


def _repair_review_payload(raw_output: str) -> dict | None:
    repair_prompt = f"""你上一次返回的内容不符合要求。

请基于原有分析内容，重新输出一个严格符合以下 schema 的 JSON 对象：
{_REVIEW_OUTPUT_SCHEMA}

要求：
1. 只能输出一个 JSON 对象，不要 Markdown、不要代码块。
2. scores 的 8 个字段必须全部提供，且分数必须是 1-10 的整数。
3. analysis 和 improvement 必须是字符串。

待修复内容如下：
{raw_output}
"""
    repaired = _safe_llm_call(repair_prompt, max_tokens=1200, system_prompt=_REVIEW_SYSTEM_PROMPT)
    payload = _load_json_payload(repaired)
    return payload if isinstance(payload, dict) else None


def _repair_pattern_payload(raw_output: str) -> list[dict] | None:
    repair_prompt = f"""你上一次返回的内容不符合要求。

请基于原有分析内容，重新输出一个严格符合以下 schema 的 JSON 数组：
{_PATTERN_OUTPUT_SCHEMA}

要求：
1. 只能输出一个 JSON 数组，不要 Markdown、不要代码块。
2. 每一项都必须包含 pattern_type、title、description。
3. pattern_type 只能是 strength 或 weakness。
4. evidence_ids 必须是数组。

待修复内容如下：
{raw_output}
"""
    repaired = _safe_llm_call(repair_prompt, max_tokens=1200, system_prompt=_REVIEW_SYSTEM_PROMPT)
    payload = _load_json_payload(repaired)
    if not isinstance(payload, list):
        return None
    return payload


def run_review_agent(db: Session, ts_code: str) -> dict:
    context = review_service.build_review_context(db, ts_code)
    if context is None:
        return build_error("该股票无交易记录")

    prompt = f"""你将收到一笔 A 股交易的复盘上下文，请输出 JSON。

## 股票信息
- 股票：{context['stock_name']}（{context['ts_code']}）
- 总资金：{context['total_capital']} 元

## 交易计划
{_format_plan_text(context['plan'])}

## 交易记录时间线
{_format_trades_timeline(context['trades'])}

## 持仓期间行情走势
{_format_quotes_summary(context['quotes'])}
"""

    response = _safe_llm_call(prompt, max_tokens=2000, system_prompt=_REVIEW_SYSTEM_PROMPT)
    payload = _load_json_payload(response)
    if not isinstance(payload, dict):
        return build_error("LLM 返回内容不是合法 JSON", "upstream")

    scores, error = validate_scores(payload.get("scores"))
    if error:
        repaired_payload = _repair_review_payload(response)
        if repaired_payload is not None:
            payload = repaired_payload
            scores, error = validate_scores(payload.get("scores"))
    if error:
        return build_error(error)
    if scores is None:
        return build_error("scores 校验失败")

    analysis = payload.get("analysis")
    improvement = payload.get("improvement")
    if not isinstance(analysis, str) or not analysis.strip():
        return build_error("analysis 不能为空")
    if improvement is not None and not isinstance(improvement, str):
        return build_error("improvement 必须是字符串")

    return {
        "status": "ok",
        "scores": scores,
        "overall_score": calculate_overall_score(scores),
        "analysis": analysis,
        "improvement": improvement,
    }


def run_pattern_agent(db: Session) -> dict:
    reviews = db.query(TradeReview).order_by(TradeReview.created_at.asc(), TradeReview.id.asc()).all()
    if len(reviews) < 3:
        return build_error("复盘数据不足 3 条，无法分析行为模式")

    parsed_reviews = [review_service.get_review_detail(db, review.id) for review in reviews]
    valid_reviews = [review for review in parsed_reviews if review is not None]
    avg_scores = {
        dimension: round(sum(review["scores"][dimension] for review in valid_reviews) / len(valid_reviews), 1)
        for dimension in REVIEW_DIMENSIONS
    }
    std_scores = {
        dimension: round(pstdev([review["scores"][dimension] for review in valid_reviews]), 3)
        for dimension in REVIEW_DIMENSIONS
    }
    win_count = sum(1 for review in valid_reviews if review["realized_pnl"] > 0)
    loss_count = sum(1 for review in valid_reviews if review["realized_pnl"] < 0)
    reviews_summary = "\n".join(
        f"- review#{review['id']} {review['ts_code']} scores={json.dumps(review['scores'], ensure_ascii=False)}"
        for review in valid_reviews
    )

    prompt = f"""你将收到多次交易复盘汇总，请输出 JSON 数组。

## 复盘数据汇总
- 总复盘数：{len(valid_reviews)}
- 各维度平均分：{json.dumps(avg_scores, ensure_ascii=False)}
- 各维度标准差：{json.dumps(std_scores, ensure_ascii=False)}
- 盈利笔数：{win_count}，亏损笔数：{loss_count}

## 各复盘详情
{reviews_summary}
"""

    response = _safe_llm_call(prompt, max_tokens=1500, system_prompt=_REVIEW_SYSTEM_PROMPT)
    payload = _load_json_payload(response)
    if not isinstance(payload, list):
        repaired_payload = _repair_pattern_payload(response)
        if repaired_payload is not None:
            payload = repaired_payload
    if not isinstance(payload, list):
        return build_error("LLM 返回内容不是合法 JSON", "upstream")

    patterns: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            return build_error("行为模式项必须是对象", "upstream")
        if not all(key in item for key in ("pattern_type", "title", "description")):
            repaired_payload = _repair_pattern_payload(json.dumps(payload, ensure_ascii=False))
            if repaired_payload is None:
                return build_error("行为模式缺少必要字段", "upstream")
            payload = repaired_payload
            patterns = []
            break
        patterns.append(
            {
                "pattern_type": item["pattern_type"],
                "title": item["title"],
                "description": item["description"],
                "dimension": item.get("dimension"),
                "evidence_ids": item.get("evidence_ids", []),
            }
        )

    if not patterns:
        for item in payload:
            if not isinstance(item, dict):
                return build_error("行为模式项必须是对象", "upstream")
            if not all(key in item for key in ("pattern_type", "title", "description")):
                return build_error("行为模式缺少必要字段", "upstream")
            patterns.append(
                {
                    "pattern_type": item["pattern_type"],
                    "title": item["title"],
                    "description": item["description"],
                    "dimension": item.get("dimension"),
                    "evidence_ids": item.get("evidence_ids", []),
                }
            )

    return {"status": "ok", "patterns": patterns}
