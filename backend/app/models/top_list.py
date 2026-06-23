"""龙虎榜汇总与营业部明细表。"""

from sqlalchemy import Column, Float, Index, Integer, String, UniqueConstraint

from app.database import Base


class TopList(Base):
    __tablename__ = "top_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(String(8), nullable=False)
    name = Column(String(50), nullable=True)
    close = Column(Float, nullable=True)
    pct_change = Column(Float, nullable=True)
    turnover_rate = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    l_buy = Column(Float, nullable=True)
    l_sell = Column(Float, nullable=True)
    net_amount = Column(Float, nullable=True)
    net_rate = Column(Float, nullable=True)
    amount_rate = Column(Float, nullable=True)
    float_values = Column(Float, nullable=True)
    reason = Column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_top_list_trade_date", "trade_date"),
        Index("ix_top_list_code_date", "ts_code", "trade_date"),
        UniqueConstraint("ts_code", "trade_date", "reason", name="uq_toplist_ts_date_reason"),
    )


class TopListDetail(Base):
    __tablename__ = "top_list_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(String(8), nullable=False)
    exalter = Column(String(200), nullable=True)
    buy = Column(Float, nullable=True)
    sell = Column(Float, nullable=True)
    net_buy = Column(Float, nullable=True)
    side = Column(String(10), nullable=True)
    reason = Column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_top_list_detail_trade_date", "trade_date"),
        Index("ix_top_list_detail_code_date", "ts_code", "trade_date"),
    )
