"""Merge scheduled-loan payments with the existing migration head."""

revision = "b6d4a9c21f30"
down_revision = ("a4c219f8d6b1", "f0c39b6d1a27")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("The merged migration heads require an explicit data-preserving rollback.")
