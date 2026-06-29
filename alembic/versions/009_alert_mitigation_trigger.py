"""Alert mitigation preview trigger_source (Phase 10F)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_alert_mitigation_trigger"
down_revision: Union[str, None] = "008_alert_pc_refinement_trigger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alert_mitigation_previews",
        sa.Column(
            "trigger_source",
            sa.String(32),
            nullable=False,
            server_default="manual",
        ),
    )


def downgrade() -> None:
    op.drop_column("alert_mitigation_previews", "trigger_source")
