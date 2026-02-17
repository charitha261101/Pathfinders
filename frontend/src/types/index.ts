// frontend/src/types/index.ts
// Shared TypeScript type definitions for the PathWise dashboard

export interface TelemetryPoint {
  timestamp: number;
  link_id: string;
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
  latency_forecast: number[];
  trend: TrendDirection;
}

export type TrendDirection = 'improving' | 'stable' | 'degrading';

export interface ScoreboardData {
  [linkId: string]: LinkHealth;
}

export interface PredictionResponse {
  link_id: string;
  health_score: number;
  confidence: number;
  latency_forecast: number[];
  jitter_forecast: number[];
  packet_loss_forecast: number[];
  timestamp: string;
}

export interface SteeringDecision {
  action: SteeringAction;
  source_link: string;
  target_link: string;
  traffic_classes: string[];
  confidence: number;
  reason: string;
  requires_sandbox_validation: boolean;
}

export type SteeringAction = 'hold' | 'shift' | 'failover' | 'rebalance';

export interface SteeringEvent {
  id: string;
  action: string;
  source_link: string;
  target_link: string;
  traffic_classes: string;
  confidence: number;
  reason: string;
  status: string;
  sandbox_validated: string;
}

export interface SandboxReport {
  id: string;
  result: string;
  details: string;
  loop_free: boolean;
  policy_compliant: boolean;
  reachability_verified: boolean;
  execution_time_ms: number;
}

export interface PolicyRule {
  name: string;
  traffic_class: string;
  priority: number;
  bandwidth_guarantee_mbps: number | null;
  latency_max_ms: number | null;
  action: string;
  target_links: string[];
}

export interface IntentResponse {
  status: string;
  intent: string;
  rules_generated: PolicyRule[];
  validation: Array<{ rule: string; validated: boolean }>;
}

export interface WebSocketMessage {
  type: string;
  data: Record<string, unknown>;
  timestamp: number;
}
