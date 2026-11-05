"""create user investment platforms

Revision ID: k4f68b1d3c97
Revises: j3e57a0c2b86
"""
from alembic import op
import sqlalchemy as sa

revision = "k4f68b1d3c97"
down_revision = "j3e57a0c2b86"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investment_platforms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("services", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "code", name="uq_investment_platform_user_code"),
    )
    op.create_index(op.f("ix_investment_platforms_user_id"), "investment_platforms", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_investment_platforms_user_id"), table_name="investment_platforms")
    op.drop_table("investment_platforms")
