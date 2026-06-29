"""Alert Pc refinement columns (Phase 10D)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_alert_pc_refinements"
down_revision: Union[str, None] = "006_alert_mitigation_previews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_pc_refinements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conjunction_alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pc_screening", sa.Float(), nullable=False),
        sa.Column("pc_refined", sa.Float(), nullable=False),
        sa.Column("pc_method", sa.String(32), nullable=False),
        sa.Column("covariance_source", sa.String(64), nullable=True),
        sa.Column("miss_distance_km", sa.Float(), nullable=False),
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
        "ix_alert_pc_refinements_alert_id",
        "alert_pc_refinements",
        ["alert_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_pc_refinements_alert_id", table_name="alert_pc_refinements")
    op.drop_table("alert_pc_refinements")
