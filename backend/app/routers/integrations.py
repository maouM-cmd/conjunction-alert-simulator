"""Third-party integration webhooks (Phase 10P)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import require_db
from backend.app.services.pagerduty_inbound_service import (
    handle_pagerduty_event,
    pagerduty_inbound_enabled,
    verify_pagerduty_signature,
)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


class PagerDutyWebhookResponse(BaseModel):
    processed: bool
    alert_id: str | None = None
    status: str | None = None
    noop: bool = False
    message: str = ""


@router.post("/pagerduty/webhook", response_model=PagerDutyWebhookResponse)
async def pagerduty_webhook(
    request: Request,
    db: Session = Depends(require_db),
) -> PagerDutyWebhookResponse:
    if not pagerduty_inbound_enabled():
        raise HTTPException(
            status_code=503,
            detail="PagerDuty inbound sync は無効です（PAGERDUTY_INBOUND_SYNC_ENABLED）。",
        )
    body = await request.body()
    if not verify_pagerduty_signature(dict(request.headers), body):
        raise HTTPException(status_code=401, detail="PagerDuty 署名が無効です。")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="JSON が不正です。") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON が不正です。")

    result = handle_pagerduty_event(db, payload)
    return PagerDutyWebhookResponse(
        processed=result.processed,
        alert_id=str(result.alert_id) if result.alert_id else None,
        status=result.status,
        noop=result.noop,
        message=result.message,
    )
