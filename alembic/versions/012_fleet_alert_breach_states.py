"""Fleet alert breach states with sticky override (Phase 10X / 10AB)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_fleet_alert_breach_states"
down_revision: Union[str, None] = "011_api_slo_fleet_buckets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fleet_alert_breach_states",
        sa.Column("fleet_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("alertname", sa.String(length=128), nullable=False),
        sa.Column("is_breaching", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_manual_sticky", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("fleet_id", "alertname"),
    )


def downgrade() -> None:
    op.drop_table("fleet_alert_breach_states")
