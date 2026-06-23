"""交易记录与持仓领域契约。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.trade import Position, TradeRecord

VALID_TRADE_DIRECTIONS = ("buy", "sell")
VALID_POSITION_STATUSES = ("holding", "closed")


def round_money(value: float | int) -> float:
    return round(float(value), 6)


def is_sh_stock(ts_code: str) -> bool:
    return ts_code.upper().endswith(".SH")


def calculate_trade_fee(
    *,
    amount: float,
    direction: str,
    ts_code: str,
    commission_rate: float,
    stamp_tax_rate: float,
    transfer_fee_rate: float,
) -> float:
    commission = amount * commission_rate
    stamp_tax = amount * stamp_tax_rate if direction == "sell" else 0.0
    transfer_fee = amount * transfer_fee_rate if is_sh_stock(ts_code) else 0.0
    return round_money(commission + stamp_tax + transfer_fee)


def validate_trade_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    ts_code = data.get("ts_code")
    if not isinstance(ts_code, str) or not ts_code.strip():
        return None, "ts_code 不能为空"

    stock_name = data.get("stock_name")
    if not isinstance(stock_name, str) or not stock_name.strip():
        return None, "stock_name 不能为空"

    direction = data.get("direction")
    if direction not in VALID_TRADE_DIRECTIONS:
        return None, f"direction 必须是 {VALID_TRADE_DIRECTIONS}"

    price = data.get("price")
    if not isinstance(price, (int, float)) or float(price) <= 0:
        return None, "price 必须大于 0"

    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity <= 0:
        return None, "quantity 必须大于 0"

    trade_date = data.get("trade_date")
    if not isinstance(trade_date, str):
        return None, "trade_date 必须为 YYYY-MM-DD"
    try:
        datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError:
        return None, "trade_date 必须为 YYYY-MM-DD"

    trade_time = data.get("trade_time")
    if trade_time not in (None, ""):
        if not isinstance(trade_time, str):
            return None, "trade_time 必须为 HH:MM:SS"
        try:
            datetime.strptime(trade_time, "%H:%M:%S")
        except ValueError:
            return None, "trade_time 必须为 HH:MM:SS"
    else:
        trade_time = None

    fee = data.get("fee")
    if fee is not None:
        if not isinstance(fee, (int, float)) or float(fee) < 0:
            return None, "fee 不能小于 0"

    note = data.get("note")
    if note is not None and not isinstance(note, str):
        return None, "note 必须为字符串"

    plan_id = data.get("plan_id")
    if plan_id is not None:
        if not isinstance(plan_id, int) or plan_id <= 0:
            return None, "plan_id 必须为正整数"

    return (
        {
            "ts_code": ts_code.strip(),
            "stock_name": stock_name.strip(),
            "direction": direction,
            "price": float(price),
            "quantity": quantity,
            "trade_date": trade_date,
            "trade_time": trade_time,
            "fee": None if fee is None else round_money(fee),
            "note": note.strip() if isinstance(note, str) and note.strip() else None,
            "plan_id": plan_id,
        },
        None,
    )


def format_trade(trade: TradeRecord) -> dict[str, Any]:
    return {
        "id": trade.id,
        "ts_code": trade.ts_code,
        "stock_name": trade.stock_name,
        "plan_id": trade.plan_id,
        "direction": trade.direction,
        "price": trade.price,
        "quantity": trade.quantity,
        "amount": trade.amount,
        "fee": trade.fee,
        "trade_date": trade.trade_date,
        "trade_time": trade.trade_time,
        "note": trade.note,
        "created_at": trade.created_at,
    }


def format_position(
    position: Position,
    *,
    current_price: float | None = None,
    quote_trade_date: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": position.id,
        "ts_code": position.ts_code,
        "stock_name": position.stock_name,
        "total_quantity": position.total_quantity,
        "avg_cost": position.avg_cost,
        "total_cost": position.total_cost,
        "realized_pnl": position.realized_pnl,
        "status": position.status,
        "first_buy_date": position.first_buy_date,
        "last_trade_date": position.last_trade_date,
        "updated_at": position.updated_at,
    }
    if current_price is not None:
        market_value = round_money(current_price * position.total_quantity)
        unrealized_pnl = round_money(market_value - position.total_cost)
        result.update(
            {
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "quote_trade_date": quote_trade_date,
            }
        )
    return result
