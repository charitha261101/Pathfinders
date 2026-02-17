import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service functions

export const telemetryApi = {
  getLinks: () => apiClient.get('/api/v1/telemetry/links'),
  getTelemetry: (linkId: string, window: string = '60s') =>
    apiClient.get(`/api/v1/telemetry/${linkId}`, { params: { window } }),
};

export const predictionApi = {
  getAll: () => apiClient.get('/api/v1/predictions/all'),
  getByLink: (linkId: string) => apiClient.get(`/api/v1/predictions/${linkId}`),
};

export const steeringApi = {
  execute: (data: {
    source_link: string;
    target_link: string;
    traffic_classes: string[];
    reason?: string;
  }) => apiClient.post('/api/v1/steering/execute', data),
  getHistory: (limit: number = 50) =>
    apiClient.get('/api/v1/steering/history', { params: { limit } }),
};

export const sandboxApi = {
  validate: (data: {
    source_link: string;
    target_link: string;
    traffic_classes: string[];
  }) => apiClient.post('/api/v1/sandbox/validate', data),
  getReport: (reportId: string) =>
    apiClient.get(`/api/v1/sandbox/reports/${reportId}`),
};

export const policyApi = {
  submitIntent: (intent: string) =>
    apiClient.post('/api/v1/policies/intent', { intent }),
  getActive: () => apiClient.get('/api/v1/policies/active'),
  remove: (policyName: string) =>
    apiClient.delete(`/api/v1/policies/${policyName}`),
};

// WebSocket connection factory
export const createWebSocket = (path: string): WebSocket => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = process.env.REACT_APP_API_URL
    ? new URL(process.env.REACT_APP_API_URL).host
    : window.location.host;
  return new WebSocket(`${wsProtocol}//${wsHost}${path}`);
};
