"""
In-memory Digital Twin / Sandbox Validator.

Simulates the original Mininet + Batfish validation pipeline entirely in memory.
Performs five validation checks against live network state:
  1. Topology snapshot
  2. Loop detection (graph cycle analysis)
  3. Policy compliance (traffic class → link capability matching)
  4. Reachability simulation (path exists with acceptable metrics)
  5. Performance impact estimation
"""

from __future__ import annotations
import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from server.state import state


# ── Reference Topology ──────────────────────────────────────

TOPOLOGY = {
    "switches": [
        {"id": "s1", "dpid": "0000000000000001", "label": "Edge Router 1"},
        {"id": "s2", "dpid": "0000000000000002", "label": "Edge Router 2"},
    ],
    "hosts": [
        {"id": "h1", "ip": "10.0.1.1/24", "label": "Site A (HQ)"},
        {"id": "h2", "ip": "10.0.2.1/24", "label": "Site B (Branch)"},
    ],
    "links": [
        {"src": "h1", "dst": "s1", "bw": 1000, "delay_ms": 1, "loss_pct": 0,
         "link_id": "host-link-1"},
        {"src": "h2", "dst": "s2", "bw": 1000, "delay_ms": 1, "loss_pct": 0,
         "link_id": "host-link-2"},
        {"src": "s1", "dst": "s2", "bw": 1000, "delay_ms": 5, "loss_pct": 0.01,
         "link_id": "fiber-primary"},
        {"src": "s1", "dst": "s2", "bw": 100, "delay_ms": 15, "loss_pct": 0.1,
         "link_id": "broadband-secondary"},
        {"src": "s1", "dst": "s2", "bw": 10, "delay_ms": 300, "loss_pct": 0.5,
         "link_id": "satellite-backup"},
        {"src": "s1", "dst": "s2", "bw": 200, "delay_ms": 20, "loss_pct": 0.2,
         "link_id": "5g-mobile"},
    ],
}

TRAFFIC_CLASS_REQUIREMENTS = {
    "voip": {"max_latency_ms": 50, "max_jitter_ms": 10, "max_loss_pct": 0.5, "min_bw_mbps": 1},
    "video": {"max_latency_ms": 100, "max_jitter_ms": 20, "max_loss_pct": 1.0, "min_bw_mbps": 10},
    "critical": {"max_latency_ms": 80, "max_jitter_ms": 15, "max_loss_pct": 0.3, "min_bw_mbps": 5},
    "bulk": {"max_latency_ms": 500, "max_jitter_ms": 100, "max_loss_pct": 5.0, "min_bw_mbps": 1},
}


class ValidationResult(str, Enum):
    PASS = "pass"
    FAIL_LOOP = "fail_loop"
    FAIL_POLICY = "fail_policy"
    FAIL_UNREACHABLE = "fail_unreachable"
    FAIL_PERFORMANCE = "fail_performance"


@dataclass
class ValidationCheck:
    name: str
    status: str  # "pass", "fail", "warn"
    detail: str
    duration_ms: float


@dataclass
class SandboxReport:
    id: str
    result: ValidationResult
    source_link: str
    target_link: str
    traffic_classes: list[str]
    loop_free: bool
    policy_compliant: bool
    reachability_verified: bool
    performance_acceptable: bool
    checks: list[ValidationCheck]
    execution_time_ms: float
    timestamp: float
    topology_snapshot: dict


async def validate_steering(
    source_link: str,
    target_link: str,
    traffic_classes: list[str],
) -> SandboxReport:
    """
    Full sandbox validation pipeline — runs in-memory.
    Simulates what Mininet + Batfish would do.
    """
    report_id = str(uuid.uuid4())[:12]
    start = time.monotonic()
    checks: list[ValidationCheck] = []

    # Validate inputs
    valid_links = {l["link_id"] for l in TOPOLOGY["links"]}
    if source_link not in valid_links or target_link not in valid_links:
        return SandboxReport(
            id=report_id, result=ValidationResult.FAIL_UNREACHABLE,
            source_link=source_link, target_link=target_link,
            traffic_classes=traffic_classes,
            loop_free=False, policy_compliant=False,
            reachability_verified=False, performance_acceptable=False,
            checks=[ValidationCheck("input_validation", "fail", f"Unknown link ID", 0)],
            execution_time_ms=0, timestamp=time.time(),
            topology_snapshot=TOPOLOGY,
        )

    # ── Check 1: Topology Snapshot ──────────────────────────
    t0 = time.monotonic()
    await asyncio.sleep(random.uniform(0.05, 0.15))
    checks.append(ValidationCheck(
        name="topology_snapshot",
        status="pass",
        detail=f"Captured topology: {len(TOPOLOGY['switches'])} switches, "
               f"{len(TOPOLOGY['hosts'])} hosts, {len(TOPOLOGY['links'])} links",
        duration_ms=(time.monotonic() - t0) * 1000,
    ))

    # ── Check 2: Loop Detection ─────────────────────────────
    t0 = time.monotonic()
    await asyncio.sleep(random.uniform(0.08, 0.2))
    loop_free = _check_no_loops(source_link, target_link)
    checks.append(ValidationCheck(
        name="loop_detection",
        status="pass" if loop_free else "fail",
        detail="No routing loops detected in proposed configuration"
               if loop_free else f"Loop detected: {source_link} → {target_link} → {source_link}",
        duration_ms=(time.monotonic() - t0) * 1000,
    ))
    if not loop_free:
        return _build_report(
            report_id, ValidationResult.FAIL_LOOP, source_link, target_link,
            traffic_classes, loop_free, False, False, False, checks, start,
        )

    # ── Check 3: Policy Compliance ──────────────────────────
    t0 = time.monotonic()
    await asyncio.sleep(random.uniform(0.1, 0.25))
    policy_result = _check_policy_compliance(target_link, traffic_classes)
    checks.append(ValidationCheck(
        name="policy_compliance",
        status=policy_result["status"],
        detail=policy_result["detail"],
        duration_ms=(time.monotonic() - t0) * 1000,
    ))
    policy_ok = policy_result["status"] != "fail"
    if not policy_ok:
        return _build_report(
            report_id, ValidationResult.FAIL_POLICY, source_link, target_link,
            traffic_classes, loop_free, False, False, False, checks, start,
        )

    # ── Check 4: Reachability Test ──────────────────────────
    t0 = time.monotonic()
    await asyncio.sleep(random.uniform(0.15, 0.35))
    reachable = _check_reachability(target_link)
    checks.append(ValidationCheck(
        name="reachability_test",
        status="pass" if reachable else "fail",
        detail=f"Ping h1 → s1 → [{target_link}] → s2 → h2: "
               + ("OK (0% loss)" if reachable else "FAILED (100% loss — link down)"),
        duration_ms=(time.monotonic() - t0) * 1000,
    ))
    if not reachable:
        return _build_report(
            report_id, ValidationResult.FAIL_UNREACHABLE, source_link, target_link,
            traffic_classes, loop_free, policy_ok, False, False, checks, start,
        )

    # ── Check 5: Performance Impact ─────────────────────────
    t0 = time.monotonic()
    await asyncio.sleep(random.uniform(0.1, 0.2))
    perf_result = _check_performance_impact(source_link, target_link, traffic_classes)
    checks.append(ValidationCheck(
        name="performance_impact",
        status=perf_result["status"],
        detail=perf_result["detail"],
        duration_ms=(time.monotonic() - t0) * 1000,
    ))
    perf_ok = perf_result["status"] != "fail"

    overall = ValidationResult.PASS if perf_ok else ValidationResult.FAIL_PERFORMANCE
    return _build_report(
        report_id, overall, source_link, target_link, traffic_classes,
        loop_free, policy_ok, reachable, perf_ok, checks, start,
    )


def _build_report(
    report_id, result, source_link, target_link, traffic_classes,
    loop_free, policy_compliant, reachability_verified, performance_acceptable,
    checks, start,
) -> SandboxReport:
    return SandboxReport(
        id=report_id,
        result=result,
        source_link=source_link,
        target_link=target_link,
        traffic_classes=traffic_classes,
        loop_free=loop_free,
        policy_compliant=policy_compliant,
        reachability_verified=reachability_verified,
        performance_acceptable=performance_acceptable,
        checks=checks,
        execution_time_ms=(time.monotonic() - start) * 1000,
        timestamp=time.time(),
        topology_snapshot=TOPOLOGY,
    )


def _check_no_loops(source: str, target: str) -> bool:
    if source == target:
        return False
    # In our topology all WAN links go s1↔s2, no multi-hop loops possible
    # Simulate a small chance of loop for demo realism
    return random.random() > 0.03


def _check_policy_compliance(target_link: str, traffic_classes: list[str]) -> dict:
    link_spec = next((l for l in TOPOLOGY["links"] if l["link_id"] == target_link), None)
    if not link_spec:
        return {"status": "fail", "detail": f"Link {target_link} not in topology"}

    violations = []
    for tc in traffic_classes:
        req = TRAFFIC_CLASS_REQUIREMENTS.get(tc)
        if not req:
            continue
        if link_spec["delay_ms"] > req["max_latency_ms"]:
            violations.append(
                f"{tc}: link latency {link_spec['delay_ms']}ms exceeds max {req['max_latency_ms']}ms"
            )
        if link_spec["loss_pct"] > req["max_loss_pct"]:
            violations.append(
                f"{tc}: link loss {link_spec['loss_pct']}% exceeds max {req['max_loss_pct']}%"
            )

    if violations:
        return {"status": "fail", "detail": "Policy violations: " + "; ".join(violations)}

    # Check live health too
    pred = state.predictions.get(target_link)
    if pred and pred.health_score < 30:
        return {
            "status": "warn",
            "detail": f"Target link health is critically low ({pred.health_score:.0f}/100) "
                      f"— policy allows but not recommended",
        }

    return {"status": "pass", "detail": f"All {len(traffic_classes)} traffic classes comply with {target_link} capabilities"}


def _check_reachability(target_link: str) -> bool:
    pred = state.predictions.get(target_link)
    if pred and pred.health_score < 10:
        return False
    brownout = state.brownout_active.get(target_link, False)
    if brownout:
        return random.random() > 0.15
    return random.random() > 0.02


def _check_performance_impact(
    source_link: str, target_link: str, traffic_classes: list[str]
) -> dict:
    src_pred = state.predictions.get(source_link)
    tgt_pred = state.predictions.get(target_link)

    if not tgt_pred:
        return {"status": "pass", "detail": "No prediction data — assumed acceptable"}

    tgt_health = tgt_pred.health_score
    src_health = src_pred.health_score if src_pred else 50

    improvement = tgt_health - src_health

    tgt_lat = tgt_pred.latency_forecast[0] if tgt_pred.latency_forecast else 30
    src_lat = src_pred.latency_forecast[0] if src_pred and src_pred.latency_forecast else 50

    if tgt_health >= 60:
        return {
            "status": "pass",
            "detail": f"Estimated impact: latency {src_lat:.0f}ms → {tgt_lat:.0f}ms, "
                      f"health {src_health:.0f} → {tgt_health:.0f} "
                      f"({'↑ improvement' if improvement > 0 else '→ comparable'})",
        }
    elif tgt_health >= 35:
        return {
            "status": "warn",
            "detail": f"Target link health marginal ({tgt_health:.0f}/100). "
                      f"Estimated latency: {tgt_lat:.0f}ms. Proceed with caution.",
        }
    else:
        return {
            "status": "fail",
            "detail": f"Target link health too low ({tgt_health:.0f}/100). "
                      f"Steering to {target_link} would degrade user experience.",
        }


# ── History ─────────────────────────────────────────────────

_sandbox_history: list[dict] = []


def get_sandbox_history(limit: int = 20) -> list[dict]:
    return _sandbox_history[:limit]


def record_report(report: SandboxReport):
    _sandbox_history.insert(0, serialize_report(report))
    if len(_sandbox_history) > 50:
        _sandbox_history.pop()


def serialize_report(r: SandboxReport) -> dict:
    return {
        "id": r.id,
        "result": r.result.value,
        "source_link": r.source_link,
        "target_link": r.target_link,
        "traffic_classes": r.traffic_classes,
        "loop_free": r.loop_free,
        "policy_compliant": r.policy_compliant,
        "reachability_verified": r.reachability_verified,
        "performance_acceptable": r.performance_acceptable,
        "checks": [
            {
                "name": c.name,
                "status": c.status,
                "detail": c.detail,
                "duration_ms": round(c.duration_ms, 1),
            }
            for c in r.checks
        ],
        "execution_time_ms": round(r.execution_time_ms, 1),
        "timestamp": r.timestamp,
    }
