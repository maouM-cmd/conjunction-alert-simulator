"""API SLO hourly buckets (Phase 10J)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_api_slo_buckets"
down_revision: Union[str, None] = "009_alert_mitigation_trigger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_slo_hourly_buckets",
        sa.Column("hour_epoch", sa.BigInteger(), primary_key=True),
        sa.Column("request_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors_5xx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("api_slo_hourly_buckets")
