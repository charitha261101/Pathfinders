import React, { useEffect, useRef, useState } from "react";
import LinkHealthCard, { LinkHealthData } from "./LinkHealthCard";

/**
 * HealthScoreboard — Multi-Link real-time scoreboard.
 *
 * Connects to the /ws/scoreboard WebSocket. On each tick it receives a
 * scoreboard_update payload and renders one LinkHealthCard per active link.
 *
 * Satisfies:
 *   Req-Func-Sw-13 — Multi-Link Health Scoreboard with Fiber/Satellite/5G/Broadband
 *   Req-Func-Sw-14 — LSTM confidence + reasoning display on every automated switch
 *   Req-Qual-Perf-4 — UI response < 2s under normal load (WebSocket, no polling)
 */

interface SteeringEvent {
  id: string;
  action: string;
  source_link: string;
  target_link: string;
  reason: string;
  confidence: number;
  timestamp: number;
  lstm_enabled: boolean;
  status: string;
}

interface ScoreboardPayload {
  type: "scoreboard_update";
  timestamp: number;
  lstm_enabled: boolean;
  links: Record<string, LinkHealthData>;
  steering_events: SteeringEvent[];
}

function apiBase() {
  return (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
}

function wsUrl() {
  const base = apiBase();
  if (base.startsWith("https://")) {
    return base.replace("https://", "wss://") + "/ws/scoreboard";
  }
  return base.replace("http://", "ws://") + "/ws/scoreboard";
}

export default function HealthScoreboard() {
  const [payload, setPayload] = useState<ScoreboardPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: any = null;

    function connect() {
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        reconnectTimer = setTimeout(connect, 2000);
      };
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "scoreboard_update") setPayload(msg);
        } catch {
          // ignore malformed
        }
      };
    }

    connect();
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  const links = payload?.links ?? {};
  const linkIds = Object.keys(links);

  // Derive overall fleet health as the lowest link score (the operator's
  // eyes should snap to the worst link first).
  const overall = linkIds.length
    ? Math.min(...linkIds.map((id) => links[id].health_score ?? 100))
    : 0;

  return (
    <div style={{
      padding: 24, background: "#0f172a", minHeight: "100vh",
      fontFamily: "Inter, system-ui, sans-serif", color: "#e5e7eb",
    }}>
      <header style={{ display: "flex", justifyContent: "space-between",
                       alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>
            Multi-Link Health Scoreboard
          </h1>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            Real-time LSTM-driven health predictions • Req-Func-Sw-13, Sw-14
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>
            LSTM: <span style={{ color: payload?.lstm_enabled ? "#4ade80" : "#f87171" }}>
              {payload?.lstm_enabled ? "ON" : "OFF"}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>
            WS: <span style={{ color: connected ? "#4ade80" : "#f87171" }}>
              {connected ? "connected" : "connecting..."}
            </span>
          </div>
          <div style={{
            fontSize: 12, background: "#1e293b", color: "#e5e7eb",
            padding: "4px 10px", borderRadius: 6,
          }}>
            Fleet min: <strong>{Math.round(overall)}</strong>/100
          </div>
        </div>
      </header>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: 16,
        marginBottom: 24,
      }}>
        {linkIds.length === 0 && (
          <div style={{ color: "#64748b", padding: 40, textAlign: "center",
                        background: "#1e293b", borderRadius: 12 }}>
            Waiting for telemetry…
          </div>
        )}
        {linkIds.map((id) => (
          <LinkHealthCard key={id} data={{ ...links[id], link_id: id }} />
        ))}
      </div>

      {/* Automated path switches — Req-Func-Sw-14 requires reasoning + confidence */}
      <section>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: "#cbd5e1", margin: "0 0 10px" }}>
          Recent automated path switches
        </h2>
        <div style={{ background: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
          {(payload?.steering_events ?? []).length === 0 ? (
            <div style={{ padding: 16, color: "#64748b", fontSize: 13 }}>
              No automated switches recorded yet.
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#0f172a", color: "#94a3b8" }}>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>Time</th>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>Action</th>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>From → To</th>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>Confidence</th>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {(payload?.steering_events ?? []).map((evt) => (
                  <tr key={evt.id} style={{ borderTop: "1px solid #334155" }}>
                    <td style={{ padding: "8px 10px", color: "#cbd5e1" }}>
                      {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: "8px 10px", color: "#cbd5e1" }}>
                      {evt.action}
                    </td>
                    <td style={{ padding: "8px 10px", color: "#cbd5e1" }}>
                      {evt.source_link} → {evt.target_link}
                    </td>
                    <td style={{ padding: "8px 10px", color: "#4ade80" }}>
                      {Math.round(evt.confidence * 100)}%
                    </td>
                    <td style={{ padding: "8px 10px", color: "#94a3b8" }}>
                      {evt.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
