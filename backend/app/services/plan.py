"""交易计划服务 (V5)"""

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models.plan import TradingPlan
from app.services.plan_contract import (
    VALID_STATUSES,
    format_plan,
    now_iso,
    serialize_alternatives,
    serialize_take_profit,
    validate_plan_payload,
)

# 状态只能前进：pending → executed 或 pending → abandoned
ALLOWED_TRANSITIONS = {
    ("pending", "executed"),
    ("pending", "abandoned"),
}


def create_plan(db: Session, data: dict) -> dict:
    """创建交易计划"""
    normalized, err = validate_plan_payload(data, require_identity=True, require_source=True)
    if err:
        return build_error(err)
    if normalized is None:
        return build_error("内部校验错误")

    now = now_iso()
    plan = TradingPlan(
        ts_code=normalized["ts_code"],
        stock_name=normalized["stock_name"],
        direction=normalized["direction"],
        target_price=normalized["target_price"],
        stop_loss_price=normalized["stop_loss_price"],
        take_profit=serialize_take_profit(normalized["take_profit"]),
        position_ratio=normalized["position_ratio"],
        reasoning=normalized["reasoning"],
        risk_comment=normalized["risk_comment"],
        tier_label=normalized["tier_label"],
        source=normalized["source"],
        status="pending",
        expiry_date=normalized["expiry_date"],
        alternatives=serialize_alternatives(normalized["alternatives"]),
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return format_plan(plan)


def get_plans(db: Session, status: str | None = None, ts_code: str | None = None) -> list[dict]:
    """获取计划列表，支持按状态和股票筛选"""
    query = db.query(TradingPlan)
    if status:
        query = query.filter(TradingPlan.status == status)
    if ts_code:
        query = query.filter(TradingPlan.ts_code == ts_code)
    query = query.order_by(TradingPlan.created_at.desc())
    return [format_plan(p) for p in query.all()]


def get_plan_detail(db: Session, plan_id: int) -> dict | None:
    """获取计划详情"""
    plan = db.get(TradingPlan, plan_id)
    if not plan:
        return None
    return format_plan(plan, include_alternatives=True)


def update_plan(db: Session, plan_id: int, updates: dict) -> dict:
    """编辑计划（仅 pending 状态可编辑）"""
    plan = db.get(TradingPlan, plan_id)
    if not plan:
        return build_error("计划不存在", "not_found")
    if plan.status != "pending":
        return build_error("只有待执行状态的计划可以编辑", "validation")

    # 如果有需要校验的字段，先合并再校验
    check_data = {
        "ts_code": plan.ts_code,
        "stock_name": plan.stock_name,
        "direction": updates.get("direction", plan.direction),
        "target_price": updates.get("target_price", plan.target_price),
        "stop_loss_price": updates.get("stop_loss_price", plan.stop_loss_price),
        "position_ratio": updates.get("position_ratio", plan.position_ratio),
        "take_profit": updates.get("take_profit", plan.take_profit),
        "reasoning": updates.get("reasoning", plan.reasoning),
        "risk_comment": updates.get("risk_comment", plan.risk_comment),
        "tier_label": updates.get("tier_label", plan.tier_label),
        "expiry_date": updates.get("expiry_date", plan.expiry_date),
        "source": plan.source,
        "alternatives": None,
    }
    normalized, err = validate_plan_payload(check_data, require_identity=True, require_source=True)
    if err:
        return build_error(err)
    if normalized is None:
        return build_error("内部校验错误")

    plan.direction = normalized["direction"]
    plan.target_price = normalized["target_price"]
    plan.stop_loss_price = normalized["stop_loss_price"]
    plan.position_ratio = normalized["position_ratio"]
    plan.take_profit = serialize_take_profit(normalized["take_profit"])
    plan.reasoning = normalized["reasoning"]
    plan.risk_comment = normalized["risk_comment"]
    plan.tier_label = normalized["tier_label"]
    plan.expiry_date = normalized["expiry_date"]
    plan.updated_at = now_iso()
    db.commit()
    db.refresh(plan)
    return format_plan(plan)


def update_plan_status(db: Session, plan_id: int, new_status: str) -> dict:
    """变更计划状态"""
    plan = db.get(TradingPlan, plan_id)
    if not plan:
        return build_error("计划不存在", "not_found")
    if new_status not in VALID_STATUSES:
        return build_error(f"status 必须为 {VALID_STATUSES}")
    if (plan.status, new_status) not in ALLOWED_TRANSITIONS:
        return build_error(f"不允许从 {plan.status} 变更为 {new_status}")

    plan.status = new_status
    plan.updated_at = now_iso()
    db.commit()
    db.refresh(plan)
    return format_plan(plan)


def delete_plan(db: Session, plan_id: int) -> bool:
    """删除计划"""
    plan = db.get(TradingPlan, plan_id)
    if not plan:
        return False
    db.delete(plan)
    db.commit()
    return True
