"""持仓服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models.quote import DailyQuote
from app.models.trade import Position, TradeRecord
from app.services.plan_contract import now_iso
from app.services.trade_contract import (
    VALID_POSITION_STATUSES,
    format_position,
    format_trade,
    round_money,
)


def _get_latest_quote(db: Session, ts_code: str) -> DailyQuote | None:
    return (
        db.query(DailyQuote)
        .filter(DailyQuote.ts_code == ts_code)
        .order_by(DailyQuote.trade_date.desc())
        .first()
    )


def _serialize_position_with_quote(db: Session, position: Position) -> dict[str, Any]:
    quote = _get_latest_quote(db, position.ts_code)
    if quote is None:
        return format_position(position)
    return format_position(
        position,
        current_price=quote.close,
        quote_trade_date=quote.trade_date,
    )


def _rebuild_position_state(trades: list[TradeRecord]) -> tuple[dict[str, Any] | None, str | None]:
    if not trades:
        return None, None

    state = {
        "ts_code": trades[0].ts_code,
        "stock_name": trades[0].stock_name,
        "total_quantity": 0,
        "avg_cost": 0.0,
        "total_cost": 0.0,
        "realized_pnl": 0.0,
        "status": "closed",
        "first_buy_date": None,
        "last_trade_date": trades[0].trade_date,
    }

    for trade in trades:
        state["stock_name"] = trade.stock_name
        state["last_trade_date"] = trade.trade_date
        if trade.direction == "buy":
            if state["first_buy_date"] is None:
                state["first_buy_date"] = trade.trade_date
            state["total_cost"] += trade.amount + trade.fee
            state["total_quantity"] += trade.quantity
            state["avg_cost"] = round_money(state["total_cost"] / state["total_quantity"])
            state["status"] = "holding"
            continue

        if state["total_quantity"] < trade.quantity:
            return None, "卖出数量超过当前持仓，无法重算"

        # 精确比例摊销成本，避免用已四舍五入的均价回减导致剩余成本累积漂移
        cost_removed = state["total_cost"] * trade.quantity / state["total_quantity"]
        state["realized_pnl"] += trade.price * trade.quantity - cost_removed - trade.fee
        state["total_cost"] -= cost_removed
        state["total_quantity"] -= trade.quantity

        if state["total_quantity"] == 0:
            state["avg_cost"] = 0.0
            state["total_cost"] = 0.0
            state["status"] = "closed"
        else:
            state["avg_cost"] = round_money(state["total_cost"] / state["total_quantity"])
            state["status"] = "holding"

    if state["first_buy_date"] is None:
        return None, "缺少买入记录，无法生成持仓"

    state["total_cost"] = round_money(state["total_cost"])
    state["realized_pnl"] = round_money(state["realized_pnl"])
    return state, None


def recalculate_position(db: Session, ts_code: str, *, commit: bool = True) -> Position | None | dict[str, Any]:
    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.ts_code == ts_code)
        .order_by(TradeRecord.trade_date.asc(), TradeRecord.trade_time.asc(), TradeRecord.id.asc())
        .all()
    )
    position = db.query(Position).filter(Position.ts_code == ts_code).first()

    if not trades:
        if position is not None:
            db.delete(position)
            if commit:
                db.commit()
        return None

    state, error = _rebuild_position_state(trades)
    if error:
        return build_error(error)
    if state is None:
        return build_error("重算持仓失败")

    if position is None:
        position = Position(ts_code=ts_code, updated_at=now_iso(), first_buy_date=state["first_buy_date"])
        db.add(position)

    position.stock_name = state["stock_name"]
    position.total_quantity = state["total_quantity"]
    position.avg_cost = state["avg_cost"]
    position.total_cost = state["total_cost"]
    position.realized_pnl = state["realized_pnl"]
    position.status = state["status"]
    position.first_buy_date = state["first_buy_date"]
    position.last_trade_date = state["last_trade_date"]
    position.updated_at = now_iso()

    if commit:
        db.commit()
        db.refresh(position)
    return position


def list_positions(db: Session, status: str | None = None) -> dict[str, list[dict[str, Any]]] | dict[str, Any]:
    if status is not None and status not in VALID_POSITION_STATUSES:
        return build_error(f"status 必须是 {VALID_POSITION_STATUSES}")

    query = db.query(Position).order_by(Position.updated_at.desc(), Position.ts_code.asc())
    if status:
        query = query.filter(Position.status == status)
    positions = [_serialize_position_with_quote(db, position) for position in query.all()]
    return {"positions": positions}


def get_position_detail(db: Session, ts_code: str) -> dict[str, Any] | None:
    position = db.query(Position).filter(Position.ts_code == ts_code).first()
    if position is None:
        return None

    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.ts_code == ts_code)
        .order_by(TradeRecord.trade_date.asc(), TradeRecord.trade_time.asc(), TradeRecord.id.asc())
        .all()
    )
    return {
        "position": _serialize_position_with_quote(db, position),
        "trades": [format_trade(trade) for trade in trades],
    }


def get_position_summary(db: Session) -> dict[str, Any]:
    holding_positions = db.query(Position).filter(Position.status == "holding").all()
    total_market_value = 0.0
    total_cost = 0.0
    total_unrealized_pnl = 0.0

    for position in holding_positions:
        quote = _get_latest_quote(db, position.ts_code)
        if quote is None:
            continue
        market_value = quote.close * position.total_quantity
        total_market_value += market_value
        total_cost += position.total_cost
        total_unrealized_pnl += market_value - position.total_cost

    all_positions = db.query(Position).all()

    return {
        "position_count": len(holding_positions),
        "holding_count": len(holding_positions),
        "closed_count": db.query(Position).filter(Position.status == "closed").count(),
        "total_market_value": round_money(total_market_value),
        "total_cost": round_money(total_cost),
        "total_unrealized_pnl": round_money(total_unrealized_pnl),
        "total_realized_pnl": round_money(sum(position.realized_pnl for position in all_positions)),
    }
