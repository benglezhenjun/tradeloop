from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models import DailyQuote, Position, TradeRecord, TradeReview, TradingPlan
from app.services import user_config
from app.services.plan import format_plan
from app.services.plan_contract import now_iso
from app.services.review_contract import (
    REVIEW_DIMENSIONS,
    calculate_overall_score,
    format_review,
    validate_scores,
)
from app.services.trade_contract import format_position, format_trade, round_money


def _parse_trade_date(trade_date: str) -> datetime:
    return datetime.strptime(trade_date, "%Y-%m-%d")


def _serialize_quote(quote: DailyQuote) -> dict[str, Any]:
    return {
        "trade_date": quote.trade_date,
        "open": quote.open,
        "high": quote.high,
        "low": quote.low,
        "close": quote.close,
        "vol": quote.vol,
        "amount": quote.amount,
        "pct_chg": quote.pct_chg,
        "total_mv": quote.total_mv,
        "turnover_rate": quote.turnover_rate,
    }


def _pick_related_plan(db: Session, ts_code: str, trades: list[TradeRecord]) -> TradingPlan | None:
    linked_plan_ids = [trade.plan_id for trade in trades if trade.plan_id is not None]
    if linked_plan_ids:
        plan_id = Counter(linked_plan_ids).most_common(1)[0][0]
        plan = db.get(TradingPlan, plan_id)
        if plan is not None:
            return plan

    return (
        db.query(TradingPlan)
        .filter(TradingPlan.ts_code == ts_code, TradingPlan.status == "executed")
        .order_by(TradingPlan.updated_at.desc(), TradingPlan.created_at.desc())
        .first()
    )


def build_review_context(db: Session, ts_code: str) -> dict[str, Any] | None:
    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.ts_code == ts_code)
        .order_by(TradeRecord.trade_date.asc(), TradeRecord.id.asc())
        .all()
    )
    if not trades:
        return None

    first_trade_date = trades[0].trade_date
    last_trade_date = trades[-1].trade_date
    start_date = (_parse_trade_date(first_trade_date) - timedelta(days=10)).strftime("%Y%m%d")
    end_date = (_parse_trade_date(last_trade_date) + timedelta(days=20)).strftime("%Y%m%d")

    position = db.query(Position).filter(Position.ts_code == ts_code).first()
    plan = _pick_related_plan(db, ts_code, trades)
    quotes = (
        db.query(DailyQuote)
        .filter(DailyQuote.ts_code == ts_code, DailyQuote.trade_date >= start_date, DailyQuote.trade_date <= end_date)
        .order_by(DailyQuote.trade_date.asc())
        .all()
    )

    total_buy_amount = round_money(sum(trade.amount for trade in trades if trade.direction == "buy"))
    total_sell_amount = round_money(sum(trade.amount for trade in trades if trade.direction == "sell"))
    total_fee = round_money(sum(trade.fee for trade in trades))
    realized_pnl = round_money(position.realized_pnl if position is not None else total_sell_amount - total_buy_amount - total_fee)
    total_capital = float(user_config.get_config(db, "total_capital") or "0")

    return {
        "ts_code": ts_code,
        "stock_name": trades[-1].stock_name,
        "position": None if position is None else format_position(position),
        "plan": None if plan is None else format_plan(plan, include_alternatives=True),
        "trades": [format_trade(trade) for trade in trades],
        "quotes": [_serialize_quote(quote) for quote in quotes],
        "total_capital": total_capital,
        "total_buy_amount": total_buy_amount,
        "total_sell_amount": total_sell_amount,
        "total_fee": total_fee,
        "realized_pnl": realized_pnl,
        "trade_count": len(trades),
        "first_trade_date": first_trade_date,
        "last_trade_date": last_trade_date,
        "holding_days": (_parse_trade_date(last_trade_date) - _parse_trade_date(first_trade_date)).days,
    }


def create_review(db: Session, ts_code: str, llm_result: dict[str, Any]) -> dict[str, Any]:
    scores, error = validate_scores(llm_result.get("scores"))
    if error:
        return build_error(error)
    if scores is None:
        return build_error("scores 校验失败")

    context = build_review_context(db, ts_code)
    if context is None:
        return build_error("该股票无交易记录", "not_found")

    analysis = llm_result.get("analysis")
    improvement = llm_result.get("improvement")
    if not isinstance(analysis, str) or not analysis.strip():
        return build_error("analysis 不能为空")
    if improvement is not None and not isinstance(improvement, str):
        return build_error("improvement 必须是字符串")

    now = now_iso()
    review = TradeReview(
        ts_code=context["ts_code"],
        stock_name=context["stock_name"],
        plan_id=context["plan"]["id"] if context["plan"] is not None else None,
        total_buy_amount=context["total_buy_amount"],
        total_sell_amount=context["total_sell_amount"],
        total_fee=context["total_fee"],
        realized_pnl=context["realized_pnl"],
        trade_count=context["trade_count"],
        first_trade_date=context["first_trade_date"],
        last_trade_date=context["last_trade_date"],
        holding_days=context["holding_days"],
        scores=json.dumps(scores, ensure_ascii=False),
        overall_score=calculate_overall_score(scores),
        analysis=analysis.strip(),
        improvement=improvement.strip() if isinstance(improvement, str) and improvement.strip() else None,
        user_notes=None,
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return format_review(review)


def list_reviews(db: Session, ts_code: str | None = None) -> dict[str, list[dict[str, Any]]]:
    query = db.query(TradeReview)
    if ts_code:
        query = query.filter(TradeReview.ts_code == ts_code)
    query = query.order_by(TradeReview.created_at.desc(), TradeReview.id.desc())
    return {"reviews": [format_review(review) for review in query.all()]}


def get_review_detail(db: Session, review_id: int) -> dict[str, Any] | None:
    review = db.get(TradeReview, review_id)
    if review is None:
        return None
    return format_review(review)


def update_review_notes(db: Session, review_id: int, notes: str) -> dict[str, Any]:
    review = db.get(TradeReview, review_id)
    if review is None:
        return build_error("复盘记录不存在", "not_found")
    if not isinstance(notes, str):
        return build_error("notes 必须是字符串")

    review.user_notes = notes
    review.updated_at = now_iso()
    db.commit()
    db.refresh(review)
    return format_review(review)


def delete_review(db: Session, review_id: int) -> dict[str, Any]:
    review = db.get(TradeReview, review_id)
    if review is None:
        return build_error("复盘记录不存在", "not_found")

    db.delete(review)
    db.commit()
    return {"message": "已删除"}


def get_review_stats(db: Session) -> dict[str, Any]:
    reviews = db.query(TradeReview).all()
    avg_scores = {dimension: 0.0 for dimension in REVIEW_DIMENSIONS}
    if not reviews:
        return {
            "total_reviews": 0,
            "avg_overall_score": 0.0,
            "avg_scores": avg_scores,
            "best_dimension": "",
            "worst_dimension": "",
            "win_count": 0,
            "loss_count": 0,
            "total_reviewed_pnl": 0.0,
        }

    totals = {dimension: 0 for dimension in REVIEW_DIMENSIONS}
    for review in reviews:
        parsed_scores = format_review(review)["scores"]
        for dimension in REVIEW_DIMENSIONS:
            totals[dimension] += int(parsed_scores.get(dimension, 0))

    avg_scores = {
        dimension: round(totals[dimension] / len(reviews), 1)
        for dimension in REVIEW_DIMENSIONS
    }
    best_dimension = max(REVIEW_DIMENSIONS, key=lambda dimension: avg_scores[dimension])
    worst_dimension = min(REVIEW_DIMENSIONS, key=lambda dimension: avg_scores[dimension])

    return {
        "total_reviews": len(reviews),
        "avg_overall_score": round(sum(review.overall_score for review in reviews) / len(reviews), 1),
        "avg_scores": avg_scores,
        "best_dimension": best_dimension,
        "worst_dimension": worst_dimension,
        "win_count": sum(1 for review in reviews if review.realized_pnl > 0),
        "loss_count": sum(1 for review in reviews if review.realized_pnl < 0),
        "total_reviewed_pnl": round_money(sum(review.realized_pnl for review in reviews)),
    }
