"""市场情绪原始题材热度表。"""

from sqlalchemy import Column, Float, Index, Integer, String

from app.database import Base


class ThemeHeatDaily(Base):
    __tablename__ = "theme_heat_daily"

    theme_code = Column(String(50), primary_key=True, comment="题材代码")
    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    theme_name = Column(String(100), nullable=True)
    rank = Column(Integer, nullable=True)
    up_nums = Column(Integer, nullable=True)
    cons_nums = Column(Integer, nullable=True)
    up_stat = Column(String(50), nullable=True)
    score = Column(Float, nullable=True)
    source = Column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_theme_heat_trade_date", "trade_date"),
        Index("ix_theme_heat_code_date", "theme_code", "trade_date"),
    )
