// frontend/src/services/websocket.ts

import { useNetworkStore } from '../store/networkStore';
import type { LinkHealth } from '../types';

/**
 * WebSocket service for real-time scoreboard updates.
 *
 * Manages connection lifecycle, reconnection, and data dispatching
 * to the Zustand store.
 */
class ScoreboardWebSocket {
  private ws: WebSocket | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.intentionalClose = false;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_API_URL
      ? new URL(process.env.REACT_APP_API_URL).host
      : window.location.host;

    this.ws = new WebSocket(`${wsProtocol}//${host}/ws/scoreboard`);

    this.ws.onopen = () => {
      useNetworkStore.getState().setWsConnected(true);
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'scoreboard_update' && msg.data) {
          const scoreboard: Record<string, LinkHealth> = msg.data;
          useNetworkStore.getState().updateScoreboard(scoreboard);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.ws.onclose = () => {
      useNetworkStore.getState().setWsConnected(false);
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    useNetworkStore.getState().setWsConnected(false);
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
      this.connect();
    }, this.reconnectDelay);
  }
}

export const scoreboardWs = new ScoreboardWebSocket();
