"""top list unique constraint

Revision ID: b2c3d4e5f6a7
Revises: a1c2e3f4a5b6
Create Date: 2026-04-08 15:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1c2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "top_list" in inspector.get_table_names():
        bind.execute(
            sa.text(
                """
                DELETE FROM top_list
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM top_list
                    GROUP BY ts_code, trade_date, reason
                )
                """
            )
        )

        with op.batch_alter_table("top_list") as batch_op:
            batch_op.create_unique_constraint(
                "uq_toplist_ts_date_reason",
                ["ts_code", "trade_date", "reason"],
            )


def downgrade() -> None:
    with op.batch_alter_table("top_list") as batch_op:
        batch_op.drop_constraint("uq_toplist_ts_date_reason", type_="unique")
