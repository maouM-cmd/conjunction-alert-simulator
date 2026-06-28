"""Alert webhook API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.webhook_notifier import send_test_webhook

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class WebhookTestResponse(BaseModel):
    sent: bool
    alert_count: int
    degraded: bool
    message: str


@router.post("/webhook/test", response_model=WebhookTestResponse)
def webhook_test() -> WebhookTestResponse:
    result = send_test_webhook()
    if not result.sent and "未設定" in result.message:
        raise HTTPException(status_code=503, detail=result.message)
    return WebhookTestResponse(
        sent=result.sent,
        alert_count=result.alert_count,
        degraded=result.degraded,
        message=result.message,
    )
