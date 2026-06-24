"""股票基础信息表"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockBasic(Base):
    """
    股票基础信息表
    存储 A 股所有股票的基本资料（代码、名称、行业、上市状态）。
    """

    __tablename__ = "stock_basic"

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True, comment="股票代码，如 000001.SZ")
    name: Mapped[str] = mapped_column(String(50), comment="股票名称")
    industry: Mapped[str | None] = mapped_column(String(50), comment="所属行业")
    market: Mapped[str | None] = mapped_column(String(20), comment="市场类型：主板/创业板/科创板/北交所")
    list_date: Mapped[str | None] = mapped_column(String(8), comment="上市日期 YYYYMMDD")
    list_status: Mapped[str | None] = mapped_column(String(1), default="L", comment="上市状态：L上市 D退市 P暂停")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
