"""v5 trading plan and user config tables

Revision ID: a5b6c7d8e9f0
Revises: e1f2a3b4c5d6
Create Date: 2026-04-06 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trading_plan",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts_code", sa.String(20), nullable=False, comment="股票代码"),
        sa.Column("stock_name", sa.String(50), nullable=False, comment="股票名称"),
        sa.Column("direction", sa.String(10), nullable=False, comment="buy 或 sell"),
        sa.Column("target_price", sa.Float(), nullable=False, comment="目标入场价"),
        sa.Column("stop_loss_price", sa.Float(), nullable=False, comment="止损价"),
        sa.Column("take_profit", sa.Text(), nullable=False, comment="分批止盈 JSON 数组"),
        sa.Column("position_ratio", sa.Float(), nullable=False, comment="仓位比例 0-0.4"),
        sa.Column("reasoning", sa.Text(), nullable=False, comment="计划理由 Markdown"),
        sa.Column("risk_comment", sa.Text(), nullable=True, comment="LLM 风控评语"),
        sa.Column("tier_label", sa.String(20), nullable=True, comment="aggressive/balanced/conservative"),
        sa.Column("source", sa.String(20), nullable=False, comment="llm_generated 或 manual"),
        sa.Column("status", sa.String(20), nullable=False, comment="pending/executed/abandoned"),
        sa.Column("expiry_date", sa.String(10), nullable=True, comment="有效期 YYYY-MM-DD"),
        sa.Column("alternatives", sa.Text(), nullable=True, comment="未选中的 LLM 备选方案 JSON"),
        sa.Column("created_at", sa.String(30), nullable=False, comment="创建时间 ISO"),
        sa.Column("updated_at", sa.String(30), nullable=False, comment="更新时间 ISO"),
    )
    op.create_index("ix_plan_ts_code", "trading_plan", ["ts_code"])
    op.create_index("ix_plan_status", "trading_plan", ["status"])

    op.create_table(
        "user_config",
        sa.Column("key", sa.String(50), primary_key=True, comment="配置键"),
        sa.Column("value", sa.Text(), nullable=False, comment="配置值"),
    )


def downgrade() -> None:
    op.drop_table("user_config")
    op.drop_index("ix_plan_status", table_name="trading_plan")
    op.drop_index("ix_plan_ts_code", table_name="trading_plan")
    op.drop_table("trading_plan")
