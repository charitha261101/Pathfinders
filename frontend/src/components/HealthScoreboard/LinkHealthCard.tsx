import React, { useState } from "react";

/**
 * LinkHealthCard — one card per WAN link showing the predictive 0-100
 * health score, color-coded per CLAUDE.md §11.3:
 *   green  ≥ 80  (healthy)
 *   yellow 50-79 (degrading)
 *   red    < 50  (critical)
 *
 * Satisfies Req-Func-Sw-13 (Fiber/Satellite/5G/Broadband) and
 * Req-Func-Sw-14 (LSTM confidence + reasoning tooltip on every
 * automated path switch).
 */

export interface LinkHealthData {
  link_id: string;
  health_score: number;
  confidence: number;
  reasoning?: string;
  latency_current?: number;
  jitter_current?: number;
  packet_loss_current?: number;
  bandwidth_util?: number;
  latency_forecast?: number[];
  trend?: "stable" | "degrading" | "improving";
  brownout_active?: boolean;
}

interface Props {
  data: LinkHealthData;
}

const LINK_LABELS: Record<string, string> = {
  "fiber-primary": "Fiber",
  "broadband-secondary": "Broadband",
  "satellite-backup": "Satellite",
  "5g-mobile": "5G Mobile",
  "wifi": "Wi-Fi",
};

function linkTypeLabel(link_id: string) {
  return LINK_LABELS[link_id] ?? link_id;
}

function scoreColor(score: number) {
  if (score >= 80) return { bg: "#0b3b1f", border: "#22c55e", fg: "#4ade80" };
  if (score >= 50) return { bg: "#3a2e0b", border: "#eab308", fg: "#facc15" };
  return { bg: "#3f1414", border: "#ef4444", fg: "#f87171" };
}

function trendIcon(trend?: string) {
  if (trend === "degrading") return "▼";
  if (trend === "improving") return "▲";
  return "→";
}

function Sparkline({ values }: { values: number[] }) {
  if (!values || values.length < 2) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = Math.max(max - min, 0.001);
  const w = 100;
  const h = 24;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const endRising = values[values.length - 1] > values[0];
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline
        points={points}
        fill="none"
        stroke={endRising ? "#f87171" : "#4ade80"}
        strokeWidth="1.5"
      />
    </svg>
  );
}

export default function LinkHealthCard({ data }: Props) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const colors = scoreColor(data.health_score);
  const label = linkTypeLabel(data.link_id);
  const confidencePct = Math.round((data.confidence ?? 0) * 100);

  return (
    <div
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        padding: 16,
        minWidth: 240,
        position: "relative",
        fontFamily: "Inter, system-ui, sans-serif",
        color: "#e5e7eb",
      }}
      aria-label={`Health card for ${label}`}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#cbd5e1" }}>{label}</div>
        <div
          style={{
            fontSize: 11, background: "#1f2937", padding: "2px 6px", borderRadius: 4,
            color: "#94a3b8",
          }}
        >
          {data.link_id}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", marginTop: 8, gap: 8 }}>
        <div style={{ fontSize: 42, fontWeight: 700, lineHeight: 1, color: colors.fg }}>
          {Math.round(data.health_score)}
        </div>
        <div style={{ fontSize: 14, color: "#94a3b8", paddingBottom: 6 }}>/100</div>
        <div style={{ marginLeft: "auto", fontSize: 16, color: colors.fg }}>
          {trendIcon(data.trend)}
        </div>
      </div>

      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 6 }}>
        LSTM confidence: <span style={{ color: "#e5e7eb" }}>{confidencePct}%</span>
        <button
          onClick={() => setTooltipOpen(!tooltipOpen)}
          style={{
            marginLeft: 8, background: "transparent", border: "1px solid #475569",
            color: "#94a3b8", borderRadius: 4, fontSize: 10, padding: "1px 5px",
            cursor: "pointer",
          }}
          aria-label="Why this score?"
        >
          Why?
        </button>
      </div>

      {tooltipOpen && (
        <div
          role="tooltip"
          style={{
            position: "absolute", top: "100%", left: 0, marginTop: 6, zIndex: 20,
            background: "#0f172a", border: "1px solid #334155", borderRadius: 8,
            padding: 10, fontSize: 12, color: "#e5e7eb", width: "100%",
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4, color: "#cbd5e1" }}>
            Reasoning
          </div>
          <div style={{ color: "#94a3b8", lineHeight: 1.4 }}>
            {data.reasoning || "LSTM has not produced a reasoning string for this link yet."}
          </div>
          {data.latency_forecast && data.latency_forecast.length > 1 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>
                Latency forecast (next {data.latency_forecast.length}s)
              </div>
              <Sparkline values={data.latency_forecast} />
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 12, fontSize: 11, color: "#94a3b8" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
          <span>Latency</span>
          <span style={{ color: "#e5e7eb" }}>
            {data.latency_current?.toFixed(1) ?? "–"} ms
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
          <span>Jitter</span>
          <span style={{ color: "#e5e7eb" }}>
            {data.jitter_current?.toFixed(1) ?? "–"} ms
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
          <span>Packet loss</span>
          <span style={{ color: "#e5e7eb" }}>
            {data.packet_loss_current?.toFixed(2) ?? "–"}%
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Bandwidth util</span>
          <span style={{ color: "#e5e7eb" }}>
            {data.bandwidth_util?.toFixed(0) ?? "–"}%
          </span>
        </div>
      </div>

      {data.brownout_active && (
        <div
          style={{
            marginTop: 10, padding: "4px 8px", fontSize: 11, fontWeight: 600,
            background: "#7f1d1d", color: "#fecaca", borderRadius: 4,
            textAlign: "center",
          }}
        >
          BROWNOUT IN PROGRESS
        </div>
      )}
    </div>
  );
}
