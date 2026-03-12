# PathWise AI

**Intelligent, Vendor-Agnostic SD-WAN Management Platform**

*Team Pathfinders — COSC6370-001 Advanced Software Engineering*

PathWise AI transforms enterprise WAN management from **reactive to predictive**. A trained LSTM neural network forecasts WAN link degradation **30–60 seconds in advance**, every routing change is validated in a digital-twin sandbox in **under 5 seconds**, and traffic is autonomously rerouted via SDN flow-table updates in **under 50 ms** — achieving hitless handoff with **zero packet loss**.

It eliminates the *"switching gap"* — the window between link degradation and reactive failover — that plagues conventional SD-WAN appliances, and does so without proprietary hardware, vendor lock-in, or CLI expertise.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem & Solution](#2-problem--solution)
3. [Key Features](#3-key-features)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Repository Layout](#6-repository-layout)
7. [Backend Modules — Deep Dive](#7-backend-modules--deep-dive)
8. [REST & WebSocket API](#8-rest--websocket-api)
9. [Frontend Dashboard (UI Details)](#9-frontend-dashboard-ui-details)
10. [LSTM Prediction Engine](#10-lstm-prediction-engine)
11. [Digital Twin Sandbox](#11-digital-twin-sandbox)
12. [Intent-Based Networking (IBN)](#12-intent-based-networking-ibn)
13. [Traffic Shaping & Application QoS](#13-traffic-shaping--application-qos)
14. [Authentication & RBAC](#14-authentication--rbac)
15. [Alerts & Audit Logging](#15-alerts--audit-logging)
16. [Reports & Exports](#16-reports--exports)
17. [Telemetry Sources & Collectors](#17-telemetry-sources--collectors)
18. [Reference Network Topology](#18-reference-network-topology)
19. [Database Schema (TimescaleDB)](#19-database-schema-timescaledb)
20. [Configuration & Environment Variables](#20-configuration--environment-variables)
21. [Installation & Local Development](#21-installation--local-development)
22. [Docker Compose Deployment](#22-docker-compose-deployment)
23. [Integration Points (SDN, Mininet, Batfish, SMTP, OS QoS)](#23-integration-points)
24. [Settings & Admin Controls](#24-settings--admin-controls)
25. [Quality Targets & Test Cases](#25-quality-targets--test-cases)
26. [Security & Compliance](#26-security--compliance)
27. [Project Status](#27-project-status)
28. [Team & Source Documents](#28-team--source-documents)

---

## 1. Project Overview

| Attribute | Value |
|---|---|
| **Project Name** | PathWise AI |
| **Version** | 2.0.0 |
| **Type** | AI-driven SD-WAN management platform |
| **Course** | COSC6370-001 — Advanced Software Engineering |
| **Team** | Pathfinders |
| **Target Users** | SMEs, MSPs, Healthcare, Education, Retail |
| **Core Innovation** | Predictive failover with sandbox-validated hitless handoff |
| **Deployment Model** | Containerized (Docker), x86-64, on-prem or virtualized |
| **License Context** | Academic / educational |

---

## 2. Problem & Solution

### Problem
Traditional SD-WAN failover is **reactive**: a link is declared "failed" *after* packets are already being lost. The interval between degradation onset and failover ("switching gap") drops voice calls, breaks video conferences, and stalls financial transactions. Existing solutions also require:
- Proprietary appliances locked to single vendors
- CLI expertise for configuration
- Manual policy translation from business intent to network rules
- Reactive monitoring without predictive intelligence

### Solution
PathWise AI sits above the SDN control plane and adds:
- **Predictive intelligence** — LSTM forecasts degradation 30–60 s ahead
- **Validated automation** — every change passes a digital-twin sandbox first
- **Vendor neutrality** — works with OpenDaylight + ONOS via standard REST/NETCONF
- **Plain English control** — natural-language intents replace CLI configuration
- **App-aware QoS** — OS-level policies for 18+ named applications

---

## 3. Key Features

### Predictive Intelligence
- LSTM forecasting of latency, jitter, packet loss at **t+30 s** and **t+60 s** horizons
- **0–100 health score** per WAN link, refreshed every second
- **Confidence + reasoning** displayed for every automated decision
- **Brownout detection** before user-facing impact
- LSTM ON/OFF A/B comparison metrics built into the dashboard

### Autonomous Traffic Steering
- Hitless handoff with **< 50 ms** end-to-end steering latency
- Pre-emptive rerouting of VoIP, video, critical, and bulk traffic
- TCP/VoIP **session-state preservation** during link transitions
- One-click **rollback** of any deployed routing rule
- Steering is gated on a **passing sandbox validation** — never blind

### Digital Twin Validation Sandbox
- **5-stage** validation pipeline: topology snapshot → loop detection → policy compliance → reachability → performance impact
- Runs entirely **in-memory** (no Mininet boot wait)
- Full validation cycle in **< 5 seconds** (typical < 100 ms)
- Per-check pass / warn / fail report with timing
- Reference reports stored for replay and audit

### Intent-Based Networking
- Natural-language intents: *"Prioritize Zoom over Netflix on fiber"*
- 11 supported intent actions
- Real-time **compliance monitoring** loop
- **Auto-steering** when intents are violated
- Pause / resume / delete lifecycle controls
- YANG/NETCONF payload generation

### Multi-Link Health Scoreboard
- Live monitoring of **Fiber, Broadband, Satellite, 5G** (and optional Wi-Fi) links
- Color-coded cards: **green (≥80), yellow (50–79), red (<50)**
- Real-time latency / jitter / loss / bandwidth-utilization values
- 10-point latency forecast sparkline
- Trend indicators: **degrading / stable / improving**
- Brownout indicator badge

### Application-Level QoS
- 18+ predefined app profiles (Zoom, Teams, YouTube, Netflix, Discord, etc.)
- **Windows** (`New-NetQosPolicy`) and **Linux** (`tc`) integration
- Priority classes: `CRITICAL`, `HIGH`, `NORMAL`, `LOW`, `BLOCKED`
- *"Prioritize App-A over App-B"* semantics that translate to real OS rules

### Security, Compliance & Operations
- JWT (HS256) + bcrypt authentication
- 5-role RBAC enforced on every endpoint
- Account lockout after **5 failed attempts**
- TLS 1.3 enforced via nginx reverse proxy
- AES-256 encryption at rest
- **HIPAA-compliant** SHA-256 chained tamper-evident audit log
- Real-time WebSocket dashboard (1 Hz)
- Email + dashboard alert delivery with suppression windows
- PDF + CSV exports for health, steering, and audit data
- 100+ concurrent site support

---

## 4. System Architecture

PathWise AI is a **unified FastAPI backend** (`server/`) plus a **React 18 + TypeScript SPA** (`frontend/`), with Docker Compose orchestrating supporting infrastructure.

```
┌──────────────────────────────────────────────────────────────────┐
│                    React 18 + TypeScript SPA                     │
│   Login · Dashboard · Simulation · Sandbox · IBN Console ·       │
│   Audit Log · Reports · Admin Panel                              │
│             (Vite · Tailwind · Recharts · Framer Motion)         │
└────────────────────┬─────────────────────────────────────────────┘
                     │ HTTPS / WebSocket  (nginx + TLS 1.3)
┌────────────────────▼─────────────────────────────────────────────┐
│                     FastAPI Backend (server/)                    │
│ ┌──────────────┬────────────┬─────────────┬──────────────────┐   │
│ │ LSTM Engine  │  Sandbox   │ IBN Engine  │  Auth + RBAC     │   │
│ │ (1 Hz infer) │ (5-stage)  │(NLP + YANG) │  (JWT/bcrypt)    │   │
│ ├──────────────┼────────────┼─────────────┼──────────────────┤   │
│ │  Collectors  │ Audit (SHA)│ Alerts(SMTP)│  Reports (PDF)   │   │
│ │ sim/live/    │ tamper-    │ + dashboard │  Traffic Shaper  │   │
│ │ hybrid       │ evident    │             │  (Win/Linux QoS) │   │
│ └──────────────┴────────────┴─────────────┴──────────────────┘   │
│              In-memory state.py (deques + dicts)                 │
└──────┬─────────────────────┬───────────────────┬─────────────────┘
       │                     │                   │
┌──────▼──────┐       ┌──────▼─────┐     ┌───────▼────────┐
│ TimescaleDB │       │   Redis 7  │     │  OpenDaylight  │
│  (telemetry │       │  (pub/sub) │     │   / ONOS       │
│  + audit +  │       └────────────┘     │  Mininet       │
│  policies)  │                          │  Batfish       │
└─────────────┘                          └────────────────┘
```

### Data Flow Lifecycle
1. **Collectors** push telemetry → `state.telemetry[link_id]` deque (300-point rolling window)
2. **LSTM engine** runs inference every 1 s → `state.predictions[link_id]`
3. **Alerts module** checks each new prediction against threshold → emits notifications
4. **IBN monitor loop** evaluates active intents against current state → triggers auto-steering
5. **Steering candidate** is sent to **sandbox validator** for 5-stage check
6. On PASS, routing rule is applied (timer asserts < 50 ms execution)
7. **Audit log** records the change with SHA-256 chain
8. **WebSocket broadcast loop** pushes scoreboard updates at 1 Hz to all connected clients

---

## 5. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| **Backend Framework** | FastAPI + Uvicorn | latest |
| **Language (backend)** | Python | 3.11+ |
| **Prediction** | PyTorch (LSTM + attention) | 2.x |
| **Time-Series DB** | TimescaleDB on PostgreSQL | 16 |
| **Message Broker** | Redis | 7-alpine |
| **SDN Controllers** | OpenDaylight, ONOS | latest |
| **Network Emulation** | Mininet (via WSL2 on Windows) | latest |
| **Policy Validator** | Batfish | latest |
| **Frontend Framework** | React + TypeScript | 18.2 / 5.3 |
| **Build Tool** | Vite | 8.0.5 |
| **State Management** | Zustand | 4.4.7 |
| **Charts** | Recharts | 2.10 |
| **Routing** | React Router | 6.21 |
| **Animation** | Framer Motion | 11.0 |
| **Icons** | Lucide React | 0.312 |
| **Styling** | Tailwind CSS | 3.4 |
| **HTTP Client** | Axios | 1.6 |
| **Auth** | PyJWT (HS256) + bcrypt | latest |
| **Encryption** | TLS 1.3 (transit), AES-256 (rest) | — |
| **Containerization** | Docker, Docker Compose | 3.9 |
| **Reverse Proxy** | nginx (Alpine) | latest |

---

## 6. Repository Layout

```
PATHWISEAI/
├── CLAUDE.md                      Authoritative build specification
├── pathwiseaireadme.md            This file
├── README.md                      Short project intro
├── docker-compose.yml             12-service orchestration
├── docker-compose.dev.yml         Development overrides
├── .env.example                   Configuration template
├── Makefile                       Build helpers
├── run.py                         Local launcher (uvicorn)
├── pyproject.toml                 Python project metadata
├── requirements-local.txt         Local dev requirements
├── build_orchestrator.py          Multi-service build helper
├── PathWise_AI_Implementation_Guide.md
├── PATHWISE_AI_CURSOR_BUILD_SPEC.py
│
├── server/                        Unified FastAPI backend
│   ├── main.py                    Entry point + 40+ routes + WebSocket
│   ├── lstm_engine.py             LSTM inference loop
│   ├── sandbox.py                 Digital twin validator (in-memory)
│   ├── ibn_engine.py              Intent-Based Networking engine
│   ├── state.py                   Central in-memory state store
│   ├── auth.py                    JWT + bcrypt authentication
│   ├── rbac.py                    Role-based access control
│   ├── alerts.py                  Threshold alerts + email
│   ├── audit.py                   Tamper-evident SHA-256 audit log
│   ├── reports.py                 PDF/CSV exports
│   ├── traffic_shaper.py          OS-level QoS controller
│   ├── collector.py               Live collector dispatcher
│   ├── simulator.py               Synthetic telemetry generator
│   └── collectors/                Per-link hardware collectors
│       ├── base.py
│       ├── fiber.py
│       ├── broadband.py
│       ├── satellite.py
│       ├── fiveg.py
│       ├── wifi.py
│       ├── ethernet.py
│       └── replay.py
│
├── frontend/                      React 18 + TypeScript SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx                Router + AuthGuard + sidebar
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── NetworkSimulation.tsx
│       │   ├── SandboxViewer.tsx
│       │   ├── IBNConsole.tsx
│       │   ├── AuditLog.tsx
│       │   ├── Reports.tsx
│       │   ├── AdminPanel.tsx
│       │   └── LoginPage.tsx
│       ├── services/api.ts        Axios client
│       ├── store/networkStore.ts  Zustand store
│       ├── hooks/useWebSocket.ts  WebSocket hook
│       └── types/index.ts
│
├── ml/                            ML training pipeline
│   ├── scripts/
│   │   ├── train_lstm.py
│   │   ├── train_real_world.py
│   │   ├── fetch_real_data.py
│   │   └── verify_checkpoint.py
│   ├── data/
│   │   ├── live_wifi/
│   │   ├── live_ethernet/
│   │   └── real_world/
│   └── checkpoints/
│       ├── best_model.pt
│       └── training_log.json
│
├── infra/
│   ├── db/
│   │   ├── init.sql               TimescaleDB schema
│   │   └── backup.sh              Daily backup script
│   ├── nginx/                     TLS 1.3 reverse proxy + certs
│   ├── redis/                     Redis config
│   └── mininet/                   Mininet container build
│
├── docs/
│   └── api/openapi.yaml
│
├── services/                      Legacy microservice scaffolds
│   ├── api-gateway/
│   ├── telemetry-ingestion/
│   ├── prediction-engine/
│   ├── traffic-steering/
│   └── digital-twin/
│
└── tests/                         Unit + integration tests
```

> **Note:** The repository contains both the legacy `services/*` microservice scaffolds (referenced by `docker-compose.yml`) and the consolidated `server/*` monolithic backend that is actively used at runtime. The monolithic server implements every documented capability with a simpler dev experience.

---

## 7. Backend Modules — Deep Dive

### `server/main.py` — FastAPI entry point
The unified application entrypoint. Defines:
- App metadata: `title="PathWise AI -- SD-WAN Orchestration Solution"`, `version="2.0.0"`
- CORS middleware (`allow_origins=["*"]` for development)
- Async **lifespan** that spawns four background tasks:
  1. `simulation_loop()` — telemetry generation (sim/live/hybrid)
  2. `prediction_loop()` — LSTM inference at 1 Hz
  3. `scoreboard_broadcast_loop()` — WebSocket fan-out at 1 Hz
  4. `ibn_monitor_loop()` — intent conformance checking
- 40+ REST endpoints organized by feature area
- A `/ws/scoreboard` WebSocket endpoint
- Pydantic models for every request body (`LoginRequest`, `RegisterRequest`, `LSTMToggleRequest`, `SandboxValidationRequest`, `ApplyRuleRequest`, `IntentRequest`, `AlertConfigRequest`, `TrafficShapeRequest`, `PrioritizeOverRequest`, etc.)
- Automatic shutdown cleanup that removes all OS-level traffic conditioning policies

### `server/lstm_engine.py` — Prediction service
- Loads trained checkpoint from `ml/checkpoints/best_model.pt` on startup
- Runs **PathWiseLSTM** (2-layer, hidden=128, attention) inference every 1 second per link
- Predicts latency, jitter, and packet loss for the next 60 seconds
- Computes a **0–100 composite health score** per link
- Updates `state.predictions[link_id]` with `LinkPrediction` dataclass
- Falls back to a heuristic predictor if PyTorch is unavailable
- Inference latency stays well under the 1 Hz polling cycle (Req-Func-Sw-2)

### `server/sandbox.py` — Virtual twin validator
- Implements an **in-memory** replacement for Mininet + Batfish for fast iteration
- Defines a **reference topology** with hosts, switches, and four WAN paths (each with realistic intermediary hops: ISP PoP, IX, cable modem, DSLAM, ground stations, GEO satellite, gNodeB, 5G core UPF)
- Defines per-traffic-class requirements:
  | Class | Max Latency | Max Jitter | Max Loss | Min BW |
  |---|---|---|---|---|
  | `voip` | 50 ms | 10 ms | 0.5% | 1 Mbps |
  | `video` | 100 ms | 20 ms | 1.0% | 10 Mbps |
  | `critical` | 80 ms | 15 ms | 0.3% | 5 Mbps |
  | `bulk` | 500 ms | 100 ms | 5.0% | 1 Mbps |
- Runs 5 checks: topology snapshot, loop detection (DFS cycle), policy conformance (class ↔ link), reachability (path metrics), performance impact
- Produces a `SandboxReport` with per-check status (pass/warn/fail), execution timing, and JSON details
- Records every report in `_sandbox_history` (deque)

### `server/ibn_engine.py` — Intent-Based Networking
- **NLP parser** uses regex + alias maps (no external LLM API)
- **11 intent actions:**
  - `PRIORITIZE`, `DEPRIORITIZE`
  - `ENSURE_LATENCY`, `ENSURE_JITTER`, `ENSURE_LOSS`, `ENSURE_BANDWIDTH`
  - `BLOCK`, `REDIRECT`
  - `THROTTLE_APP`, `PRIORITIZE_APP`, `PRIORITIZE_OVER`
- **Lifecycle states:** `ACTIVE`, `COMPLIANT`, `VIOLATED`, `AUTO_STEERING`, `PAUSED`, `DELETED`
- Maps loose terminology via alias maps:
  - **Link aliases:** `fiber/fibre/primary/mpls → fiber-primary`, `cable/dsl/secondary → broadband-secondary`, `sat/vsat/backup → satellite-backup`, `lte/cellular/mobile → 5g-mobile`
  - **Traffic aliases:** `voice/sip/phone/calls → voip`, `streaming/conferencing/zoom/teams → video`, `business/erp/database/medical → critical`, `bulk/backup/transfer/ftp → bulk`
  - **Metric aliases:** `delay/lag → latency_ms`, `variation → jitter_ms`, `loss/drop → packet_loss_pct`, `throughput/speed/mbps → bandwidth_util_pct`
- Generates **YANG/NETCONF** payloads from parsed intents
- Background `ibn_monitor_loop()` continuously checks conformance and triggers auto-steering on violation

### `server/state.py` — Central state store
- All state is held in **in-memory Python deques and dicts** for offline operation (no Redis/TimescaleDB required for standalone mode)
- Default active links:
  - `fiber-primary`, `broadband-secondary`, `satellite-backup`, `5g-mobile`
  - In hybrid mode: `fiber-primary`, `5g-mobile`, `satellite-backup`, `wifi`
- **Telemetry buffer:** `dict[link_id → deque(maxlen=300)]` of `TelemetryPoint` (300 sec rolling)
- Tracks: `predictions`, `steering_history` (deque), `routing_rules` (list), `metrics_lstm_on`/`metrics_lstm_off` (`ComparisonMetrics` dataclass), `brownout_active`, `tick_count`, `start_time`, `lstm_enabled`
- Convenience methods: `get_latest_telemetry()`, `get_latest_effective()`, `get_active_rules()`

### `server/auth.py` — Authentication
- **JWT** (HS256), default expiry **60 minutes** (configurable via `JWT_EXPIRY_MINUTES`)
- **bcrypt** password hashing
- **Account lockout** after 5 failed attempts (`MAX_FAILED_ATTEMPTS = 5`)
- 5 default seeded users created on startup:
  | Email | Password | Role |
  |---|---|---|
  | `admin@pathwise.local` | `admin` | NETWORK_ADMIN |
  | `manager@pathwise.local` | `manager` | IT_MANAGER |
  | `tech@pathwise.local` | `tech` | MSP_TECH |
  | `staff@pathwise.local` | `staff` | IT_STAFF |
  | `user@pathwise.local` | `user` | END_USER |
- Provides `get_current_user()` (HTTP) and `get_ws_user()` (WebSocket) FastAPI dependencies

### `server/rbac.py` — Role-based access control
- 5 roles defined as a `Role` enum: `NETWORK_ADMIN`, `IT_MANAGER`, `MSP_TECH`, `IT_STAFF`, `END_USER`
- **Permission categories:** `telemetry`, `predictions`, `steering`, `routing`, `sandbox`, `policies`, `ibn`, `admin`, `audit`, `reports`, `alerts`, `users`
- Two factory dependencies:
  - `require_role("NETWORK_ADMIN", ...)` — exact role match
  - `require_permission("steering")` — category-based check
- Returns HTTP 401 (not authenticated) or 403 (insufficient permissions)

### `server/alerts.py` — Real-time alerting
- Health-score threshold breach detection
- SMTP email + dashboard notifications
- Configurable threshold (default **70**) and **suppression window** (default 5 s)
- **500-entry rolling history** with deduplication
- Alert types: `threshold_breach`, `brownout`, `recovery`
- Live config update via `/api/v1/alerts/config`

### `server/audit.py` — Tamper-evident audit log
- **10,000-entry deque** with **SHA-256 chained checksums** (HIPAA-compliant)
- Each entry's hash incorporates the previous hash → any tampering breaks the chain
- Event types: `STEERING`, `VALIDATION`, `POLICY_CHANGE`, `AUTH`, `ALERT`, `SYSTEM`
- Fields per entry: `id`, `event_time`, `event_type`, `actor`, `link_id`, `health_score`, `confidence`, `validation_result`, `routing_change` (JSON), `policy_change` (JSON), `details`, `checksum`
- Integrity verification endpoint at `/api/v1/audit/verify`

### `server/reports.py` — Data exports
- PDF + CSV generation streamed via FastAPI `StreamingResponse`
- Three exportable datasets: health scores, steering events, audit log
- CSV via standard library; PDF via lightweight generator

### `server/traffic_shaper.py` — OS-level QoS
- **Windows:** PowerShell `New-NetQosPolicy`
- **Linux:** `tc` (traffic control)
- **5 priority classes:** `CRITICAL`, `HIGH`, `NORMAL`, `LOW`, `BLOCKED`
- 18+ predefined `AppProfile` entries — each with process names, domain patterns, IP CIDR ranges, and default priority
- Supported actions: `throttle_app(app, kbps)`, `prioritize_app(app)`, `prioritize_over(high, low, kbps)`, `remove_policy(id)`, `remove_all_policies()`
- All policy changes recorded in the audit log
- All policies cleaned up automatically on shutdown via `lifespan`

### `server/collectors/` — Live hardware telemetry
| Module | Purpose |
|---|---|
| `base.py` | Abstract collector interface |
| `fiber.py` | Ping + SNMP via configurable router |
| `broadband.py` | Ping + interface statistics |
| `satellite.py` | GEO satellite latency modeling |
| `fiveg.py` | 5G CPE metric collection |
| `wifi.py` | Wi-Fi interface monitoring |
| `ethernet.py` | Local Ethernet stats |
| `replay.py` | Replay recorded CSV traces |

### `server/simulator.py` — Synthetic telemetry
- Used when `DATA_SOURCE=sim`
- Per-link base latencies: **fiber 12 ms, broadband 22 ms, satellite 55 ms, 5G 18 ms**
- Realistic noise scaling, **diurnal traffic cycles**, and stochastic **brownout events** (per-link probability 0.8%–1.5%)
- Pushes synthetic `TelemetryPoint` records into `state.telemetry` at 1 Hz

---

## 8. REST & WebSocket API

Base URL (dev): `http://localhost:8000`

### Public
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/status` | Returns `running`, LSTM state, uptime, tick count, active links |

### Authentication
| Method | Path | RBAC | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | public | Email + password → JWT token |
| POST | `/api/v1/auth/register` | NETWORK_ADMIN | Register new user |
| GET | `/api/v1/auth/me` | any logged-in | Current user profile |
| GET | `/api/v1/auth/users` | NETWORK_ADMIN | List all users |
| POST | `/api/v1/auth/unlock/{user_id}` | NETWORK_ADMIN | Unlock locked account |

### Telemetry
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/telemetry/links` | List active link IDs |
| GET | `/api/v1/telemetry/{link_id}?window=60` | Effective telemetry (post-steering) |
| GET | `/api/v1/telemetry/{link_id}/raw?window=60` | Raw collector data (pre-steering) |

### Predictions & Comparison
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/predictions/all` | All link forecasts |
| GET | `/api/v1/predictions/{link_id}` | Single-link forecast |
| GET | `/api/v1/metrics/comparison` | LSTM ON vs OFF metrics |

### Steering & Routing
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/steering/history?limit=50` | Recent steering events |
| POST | `/api/v1/routing/apply` | Apply a sandbox-validated rule |
| GET | `/api/v1/routing/active` | Currently active routing rules |
| GET | `/api/v1/routing/all` | All rules (active + rolled-back) |
| DELETE | `/api/v1/routing/{rule_id}` | Roll back a rule |

### Sandbox
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/sandbox/validate` | Validate a proposed routing change |
| GET | `/api/v1/sandbox/history?limit=20` | Past validation reports |
| GET | `/api/v1/sandbox/topology` | Reference topology + per-link health |

### IBN
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/ibn/intents` | Create new intent |
| GET | `/api/v1/ibn/intents` | List all intents |
| GET | `/api/v1/ibn/intents/{id}` | Get intent details |
| DELETE | `/api/v1/ibn/intents/{id}` | Delete intent |
| POST | `/api/v1/ibn/intents/{id}/pause` | Pause intent |
| POST | `/api/v1/ibn/intents/{id}/resume` | Resume intent |
| POST | `/api/v1/ibn/parse` | Parse-only preview (no persistence) |

### Traffic Shaping
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/traffic/apps` | List supported app profiles |
| GET | `/api/v1/traffic/policies` | Active policies |
| GET | `/api/v1/traffic/policies/all` | All policies (history) |
| POST | `/api/v1/traffic/throttle` | Throttle an app to N kbps |
| POST | `/api/v1/traffic/prioritize` | Prioritize an app |
| POST | `/api/v1/traffic/prioritize-over` | Prioritize App-A over App-B |
| DELETE | `/api/v1/traffic/policies/{id}` | Remove specific policy |
| POST | `/api/v1/traffic/reset` | Remove all policies (admin) |

### Audit · Alerts · Reports · Admin
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/audit?page=1&per_page=50` | Paginated audit log (filterable) |
| GET | `/api/v1/audit/verify` | Verify SHA-256 chain integrity |
| GET | `/api/v1/alerts/history?limit=50` | Recent alerts |
| PUT | `/api/v1/alerts/config` | Update threshold + suppression |
| GET | `/api/v1/reports/health-scores?format=csv\|pdf` | Export health scores |
| GET | `/api/v1/reports/steering-events?format=csv\|pdf` | Export steering events |
| GET | `/api/v1/reports/audit-log?format=csv\|pdf` | Export audit log |
| POST | `/api/v1/admin/lstm-toggle` | Enable/disable LSTM model |
| GET | `/api/v1/admin/lstm-status` | LSTM model state |
| GET | `/api/v1/live-data/stats` | Live collector sample counts |

### WebSocket — `/ws/scoreboard`
Broadcasts a JSON payload **once per second** containing:
```json
{
  "type": "scoreboard_update",
  "timestamp": <unix>,
  "lstm_enabled": true,
  "links": {
    "fiber-primary": {
      "health_score": 87,
      "confidence": 0.93,
      "latency_current": 12.3,
      "jitter_current": 1.8,
      "packet_loss_current": 0.04,
      "bandwidth_util": 42.1,
      "latency_forecast": [12.5, 12.7, ...],
      "trend": "stable",
      "brownout_active": false,
      "raw_latency": 12.5, "raw_jitter": 1.9, "raw_packet_loss": 0.05
    }
  },
  "active_routing_rules": [ ... ],
  "ibn_intents": [ ... ],
  "steering_events": [ ... ],
  "comparison": { "lstm_on": {...}, "lstm_off": {...} }
}
```

---

## 9. Frontend Dashboard (UI Details)

The dashboard is a React 18 + TypeScript SPA built with Vite, styled with Tailwind CSS, animated with Framer Motion, and visualized with Recharts.

### 9.1 Layout

The main layout (`AppLayout` in `App.tsx`) is a fixed two-column shell:

**Sidebar (256 px wide, dark surface):**
- **Brand block** — gradient logo + "PathWise" wordmark + "AI-Powered SD-WAN" tagline
- **Navigation list** with Lucide icons:
  | Icon | Label | Route |
  |---|---|---|
  | `LayoutDashboard` | Dashboard | `/dashboard` |
  | `Network` | Network Simulation | `/simulation` |
  | `FlaskConical` | Sandbox | `/sandbox` |
  | `Terminal` | IBN Console | `/ibn` |
  | `ScrollText` | Audit Log | `/audit` |
  | `FileBarChart` | Reports | `/reports` |
  | `ShieldCheck` | Admin Panel | `/admin` |
- **Status footer:**
  - Logged-in user (email + role) and sign-out button (when AUTH_ENABLED)
  - **Server** indicator: green dot "Connected" or red dot "Offline"
  - **LSTM Model** indicator: green "Active" or amber "Inactive"
  - "Offline Mode" tag with Wi-Fi icon

**Main Content** — animated route outlet (Framer Motion fade-in)

### 9.2 Routing

```tsx
<Router>
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/*" element={<AuthGuard><AppLayout /></AuthGuard>}>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/simulation" element={<NetworkSimulation />} />
      <Route path="/sandbox" element={<SandboxViewer />} />
      <Route path="/ibn" element={<IBNConsole />} />
      <Route path="/audit" element={<AuditLog />} />
      <Route path="/reports" element={<Reports />} />
      <Route path="/admin" element={<AdminPanel />} />
    </Route>
  </Routes>
</Router>
```

`AuthGuard` redirects to `/login` when `VITE_AUTH_ENABLED=true` and the user is not authenticated.

### 9.3 Pages

**LoginPage.tsx**
- Email + password inputs
- Generic error message on failure (no leakage of which field was wrong)
- On success: stores `pathwise_token`, `pathwise_role`, `pathwise_email` in `localStorage`
- Calls Zustand `setAuth()` and redirects to `/dashboard`

**Dashboard.tsx — Main landing page**
- **Multi-link health scoreboard** (4 link cards): each card displays
  - Health score 0–100 (color-coded green/yellow/red)
  - Confidence percentage
  - Real-time latency / jitter / packet loss / bandwidth utilization
  - Trend indicator (degrading / stable / improving)
  - Brownout badge when active
  - 10-point latency forecast sparkline (Recharts)
- **Active routing rules table** with rule ID, source → target, traffic classes, age
- **LSTM ON vs LSTM OFF comparison panel:**
  - LSTM ON: avg latency, avg jitter, avg packet loss, proactive steerings, brownouts avoided
  - LSTM OFF: same averages + reactive steerings + brownouts hit
- **Recent steering events** scrolling feed
- **WebSocket connection indicator** (green/red dot)

**NetworkSimulation.tsx — Real-time telemetry**
- Per-link time-series charts (latency, jitter, packet loss, bandwidth) via Recharts
- **Raw vs effective** telemetry toggle (switches between pre-steering and post-steering data)
- **Data source selector** (sim / live / hybrid)
- Live collector sample counts when in live mode

**SandboxViewer.tsx — Digital twin validation console**
- Source link dropdown
- Target link dropdown
- Traffic class multi-select (`voip`, `video`, `critical`, `bulk`)
- "Validate" button → POST `/api/v1/sandbox/validate`
- **Detailed validation report:**
  - Topology snapshot
  - Each of the 5 checks with pass/warn/fail badge
  - Per-check details + timing
  - Total execution time in ms
- "Apply Rule" button (gated on validation pass) → POST `/api/v1/routing/apply`
- **History table** of past validations (paginated, sortable)

**IBNConsole.tsx — Natural-language policy editor**
- **Intent input textarea** with example prompts
- **Real-time parse preview** (calls `/api/v1/ibn/parse` as user types):
  - Action (e.g., `prioritize_over`)
  - Traffic classes
  - Metric + threshold + unit
  - Preferred / avoid links
  - High / low app, throttle kbps
- **Generated YANG config viewer** (JSON code block)
- **Active intents list** with status badges (active / compliant / violated / auto_steering / paused)
- **Pause / resume / delete** controls per intent
- Per-intent **violation counter** and **auto-steer count**

**AuditLog.tsx — Tamper-evident log viewer**
- Paginated table (50 entries/page default)
- Columns: timestamp, event_type, actor, link_id, health_score, validation_result, details, checksum (first 16 chars)
- Filter dropdowns: by event type (`STEERING`, `VALIDATION`, `POLICY_CHANGE`, `AUTH`, `ALERT`, `SYSTEM`), by actor
- **"Verify Integrity"** button — calls `/api/v1/audit/verify` and shows SHA-256 chain status

**Reports.tsx — Data export interface**
- Three sections: Health Scores · Steering Events · Audit Log
- Per section: "Download CSV" + "Download PDF" buttons
- File download via blob streaming

**AdminPanel.tsx — Admin-only configuration**
- **LSTM Model toggle** (calls `/api/v1/admin/lstm-toggle`)
- **Alert configuration:**
  - Threshold slider 0–100
  - Suppression window (seconds) input
- **User management table** (email, role, status, failed attempts, lock state)
- **Per-user "Unlock" button** for locked accounts
- **New user registration form** (email, password, role selector)

### 9.4 Zustand Store (`networkStore.ts`)

```ts
interface NetworkState {
  activeLinks: string[];
  lstmEnabled: boolean;
  scoreboard: Record<string, LinkHealth>;
  predictions: Record<string, PredictionResponse>;
  steeringEvents: SteeringEvent[];
  activeRoutingRules: ActiveRoutingRule[];
  comparison: { lstm_on: ComparisonMetrics; lstm_off: ComparisonMetrics };
  wsConnected: boolean;
  tickCount: number;

  // Auth state (rehydrated from localStorage on init)
  isAuthenticated: boolean;
  userRole: string | null;
  userEmail: string | null;
  setAuth: (token, role, email) => void;
  logout: () => void;
}
```

The store hydrates auth state from `localStorage` on initial load so refresh persists the session.

### 9.5 WebSocket Hook (`useWebSocket.ts`)

`useScoreboardWebSocket()` is called once at the layout level. It opens a connection to `/ws/scoreboard`, receives 1 Hz updates, and pushes the payload into the Zustand store via `updateScoreboard`, `setSteeringEvents`, `setActiveRoutingRules`, `updateComparison`, and `setLstmEnabled`. It tracks connection status via `setWsConnected`.

### 9.6 API Client (`services/api.ts`)

Axios-based client with two interceptors:
- **Request interceptor** — auto-attaches `Authorization: Bearer <token>` from `localStorage`
- **Response interceptor** — on 401, clears auth state and redirects to `/login`

Provides typed wrappers for all 40+ backend endpoints (login, getUsers, validateSandbox, applyRoutingRule, createIntent, parseIntent, getAuditLog, exportHealthScoresPDF, throttleApp, prioritizeOver, etc.).

---

## 10. LSTM Prediction Engine

### Architecture (`PathWiseLSTM`)
```python
# Input:  [batch, seq_len=60, features=3]   (latency, jitter, packet_loss)
# Output: [batch, 2, features=3]            (predictions at t+30s, t+60s)
#
# - 2 stacked LSTM layers, hidden_size=128
# - Dropout=0.2 between layers
# - Bahdanau attention over LSTM output sequence
# - Linear projection head → 2 × 3 outputs
# - Health score: weighted combination of normalized predictions → 0–100
```

### Training Configuration
- Optimizer: **Adam**, lr = 1e-3
- Loss: **MSE** on (latency, jitter, packet_loss) at t+30 s and t+60 s
- Batch size: **256**
- Epochs: **50** with early stopping (patience = 5)
- Train/val/test split: **70 / 15 / 15**
- Sequence length: **60 timesteps** (60 s of 1 Hz data)

### Achieved Metrics (`ml/checkpoints/training_log.json`)

| Metric | Value |
|---|---|
| Best epoch | **30** |
| Best validation loss | **306.38** |
| Test loss | **297.14** |
| **Latency MAE** | **6.94 ms** |
| **Jitter MAE** | **2.14 ms** |
| **Packet loss MAE** | **0.369 %** |
| Training data | `real_world_calibrated` |

### Health Score Distribution (test set)
| Band | Range | Share |
|---|---|---|
| **Critical** | < 40 | 3.65 % |
| **Warning** | 40 – 70 | 26.99 % |
| **Healthy** | > 70 | 69.35 % |

Mean: **67.12** · Std: **12.98**

### Inference Service
- Runs **1 inference per link per second**
- < 1 second per inference pass (Req-Func-Sw-2)
- Loads from `ml/checkpoints/best_model.pt` on startup
- Deterministic heuristic fallback when PyTorch is unavailable

---

## 11. Digital Twin Sandbox

### Validation Pipeline
1. **Topology snapshot** — capture current network state from `state` and reference `TOPOLOGY`
2. **Loop detection** — DFS-based cycle detection on the flow graph
3. **Policy compliance** — match traffic class capability requirements against link characteristics
4. **Reachability simulation** — verify path exists and metrics are acceptable
5. **Performance impact estimation** — predicted latency / jitter / loss after steering

### SLA
Full validation cycle in **< 5 seconds** (Req-Qual-Perf-3). In practice the in-memory validator typically completes in < 100 ms.

### Output (`SandboxReport`)
```json
{
  "id": "abc123...",
  "result": "PASSED",
  "execution_time_ms": 87.3,
  "checks": [
    { "name": "topology", "status": "pass", "message": "...", "duration_ms": 5.1 },
    { "name": "loop_free", "status": "pass", "message": "...", "duration_ms": 12.4 },
    { "name": "policy_compliant", "status": "pass", "message": "...", "duration_ms": 8.7 },
    { "name": "reachability", "status": "pass", "message": "...", "duration_ms": 47.2 },
    { "name": "performance", "status": "warn", "message": "...", "duration_ms": 13.9 }
  ],
  "topology_snapshot": { ... }
}
```

### Traffic Class Requirements (enforced by validator)
| Class | Max Latency | Max Jitter | Max Loss | Min BW |
|---|---|---|---|---|
| `voip` | 50 ms | 10 ms | 0.5% | 1 Mbps |
| `video` | 100 ms | 20 ms | 1.0% | 10 Mbps |
| `critical` | 80 ms | 15 ms | 0.3% | 5 Mbps |
| `bulk` | 500 ms | 100 ms | 5.0% | 1 Mbps |

---

## 12. Intent-Based Networking (IBN)

### Example Intents
- `Prioritize VoIP traffic on fiber`
- `Ensure video latency stays below 100ms`
- `Block bulk traffic on satellite`
- `Redirect critical traffic from broadband to fiber`
- `Guarantee medical imaging gets at least 50Mbps on fiber`
- `Prioritize Zoom over Netflix and throttle Netflix to 500 kbps`

### Supported Actions (11 total)
| Action | Purpose |
|---|---|
| `PRIORITIZE` | Make a traffic class higher priority |
| `DEPRIORITIZE` | Lower a class's priority |
| `ENSURE_LATENCY` | SLA on latency for a class |
| `ENSURE_JITTER` | SLA on jitter for a class |
| `ENSURE_LOSS` | SLA on packet loss |
| `ENSURE_BANDWIDTH` | Minimum bandwidth guarantee |
| `BLOCK` | Drop class on a link/scope |
| `REDIRECT` | Force a class onto a specific link |
| `THROTTLE_APP` | OS-level app throttling |
| `PRIORITIZE_APP` | OS-level app prioritization |
| `PRIORITIZE_OVER` | Prefer App-A over App-B |

### Lifecycle States
| State | Meaning |
|---|---|
| `ACTIVE` | Registered, monitoring |
| `COMPLIANT` | Conditions currently met |
| `VIOLATED` | Conditions breached |
| `AUTO_STEERING` | Auto-recovery in progress |
| `PAUSED` | Temporarily disabled |
| `DELETED` | Soft-deleted |

### YANG / NETCONF Translation
Parsed intents are translated to:
- `ietf-diffserv-classifier` for traffic prioritization
- `ietf-qos-policy` for QoS rules
- ODL/ONOS-specific flow rule schemas for routing policies

---

## 13. Traffic Shaping & Application QoS

OS-level enforcement via:
- **Windows** — PowerShell `New-NetQosPolicy` (requires admin)
- **Linux** — `tc` (traffic control)

### Priority Classes
| Class | Purpose |
|---|---|
| `CRITICAL` | VoIP, real-time — never throttle |
| `HIGH` | Business apps — minimal throttling |
| `NORMAL` | Default |
| `LOW` | Streaming, bulk — throttle first |
| `BLOCKED` | Fully blocked |

### Built-in App Profiles (selected, 18+ total)
| App | Category | Default Priority |
|---|---|---|
| Zoom | video_call | CRITICAL |
| Microsoft Teams | video_call | CRITICAL |
| Google Meet | video_call | CRITICAL |
| Webex | video_call | CRITICAL |
| Skype | video_call | HIGH |
| Slack | business | HIGH |
| Discord | social | NORMAL |
| YouTube | streaming | LOW |
| Netflix | streaming | LOW |
| Spotify | streaming | LOW |
| Twitch | streaming | LOW |
| Steam | gaming | LOW |
| Xbox Live | gaming | LOW |
| PlayStation Network | gaming | LOW |
| Dropbox | bulk | LOW |
| OneDrive | bulk | LOW |
| Google Drive | bulk | LOW |
| AWS S3 | bulk | LOW |

Each profile carries: process names, domain patterns (e.g. `*.zoom.us`), known IP CIDR ranges (e.g. `3.7.35.0/25`), and a default priority.

### Operations
- `throttle_app(app_name, bandwidth_kbps)` — enforce a per-app rate limit
- `prioritize_app(app_name)` — promote app to CRITICAL/HIGH
- `prioritize_over(high_app, low_app, throttle_kbps)` — combined two-policy operation
- `remove_policy(policy_id)` — clean up
- `remove_all_policies()` — full reset (auto-invoked on shutdown)

All operations are recorded in the audit log.

---

## 14. Authentication & RBAC

### Default Seeded Users
| Email | Password | Role |
|---|---|---|
| `admin@pathwise.local` | `admin` | NETWORK_ADMIN |
| `manager@pathwise.local` | `manager` | IT_MANAGER |
| `tech@pathwise.local` | `tech` | MSP_TECH |
| `staff@pathwise.local` | `staff` | IT_STAFF |
| `user@pathwise.local` | `user` | END_USER |

### Permission Matrix
| Resource | Admin | IT Mgr | MSP Tech | IT Staff | End User |
|---|---|---|---|---|---|
| Telemetry | ✅ | ✅ | ✅ | ✅ | ✅ |
| Predictions | ✅ | ✅ | ✅ | ✅ | ✅ |
| Steering | ✅ | ✅ | ✅ | ❌ | ❌ |
| Routing | ✅ | ✅ | ✅ | ❌ | ❌ |
| Sandbox | ✅ | ✅ | ✅ | ✅ | ❌ |
| Policies / IBN | ✅ | ✅ | ✅ | ❌ | ❌ |
| Audit | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reports | ✅ | ✅ | ✅ | ✅ | ❌ |
| Alerts | ✅ | ✅ | ❌ | ❌ | ❌ |
| Admin | ✅ | ❌ | ❌ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ | ❌ |

### Security Controls
- **bcrypt** password hashing (one-way)
- **JWT** (HS256), default 60-minute expiry
- **Account lockout** after 5 failed attempts
- **Generic error** on failed login (no info leakage)
- **TLS 1.3** enforced via nginx
- **CORS** middleware (development = wildcard, production should restrict)

---

## 15. Alerts & Audit Logging

### Alerts (`alerts.py`)
- Triggered on health score < threshold (default **70**)
- Configurable **suppression window** (default 5 s) prevents floods
- Channels: dashboard notification panel + SMTP email
- 500-entry rolling history with deduplication
- Alert types: `threshold_breach`, `brownout`, `recovery`
- Live config edit via `PUT /api/v1/alerts/config`

### Audit Log (`audit.py`)
- 10,000-entry tamper-evident deque
- **SHA-256 chained checksums** — each entry incorporates the previous hash
- Event types: `STEERING`, `VALIDATION`, `POLICY_CHANGE`, `AUTH`, `ALERT`, `SYSTEM`
- Per-entry fields: `id`, `event_time`, `event_type`, `actor`, `link_id`, `health_score`, `confidence`, `validation_result`, `routing_change` (JSON), `policy_change` (JSON), `details`, `checksum`
- Filterable by event type and actor via `/api/v1/audit`
- Integrity verification via `/api/v1/audit/verify`
- HIPAA-compliant for healthcare deployments (Req-Qual-Sec-3)

---

## 16. Reports & Exports

PDF + CSV exports streamed via FastAPI `StreamingResponse`:

| Report | Endpoint | Columns |
|---|---|---|
| Health Scores | `/api/v1/reports/health-scores?format=csv\|pdf` | link_id, score, confidence, forecast averages, timestamps |
| Steering Events | `/api/v1/reports/steering-events?format=csv\|pdf` | id, timestamp, action, source/target, traffic_classes, confidence, reason, status, lstm_enabled |
| Audit Log | `/api/v1/reports/audit-log?format=csv\|pdf` | id, event_time, event_type, actor, details, checksum |

All export endpoints require the `reports` permission.

---

## 17. Telemetry Sources & Collectors

The `DATA_SOURCE` env var controls telemetry origin:

| Mode | Active Links | Behavior |
|---|---|---|
| `sim` | fiber, broadband, satellite, 5g | Pure synthetic generator |
| `live` | fiber, broadband, satellite, 5g | Real hardware collectors |
| `hybrid` | fiber, 5g, satellite, **wifi** | WiFi live + 3 replayed CSVs |

### Default Per-Link Profiles (sim mode)
| Link | Type | Base Latency | Brownout Probability |
|---|---|---|---|
| `fiber-primary` | Fiber | 12 ms | ~0.8 % |
| `broadband-secondary` | Broadband | 22 ms | ~1.2 % |
| `satellite-backup` | Satellite | 55 ms | ~1.5 % |
| `5g-mobile` | 5G | 18 ms | ~1.0 % |

Synthetic generator includes:
- Realistic Gaussian noise
- Diurnal traffic cycles
- Stochastic brownout events
- Link-specific failure modes (jitter spikes, packet loss bursts, latency drift)

---

## 18. Reference Network Topology

`sandbox.py` defines a fixed reference topology used for validation, with realistic intermediary hops per WAN link:

```
Site A (HQ)                                            Site B (Branch)
   h1                                                     h2
   │                                                      │
  s1 (Edge Router 1)                                  s2 (Edge Router 2)
   │                                                      │
   ├──── fiber-primary ──────────────────────────────────┤
   │   s1 → ISP PoP → Internet Exchange → ISP PoP → s2   │
   │                                                      │
   ├──── broadband-secondary ────────────────────────────┤
   │   s1 → Cable Modem → DSLAM → ISP Hub → s2           │
   │                                                      │
   ├──── satellite-backup ───────────────────────────────┤
   │   s1 → Ground Stn → GEO Satellite → Ground Stn → s2 │
   │                                                      │
   └──── 5g-mobile ──────────────────────────────────────┘
       s1 → gNodeB → 5G Core (UPF) → gNodeB → s2
```

### WAN Link Characteristics
| Link ID | Bandwidth | Delay | Loss | Hops |
|---|---|---|---|---|
| `fiber-primary` | 1000 Mbps | 5 ms | 0.01 % | 5 |
| `broadband-secondary` | 100 Mbps | 15 ms | 0.10 % | 5 |
| `satellite-backup` | 10 Mbps | 300 ms | 0.50 % | 5 |
| `5g-mobile` | 200 Mbps | 20 ms | 0.20 % | 5 |

---

## 19. Database Schema (TimescaleDB)

`infra/db/init.sql` creates:

```sql
-- Raw 1-second telemetry hypertable
CREATE TABLE wan_telemetry (
    time          TIMESTAMPTZ NOT NULL,
    link_id       UUID        NOT NULL,
    site_id       UUID        NOT NULL,
    latency_ms    FLOAT       NOT NULL,
    jitter_ms     FLOAT       NOT NULL,
    packet_loss   FLOAT       NOT NULL,
    link_type     VARCHAR(20) NOT NULL  -- FIBER, SATELLITE, 5G, BROADBAND
);
SELECT create_hypertable('wan_telemetry', 'time');
CREATE INDEX ON wan_telemetry (link_id, time DESC);

-- Predicted health scores
CREATE TABLE health_scores (
    time            TIMESTAMPTZ NOT NULL,
    link_id         UUID        NOT NULL,
    health_score    FLOAT       NOT NULL,
    confidence      FLOAT       NOT NULL,
    prediction_window_s INT     NOT NULL
);
SELECT create_hypertable('health_scores', 'time');

-- Tamper-evident audit log
CREATE TABLE audit_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      VARCHAR(50) NOT NULL,
    actor           VARCHAR(100),
    link_id         UUID,
    health_score    FLOAT,
    confidence      FLOAT,
    validation_result VARCHAR(10),
    routing_change  JSONB,
    policy_change   JSONB,
    details         TEXT,
    checksum        VARCHAR(64)
);

-- Users & RBAC
CREATE TABLE users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50)  NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    failed_attempts INT          NOT NULL DEFAULT 0,
    locked_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Network policies
CREATE TABLE policies (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    natural_language TEXT        NOT NULL,
    yang_config     JSONB        NOT NULL,
    created_by      UUID         REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);
```

**Retention policies:** raw 7 days, aggregates 90 days
**Backup cycle:** daily via `infra/db/backup.sh` (Req-Qual-Rel-3)

---

## 20. Configuration & Environment Variables

Copy `.env.example` to `.env` and adjust values:

```env
# ── Database ────────────────────────────────────────────────
POSTGRES_DB=pathwise
POSTGRES_USER=pathwise
POSTGRES_PASSWORD=pathwise_dev
TIMESCALEDB_URL=postgresql://pathwise:pathwise_dev@timescaledb:5432/pathwise
REDIS_URL=redis://redis:6379/0

# ── SDN Controllers ─────────────────────────────────────────
SDN_TYPE=opendaylight
ODL_HOST=localhost
ODL_PORT=8181
ODL_USER=admin
ODL_PASS=admin
ONOS_HOST=localhost
ONOS_PORT=8181
ONOS_USER=onos
ONOS_PASS=rocks

# ── Authentication ──────────────────────────────────────────
AUTH_ENABLED=false
JWT_SECRET=change-this-to-a-256-bit-random-secret
JWT_EXPIRY_MINUTES=60

# ── Encryption ──────────────────────────────────────────────
ENCRYPTION_KEY=change-this-to-an-aes-256-key

# ── LSTM Model ──────────────────────────────────────────────
MODEL_PATH=ml/checkpoints/best_model.pt
PREDICTION_WINDOW_S=60
HEALTH_SCORE_THRESHOLD=70

# ── Data Source ─────────────────────────────────────────────
# sim | live | hybrid
DATA_SOURCE=sim

# ── Live Collector Config (when DATA_SOURCE=live) ───────────
FIBER_MODE=ping
FIBER_ROUTER_IP=10.0.1.1
FIBER_SNMP_COMMUNITY=public
FIBER_PING_TARGET=8.8.8.8
FIBER_LINK_SPEED=1000

BROADBAND_PING_TARGET=1.1.1.1
BROADBAND_INTERFACE=eth1
BROADBAND_LINK_SPEED=100

SATELLITE_MODE=ping
SATELLITE_DISH_IP=192.168.100.1
SATELLITE_PING_TARGET=8.8.4.4
SATELLITE_LINK_SPEED=200

FIVEG_MODE=ping
FIVEG_CPE_IP=192.168.1.1
FIVEG_INTERFACE=wwan0
FIVEG_PING_TARGET=8.8.8.8
FIVEG_LINK_SPEED=300

# ── Alerts ──────────────────────────────────────────────────
ALERT_EMAIL_SMTP_HOST=
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
ALERT_EMAIL_USER=
ALERT_EMAIL_PASS=
ALERT_SUPPRESSION_WINDOW_S=5

# ── Batfish / Mininet ───────────────────────────────────────
BATFISH_HOST=batfish
BATFISH_PORT=9997
MININET_WSL_COMMAND=wsl mininet

# ── Frontend ────────────────────────────────────────────────
REACT_APP_API_URL=http://localhost:8000
VITE_API_URL=http://localhost:8000
VITE_AUTH_ENABLED=false

# ── Debug ───────────────────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO
```

---

## 21. Installation & Local Development

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop** (with WSL2 backend on Windows)
- ≥ 8 CPU cores, ≥ 32 GB RAM, ≥ 1 TB SSD (production)
- ≥ 1920 × 1080 dashboard resolution

### Local Standalone Mode (No Docker)

```bash
# 1. Clone & configure
git clone <repo-url>
cd PATHWISEAI
cp .env.example .env

# 2. Backend
python -m venv .venv
source .venv/Scripts/activate          # Windows bash
pip install -r requirements-local.txt
python run.py                          # FastAPI on :8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                            # Vite dev server on :3000
```

Open `http://localhost:3000`. With `VITE_AUTH_ENABLED=false` you go straight to the dashboard; with auth enabled, login as `admin@pathwise.local / admin`.

### Quick Smoke Test
```bash
curl http://localhost:8000/api/v1/status
# {"status":"running","lstm_enabled":false,"uptime_seconds":12.4,...}
```

---

## 22. Docker Compose Deployment

```bash
docker compose up --build
```

### Services (12 total)

| Service | Image / Build | Ports | Notes |
|---|---|---|---|
| `timescaledb` | `timescale/timescaledb:latest-pg16` | 5432 | 8 GB RAM limit; init.sql mounted |
| `redis` | `redis:7-alpine` | 6379 | maxmemory 256 MB, allkeys-lru |
| `opendaylight` | `opendaylight/odl:latest` | 6633, 8181 | RESTCONF + OpenFlow |
| `mininet` | `./infra/mininet` | host network | Privileged container |
| `batfish` | `batfish/allinone:latest` | 9997, 9996 | Health-checked |
| `api-gateway` | `./services/api-gateway` | 8000 | Auth enabled |
| `telemetry-ingestion` | `./services/telemetry-ingestion` | — | Depends on Redis + DB |
| `prediction-engine` | `./services/prediction-engine` | — | Mounts `./ml/checkpoints` |
| `traffic-steering` | `./services/traffic-steering` | — | Depends on ODL |
| `digital-twin` | `./services/digital-twin` | — | Privileged for Mininet |
| `frontend` | `./frontend` | 3000 | Vite build |
| `nginx` | `nginx:alpine` | 80, 443 | TLS 1.3 reverse proxy |

### Health Checks
All long-running services declare Docker health checks:
- `timescaledb`: `pg_isready -U pathwise -d pathwise` every 10 s
- `redis`: `redis-cli ping` every 10 s
- `opendaylight`: `curl /restconf/` every 30 s
- `batfish`: `curl /v2/status` every 20 s
- `api-gateway`: `curl /api/v1/status` every 15 s
- `frontend`: `curl /` every 15 s

### Resource Limits
- **TimescaleDB:** 8 GB RAM (Req-Func-Hw-1)
- **Redis:** 256 MB max-memory with LRU eviction

### Restart Policy
All services use `restart: always` to satisfy **Req-Qual-Rel-2** (single-component failure must not halt platform).

### Volumes
`timescale_data` — persistent PostgreSQL data

### Backup
`infra/db/backup.sh` runs daily, retains 7 days of `pg_dump --format=custom` archives. Implements **Req-Qual-Rel-3** (24 h backup cycle).

### nginx Reverse Proxy
- TLS 1.3 only
- Cipher suites: `TLS_AES_256_GCM_SHA384`, `TLS_AES_128_GCM_SHA256`, `TLS_CHACHA20_POLY1305_SHA256`
- Security headers: HSTS (63072000 s), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`
- Rate limiting: 30 req/s per IP, 20 burst
- Routes: `/api/*` → backend, `/ws/*` → WebSocket upgrade, `/` → frontend

---

## 23. Integration Points

### 23.1 OpenDaylight (ODL)
- Base URL: `http://{ODL_HOST}:8181/restconf/`
- Auth: Basic auth via `ODL_USER` / `ODL_PASS`
- Operations: `get_flow_tables`, `update_flow_entry`, `delete_flow_entry`, `get_topology`

### 23.2 ONOS
- Base URL: `http://{ONOS_HOST}:8181/onos/v1/`
- Auth: Basic auth via `ONOS_USER` / `ONOS_PASS`
- Same operations as ODL (mirror interface)

### 23.3 Mininet (WSL2 on Windows)
Invoked via:
```bash
wsl sudo mn --topo=linear,3 --controller=remote,ip=...
```
Used by data generation pipeline (`ml/data_generation/mininet_telemetry_gen.py`) and originally by the digital twin (replaced with in-memory validator for performance).

### 23.4 Batfish
- Container `batfish/allinone:latest` on ports 9997 / 9996
- Used via `pybatfish` for: routing loop checks (`hasRoute` assertions), reachability checks, ACL violation detection
- Configurable via `BATFISH_HOST` / `BATFISH_PORT`

### 23.5 SMTP (Alerts)
Configurable via `ALERT_EMAIL_SMTP_HOST`, `ALERT_EMAIL_SMTP_PORT` (default 587), `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO`, `ALERT_EMAIL_USER`, `ALERT_EMAIL_PASS`. Sends on threshold breach via `alerts.send_email()`.

### 23.6 OS-Level QoS
- **Windows:** PowerShell `New-NetQosPolicy` (requires admin)
- **Linux:** `tc qdisc add dev <iface> root htb`
- All policies tracked in-memory and removed automatically on shutdown

---

## 24. Settings & Admin Controls

The Admin Panel provides live configuration controls (NETWORK_ADMIN role only):

| Setting | API Endpoint | Default | Description |
|---|---|---|---|
| **LSTM Model** | `POST /api/v1/admin/lstm-toggle` | `false` | Enable/disable LSTM-driven steering for A/B testing |
| **Health Threshold** | `PUT /api/v1/alerts/config` | `70` | Health score below which alerts fire |
| **Suppression Window** | `PUT /api/v1/alerts/config` | `5 s` | Minimum interval between duplicate alerts |
| **User Management** | `/api/v1/auth/users`, `/auth/register`, `/auth/unlock/{id}` | — | Create, list, unlock users |
| **JWT Expiry** | `JWT_EXPIRY_MINUTES` env | `60 min` | Session token lifetime |
| **Data Source** | `DATA_SOURCE` env | `sim` | sim / live / hybrid |
| **Prediction Window** | `PREDICTION_WINDOW_S` env | `60 s` | Forecast horizon |
| **Traffic Policies** | `/api/v1/traffic/*` | — | Throttle / prioritize apps |
| **Routing Rules** | `/api/v1/routing/*` | — | Apply / rollback |

Per-user RBAC overrides which Admin Panel sections are visible.

---

## 25. Quality Targets & Test Cases

### Hard Constraints (from SRS)

| ID | Attribute | Target | Measurement |
|---|---|---|---|
| Req-Qual-Perf-1 | LSTM prediction accuracy | ≥ 90 % | MSE on test set; achieved **MAE 6.94 ms / 2.14 ms / 0.37 %** |
| Req-Qual-Perf-2 | End-to-end traffic steering | < 50 ms | Routing rule application timer |
| Req-Qual-Perf-3 | Digital Twin validation cycle | < 5 s | Sandbox API response time |
| Req-Qual-Perf-4 | IBN UI response | < 2 s | Frontend perf budget |
| Req-Qual-Sec-1 | Data in transit | TLS 1.3+ | nginx config |
| Req-Qual-Sec-2 | Data at rest | AES-256 | DB encryption |
| Req-Qual-Sec-3 | Healthcare deployments | HIPAA audit log | SHA-256 chained log |
| Req-Qual-Use-1 | No CLI required | All admin via UI | Usability checklist |
| Req-Qual-Rel-1 | Platform availability | ≥ 99.9 % | Health checks + restart policy |
| Req-Qual-Rel-2 | Automated failover | Single-component failure tolerated | `restart: always` |
| Req-Qual-Rel-3 | DB backups | Every 24 h | `infra/db/backup.sh` |
| Req-Qual-Scal-1 | Concurrent sites | ≥ 100 | Load test |

### Test Cases (22 mandatory)

| ID | What to Test | Acceptance |
|---|---|---|
| TC-1 | Telemetry ingestion at 1 Hz | ≥ 1 row/sec |
| TC-2 | LSTM prediction accuracy | ≥ 90 % on held-out test |
| TC-3 | Health-score threshold alert | Alert fires within 1 polling cycle |
| TC-4 | SDN flow table modification | ODL + ONOS APIs return 200 |
| TC-5 | End-to-end hitless handoff | < 50 ms, zero packet loss |
| TC-6 | Session state preservation | No TCP session dropped |
| TC-7 | LSTM inference within 1 s | Single inference < 1000 ms |
| TC-8 | Sandbox full validation cycle | < 5 s total |
| TC-9 | Batfish loop detection | Correctly rejects loop-introducing change |
| TC-10 | IBN NLP parsing | > 90 % accuracy on common intents |
| TC-11 | YANG/NETCONF translation | Generated payload accepted by SDN controller |
| TC-12 | Health scoreboard rendering | All link types display at 1920 × 1080 |
| TC-13 | Confidence + reasoning display | Shown on every automated path switch |
| TC-14 | RBAC enforcement | Each role limited to permitted routes |
| TC-15 | Auth credential hashing | bcrypt only, never plaintext |
| TC-16 | Email alert delivery | Email sent on threshold breach |
| TC-17 | Audit log completeness | All event types produce tamper-evident entries |
| TC-18 | 100-site scalability | No degradation with 100 simulated sites |
| TC-19 | Commodity hardware deploy | Successful x86-64 Docker host deploy |
| TC-20 | VMware/KVM deploy | Containers run in virtualized environment |
| TC-21 | Service restart resilience | Auto-reconnect after restart |
| TC-22 | TLS 1.3 enforcement | Sub-TLS-1.3 connections rejected |

---

## 26. Security & Compliance

### Authentication
- bcrypt password hashing
- JWT (HS256) tokens with configurable expiry
- Account lockout after 5 failed attempts
- Generic error messages on failed login

### Authorization
- Role-based access control on every endpoint
- Permission categories enforced via dependency injection
- 5 distinct user roles

### Network Security
- TLS 1.3 enforced via nginx
- HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff
- CSRF protection via JWT bearer tokens (no cookies)
- Rate limiting at the reverse proxy

### Data Security
- AES-256 encryption at rest
- Encrypted credentials and telemetry in TimescaleDB
- Tamper-evident audit log with SHA-256 chaining

### Compliance
- **HIPAA-ready** audit log for healthcare deployments
- All AI routing decisions, health scores, sandbox results, and policy changes recorded
- Integrity verification endpoint for forensic analysis

---

## 27. Project Status

### Fully Implemented
- LSTM prediction engine with real-world calibrated checkpoint (6.94 ms latency MAE)
- Digital twin sandbox (5-stage in-memory validator)
- Intent-Based Networking with NLP parser, 11 actions, lifecycle states, auto-steering
- Autonomous routing rules with rollback
- Application-level QoS (Windows + Linux, 18+ apps)
- Tamper-evident SHA-256 chained audit log
- Real-time alerts with email + dashboard delivery and suppression
- 5-role RBAC with full permission matrix
- 1 Hz WebSocket dashboard
- 8-page React SPA (Login, Dashboard, Simulation, Sandbox, IBN Console, Audit, Reports, Admin)
- Multi-link telemetry with sim / live / hybrid modes
- nginx TLS 1.3 reverse proxy
- Daily TimescaleDB backups
- 5 default seeded users + JWT authentication
- 40+ REST endpoints + WebSocket
- PDF + CSV export for all major datasets

### Partial / Stubbed
- OpenDaylight / ONOS SDN integration (interfaces defined, full runtime under development)
- Real Mininet + Batfish (replaced with high-performance in-memory validator)
- Hardware collectors (code complete; require real devices to validate end-to-end)
- Microservice split (code consolidated into `server/` monolith for simpler dev experience)

---

## 28. Team & Source Documents

### Team Pathfinders
COSC6370-001 — Advanced Software Engineering

- **Vineeth Reddy Kodakandla**
- **Meghana Nalluri**
- **Bharadwaj Jakkula**
- **Sricharitha Katta**

### Source Documents
- **Project Vision Document (PVD)** v1.2 — 02/15/26
- **Software Requirements Specification (SRS)** v1.0 — 03/29/26
- **Project Plan (PP)** v1.0 — 02/24/26

### Authoritative Build Spec
The complete authoritative build specification is in `CLAUDE.md` at the repository root. It defines repository structure, technology stack, all 21 functional requirements, 12 quality targets, 22 test cases, schemas, environment variables, and the build order.

---

*PathWise AI — predictive, autonomous, vendor-agnostic SD-WAN management.*
