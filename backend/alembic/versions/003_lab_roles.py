"""Move operational roles to LabMembership; org membership becomes ADMIN/MEMBER."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organization_memberships", sa.Column("org_role", sa.String(50), nullable=True))
    op.add_column("lab_memberships", sa.Column("lab_role", sa.String(50), nullable=True))
    op.add_column("invitations", sa.Column("lab_role", sa.String(50), nullable=True))
    op.add_column("invitations", sa.Column("org_role", sa.String(50), nullable=True))

    op.execute("""
        UPDATE organization_memberships om
        SET org_role = CASE WHEN r.name = 'Admin' THEN 'ADMIN' ELSE 'MEMBER' END
        FROM roles r WHERE r.id = om.role_id
    """)
    op.execute("""
        UPDATE lab_memberships lm
        SET lab_role = CASE
            WHEN r.name = 'Manager' THEN 'MANAGER'
            WHEN r.name = 'Contributor' THEN 'CONTRIBUTOR'
            ELSE 'CONTRIBUTOR'
        END
        FROM roles r WHERE r.id = lm.role_id
    """)
    op.execute("""
        UPDATE invitations i
        SET lab_role = CASE
            WHEN r.name = 'Manager' THEN 'MANAGER'
            WHEN r.name = 'Contributor' THEN 'CONTRIBUTOR'
            ELSE NULL
        END,
        org_role = CASE WHEN r.name = 'Admin' THEN 'ADMIN' ELSE 'MEMBER' END
        FROM roles r WHERE r.id = i.role_id
    """)

    op.alter_column("organization_memberships", "org_role", nullable=False, server_default="MEMBER")
    op.alter_column("lab_memberships", "lab_role", nullable=False, server_default="CONTRIBUTOR")

    op.create_table(
        "lab_google_workspace",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lab_id", sa.UUID(), sa.ForeignKey("labs.id"), nullable=False, unique=True),
        sa.Column("drive_url", sa.String(1024), nullable=True),
        sa.Column("calendar_id", sa.String(255), nullable=True),
        sa.Column("chat_space_url", sa.String(1024), nullable=True),
        sa.Column("meet_url", sa.String(1024), nullable=True),
        sa.Column("provisioning_status", sa.String(50), server_default="REQUESTED"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("lab_google_workspace")
    op.drop_column("invitations", "org_role")
    op.drop_column("invitations", "lab_role")
    op.drop_column("lab_memberships", "lab_role")
    op.drop_column("organization_memberships", "org_role")
