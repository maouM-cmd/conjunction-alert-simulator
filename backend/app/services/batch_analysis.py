"""Batch conjunction analysis for multiple satellites."""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from backend.app.services.analysis import ConjunctionAnalysisResult, run_conjunction_analysis
from backend.app.services.tle_fetcher import CatalogMeta, fetch_debris_catalog, set_last_provider_label
from backend.app.services.tle_parser import parse_tle

MAX_SATELLITES = 25


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
    parallel: bool
    worker_count: int


def _batch_worker(args: tuple) -> ConjunctionAnalysisResult:
    """Top-level worker for ProcessPoolExecutor (must be picklable)."""
    (
        tle_text,
        duration_days,
        threshold_km,
        step_minutes,
        sigma_km,
        debris_catalog,
        catalog_meta,
        use_advanced_pc,
        use_anisotropic_cov,
    ) = args
    return run_conjunction_analysis(
        tle_text,
        duration_days=duration_days,
        threshold_km=threshold_km,
        step_minutes=step_minutes,
        sigma_km=sigma_km,
        use_advanced_pc=use_advanced_pc,
        use_anisotropic_cov=use_anisotropic_cov,
        debris_catalog=debris_catalog,
        catalog_meta=catalog_meta,
    )


def _resolve_worker_count(satellite_count: int, max_workers: int | None) -> int:
    if max_workers is not None:
        return max(1, min(max_workers, satellite_count))
    env_val = os.environ.get("BATCH_MAX_WORKERS")
    if env_val:
        try:
            return max(1, min(int(env_val), satellite_count))
        except ValueError:
            pass
    cpu = os.cpu_count() or 4
    return max(1, min(cpu, satellite_count))


def _build_summary(results: list[ConjunctionAnalysisResult]) -> BatchSummary:
    total_events = 0
    highest_pc = 0.0
    highest_sat: str | None = None
    highest_deb: str | None = None
    for result in results:
        total_events += len(result.events)
        for event in result.events:
            if event.pc > highest_pc:
                highest_pc = event.pc
                highest_sat = result.satellite.name
                highest_deb = event.debris_name
    return BatchSummary(
        satellite_count=len(results),
        total_events=total_events,
        highest_pc=highest_pc,
        highest_pc_satellite=highest_sat,
        highest_pc_debris=highest_deb,
    )


def run_batch_conjunction_analysis(
    satellite_tles: list[str],
    duration_days: float = 7.0,
    threshold_km: float = 5.0,
    step_minutes: int = 1,
    sigma_km: float | None = None,
    parallel: bool = True,
    max_workers: int | None = None,
    use_advanced_pc: bool = False,
    use_anisotropic_cov: bool = False,
) -> BatchAnalysisResult:
    if not satellite_tles:
        raise ValueError("衛星 TLE が1件以上必要です。")
    if len(satellite_tles) > MAX_SATELLITES:
        raise ValueError(f"衛星数は最大 {MAX_SATELLITES} 件です。")

    t0 = time.perf_counter()
    debris_catalog, catalog_meta = fetch_debris_catalog()
    set_last_provider_label(catalog_meta.provider)

    worker_count = _resolve_worker_count(len(satellite_tles), max_workers)
    use_parallel = parallel and len(satellite_tles) > 1 and worker_count > 1

    if use_parallel:
        task_args = [
            (
                tle_text,
                duration_days,
                threshold_km,
                step_minutes,
                sigma_km,
                debris_catalog,
                catalog_meta,
                use_advanced_pc,
                use_anisotropic_cov,
            )
            for tle_text in satellite_tles
        ]
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(_batch_worker, task_args))
    else:
        worker_count = 1
        results = [
            run_conjunction_analysis(
                tle_text,
                duration_days=duration_days,
                threshold_km=threshold_km,
                step_minutes=step_minutes,
                sigma_km=sigma_km,
                use_advanced_pc=use_advanced_pc,
                use_anisotropic_cov=use_anisotropic_cov,
                debris_catalog=debris_catalog,
                catalog_meta=catalog_meta,
            )
            for tle_text in satellite_tles
        ]

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return BatchAnalysisResult(
        results=results,
        summary=_build_summary(results),
        computation_time_ms=elapsed_ms,
        tle_provider=catalog_meta.provider,
        parallel=use_parallel,
        worker_count=worker_count if use_parallel else 1,
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
