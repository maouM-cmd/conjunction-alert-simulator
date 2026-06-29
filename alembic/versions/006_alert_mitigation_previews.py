"""Alert mitigation preview columns (Phase 10A)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_alert_mitigation_previews"
down_revision: Union[str, None] = "005_api_keys_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_mitigation_previews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conjunction_alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("delta_v_ms", sa.Float(), nullable=False),
        sa.Column("before_tca", sa.DateTime(timezone=True), nullable=False),
        sa.Column("before_miss_distance_km", sa.Float(), nullable=False),
        sa.Column("after_tca", sa.DateTime(timezone=True), nullable=False),
        sa.Column("after_miss_distance_km", sa.Float(), nullable=False),
        sa.Column("relative_velocity_kms", sa.Float(), nullable=True),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alert_mitigation_previews_alert_id",
        "alert_mitigation_previews",
        ["alert_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_mitigation_previews_alert_id", table_name="alert_mitigation_previews")
    op.drop_table("alert_mitigation_previews")
