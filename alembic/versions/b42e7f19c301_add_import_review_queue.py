"""Add document import review queue

Revision ID: b42e7f19c301
Revises: 536fa86e74bb
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b42e7f19c301"
down_revision: Union[str, Sequence[str], None] = "536fa86e74bb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("import_batches", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("filename", sa.String(255), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("file_type", sa.String(100), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("next_reminder_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_import_batches_status", "import_batches", ["status"])
    op.create_table("imported_operations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False), sa.Column("operation_type", sa.String(40), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=True), sa.Column("currency", sa.String(10), nullable=True), sa.Column("transaction_date", sa.String(30), nullable=True), sa.Column("card_last4", sa.String(4), nullable=True), sa.Column("confidence", sa.Integer(), nullable=False), sa.Column("source_text", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False))
    op.create_index("ix_imported_operations_batch_id", "imported_operations", ["batch_id"])
    op.create_index("ix_imported_operations_status", "imported_operations", ["status"])


def downgrade() -> None:
    op.drop_table("imported_operations")
    op.drop_table("import_batches")
