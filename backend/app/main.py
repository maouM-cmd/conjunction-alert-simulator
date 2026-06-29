"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.middleware.http_metrics import HttpMetricsMiddleware
from backend.app.routers import alerts, auth, batch, cdm, conjunctions, fleets, health, integrations, maneuver, metrics, ops, orbit, screening

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

FRONTEND_DIR = PROJECT_ROOT / "frontend"
SAMPLES_DIR = PROJECT_ROOT / "samples"

app = FastAPI(
    title="Conjunction Alert Simulator",
    description="衛星 TLE からデブリ接近を検出し、3D 可視化と回避試算を行う API",
    version="1.39.0",
)

app.add_middleware(HttpMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(auth.router)
app.include_router(fleets.router)
app.include_router(screening.router)
app.include_router(ops.router)
app.include_router(conjunctions.router)
app.include_router(alerts.router)
app.include_router(integrations.router)
app.include_router(batch.router)
app.include_router(cdm.router)
app.include_router(orbit.router)
app.include_router(maneuver.router)

if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if SAMPLES_DIR.is_dir():
    app.mount("/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Conjunction Alert Simulator API",
        "docs": "/docs",
        "app": "/app/",
    }
