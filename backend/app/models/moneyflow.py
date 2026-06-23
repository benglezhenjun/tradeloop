"""个股资金流向表。"""

from sqlalchemy import Column, Float, Index, String

from app.database import Base


class DailyMoneyflow(Base):
    __tablename__ = "daily_moneyflow"

    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    net_mf_amount = Column(Float, nullable=True)
    net_mf_vol = Column(Float, nullable=True)
    net_amount = Column(Float, nullable=True)
    buy_elg_amount = Column(Float, nullable=True)
    buy_lg_amount = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_moneyflow_trade_date", "trade_date"),
        Index("ix_moneyflow_code_date", "ts_code", "trade_date"),
    )
