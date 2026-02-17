// frontend/src/components/HealthScoreboard/HealthScoreboard.tsx

import React, { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface LinkHealth {
  health_score: number;
  confidence: number;
  latency_current: number;
  jitter_current: number;
  packet_loss_current: number;
  latency_forecast: number[];
  trend: 'improving' | 'stable' | 'degrading';
}

interface ScoreboardData {
  [linkId: string]: LinkHealth;
}

const HealthScoreboard: React.FC = () => {
  const [data, setData] = useState<ScoreboardData>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/scoreboard`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'scoreboard_update') {
        setData(msg.data);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-6">
      {Object.entries(data).map(([linkId, health]) => (
        <LinkCard key={linkId} linkId={linkId} health={health} />
      ))}
    </div>
  );
};

const LinkCard: React.FC<{ linkId: string; health: LinkHealth }> = ({ linkId, health }) => {
  const scoreColor = health.health_score >= 70
    ? '#22c55e'
    : health.health_score >= 40
    ? '#eab308'
    : '#ef4444';

  const trendIcon = {
    improving: '\u2191',
    stable: '\u2192',
    degrading: '\u2193',
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-5 border-l-4"
         style={{ borderLeftColor: scoreColor }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-gray-600 uppercase">{linkId}</h3>
        <span className="text-xs text-gray-400">
          {(health.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>

      {/* Health Score (large) */}
      <div className="text-center mb-4">
        <span className="text-5xl font-bold" style={{ color: scoreColor }}>
          {health.health_score.toFixed(0)}
        </span>
        <span className="text-lg ml-1" style={{ color: scoreColor }}>
          {trendIcon[health.trend]}
        </span>
        <p className="text-xs text-gray-400 mt-1">Health Score</p>
      </div>

      {/* Current Metrics */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <MetricBadge label="Latency" value={`${health.latency_current.toFixed(1)}ms`} />
        <MetricBadge label="Jitter" value={`${health.jitter_current.toFixed(1)}ms`} />
        <MetricBadge label="Loss" value={`${health.packet_loss_current.toFixed(2)}%`} />
      </div>

      {/* Forecast Sparkline */}
      <div className="mt-4">
        <ForecastSparkline data={health.latency_forecast} color={scoreColor} />
      </div>
    </div>
  );
};

const MetricBadge: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="bg-gray-50 rounded-md py-1 px-2">
    <div className="font-medium text-gray-700">{value}</div>
    <div className="text-gray-400">{label}</div>
  </div>
);

const ForecastSparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 200, height = 40;
    const x = d3.scaleLinear().domain([0, data.length - 1]).range([0, width]);
    const y = d3.scaleLinear()
      .domain([d3.min(data)! * 0.9, d3.max(data)! * 1.1])
      .range([height, 0]);

    const line = d3.line<number>()
      .x((_, i) => x(i))
      .y((d) => y(d))
      .curve(d3.curveBasis);

    svg.append('path')
      .datum(data)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 1.5);
  }, [data, color]);

  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-400">30s forecast</span>
      <svg ref={svgRef} width={200} height={40} />
    </div>
  );
};

export default HealthScoreboard;
