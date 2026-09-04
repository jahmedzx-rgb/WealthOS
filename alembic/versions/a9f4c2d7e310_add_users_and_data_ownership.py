"""add users and data ownership

Revision ID: a9f4c2d7e310
Revises: f31bc6ad8102
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9f4c2d7e310"
down_revision: str | None = "f31bc6ad8102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OWNED_TABLES = ("entities", "brokers", "journal_entries", "loans", "import_batches")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.execute(sa.text("INSERT INTO users (id, email, full_name, is_active) VALUES (1, 'ahmed@local.wealthos', 'Ahmed', true)"))

    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"))
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_foreign_key(
                f"fk_{table}_user_id_users",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                server_default=None,
            )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in reversed(OWNED_TABLES):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_user_id_users", type_="foreignkey")
            batch_op.drop_column("user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
