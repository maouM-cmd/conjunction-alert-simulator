"""Fleet breach history retention days override (Phase 10AG)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_fleet_breach_history_retention_days"
down_revision: Union[str, None] = "013_fleet_alert_breach_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fleets",
        sa.Column("breach_history_retention_days", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fleets", "breach_history_retention_days")
