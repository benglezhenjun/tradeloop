"""cleanup invalid watchlist stock records

Revision ID: 9d7c1a4b2e3f
Revises: 0127a57fdd13
Create Date: 2026-04-05 17:05:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "9d7c1a4b2e3f"
down_revision: Union[str, Sequence[str], None] = "0127a57fdd13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM watchlist_stock
        WHERE NOT EXISTS (
            SELECT 1
            FROM stock_basic
            WHERE stock_basic.ts_code = watchlist_stock.ts_code
        )
        """
    )


def downgrade() -> None:
    pass
