"""Add login-lockout tracking columns to users (P0 security)."""

import sqlalchemy as sa

from alembic import op

revision = "0028_user_login_lockout"
down_revision = "0027_add_document_index_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
