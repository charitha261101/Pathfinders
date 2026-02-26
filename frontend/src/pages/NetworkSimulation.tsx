import React, { useMemo, useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  ArrowRightLeft,
  Radio,
  Satellite,
  Wifi,
  Cable,
  BrainCircuit,
  TrendingDown,
  TrendingUp,
  Activity,
  Rocket,
  Undo2,
  ChevronRight,
  Clock,
} from "lucide-react";
import { api } from "../services/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Area,
  AreaChart,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { useNetworkStore } from "../store/networkStore";
import type { LinkHealth } from "../types";

const LINK_META: Record<
  string,
  { label: string; icon: React.ElementType; color: string; gradient: string }
> = {
  "fiber-primary": {
    label: "Fiber Primary",
    icon: Cable,
    color: "#6366f1",
    gradient: "from-indigo-500 to-indigo-600",
  },
  "broadband-secondary": {
    label: "Broadband",
    icon: Wifi,
    color: "#22d3ee",
    gradient: "from-cyan-500 to-cyan-600",
  },
  "satellite-backup": {
    label: "Satellite",
    icon: Satellite,
    color: "#fbbf24",
    gradient: "from-amber-500 to-amber-600",
  },
  "5g-mobile": {
    label: "5G Mobile",
    icon: Radio,
    color: "#34d399",
    gradient: "from-emerald-500 to-emerald-600",
  },
};

const NetworkSimulation: React.FC = () => {
  const scoreboard = useNetworkStore((s) => s.scoreboard);
  const lstmEnabled = useNetworkStore((s) => s.lstmEnabled);
  const comparison = useNetworkStore((s) => s.comparison);
  const steeringEvents = useNetworkStore((s) => s.steeringEvents);
  const activeRoutingRules = useNetworkStore((s) => s.activeRoutingRules);
  const [rollingBack, setRollingBack] = useState<string | null>(null);

  const handleRollback = useCallback(async (ruleId: string) => {
    setRollingBack(ruleId);
    try {
      await api.rollbackRule(ruleId);
    } catch (err) {
      console.error("Rollback failed", err);
    } finally {
      setRollingBack(null);
    }
  }, []);

  const links = Object.entries(scoreboard);

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Live Network Simulation
          </h1>
          <p className="text-pw-muted text-sm mt-1">
            Real-time view of SD-WAN link performance as experienced by users
          </p>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={lstmEnabled ? "on" : "off"}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className={`flex items-center gap-3 px-5 py-2.5 rounded-2xl border ${
              lstmEnabled
                ? "bg-pw-emerald/10 border-pw-emerald/30 text-pw-emerald"
                : "bg-pw-rose/10 border-pw-rose/30 text-pw-rose"
            }`}
          >
            <BrainCircuit className="w-5 h-5" />
            <span className="text-sm font-semibold">
              {lstmEnabled ? "LSTM AI Active" : "LSTM AI Disabled"}
            </span>
            <div
              className={`w-2 h-2 rounded-full ${
                lstmEnabled ? "bg-pw-emerald animate-pulse" : "bg-pw-rose"
              }`}
            />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Active Routing Rules (from Sandbox Deployments) */}
      <AnimatePresence>
        {activeRoutingRules.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-card p-5 border-l-4 border-pw-emerald"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-pw-emerald/20 flex items-center justify-center">
                <Rocket className="w-4 h-4 text-pw-emerald" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Active Routing Rules
                </h3>
                <p className="text-xs text-pw-muted">
                  Sandbox-validated changes applied to live simulation
                </p>
              </div>
              <span className="ml-auto px-2.5 py-0.5 bg-pw-emerald/15 border border-pw-emerald/30 rounded-full text-xs font-bold text-pw-emerald">
                {activeRoutingRules.length} LIVE
              </span>
            </div>
            <div className="space-y-2">
              {activeRoutingRules.map((rule) => (
                <motion.div
                  key={rule.id}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center justify-between bg-pw-surface/80 rounded-xl px-4 py-3 border border-pw-border"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-sm">
                      <span className="font-mono font-semibold text-red-400">
                        {rule.source_link}
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 text-pw-emerald" />
                      <span className="font-mono font-semibold text-emerald-400">
                        {rule.target_link}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      {rule.traffic_classes.map((tc) => (
                        <span
                          key={tc}
                          className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-pw-accent/10 text-pw-accent-light border border-pw-accent/20"
                        >
                          {tc}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-xs text-pw-muted">
                      <Clock className="w-3 h-3" />
                      {rule.age_seconds != null
                        ? rule.age_seconds < 60
                          ? `${Math.round(rule.age_seconds)}s ago`
                          : `${Math.round(rule.age_seconds / 60)}m ago`
                        : "just now"}
                    </div>
                    <button
                      onClick={() => handleRollback(rule.id)}
                      disabled={rollingBack === rule.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                    >
                      <Undo2 className="w-3 h-3" />
                      {rollingBack === rule.id ? "Rolling back…" : "Rollback"}
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Network Topology Visualization */}
      <div className="glass-card p-6">
        <TopologyView scoreboard={scoreboard} lstmEnabled={lstmEnabled} activeRules={activeRoutingRules} />
      </div>

      {/* Link Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {links.map(([linkId, health]) => (
          <LinkCard
            key={linkId}
            linkId={linkId}
            health={health}
            lstmEnabled={lstmEnabled}
            rerouteStatus={
              activeRoutingRules.find((r) => r.source_link === linkId)
                ? "diverted_from"
                : activeRoutingRules.find((r) => r.target_link === linkId)
                ? "diverted_to"
                : undefined
            }
          />
        ))}
      </div>

      {/* Comparison Bar */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <ArrowRightLeft className="w-4 h-4 text-pw-accent-light" />
          Performance Comparison: LSTM ON vs OFF
        </h3>
        <div className="grid grid-cols-3 gap-8">
          <ComparisonBar
            label="Average Latency"
            lstmOnVal={comparison.lstm_on.avg_latency}
            lstmOffVal={comparison.lstm_off.avg_latency}
            unit="ms"
            lowerIsBetter
          />
          <ComparisonBar
            label="Average Jitter"
            lstmOnVal={comparison.lstm_on.avg_jitter}
            lstmOffVal={comparison.lstm_off.avg_jitter}
            unit="ms"
            lowerIsBetter
          />
          <ComparisonBar
            label="Packet Loss"
            lstmOnVal={comparison.lstm_on.avg_packet_loss}
            lstmOffVal={comparison.lstm_off.avg_packet_loss}
            unit="%"
            lowerIsBetter
            decimals={3}
          />
        </div>
      </div>

      {/* Live Steering Feed */}
      {steeringEvents.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-pw-accent-light" />
            Live Steering Feed
          </h3>
          <div className="space-y-2">
            {steeringEvents.map((evt, i) => (
              <motion.div
                key={evt.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-3 text-xs py-2 px-3 rounded-lg bg-pw-bg/50"
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    evt.lstm_enabled ? "bg-pw-emerald" : "bg-pw-rose"
                  }`}
                />
                <span
                  className={`font-semibold uppercase ${
                    evt.action === "PREEMPTIVE_SHIFT"
                      ? "text-pw-emerald"
                      : "text-pw-rose"
                  }`}
                >
                  {evt.action.replace("_", " ")}
                </span>
                <span className="text-pw-muted">
                  {evt.source_link} → {evt.target_link}
                </span>
                <span className="flex-1 text-pw-muted/60 truncate">
                  {evt.reason}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Topology Visualization ─────────────────────────────── */

function TopologyView({
  scoreboard,
  lstmEnabled,
  activeRules = [],
}: {
  scoreboard: Record<string, LinkHealth>;
  lstmEnabled: boolean;
  activeRules?: { id: string; source_link: string; target_link: string; traffic_classes: string[] }[];
}) {
  const links = Object.entries(scoreboard);

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Network className="w-4 h-4 text-pw-accent-light" />
          SD-WAN Topology — Live Status
        </h3>
        <div className="flex items-center gap-4 text-xs text-pw-muted">
          <span className="flex items-center gap-1.5">
            <div className="w-3 h-1 rounded-full bg-pw-emerald" /> Healthy
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-3 h-1 rounded-full bg-pw-amber" /> Degraded
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-3 h-1 rounded-full bg-pw-rose" /> Critical
          </span>
        </div>
      </div>

      <svg viewBox="0 0 900 260" className="w-full" style={{ maxHeight: 280 }}>
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1f2a40" strokeWidth="0.3" />
          </pattern>
          <filter id="glow-green">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-red">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="node-shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.3" />
          </filter>
        </defs>
        <rect width="900" height="260" fill="url(#grid)" rx="12" />

        {/* Switch nodes */}
        <g filter="url(#node-shadow)">
          <rect x="120" y="100" width="100" height="50" rx="12" fill="#1a2035" stroke="#6366f1" strokeWidth="1.5" />
          <text x="170" y="122" textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="600">Switch 1</text>
          <text x="170" y="138" textAnchor="middle" fill="#94a3b8" fontSize="9">Edge Router</text>
        </g>
        <g filter="url(#node-shadow)">
          <rect x="680" y="100" width="100" height="50" rx="12" fill="#1a2035" stroke="#6366f1" strokeWidth="1.5" />
          <text x="730" y="122" textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="600">Switch 2</text>
          <text x="730" y="138" textAnchor="middle" fill="#94a3b8" fontSize="9">Edge Router</text>
        </g>

        {/* Host nodes */}
        <g filter="url(#node-shadow)">
          <circle cx="50" cy="125" r="22" fill="#1a2035" stroke="#818cf8" strokeWidth="1.5" />
          <text x="50" y="128" textAnchor="middle" fill="#e2e8f0" fontSize="10" fontWeight="600">H1</text>
        </g>
        <g filter="url(#node-shadow)">
          <circle cx="850" cy="125" r="22" fill="#1a2035" stroke="#818cf8" strokeWidth="1.5" />
          <text x="850" y="128" textAnchor="middle" fill="#e2e8f0" fontSize="10" fontWeight="600">H2</text>
        </g>

        {/* Host-to-switch connections */}
        <line x1="72" y1="125" x2="120" y2="125" stroke="#4b5563" strokeWidth="1.5" strokeDasharray="4 2" />
        <line x1="780" y1="125" x2="828" y2="125" stroke="#4b5563" strokeWidth="1.5" strokeDasharray="4 2" />

        {/* WAN Links */}
        {[
          { id: "fiber-primary", y: 55 },
          { id: "broadband-secondary", y: 105 },
          { id: "satellite-backup", y: 155 },
          { id: "5g-mobile", y: 205 },
        ].map(({ id, y }) => {
          const h = scoreboard[id];
          const score = h?.health_score ?? 75;
          const brownout = h?.brownout_active ?? false;
          const meta = LINK_META[id];
          const linkColor =
            score >= 70 ? "#34d399" : score >= 40 ? "#fbbf24" : "#f43f5e";
          const isActive = !brownout || lstmEnabled;

          return (
            <g key={id}>
              {/* Link line */}
              <line
                x1="220"
                y1={y}
                x2="680"
                y2={y}
                stroke={linkColor}
                strokeWidth={isActive ? 2.5 : 1.5}
                strokeOpacity={isActive ? 0.8 : 0.3}
                strokeDasharray={brownout && !lstmEnabled ? "6 4" : "none"}
              />
              {/* Animated flow particles */}
              {isActive && (
                <>
                  <circle r="3" fill={linkColor} opacity="0.9">
                    <animateMotion
                      dur={`${2 + Math.random()}s`}
                      repeatCount="indefinite"
                      path={`M220,${y} L680,${y}`}
                    />
                  </circle>
                  <circle r="3" fill={linkColor} opacity="0.6">
                    <animateMotion
                      dur={`${2.5 + Math.random()}s`}
                      repeatCount="indefinite"
                      path={`M220,${y} L680,${y}`}
                      begin="0.8s"
                    />
                  </circle>
                </>
              )}
              {/* Label */}
              <text
                x="450"
                y={y - 8}
                textAnchor="middle"
                fill={linkColor}
                fontSize="9"
                fontWeight="600"
              >
                {meta?.label} — {score.toFixed(0)}
                {brownout && !lstmEnabled ? " ⚠" : ""}
              </text>
              {/* Brownout warning */}
              {brownout && (
                <text
                  x="450"
                  y={y + 14}
                  textAnchor="middle"
                  fill={lstmEnabled ? "#34d399" : "#f43f5e"}
                  fontSize="8"
                >
                  {lstmEnabled ? "✓ Brownout avoided (LSTM)" : "⚠ BROWNOUT ACTIVE"}
                </text>
              )}
            </g>
          );
        })}

        {/* Reroute arcs for active routing rules */}
        {activeRules.map((rule) => {
          const linkYMap: Record<string, number> = {
            "fiber-primary": 55,
            "broadband-secondary": 105,
            "satellite-backup": 155,
            "5g-mobile": 205,
          };
          const yFrom = linkYMap[rule.source_link];
          const yTo = linkYMap[rule.target_link];
          if (yFrom == null || yTo == null) return null;
          const midY = (yFrom + yTo) / 2;
          const curveX = 780;
          return (
            <g key={`reroute-${rule.id}`}>
              <path
                d={`M700,${yFrom} Q${curveX},${midY} 700,${yTo}`}
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                strokeDasharray="5 3"
                opacity="0.7"
              >
                <animate attributeName="stroke-dashoffset" from="16" to="0" dur="0.8s" repeatCount="indefinite" />
              </path>
              <circle r="4" fill="#10b981">
                <animateMotion
                  dur="1.5s"
                  repeatCount="indefinite"
                  path={`M700,${yFrom} Q${curveX},${midY} 700,${yTo}`}
                />
              </circle>
              <text x={curveX + 8} y={midY + 4} fill="#10b981" fontSize="8" fontWeight="600">
                REROUTE
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ── Link Card ──────────────────────────────────────────── */

function LinkCard({
  linkId,
  health,
  lstmEnabled,
  rerouteStatus,
}: {
  linkId: string;
  health: LinkHealth;
  lstmEnabled: boolean;
  rerouteStatus?: "diverted_from" | "diverted_to";
}) {
  const meta = LINK_META[linkId] || {
    label: linkId,
    icon: Network,
    color: "#6366f1",
    gradient: "from-indigo-500 to-indigo-600",
  };
  const Icon = meta.icon;

  const score = health.health_score;
  const scoreColor =
    score >= 70
      ? "text-pw-emerald"
      : score >= 40
      ? "text-pw-amber"
      : "text-pw-rose";
  const scoreGlow =
    score >= 70
      ? "shadow-pw-emerald/20"
      : score >= 40
      ? "shadow-pw-amber/20"
      : "shadow-pw-rose/20";

  const forecastData = (health.latency_forecast || []).map((v, i) => ({
    t: i,
    value: v,
  }));

  const showRawComparison =
    lstmEnabled && health.raw_latency !== undefined;

  return (
    <motion.div
      layout
      className={`glass-card-hover p-5 ${
        health.brownout_active ? "border-pw-rose/40" : ""
      } ${
        rerouteStatus === "diverted_from"
          ? "border-red-500/30"
          : rerouteStatus === "diverted_to"
          ? "border-pw-emerald/40"
          : ""
      }`}
    >
      {/* Reroute Indicator */}
      {rerouteStatus && (
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold mb-3 ${
            rerouteStatus === "diverted_from"
              ? "bg-red-500/10 text-red-400 border border-red-500/20"
              : "bg-pw-emerald/10 text-pw-emerald border border-pw-emerald/20"
          }`}
        >
          {rerouteStatus === "diverted_from" ? (
            <>
              <TrendingDown className="w-3 h-3" />
              Traffic diverted away — load reduced
            </>
          ) : (
            <>
              <TrendingUp className="w-3 h-3" />
              Receiving rerouted traffic
            </>
          )}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-xl bg-gradient-to-br ${meta.gradient} flex items-center justify-center`}
          >
            <Icon className="w-4 h-4 text-white" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">{meta.label}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              {health.trend === "degrading" ? (
                <TrendingDown className="w-3 h-3 text-pw-rose" />
              ) : health.trend === "improving" ? (
                <TrendingUp className="w-3 h-3 text-pw-emerald" />
              ) : (
                <Activity className="w-3 h-3 text-pw-muted" />
              )}
              <span className="text-[10px] uppercase tracking-wider text-pw-muted">
                {health.trend}
              </span>
            </div>
          </div>
        </div>

        {/* Health Score */}
        <div className="text-right">
          <p className={`text-2xl font-bold ${scoreColor}`}>
            {score.toFixed(0)}
          </p>
          <p className="text-[10px] text-pw-muted uppercase tracking-wider">
            Health
          </p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <MiniMetric
          label="Latency"
          value={health.latency_current}
          unit="ms"
          rawValue={showRawComparison ? health.raw_latency : undefined}
        />
        <MiniMetric
          label="Jitter"
          value={health.jitter_current}
          unit="ms"
          rawValue={showRawComparison ? health.raw_jitter : undefined}
        />
        <MiniMetric
          label="Pkt Loss"
          value={health.packet_loss_current}
          unit="%"
          decimals={2}
          rawValue={showRawComparison ? health.raw_packet_loss : undefined}
        />
      </div>

      {/* Forecast Sparkline */}
      {forecastData.length > 0 && (
        <div className="h-16 -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={forecastData}>
              <defs>
                <linearGradient
                  id={`grad-${linkId}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor={meta.color}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="100%"
                    stopColor={meta.color}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="value"
                stroke={meta.color}
                strokeWidth={1.5}
                fill={`url(#grad-${linkId})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Brownout Indicator */}
      <AnimatePresence>
        {health.brownout_active && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className={`mt-3 pt-3 border-t border-pw-border flex items-center gap-2 text-xs ${
              lstmEnabled ? "text-pw-emerald" : "text-pw-rose"
            }`}
          >
            {lstmEnabled ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>
                  Brownout detected — traffic proactively rerouted by LSTM
                </span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
                <span>BROWNOUT — degraded performance, reactive failover</span>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Mini Metric ────────────────────────────────────────── */

function MiniMetric({
  label,
  value,
  unit,
  decimals = 1,
  rawValue,
}: {
  label: string;
  value: number;
  unit: string;
  decimals?: number;
  rawValue?: number;
}) {
  const improved = rawValue !== undefined && value < rawValue;

  return (
    <div className="bg-pw-bg/50 rounded-xl px-3 py-2 text-center">
      <p className="text-[10px] uppercase tracking-wider text-pw-muted mb-1">
        {label}
      </p>
      <p className="text-sm font-bold text-pw-text">
        {value.toFixed(decimals)}
        <span className="text-[10px] text-pw-muted ml-0.5">{unit}</span>
      </p>
      {rawValue !== undefined && (
        <p
          className={`text-[9px] mt-0.5 ${
            improved ? "text-pw-emerald" : "text-pw-muted/60"
          }`}
        >
          {improved ? "↓" : ""} raw: {rawValue.toFixed(decimals)}
          {unit}
        </p>
      )}
    </div>
  );
}

/* ── Comparison Bar ─────────────────────────────────────── */

function ComparisonBar({
  label,
  lstmOnVal,
  lstmOffVal,
  unit,
  lowerIsBetter = true,
  decimals = 1,
}: {
  label: string;
  lstmOnVal: number;
  lstmOffVal: number;
  unit: string;
  lowerIsBetter?: boolean;
  decimals?: number;
}) {
  const maxVal = Math.max(lstmOnVal, lstmOffVal, 0.01);
  const onPct = Math.min((lstmOnVal / (maxVal * 1.3)) * 100, 100);
  const offPct = Math.min((lstmOffVal / (maxVal * 1.3)) * 100, 100);
  const onBetter = lowerIsBetter
    ? lstmOnVal < lstmOffVal
    : lstmOnVal > lstmOffVal;

  const improvement =
    lstmOffVal > 0
      ? (((lstmOffVal - lstmOnVal) / lstmOffVal) * 100).toFixed(0)
      : "0";

  return (
    <div>
      <p className="text-xs text-pw-muted mb-3 font-medium">{label}</p>

      {/* LSTM ON bar */}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-[10px] w-14 text-pw-emerald font-medium">
          AI ON
        </span>
        <div className="flex-1 h-3 bg-pw-bg/80 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${onPct}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="h-full rounded-full bg-gradient-to-r from-pw-emerald/80 to-pw-emerald"
          />
        </div>
        <span className="text-xs font-bold text-pw-emerald w-20 text-right">
          {lstmOnVal.toFixed(decimals)} {unit}
        </span>
      </div>

      {/* LSTM OFF bar */}
      <div className="flex items-center gap-3">
        <span className="text-[10px] w-14 text-pw-rose font-medium">
          AI OFF
        </span>
        <div className="flex-1 h-3 bg-pw-bg/80 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${offPct}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="h-full rounded-full bg-gradient-to-r from-pw-rose/80 to-pw-rose"
          />
        </div>
        <span className="text-xs font-bold text-pw-rose w-20 text-right">
          {lstmOffVal.toFixed(decimals)} {unit}
        </span>
      </div>

      {/* Improvement badge */}
      {onBetter && Number(improvement) > 0 && (
        <div className="mt-2 text-right">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-pw-emerald/10 text-pw-emerald font-medium">
            ↓ {improvement}% better with AI
          </span>
        </div>
      )}
    </div>
  );
}

export default NetworkSimulation;
