"""Fleet API SLO hourly buckets (Phase 10N)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_api_slo_fleet_buckets"
down_revision: Union[str, None] = "010_api_slo_buckets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_slo_fleet_hourly_buckets",
        sa.Column("fleet_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("hour_epoch", sa.BigInteger(), nullable=False),
        sa.Column("request_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors_5xx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("fleet_id", "hour_epoch"),
    )


def downgrade() -> None:
    op.drop_table("api_slo_fleet_hourly_buckets")
