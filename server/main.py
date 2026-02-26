"""
Unified FastAPI server — runs the entire PathWise AI platform offline.
No Docker, Redis, or TimescaleDB required.
"""

from __future__ import annotations
import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.state import state, ActiveRoutingRule, SteeringEvent
from server.simulator import simulation_loop
from server.lstm_engine import prediction_loop
from server.sandbox import (
    validate_steering,
    serialize_report,
    record_report,
    get_sandbox_history,
    TOPOLOGY,
)


# ── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    sim_task = asyncio.create_task(simulation_loop())
    pred_task = asyncio.create_task(prediction_loop())
    ws_task = asyncio.create_task(scoreboard_broadcast_loop())
    yield
    sim_task.cancel()
    pred_task.cancel()
    ws_task.cancel()


app = FastAPI(
    title="PathWise AI — Offline Server",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ─────────────────────────────────────────

class LSTMToggleRequest(BaseModel):
    enabled: bool


class StatusResponse(BaseModel):
    status: str
    lstm_enabled: bool
    uptime_seconds: float
    tick_count: int
    active_links: list[str]


class SandboxValidationRequest(BaseModel):
    source_link: str
    target_link: str
    traffic_classes: list[str]


class ApplyRuleRequest(BaseModel):
    sandbox_report_id: str
    source_link: str
    target_link: str
    traffic_classes: list[str]


# ── REST Endpoints ──────────────────────────────────────────

@app.get("/api/v1/status")
async def get_status():
    return StatusResponse(
        status="running",
        lstm_enabled=state.lstm_enabled,
        uptime_seconds=time.time() - state.start_time,
        tick_count=state.tick_count,
        active_links=state.active_links,
    )


@app.post("/api/v1/admin/lstm-toggle")
async def toggle_lstm(req: LSTMToggleRequest):
    state.lstm_enabled = req.enabled
    return {"lstm_enabled": state.lstm_enabled, "message": f"LSTM {'enabled' if req.enabled else 'disabled'}"}


@app.get("/api/v1/admin/lstm-status")
async def lstm_status():
    return {"lstm_enabled": state.lstm_enabled}


@app.get("/api/v1/telemetry/links")
async def get_links():
    return {"links": state.active_links}


@app.get("/api/v1/telemetry/{link_id}")
async def get_telemetry(link_id: str, window: int = 60):
    points = state.get_latest_effective(link_id, window)
    return {
        "link_id": link_id,
        "points": [
            {
                "timestamp": p.timestamp,
                "latency_ms": round(p.latency_ms, 2),
                "jitter_ms": round(p.jitter_ms, 2),
                "packet_loss_pct": round(p.packet_loss_pct, 3),
                "bandwidth_util_pct": round(p.bandwidth_util_pct, 1),
                "rtt_ms": round(p.rtt_ms, 2),
            }
            for p in points
        ],
    }


@app.get("/api/v1/telemetry/{link_id}/raw")
async def get_raw_telemetry(link_id: str, window: int = 60):
    points = state.get_latest_telemetry(link_id, window)
    return {
        "link_id": link_id,
        "points": [
            {
                "timestamp": p.timestamp,
                "latency_ms": round(p.latency_ms, 2),
                "jitter_ms": round(p.jitter_ms, 2),
                "packet_loss_pct": round(p.packet_loss_pct, 3),
                "bandwidth_util_pct": round(p.bandwidth_util_pct, 1),
                "rtt_ms": round(p.rtt_ms, 2),
            }
            for p in points
        ],
    }


@app.get("/api/v1/predictions/all")
async def get_all_predictions():
    result = {}
    for link_id, pred in state.predictions.items():
        if pred:
            result[link_id] = _serialize_prediction(pred)
    return result


@app.get("/api/v1/predictions/{link_id}")
async def get_prediction(link_id: str):
    pred = state.predictions.get(link_id)
    if not pred:
        return {"error": "No prediction available yet"}
    return _serialize_prediction(pred)


@app.get("/api/v1/steering/history")
async def get_steering_history(limit: int = 50):
    events = list(state.steering_history)[:limit]
    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "action": e.action,
                "source_link": e.source_link,
                "target_link": e.target_link,
                "traffic_classes": e.traffic_classes,
                "confidence": round(e.confidence, 2),
                "reason": e.reason,
                "status": e.status,
                "lstm_enabled": e.lstm_enabled,
            }
            for e in events
        ]
    }


@app.get("/api/v1/metrics/comparison")
async def get_comparison_metrics():
    m_on = state.metrics_lstm_on
    m_off = state.metrics_lstm_off
    return {
        "lstm_on": {
            "avg_latency": round(m_on.avg_latency, 2),
            "avg_jitter": round(m_on.avg_jitter, 2),
            "avg_packet_loss": round(m_on.avg_packet_loss, 3),
            "proactive_steerings": m_on.proactive_steerings,
            "brownouts_avoided": m_on.brownouts_avoided,
        },
        "lstm_off": {
            "avg_latency": round(m_off.avg_latency, 2),
            "avg_jitter": round(m_off.avg_jitter, 2),
            "avg_packet_loss": round(m_off.avg_packet_loss, 3),
            "reactive_steerings": m_off.reactive_steerings,
            "brownouts_hit": m_off.brownouts_hit,
        },
    }


# ── Sandbox Endpoints ────────────────────────────────────────

@app.post("/api/v1/sandbox/validate")
async def sandbox_validate(req: SandboxValidationRequest):
    report = await validate_steering(
        source_link=req.source_link,
        target_link=req.target_link,
        traffic_classes=req.traffic_classes,
    )
    record_report(report)
    return serialize_report(report)


@app.get("/api/v1/sandbox/history")
async def sandbox_history(limit: int = 20):
    return {"reports": get_sandbox_history(limit)}


@app.get("/api/v1/sandbox/topology")
async def sandbox_topology():
    links_health = {}
    for link in TOPOLOGY["links"]:
        lid = link["link_id"]
        pred = state.predictions.get(lid)
        links_health[lid] = {
            "health_score": pred.health_score if pred else None,
            "brownout_active": state.brownout_active.get(lid, False),
        }
    return {"topology": TOPOLOGY, "links_health": links_health}


# ── Routing Rule Endpoints ───────────────────────────────────

@app.post("/api/v1/routing/apply")
async def apply_routing_rule(req: ApplyRuleRequest):
    import uuid as _uuid

    if req.source_link == req.target_link:
        return {"error": "Source and target must differ"}
    if req.source_link not in state.active_links or req.target_link not in state.active_links:
        return {"error": "Invalid link ID"}

    for existing in state.get_active_rules():
        if existing.source_link == req.source_link:
            return {"error": f"Traffic from {req.source_link} is already being diverted by rule {existing.id}"}

    rule = ActiveRoutingRule(
        id=str(_uuid.uuid4())[:8],
        source_link=req.source_link,
        target_link=req.target_link,
        traffic_classes=req.traffic_classes,
        applied_at=time.time(),
        sandbox_report_id=req.sandbox_report_id,
        status="active",
    )
    state.routing_rules.append(rule)

    evt = SteeringEvent(
        id=rule.id,
        timestamp=time.time(),
        action="SANDBOX_DEPLOY",
        source_link=req.source_link,
        target_link=req.target_link,
        traffic_classes=",".join(req.traffic_classes),
        confidence=1.0,
        reason=f"Sandbox-validated rule applied (report {req.sandbox_report_id[:8]})",
        status="deployed",
        lstm_enabled=state.lstm_enabled,
    )
    state.steering_history.appendleft(evt)

    return {
        "rule_id": rule.id,
        "status": "deployed",
        "source_link": rule.source_link,
        "target_link": rule.target_link,
        "traffic_classes": rule.traffic_classes,
        "message": f"Traffic rerouted: {rule.source_link} → {rule.target_link}",
    }


@app.get("/api/v1/routing/active")
async def get_active_rules():
    rules = state.get_active_rules()
    return {
        "rules": [
            {
                "id": r.id,
                "source_link": r.source_link,
                "target_link": r.target_link,
                "traffic_classes": r.traffic_classes,
                "applied_at": r.applied_at,
                "sandbox_report_id": r.sandbox_report_id,
                "status": r.status,
                "age_seconds": round(time.time() - r.applied_at, 1),
            }
            for r in rules
        ]
    }


@app.get("/api/v1/routing/all")
async def get_all_rules():
    return {
        "rules": [
            {
                "id": r.id,
                "source_link": r.source_link,
                "target_link": r.target_link,
                "traffic_classes": r.traffic_classes,
                "applied_at": r.applied_at,
                "sandbox_report_id": r.sandbox_report_id,
                "status": r.status,
                "age_seconds": round(time.time() - r.applied_at, 1),
            }
            for r in state.routing_rules
        ]
    }


@app.delete("/api/v1/routing/{rule_id}")
async def rollback_rule(rule_id: str):
    for r in state.routing_rules:
        if r.id == rule_id and r.status == "active":
            r.status = "rolled_back"

            evt = SteeringEvent(
                id=r.id + "-rb",
                timestamp=time.time(),
                action="SANDBOX_ROLLBACK",
                source_link=r.target_link,
                target_link=r.source_link,
                traffic_classes=",".join(r.traffic_classes),
                confidence=1.0,
                reason=f"Routing rule {r.id} rolled back — traffic restored to {r.source_link}",
                status="rolled_back",
                lstm_enabled=state.lstm_enabled,
            )
            state.steering_history.appendleft(evt)

            return {
                "rule_id": r.id,
                "status": "rolled_back",
                "message": f"Traffic restored to {r.source_link}",
            }
    return {"error": "Rule not found or already rolled back"}


def _serialize_prediction(pred):
    return {
        "link_id": pred.link_id,
        "health_score": pred.health_score,
        "confidence": round(pred.confidence, 3),
        "latency_forecast": [round(v, 2) for v in pred.latency_forecast],
        "jitter_forecast": [round(v, 2) for v in pred.jitter_forecast],
        "packet_loss_forecast": [round(v, 3) for v in pred.packet_loss_forecast],
        "timestamp": pred.timestamp,
    }


# ── WebSocket ───────────────────────────────────────────────

_ws_clients: set[WebSocket] = set()


@app.websocket("/ws/scoreboard")
async def websocket_scoreboard(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)


async def scoreboard_broadcast_loop():
    """Broadcast scoreboard updates at 1 Hz to all connected WebSocket clients."""
    while True:
        if _ws_clients:
            payload = _build_scoreboard_payload()
            msg = json.dumps(payload)
            dead = set()
            for ws in _ws_clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            _ws_clients.difference_update(dead)
        await asyncio.sleep(1.0)


def _build_scoreboard_payload() -> dict:
    links_data = {}
    for link_id in state.active_links:
        eff_points = state.get_latest_effective(link_id, 5)
        raw_points = state.get_latest_telemetry(link_id, 5)
        pred = state.predictions.get(link_id)

        if eff_points:
            latest = eff_points[-1]
            lat_vals = [p.latency_ms for p in eff_points]
            trend = "stable"
            if len(lat_vals) >= 3:
                diff = lat_vals[-1] - lat_vals[0]
                if diff > 5:
                    trend = "degrading"
                elif diff < -5:
                    trend = "improving"

            links_data[link_id] = {
                "health_score": pred.health_score if pred else 75,
                "confidence": pred.confidence if pred else 0.5,
                "latency_current": round(latest.latency_ms, 2),
                "jitter_current": round(latest.jitter_ms, 2),
                "packet_loss_current": round(latest.packet_loss_pct, 3),
                "bandwidth_util": round(latest.bandwidth_util_pct, 1),
                "latency_forecast": pred.latency_forecast[:10] if pred else [],
                "trend": trend,
                "brownout_active": state.brownout_active.get(link_id, False),
            }

        if raw_points:
            raw_latest = raw_points[-1]
            links_data[link_id]["raw_latency"] = round(raw_latest.latency_ms, 2)
            links_data[link_id]["raw_jitter"] = round(raw_latest.jitter_ms, 2)
            links_data[link_id]["raw_packet_loss"] = round(raw_latest.packet_loss_pct, 3)

    recent_events = list(state.steering_history)[:5]
    m_on = state.metrics_lstm_on
    m_off = state.metrics_lstm_off

    active_rules = [
        {
            "id": r.id,
            "source_link": r.source_link,
            "target_link": r.target_link,
            "traffic_classes": r.traffic_classes,
            "age_seconds": round(time.time() - r.applied_at, 1),
        }
        for r in state.get_active_rules()
    ]

    return {
        "type": "scoreboard_update",
        "timestamp": time.time(),
        "lstm_enabled": state.lstm_enabled,
        "links": links_data,
        "active_routing_rules": active_rules,
        "steering_events": [
            {
                "id": e.id,
                "action": e.action,
                "source_link": e.source_link,
                "target_link": e.target_link,
                "reason": e.reason,
                "confidence": round(e.confidence, 2),
                "status": e.status,
                "lstm_enabled": e.lstm_enabled,
                "timestamp": e.timestamp,
            }
            for e in recent_events
        ],
        "comparison": {
            "lstm_on": {
                "avg_latency": round(m_on.avg_latency, 2),
                "avg_jitter": round(m_on.avg_jitter, 2),
                "avg_packet_loss": round(m_on.avg_packet_loss, 3),
                "proactive_steerings": m_on.proactive_steerings,
                "brownouts_avoided": m_on.brownouts_avoided,
            },
            "lstm_off": {
                "avg_latency": round(m_off.avg_latency, 2),
                "avg_jitter": round(m_off.avg_jitter, 2),
                "avg_packet_loss": round(m_off.avg_packet_loss, 3),
                "reactive_steerings": m_off.reactive_steerings,
                "brownouts_hit": m_off.brownouts_hit,
            },
        },
    }
