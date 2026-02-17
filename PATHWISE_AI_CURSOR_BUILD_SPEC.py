# PATHWISE AI — CURSOR MULTI-AGENT BUILD SPECIFICATION
# ====================================================
# 
# INSTRUCTIONS FOR CURSOR:
# This is a complete specification to build PathWise AI from scratch.
# Follow the AGENT PROTOCOL below. Each agent builds its domain, then
# cross-validates other agents' output. If any agent detects an error,
# it fixes it immediately and logs the correction.
#
# TO START: Run `python build_orchestrator.py` after generating all files.
# ====================================================

"""
╔══════════════════════════════════════════════════════════════════════╗
║                   MULTI-AGENT BUILD ORCHESTRATOR                    ║
║                                                                      ║
║  Agent 1: ARCHITECT    — Project structure, Docker, CI/CD, configs   ║
║  Agent 2: ML_ENGINEER  — LSTM model, training, inference, data       ║
║  Agent 3: BACKEND_DEV  — FastAPI, services, SDN integration          ║
║  Agent 4: FRONTEND_DEV — React dashboard, WebSocket, visualization   ║
║  Agent 5: QA_AGENT     — Tests, validation, cross-agent correction   ║
║                                                                      ║
║  CORRECTION PROTOCOL:                                                ║
║  After each agent completes, QA_AGENT reviews ALL files for:         ║
║    - Import consistency (no missing modules)                         ║
║    - Interface contracts (function signatures match across services)  ║
║    - Type safety (Pydantic models match between producer/consumer)   ║
║    - Docker networking (service names match docker-compose)           ║
║    - Environment variables (consistent across all services)           ║
║    - Port conflicts (no duplicate port bindings)                     ║
║  Any error found → fix immediately → log in CORRECTIONS.md           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ==============================================================================
# PHASE 0: PROJECT STRUCTURE (Agent: ARCHITECT)
# ==============================================================================
# 
# Generate this EXACT directory tree first. Every subsequent file references
# this structure. Do NOT deviate from these paths.
#
# pathwise-ai/
# ├── build_orchestrator.py          ← Run this to verify entire build
# ├── CORRECTIONS.md                 ← Multi-agent correction log
# ├── docker-compose.yml
# ├── docker-compose.dev.yml
# ├── .env                           ← Shared environment variables
# ├── .env.example
# ├── .gitignore
# ├── README.md
# ├── Makefile                       ← Developer convenience commands
# ├── pyproject.toml                 ← Monorepo Python config
# │
# ├── shared/                        ← Shared types, constants, utilities
# │   ├── __init__.py
# │   ├── schemas.py                 ← Pydantic models shared across ALL services
# │   ├── constants.py               ← Thresholds, config values
# │   ├── redis_keys.py              ← ALL Redis key patterns in one place
# │   └── exceptions.py
# │
# ├── services/
# │   ├── api_gateway/
# │   │   ├── Dockerfile
# │   │   ├── requirements.txt
# │   │   └── app/
# │   │       ├── __init__.py
# │   │       ├── main.py
# │   │       ├── config.py
# │   │       ├── dependencies.py
# │   │       ├── routers/
# │   │       │   ├── __init__.py
# │   │       │   ├── telemetry.py
# │   │       │   ├── predictions.py
# │   │       │   ├── steering.py
# │   │       │   ├── sandbox.py
# │   │       │   └── policies.py
# │   │       ├── websocket/
# │   │       │   ├── __init__.py
# │   │       │   └── scoreboard.py
# │   │       └── middleware/
# │   │           ├── __init__.py
# │   │           └── error_handler.py
# │   │
# │   ├── telemetry_ingestion/
# │   │   ├── Dockerfile
# │   │   ├── requirements.txt
# │   │   └── app/
# │   │       ├── __init__.py
# │   │       ├── main.py
# │   │       ├── collector.py
# │   │       ├── parsers/
# │   │       │   ├── __init__.py
# │   │       │   ├── snmp_parser.py
# │   │       │   └── netflow_parser.py
# │   │       └── db_writer.py
# │   │
# │   ├── prediction_engine/
# │   │   ├── Dockerfile
# │   │   ├── requirements.txt
# │   │   └── app/
# │   │       ├── __init__.py
# │   │       ├── main.py
# │   │       ├── serve.py
# │   │       └── model/
# │   │           ├── __init__.py
# │   │           ├── lstm_network.py
# │   │           ├── feature_engineering.py
# │   │           ├── trainer.py
# │   │           ├── inference.py
# │   │           └── health_score.py
# │   │
# │   ├── traffic_steering/
# │   │   ├── Dockerfile
# │   │   ├── requirements.txt
# │   │   └── app/
# │   │       ├── __init__.py
# │   │       ├── main.py
# │   │       ├── steering_engine.py
# │   │       ├── sdn_clients/
# │   │       │   ├── __init__.py
# │   │       │   ├── base.py
# │   │       │   ├── opendaylight.py
# │   │       │   └── onos.py
# │   │       └── flow_manager.py
# │   │
# │   └── digital_twin/
# │       ├── Dockerfile
# │       ├── requirements.txt
# │       └── app/
# │           ├── __init__.py
# │           ├── main.py
# │           ├── twin_manager.py
# │           ├── mininet_topology.py
# │           └── batfish_validator.py
# │
# ├── frontend/
# │   ├── Dockerfile
# │   ├── package.json
# │   ├── tsconfig.json
# │   ├── tailwind.config.js
# │   ├── vite.config.ts
# │   ├── index.html
# │   └── src/
# │       ├── main.tsx
# │       ├── App.tsx
# │       ├── vite-env.d.ts
# │       ├── types/
# │       │   └── index.ts
# │       ├── services/
# │       │   ├── api.ts
# │       │   └── websocket.ts
# │       ├── store/
# │       │   └── useStore.ts
# │       ├── hooks/
# │       │   ├── useWebSocket.ts
# │       │   └── useTelemetry.ts
# │       ├── pages/
# │       │   ├── Dashboard.tsx
# │       │   ├── PolicyManager.tsx
# │       │   └── SandboxViewer.tsx
# │       └── components/
# │           ├── Layout/
# │           │   ├── Sidebar.tsx
# │           │   └── Header.tsx
# │           ├── HealthScoreboard/
# │           │   ├── HealthScoreboard.tsx
# │           │   ├── LinkCard.tsx
# │           │   └── ForecastSparkline.tsx
# │           ├── IBNConsole/
# │           │   ├── IBNConsole.tsx
# │           │   └── PolicyList.tsx
# │           ├── TopologyMap/
# │           │   └── TopologyMap.tsx
# │           └── SteeringLog/
# │               └── SteeringLog.tsx
# │
# ├── ml/
# │   ├── scripts/
# │   │   ├── generate_synthetic_data.py
# │   │   ├── train.py
# │   │   └── evaluate.py
# │   ├── data/
# │   │   ├── synthetic/           ← Generated parquet files
# │   │   └── processed/           ← Feature-engineered datasets
# │   └── checkpoints/             ← Trained model weights
# │
# ├── infra/
# │   ├── db/
# │   │   └── init.sql
# │   ├── mininet/
# │   │   ├── Dockerfile
# │   │   └── topologies/
# │   │       └── default_topo.py
# │   └── nginx/
# │       └── nginx.conf
# │
# └── tests/
#     ├── conftest.py
#     ├── unit/
#     │   ├── test_feature_engineering.py
#     │   ├── test_lstm_model.py
#     │   ├── test_intent_parser.py
#     │   ├── test_health_score.py
#     │   ├── test_steering_engine.py
#     │   └── test_flow_manager.py
#     ├── integration/
#     │   ├── test_telemetry_pipeline.py
#     │   ├── test_prediction_pipeline.py
#     │   ├── test_steering_pipeline.py
#     │   └── test_sandbox_pipeline.py
#     └── e2e/
#         └── test_full_flow.py


# ==============================================================================
# FILE 1: shared/schemas.py
# ==============================================================================
# CRITICAL: This is the SINGLE SOURCE OF TRUTH for all data types.
# Every service imports from here. Never redefine these models elsewhere.
# QA_AGENT: verify every service imports from shared.schemas, not local copies.

SHARED_SCHEMAS = '''
"""
PathWise AI — Shared Pydantic Schemas
Single source of truth for all data contracts across services.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum
from datetime import datetime


# ─── Telemetry ────────────────────────────────────────────────────────────────

class TelemetryPoint(BaseModel):
    """Raw telemetry from a single network link at one point in time."""
    timestamp: datetime
    link_id: str
    latency_ms: float = Field(ge=0)
    jitter_ms: float = Field(ge=0)
    packet_loss_pct: float = Field(ge=0, le=100)
    bandwidth_util_pct: float = Field(ge=0, le=100)
    rtt_ms: float = Field(ge=0)

class TelemetryBatch(BaseModel):
    """Batch of telemetry points for bulk ingestion."""
    points: list[TelemetryPoint]
    source: str = "snmp"


# ─── Predictions ──────────────────────────────────────────────────────────────

class PredictionResult(BaseModel):
    """Output of the LSTM prediction engine for one link."""
    link_id: str
    timestamp: datetime
    health_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    latency_forecast: list[float]       # 30 values, one per second
    jitter_forecast: list[float]
    packet_loss_forecast: list[float]
    trend: Literal["improving", "stable", "degrading"]

    @validator("latency_forecast", "jitter_forecast", "packet_loss_forecast")
    def forecast_length(cls, v):
        if len(v) != 30:
            raise ValueError("Forecast must contain exactly 30 values")
        return v


# ─── Steering ─────────────────────────────────────────────────────────────────

class SteeringAction(str, Enum):
    HOLD = "hold"
    PREEMPTIVE_SHIFT = "shift"
    EMERGENCY_FAILOVER = "failover"
    REBALANCE = "rebalance"

class TrafficClass(str, Enum):
    VOIP = "voip"
    VIDEO = "video"
    CRITICAL = "critical"
    MEDICAL = "medical_imaging"
    FINANCIAL = "financial"
    BULK = "bulk"
    GUEST = "guest_wifi"

class SteeringDecision(BaseModel):
    """A decision to move traffic from one link to another."""
    id: Optional[str] = None
    action: SteeringAction
    source_link: str
    target_link: str
    traffic_classes: list[TrafficClass]
    confidence: float = Field(ge=0, le=1)
    reason: str
    requires_sandbox: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SteeringAuditEntry(BaseModel):
    """Immutable audit log of a steering action."""
    decision: SteeringDecision
    sandbox_validated: Optional[bool] = None
    sandbox_report_id: Optional[str] = None
    executed: bool = False
    execution_time_ms: Optional[float] = None
    status: Literal["pending", "validated", "blocked", "executed", "failed"]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Sandbox ──────────────────────────────────────────────────────────────────

class ValidationResult(str, Enum):
    PASS = "pass"
    FAIL_LOOP = "fail_loop"
    FAIL_POLICY = "fail_policy"
    FAIL_UNREACHABLE = "fail_unreachable"
    FAIL_TIMEOUT = "fail_timeout"

class SandboxReport(BaseModel):
    """Result of validating a steering decision in the Digital Twin."""
    id: Optional[str] = None
    result: ValidationResult
    details: str
    loop_free: bool
    policy_compliant: bool
    reachability_verified: bool
    execution_time_ms: float
    decision_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── IBN / Policies ──────────────────────────────────────────────────────────

class PolicyAction(str, Enum):
    PRIORITIZE = "prioritize"
    THROTTLE = "throttle"
    BLOCK = "block"
    REDIRECT = "redirect"
    GUARANTEE_BW = "guarantee_bw"
    LIMIT_LATENCY = "limit_latency"

class PolicyRule(BaseModel):
    """A parsed network policy rule from an IBN intent."""
    name: str
    traffic_class: str
    priority: int = Field(ge=0, le=1000)
    bandwidth_guarantee_mbps: Optional[float] = None
    latency_max_ms: Optional[float] = None
    action: PolicyAction
    target_links: list[str] = ["all"]
    active: bool = True

class IntentRequest(BaseModel):
    """Natural language intent input."""
    intent: str = Field(min_length=5, max_length=500)

class IntentResponse(BaseModel):
    """Result of parsing and applying a natural language intent."""
    status: Literal["applied", "failed", "pending_validation"]
    intent: str
    rules: list[PolicyRule]
    validation_results: list[dict] = []
    error: Optional[str] = None


# ─── Scoreboard (WebSocket payloads) ─────────────────────────────────────────

class LinkHealthSnapshot(BaseModel):
    """Real-time health data for one link, pushed via WebSocket."""
    link_id: str
    health_score: float
    confidence: float
    latency_current: float
    jitter_current: float
    packet_loss_current: float
    bandwidth_util_current: float
    latency_forecast: list[float]
    trend: Literal["improving", "stable", "degrading"]

class ScoreboardUpdate(BaseModel):
    """WebSocket message: full scoreboard state."""
    type: Literal["scoreboard_update"] = "scoreboard_update"
    links: dict[str, LinkHealthSnapshot]
    timestamp: float

class SteeringEvent(BaseModel):
    """WebSocket message: a steering action occurred."""
    type: Literal["steering_event"] = "steering_event"
    decision: SteeringDecision
    sandbox_result: Optional[ValidationResult] = None


# ─── Network Topology ────────────────────────────────────────────────────────

class NetworkSwitch(BaseModel):
    id: str
    dpid: str
    name: Optional[str] = None

class NetworkHost(BaseModel):
    id: str
    ip: str
    name: Optional[str] = None

class NetworkLink(BaseModel):
    src: str
    dst: str
    link_id: str
    bw_mbps: float = 100
    delay_ms: float = 5
    loss_pct: float = 0

class NetworkTopology(BaseModel):
    """Complete network topology snapshot."""
    switches: list[NetworkSwitch]
    hosts: list[NetworkHost]
    links: list[NetworkLink]
'''


# ==============================================================================
# FILE 2: shared/constants.py
# ==============================================================================

SHARED_CONSTANTS = '''
"""
PathWise AI — Global Constants
All thresholds, magic numbers, and configuration in one place.
QA_AGENT: If any service hardcodes a threshold, flag it and move here.
"""

# ─── Telemetry ────────────────────────────────────────────────────────────────
TELEMETRY_POLL_INTERVAL_SEC = 1.0
TELEMETRY_STREAM_MAX_LEN = 86400       # 24h at 1Hz
TELEMETRY_RETENTION_RAW_DAYS = 7
TELEMETRY_RETENTION_AGG_DAYS = 90
TELEMETRY_AGG_BUCKET_SEC = 10

# ─── LSTM Model ───────────────────────────────────────────────────────────────
LSTM_INPUT_WINDOW = 60                  # 60 timesteps (seconds) input
LSTM_HORIZON = 30                       # predict 30 steps ahead
LSTM_NUM_FEATURES = 13
LSTM_HIDDEN_SIZE = 128
LSTM_NUM_LAYERS = 2
LSTM_DROPOUT = 0.2
LSTM_BATCH_SIZE = 256
LSTM_MAX_EPOCHS = 100
LSTM_PATIENCE = 10
LSTM_LEARNING_RATE = 1e-3
LSTM_WEIGHT_DECAY = 1e-4
LSTM_UNDERESTIMATE_PENALTY = 2.0
LSTM_LOSS_WEIGHTS = {"latency": 1.0, "jitter": 1.0, "packet_loss": 2.0}

# ─── Health Score ─────────────────────────────────────────────────────────────
HEALTH_LATENCY_GOOD_MS = 30
HEALTH_LATENCY_BAD_MS = 200
HEALTH_JITTER_GOOD_MS = 5
HEALTH_JITTER_BAD_MS = 50
HEALTH_LOSS_GOOD_PCT = 0.1
HEALTH_LOSS_BAD_PCT = 5.0
HEALTH_WEIGHT_LATENCY = 0.4
HEALTH_WEIGHT_JITTER = 0.3
HEALTH_WEIGHT_LOSS = 0.3
HEALTH_CONFIDENCE_FLOOR = 0.5          # min confidence contribution

# ─── Steering Thresholds ─────────────────────────────────────────────────────
STEERING_CRITICAL_THRESHOLD = 30       # health_score < this → emergency
STEERING_WARNING_THRESHOLD = 50        # health_score < this → preemptive shift
STEERING_CONFIDENCE_MIN = 0.7          # min confidence to act preemptively
STEERING_REBALANCE_VARIANCE = 30       # score variance trigger

# ─── Sandbox ──────────────────────────────────────────────────────────────────
SANDBOX_TIMEOUT_SEC = 5.0              # PVD quality requirement
SANDBOX_TRAFFIC_TEST_TIMEOUT_SEC = 3.0

# ─── SDN ──────────────────────────────────────────────────────────────────────
SDN_FLOW_PRIORITY_HIGH = 200
SDN_FLOW_PRIORITY_NORMAL = 100
SDN_FLOW_PRIORITY_LOW = 50
SDN_HANDOFF_VERIFY_TIMEOUT_SEC = 2.0

# ─── IBN Intent Parser ───────────────────────────────────────────────────────
IBN_MAX_RULES_PER_INTENT = 5

# ─── API ──────────────────────────────────────────────────────────────────────
API_DEFAULT_PAGE_SIZE = 50
API_MAX_PAGE_SIZE = 200
WEBSOCKET_BROADCAST_INTERVAL_SEC = 1.0
'''


# ==============================================================================
# FILE 3: shared/redis_keys.py
# ==============================================================================

SHARED_REDIS_KEYS = '''
"""
PathWise AI — Redis Key Registry
Every Redis key used anywhere in the system is defined here.
QA_AGENT: If any service constructs a Redis key not listed here, flag it.
"""

# Sets
ACTIVE_LINKS = "pathwise:active_links"

# Streams
TELEMETRY_RAW_STREAM = "pathwise:telemetry:raw"
DEGRADATION_ALERTS_STREAM = "pathwise:alerts:degradation"
STEERING_EVENTS_STREAM = "pathwise:events:steering"

# Hashes (per link)
def prediction_key(link_id: str) -> str:
    return f"pathwise:prediction:{link_id}"

def link_config_key(link_id: str) -> str:
    return f"pathwise:link_config:{link_id}"

# Sorted Sets
STEERING_AUDIT_LOG = "pathwise:audit:steering"

# Simple keys
def sandbox_report_key(report_id: str) -> str:
    return f"pathwise:sandbox:report:{report_id}"

# Lists
ACTIVE_POLICIES = "pathwise:policies:active"

def policy_key(policy_name: str) -> str:
    return f"pathwise:policy:{policy_name}"

# Consumer groups
TELEMETRY_CONSUMER_GROUP = "pathwise:cg:telemetry"
ALERTS_CONSUMER_GROUP = "pathwise:cg:alerts"
'''


# ==============================================================================
# FILE 4: .env
# ==============================================================================

ENV_FILE = '''
# PathWise AI Environment Variables
# QA_AGENT: verify every service reads from these, never hardcodes values

# ─── Database ─────────────────────────────────────────────────────────────────
POSTGRES_DB=pathwise
POSTGRES_USER=pathwise
POSTGRES_PASSWORD=pathwise_dev_2026
DATABASE_URL=postgresql://pathwise:pathwise_dev_2026@timescaledb:5432/pathwise

# ─── Redis ────────────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── SDN Controller ──────────────────────────────────────────────────────────
SDN_CONTROLLER_TYPE=opendaylight
ODL_BASE_URL=http://opendaylight:8181
ODL_USERNAME=admin
ODL_PASSWORD=admin
ONOS_BASE_URL=http://onos:8181/onos/v1
ONOS_USERNAME=onos
ONOS_PASSWORD=rocks

# ─── Batfish ──────────────────────────────────────────────────────────────────
BATFISH_HOST=batfish
BATFISH_PORT=9997

# ─── Model ────────────────────────────────────────────────────────────────────
MODEL_PATH=/models/best_model.pt
MODEL_DEVICE=cpu

# ─── API ──────────────────────────────────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ─── Frontend ─────────────────────────────────────────────────────────────────
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
'''


# ==============================================================================
# FILE 5: docker-compose.yml
# ==============================================================================

DOCKER_COMPOSE = '''
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════
  # DATA LAYER
  # ═══════════════════════════════════════════════════════════════════

  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: pathwise-db
    env_file: .env
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./infra/db/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pathwise"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: pathwise-redis
    ports:
      - "6379:6379"
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ═══════════════════════════════════════════════════════════════════
  # SDN & NETWORK EMULATION
  # ═══════════════════════════════════════════════════════════════════

  opendaylight:
    image: opendaylight/odl:0.18.2
    container_name: pathwise-odl
    ports:
      - "6633:6633"
      - "6653:6653"
      - "8181:8181"
    environment:
      - FEATURES=odl-restconf,odl-l2switch-switch-ui,odl-openflowplugin-flow-services-ui
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8181/restconf/operational/network-topology:network-topology || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 120s

  batfish:
    image: batfish/allinone:latest
    container_name: pathwise-batfish
    ports:
      - "9997:9997"
      - "9996:9996"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9996/v2/status || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ═══════════════════════════════════════════════════════════════════
  # APPLICATION SERVICES
  # ═══════════════════════════════════════════════════════════════════

  api-gateway:
    build:
      context: .
      dockerfile: services/api_gateway/Dockerfile
    container_name: pathwise-api
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    volumes:
      - ./shared:/app/shared:ro
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  telemetry-ingestion:
    build:
      context: .
      dockerfile: services/telemetry_ingestion/Dockerfile
    container_name: pathwise-telemetry
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    volumes:
      - ./shared:/app/shared:ro

  prediction-engine:
    build:
      context: .
      dockerfile: services/prediction_engine/Dockerfile
    container_name: pathwise-prediction
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./shared:/app/shared:ro
      - ./ml/checkpoints:/models:ro

  traffic-steering:
    build:
      context: .
      dockerfile: services/traffic_steering/Dockerfile
    container_name: pathwise-steering
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      api-gateway:
        condition: service_healthy
    volumes:
      - ./shared:/app/shared:ro

  digital-twin:
    build:
      context: .
      dockerfile: services/digital_twin/Dockerfile
    container_name: pathwise-twin
    privileged: true
    env_file: .env
    depends_on:
      batfish:
        condition: service_healthy
    volumes:
      - ./shared:/app/shared:ro

  # ═══════════════════════════════════════════════════════════════════
  # FRONTEND
  # ═══════════════════════════════════════════════════════════════════

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: pathwise-frontend
    ports:
      - "3000:3000"
    depends_on:
      api-gateway:
        condition: service_healthy
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000

volumes:
  timescale_data:
  redis_data:
'''


# ==============================================================================
# FILE 6: infra/db/init.sql
# ==============================================================================

DB_INIT_SQL = '''
-- PathWise AI Database Initialization
-- TimescaleDB hypertables and schemas

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─── Raw Telemetry (1Hz per link) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS telemetry (
    time                TIMESTAMPTZ     NOT NULL,
    link_id             TEXT            NOT NULL,
    latency_ms          DOUBLE PRECISION,
    jitter_ms           DOUBLE PRECISION,
    packet_loss_pct     DOUBLE PRECISION,
    bandwidth_util_pct  DOUBLE PRECISION,
    rtt_ms              DOUBLE PRECISION
);

SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_telemetry_link_time ON telemetry (link_id, time DESC);

-- ─── 10-Second Aggregates (for ML training) ──────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_10s
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('10 seconds', time) AS bucket,
    link_id,
    AVG(latency_ms)             AS avg_latency,
    STDDEV(latency_ms)          AS std_latency,
    MAX(latency_ms)             AS max_latency,
    AVG(jitter_ms)              AS avg_jitter,
    MAX(jitter_ms)              AS max_jitter,
    AVG(packet_loss_pct)        AS avg_packet_loss,
    MAX(packet_loss_pct)        AS max_packet_loss,
    AVG(bandwidth_util_pct)     AS avg_bw_util,
    AVG(rtt_ms)                 AS avg_rtt
FROM telemetry
GROUP BY bucket, link_id
WITH NO DATA;

-- ─── Retention Policies ──────────────────────────────────────────────────────
SELECT add_retention_policy('telemetry', INTERVAL '7 days', if_not_exists => TRUE);

-- ─── Steering Audit Log ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS steering_audit (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    action          TEXT            NOT NULL,
    source_link     TEXT            NOT NULL,
    target_link     TEXT            NOT NULL,
    traffic_classes TEXT[]          NOT NULL,
    confidence      DOUBLE PRECISION,
    reason          TEXT,
    sandbox_result  TEXT,
    status          TEXT            NOT NULL,
    execution_ms    DOUBLE PRECISION
);

-- ─── Sandbox Reports ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sandbox_reports (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    result          TEXT            NOT NULL,
    details         TEXT,
    loop_free       BOOLEAN,
    policy_compliant BOOLEAN,
    reachability    BOOLEAN,
    execution_ms    DOUBLE PRECISION,
    decision_id     INTEGER
);

-- ─── Active Policies ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS policies (
    id              SERIAL PRIMARY KEY,
    name            TEXT            UNIQUE NOT NULL,
    traffic_class   TEXT            NOT NULL,
    priority        INTEGER         NOT NULL,
    action          TEXT            NOT NULL,
    bw_guarantee    DOUBLE PRECISION,
    latency_max     DOUBLE PRECISION,
    target_links    TEXT[]          DEFAULT ARRAY['all'],
    active          BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    intent_text     TEXT
);
'''


# ==============================================================================
# FILE 7: services/prediction_engine/app/model/lstm_network.py
# ==============================================================================

LSTM_NETWORK = '''
"""
PathWise LSTM Neural Network
Agent: ML_ENGINEER
QA_AGENT: Verify constants imported from shared.constants, not hardcoded.
"""
import torch
import torch.nn as nn
import sys
sys.path.insert(0, "/app")
from shared.constants import (
    LSTM_NUM_FEATURES, LSTM_HIDDEN_SIZE, LSTM_NUM_LAYERS,
    LSTM_DROPOUT, LSTM_HORIZON, LSTM_LOSS_WEIGHTS,
    LSTM_UNDERESTIMATE_PENALTY,
)


class PathWiseLSTM(nn.Module):
    """
    Multi-output LSTM for network telemetry forecasting.

    Architecture:
    - 2-layer stacked LSTM with dropout
    - Temporal attention over all hidden states
    - Separate prediction heads for latency, jitter, packet_loss
    - Confidence estimation head for health score weighting
    """

    def __init__(
        self,
        input_size: int = LSTM_NUM_FEATURES,
        hidden_size: int = LSTM_HIDDEN_SIZE,
        num_layers: int = LSTM_NUM_LAYERS,
        dropout: float = LSTM_DROPOUT,
        horizon: int = LSTM_HORIZON,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.horizon = horizon

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        self.attention = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

        self.latency_head = self._make_head(hidden_size, horizon, dropout)
        self.jitter_head = self._make_head(hidden_size, horizon, dropout)
        self.packet_loss_head = self._make_head(hidden_size, horizon, dropout)

        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    @staticmethod
    def _make_head(in_features: int, out_features: int, dropout: float) -> nn.Module:
        return nn.Sequential(
            nn.Linear(in_features, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, out_features),
        )

    def forward(self, x: torch.Tensor) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
        """
        Args:
            x: (batch, seq_len=60, features=13)
        Returns:
            predictions: {"latency": (B, 30), "jitter": (B, 30), "packet_loss": (B, 30)}
            confidence:  (B, 1)
        """
        lstm_out, _ = self.lstm(x)

        attn_weights = self.attention(lstm_out)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = (lstm_out * attn_weights).sum(dim=1)

        predictions = {
            "latency": self.latency_head(context),
            "jitter": self.jitter_head(context),
            "packet_loss": self.packet_loss_head(context),
        }
        confidence = self.confidence_head(context)

        return predictions, confidence


class PathWiseLoss(nn.Module):
    """
    Asymmetric MSE loss: penalizes underestimation of degradation harder.
    Missing a real brownout is worse than a false alarm.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        underestimate_penalty: float = LSTM_UNDERESTIMATE_PENALTY,
    ):
        super().__init__()
        self.weights = weights or LSTM_LOSS_WEIGHTS.copy()
        self.penalty = underestimate_penalty

    def forward(self, preds: dict[str, torch.Tensor], targets: torch.Tensor) -> torch.Tensor:
        """
        preds:   {"latency": (B, H), "jitter": (B, H), "packet_loss": (B, H)}
        targets: (B, H, 3) — latency, jitter, packet_loss
        """
        total_loss = torch.tensor(0.0, device=targets.device)
        target_map = {"latency": 0, "jitter": 1, "packet_loss": 2}

        for key, weight in self.weights.items():
            pred = preds[key]
            target = targets[:, :, target_map[key]]
            error = pred - target
            mse = error ** 2
            underestimate_mask = (error < 0).float()
            asymmetric = mse * (1 + underestimate_mask * (self.penalty - 1))
            total_loss = total_loss + weight * asymmetric.mean()

        return total_loss
'''


# ==============================================================================
# FILE 8: services/prediction_engine/app/model/feature_engineering.py
# ==============================================================================

FEATURE_ENGINEERING = '''
"""
Feature Engineering Pipeline
Agent: ML_ENGINEER
"""
import numpy as np
import pandas as pd
from typing import Tuple
import sys
sys.path.insert(0, "/app")
from shared.constants import LSTM_INPUT_WINDOW, LSTM_HORIZON, LSTM_NUM_FEATURES


class FeatureEngineer:
    """
    Transforms raw telemetry into LSTM-ready sequences.

    Feature vector per timestep (13 features):
      [0]  latency_ms
      [1]  jitter_ms
      [2]  packet_loss_pct
      [3]  bandwidth_util_pct
      [4]  rtt_ms
      [5]  mean_latency_30s    (rolling mean)
      [6]  std_latency_30s     (rolling std)
      [7]  mean_jitter_30s     (rolling mean)
      [8]  ema_latency         (alpha=0.3)
      [9]  ema_packet_loss     (alpha=0.3)
      [10] d_latency           (first derivative)
      [11] d_jitter            (first derivative)
      [12] d_packet_loss       (first derivative)
    """

    FEATURE_COLS = [
        "latency_ms", "jitter_ms", "packet_loss_pct",
        "bandwidth_util_pct", "rtt_ms",
        "mean_latency_30s", "std_latency_30s", "mean_jitter_30s",
        "ema_latency", "ema_packet_loss",
        "d_latency", "d_jitter", "d_packet_loss",
    ]
    TARGET_COLS = ["latency_ms", "jitter_ms", "packet_loss_pct"]

    def __init__(self):
        self.scalers: dict[str, dict] = {}

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add engineered features to raw telemetry DataFrame."""
        df = df.sort_values("time").copy()

        # Rolling 30s window
        df["mean_latency_30s"] = df["latency_ms"].rolling(30, min_periods=1).mean()
        df["std_latency_30s"] = df["latency_ms"].rolling(30, min_periods=1).std().fillna(0)
        df["mean_jitter_30s"] = df["jitter_ms"].rolling(30, min_periods=1).mean()

        # EMA
        df["ema_latency"] = df["latency_ms"].ewm(alpha=0.3, adjust=False).mean()
        df["ema_packet_loss"] = df["packet_loss_pct"].ewm(alpha=0.3, adjust=False).mean()

        # Derivatives
        df["d_latency"] = df["latency_ms"].diff().fillna(0)
        df["d_jitter"] = df["jitter_ms"].diff().fillna(0)
        df["d_packet_loss"] = df["packet_loss_pct"].diff().fillna(0)

        return df

    def create_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sliding-window sequences for training.
        Returns:
            X: (N, LSTM_INPUT_WINDOW, LSTM_NUM_FEATURES)
            y: (N, LSTM_HORIZON, 3)
        """
        features = df[self.FEATURE_COLS].values
        targets = df[self.TARGET_COLS].values

        X, y = [], []
        total = len(features) - LSTM_INPUT_WINDOW - LSTM_HORIZON
        for i in range(total):
            X.append(features[i : i + LSTM_INPUT_WINDOW])
            y.append(targets[i + LSTM_INPUT_WINDOW : i + LSTM_INPUT_WINDOW + LSTM_HORIZON])

        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    def normalize(self, X: np.ndarray, link_id: str, fit: bool = True) -> np.ndarray:
        """Per-link min-max normalization to [0, 1]."""
        flat = X.reshape(-1, X.shape[-1])
        if fit:
            self.scalers[link_id] = {
                "min": flat.min(axis=0),
                "max": flat.max(axis=0),
            }
        s = self.scalers[link_id]
        denom = s["max"] - s["min"]
        denom[denom == 0] = 1.0
        return (X - s["min"]) / denom

    def denormalize(self, X: np.ndarray, link_id: str) -> np.ndarray:
        """Reverse normalization."""
        s = self.scalers[link_id]
        denom = s["max"] - s["min"]
        denom[denom == 0] = 1.0
        return X * denom + s["min"]

    def build_realtime_window(self, points: list[dict]) -> np.ndarray | None:
        """
        Convert list of raw telemetry dicts (from Redis) into a feature window.
        Used for inference, not training.
        """
        if len(points) < LSTM_INPUT_WINDOW:
            return None

        df = pd.DataFrame(points[-LSTM_INPUT_WINDOW - 30:])  # extra 30 for rolling warmup
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        df = self.compute_features(df)
        window = df[self.FEATURE_COLS].values[-LSTM_INPUT_WINDOW:]

        if window.shape != (LSTM_INPUT_WINDOW, LSTM_NUM_FEATURES):
            return None

        return window.astype(np.float32)
'''


# ==============================================================================
# FILE 9: services/prediction_engine/app/model/health_score.py
# ==============================================================================

HEALTH_SCORE = '''
"""
Health Score Calculator
Agent: ML_ENGINEER
"""
import numpy as np
import sys
sys.path.insert(0, "/app")
from shared.constants import (
    HEALTH_LATENCY_GOOD_MS, HEALTH_LATENCY_BAD_MS,
    HEALTH_JITTER_GOOD_MS, HEALTH_JITTER_BAD_MS,
    HEALTH_LOSS_GOOD_PCT, HEALTH_LOSS_BAD_PCT,
    HEALTH_WEIGHT_LATENCY, HEALTH_WEIGHT_JITTER, HEALTH_WEIGHT_LOSS,
    HEALTH_CONFIDENCE_FLOOR,
)


def compute_health_score(
    latency_forecast: np.ndarray,
    jitter_forecast: np.ndarray,
    packet_loss_forecast: np.ndarray,
    confidence: float,
) -> float:
    """
    Composite health score (0-100).

    Averaging over the forecast horizon, then weighting by metric importance
    and scaling by prediction confidence.
    """
    lat = float(np.mean(latency_forecast))
    jit = float(np.mean(jitter_forecast))
    pkt = float(np.mean(packet_loss_forecast))

    lat_score = _linear_score(lat, HEALTH_LATENCY_GOOD_MS, HEALTH_LATENCY_BAD_MS)
    jit_score = _linear_score(jit, HEALTH_JITTER_GOOD_MS, HEALTH_JITTER_BAD_MS)
    pkt_score = _linear_score(pkt, HEALTH_LOSS_GOOD_PCT, HEALTH_LOSS_BAD_PCT)

    raw = (
        HEALTH_WEIGHT_LATENCY * lat_score +
        HEALTH_WEIGHT_JITTER * jit_score +
        HEALTH_WEIGHT_LOSS * pkt_score
    )

    # Discount by confidence (floor prevents zeroing out)
    scaled = raw * (HEALTH_CONFIDENCE_FLOOR + (1 - HEALTH_CONFIDENCE_FLOOR) * confidence)
    return round(max(0.0, min(100.0, scaled)), 1)


def compute_trend(
    current_score: float,
    previous_scores: list[float],
    window: int = 10,
) -> str:
    """Determine trend direction over last N scores."""
    if len(previous_scores) < window:
        return "stable"
    recent = previous_scores[-window:]
    avg_recent = sum(recent) / len(recent)
    delta = current_score - avg_recent
    if delta > 3:
        return "improving"
    elif delta < -3:
        return "degrading"
    return "stable"


def _linear_score(value: float, good_threshold: float, bad_threshold: float) -> float:
    """Linear interpolation: good=100, bad=0, clamped."""
    if value <= good_threshold:
        return 100.0
    if value >= bad_threshold:
        return 0.0
    return 100.0 * (1 - (value - good_threshold) / (bad_threshold - good_threshold))
'''


# ==============================================================================
# FILE 10: services/prediction_engine/app/model/trainer.py
# ==============================================================================

TRAINER = '''
"""
LSTM Training Pipeline
Agent: ML_ENGINEER
"""
import torch
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import logging
import json
from datetime import datetime
import sys
sys.path.insert(0, "/app")
from shared.constants import (
    LSTM_BATCH_SIZE, LSTM_MAX_EPOCHS, LSTM_PATIENCE,
    LSTM_LEARNING_RATE, LSTM_WEIGHT_DECAY,
)
from app.model.lstm_network import PathWiseLSTM, PathWiseLoss

logger = logging.getLogger(__name__)


class LSTMTrainer:
    """
    Training loop with:
    - AdamW optimizer
    - ReduceLROnPlateau scheduler
    - Early stopping
    - Best-model checkpointing
    - Training metrics export (JSON)
    """

    def __init__(
        self,
        model: PathWiseLSTM,
        checkpoint_dir: str = "./checkpoints",
        device: str | None = None,
    ):
        self.model = model
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model.to(self.device)

        self.optimizer = torch.optim.AdamW(
            model.parameters(), lr=LSTM_LEARNING_RATE, weight_decay=LSTM_WEIGHT_DECAY
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=5
        )
        self.criterion = PathWiseLoss()

    def train(self, X_train, y_train, X_val, y_val) -> dict:
        """Full training loop. Returns history dict."""
        train_loader = DataLoader(
            TensorDataset(torch.tensor(X_train), torch.tensor(y_train)),
            batch_size=LSTM_BATCH_SIZE, shuffle=True, drop_last=True,
        )
        val_loader = DataLoader(
            TensorDataset(torch.tensor(X_val), torch.tensor(y_val)),
            batch_size=LSTM_BATCH_SIZE, shuffle=False,
        )

        best_val_loss = float("inf")
        no_improve = 0
        history = {"train_loss": [], "val_loss": [], "lr": []}

        for epoch in range(LSTM_MAX_EPOCHS):
            # ── Train ──
            self.model.train()
            train_loss = 0.0
            for X_b, y_b in train_loader:
                X_b, y_b = X_b.to(self.device), y_b.to(self.device)
                self.optimizer.zero_grad()
                preds, _ = self.model(X_b)
                loss = self.criterion(preds, y_b)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                train_loss += loss.item()
            train_loss /= len(train_loader)

            # ── Validate ──
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for X_b, y_b in val_loader:
                    X_b, y_b = X_b.to(self.device), y_b.to(self.device)
                    preds, _ = self.model(X_b)
                    loss = self.criterion(preds, y_b)
                    val_loss += loss.item()
            val_loss /= len(val_loader)

            lr = self.optimizer.param_groups[0]["lr"]
            self.scheduler.step(val_loss)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["lr"].append(lr)

            logger.info(
                f"Epoch {epoch+1}/{LSTM_MAX_EPOCHS} | "
                f"Train: {train_loss:.6f} | Val: {val_loss:.6f} | LR: {lr:.2e}"
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                no_improve = 0
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": val_loss,
                    "timestamp": datetime.utcnow().isoformat(),
                }, self.checkpoint_dir / "best_model.pt")
                logger.info(f"  → Saved best model (val_loss={val_loss:.6f})")
            else:
                no_improve += 1
                if no_improve >= LSTM_PATIENCE:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

        # Save training history
        with open(self.checkpoint_dir / "training_history.json", "w") as f:
            json.dump(history, f, indent=2)

        return history
'''


# ==============================================================================
# FILE 11: ml/scripts/generate_synthetic_data.py
# ==============================================================================

SYNTHETIC_DATA_GENERATOR = '''
"""
Synthetic Telemetry Data Generator
Agent: ML_ENGINEER

Generates realistic network telemetry with:
- Diurnal traffic patterns
- Brownout events (gradual degradation)
- Congestion-correlated packet loss
- Link-type-specific baselines (fiber vs satellite vs 5g)
"""
import numpy as np
import pandas as pd
from pathlib import Path
import argparse


LINK_PROFILES = {
    "fiber-primary": {
        "base_latency": 8, "latency_noise": 1.5,
        "base_jitter": 0.5, "jitter_noise": 0.2,
        "base_loss": 0.01, "base_bw_util": 25,
        "brownout_prob": 0.001,
    },
    "broadband-secondary": {
        "base_latency": 20, "latency_noise": 4,
        "base_jitter": 2, "jitter_noise": 0.8,
        "base_loss": 0.05, "base_bw_util": 35,
        "brownout_prob": 0.003,
    },
    "satellite-backup": {
        "base_latency": 550, "latency_noise": 30,
        "base_jitter": 15, "jitter_noise": 5,
        "base_loss": 0.2, "base_bw_util": 20,
        "brownout_prob": 0.005,
    },
    "5g-mobile": {
        "base_latency": 12, "latency_noise": 6,
        "base_jitter": 3, "jitter_noise": 1.5,
        "base_loss": 0.08, "base_bw_util": 30,
        "brownout_prob": 0.004,
    },
}


def generate_link_telemetry(
    link_id: str,
    duration_hours: int = 24 * 30,
    interval_sec: int = 1,
    seed: int | None = None,
) -> pd.DataFrame:
    if seed is not None:
        np.random.seed(seed)

    profile = LINK_PROFILES.get(link_id, LINK_PROFILES["broadband-secondary"])
    n = (duration_hours * 3600) // interval_sec
    ts = pd.date_range(start="2026-01-01", periods=n, freq=f"{interval_sec}s")

    # Diurnal pattern
    hour = ts.hour + ts.minute / 60.0
    diurnal = 0.3 * np.sin(2 * np.pi * (hour - 6) / 24) + 0.7

    # Base metrics
    latency = profile["base_latency"] + 10 * diurnal + np.random.normal(0, profile["latency_noise"], n)
    jitter = profile["base_jitter"] + 3 * diurnal + np.random.normal(0, profile["jitter_noise"], n)
    loss = profile["base_loss"] + 0.05 * diurnal + np.random.normal(0, 0.01, n)
    bw = profile["base_bw_util"] + 40 * diurnal + np.random.normal(0, 5, n)
    rtt = latency * 2 + np.random.normal(0, 1, n)

    # Inject brownouts
    brownout_mask = np.random.random(n) < profile["brownout_prob"]
    for start in np.where(brownout_mask)[0]:
        dur = np.random.randint(30, 120)
        end = min(start + dur, n)
        ramp = np.linspace(0, 1, end - start)
        severity = np.random.uniform(2, 8)
        latency[start:end] += severity * 20 * ramp
        jitter[start:end] += severity * 5 * ramp
        loss[start:end] += severity * 2 * ramp

    # Congestion events (bandwidth > 85% → correlated packet loss spike)
    congestion = bw > 85
    loss[congestion] += np.random.uniform(1, 5, congestion.sum())

    return pd.DataFrame({
        "time": ts,
        "link_id": link_id,
        "latency_ms": np.clip(latency, 0, None),
        "jitter_ms": np.clip(jitter, 0, None),
        "packet_loss_pct": np.clip(loss, 0, 100),
        "bandwidth_util_pct": np.clip(bw, 0, 100),
        "rtt_ms": np.clip(rtt, 0, None),
    })


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic telemetry data")
    parser.add_argument("--hours", type=int, default=24*7, help="Duration in hours (default: 1 week)")
    parser.add_argument("--output", type=str, default="ml/data/synthetic", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for link_id in LINK_PROFILES:
        print(f"Generating {link_id} ({args.hours}h)...", end=" ", flush=True)
        df = generate_link_telemetry(link_id, args.hours, seed=args.seed)
        path = out_dir / f"{link_id}.parquet"
        df.to_parquet(path, index=False)
        print(f"{len(df):,} points → {path}")

    print("\\nDone. All synthetic data generated.")


if __name__ == "__main__":
    main()
'''


# ==============================================================================
# FILE 12: ml/scripts/train.py
# ==============================================================================

ML_TRAIN_SCRIPT = '''
"""
Model Training Entry Point
Agent: ML_ENGINEER

Usage:
    python ml/scripts/train.py --data ml/data/synthetic --output ml/checkpoints
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.prediction_engine.app.model.lstm_network import PathWiseLSTM
from services.prediction_engine.app.model.feature_engineering import FeatureEngineer
from services.prediction_engine.app.model.trainer import LSTMTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="ml/data/synthetic")
    parser.add_argument("--output", default="ml/checkpoints")
    parser.add_argument("--val-split", type=float, default=0.2)
    args = parser.parse_args()

    data_dir = Path(args.data)
    fe = FeatureEngineer()

    # Load and process all link data
    all_X, all_y = [], []
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        link_id = parquet_file.stem
        logger.info(f"Processing {link_id}...")

        df = pd.read_parquet(parquet_file)
        df = fe.compute_features(df)
        df = df.dropna()

        X, y = fe.create_sequences(df)
        X = fe.normalize(X, link_id, fit=True)

        logger.info(f"  → {X.shape[0]:,} sequences")
        all_X.append(X)
        all_y.append(y)

    X_all = np.concatenate(all_X, axis=0)
    y_all = np.concatenate(all_y, axis=0)

    logger.info(f"Total dataset: {X_all.shape[0]:,} sequences")
    logger.info(f"  X shape: {X_all.shape}")
    logger.info(f"  y shape: {y_all.shape}")

    # Split
    X_train, X_val, y_train, y_val = train_test_split(
        X_all, y_all, test_size=args.val_split, shuffle=True, random_state=42
    )
    logger.info(f"Train: {X_train.shape[0]:,} | Val: {X_val.shape[0]:,}")

    # Train
    model = PathWiseLSTM()
    trainer = LSTMTrainer(model, checkpoint_dir=args.output)
    history = trainer.train(X_train, y_train, X_val, y_val)

    logger.info(f"Training complete. Best val loss: {min(history['val_loss']):.6f}")
    logger.info(f"Checkpoint saved to: {args.output}/best_model.pt")


if __name__ == "__main__":
    main()
'''


# ==============================================================================
# FILE 13: services/prediction_engine/app/serve.py
# ==============================================================================

PREDICTION_SERVE = '''
"""
Real-Time Prediction Service
Agent: ML_ENGINEER + BACKEND_DEV

Background loop: reads telemetry from Redis, runs inference, publishes predictions.
"""
import asyncio
import json
import time
import logging
import numpy as np
import torch
import redis.asyncio as redis
import sys
sys.path.insert(0, "/app")

from shared.constants import LSTM_INPUT_WINDOW, WEBSOCKET_BROADCAST_INTERVAL_SEC
from shared.redis_keys import (
    ACTIVE_LINKS, TELEMETRY_RAW_STREAM,
    prediction_key, DEGRADATION_ALERTS_STREAM,
)
from app.model.lstm_network import PathWiseLSTM
from app.model.feature_engineering import FeatureEngineer
from app.model.health_score import compute_health_score, compute_trend

logger = logging.getLogger(__name__)


class PredictionService:
    """Continuous inference loop publishing predictions at 1Hz."""

    def __init__(self, model_path: str, redis_url: str, device: str = "cpu"):
        self.device = torch.device(device)
        self.model = PathWiseLSTM()
        self.fe = FeatureEngineer()
        self.redis_url = redis_url
        self.redis: redis.Redis | None = None

        # Load model
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        self.model.to(self.device)
        logger.info(f"Model loaded from {model_path} (val_loss={checkpoint.get('val_loss', 'N/A')})")

        # Score history for trend computation
        self._score_history: dict[str, list[float]] = {}

    async def start(self):
        """Main entry: connect Redis and start prediction loop."""
        self.redis = redis.from_url(self.redis_url)
        logger.info("Prediction service started")
        await self._prediction_loop()

    async def _prediction_loop(self):
        while True:
            loop_start = time.monotonic()
            try:
                link_ids = await self.redis.smembers(ACTIVE_LINKS)
                for link_bytes in link_ids:
                    link_id = link_bytes.decode()
                    await self._predict_for_link(link_id)
            except Exception as e:
                logger.error(f"Prediction loop error: {e}", exc_info=True)

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, WEBSOCKET_BROADCAST_INTERVAL_SEC - elapsed)
            await asyncio.sleep(sleep_time)

    async def _predict_for_link(self, link_id: str):
        # Fetch recent telemetry from Redis Stream
        entries = await self.redis.xrevrange(
            TELEMETRY_RAW_STREAM, count=LSTM_INPUT_WINDOW + 30
        )
        if len(entries) < LSTM_INPUT_WINDOW:
            return

        # Filter for this link and build window
        points = []
        for entry_id, fields in reversed(entries):
            if fields.get(b"link_id", b"").decode() == link_id:
                points.append({
                    "timestamp": float(fields[b"timestamp"]),
                    "latency_ms": float(fields[b"latency_ms"]),
                    "jitter_ms": float(fields[b"jitter_ms"]),
                    "packet_loss_pct": float(fields[b"packet_loss_pct"]),
                    "bandwidth_util_pct": float(fields[b"bandwidth_util_pct"]),
                    "rtt_ms": float(fields[b"rtt_ms"]),
                })

        window = self.fe.build_realtime_window(points)
        if window is None:
            return

        # Inference
        with torch.no_grad():
            x = torch.tensor(window, device=self.device).unsqueeze(0)
            preds, confidence = self.model(x)

        lat = preds["latency"][0].cpu().numpy()
        jit = preds["jitter"][0].cpu().numpy()
        pkt = preds["packet_loss"][0].cpu().numpy()
        conf = float(confidence[0].cpu())

        score = compute_health_score(lat, jit, pkt, conf)

        # Track history for trend
        if link_id not in self._score_history:
            self._score_history[link_id] = []
        self._score_history[link_id].append(score)
        if len(self._score_history[link_id]) > 60:
            self._score_history[link_id] = self._score_history[link_id][-60:]

        trend = compute_trend(score, self._score_history[link_id])

        # Publish to Redis
        await self.redis.hset(prediction_key(link_id), mapping={
            "health_score": str(score),
            "confidence": str(conf),
            "latency_forecast": json.dumps(lat.tolist()),
            "jitter_forecast": json.dumps(jit.tolist()),
            "packet_loss_forecast": json.dumps(pkt.tolist()),
            "trend": trend,
            "timestamp": str(time.time()),
        })

        # Alert if degradation predicted
        from shared.constants import STEERING_WARNING_THRESHOLD
        if score < STEERING_WARNING_THRESHOLD:
            await self.redis.xadd(DEGRADATION_ALERTS_STREAM, {
                "link_id": link_id,
                "health_score": str(score),
                "confidence": str(conf),
                "trend": trend,
            }, maxlen=1000)
'''


# ==============================================================================
# FILE 14: services/traffic_steering/app/steering_engine.py
# ==============================================================================

STEERING_ENGINE = '''
"""
Traffic Steering Decision Engine
Agent: BACKEND_DEV
"""
import asyncio
import time
import logging
import json
import redis.asyncio as redis
import sys
sys.path.insert(0, "/app")

from shared.schemas import SteeringDecision, SteeringAction, TrafficClass, SteeringAuditEntry
from shared.constants import (
    STEERING_CRITICAL_THRESHOLD, STEERING_WARNING_THRESHOLD,
    STEERING_CONFIDENCE_MIN, STEERING_REBALANCE_VARIANCE,
)
from shared.redis_keys import (
    ACTIVE_LINKS, prediction_key,
    DEGRADATION_ALERTS_STREAM, STEERING_EVENTS_STREAM,
    ALERTS_CONSUMER_GROUP,
)

logger = logging.getLogger(__name__)


class SteeringEngine:
    """
    Consumes degradation alerts and makes steering decisions.

    Decision matrix:
    ┌──────────────────────────────┬─────────────────────────────────┐
    │ Condition                    │ Action                          │
    ├──────────────────────────────┼─────────────────────────────────┤
    │ health < 30                  │ EMERGENCY_FAILOVER (immediate)  │
    │ health < 50, conf > 0.7     │ PREEMPTIVE_SHIFT (sandbox first)│
    │ score variance > 30         │ REBALANCE                       │
    │ else                         │ HOLD                            │
    └──────────────────────────────┴─────────────────────────────────┘
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: redis.Redis | None = None

    async def start(self):
        self.redis = redis.from_url(self.redis_url)

        # Create consumer group
        try:
            await self.redis.xgroup_create(
                DEGRADATION_ALERTS_STREAM, ALERTS_CONSUMER_GROUP, id="0", mkstream=True
            )
        except redis.ResponseError:
            pass  # Group already exists

        logger.info("Steering engine started")
        await self._decision_loop()

    async def _decision_loop(self):
        while True:
            try:
                # Read alerts
                messages = await self.redis.xreadgroup(
                    ALERTS_CONSUMER_GROUP, "steering-worker",
                    {DEGRADATION_ALERTS_STREAM: ">"},
                    count=10, block=1000,
                )

                if messages:
                    for stream, entries in messages:
                        for msg_id, fields in entries:
                            await self._handle_alert(fields)
                            await self.redis.xack(
                                DEGRADATION_ALERTS_STREAM, ALERTS_CONSUMER_GROUP, msg_id
                            )

                # Periodic full evaluation (every 5 seconds even without alerts)
                await self._full_evaluation()
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Decision loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _handle_alert(self, fields: dict):
        link_id = fields[b"link_id"].decode()
        score = float(fields[b"health_score"])
        conf = float(fields[b"confidence"])
        logger.warning(f"Alert: {link_id} health={score:.1f} conf={conf:.2f}")

    async def _full_evaluation(self) -> list[SteeringDecision]:
        link_ids = await self.redis.smembers(ACTIVE_LINKS)
        link_scores: dict[str, dict] = {}

        for lid_bytes in link_ids:
            lid = lid_bytes.decode()
            pred = await self.redis.hgetall(prediction_key(lid))
            if pred:
                link_scores[lid] = {
                    "health_score": float(pred[b"health_score"]),
                    "confidence": float(pred[b"confidence"]),
                }

        if not link_scores:
            return []

        # Find best link
        sorted_links = sorted(link_scores.items(), key=lambda x: x[1]["health_score"], reverse=True)
        best_link = sorted_links[0][0]

        decisions = []
        for link_id, scores in link_scores.items():
            if link_id == best_link:
                continue

            hs = scores["health_score"]
            conf = scores["confidence"]

            if hs < STEERING_CRITICAL_THRESHOLD:
                decisions.append(SteeringDecision(
                    action=SteeringAction.EMERGENCY_FAILOVER,
                    source_link=link_id,
                    target_link=best_link,
                    traffic_classes=[TrafficClass.VOIP, TrafficClass.VIDEO, TrafficClass.CRITICAL, TrafficClass.BULK],
                    confidence=conf,
                    reason=f"CRITICAL: {link_id} health={hs:.1f}",
                    requires_sandbox=False,
                ))

            elif hs < STEERING_WARNING_THRESHOLD and conf > STEERING_CONFIDENCE_MIN:
                decisions.append(SteeringDecision(
                    action=SteeringAction.PREEMPTIVE_SHIFT,
                    source_link=link_id,
                    target_link=best_link,
                    traffic_classes=[TrafficClass.VOIP, TrafficClass.VIDEO, TrafficClass.CRITICAL],
                    confidence=conf,
                    reason=f"Predicted degradation: {link_id} health={hs:.1f} conf={conf:.0%}",
                    requires_sandbox=True,
                ))

        # Publish decisions
        for decision in decisions:
            await self.redis.xadd(STEERING_EVENTS_STREAM, {
                "decision": decision.model_dump_json(),
            }, maxlen=500)
            logger.info(f"Decision: {decision.action.value} {decision.source_link} → {decision.target_link}")

        return decisions
'''


# ==============================================================================
# FILE 15: services/traffic_steering/app/sdn_clients/base.py
# ==============================================================================

SDN_CLIENT_BASE = '''
"""
Abstract SDN Controller Client
Agent: BACKEND_DEV
"""
from abc import ABC, abstractmethod
from typing import Optional


class SDNClient(ABC):
    """
    Interface for SDN controller integration.
    Implementations: OpenDaylight, ONOS.
    """

    @abstractmethod
    async def install_flow(
        self,
        switch_id: str,
        flow_id: str,
        priority: int,
        match: dict,
        output_port: int,
    ) -> bool:
        """Install a single flow rule on a switch."""
        ...

    @abstractmethod
    async def delete_flow(self, switch_id: str, flow_id: str) -> bool:
        """Delete a flow rule from a switch."""
        ...

    @abstractmethod
    async def get_flow_stats(self, switch_id: str, flow_id: str) -> Optional[dict]:
        """Get statistics for a specific flow (packet/byte counts)."""
        ...

    @abstractmethod
    async def get_topology(self) -> dict:
        """Get current network topology from the controller."""
        ...

    async def make_before_break_handoff(
        self,
        switch_id: str,
        old_flow_id: str,
        new_flow_id: str,
        new_priority: int,
        new_match: dict,
        new_output_port: int,
        verify_timeout: float = 2.0,
    ) -> bool:
        """
        Hitless handoff: install new path first, verify active, then remove old.
        """
        import asyncio

        # Step 1: Install new flow (higher priority)
        success = await self.install_flow(
            switch_id, new_flow_id, new_priority, new_match, new_output_port
        )
        if not success:
            return False

        # Step 2: Verify new flow is active (receiving packets)
        deadline = asyncio.get_event_loop().time() + verify_timeout
        while asyncio.get_event_loop().time() < deadline:
            stats = await self.get_flow_stats(switch_id, new_flow_id)
            if stats and stats.get("packet_count", 0) > 0:
                break
            await asyncio.sleep(0.1)

        # Step 3: Remove old flow
        await self.delete_flow(switch_id, old_flow_id)
        return True
'''


# ==============================================================================
# FILE 16: services/traffic_steering/app/sdn_clients/opendaylight.py
# ==============================================================================

ODL_CLIENT = '''
"""
OpenDaylight RESTCONF Client
Agent: BACKEND_DEV
"""
import httpx
import logging
from typing import Optional
import sys
sys.path.insert(0, "/app")
from app.sdn_clients.base import SDNClient

logger = logging.getLogger(__name__)

BASE_PATH = "/restconf/config/opendaylight-inventory:nodes/node"
OPS_PATH = "/restconf/operational/opendaylight-inventory:nodes/node"


class OpenDaylightClient(SDNClient):
    """Integration with OpenDaylight via RESTCONF API."""

    def __init__(self, base_url: str, username: str = "admin", password: str = "admin"):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}

    async def install_flow(
        self, switch_id: str, flow_id: str, priority: int,
        match: dict, output_port: int,
    ) -> bool:
        url = f"{self.base_url}{BASE_PATH}/{switch_id}/flow-node-inventory:table/0/flow/{flow_id}"
        payload = {
            "flow-node-inventory:flow": [{
                "id": flow_id,
                "table_id": 0,
                "priority": priority,
                "match": match,
                "instructions": {"instruction": [{
                    "order": 0,
                    "apply-actions": {"action": [{
                        "order": 0,
                        "output-action": {
                            "output-node-connector": str(output_port),
                            "max-length": 65535,
                        }
                    }]}
                }]}
            }]
        }
        async with httpx.AsyncClient(auth=self.auth, timeout=10) as client:
            resp = await client.put(url, json=payload, headers=self.headers)
            if resp.status_code in (200, 201):
                logger.info(f"Flow installed: {flow_id} on {switch_id}")
                return True
            logger.error(f"Flow install failed: {resp.status_code} {resp.text}")
            return False

    async def delete_flow(self, switch_id: str, flow_id: str) -> bool:
        url = f"{self.base_url}{BASE_PATH}/{switch_id}/flow-node-inventory:table/0/flow/{flow_id}"
        async with httpx.AsyncClient(auth=self.auth, timeout=10) as client:
            resp = await client.delete(url, headers=self.headers)
            return resp.status_code in (200, 204)

    async def get_flow_stats(self, switch_id: str, flow_id: str) -> Optional[dict]:
        url = f"{self.base_url}{OPS_PATH}/{switch_id}/flow-node-inventory:table/0/flow/{flow_id}"
        async with httpx.AsyncClient(auth=self.auth, timeout=10) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                flow = data.get("flow-node-inventory:flow", [{}])[0]
                stats = flow.get("opendaylight-flow-statistics:flow-statistics", {})
                return {
                    "packet_count": stats.get("packet-count", 0),
                    "byte_count": stats.get("byte-count", 0),
                }
            return None

    async def get_topology(self) -> dict:
        url = f"{self.base_url}/restconf/operational/network-topology:network-topology"
        async with httpx.AsyncClient(auth=self.auth, timeout=10) as client:
            resp = await client.get(url, headers=self.headers)
            return resp.json() if resp.status_code == 200 else {}
'''


# ==============================================================================
# FILE 17: services/api_gateway/app/main.py
# ==============================================================================

API_GATEWAY_MAIN = '''
"""
PathWise AI — API Gateway
Agent: BACKEND_DEV
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.insert(0, "/app")

from app.config import settings
from app.routers import telemetry, predictions, steering, sandbox, policies
from app.websocket.scoreboard import ScoreboardManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

scoreboard = ScoreboardManager(redis_url=settings.REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scoreboard.broadcast_loop())
    logger.info("PathWise API Gateway started")
    yield
    task.cancel()
    logger.info("PathWise API Gateway stopped")


app = FastAPI(
    title="PathWise AI API",
    version="1.0.0",
    description="AI-Powered SD-WAN Management Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REST Routes ──────────────────────────────────────────────────────────────
app.include_router(telemetry.router)
app.include_router(predictions.router)
app.include_router(steering.router)
app.include_router(sandbox.router)
app.include_router(policies.router)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}


# ─── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws/scoreboard")
async def scoreboard_ws(ws: WebSocket):
    await scoreboard.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await scoreboard.disconnect(ws)
'''


# ==============================================================================
# FILE 18: services/api_gateway/app/config.py
# ==============================================================================

API_CONFIG = '''
"""
API Gateway Configuration
Agent: BACKEND_DEV
"""
import os


class Settings:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://pathwise:pathwise_dev_2026@localhost:5432/pathwise")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    ODL_BASE_URL: str = os.getenv("ODL_BASE_URL", "http://localhost:8181")
    BATFISH_HOST: str = os.getenv("BATFISH_HOST", "localhost")


settings = Settings()
'''


# ==============================================================================
# FILE 19: services/api_gateway/app/routers/policies.py (IBN Intent Parser)
# ==============================================================================

IBN_ROUTER = '''
"""
Intent-Based Networking Router — Natural Language Policy Management
Agent: BACKEND_DEV
"""
import re
import logging
from fastapi import APIRouter, HTTPException
import sys
sys.path.insert(0, "/app")

from shared.schemas import IntentRequest, IntentResponse, PolicyRule, PolicyAction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/policies", tags=["IBN"])


# ─── Traffic Class Resolver ───────────────────────────────────────────────────

TRAFFIC_PATTERNS: list[tuple[str, str]] = [
    (r"voip|voice|sip|phone\\s*call", "voip"),
    (r"video|zoom|teams|conferencing|webex", "video"),
    (r"medical\\s*imaging|dicom|pacs|surgical", "medical_imaging"),
    (r"financial|trading|transaction", "financial"),
    (r"guest\\s*wi-?fi|guest\\s*network", "guest_wifi"),
    (r"backup|sync|replication", "backup"),
    (r"web|browsing|http", "web_browsing"),
    (r"streaming|netflix|youtube", "streaming"),
]

INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"prioritize\\s+(.+?)\\s+over\\s+(.+)", "prioritize"),
    (r"block\\s+(.+?)\\s+on\\s+(.+)", "block"),
    (r"guarantee\\s+(\\d+)\\s*(?:mbps|mb)\\s+(?:for|to)\\s+(.+)", "guarantee_bw"),
    (r"limit\\s+(.+?)\\s+to\\s+(\\d+)\\s*(?:mbps|mb)", "limit_bw"),
    (r"redirect\\s+(.+?)\\s+(?:to|through)\\s+(.+)", "redirect"),
    (r"(?:set|max)\\s+latency\\s+(?:for\\s+)?(.+?)\\s+(?:to\\s+)?(\\d+)\\s*ms", "max_latency"),
]


def resolve_traffic_class(text: str) -> str:
    text = text.strip().lower()
    for pattern, class_name in TRAFFIC_PATTERNS:
        if re.search(pattern, text):
            return class_name
    return "custom"


def parse_intent(intent_text: str) -> list[PolicyRule]:
    """Parse natural language intent into policy rules."""
    text = intent_text.lower().strip()
    rules: list[PolicyRule] = []

    for pattern, action_type in INTENT_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue

        if action_type == "prioritize":
            high = resolve_traffic_class(match.group(1))
            low = resolve_traffic_class(match.group(2))
            rules.append(PolicyRule(
                name=f"prioritize-{high}-over-{low}",
                traffic_class=high, priority=200,
                action=PolicyAction.PRIORITIZE, target_links=["all"],
            ))
            rules.append(PolicyRule(
                name=f"deprioritize-{low}",
                traffic_class=low, priority=50,
                action=PolicyAction.THROTTLE, target_links=["all"],
            ))

        elif action_type == "block":
            tc = resolve_traffic_class(match.group(1))
            link = match.group(2).strip()
            rules.append(PolicyRule(
                name=f"block-{tc}-on-{link}",
                traffic_class=tc, priority=300,
                action=PolicyAction.BLOCK, target_links=[link],
            ))

        elif action_type == "guarantee_bw":
            bw = float(match.group(1))
            tc = resolve_traffic_class(match.group(2))
            rules.append(PolicyRule(
                name=f"guarantee-bw-{tc}",
                traffic_class=tc, priority=150,
                bandwidth_guarantee_mbps=bw,
                action=PolicyAction.GUARANTEE_BW, target_links=["all"],
            ))

        elif action_type == "limit_bw":
            tc = resolve_traffic_class(match.group(1))
            bw = float(match.group(2))
            rules.append(PolicyRule(
                name=f"limit-bw-{tc}",
                traffic_class=tc, priority=100,
                bandwidth_guarantee_mbps=bw,
                action=PolicyAction.THROTTLE, target_links=["all"],
            ))

        elif action_type == "redirect":
            tc = resolve_traffic_class(match.group(1))
            link = match.group(2).strip()
            rules.append(PolicyRule(
                name=f"redirect-{tc}-to-{link}",
                traffic_class=tc, priority=180,
                action=PolicyAction.REDIRECT, target_links=[link],
            ))

        elif action_type == "max_latency":
            tc = resolve_traffic_class(match.group(1))
            lat = float(match.group(2))
            rules.append(PolicyRule(
                name=f"max-latency-{tc}",
                traffic_class=tc, priority=160,
                latency_max_ms=lat,
                action=PolicyAction.LIMIT_LATENCY, target_links=["all"],
            ))

        break  # Only match first pattern

    if not rules:
        raise ValueError(
            f"Could not parse intent: \\"{intent_text}\\". "
            "Supported formats: 'Prioritize VoIP over guest WiFi', "
            "'Block streaming on satellite-backup', "
            "'Guarantee 50 Mbps for video conferencing'"
        )

    return rules


# ─── API Endpoints ────────────────────────────────────────────────────────────

@router.post("/intent", response_model=IntentResponse)
async def apply_intent(request: IntentRequest):
    """Parse and apply a natural language network policy."""
    try:
        rules = parse_intent(request.intent)
        return IntentResponse(
            status="applied",
            intent=request.intent,
            rules=rules,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/active")
async def list_active_policies():
    """List all currently active network policies."""
    return {"policies": []}  # TODO: read from DB


@router.delete("/{policy_name}")
async def remove_policy(policy_name: str):
    """Remove a policy."""
    return {"status": "removed", "name": policy_name}
'''


# ==============================================================================
# FILE 20: services/api_gateway/app/websocket/scoreboard.py
# ==============================================================================

SCOREBOARD_WS = '''
"""
WebSocket Scoreboard Manager
Agent: BACKEND_DEV + FRONTEND_DEV

Pushes real-time health scores to dashboard at 1Hz.
"""
import asyncio
import json
import time
import logging
from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import sys
sys.path.insert(0, "/app")

from shared.redis_keys import ACTIVE_LINKS, prediction_key, TELEMETRY_RAW_STREAM
from shared.constants import WEBSOCKET_BROADCAST_INTERVAL_SEC

logger = logging.getLogger(__name__)


class ScoreboardManager:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: redis.Redis | None = None
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        logger.info(f"WebSocket connected ({len(self.connections)} total)")

    async def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        logger.info(f"WebSocket disconnected ({len(self.connections)} total)")

    async def broadcast_loop(self):
        self.redis = redis.from_url(self.redis_url)
        while True:
            try:
                if not self.connections:
                    await asyncio.sleep(WEBSOCKET_BROADCAST_INTERVAL_SEC)
                    continue

                data = await self._build_scoreboard()
                if data:
                    message = json.dumps({
                        "type": "scoreboard_update",
                        "links": data,
                        "timestamp": time.time(),
                    })

                    dead = []
                    for ws in self.connections:
                        try:
                            await ws.send_text(message)
                        except Exception:
                            dead.append(ws)
                    for ws in dead:
                        self.connections.remove(ws)

            except Exception as e:
                logger.error(f"Broadcast error: {e}")

            await asyncio.sleep(WEBSOCKET_BROADCAST_INTERVAL_SEC)

    async def _build_scoreboard(self) -> dict:
        links = await self.redis.smembers(ACTIVE_LINKS)
        result = {}
        for lid_bytes in links:
            lid = lid_bytes.decode()
            pred = await self.redis.hgetall(prediction_key(lid))
            if not pred:
                continue
            result[lid] = {
                "health_score": float(pred.get(b"health_score", 0)),
                "confidence": float(pred.get(b"confidence", 0)),
                "latency_forecast": json.loads(pred.get(b"latency_forecast", b"[]")),
                "jitter_forecast": json.loads(pred.get(b"jitter_forecast", b"[]")),
                "packet_loss_forecast": json.loads(pred.get(b"packet_loss_forecast", b"[]")),
                "trend": pred.get(b"trend", b"stable").decode(),
            }
        return result
'''


# ==============================================================================
# FILE 21: frontend/src/types/index.ts
# ==============================================================================

FRONTEND_TYPES = '''
// PathWise AI Frontend Types
// Agent: FRONTEND_DEV
// QA_AGENT: These MUST mirror shared/schemas.py exactly

export interface TelemetryPoint {
  timestamp: string;
  link_id: string;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  bandwidth_util_pct: number;
  rtt_ms: number;
}

export interface LinkHealthSnapshot {
  link_id: string;
  health_score: number;
  confidence: number;
  latency_current: number;
  jitter_current: number;
  packet_loss_current: number;
  bandwidth_util_current: number;
  latency_forecast: number[];
  jitter_forecast: number[];
  packet_loss_forecast: number[];
  trend: "improving" | "stable" | "degrading";
}

export interface ScoreboardUpdate {
  type: "scoreboard_update";
  links: Record<string, LinkHealthSnapshot>;
  timestamp: number;
}

export interface SteeringEvent {
  type: "steering_event";
  decision: SteeringDecision;
  sandbox_result?: string;
}

export interface SteeringDecision {
  id?: string;
  action: "hold" | "shift" | "failover" | "rebalance";
  source_link: string;
  target_link: string;
  traffic_classes: string[];
  confidence: number;
  reason: string;
  requires_sandbox: boolean;
  timestamp: string;
}

export interface PolicyRule {
  name: string;
  traffic_class: string;
  priority: number;
  bandwidth_guarantee_mbps?: number;
  latency_max_ms?: number;
  action: string;
  target_links: string[];
  active: boolean;
}

export interface IntentResponse {
  status: "applied" | "failed" | "pending_validation";
  intent: string;
  rules: PolicyRule[];
  validation_results: Record<string, unknown>[];
  error?: string;
}

export interface SandboxReport {
  id?: string;
  result: "pass" | "fail_loop" | "fail_policy" | "fail_unreachable" | "fail_timeout";
  details: string;
  loop_free: boolean;
  policy_compliant: boolean;
  reachability_verified: boolean;
  execution_time_ms: number;
}

export type WebSocketMessage = ScoreboardUpdate | SteeringEvent;
'''


# ==============================================================================
# FILE 22: frontend/package.json
# ==============================================================================

FRONTEND_PACKAGE_JSON = '''
{
  "name": "pathwise-ai-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.22.0",
    "zustand": "^4.5.0",
    "d3": "^7.9.0",
    "lucide-react": "^0.330.0",
    "clsx": "^2.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@types/d3": "^7.4.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.1.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.57.0"
  }
}
'''


# ==============================================================================
# FILE 23: Makefile
# ==============================================================================

MAKEFILE = '''
.PHONY: help setup data train up down logs test clean

help:  ## Show this help
\t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

setup:  ## Install dependencies and initialize project
\tcd frontend && npm install
\tpip install -r services/prediction_engine/requirements.txt
\tpip install -r services/api_gateway/requirements.txt

data:  ## Generate synthetic training data (1 week)
\tpython ml/scripts/generate_synthetic_data.py --hours 168 --output ml/data/synthetic

train:  ## Train the LSTM model
\tpython ml/scripts/train.py --data ml/data/synthetic --output ml/checkpoints

up:  ## Start all services with Docker Compose
\tdocker compose up -d --build

down:  ## Stop all services
\tdocker compose down

logs:  ## Tail all service logs
\tdocker compose logs -f

logs-api:  ## Tail API gateway logs
\tdocker compose logs -f api-gateway

logs-pred:  ## Tail prediction engine logs
\tdocker compose logs -f prediction-engine

test:  ## Run all tests
\tpytest tests/ -v --tb=short

test-unit:  ## Run unit tests only
\tpytest tests/unit/ -v

test-integration:  ## Run integration tests
\tpytest tests/integration/ -v

lint:  ## Lint Python and TypeScript
\truff check services/ shared/ ml/ tests/
\tcd frontend && npm run lint

clean:  ## Remove generated files and volumes
\tdocker compose down -v
\trm -rf ml/data/synthetic/*.parquet
\trm -rf ml/checkpoints/*.pt
\trm -rf frontend/node_modules
'''


# ==============================================================================
# FILE 24: build_orchestrator.py
# ==============================================================================

BUILD_ORCHESTRATOR = '''
#!/usr/bin/env python3
"""
PathWise AI — Build Verification Orchestrator

Run this after Cursor generates all files to verify project integrity.
Implements the QA_AGENT cross-validation checks.

Usage: python build_orchestrator.py
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

CORRECTIONS = []
ERRORS = 0


def log_correction(agent: str, file: str, issue: str, fix: str):
    global ERRORS
    ERRORS += 1
    CORRECTIONS.append({
        "agent": agent,
        "file": file,
        "issue": issue,
        "fix": fix,
        "timestamp": datetime.utcnow().isoformat(),
    })
    print(f"  ❌ [{agent}] {file}: {issue}")


def log_ok(check: str):
    print(f"  ✅ {check}")


def check_file_exists(path: str) -> bool:
    if not Path(path).exists():
        log_correction("QA_AGENT", path, f"File missing: {path}", "Generate this file")
        return False
    return True


def check_structure():
    """Verify all required files exist."""
    print("\\n🔍 Checking project structure...")
    required = [
        "docker-compose.yml", ".env", "Makefile",
        "shared/__init__.py", "shared/schemas.py", "shared/constants.py", "shared/redis_keys.py",
        "services/api_gateway/Dockerfile", "services/api_gateway/app/main.py",
        "services/api_gateway/app/config.py",
        "services/api_gateway/app/routers/policies.py",
        "services/api_gateway/app/websocket/scoreboard.py",
        "services/prediction_engine/Dockerfile",
        "services/prediction_engine/app/model/lstm_network.py",
        "services/prediction_engine/app/model/feature_engineering.py",
        "services/prediction_engine/app/model/health_score.py",
        "services/prediction_engine/app/model/trainer.py",
        "services/prediction_engine/app/serve.py",
        "services/traffic_steering/Dockerfile",
        "services/traffic_steering/app/steering_engine.py",
        "services/traffic_steering/app/sdn_clients/base.py",
        "services/traffic_steering/app/sdn_clients/opendaylight.py",
        "services/digital_twin/Dockerfile",
        "services/digital_twin/app/twin_manager.py",
        "ml/scripts/generate_synthetic_data.py",
        "ml/scripts/train.py",
        "frontend/package.json", "frontend/src/types/index.ts",
        "infra/db/init.sql",
        "tests/conftest.py",
    ]
    all_ok = True
    for f in required:
        if not check_file_exists(f):
            all_ok = False
    if all_ok:
        log_ok("All required files present")


def check_imports():
    """Verify shared module imports are consistent."""
    print("\\n🔍 Checking import consistency...")
    service_dirs = [
        "services/api_gateway/app",
        "services/prediction_engine/app",
        "services/traffic_steering/app",
        "services/digital_twin/app",
    ]
    for sdir in service_dirs:
        p = Path(sdir)
        if not p.exists():
            continue
        for py_file in p.rglob("*.py"):
            content = py_file.read_text()
            # Check no one redefines schemas locally
            if "class TelemetryPoint" in content and "shared" not in str(py_file):
                log_correction(
                    "QA_AGENT", str(py_file),
                    "Redefines TelemetryPoint locally instead of importing from shared.schemas",
                    "Replace with: from shared.schemas import TelemetryPoint",
                )
    log_ok("Import consistency check complete")


def check_redis_keys():
    """Verify all Redis key usage goes through shared/redis_keys.py."""
    print("\\n🔍 Checking Redis key consistency...")
    for py_file in Path("services").rglob("*.py"):
        content = py_file.read_text()
        if "redis_keys" in str(py_file):
            continue
        # Check for hardcoded Redis keys
        import re
        hardcoded = re.findall(r'["\\'](pathwise:[a-z:]+)["\\'']', content)
        for key in hardcoded:
            log_correction(
                "QA_AGENT", str(py_file),
                f"Hardcoded Redis key '{key}' — must use shared.redis_keys",
                f"Import from shared.redis_keys instead",
            )
    log_ok("Redis key consistency check complete")


def check_env_vars():
    """Verify .env has all required variables and services read from env."""
    print("\\n🔍 Checking environment variables...")
    env_path = Path(".env")
    if env_path.exists():
        env_content = env_path.read_text()
        required_vars = [
            "REDIS_URL", "DATABASE_URL", "ODL_BASE_URL",
            "BATFISH_HOST", "MODEL_PATH", "API_PORT",
        ]
        for var in required_vars:
            if var not in env_content:
                log_correction("QA_AGENT", ".env", f"Missing env var: {var}", f"Add {var} to .env")
    log_ok("Environment variable check complete")


def check_docker_compose():
    """Verify docker-compose service names match code references."""
    print("\\n🔍 Checking Docker Compose consistency...")
    dc_path = Path("docker-compose.yml")
    if dc_path.exists():
        content = dc_path.read_text()
        required_services = ["timescaledb", "redis", "api-gateway", "prediction-engine",
                             "traffic-steering", "digital-twin", "frontend"]
        for svc in required_services:
            if svc not in content:
                log_correction("QA_AGENT", "docker-compose.yml",
                               f"Missing service: {svc}", f"Add {svc} service definition")
    log_ok("Docker Compose check complete")


def write_corrections():
    """Write corrections log."""
    with open("CORRECTIONS.md", "w") as f:
        f.write("# PathWise AI — Multi-Agent Correction Log\\n\\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}\\n\\n")
        if not CORRECTIONS:
            f.write("✅ No corrections needed. All agents produced consistent output.\\n")
        else:
            f.write(f"⚠️ {len(CORRECTIONS)} corrections identified:\\n\\n")
            for i, c in enumerate(CORRECTIONS, 1):
                f.write(f"## Correction {i}\\n")
                f.write(f"- **Agent**: {c['agent']}\\n")
                f.write(f"- **File**: `{c['file']}`\\n")
                f.write(f"- **Issue**: {c['issue']}\\n")
                f.write(f"- **Fix**: {c['fix']}\\n\\n")


def main():
    print("=" * 60)
    print("  PathWise AI — Build Verification (QA Agent)")
    print("=" * 60)

    check_structure()
    check_imports()
    check_redis_keys()
    check_env_vars()
    check_docker_compose()
    write_corrections()

    print("\\n" + "=" * 60)
    if ERRORS == 0:
        print("  ✅ BUILD VERIFIED — All cross-agent checks passed")
    else:
        print(f"  ⚠️  {ERRORS} issues found — see CORRECTIONS.md")
    print("=" * 60)
    return 1 if ERRORS > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
'''


# ==============================================================================
# FILE 25: tests/conftest.py
# ==============================================================================

TEST_CONFTEST = '''
"""
Shared test fixtures
Agent: QA_AGENT
"""
import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def sample_telemetry_df():
    """Generate a small telemetry DataFrame for testing."""
    import pandas as pd
    n = 200
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="1s"),
        "link_id": "fiber-primary",
        "latency_ms": np.random.normal(15, 3, n).clip(0),
        "jitter_ms": np.random.normal(2, 0.5, n).clip(0),
        "packet_loss_pct": np.random.normal(0.05, 0.02, n).clip(0, 100),
        "bandwidth_util_pct": np.random.normal(40, 10, n).clip(0, 100),
        "rtt_ms": np.random.normal(30, 5, n).clip(0),
    })


@pytest.fixture
def sample_model():
    """Create an untrained PathWiseLSTM for structure tests."""
    from services.prediction_engine.app.model.lstm_network import PathWiseLSTM
    return PathWiseLSTM()


@pytest.fixture
def sample_input_tensor():
    """Random input tensor matching LSTM expected shape."""
    import torch
    from shared.constants import LSTM_INPUT_WINDOW, LSTM_NUM_FEATURES
    return torch.randn(4, LSTM_INPUT_WINDOW, LSTM_NUM_FEATURES)
'''


# ==============================================================================
# FILE 26: tests/unit/test_lstm_model.py
# ==============================================================================

TEST_LSTM = '''
"""
LSTM Model Unit Tests
Agent: QA_AGENT
"""
import torch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.constants import LSTM_HORIZON


def test_model_output_shapes(sample_model, sample_input_tensor):
    """Verify model outputs have correct shapes."""
    sample_model.eval()
    with torch.no_grad():
        preds, confidence = sample_model(sample_input_tensor)

    batch_size = sample_input_tensor.shape[0]
    assert preds["latency"].shape == (batch_size, LSTM_HORIZON)
    assert preds["jitter"].shape == (batch_size, LSTM_HORIZON)
    assert preds["packet_loss"].shape == (batch_size, LSTM_HORIZON)
    assert confidence.shape == (batch_size, 1)


def test_confidence_bounded(sample_model, sample_input_tensor):
    """Confidence must be in [0, 1] (sigmoid output)."""
    sample_model.eval()
    with torch.no_grad():
        _, confidence = sample_model(sample_input_tensor)
    assert (confidence >= 0).all()
    assert (confidence <= 1).all()


def test_loss_computation(sample_model, sample_input_tensor):
    """Loss should be a positive scalar."""
    from services.prediction_engine.app.model.lstm_network import PathWiseLoss
    criterion = PathWiseLoss()
    preds, _ = sample_model(sample_input_tensor)
    targets = torch.randn(sample_input_tensor.shape[0], LSTM_HORIZON, 3)
    loss = criterion(preds, targets)
    assert loss.dim() == 0  # scalar
    assert loss.item() > 0
'''


# ==============================================================================
# FILE 27: tests/unit/test_intent_parser.py
# ==============================================================================

TEST_IBN = '''
"""
IBN Intent Parser Unit Tests
Agent: QA_AGENT
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.api_gateway.app.routers.policies import parse_intent
from shared.schemas import PolicyAction


class TestIntentParser:
    def test_prioritize_voip_over_guest(self):
        rules = parse_intent("Prioritize VoIP over guest WiFi")
        assert len(rules) == 2
        assert rules[0].traffic_class == "voip"
        assert rules[0].action == PolicyAction.PRIORITIZE
        assert rules[1].traffic_class == "guest_wifi"
        assert rules[0].priority > rules[1].priority

    def test_guarantee_bandwidth(self):
        rules = parse_intent("Guarantee 50 Mbps for video conferencing")
        assert len(rules) == 1
        assert rules[0].bandwidth_guarantee_mbps == 50.0
        assert rules[0].traffic_class == "video"

    def test_block_traffic(self):
        rules = parse_intent("Block streaming on satellite-backup")
        assert len(rules) == 1
        assert rules[0].action == PolicyAction.BLOCK
        assert rules[0].traffic_class == "streaming"

    def test_case_insensitive(self):
        rules = parse_intent("PRIORITIZE MEDICAL IMAGING OVER GUEST WIFI")
        assert rules[0].traffic_class == "medical_imaging"

    def test_invalid_intent_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_intent("Make network go brrr")

    def test_max_latency(self):
        rules = parse_intent("Set max latency for VoIP to 30ms")
        assert rules[0].latency_max_ms == 30.0
        assert rules[0].traffic_class == "voip"
'''


# ==============================================================================
# FILE 28: tests/unit/test_health_score.py
# ==============================================================================

TEST_HEALTH = '''
"""
Health Score Unit Tests
Agent: QA_AGENT
"""
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.prediction_engine.app.model.health_score import compute_health_score, compute_trend


def test_perfect_health():
    """Low metrics → score near 100."""
    score = compute_health_score(
        np.full(30, 10.0),   # low latency
        np.full(30, 1.0),    # low jitter
        np.full(30, 0.01),   # low loss
        confidence=0.95,
    )
    assert score > 85


def test_degraded_health():
    """High metrics → score below 30."""
    score = compute_health_score(
        np.full(30, 180.0),
        np.full(30, 40.0),
        np.full(30, 4.0),
        confidence=0.9,
    )
    assert score < 30


def test_confidence_scaling():
    """Same metrics, lower confidence → lower score."""
    high_conf = compute_health_score(np.full(30, 50.0), np.full(30, 10.0), np.full(30, 0.5), 0.95)
    low_conf = compute_health_score(np.full(30, 50.0), np.full(30, 10.0), np.full(30, 0.5), 0.3)
    assert high_conf > low_conf


def test_trend_improving():
    assert compute_trend(80, [70, 71, 72, 73, 74, 75, 76, 77, 78, 79]) == "improving"


def test_trend_degrading():
    assert compute_trend(60, [75, 74, 73, 72, 71, 70, 69, 68, 67, 66]) == "degrading"


def test_trend_stable():
    assert compute_trend(50, [50, 50, 50, 50, 50, 50, 50, 50, 50, 50]) == "stable"
'''


# ==============================================================================
# FILE 29: Dockerfiles for each service
# ==============================================================================

DOCKERFILE_API = '''
FROM python:3.11-slim
WORKDIR /app
COPY services/api_gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY services/api_gateway/app/ /app/app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

DOCKERFILE_PREDICTION = '''
FROM python:3.11-slim
WORKDIR /app
COPY services/prediction_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY services/prediction_engine/app/ /app/app/
CMD ["python", "-m", "app.main"]
'''

DOCKERFILE_STEERING = '''
FROM python:3.11-slim
WORKDIR /app
COPY services/traffic_steering/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY services/traffic_steering/app/ /app/app/
CMD ["python", "-m", "app.main"]
'''

DOCKERFILE_TWIN = '''
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \\
    openvswitch-switch iproute2 net-tools iputils-ping \\
    && rm -rf /var/lib/apt/lists/*
COPY services/digital_twin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY services/digital_twin/app/ /app/app/
CMD ["python", "-m", "app.main"]
'''

DOCKERFILE_TELEMETRY = '''
FROM python:3.11-slim
WORKDIR /app
COPY services/telemetry_ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY services/telemetry_ingestion/app/ /app/app/
CMD ["python", "-m", "app.main"]
'''

DOCKERFILE_FRONTEND = '''
FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
'''


# ==============================================================================
# FILE 30: Requirements files
# ==============================================================================

REQUIREMENTS_API = '''
fastapi==0.109.2
uvicorn[standard]==0.27.1
redis[hiredis]==5.0.1
asyncpg==0.29.0
httpx==0.27.0
pydantic==2.6.1
'''

REQUIREMENTS_PREDICTION = '''
torch==2.2.0
numpy==1.26.4
pandas==2.2.0
redis[hiredis]==5.0.1
scikit-learn==1.4.0
pydantic==2.6.1
'''

REQUIREMENTS_STEERING = '''
redis[hiredis]==5.0.1
httpx==0.27.0
pydantic==2.6.1
'''

REQUIREMENTS_TWIN = '''
redis[hiredis]==5.0.1
httpx==0.27.0
pydantic==2.6.1
pybatfish==2024.1.12
'''

REQUIREMENTS_TELEMETRY = '''
redis[hiredis]==5.0.1
asyncpg==0.29.0
pysnmp==6.1.2
pydantic==2.6.1
'''


# ==============================================================================
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     CURSOR EXECUTION INSTRUCTIONS                       ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║                                                                        ║
# ║  1. CREATE all files listed in the directory tree (Phase 0)            ║
# ║  2. POPULATE each file using the code blocks above                     ║
# ║  3. For files not explicitly defined above (routers/telemetry.py,      ║
# ║     routers/predictions.py, etc.), generate them following the         ║
# ║     patterns established in the defined files and using the schemas    ║
# ║     from shared/schemas.py                                             ║
# ║  4. Generate the React frontend components following the types in      ║
# ║     frontend/src/types/index.ts                                        ║
# ║  5. Run build_orchestrator.py to verify                                ║
# ║  6. Fix any issues found by the QA agent                              ║
# ║  7. Run `make data` then `make train` then `make up`                  ║
# ║                                                                        ║
# ║  AGENT CORRECTION PROTOCOL:                                           ║
# ║  After generating each service, review ALL other services for:         ║
# ║  - Matching Pydantic model usage                                       ║
# ║  - Consistent Redis key references                                     ║
# ║  - Matching environment variable names                                 ║
# ║  - Compatible async/await patterns                                     ║
# ║  - Docker service name consistency                                     ║
# ║  If ANY inconsistency is found, fix it immediately.                    ║
# ║                                                                        ║
# ║  QUALITY TARGETS (from PVD):                                          ║
# ║  - Prediction accuracy: >= 90% (MSE)                                  ║
# ║  - System availability: >= 99.9%                                      ║
# ║  - Failover time: < 50ms                                              ║
# ║  - Sandbox validation: < 5 seconds                                    ║
# ║  - UI response: < 2 seconds                                           ║
# ║  - Scalability: >= 100 sites                                          ║
# ║                                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# ==============================================================================
