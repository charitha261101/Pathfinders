import { create } from 'zustand';

interface LinkPrediction {
  health_score: number;
  confidence: number;
  latency_forecast: number[];
  jitter_forecast: number[];
  packet_loss_forecast: number[];
  timestamp: string;
}

interface LinkHealth {
  health_score: number;
  confidence: number;
  latency_current: number;
  jitter_current: number;
  packet_loss_current: number;
  latency_forecast: number[];
  trend: 'improving' | 'stable' | 'degrading';
}

interface SteeringEvent {
  action: string;
  source: string;
  target: string;
  reason: string;
  timestamp: string;
}

interface NetworkState {
  // Active links
  activeLinks: string[];
  setActiveLinks: (links: string[]) => void;

  // Predictions per link
  predictions: Record<string, LinkPrediction>;
  updatePredictions: (preds: Record<string, LinkPrediction>) => void;

  // Real-time health data (from WebSocket)
  scoreboard: Record<string, LinkHealth>;
  updateScoreboard: (data: Record<string, LinkHealth>) => void;

  // Steering events
  steeringHistory: SteeringEvent[];
  addSteeringEvent: (event: SteeringEvent) => void;

  // Connection state
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
}

export const useNetworkStore = create<NetworkState>((set) => ({
  activeLinks: [],
  setActiveLinks: (links) => set({ activeLinks: links }),

  predictions: {},
  updatePredictions: (preds) =>
    set((state) => ({
      predictions: { ...state.predictions, ...preds },
    })),

  scoreboard: {},
  updateScoreboard: (data) => set({ scoreboard: data }),

  steeringHistory: [],
  addSteeringEvent: (event) =>
    set((state) => ({
      steeringHistory: [event, ...state.steeringHistory].slice(0, 100),
    })),

  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
