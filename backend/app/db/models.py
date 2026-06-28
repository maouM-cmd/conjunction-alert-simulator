"""SQLAlchemy ORM models for fleet registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
