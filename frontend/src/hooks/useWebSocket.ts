import { useEffect, useRef, useCallback } from 'react';
import { useNetworkStore } from '../store/networkStore';
import { createWebSocket } from '../services/api';

/**
 * Custom hook for managing the WebSocket connection to the
 * PathWise scoreboard real-time feed.
 *
 * Handles:
 * - Automatic connection on mount
 * - Reconnection with exponential backoff
 * - Parsing scoreboard updates and pushing to Zustand store
 * - Cleanup on unmount
 */
export function useScoreboardWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelay = useRef(1000);
  const updateScoreboard = useNetworkStore((s) => s.updateScoreboard);
  const setWsConnected = useNetworkStore((s) => s.setWsConnected);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = createWebSocket('/ws/scoreboard');
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      reconnectDelay.current = 1000;
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'scoreboard_update' && msg.data) {
          updateScoreboard(msg.data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      // Exponential backoff reconnection
      reconnectTimeout.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
        connect();
      }, reconnectDelay.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [updateScoreboard, setWsConnected]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
