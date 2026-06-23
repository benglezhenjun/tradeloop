"""股票基础信息表"""

from sqlalchemy import Column, DateTime, String, func

from app.database import Base


class StockBasic(Base):
    """
    股票基础信息表
    存储 A 股所有股票的基本资料（代码、名称、行业、上市状态）。
    """

    __tablename__ = "stock_basic"

    ts_code = Column(String(20), primary_key=True, comment="股票代码，如 000001.SZ")
    name = Column(String(50), nullable=False, comment="股票名称")
    industry = Column(String(50), comment="所属行业")
    market = Column(String(20), comment="市场类型：主板/创业板/科创板/北交所")
    list_date = Column(String(8), comment="上市日期 YYYYMMDD")
    list_status = Column(String(1), default="L", comment="上市状态：L上市 D退市 P暂停")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
