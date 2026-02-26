export interface TelemetryPoint {
  timestamp: number;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  bandwidth_util_pct: number;
  rtt_ms: number;
}

export interface LinkHealth {
  health_score: number;
  confidence: number;
  latency_current: number;
  jitter_current: number;
  packet_loss_current: number;
  bandwidth_util: number;
  latency_forecast: number[];
  trend: TrendDirection;
  brownout_active: boolean;
  raw_latency?: number;
  raw_jitter?: number;
  raw_packet_loss?: number;
}

export type TrendDirection = "improving" | "stable" | "degrading";

export interface PredictionResponse {
  link_id: string;
  health_score: number;
  confidence: number;
  latency_forecast: number[];
  jitter_forecast: number[];
  packet_loss_forecast: number[];
  timestamp: number;
}

export interface SteeringEvent {
  id: string;
  timestamp: number;
  action: string;
  source_link: string;
  target_link: string;
  reason: string;
  confidence: number;
  status: string;
  lstm_enabled: boolean;
}

export interface ComparisonMetrics {
  avg_latency: number;
  avg_jitter: number;
  avg_packet_loss: number;
  proactive_steerings?: number;
  reactive_steerings?: number;
  brownouts_avoided?: number;
  brownouts_hit?: number;
}

export interface SandboxCheck {
  name: string;
  status: "pass" | "fail" | "warn";
  detail: string;
  duration_ms: number;
}

export interface SandboxReport {
  id: string;
  result: string;
  source_link: string;
  target_link: string;
  traffic_classes: string[];
  loop_free: boolean;
  policy_compliant: boolean;
  reachability_verified: boolean;
  performance_acceptable: boolean;
  checks: SandboxCheck[];
  execution_time_ms: number;
  timestamp: number;
}

export interface ActiveRoutingRule {
  id: string;
  source_link: string;
  target_link: string;
  traffic_classes: string[];
  applied_at?: number;
  sandbox_report_id?: string;
  status?: string;
  age_seconds?: number;
}

export interface ScoreboardUpdate {
  type: string;
  timestamp: number;
  lstm_enabled: boolean;
  links: Record<string, LinkHealth>;
  active_routing_rules: ActiveRoutingRule[];
  steering_events: SteeringEvent[];
  comparison: {
    lstm_on: ComparisonMetrics;
    lstm_off: ComparisonMetrics;
  };
}
