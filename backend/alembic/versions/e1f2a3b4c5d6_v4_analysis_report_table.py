"""v4 analysis report table

Revision ID: e1f2a3b4c5d6
Revises: 9d7c1a4b2e3f
Create Date: 2026-04-05 20:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "9d7c1a4b2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_report",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_type", sa.String(20), nullable=False, comment="daily 或 stock"),
        sa.Column("ts_code", sa.String(20), nullable=True, comment="仅 stock 类型有值"),
        sa.Column("content", sa.Text(), nullable=False, comment="完整报告 Markdown"),
        sa.Column("sections", sa.Text(), nullable=True, comment="各 Agent 分段输出 JSON"),
        sa.Column("generated_at", sa.String(30), nullable=False, comment="生成时间 ISO 格式"),
    )
    op.create_index("ix_report_type", "analysis_report", ["report_type"])
    op.create_index("ix_report_ts_code", "analysis_report", ["ts_code"])


def downgrade() -> None:
    op.drop_index("ix_report_ts_code", table_name="analysis_report")
    op.drop_index("ix_report_type", table_name="analysis_report")
    op.drop_table("analysis_report")
