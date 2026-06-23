"""
数据库模型定义

【学习要点】
- 每个 class 对应数据库中的一张表
- 类的属性（Column）对应表的列
- SQLAlchemy 会根据这些定义自动创建表结构
- 这就是 ORM 的核心思想：用 Python 类描述数据库结构

MVP 阶段只需要 3 张表：
1. StockBasic - 股票基础信息（代码、名称、行业等）
2. DailyQuote - 日线行情（每天的开高低收、成交额等）
3. StockFinancial - 财务数据（用于基本面筛选）
"""

from sqlalchemy import Column, Date, DateTime, Float, Index, Integer, String, func

from app.database import Base


class StockBasic(Base):
    """
    股票基础信息表

    存储 A 股所有股票的基本资料，数据来源于 Tushare 的 stock_basic 接口。
    这张表相当于"花名册"，记录每只股票是谁、属于什么行业。
    """

    __tablename__ = "stock_basic"

    ts_code = Column(String(20), primary_key=True, comment="股票代码，如 000001.SZ")
    name = Column(String(50), nullable=False, comment="股票名称，如 平安银行")
    industry = Column(String(50), comment="所属行业，如 银行")
    market = Column(String(20), comment="市场类型：主板/创业板/科创板/北交所")
    list_date = Column(String(8), comment="上市日期，格式 YYYYMMDD")
    list_status = Column(String(1), default="L", comment="上市状态：L上市 D退市 P暂停")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="最后更新时间")


class DailyQuote(Base):
    """
    日线行情表

    存储每只股票每个交易日的行情数据。
    这是系统中数据量最大的表（约 5000 只股票 × 250 个交易日/年 × N 年）。

    【学习要点】
    - 复合主键：用 (ts_code, trade_date) 两个字段一起作为主键
      因为同一只股票的不同日期、同一天的不同股票，都需要各自独立的记录
    - Index：索引是数据库的"目录"，让查询更快
      比如经常按日期查询，就给 trade_date 建索引
    """

    __tablename__ = "daily_quote"

    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    vol = Column(Float, comment="成交量（手）")
    amount = Column(Float, comment="成交额（千元）")
    pct_chg = Column(Float, comment="涨跌幅（%）")
    # 以下字段来自 daily_basic 接口
    total_mv = Column(Float, comment="总市值（万元）")
    turnover_rate = Column(Float, comment="换手率（%）")

    # 建立索引，加速按日期查询
    __table_args__ = (
        Index("ix_daily_trade_date", "trade_date"),
        Index("ix_daily_code_date", "ts_code", "trade_date"),
    )


class StockFinancial(Base):
    """
    财务数据表

    存储每只股票每个报告期的关键财务指标。
    主要用途：判断"扣非归母净利润连续三年增长"。

    【学习要点】
    - 财务数据按"报告期"(end_date)区分，如 20231231 表示 2023 年年报
    - ann_date 是公告日期（实际发布日），end_date 是报告期截止日
    - 同一报告期可能有多次公告（修正），所以用 (ts_code, ann_date, end_date) 做复合主键
    """

    __tablename__ = "stock_financial"

    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    ann_date = Column(String(8), primary_key=True, comment="公告日期")
    end_date = Column(String(8), primary_key=True, comment="报告期截止日")
    profit_dedt = Column(Float, comment="扣非归母净利润（元）")
    revenue = Column(Float, comment="营业收入（元）")
    updated_at = Column(DateTime, server_default=func.now(), comment="入库时间")

    __table_args__ = (
        Index("ix_financial_code", "ts_code"),
        Index("ix_financial_end_date", "end_date"),
    )
