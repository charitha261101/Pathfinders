import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { useNetworkStore } from '../../store/networkStore';

const PredictionChart: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const predictions = useNetworkStore((state) => state.predictions);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 120, bottom: 40, left: 50 };
    const width = 700 - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Collect all forecast data
    const linkIds = Object.keys(predictions);
    if (linkIds.length === 0) {
      g.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#9ca3af')
        .attr('font-size', '14px')
        .text('Waiting for prediction data...');
      return;
    }

    const colors = d3.scaleOrdinal<string>()
      .domain(linkIds)
      .range(['#3b82f6', '#ef4444', '#f59e0b', '#10b981']);

    // Find max horizon length
    const maxLen = Math.max(
      ...linkIds.map((id) => predictions[id]?.latency_forecast?.length ?? 0)
    );

    if (maxLen === 0) return;

    const allValues = linkIds.flatMap(
      (id) => predictions[id]?.latency_forecast ?? []
    );

    const x = d3.scaleLinear().domain([0, maxLen - 1]).range([0, width]);
    const y = d3.scaleLinear()
      .domain([
        Math.max(0, (d3.min(allValues) ?? 0) * 0.8),
        (d3.max(allValues) ?? 100) * 1.2,
      ])
      .range([height, 0]);

    // Axes
    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat((d) => `${d}s`))
      .attr('font-size', '10px');

    g.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .attr('font-size', '10px');

    // Y-axis label
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -40)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('fill', '#6b7280')
      .text('Latency (ms)');

    // X-axis label
    g.append('text')
      .attr('x', width / 2)
      .attr('y', height + 35)
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('fill', '#6b7280')
      .text('Forecast Horizon');

    // Draw forecast lines
    linkIds.forEach((linkId) => {
      const forecast = predictions[linkId]?.latency_forecast ?? [];
      if (forecast.length === 0) return;

      const line = d3.line<number>()
        .x((_, i) => x(i))
        .y((d) => y(d))
        .curve(d3.curveCatmullRom);

      g.append('path')
        .datum(forecast)
        .attr('d', line)
        .attr('fill', 'none')
        .attr('stroke', colors(linkId))
        .attr('stroke-width', 2);
    });

    // Legend
    const legend = g.append('g')
      .attr('transform', `translate(${width + 10}, 0)`);

    linkIds.forEach((linkId, i) => {
      const lg = legend.append('g')
        .attr('transform', `translate(0, ${i * 20})`);

      lg.append('rect')
        .attr('width', 12)
        .attr('height', 12)
        .attr('fill', colors(linkId));

      lg.append('text')
        .attr('x', 16)
        .attr('y', 10)
        .attr('font-size', '10px')
        .attr('fill', '#374151')
        .text(linkId);
    });
  }, [predictions]);

  return (
    <svg ref={svgRef} width="100%" height={300} viewBox="0 0 700 300" />
  );
};

export default PredictionChart;
