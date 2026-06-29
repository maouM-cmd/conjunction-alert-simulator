"""Screening run chunk columns (Phase 9D)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_screening_chunks"
down_revision: Union[str, None] = "003_conjunction_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "screening_runs",
        sa.Column("parent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("screening_runs", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column("screening_runs", sa.Column("chunk_total", sa.Integer(), nullable=True))
    op.add_column(
        "screening_runs",
        sa.Column("completed_chunks", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_screening_runs_parent_run_id",
        "screening_runs",
        "screening_runs",
        ["parent_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_screening_runs_parent_run_id", "screening_runs", ["parent_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_screening_runs_parent_run_id", table_name="screening_runs")
    op.drop_constraint("fk_screening_runs_parent_run_id", "screening_runs", type_="foreignkey")
    op.drop_column("screening_runs", "completed_chunks")
    op.drop_column("screening_runs", "chunk_total")
    op.drop_column("screening_runs", "chunk_index")
    op.drop_column("screening_runs", "parent_run_id")
