"""市场情绪原始涨停/炸板事件表。"""

from sqlalchemy import Column, Float, Index, Integer, String

from app.database import Base


class LimitEventDaily(Base):
    __tablename__ = "limit_event_daily"

    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    limit_type = Column(String(1), primary_key=True, comment="事件类型 U/Z")
    name = Column(String(50), nullable=True)
    limit_times = Column(Integer, nullable=True)
    up_stat = Column(String(50), nullable=True)
    first_time = Column(String(10), nullable=True)
    last_time = Column(String(10), nullable=True)
    open_num = Column(Integer, nullable=True)
    fd_amount = Column(Float, nullable=True)
    source = Column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_limit_event_trade_date", "trade_date"),
        Index("ix_limit_event_code_date", "ts_code", "trade_date"),
        Index("ix_limit_event_type_date", "trade_date", "limit_type"),
    )
