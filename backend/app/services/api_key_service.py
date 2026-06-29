"""API Key management (Phase 9E)."""

from __future__ import annotations

import hashlib
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ApiKey
from backend.app.services import fleet_service

KEY_PREFIX = "cas_"


class ApiKeyServiceError(Exception):
    pass


class NotFoundError(ApiKeyServiceError):
    pass


def hash_api_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def verify_api_key(db: Session, plain: str) -> ApiKey | None:
    if not plain:
        return None
    key_hash = hash_api_key(plain)
    return db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.active.is_(True))
    ).scalar_one_or_none()


def count_active_keys(db: Session, fleet_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.fleet_id == fleet_id, ApiKey.active.is_(True))
        ).scalar_one()
    )


def create_api_key(
    db: Session,
    *,
    fleet_id: uuid.UUID,
    name: str,
) -> tuple[ApiKey, str]:
    fleet_service.get_fleet(db, fleet_id)
    plain = generate_api_key()
    record = ApiKey(
        fleet_id=fleet_id,
        name=name,
        key_prefix=plain[:8],
        key_hash=hash_api_key(plain),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, plain


def list_api_keys(db: Session, fleet_id: uuid.UUID) -> list[ApiKey]:
    fleet_service.get_fleet(db, fleet_id)
    return list(
        db.execute(
            select(ApiKey)
            .where(ApiKey.fleet_id == fleet_id, ApiKey.active.is_(True))
            .order_by(ApiKey.created_at.desc())
        )
        .scalars()
        .all()
    )


def revoke_api_key(db: Session, fleet_id: uuid.UUID, key_id: uuid.UUID) -> None:
    record = db.get(ApiKey, key_id)
    if record is None or not record.active or record.fleet_id != fleet_id:
        raise NotFoundError("API Key が見つかりません。")
    record.active = False
    db.commit()
