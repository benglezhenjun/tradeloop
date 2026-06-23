from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text

from app.database import Base


class TradeReview(Base):
    __tablename__ = "trade_review"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    plan_id = Column(Integer, ForeignKey("trading_plan.id", ondelete="SET NULL"), nullable=True)
    total_buy_amount = Column(Float, nullable=False)
    total_sell_amount = Column(Float, nullable=False)
    total_fee = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    trade_count = Column(Integer, nullable=False)
    first_trade_date = Column(String(10), nullable=False)
    last_trade_date = Column(String(10), nullable=False)
    holding_days = Column(Integer, nullable=False)
    scores = Column(Text, nullable=False)
    overall_score = Column(Float, nullable=False)
    analysis = Column(Text, nullable=False)
    improvement = Column(Text, nullable=True)
    user_notes = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)

    __table_args__ = (
        Index("ix_review_ts_code", "ts_code"),
        Index("ix_review_plan_id", "plan_id"),
    )


class BehaviorPattern(Base):
    __tablename__ = "behavior_pattern"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(20), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    dimension = Column(String(30), nullable=True)
    evidence_ids = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)
