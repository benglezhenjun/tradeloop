from __future__ import annotations

import json
from typing import Any

from app.models.review import BehaviorPattern, TradeReview

REVIEW_DIMENSIONS = [
    "entry_timing",
    "exit_timing",
    "stop_loss",
    "take_profit",
    "position_sizing",
    "holding_period",
    "discipline",
    "risk_reward",
]

DIMENSION_LABELS = {
    "entry_timing": "入场时机",
    "exit_timing": "离场时机",
    "stop_loss": "止损纪律",
    "take_profit": "止盈执行",
    "position_sizing": "仓位管理",
    "holding_period": "持仓周期",
    "discipline": "交易纪律",
    "risk_reward": "盈亏比",
}


def _load_json(raw: Any, fallback: Any) -> Any:
    if not isinstance(raw, str):
        return raw if raw is not None else fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def validate_scores(scores: dict[str, Any] | Any) -> tuple[dict[str, int] | None, str | None]:
    if not isinstance(scores, dict):
        return None, "scores 必须是对象"

    normalized: dict[str, int] = {}
    missing = [key for key in REVIEW_DIMENSIONS if key not in scores]
    if missing:
        return None, f"scores 缺少维度: {', '.join(missing)}"

    for key in REVIEW_DIMENSIONS:
        value = scores.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            return None, f"{key} 必须是 1-10 的整数"
        if value < 1 or value > 10:
            return None, f"{key} 必须在 1-10 之间"
        normalized[key] = value

    return normalized, None


def calculate_overall_score(scores: dict[str, int]) -> float:
    return round(sum(scores.values()) / len(REVIEW_DIMENSIONS), 1)


def format_review(review: TradeReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "ts_code": review.ts_code,
        "stock_name": review.stock_name,
        "plan_id": review.plan_id,
        "total_buy_amount": review.total_buy_amount,
        "total_sell_amount": review.total_sell_amount,
        "total_fee": review.total_fee,
        "realized_pnl": review.realized_pnl,
        "trade_count": review.trade_count,
        "first_trade_date": review.first_trade_date,
        "last_trade_date": review.last_trade_date,
        "holding_days": review.holding_days,
        "scores": _load_json(review.scores, {}),
        "overall_score": review.overall_score,
        "analysis": review.analysis,
        "improvement": review.improvement,
        "user_notes": review.user_notes,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def format_pattern(pattern: BehaviorPattern) -> dict[str, Any]:
    return {
        "id": pattern.id,
        "pattern_type": pattern.pattern_type,
        "title": pattern.title,
        "description": pattern.description,
        "dimension": pattern.dimension,
        "evidence_ids": _load_json(pattern.evidence_ids, []),
        "status": pattern.status,
        "created_at": pattern.created_at,
        "updated_at": pattern.updated_at,
    }
