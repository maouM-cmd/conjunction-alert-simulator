"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.routers import conjunctions, health, maneuver, orbit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Conjunction Alert Simulator",
    description="衛星 TLE からデブリ接近を検出し、3D 可視化と回避試算を行う API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(conjunctions.router)
app.include_router(orbit.router)
app.include_router(maneuver.router)

if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Conjunction Alert Simulator API",
        "docs": "/docs",
        "app": "/app/",
    }
