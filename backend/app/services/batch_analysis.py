"""Batch conjunction analysis for multiple satellites."""

from __future__ import annotations

import time
from dataclasses import dataclass

from backend.app.services.analysis import ConjunctionAnalysisResult, run_conjunction_analysis
from backend.app.services.tle_fetcher import CatalogMeta, fetch_debris_catalog, set_last_provider_label
from backend.app.services.tle_parser import parse_tle

MAX_SATELLITES = 10


@dataclass(frozen=True)
class BatchSummary:
    satellite_count: int
    total_events: int
    highest_pc: float
    highest_pc_satellite: str | None
    highest_pc_debris: str | None


@dataclass(frozen=True)
class BatchAnalysisResult:
    results: list[ConjunctionAnalysisResult]
    summary: BatchSummary
    computation_time_ms: int
    tle_provider: str


def run_batch_conjunction_analysis(
    satellite_tles: list[str],
    duration_days: float = 7.0,
    threshold_km: float = 5.0,
    step_minutes: int = 1,
    sigma_km: float | None = None,
) -> BatchAnalysisResult:
    if not satellite_tles:
        raise ValueError("衛星 TLE が1件以上必要です。")
    if len(satellite_tles) > MAX_SATELLITES:
        raise ValueError(f"衛星数は最大 {MAX_SATELLITES} 件です。")

    t0 = time.perf_counter()
    debris_catalog, catalog_meta = fetch_debris_catalog()
    set_last_provider_label(catalog_meta.provider)

    results: list[ConjunctionAnalysisResult] = []
    total_events = 0
    highest_pc = 0.0
    highest_sat: str | None = None
    highest_deb: str | None = None

    for tle_text in satellite_tles:
        result = run_conjunction_analysis(
            tle_text,
            duration_days=duration_days,
            threshold_km=threshold_km,
            step_minutes=step_minutes,
            sigma_km=sigma_km,
            debris_catalog=debris_catalog,
            catalog_meta=catalog_meta,
        )
        results.append(result)
        total_events += len(result.events)
        for event in result.events:
            if event.pc > highest_pc:
                highest_pc = event.pc
                highest_sat = result.satellite.name
                highest_deb = event.debris_name

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return BatchAnalysisResult(
        results=results,
        summary=BatchSummary(
            satellite_count=len(results),
            total_events=total_events,
            highest_pc=highest_pc,
            highest_pc_satellite=highest_sat,
            highest_pc_debris=highest_deb,
        ),
        computation_time_ms=elapsed_ms,
        tle_provider=catalog_meta.provider,
    )


def parse_multi_tle_block(text: str) -> list[str]:
    """Split --- separated TLE blocks."""
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    if len(blocks) == 1:
        blocks = [b.strip() for b in text.split("\n\n") if b.strip() and "1 " in b]
    validated: list[str] = []
    for block in blocks:
        parse_tle(block)
        validated.append(block)
    return validated
