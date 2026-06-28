"""Conjunction alerts schema (Phase 9C)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_conjunction_alerts"
down_revision: Union[str, None] = "002_screening_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conjunction_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("satellite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("screening_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("debris_norad_id", sa.Integer(), nullable=False),
        sa.Column("debris_name", sa.String(length=255), nullable=False),
        sa.Column("tca", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pc", sa.Float(), nullable=False),
        sa.Column("miss_distance_km", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["satellite_id"], ["satellites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["screening_run_id"], ["screening_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conjunction_alerts_fleet_id", "conjunction_alerts", ["fleet_id"], unique=False)
    op.create_index("ix_conjunction_alerts_satellite_id", "conjunction_alerts", ["satellite_id"], unique=False)
    op.create_index(
        "ix_conjunction_alerts_screening_run_id", "conjunction_alerts", ["screening_run_id"], unique=False
    )
    op.create_index(
        "ix_conjunction_alerts_sat_debris",
        "conjunction_alerts",
        ["satellite_id", "debris_norad_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conjunction_alerts_sat_debris", table_name="conjunction_alerts")
    op.drop_index("ix_conjunction_alerts_screening_run_id", table_name="conjunction_alerts")
    op.drop_index("ix_conjunction_alerts_satellite_id", table_name="conjunction_alerts")
    op.drop_index("ix_conjunction_alerts_fleet_id", table_name="conjunction_alerts")
    op.drop_table("conjunction_alerts")
