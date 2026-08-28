"""Track scavenger-hunt onboarding step progress."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lab_onboarding_progress",
        sa.Column("steps_completed", JSON, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("lab_onboarding_progress", "steps_completed")
