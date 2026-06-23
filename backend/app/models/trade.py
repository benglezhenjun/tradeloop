"""交易记录与持仓模型。"""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text

from app.database import Base


class TradeRecord(Base):
    __tablename__ = "trade_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    plan_id = Column(Integer, ForeignKey("trading_plan.id", ondelete="SET NULL"), nullable=True)
    direction = Column(String(10), nullable=False, comment="buy / sell")
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, comment="成交股数")
    amount = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0)
    trade_date = Column(String(10), nullable=False, comment="YYYY-MM-DD")
    trade_time = Column(String(8), nullable=True, comment="HH:MM:SS")
    note = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False)

    __table_args__ = (
        Index("ix_trade_ts_code_date", "ts_code", "trade_date"),
        Index("ix_trade_plan_id", "plan_id"),
    )


class Position(Base):
    __tablename__ = "position"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, unique=True, index=True)
    stock_name = Column(String(50), nullable=False)
    total_quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0)
    realized_pnl = Column(Float, nullable=False, default=0)
    status = Column(String(10), nullable=False, default="holding", comment="holding / closed")
    first_buy_date = Column(String(10), nullable=False)
    last_trade_date = Column(String(10), nullable=False)
    updated_at = Column(String(30), nullable=False)
