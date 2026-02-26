import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10_000,
});

export const api = {
  getStatus: () => client.get("/api/v1/status").then((r) => r.data),

  toggleLSTM: (enabled: boolean) =>
    client
      .post("/api/v1/admin/lstm-toggle", { enabled })
      .then((r) => r.data),

  getLSTMStatus: () =>
    client.get("/api/v1/admin/lstm-status").then((r) => r.data),

  getLinks: () =>
    client.get("/api/v1/telemetry/links").then((r) => r.data),

  getTelemetry: (linkId: string, window = 60) =>
    client
      .get(`/api/v1/telemetry/${linkId}`, { params: { window } })
      .then((r) => r.data),

  getRawTelemetry: (linkId: string, window = 60) =>
    client
      .get(`/api/v1/telemetry/${linkId}/raw`, { params: { window } })
      .then((r) => r.data),

  getAllPredictions: () =>
    client.get("/api/v1/predictions/all").then((r) => r.data),

  getSteeringHistory: (limit = 50) =>
    client
      .get("/api/v1/steering/history", { params: { limit } })
      .then((r) => r.data),

  getComparisonMetrics: () =>
    client.get("/api/v1/metrics/comparison").then((r) => r.data),

  sandboxValidate: (source_link: string, target_link: string, traffic_classes: string[]) =>
    client
      .post("/api/v1/sandbox/validate", { source_link, target_link, traffic_classes })
      .then((r) => r.data),

  sandboxHistory: (limit = 20) =>
    client.get("/api/v1/sandbox/history", { params: { limit } }).then((r) => r.data),

  sandboxTopology: () =>
    client.get("/api/v1/sandbox/topology").then((r) => r.data),

  applyRoutingRule: (sandbox_report_id: string, source_link: string, target_link: string, traffic_classes: string[]) =>
    client
      .post("/api/v1/routing/apply", { sandbox_report_id, source_link, target_link, traffic_classes })
      .then((r) => r.data),

  getActiveRules: () =>
    client.get("/api/v1/routing/active").then((r) => r.data),

  getAllRules: () =>
    client.get("/api/v1/routing/all").then((r) => r.data),

  rollbackRule: (ruleId: string) =>
    client.delete(`/api/v1/routing/${ruleId}`).then((r) => r.data),
};

export function createWebSocket(): WebSocket {
  const wsUrl = API_BASE.replace(/^http/, "ws") + "/ws/scoreboard";
  return new WebSocket(wsUrl);
}
