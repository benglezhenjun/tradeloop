"""分析报告表 (V4)"""

from sqlalchemy import Column, Index, Integer, String, Text

from app.database import Base


class AnalysisReport(Base):
    """
    LLM 分析报告表

    存储历史生成的分析报告，支持日报（daily）和个股分析（stock）两类。
    """

    __tablename__ = "analysis_report"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False, comment="daily 或 stock")
    ts_code = Column(String(20), nullable=True, comment="仅 stock 类型有值")
    content = Column(Text, nullable=False, comment="完整报告 Markdown")
    sections = Column(Text, nullable=True, comment="各 Agent 分段输出 JSON")
    generated_at = Column(String(30), nullable=False, comment="生成时间 ISO 格式")

    __table_args__ = (
        Index("ix_report_type", "report_type"),
        Index("ix_report_ts_code", "ts_code"),
    )
