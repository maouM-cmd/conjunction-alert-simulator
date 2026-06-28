"""Database engine and session management."""

from __future__ import annotations

import os
from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    if url:
        return url.strip()
    return None


def reset_engine_for_tests() -> None:
    """Reset cached engine (pytest only)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine | None:
    global _engine, _SessionLocal
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        connect_args: dict = {}
        engine_kwargs: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            if url.endswith(":memory:") or url.rstrip("/").endswith(":memory:"):
                engine_kwargs["poolclass"] = StaticPool
        _engine = create_engine(url, connect_args=connect_args, **engine_kwargs)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    get_engine()
    return _SessionLocal


def is_database_configured() -> bool:
    return get_database_url() is not None


def require_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    if factory is None:
        raise HTTPException(
            status_code=503,
            detail="データベースが設定されていません。DATABASE_URL を設定してください。",
        )
    db = factory()
    try:
        yield db
    finally:
        db.close()
