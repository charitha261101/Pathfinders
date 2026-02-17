-- Hypertable for high-frequency telemetry storage
CREATE TABLE telemetry (
    time        TIMESTAMPTZ NOT NULL,
    link_id     TEXT NOT NULL,
    latency_ms  DOUBLE PRECISION,
    jitter_ms   DOUBLE PRECISION,
    packet_loss_pct DOUBLE PRECISION,
    bandwidth_util_pct DOUBLE PRECISION,
    rtt_ms      DOUBLE PRECISION
);

SELECT create_hypertable('telemetry', 'time');

-- Continuous aggregate for 10-second rollups (model training)
CREATE MATERIALIZED VIEW telemetry_10s
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('10 seconds', time) AS bucket,
    link_id,
    AVG(latency_ms) AS avg_latency,
    STDDEV(latency_ms) AS std_latency,
    AVG(jitter_ms) AS avg_jitter,
    MAX(jitter_ms) AS max_jitter,
    AVG(packet_loss_pct) AS avg_packet_loss,
    MAX(packet_loss_pct) AS max_packet_loss,
    AVG(bandwidth_util_pct) AS avg_bw_util,
    AVG(rtt_ms) AS avg_rtt
FROM telemetry
GROUP BY bucket, link_id;

-- Retention policy: raw data 7 days, aggregates 90 days
SELECT add_retention_policy('telemetry', INTERVAL '7 days');
SELECT add_retention_policy('telemetry_10s', INTERVAL '90 days');

-- Index for fast range queries per link
CREATE INDEX idx_telemetry_link_time ON telemetry (link_id, time DESC);

-- Steering audit log
CREATE TABLE steering_audit (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action      TEXT NOT NULL,
    source_link TEXT NOT NULL,
    target_link TEXT NOT NULL,
    traffic_classes TEXT[],
    confidence  DOUBLE PRECISION,
    reason      TEXT,
    sandbox_validated BOOLEAN,
    status      TEXT NOT NULL
);

-- Active policies table
CREATE TABLE active_policies (
    name            TEXT PRIMARY KEY,
    traffic_class   TEXT NOT NULL,
    priority        INTEGER NOT NULL,
    bandwidth_guarantee_mbps DOUBLE PRECISION,
    latency_max_ms  DOUBLE PRECISION,
    action          TEXT NOT NULL,
    target_links    TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sandbox validation reports
CREATE TABLE sandbox_reports (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result          TEXT NOT NULL,
    details         TEXT,
    loop_free       BOOLEAN NOT NULL,
    policy_compliant BOOLEAN NOT NULL,
    reachability_verified BOOLEAN NOT NULL,
    execution_time_ms DOUBLE PRECISION,
    topology_snapshot JSONB
);
