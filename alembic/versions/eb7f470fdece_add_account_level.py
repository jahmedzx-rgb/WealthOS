"""Add account level

Revision ID: eb7f470fdece
Revises: 80d3bbbd17f1
Create Date: 2026-07-14 23:07:01.954369
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "eb7f470fdece"
down_revision: Union[str, Sequence[str], None] = "80d3bbbd17f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "accounts",
        sa.Column(
            "level",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # SQLite has no direct ALTER COLUMN operation. Batch mode recreates the
    # table there while retaining PostgreSQL's native ALTER behavior.
    with op.batch_alter_table("journal_entries") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table("journal_entries") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=False,
        )

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("level")
