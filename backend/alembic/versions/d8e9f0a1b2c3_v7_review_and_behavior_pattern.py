"""v7 review and behavior pattern tables

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-04-06 22:45:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_review",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("stock_name", sa.String(length=50), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("total_buy_amount", sa.Float(), nullable=False),
        sa.Column("total_sell_amount", sa.Float(), nullable=False),
        sa.Column("total_fee", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("first_trade_date", sa.String(length=10), nullable=False),
        sa.Column("last_trade_date", sa.String(length=10), nullable=False),
        sa.Column("holding_days", sa.Integer(), nullable=False),
        sa.Column("scores", sa.Text(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("improvement", sa.Text(), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["trading_plan.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_ts_code", "trade_review", ["ts_code"], unique=False)
    op.create_index("ix_review_plan_id", "trade_review", ["plan_id"], unique=False)

    op.create_table(
        "behavior_pattern",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pattern_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("dimension", sa.String(length=30), nullable=True),
        sa.Column("evidence_ids", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("behavior_pattern")
    op.drop_index("ix_review_plan_id", table_name="trade_review")
    op.drop_index("ix_review_ts_code", table_name="trade_review")
    op.drop_table("trade_review")
