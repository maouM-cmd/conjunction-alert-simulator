"""Initial fleet registry schema (Phase 9A)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_fleet_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fleets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "satellites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("norad_id", sa.Integer(), nullable=False),
        sa.Column("tle", sa.Text(), nullable=False),
        sa.Column("tle_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fleet_id", "norad_id", name="uq_satellites_fleet_norad"),
    )
    op.create_index("ix_satellites_fleet_id", "satellites", ["fleet_id"], unique=False)
    op.create_table(
        "tle_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("satellite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tle", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["satellite_id"], ["satellites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tle_revisions_satellite_id", "tle_revisions", ["satellite_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tle_revisions_satellite_id", table_name="tle_revisions")
    op.drop_table("tle_revisions")
    op.drop_index("ix_satellites_fleet_id", table_name="satellites")
    op.drop_table("satellites")
    op.drop_table("fleets")
