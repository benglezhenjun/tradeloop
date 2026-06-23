"""技术指标预计算表。"""

from sqlalchemy import Column, Float, Index, String

from app.database import Base


class DailyIndicator(Base):
    __tablename__ = "daily_indicator"

    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    ma5 = Column(Float, nullable=True)
    ma10 = Column(Float, nullable=True)
    ma20 = Column(Float, nullable=True)
    ma60 = Column(Float, nullable=True)
    ma120 = Column(Float, nullable=True)
    ma240 = Column(Float, nullable=True)
    macd_dif = Column(Float, nullable=True)
    macd_dea = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    kdj_k = Column(Float, nullable=True)
    kdj_d = Column(Float, nullable=True)
    kdj_j = Column(Float, nullable=True)
    rsi_6 = Column(Float, nullable=True)
    rsi_12 = Column(Float, nullable=True)
    rsi_24 = Column(Float, nullable=True)
    boll_upper = Column(Float, nullable=True)
    boll_mid = Column(Float, nullable=True)
    boll_lower = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    obv = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    turnover_change = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_indicator_trade_date", "trade_date"),
        Index("ix_indicator_code_date", "ts_code", "trade_date"),
    )
