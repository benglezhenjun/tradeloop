"""market sentiment raw tables

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-04-08 15:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "limit_event_daily",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("limit_type", sa.String(length=1), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("limit_times", sa.Integer(), nullable=True),
        sa.Column("up_stat", sa.String(length=50), nullable=True),
        sa.Column("first_time", sa.String(length=10), nullable=True),
        sa.Column("last_time", sa.String(length=10), nullable=True),
        sa.Column("open_num", sa.Integer(), nullable=True),
        sa.Column("fd_amount", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", "limit_type"),
    )
    op.create_index(
        "ix_limit_event_trade_date",
        "limit_event_daily",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        "ix_limit_event_code_date",
        "limit_event_daily",
        ["ts_code", "trade_date"],
        unique=False,
    )
    op.create_index(
        "ix_limit_event_type_date",
        "limit_event_daily",
        ["trade_date", "limit_type"],
        unique=False,
    )

    op.create_table(
        "theme_heat_daily",
        sa.Column("theme_code", sa.String(length=50), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("theme_name", sa.String(length=100), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("up_nums", sa.Integer(), nullable=True),
        sa.Column("cons_nums", sa.Integer(), nullable=True),
        sa.Column("up_stat", sa.String(length=50), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("theme_code", "trade_date"),
    )
    op.create_index(
        "ix_theme_heat_trade_date",
        "theme_heat_daily",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        "ix_theme_heat_code_date",
        "theme_heat_daily",
        ["theme_code", "trade_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_theme_heat_code_date", table_name="theme_heat_daily")
    op.drop_index("ix_theme_heat_trade_date", table_name="theme_heat_daily")
    op.drop_table("theme_heat_daily")

    op.drop_index("ix_limit_event_type_date", table_name="limit_event_daily")
    op.drop_index("ix_limit_event_code_date", table_name="limit_event_daily")
    op.drop_index("ix_limit_event_trade_date", table_name="limit_event_daily")
    op.drop_table("limit_event_daily")
