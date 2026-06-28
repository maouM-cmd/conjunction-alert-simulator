"""Initial screening jobs schema (Phase 9B)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_screening_jobs"
down_revision: Union[str, None] = "001_initial_fleet_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screening_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cron_expression", sa.String(length=128), nullable=False),
        sa.Column("threshold_km", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("duration_days", sa.Float(), nullable=False, server_default="7.0"),
        sa.Column("step_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("use_advanced_pc", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("use_altitude_prefilter", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_spacetrack_cdm", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("spacetrack_cdm_pc_min", sa.Float(), nullable=True),
        sa.Column("notify_on_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screening_schedules_fleet_id", "screening_schedules", ["fleet_id"], unique=False)

    op.create_table(
        "screening_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("satellite_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("computation_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["screening_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screening_runs_schedule_id", "screening_runs", ["schedule_id"], unique=False)
    op.create_index("ix_screening_runs_fleet_id", "screening_runs", ["fleet_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_screening_runs_fleet_id", table_name="screening_runs")
    op.drop_index("ix_screening_runs_schedule_id", table_name="screening_runs")
    op.drop_table("screening_runs")
    op.drop_index("ix_screening_schedules_fleet_id", table_name="screening_schedules")
    op.drop_table("screening_schedules")
