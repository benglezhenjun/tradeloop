"""
策略相关数据表

涉及 5 张表，完整描述了"策略是什么 + 跑了什么结果"：

Condition        ← 条件定义（系统内置，不是用户创建）
Strategy         ← 用户定义的策略（一个名字 + 一组条件）
StrategyCondition← 策略和条件的关联（多对多，含参数快照）
StrategyRun      ← 策略每次运行的记录（何时跑、跑了哪天）
ScreeningResult  ← 每次运行的结果（哪些股票入选了）
"""

import json

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class Condition(Base):
    """
    条件定义表（系统内置，不需要用户手动创建）

    每一行代表一种筛选条件，如"成交额大于阈值"、"价格在MA20附近"。
    param_schema 字段存储这个条件有哪些参数、默认值是什么（JSON格式）。

    示例 param_schema：
    {
        "threshold": {"label": "成交额下限（元）", "type": "number", "default": 2000000000}
    }
    """

    __tablename__ = "condition"

    code = Column(String(50), primary_key=True, comment="条件代码，如 amount_gt（程序内部用）")
    name = Column(String(100), nullable=False, comment="条件名称（给用户看的）")
    category = Column(String(30), comment="分类：量价/市值/技术/基本面/排名")
    description = Column(Text, comment="条件说明")
    param_schema = Column(Text, default="{}", comment="参数定义（JSON）")


class Strategy(Base):
    """
    策略定义表

    一个策略 = 一个名字 + N 个条件（通过 StrategyCondition 关联）。
    """

    __tablename__ = "strategy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="策略名称")
    description = Column(Text, comment="策略说明")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyCondition(Base):
    """
    策略-条件关联表（多对多）

    记录某个策略用了哪些条件，以及这个策略里这个条件的参数是什么。
    params 字段存储该条件在本策略中的参数值（覆盖条件的默认值）。
    """

    __tablename__ = "strategy_condition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategy.id", ondelete="CASCADE"), nullable=False)
    condition_code = Column(String(50), ForeignKey("condition.code"), nullable=False)
    params = Column(Text, default="{}", comment="参数值（JSON），覆盖条件默认值")
    is_enabled = Column(Boolean, default=True, comment="在本策略中是否启用此条件")
    sort_order = Column(Integer, default=0, comment="条件执行顺序")

    __table_args__ = (Index("ix_sc_strategy", "strategy_id"),)

    def get_params(self) -> dict:
        return json.loads(self.params or "{}")

    def set_params(self, params: dict):
        self.params = json.dumps(params, ensure_ascii=False)


class StrategyRun(Base):
    """
    策略运行记录表

    每次点击"运行"都会产生一条记录，记录当时用的参数和筛选日期。
    这样可以回顾历史："上周三用策略1筛出了哪些股票？"
    """

    __tablename__ = "strategy_run"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategy.id", ondelete="SET NULL"), nullable=True)
    strategy_name = Column(String(100), comment="运行时的策略名称快照")
    trade_date = Column(String(8), comment="筛选的交易日期 YYYYMMDD")
    run_at = Column(DateTime, server_default=func.now(), comment="实际运行时间")
    result_count = Column(Integer, default=0, comment="筛出的股票数量")
    duration_ms = Column(Integer, comment="执行耗时（毫秒）")

    __table_args__ = (Index("ix_run_strategy", "strategy_id"), Index("ix_run_date", "trade_date"))


class ScreeningResult(Base):
    """
    筛选结果表

    每次运行的每只入选股票都存一行，关键字段快照存 JSON。
    保存历史结果，方便以后回顾。
    """

    __tablename__ = "screening_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("strategy_run.id", ondelete="CASCADE"), nullable=False)
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    rank = Column(Integer, comment="本次筛选中的排名")
    snapshot = Column(Text, default="{}", comment="当时的关键数据快照（JSON）")

    __table_args__ = (Index("ix_result_run", "run_id"), Index("ix_result_code", "ts_code"))

    def get_snapshot(self) -> dict:
        return json.loads(self.snapshot or "{}")
