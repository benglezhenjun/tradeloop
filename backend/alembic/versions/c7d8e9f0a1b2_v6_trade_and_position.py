"""v6 trade and position tables

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-04-06 20:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("stock_name", sa.String(50), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("trading_plan.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False, comment="buy / sell"),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, comment="成交股数"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("fee", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trade_date", sa.String(10), nullable=False, comment="YYYY-MM-DD"),
        sa.Column("trade_time", sa.String(8), nullable=True, comment="HH:MM:SS"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(30), nullable=False),
    )
    op.create_index("ix_trade_record_ts_code", "trade_record", ["ts_code"])
    op.create_index("ix_trade_ts_code_date", "trade_record", ["ts_code", "trade_date"])
    op.create_index("ix_trade_plan_id", "trade_record", ["plan_id"])

    op.create_table(
        "position",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts_code", sa.String(20), nullable=False, unique=True),
        sa.Column("stock_name", sa.String(50), nullable=False),
        sa.Column("total_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(10), nullable=False, server_default="holding", comment="holding / closed"),
        sa.Column("first_buy_date", sa.String(10), nullable=False),
        sa.Column("last_trade_date", sa.String(10), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
    )
    op.create_index("ix_position_ts_code", "position", ["ts_code"], unique=True)

    for key, value in (
        ("commission_rate", "0.00025"),
        ("stamp_tax_rate", "0.001"),
        ("transfer_fee_rate", "0.00002"),
    ):
        op.execute(
            sa.text(
                f"""
                INSERT INTO user_config ("key", value)
                SELECT '{key}', '{value}'
                WHERE NOT EXISTS (
                    SELECT 1 FROM user_config WHERE "key" = '{key}'
                )
                """
            )
        )


def downgrade() -> None:
    for key, value in (
        ("commission_rate", "0.00025"),
        ("stamp_tax_rate", "0.001"),
        ("transfer_fee_rate", "0.00002"),
    ):
        op.execute(
            sa.text(
                f"DELETE FROM user_config WHERE \"key\" = '{key}' AND value = '{value}'"
            )
        )

    op.drop_index("ix_position_ts_code", table_name="position")
    op.drop_table("position")
    op.drop_index("ix_trade_plan_id", table_name="trade_record")
    op.drop_index("ix_trade_ts_code_date", table_name="trade_record")
    op.drop_index("ix_trade_record_ts_code", table_name="trade_record")
    op.drop_table("trade_record")
