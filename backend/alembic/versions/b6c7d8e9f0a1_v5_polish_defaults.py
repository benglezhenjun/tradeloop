"""v5 polish defaults

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-04-06 18:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO user_config ("key", value)
            SELECT 'total_capital', '0'
            WHERE NOT EXISTS (
                SELECT 1 FROM user_config WHERE "key" = 'total_capital'
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM user_config WHERE \"key\" = 'total_capital' AND value = '0'"))
