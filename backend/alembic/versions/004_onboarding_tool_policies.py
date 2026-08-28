"""Lab tool policies, contributor onboarding, role change notices."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_tool_policies",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("lab_id", sa.UUID(), sa.ForeignKey("labs.id"), nullable=False),
        sa.Column("tool_type", sa.String(100), nullable=False),
        sa.Column("access_mode", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("lab_id", "tool_type", name="uq_lab_tool_policy"),
    )

    op.create_table(
        "lab_onboarding_progress",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lab_id", sa.UUID(), sa.ForeignKey("labs.id"), nullable=False),
        sa.Column("lab_role", sa.String(50), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "lab_id", name="uq_lab_onboarding"),
    )

    op.add_column("lab_memberships", sa.Column("role_change_notice", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("lab_memberships", "role_change_notice")
    op.drop_table("lab_onboarding_progress")
    op.drop_table("lab_tool_policies")
