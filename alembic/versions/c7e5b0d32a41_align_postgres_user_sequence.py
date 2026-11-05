"""Advance the PostgreSQL user sequence past legacy explicitly inserted IDs."""

from alembic import op
import sqlalchemy as sa

revision = "c7e5b0d32a41"
down_revision = "b6d4a9c21f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return
    # Registration must not run during this migration. Never rewind an already
    # advanced sequence, including IDs consumed by rolled-back registrations.
    connection.execute(sa.text("LOCK TABLE users IN ACCESS EXCLUSIVE MODE"))
    sequence = connection.execute(sa.text("SELECT pg_get_serial_sequence('users', 'id')")).scalar_one()
    if sequence:
        connection.execute(sa.text("""
            SELECT setval(CAST(:sequence AS regclass),
                GREATEST(COALESCE((SELECT MAX(id) FROM users), 1),
                         COALESCE(pg_sequence_last_value(CAST(:sequence AS regclass)), 1)),
                true)
        """), {"sequence": sequence})


def downgrade() -> None:
    # Sequence values must never be rewound: this change preserves all rows.
    pass
