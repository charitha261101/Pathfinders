import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { useNetworkStore } from '../../store/networkStore';

interface TopoNode {
  id: string;
  type: 'switch' | 'host';
  x: number;
  y: number;
}

interface TopoLink {
  source: string;
  target: string;
  linkId: string;
  healthScore: number;
}

const TopologyMap: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const predictions = useNetworkStore((state) => state.predictions);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 400;

    // Reference SD-WAN topology nodes
    const nodes: TopoNode[] = [
      { id: 's1', type: 'switch', x: 200, y: 200 },
      { id: 's2', type: 'switch', x: 600, y: 200 },
      { id: 'h1', type: 'host', x: 50, y: 200 },
      { id: 'h2', type: 'host', x: 750, y: 200 },
    ];

    // WAN links between switches
    const links: TopoLink[] = [
      { source: 'h1', target: 's1', linkId: 'host-link-1', healthScore: 100 },
      { source: 's2', target: 'h2', linkId: 'host-link-2', healthScore: 100 },
      { source: 's1', target: 's2', linkId: 'fiber-primary', healthScore: predictions['fiber-primary']?.health_score ?? 80 },
      { source: 's1', target: 's2', linkId: 'broadband-secondary', healthScore: predictions['broadband-secondary']?.health_score ?? 70 },
      { source: 's1', target: 's2', linkId: 'satellite-backup', healthScore: predictions['satellite-backup']?.health_score ?? 50 },
      { source: 's1', target: 's2', linkId: '5g-mobile', healthScore: predictions['5g-mobile']?.health_score ?? 65 },
    ];

    const g = svg.append('g');

    // Draw links
    const linkOffsets: Record<string, number> = {
      'fiber-primary': -45,
      'broadband-secondary': -15,
      'satellite-backup': 15,
      '5g-mobile': 45,
    };

    links.forEach((link) => {
      const src = nodes.find((n) => n.id === link.source)!;
      const dst = nodes.find((n) => n.id === link.target)!;
      const offset = linkOffsets[link.linkId] ?? 0;

      const color = link.healthScore >= 70
        ? '#22c55e'
        : link.healthScore >= 40
        ? '#eab308'
        : '#ef4444';

      g.append('line')
        .attr('x1', src.x)
        .attr('y1', src.y + offset)
        .attr('x2', dst.x)
        .attr('y2', dst.y + offset)
        .attr('stroke', color)
        .attr('stroke-width', 3)
        .attr('stroke-opacity', 0.7);

      // Link label
      if (linkOffsets[link.linkId] !== undefined) {
        g.append('text')
          .attr('x', (src.x + dst.x) / 2)
          .attr('y', (src.y + dst.y) / 2 + offset - 8)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10px')
          .attr('fill', '#6b7280')
          .text(`${link.linkId} (${link.healthScore.toFixed(0)})`);
      }
    });

    // Draw nodes
    nodes.forEach((node) => {
      const color = node.type === 'switch' ? '#3b82f6' : '#8b5cf6';
      const radius = node.type === 'switch' ? 25 : 18;

      g.append('circle')
        .attr('cx', node.x)
        .attr('cy', node.y)
        .attr('r', radius)
        .attr('fill', color)
        .attr('stroke', 'white')
        .attr('stroke-width', 2);

      g.append('text')
        .attr('x', node.x)
        .attr('y', node.y + 4)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('fill', 'white')
        .attr('font-weight', 'bold')
        .text(node.id);
    });
  }, [predictions]);

  return (
    <svg ref={svgRef} width="100%" height={400} viewBox="0 0 800 400" />
  );
};

export default TopologyMap;
