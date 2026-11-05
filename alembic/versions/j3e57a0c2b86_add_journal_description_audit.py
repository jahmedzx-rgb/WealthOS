"""add journal description audit

Revision ID: j3e57a0c2b86
Revises: i2d46f9b1a75
"""
from alembic import op
import sqlalchemy as sa

revision = "j3e57a0c2b86"
down_revision = "i2d46f9b1a75"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journal_entry_description_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("previous_description", sa.String(length=255), nullable=False),
        sa.Column("new_description", sa.String(length=255), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journal_entry_description_audits_journal_entry_id"), "journal_entry_description_audits", ["journal_entry_id"], unique=False)
    op.create_index(op.f("ix_journal_entry_description_audits_user_id"), "journal_entry_description_audits", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_journal_entry_description_audits_user_id"), table_name="journal_entry_description_audits")
    op.drop_index(op.f("ix_journal_entry_description_audits_journal_entry_id"), table_name="journal_entry_description_audits")
    op.drop_table("journal_entry_description_audits")
