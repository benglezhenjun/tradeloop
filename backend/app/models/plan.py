"""交易计划表 + 用户配置表 (V5)"""

from sqlalchemy import Column, Float, Index, Integer, String, Text

from app.database import Base


class TradingPlan(Base):
    """
    交易计划表

    存储用户的交易计划，来源可以是 LLM 生成或手动创建。
    LLM 生成时，未被选中的备选方案存储在 alternatives 字段。
    """

    __tablename__ = "trading_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    stock_name = Column(String(50), nullable=False, comment="股票名称")
    direction = Column(String(10), nullable=False, comment="buy 或 sell")
    target_price = Column(Float, nullable=False, comment="目标入场价")
    stop_loss_price = Column(Float, nullable=False, comment="止损价")
    take_profit = Column(Text, nullable=False, comment="分批止盈 JSON 数组")
    position_ratio = Column(Float, nullable=False, comment="仓位比例 0-0.4")
    reasoning = Column(Text, nullable=False, comment="计划理由 Markdown")
    risk_comment = Column(Text, nullable=True, comment="LLM 风控评语")
    tier_label = Column(String(20), nullable=True, comment="aggressive/balanced/conservative")
    source = Column(String(20), nullable=False, comment="llm_generated 或 manual")
    status = Column(
        String(20),
        nullable=False,
        comment="pending/executed/abandoned",
    )
    expiry_date = Column(String(10), nullable=True, comment="有效期 YYYY-MM-DD")
    alternatives = Column(Text, nullable=True, comment="未选中的 LLM 备选方案 JSON")
    created_at = Column(String(30), nullable=False, comment="创建时间 ISO")
    updated_at = Column(String(30), nullable=False, comment="更新时间 ISO")

    __table_args__ = (
        Index("ix_plan_ts_code", "ts_code"),
        Index("ix_plan_status", "status"),
    )


class UserConfig(Base):
    """
    用户配置表（键值对）

    存储全局用户配置，如总资金等。
    """

    __tablename__ = "user_config"

    key = Column(String(50), primary_key=True, comment="配置键")
    value = Column(Text, nullable=False, comment="配置值")
