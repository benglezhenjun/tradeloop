"""market sentiment snapshot table

Revision ID: a1c2e3f4a5b6
Revises: f0a1b2c3d4e5
Create Date: 2026-04-08 16:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1c2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_sentiment_daily",
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("max_limit_height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_limit_height_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_limit_height_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limit_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_broken_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("yday_limit_premium_avg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("yday_limit_premium_median", sa.Float(), nullable=False, server_default="0"),
        sa.Column("yday_limit_red_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("yday_limit_sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_board_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("high_board_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_board_advanced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_board_promotion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("main_theme_code", sa.String(length=50), nullable=True),
        sa.Column("main_theme_name", sa.String(length=100), nullable=True),
        sa.Column("main_theme_score", sa.Float(), nullable=True),
        sa.Column("main_theme_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes_json", sa.Text(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("trade_date"),
    )
    op.create_index(
        "ix_market_sentiment_trade_date",
        "market_sentiment_daily",
        ["trade_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_sentiment_trade_date", table_name="market_sentiment_daily")
    op.drop_table("market_sentiment_daily")
