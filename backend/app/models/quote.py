"""日线行情表"""

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyQuote(Base):
    """
    日线行情表
    每只股票每个交易日的行情数据（开高低收、成交额、市值等）。
    数据量最大的表：约 5000只 × 250天/年 × 3年 ≈ 375 万条。
    """

    __tablename__ = "daily_quote"

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True, comment="股票代码")
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    open: Mapped[float | None] = mapped_column(Float, comment="开盘价")
    high: Mapped[float | None] = mapped_column(Float, comment="最高价")
    low: Mapped[float | None] = mapped_column(Float, comment="最低价")
    close: Mapped[float | None] = mapped_column(Float, comment="收盘价")
    vol: Mapped[float | None] = mapped_column(Float, comment="成交量（手）")
    amount: Mapped[float | None] = mapped_column(Float, comment="成交额（千元）")
    pct_chg: Mapped[float | None] = mapped_column(Float, comment="涨跌幅（%）")
    total_mv: Mapped[float | None] = mapped_column(Float, comment="总市值（万元）")
    turnover_rate: Mapped[float | None] = mapped_column(Float, comment="换手率（%）")

    __table_args__ = (
        Index("ix_daily_trade_date", "trade_date"),
        Index("ix_daily_code_date", "ts_code", "trade_date"),
    )
