"""Production-shaped large table response latency and health regression.

This test emits ``LARGE_TABLE_ROUND`` JSON records for the host-side
``scripts/benchmark_large_table_responses.py`` sampler.  The sampler correlates
those timestamps with API process and cgroup memory without giving the test
runner access to Docker or the API container's process namespace.
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from uuid import uuid4

import httpx
import pytest


pytestmark = pytest.mark.e2e

_ROW_COUNT = 1_500
_PAGE_SIZE = 500
_ROUNDS = 6
_SETTLE_SECONDS = 0.35
_MAX_QUERY_SECONDS = 2.0
_MAX_HEALTH_SECONDS = 0.5


def _production_shaped_row(index: int) -> dict:
    """Return a deterministic Ninja-state-shaped row of roughly 500 bytes."""
    now = "2026-09-10T16:09:36.123456+00:00"
    organization_id = index % 120
    location_id = index % 260
    current_ip = f"198.51.{index % 100}.{(index % 250) + 1}"
    return {
        "device_id": 100_000 + index,
        "system_name": f"workstation-{index:05d}",
        "node_class": "WINDOWS_WORKSTATION",
        "ninja_org_id": organization_id,
        "home_location_id": location_id,
        "current_ip": current_ip,
        "current_ip_since": now,
        "prev_ip": None,
        "baseline_ip": None,
        "stationary": False,
        "matched_site": None,
        "matched_org": None,
        "home_matched": False,
        "off_all_sites_since": now,
        "last_classification": "roaming_unknown",
        "last_seen": now,
        "updated_at": now,
        "ip_changed_this_run": False,
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def test_repeated_large_table_responses_keep_health_responsive(
    e2e_client,
    e2e_api_url,
    platform_admin,
) -> None:
    table_name = f"large_response_memory_{uuid4().hex[:8]}"
    create = e2e_client.post(
        "/api/tables",
        headers=platform_admin.headers,
        json={"name": table_name, "description": "large-response memory regression"},
    )
    assert create.status_code == 201, create.text
    table_id = create.json()["id"]

    documents = [
        {"id": str(100_000 + index), "data": _production_shaped_row(index)}
        for index in range(_ROW_COUNT)
    ]

    health_latencies: list[float] = []
    health_failures: list[str] = []
    health_lock = threading.Lock()
    stop_health = threading.Event()

    def probe_health() -> None:
        with httpx.Client(base_url=e2e_api_url, timeout=2.0) as client:
            while not stop_health.is_set():
                started = time.perf_counter()
                try:
                    response = client.get("/health")
                    elapsed = time.perf_counter() - started
                    with health_lock:
                        health_latencies.append(elapsed)
                        if response.status_code != 200:
                            health_failures.append(f"HTTP {response.status_code}")
                except Exception as exc:  # noqa: BLE001 - preserve benchmark evidence
                    with health_lock:
                        health_failures.append(type(exc).__name__)
                stop_health.wait(0.01)

    try:
        for start in range(0, len(documents), 750):
            seeded = e2e_client.post(
                f"/api/tables/{table_id}/documents/bulk-upsert",
                headers=platform_admin.headers,
                json={"documents": documents[start : start + 750]},
            )
            assert seeded.status_code == 200, seeded.text
            assert seeded.json() == {"count": min(750, len(documents) - start)}

        health_thread = threading.Thread(target=probe_health, daemon=True)
        health_thread.start()
        query_latencies: list[float] = []

        for round_index in range(_ROUNDS):
            round_started_at = time.time()
            health_start = len(health_latencies)
            round_latencies: list[float] = []
            response_bytes = 0
            for offset in range(0, _ROW_COUNT, _PAGE_SIZE):
                started = time.perf_counter()
                response = e2e_client.post(
                    f"/api/tables/{table_id}/documents/query",
                    headers=platform_admin.headers,
                    json={"limit": _PAGE_SIZE, "offset": offset},
                )
                elapsed = time.perf_counter() - started
                assert response.status_code == 200, response.text
                assert len(response.json()["documents"]) == _PAGE_SIZE
                round_latencies.append(elapsed)
                response_bytes += len(response.content)

            query_latencies.extend(round_latencies)
            stop_health.wait(_SETTLE_SECONDS)
            with health_lock:
                round_health = health_latencies[health_start:]
                round_failures = list(health_failures)

            record = {
                "round": round_index + 1,
                "round_started_at_unix": round_started_at,
                "settled_at_unix": time.time(),
                "query_ms": [round(value * 1_000, 2) for value in round_latencies],
                "response_bytes": response_bytes,
                "health_samples": len(round_health),
                "health_max_ms": round(max(round_health, default=0.0) * 1_000, 2),
                "health_failures": len(round_failures),
            }
            print(f"LARGE_TABLE_ROUND {json.dumps(record, sort_keys=True)}", flush=True)

        stop_health.set()
        health_thread.join(timeout=3.0)

        assert not health_failures, f"health probe failures: {health_failures}"
        assert health_latencies, "continuous health probe recorded no samples"
        assert max(query_latencies) < _MAX_QUERY_SECONDS, (
            f"large response exceeded {_MAX_QUERY_SECONDS}s: "
            f"max={max(query_latencies):.3f}s median={statistics.median(query_latencies):.3f}s"
        )
        assert _percentile(health_latencies, 0.99) < _MAX_HEALTH_SECONDS, (
            f"health p99 exceeded {_MAX_HEALTH_SECONDS}s during large responses: "
            f"p99={_percentile(health_latencies, 0.99):.3f}s "
            f"max={max(health_latencies):.3f}s"
        )
    finally:
        stop_health.set()
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)
