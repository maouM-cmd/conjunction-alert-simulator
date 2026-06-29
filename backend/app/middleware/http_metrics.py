"""HTTP request metrics middleware (Phase 10B)."""

from __future__ import annotations

from backend.app.metrics_registry import record_http_request
from backend.app.services import api_availability_service
from backend.app.services.api_slo_fleet_context import fleet_id_from_scope


class HttpMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        method = scope.get("method", "GET")
        record_http_request(method, status_code)
        api_availability_service.record_http_status(
            status_code,
            fleet_id=fleet_id_from_scope(scope),
        )
