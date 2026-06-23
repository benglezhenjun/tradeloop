"""交易计划领域契约：校验、归一化、序列化。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.models.plan import TradingPlan

MAX_POSITION_RATIO = 0.4
VALID_DIRECTIONS = ("buy", "sell")
VALID_STATUSES = ("pending", "executed", "abandoned")
VALID_SOURCES = ("llm_generated", "manual")
VALID_TIER_LABELS = ("aggressive", "balanced", "conservative")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def build_manual_fallback(
    *,
    ts_code: str,
    stock_name: str,
    message: str,
    raw_response: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "manual_fallback",
        "message": message,
        "prefill": {
            "ts_code": ts_code,
            "stock_name": stock_name,
        },
    }
    if raw_response:
        result["raw_response"] = raw_response
    return result


def _normalize_string(value: Any, field_name: str) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


def _normalize_take_profit(take_profit: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if isinstance(take_profit, str):
        try:
            take_profit = json.loads(take_profit)
        except json.JSONDecodeError:
            return None, "take_profit JSON 格式错误"

    if not isinstance(take_profit, list) or len(take_profit) == 0:
        return None, "止盈档位不能为空"

    normalized: list[dict[str, Any]] = []
    total_ratio = 0.0

    for idx, tier in enumerate(take_profit, start=1):
        if not isinstance(tier, dict):
            return None, f"第{idx}档格式错误"

        price = tier.get("price")
        ratio = tier.get("ratio")
        note = tier.get("note")

        if not isinstance(price, (int, float)) or price <= 0:
            return None, f"第{idx}档 price 必须为正数"
        if not isinstance(ratio, (int, float)) or ratio <= 0:
            return None, f"第{idx}档 ratio 必须为正数"
        if note is not None and not isinstance(note, str):
            return None, f"第{idx}档 note 必须为字符串"

        normalized.append(
            {
                "price": float(price),
                "ratio": float(ratio),
                "note": note or "",
            }
        )
        total_ratio += float(ratio)

    if abs(total_ratio - 1.0) > 0.01:
        return None, f"所有止盈档位 ratio 之和应为 1.0，当前为 {total_ratio:.2f}"

    return normalized, None


def validate_plan_payload(
    data: dict[str, Any],
    *,
    require_identity: bool,
    require_source: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    normalized: dict[str, Any] = {}

    if require_identity:
        ts_code = _normalize_string(data.get("ts_code"), "ts_code")
        if ts_code is None:
            return None, "ts_code 不能为空"
        stock_name = _normalize_string(data.get("stock_name"), "stock_name")
        if stock_name is None:
            return None, "stock_name 不能为空"
        normalized["ts_code"] = ts_code
        normalized["stock_name"] = stock_name

    direction = data.get("direction")
    if direction not in VALID_DIRECTIONS:
        return None, f"direction 必须为 {VALID_DIRECTIONS}"
    normalized["direction"] = direction

    target_price = data.get("target_price")
    if not isinstance(target_price, (int, float)) or target_price <= 0:
        return None, "target_price 必须为正数"
    normalized["target_price"] = float(target_price)

    stop_loss_price = data.get("stop_loss_price")
    if not isinstance(stop_loss_price, (int, float)) or stop_loss_price <= 0:
        return None, "stop_loss_price 必须为正数"
    normalized["stop_loss_price"] = float(stop_loss_price)

    position_ratio = data.get("position_ratio")
    if not isinstance(position_ratio, (int, float)) or position_ratio <= 0 or position_ratio > MAX_POSITION_RATIO:
        return None, f"position_ratio 必须在 0-{MAX_POSITION_RATIO} 之间"
    normalized["position_ratio"] = float(position_ratio)

    take_profit, tp_error = _normalize_take_profit(data.get("take_profit"))
    if tp_error:
        return None, tp_error
    normalized["take_profit"] = take_profit

    reasoning = data.get("reasoning", "")
    if not isinstance(reasoning, str):
        return None, "reasoning 必须为字符串"
    normalized["reasoning"] = reasoning.strip()

    risk_comment = data.get("risk_comment")
    if risk_comment is not None and not isinstance(risk_comment, str):
        return None, "risk_comment 必须为字符串"
    normalized["risk_comment"] = risk_comment.strip() if isinstance(risk_comment, str) else None

    tier_label = data.get("tier_label")
    if tier_label is not None and tier_label not in VALID_TIER_LABELS:
        return None, f"tier_label 必须为 {VALID_TIER_LABELS}"
    normalized["tier_label"] = tier_label

    expiry_date = data.get("expiry_date")
    if expiry_date not in (None, ""):
        if not isinstance(expiry_date, str):
            return None, "expiry_date 必须为 YYYY-MM-DD 字符串"
        try:
            datetime.strptime(expiry_date, "%Y-%m-%d")
        except ValueError:
            return None, "expiry_date 必须为 YYYY-MM-DD 格式"
        normalized["expiry_date"] = expiry_date
    else:
        normalized["expiry_date"] = None

    if require_source:
        source = data.get("source", "manual")
        if source not in VALID_SOURCES:
            return None, f"source 必须为 {VALID_SOURCES}"
        normalized["source"] = source

        alternatives = data.get("alternatives")
        if alternatives is not None and not isinstance(alternatives, list):
            return None, "alternatives 必须为数组"
        normalized["alternatives"] = alternatives

    return normalized, None


def serialize_take_profit(take_profit: list[dict[str, Any]]) -> str:
    return json.dumps(take_profit, ensure_ascii=False)


def serialize_alternatives(alternatives: list[dict[str, Any]] | None) -> str | None:
    if alternatives is None:
        return None
    return json.dumps(alternatives, ensure_ascii=False)


def deserialize_json_field(raw: Any, *, fallback: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def format_plan(plan: TradingPlan, include_alternatives: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": plan.id,
        "ts_code": plan.ts_code,
        "stock_name": plan.stock_name,
        "direction": plan.direction,
        "target_price": plan.target_price,
        "stop_loss_price": plan.stop_loss_price,
        "take_profit": deserialize_json_field(plan.take_profit, fallback=[]),
        "position_ratio": plan.position_ratio,
        "reasoning": plan.reasoning,
        "risk_comment": plan.risk_comment,
        "tier_label": plan.tier_label,
        "source": plan.source,
        "status": plan.status,
        "expiry_date": plan.expiry_date,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
    if include_alternatives:
        result["alternatives"] = deserialize_json_field(plan.alternatives, fallback=[])
    return result
