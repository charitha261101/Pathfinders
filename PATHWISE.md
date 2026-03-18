# CLAUDE.md — PathWise AI Build Specification
## Team Pathfinders | COSC6370-001 Advanced Software Engineering

> This file is the authoritative build instruction set for Claude Code.
> Read this file completely before writing any code. Every architectural
> decision, requirement, and constraint below derives directly from the
> project's PVD (v1.2), SRS (v1.0), and Project Plan (v1.0).

---

## 0. PROJECT OVERVIEW

**PathWise AI** is an intelligent, vendor-agnostic SD-WAN management platform
that transforms enterprise network management from reactive to predictive. It
uses LSTM neural networks to forecast WAN link degradation 30–60 seconds in
advance and autonomously reroutes mission-critical traffic via SDN controller
integration — achieving hitless handoff with zero packet loss.

**Target Users:** SMEs, MSPs, Healthcare Facilities, Educational Institutions,
Retail Chains — organizations needing enterprise-grade network reliability
without proprietary hardware or CLI expertise.

**Core problem solved:** The "switching gap" — where packets drop during the
window between link degradation and reactive failover.

---

## 1. REPOSITORY STRUCTURE

Scaffold the following directory layout before writing any implementation code.

```
pathwise-ai/
├── CLAUDE.md                          ← this file
├── docker-compose.yml
├── .env.example
├── README.md
│
├── services/
│   ├── telemetry-engine/              ← WP-4: LSTM Predictive Telemetry Engine
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── ingestor.py            ← SNMP/NetFlow/streaming telemetry ingestion
│   │   │   ├── lstm_model.py          ← LSTM architecture + attention mechanism
│   │   │   ├── health_scorer.py       ← 0–100 health score generation
│   │   │   ├── predictor.py           ← inference service, 1-second polling loop
│   │   │   └── alert_manager.py       ← threshold alerts + suppression logic
│   │   └── tests/
│   │       ├── test_ingestor.py
│   │       ├── test_lstm_model.py
│   │       └── test_health_scorer.py
│   │
│   ├── traffic-steering/              ← WP-5: Autonomous Traffic Steering
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── steering_engine.py     ← hitless handoff orchestrator
│   │   │   ├── sdn_client.py          ← OpenDaylight + ONOS northbound API client
│   │   │   ├── flow_table_manager.py  ← OpenFlow 1.3 flow table builder
│   │   │   └── session_manager.py     ← TCP/VoIP session state preservation
│   │   └── tests/
│   │       ├── test_steering_engine.py
│   │       └── test_sdn_client.py
│   │
│   ├── digital-twin/                  ← WP-6: Digital Twin Validation Sandbox
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── sandbox_api.py         ← validation request handler (FastAPI)
│   │   │   ├── mininet_builder.py     ← virtual topology mirroring
│   │   │   ├── batfish_validator.py   ← loop detection + firewall policy checks
│   │   │   └── audit_logger.py        ← tamper-evident validation audit trail
│   │   └── tests/
│   │       ├── test_sandbox_api.py
│   │       └── test_batfish_validator.py
│   │
│   ├── ibn-interface/                 ← WP-7: Intent-Based Management Interface
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── nlp_engine.py          ← natural language → policy intent parser
│   │   │   ├── yang_translator.py     ← policy intent → YANG/NETCONF payload
│   │   │   ├── policy_manager.py      ← CRUD for network policies
│   │   │   └── ibn_api.py             ← FastAPI routes for IBN operations
│   │   └── tests/
│   │       ├── test_nlp_engine.py
│   │       └── test_yang_translator.py
│   │
│   ├── backend-api/                   ← WP-9: Backend API and Integration Layer
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py                ← FastAPI application entry point
│   │   │   ├── auth.py                ← JWT auth + bcrypt credential hashing
│   │   │   ├── rbac.py                ← role-based access control enforcement
│   │   │   ├── routes/
│   │   │   │   ├── telemetry.py
│   │   │   │   ├── steering.py
│   │   │   │   ├── sandbox.py
│   │   │   │   ├── policy.py
│   │   │   │   └── health.py
│   │   │   ├── models/
│   │   │   │   ├── user.py
│   │   │   │   ├── telemetry.py
│   │   │   │   ├── policy.py
│   │   │   │   └── audit.py
│   │   │   └── redis_broker.py        ← Redis pub/sub for inter-service messaging
│   │   └── tests/
│   │       ├── test_auth.py
│   │       └── test_routes.py
│   │
│   └── dashboard/                     ← WP-7+8: React Frontend
│       ├── Dockerfile
│       ├── package.json
│       ├── public/
│       └── src/
│           ├── App.tsx
│           ├── components/
│           │   ├── HealthScoreboard/  ← WP-8: Multi-Link Health Scoreboard
│           │   │   ├── ScoreboardPanel.tsx
│           │   │   ├── LinkHealthCard.tsx
│           │   │   └── PredictionChart.tsx    ← D3.js time-series chart
│           │   ├── TelemetryMonitor/
│           │   │   ├── TelemetryDashboard.tsx
│           │   │   └── MetricGraph.tsx        ← D3.js latency/jitter/loss graph
│           │   ├── PolicyManager/
│           │   │   ├── IBNInterface.tsx       ← natural language input panel
│           │   │   ├── PolicyList.tsx
│           │   │   └── PolicyConfirmDialog.tsx
│           │   ├── AuditLog/
│           │   │   └── AuditLogTable.tsx
│           │   └── Auth/
│           │       └── LoginPage.tsx
│           ├── hooks/
│           │   ├── useWebSocket.ts
│           │   └── useTelemetry.ts
│           └── api/
│               └── client.ts
│
├── ml/                                ← LSTM model training pipeline
│   ├── data_generation/
│   │   ├── mininet_telemetry_gen.py   ← synthetic data via Mininet/WSL2
│   │   └── scenario_configs/
│   ├── training/
│   │   ├── train_lstm.py
│   │   ├── hyperparameter_tuning.py
│   │   └── evaluate_model.py
│   └── models/
│       └── .gitkeep                   ← trained model artifacts stored here
│
├── infra/
│   ├── timescaledb/
│   │   └── init.sql                   ← schema: telemetry, health_scores, audit_log
│   ├── redis/
│   │   └── redis.conf
│   └── nginx/
│       └── nginx.conf
│
└── docs/
    └── api/
        └── openapi.yaml
```

---

## 2. TECHNOLOGY STACK

Use exactly the following. Do not substitute alternatives without flagging it.

| Layer | Technology | Notes |
|---|---|---|
| Prediction Engine | Python 3.11, PyTorch 2.x (LSTM) | LSTM with attention mechanism |
| Time-Series DB | TimescaleDB (PostgreSQL extension) | Telemetry + health score storage |
| Message Broker | Redis 7.x (pub/sub) | Inter-service real-time events |
| Backend API | FastAPI + Uvicorn | All microservices expose REST APIs |
| SDN Controllers | OpenDaylight (ODL), ONOS | Northbound REST API integration |
| Network Emulation | Mininet (via WSL2 on Windows) | Digital Twin + training data gen |
| Policy Validation | Batfish | Loop detection + firewall compliance |
| Frontend | React 18 + TypeScript | Dashboard SPA |
| Data Visualization | D3.js v7 | Health scoreboard + telemetry graphs |
| Auth | JWT + bcrypt | Credential hashing (one-way) |
| Encryption in transit | TLS 1.3 | All API communication |
| Encryption at rest | AES-256 | Telemetry data + credentials |
| Containerization | Docker + Docker Compose | All services containerized |

---

## 3. FUNCTIONAL REQUIREMENTS CHECKLIST

Implement every requirement below. Each is tagged with its SRS ID. Mark `[x]`
as you complete each one. Do not mark complete until the requirement has a
corresponding passing test.

### 3.1 Software Requirements (Req-Func-Sw)

- [ ] **Req-Func-Sw-1** — Ingest telemetry (latency, jitter, packet loss) from all WAN links at ≥ 1 Hz polling frequency.
- [ ] **Req-Func-Sw-2** — Use trained LSTM model to forecast WAN link degradation 30–60 seconds ahead.
- [ ] **Req-Func-Sw-3** — Generate a 0–100 predictive health score per WAN link from real-time + historical telemetry.
- [ ] **Req-Func-Sw-4** — Trigger autonomous traffic steering when health score drops below an administrator-configurable threshold.
- [ ] **Req-Func-Sw-5** — Integrate with OpenDaylight and ONOS northbound APIs to read and modify flow tables.
- [ ] **Req-Func-Sw-6** — Execute hitless handoff: pre-emptively reroute VoIP, video, and financial traffic from degrading to stable link with zero packet loss.
- [ ] **Req-Func-Sw-7** — Maintain all active session states during link handoff transitions (no session termination).
- [ ] **Req-Func-Sw-8** — Auto-submit every AI routing change to the Digital Twin Sandbox before any production deployment.
- [ ] **Req-Func-Sw-9** — Use Mininet to construct a virtual replica of the live network topology per validation request.
- [ ] **Req-Func-Sw-10** — Use Batfish to verify every routing change is loop-free and firewall-policy-compliant before approval.
- [ ] **Req-Func-Sw-11** — Provide an IBN interface accepting natural language policy commands with no CLI knowledge required.
- [ ] **Req-Func-Sw-12** — Translate natural language policy commands into valid YANG/NETCONF payloads and submit to the SDN controller.
- [ ] **Req-Func-Sw-13** — Display a real-time Multi-Link Health Scoreboard showing health scores for Fiber, Satellite, 5G, and Broadband links.
- [ ] **Req-Func-Sw-14** — Display LSTM prediction confidence level and human-readable reasoning for every automated path switch on the scoreboard.
- [ ] **Req-Func-Sw-15** — Enforce role-based access control (RBAC) for: Network Administrator, IT Manager, MSP Technician, Generalist IT Staff, End User.
- [ ] **Req-Func-Sw-16** — Authenticate all users with secure credential login; store all passwords using one-way cryptographic hashing (bcrypt).
- [ ] **Req-Func-Sw-17** — Send real-time alert notifications via dashboard panel and email when any link health score drops below threshold.
- [ ] **Req-Func-Sw-18** — Maintain a persistent, tamper-evident audit log recording all AI routing decisions, health scores, confidence levels, sandbox results, and routing changes.
- [ ] **Req-Func-Sw-19** — Support concurrent monitoring and management of ≥ 100 network sites from a single dashboard.
- [ ] **Req-Func-Sw-20** — Accept telemetry from devices via SNMP v2c+ and NetFlow v9+.
- [ ] **Req-Func-Sw-21** — Provide exportable performance reports (PDF and CSV) including historical health scores, prediction accuracy metrics, and traffic steering event logs.

### 3.2 Hardware Requirements (Req-Func-Hw)

These inform deployment configuration — implement as Docker resource limits and
deployment documentation:

- [ ] **Req-Func-Hw-1** — System requires ≥ 32 GB RAM server (document in `docker-compose.yml` resource constraints).
- [ ] **Req-Func-Hw-2** — All managed network devices must support OpenFlow 1.3+.
- [ ] **Req-Func-Hw-3** — Deployable on commodity x86-64 hardware; no proprietary appliances required.
- [ ] **Req-Func-Hw-4** — Requires ≥ 1 TB SSD for TimescaleDB telemetry retention and LSTM training dataset storage.
- [ ] **Req-Func-Hw-5** — Requires ≥ 100 Mbps dedicated management network connection.
- [ ] **Req-Func-Hw-6** — Server requires ≥ 8 CPU cores (document in compose resource constraints).
- [ ] **Req-Func-Hw-7** — Support deployment on VMware ESXi and KVM hypervisors.
- [ ] **Req-Func-Hw-8** — Dashboard renders correctly at ≥ 1920×1080 resolution.

---

## 4. QUALITY REQUIREMENTS — HARD CONSTRAINTS

These are non-negotiable performance and security targets. Every feature must
be benchmarked against these before marking it complete.

| SRS ID | Attribute | Target | How to Verify |
|---|---|---|---|
| Req-Qual-Perf-1 | LSTM Prediction Accuracy | ≥ 90% (MSE against ground truth) | `ml/training/evaluate_model.py` output |
| Req-Qual-Perf-2 | End-to-end traffic steering | < 50 ms (trigger → SDN flow table updated) | Integration test with timer assertions |
| Req-Qual-Perf-3 | Digital Twin full validation cycle | < 5 seconds | Sandbox API response time test |
| Req-Qual-Perf-4 | IBN dashboard UI response | < 2 seconds under normal load | Frontend performance test |
| Req-Qual-Sec-1 | Data in transit | TLS 1.3+ on all connections | nginx TLS config + cert validation |
| Req-Qual-Sec-2 | Data at rest | AES-256 for telemetry + credentials | DB encryption config check |
| Req-Qual-Sec-3 | Healthcare deployments | HIPAA-compliant audit log + access controls | Audit log completeness test |
| Req-Qual-Use-1 | No CLI required | All admin tasks via IBN interface | Usability test checklist |
| Req-Qual-Rel-1 | Platform availability | ≥ 99.9% annually | Docker health checks + restart policies |
| Req-Qual-Rel-2 | Automated failover | Single component failure must not halt platform | Docker restart:always + redundancy test |
| Req-Qual-Rel-3 | DB backups | Every 24 hours, geographically separate | Backup cron job in compose |
| Req-Qual-Scal-1 | Concurrent sites | ≥ 100 sites, no degradation | Load test with 100-site simulation |

---

## 5. USE CASE IMPLEMENTATION MAP

Map each use case (from SRS Appendix B) to the services and routes that
implement it:

| UC ID | Use Case | Primary Service | API Route |
|---|---|---|---|
| UC-1 | Monitor Network Telemetry | `backend-api`, `telemetry-engine` | `GET /api/telemetry/{link_id}` |
| UC-2 | Predict Link Degradation | `telemetry-engine` (automated) | Internal event → Redis pub/sub |
| UC-3 | Execute Traffic Steering | `traffic-steering` (automated) | Internal trigger from sandbox pass |
| UC-4 | Validate Routing Change | `digital-twin` (automated) | `POST /api/sandbox/validate` |
| UC-5 | Manage Network Policy | `ibn-interface`, `backend-api` | `POST /api/policy` |
| UC-6 | Authenticate User | `backend-api` | `POST /api/auth/login` |

### UC-1: Monitor Network Telemetry
- Dashboard polls `GET /api/telemetry/{link_id}?window=30m` via WebSocket stream.
- TimescaleDB query must return results within 200ms for any 30-minute window.
- If a link is offline: return cached last-known values + `status: "offline"` flag.
- If requested time range exceeds retention: return max available + warning flag.
- Supports ≥ 10 concurrent admin sessions without performance degradation.

### UC-2: Predict Link Degradation
- Fully automated. Triggered every 1 second per link by the telemetry polling loop.
- On malformed telemetry: log error, discard from LSTM buffer, continue with last valid point.
- Alert suppression: deduplicate alerts for the same link within a configurable window (default: 5s).
- Alert channels: dashboard notification panel + email.

### UC-3: Execute Traffic Steering
- Only initiates after a `PASSED` sandbox validation result is received.
- Flow table update must complete within **50ms** of receiving the validation result.
- On SDN API error: retry up to 3 times with exponential backoff; alert admin if all fail.
- If target link degrades during handoff: abort, re-evaluate all links by health score, restart validation cycle.
- Audit log entry must capture: prediction trigger score, confidence level, routing change, timestamp.

### UC-4: Validate Routing Change
- Full cycle (Mininet topology instantiation + Batfish analysis) must complete in **< 5 seconds**.
- On routing loop detected: immediately reject, log violation details, alert admin.
- On Batfish policy violation: reject, log specific rule violated, alert admin.
- Irrelevant assumption in SRS ("The desired item is available for purchase") — disregard that line.

### UC-5: Manage Network Policy
- NLP engine displays interpreted policy summary before any deployment action.
- On ambiguous NLP parse: show error, provide rephrasing suggestions, do NOT attempt deployment.
- On SDN controller deployment error: roll back, notify user, preserve previous policy state.
- Audit log entry on every policy change: user, timestamp, old policy, new policy.

### UC-6: Authenticate User
- Display generic error message on failed login (never reveal whether email or password was wrong).
- Lock account after **5 consecutive failed attempts**.
- All credential transmission exclusively over TLS 1.3.
- On locked account: display instructions for contacting system administrator.

---

## 6. DATA ARCHITECTURE

### 6.1 TimescaleDB Schema

```sql
-- Run via infra/timescaledb/init.sql

-- Raw telemetry hypertable (1-second granularity)
CREATE TABLE wan_telemetry (
    time          TIMESTAMPTZ NOT NULL,
    link_id       UUID        NOT NULL,
    site_id       UUID        NOT NULL,
    latency_ms    FLOAT       NOT NULL,
    jitter_ms     FLOAT       NOT NULL,
    packet_loss   FLOAT       NOT NULL,  -- percentage 0.0–100.0
    link_type     VARCHAR(20) NOT NULL   -- FIBER, SATELLITE, 5G, BROADBAND
);
SELECT create_hypertable('wan_telemetry', 'time');
CREATE INDEX ON wan_telemetry (link_id, time DESC);

-- Predicted health scores
CREATE TABLE health_scores (
    time            TIMESTAMPTZ NOT NULL,
    link_id         UUID        NOT NULL,
    health_score    FLOAT       NOT NULL,  -- 0.0–100.0
    confidence      FLOAT       NOT NULL,  -- 0.0–1.0
    prediction_window_s INT     NOT NULL   -- 30 or 60
);
SELECT create_hypertable('health_scores', 'time');

-- Tamper-evident audit log
CREATE TABLE audit_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      VARCHAR(50) NOT NULL,  -- STEERING, VALIDATION, POLICY_CHANGE, AUTH
    actor           VARCHAR(100),          -- user id or "SYSTEM"
    link_id         UUID,
    health_score    FLOAT,
    confidence      FLOAT,
    validation_result VARCHAR(10),         -- PASSED, FAILED
    routing_change  JSONB,
    policy_change   JSONB,
    details         TEXT,
    checksum        VARCHAR(64)            -- SHA-256 of row content for tamper evidence
);

-- Users and RBAC
CREATE TABLE users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50)  NOT NULL,  -- NETWORK_ADMIN, IT_MANAGER, MSP_TECH, IT_STAFF, END_USER
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    failed_attempts INT          NOT NULL DEFAULT 0,
    locked_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Network policies
CREATE TABLE policies (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    natural_language TEXT        NOT NULL,
    yang_config     JSONB        NOT NULL,
    created_by      UUID         REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);
```

### 6.2 LSTM Training Data

- **Source:** Synthetic network telemetry generated via Mininet on WSL2.
- **Target size:** ≥ 10M training points.
- **Format:** Parquet files in `ml/data_generation/output/`.
- **Scenarios to generate:**
  - Gradual link degradation (latency brownout)
  - Sudden packet loss spikes
  - Jitter oscillation patterns
  - Multi-link simultaneous degradation
  - Link recovery after failover
- **Sequence length for LSTM input:** 60 timesteps (60 seconds of 1 Hz data).
- **Prediction targets:** latency, jitter, and packet loss at t+30s and t+60s.

### 6.3 Redis Pub/Sub Channels

```
pathwise:telemetry:{link_id}        ← raw telemetry stream
pathwise:alerts:{site_id}           ← health score threshold breach alerts
pathwise:validation:request         ← routing change proposals to sandbox
pathwise:validation:result          ← sandbox PASSED/FAILED results
pathwise:steering:trigger           ← steering engine activation events
pathwise:dashboard:updates          ← WebSocket broadcast to dashboard clients
```

---

## 7. LSTM MODEL SPECIFICATION

### Architecture

```python
# Implement in services/telemetry-engine/src/lstm_model.py

class PathWiseLSTM(nn.Module):
    """
    LSTM with attention mechanism for WAN link health prediction.
    Input:  [batch, seq_len=60, features=3]  (latency, jitter, packet_loss)
    Output: [batch, 2, features=3]           (predictions at t+30s, t+60s)
    """
    # Layer specification:
    # - 2x stacked LSTM layers, hidden_size=128
    # - Dropout=0.2 between LSTM layers
    # - Bahdanau attention over LSTM output sequence
    # - Linear projection head → 2 * 3 outputs
    # - Health score mapping: weighted combination of normalized predictions → 0–100
```

### Training

- Optimizer: Adam, lr=1e-3
- Loss: MSE on (latency_t+30, jitter_t+30, pkt_loss_t+30, latency_t+60, jitter_t+60, pkt_loss_t+60)
- Batch size: 256
- Epochs: 50 with early stopping (patience=5)
- Train/val/test split: 70/15/15
- **Acceptance criterion:** MSE on test set must yield ≥ 90% prediction accuracy (Req-Qual-Perf-1).

### Inference Service

- Must complete one inference pass in < 1 second (to stay within the 1 Hz telemetry polling loop).
- Load model from `ml/models/pathwise_lstm.pt` on startup.
- Expose health check endpoint at `GET /health`.

---

## 8. SDN INTEGRATION SPECIFICATION

### OpenDaylight (ODL) Client

```python
# Implement in services/traffic-steering/src/sdn_client.py
# Base URL: http://{ODL_HOST}:8181/restconf/
# Auth: Basic auth via environment variables ODL_USER / ODL_PASS

# Required methods:
# - get_flow_tables(node_id: str) → list[FlowEntry]
# - update_flow_entry(node_id: str, flow: FlowEntry) → bool
# - delete_flow_entry(node_id: str, flow_id: str) → bool
# - get_topology() → NetworkTopology
```

### ONOS Client

```python
# Base URL: http://{ONOS_HOST}:8181/onos/v1/
# Auth: Basic auth via environment variables ONOS_USER / ONOS_PASS

# Required methods (mirror ODL interface):
# - get_flow_tables, update_flow_entry, delete_flow_entry, get_topology
```

### Hitless Handoff Sequence

1. Receive PASSED validation result from sandbox.
2. Pre-compute new flow table entries for target alternative link.
3. Atomically apply flow table update via SDN northbound API.
4. Simultaneously preserve all active TCP/VoIP session states.
5. Confirm updated flow table state via SDN API read-back.
6. Write audit log entry.
7. Publish `pathwise:dashboard:updates` to Redis.
8. Entire sequence must complete in **< 50 ms** (Req-Qual-Perf-2).

---

## 9. DIGITAL TWIN SANDBOX SPECIFICATION

### Validation API

```python
# POST /api/sandbox/validate
# Input:  RoutingChangeProposal { link_from, link_to, flow_entries, site_topology }
# Output: ValidationResult { status: "PASSED"|"FAILED", loop_check, policy_check, details }
# SLA:    < 5 seconds end-to-end (Req-Qual-Perf-3)
```

### Validation Steps (must run in this order)

1. Instantiate Mininet topology mirroring current live network.
2. Apply proposed routing change to virtual topology.
3. Run routing loop detection (DFS-based cycle detection on the flow graph).
4. Submit config to Batfish for firewall ACL and policy compliance check.
5. If either check fails → FAILED result, log violation, alert admin.
6. If both pass → PASSED result, forward change payload to traffic steering module.

### Batfish Integration

```python
# Use pybatfish library
# Network snapshot: generated from current SDN controller topology export
# Required assertions:
# - No routing loops (hasRoute assertions)
# - No firewall policy violations (reachability assertions)
# - No ACL violations
```

---

## 10. INTENT-BASED NETWORKING (IBN) SPECIFICATION

### NLP Engine

Use a template-matching + embedding similarity approach (no external LLM API calls).
Define a controlled vocabulary of supported intent patterns:

```python
INTENT_PATTERNS = [
    # Priority patterns
    r"prioritize (?P<high_traffic>\w+) (?:traffic )?over (?P<low_traffic>\w+)",
    r"block (?P<blocked_traffic>\w+) (?:traffic )?(?:from|on) (?P<scope>.+)",
    r"limit (?P<traffic_type>\w+) to (?P<bandwidth>\d+\s*(?:Mbps|Gbps))",
    r"route (?P<traffic_type>\w+) via (?P<link_type>\w+)",
    # Add patterns for all common SME network policy use cases
]
```

### YANG/NETCONF Translation

Map parsed intent to YANG module `ietf-diffserv-classifier` and
`ietf-qos-policy` for traffic prioritization, and to relevant
OpenDaylight/ONOS flow rule schemas for routing policies.

---

## 11. REACT DASHBOARD SPECIFICATION

### Key Screens (from SDD)

1. **Login Page** — email + password, TLS enforced, generic error on failure.
2. **Telemetry Monitor** — real-time D3.js line graphs, per-link selector, time range filter.
3. **Multi-Link Health Scoreboard** — health score cards (0–100) per link, color-coded (green ≥ 80, yellow 50–79, red < 50), LSTM confidence display, reasoning tooltip.
4. **Policy Manager (IBN Interface)** — natural language input field, interpreted policy preview before Apply, active policy list.
5. **Audit Log** — paginated table of all events, filterable by type/date/actor.
6. **Reports** — export historical health scores, prediction accuracy, and traffic steering events as PDF or CSV.

### WebSocket

All real-time dashboard updates (health scores, alerts) delivered via WebSocket
from `backend-api`. Subscribe to `pathwise:dashboard:updates` Redis channel
and broadcast to connected clients.

---

## 12. ENVIRONMENT VARIABLES

Create `.env.example` with all of the following (no real secrets committed):

```env
# Database
TIMESCALEDB_URL=postgresql://pathwise:password@timescaledb:5432/pathwise
REDIS_URL=redis://redis:6379/0

# SDN Controllers
ODL_HOST=localhost
ODL_PORT=8181
ODL_USER=admin
ODL_PASS=admin
ONOS_HOST=localhost
ONOS_PORT=8181
ONOS_USER=onos
ONOS_PASS=rocks

# Auth
JWT_SECRET=<generate-256-bit-secret>
JWT_EXPIRY_MINUTES=60

# Encryption
ENCRYPTION_KEY=<AES-256-key>

# LSTM Model
MODEL_PATH=/app/models/pathwise_lstm.pt
PREDICTION_WINDOW_S=60
HEALTH_SCORE_THRESHOLD=70

# Alerts
ALERT_EMAIL_SMTP_HOST=
ALERT_EMAIL_FROM=
ALERT_SUPPRESSION_WINDOW_S=5

# Mininet (WSL2 path on Windows)
MININET_WSL_COMMAND=wsl mininet
BATFISH_HOST=localhost
BATFISH_PORT=9997
```

---

## 13. DOCKER COMPOSE

```yaml
# docker-compose.yml — scaffold all services
version: '3.9'
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    restart: always
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: pathwise
    volumes:
      - ./infra/timescaledb/init.sql:/docker-entrypoint-initdb.d/init.sql
      - timescale_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 8G

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./infra/redis/redis.conf:/etc/redis/redis.conf

  backend-api:
    build: ./services/backend-api
    restart: always
    ports: ["8000:8000"]
    depends_on: [timescaledb, redis]
    env_file: .env

  telemetry-engine:
    build: ./services/telemetry-engine
    restart: always
    depends_on: [timescaledb, redis]
    env_file: .env

  traffic-steering:
    build: ./services/traffic-steering
    restart: always
    depends_on: [redis, digital-twin]
    env_file: .env

  digital-twin:
    build: ./services/digital-twin
    restart: always
    depends_on: [redis]
    env_file: .env

  ibn-interface:
    build: ./services/ibn-interface
    restart: always
    depends_on: [backend-api, redis]
    env_file: .env

  dashboard:
    build: ./services/dashboard
    restart: always
    ports: ["3000:80"]
    depends_on: [backend-api]

  nginx:
    image: nginx:alpine
    ports: ["443:443", "80:80"]
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./infra/nginx/certs:/etc/nginx/certs
    depends_on: [backend-api, dashboard]

volumes:
  timescale_data:
```

---

## 14. TESTING REQUIREMENTS

Every service must have unit tests. The following integration tests are
mandatory before marking the build complete:

| Test Case ID | What to Test | Acceptance Criterion |
|---|---|---|
| Test-Case-1 | Telemetry ingestion at 1 Hz | ≥ 1 row/sec written to TimescaleDB |
| Test-Case-2 | LSTM prediction accuracy | ≥ 90% on held-out test set (MSE) |
| Test-Case-3 | Health score threshold alert | Alert fires within 1 polling cycle |
| Test-Case-4 | SDN flow table modification | ODL + ONOS APIs return 200 on update |
| Test-Case-5 | End-to-end hitless handoff | < 50 ms, zero packet loss confirmed |
| Test-Case-6 | Session state preservation | No TCP session dropped during handoff |
| Test-Case-7 | LSTM inference within 1s | Single inference < 1000 ms |
| Test-Case-8 | Sandbox full validation cycle | < 5 seconds total |
| Test-Case-9 | Batfish loop detection | Correctly rejects a loop-introducing change |
| Test-Case-10 | IBN NLP parsing | Common intents parsed with > 90% accuracy |
| Test-Case-11 | YANG/NETCONF translation | Generated payload accepted by SDN controller |
| Test-Case-12 | Health Scoreboard renders | All link types display at 1920×1080 |
| Test-Case-13 | Confidence + reasoning display | Shows on every automated path switch |
| Test-Case-14 | RBAC enforcement | Each role can only access permitted routes |
| Test-Case-15 | Auth credential hashing | Passwords stored as bcrypt hash, never plaintext |
| Test-Case-16 | Email alert delivery | Alert email sent on threshold breach |
| Test-Case-17 | Audit log completeness | All event types produce tamper-evident entries |
| Test-Case-18 | 100-site scalability | No degradation with 100 simulated sites |
| Test-Case-19 | Commodity hardware deploy | Deploys successfully on x86-64 Docker host |
| Test-Case-20 | VMware/KVM deploy | Docker containers run in virtualized environment |
| Test-Case-21 | Service restart resilience | Each service restarts and reconnects automatically |
| Test-Case-22 | TLS 1.3 enforcement | Connections on < TLS 1.3 are rejected |

---

## 15. WINDOWS-SPECIFIC NOTES (WSL2)

- Mininet must be invoked via WSL2. Use `subprocess` with `wsl` prefix:
  ```python
  subprocess.run(["wsl", "sudo", "mn", "--topo=linear,3"], ...)
  ```
- Batfish runs as a Docker container; no WSL2 dependency.
- All Python services run natively in Docker containers on Windows.
- LSTM training pipeline (`ml/`) runs in WSL2 for Mininet-based data generation.
- Ensure Docker Desktop is configured to use WSL2 backend.

---

## 16. BUILD ORDER

Build and validate in this order to respect service dependencies:

1. `infra/` — TimescaleDB schema, Redis config, nginx TLS
2. `services/backend-api/` — auth, RBAC, all REST routes, WebSocket
3. `services/telemetry-engine/` — ingestion → LSTM inference → health scoring → alerts
4. `services/digital-twin/` — Mininet builder + Batfish validator + sandbox API
5. `services/traffic-steering/` — ODL/ONOS clients + hitless handoff logic
6. `services/ibn-interface/` — NLP engine + YANG translator + policy manager
7. `services/dashboard/` — React SPA: login, telemetry, scoreboard, policy, audit, reports
8. `ml/` — data generation, LSTM training pipeline, model evaluation
9. Integration tests across all services
10. `docker-compose.yml` — full stack bring-up and end-to-end test

---

## 17. DEFINITION OF DONE

A feature is considered **done** when:

1. Implementation satisfies all linked SRS requirements (see Section 3).
2. All quality targets in Section 4 are met and measured.
3. Unit tests pass with ≥ 80% code coverage for that service.
4. Relevant integration test cases from Section 14 pass.
5. No hardcoded secrets or credentials in any committed file.
6. Docker container builds without errors.
7. API endpoints are documented in `docs/api/openapi.yaml`.

---

*Generated from: PVD v1.2 (02/15/26), SRS v1.0 (03/29/26), Project Plan v1.0 (02/24/26)*
*Team Pathfinders — Vineeth Reddy Kodakandla, Meghana Nalluri, Bharadwaj Jakkula, Sricharitha Katta*
