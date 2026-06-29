"""Fleet alert breach history (Phase 10AC)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_fleet_alert_breach_history"
down_revision: Union[str, None] = "012_fleet_alert_breach_states"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fleet_alert_breach_history",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("fleet_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("alertname", sa.String(length=128), nullable=False),
        sa.Column("is_breaching", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("is_sticky", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fleet_alert_breach_history_fleet_created",
        "fleet_alert_breach_history",
        ["fleet_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_fleet_alert_breach_history_fleet_created", table_name="fleet_alert_breach_history")
    op.drop_table("fleet_alert_breach_history")
