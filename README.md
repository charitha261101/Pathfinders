# PathWise AI

**AI-Powered SD-WAN Management Platform**

Team Pathfinders | COSC6370-001 Advanced Software Engineering | Spring 2026

---

## Overview

PathWise AI is an intelligent SD-WAN management system that uses LSTM-based predictive telemetry to proactively optimize network traffic across multiple WAN links. The platform predicts link degradation 30-60 seconds in advance and autonomously steers traffic to maintain service quality — all validated through a digital twin sandbox before production changes.

### Five Core Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Predictive Telemetry Engine** | LSTM model forecasting latency, jitter, and packet loss 30-60s ahead |
| 2 | **Autonomous Traffic Steering** | Make-before-break hitless handoff across WAN links via SDN controllers |
| 3 | **Digital Twin Sandbox** | Mininet + Batfish validation of routing changes in <5 seconds |
| 4 | **Intent-Based Management** | Natural language policy interface ("Prioritize VoIP over guest WiFi") |
| 5 | **Multi-Link Health Scoreboard** | Real-time WebSocket dashboard with D3.js visualizations |

---

## Architecture

```
Frontend (React + D3 + TailwindCSS)
        │  REST / WebSocket
API Gateway (FastAPI)
        │
Core Services ─── Telemetry Ingestion
        │         Prediction Engine (LSTM)
        │         Traffic Steering (SDN)
        │         Digital Twin (Mininet + Batfish)
        │
Data Layer ────── TimescaleDB (telemetry)
                  Redis (state + pub/sub)
                  SDN Controllers (OpenDaylight / ONOS)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, D3.js, TailwindCSS, Zustand |
| API Gateway | FastAPI (Python 3.11+) |
| ML Engine | PyTorch 2.x, LSTM with attention |
| Telemetry Store | TimescaleDB (PostgreSQL) |
| Cache / Pub-Sub | Redis 7+ Streams |
| SDN Controllers | OpenDaylight / ONOS |
| Network Emulation | Mininet |
| Config Validation | Batfish |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### 1. Clone and configure

```bash
git clone <repo-url> pathwise-ai
cd pathwise-ai
cp .env.example .env
```

### 2. Generate synthetic telemetry data

```bash
pip install numpy pandas pyarrow
python ml/scripts/generate_synthetic_data.py --duration-hours 1
```

### 3. Start infrastructure

```bash
docker compose up -d timescaledb redis
```

### 4. Start all services

```bash
docker compose up --build
```

### 5. Access the dashboard

- **Dashboard:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API (Swagger):** http://localhost:8000/redoc

---

## Development

### Run with hot-reload

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Run tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires Redis)
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

### Train the LSTM model

```bash
# Generate 30 days of synthetic data
python ml/scripts/generate_synthetic_data.py

# Train
python ml/scripts/train.py --epochs 100

# Evaluate
python ml/scripts/evaluate.py
```

### Verify project structure

```bash
python build_orchestrator.py
```

---

## Project Structure

```
pathwise-ai/
├── docker-compose.yml          # Full stack orchestration
├── docker-compose.dev.yml      # Dev overrides (hot-reload)
├── build_orchestrator.py       # Project structure validator
├── pyproject.toml              # Python project config
├── .github/workflows/          # CI/CD pipelines
├── services/
│   ├── api-gateway/            # FastAPI application
│   ├── telemetry-ingestion/    # SNMP/NetFlow/gNMI collector
│   ├── prediction-engine/      # LSTM ML service
│   ├── traffic-steering/       # SDN integration service
│   └── digital-twin/           # Mininet + Batfish sandbox
├── frontend/                   # React + D3 dashboard
├── ml/
│   ├── scripts/                # Training & evaluation scripts
│   ├── notebooks/              # Jupyter exploration notebooks
│   └── data/                   # Raw, processed, synthetic data
├── infra/
│   ├── db/                     # TimescaleDB schema
│   ├── mininet/                # Topology definitions
│   └── batfish/                # Network configs
└── tests/
    ├── unit/                   # Component tests
    ├── integration/            # Service-to-service tests
    └── e2e/                    # End-to-end tests
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/telemetry/{link_id}` | Raw telemetry for a link |
| `GET` | `/api/v1/telemetry/links` | List all active links |
| `GET` | `/api/v1/predictions/{link_id}` | Latest prediction + health score |
| `GET` | `/api/v1/predictions/all` | All link predictions |
| `POST` | `/api/v1/steering/execute` | Trigger a steering action |
| `GET` | `/api/v1/steering/history` | Audit log of steering decisions |
| `POST` | `/api/v1/sandbox/validate` | Run sandbox validation |
| `GET` | `/api/v1/sandbox/reports/{id}` | Get validation report |
| `POST` | `/api/v1/policies/intent` | Submit NL policy intent |
| `GET` | `/api/v1/policies/active` | List active policies |
| `DELETE` | `/api/v1/policies/{name}` | Remove a policy |
| `WS` | `/ws/scoreboard` | Real-time health score stream |

---

## Team

| Member | Role | Responsibility |
|--------|------|----------------|
| Vineeth | PM | API Gateway, Docker orchestration, CI/CD, integration |
| Meghana | Requirements | ML pipeline, data engineering, LSTM training |
| Bharadwaj | Design/Test | React dashboard, Health Scoreboard, IBN console, tests |
| Sricharitha | Config/Tech | Mininet/Batfish, SDN integration, steering engine |

---

## License

Academic project — COSC6370-001, Spring 2026.
