"""交易记录服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models.plan import TradingPlan
from app.models.trade import TradeRecord
from app.services import position as position_service
from app.services import user_config
from app.services.plan_contract import now_iso
from app.services.trade_contract import (
    calculate_trade_fee,
    format_position,
    format_trade,
    validate_trade_payload,
)


def _load_fee_rates(db: Session) -> tuple[float, float, float]:
    commission_rate = float(user_config.get_config(db, "commission_rate") or "0")
    stamp_tax_rate = float(user_config.get_config(db, "stamp_tax_rate") or "0")
    transfer_fee_rate = float(user_config.get_config(db, "transfer_fee_rate") or "0")
    return commission_rate, stamp_tax_rate, transfer_fee_rate


def _build_trade_record(db: Session, normalized: dict[str, Any]) -> tuple[TradeRecord | None, str | None]:
    amount = normalized["price"] * normalized["quantity"]
    fee = normalized["fee"]
    if fee is None:
        commission_rate, stamp_tax_rate, transfer_fee_rate = _load_fee_rates(db)
        fee = calculate_trade_fee(
            amount=amount,
            direction=normalized["direction"],
            ts_code=normalized["ts_code"],
            commission_rate=commission_rate,
            stamp_tax_rate=stamp_tax_rate,
            transfer_fee_rate=transfer_fee_rate,
        )

    trade = TradeRecord(
        ts_code=normalized["ts_code"],
        stock_name=normalized["stock_name"],
        plan_id=normalized["plan_id"],
        direction=normalized["direction"],
        price=normalized["price"],
        quantity=normalized["quantity"],
        amount=amount,
        fee=fee,
        trade_date=normalized["trade_date"],
        trade_time=normalized["trade_time"],
        note=normalized["note"],
        created_at=now_iso(),
    )
    return trade, None


def create_trade(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    normalized, error = validate_trade_payload(data)
    if error:
        return build_error(error)
    if normalized is None:
        return build_error("交易参数校验失败")

    if normalized["direction"] == "sell":
        current_position = db.query(position_service.Position).filter(
            position_service.Position.ts_code == normalized["ts_code"]
        ).first()
        if current_position is None or current_position.total_quantity < normalized["quantity"]:
            return build_error("卖出数量超过当前持仓")

    if normalized["plan_id"] is not None:
        linked_plan = db.get(TradingPlan, normalized["plan_id"])
        if linked_plan is None:
            return build_error("关联计划不存在", "not_found")
    else:
        linked_plan = None

    trade, _ = _build_trade_record(db, normalized)
    if trade is None:
        return build_error("创建交易记录失败")

    db.add(trade)
    db.flush()

    if linked_plan is not None and trade.direction == "buy" and linked_plan.status == "pending":
        linked_plan.status = "executed"
        linked_plan.updated_at = now_iso()

    position = position_service.recalculate_position(db, trade.ts_code, commit=False)
    if isinstance(position, dict) and "error" in position:
        db.rollback()
        return position

    db.commit()
    db.refresh(trade)
    if trade.direction == "buy" and linked_plan is not None:
        db.refresh(linked_plan)
    if position is not None:
        db.refresh(position)

    return {
        "trade": format_trade(trade),
        "position": None if position is None else format_position(position),
    }


def list_trades(
    db: Session,
    *,
    ts_code: str | None = None,
    direction: str | None = None,
) -> dict[str, list[dict[str, Any]]] | dict[str, Any]:
    if direction is not None and direction not in ("buy", "sell"):
        return build_error("direction 必须是 ('buy', 'sell')")

    query = db.query(TradeRecord).order_by(TradeRecord.trade_date.desc(), TradeRecord.id.desc())
    if ts_code:
        query = query.filter(TradeRecord.ts_code == ts_code)
    if direction:
        query = query.filter(TradeRecord.direction == direction)
    return {"trades": [format_trade(trade) for trade in query.all()]}


def get_trade_detail(db: Session, trade_id: int) -> dict[str, Any] | None:
    trade = db.get(TradeRecord, trade_id)
    if trade is None:
        return None
    return {"trade": format_trade(trade)}


def delete_trade(db: Session, trade_id: int) -> dict[str, Any]:
    trade = db.get(TradeRecord, trade_id)
    if trade is None:
        return build_error("交易记录不存在", "not_found")

    ts_code = trade.ts_code
    db.delete(trade)
    db.flush()

    position = position_service.recalculate_position(db, ts_code, commit=False)
    if isinstance(position, dict) and "error" in position:
        db.rollback()
        return position

    db.commit()
    return {"message": "已删除"}
