"""交易记录与持仓模型。"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradeRecord(Base):
    __tablename__ = "trade_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), index=True)
    stock_name: Mapped[str] = mapped_column(String(50))
    plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trading_plan.id", ondelete="SET NULL")
    )
    direction: Mapped[str] = mapped_column(String(10), comment="buy / sell")
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, comment="成交股数")
    amount: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0)
    trade_date: Mapped[str] = mapped_column(String(10), comment="YYYY-MM-DD")
    trade_time: Mapped[str | None] = mapped_column(String(8), comment="HH:MM:SS")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(30))

    __table_args__ = (
        Index("ix_trade_ts_code_date", "ts_code", "trade_date"),
        Index("ix_trade_plan_id", "plan_id"),
    )


class Position(Base):
    __tablename__ = "position"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(50))
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_cost: Mapped[float] = mapped_column(Float, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(10), default="holding", comment="holding / closed")
    first_buy_date: Mapped[str] = mapped_column(String(10))
    last_trade_date: Mapped[str] = mapped_column(String(10))
    updated_at: Mapped[str] = mapped_column(String(30))
