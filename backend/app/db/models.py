"""SQLAlchemy ORM models for fleet registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    satellites: Mapped[list[Satellite]] = relationship(
        "Satellite", back_populates="fleet", cascade="all, delete-orphan"
    )


class Satellite(Base):
    __tablename__ = "satellites"
    __table_args__ = (UniqueConstraint("fleet_id", "norad_id", name="uq_satellites_fleet_norad"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    norad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tle: Mapped[str] = mapped_column(Text, nullable=False)
    tle_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    fleet: Mapped[Fleet] = relationship("Fleet", back_populates="satellites")
    tle_revisions: Mapped[list[TleRevision]] = relationship(
        "TleRevision", back_populates="satellite", cascade="all, delete-orphan"
    )


class TleRevision(Base):
    __tablename__ = "tle_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tle: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="tle_revisions")


class ScreeningSchedule(Base):
    __tablename__ = "screening_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    threshold_km: Mapped[float] = mapped_column(nullable=False, default=5.0)
    duration_days: Mapped[float] = mapped_column(nullable=False, default=7.0)
    step_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    use_advanced_pc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    use_altitude_prefilter: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_spacetrack_cdm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    spacetrack_cdm_pc_min: Mapped[float | None] = mapped_column(nullable=True)
    notify_on_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    fleet: Mapped[Fleet] = relationship("Fleet")
    runs: Mapped[list[ScreeningRun]] = relationship("ScreeningRun", back_populates="schedule")


class ScreeningRun(Base):
    __tablename__ = "screening_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("screening_schedules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fleet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satellite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    computation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    schedule: Mapped[ScreeningSchedule | None] = relationship("ScreeningSchedule", back_populates="runs")
    fleet: Mapped[Fleet] = relationship("Fleet")
    alerts: Mapped[list[ConjunctionAlert]] = relationship("ConjunctionAlert", back_populates="screening_run")


class ConjunctionAlert(Base):
    __tablename__ = "conjunction_alerts"
    __table_args__ = (
        Index("ix_conjunction_alerts_sat_debris", "satellite_id", "debris_norad_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    satellite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    screening_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("screening_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    debris_norad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    debris_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tca: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pc: Mapped[float] = mapped_column(Float, nullable=False)
    miss_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    fleet: Mapped[Fleet] = relationship("Fleet")
    satellite: Mapped[Satellite] = relationship("Satellite")
    screening_run: Mapped[ScreeningRun | None] = relationship("ScreeningRun", back_populates="alerts")
