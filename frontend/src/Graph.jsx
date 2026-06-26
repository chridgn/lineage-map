import { useEffect, useRef, useMemo, useState } from 'react';
import * as d3 from 'd3';
import dagre from '@dagrejs/dagre';

const NODE_W = 172;
const NODE_H = 46;

// ── layout ──────────────────────────────────────────────────────────────────

function computeLayout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 90, marginx: 48, marginy: 48 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach(e => {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  });

  dagre.layout(g);

  return {
    nodes: nodes.map(n => {
      const pos = g.node(n.id) || { x: 0, y: 0 };
      return { ...n, x: pos.x, y: pos.y };
    }),
    edges: edges
      .filter(e => g.hasNode(e.source) && g.hasNode(e.target))
      .map(e => {
        const data = g.edge({ v: e.source, w: e.target });
        return { ...e, points: data?.points || [] };
      }),
    graphWidth: g.graph().width || 800,
    graphHeight: g.graph().height || 600,
  };
}

// ── highlight helpers ────────────────────────────────────────────────────────

function buildAdjacency(edges) {
  const up = {};   // target → [sources]
  const down = {}; // source → [targets]
  edges.forEach(({ source, target }) => {
    (up[target] = up[target] || []).push(source);
    (down[source] = down[source] || []).push(target);
  });
  return { up, down };
}

function bfs(startId, adjMap) {
  const visited = new Set();
  const queue = [startId];
  while (queue.length) {
    const id = queue.shift();
    if (visited.has(id)) continue;
    visited.add(id);
    (adjMap[id] || []).forEach(n => queue.push(n));
  }
  visited.delete(startId);
  return visited;
}

// ── edge path ────────────────────────────────────────────────────────────────

const curveLine = d3.line().x(p => p.x).y(p => p.y).curve(d3.curveBasis);

function edgePath(points) {
  if (!points?.length) return '';
  return curveLine(points);
}

// ── node colors ──────────────────────────────────────────────────────────────

// Deterministic pastel from model name (for model group identity)
function modelHue(model) {
  let h = 0;
  for (let i = 0; i < model.length; i++) h = (h * 31 + model.charCodeAt(i)) % 360;
  return h;
}

// ── component ────────────────────────────────────────────────────────────────

export default function Graph({ nodes, edges, searchIds }) {
  const svgRef = useRef(null);
  const canvasRef = useRef(null);
  const [hoveredId, setHoveredId] = useState(null);

  const layout = useMemo(() => computeLayout(nodes, edges), [nodes, edges]);
  const adj = useMemo(() => buildAdjacency(edges), [edges]);

  const upstream = useMemo(
    () => hoveredId ? bfs(hoveredId, adj.up) : new Set(),
    [hoveredId, adj]
  );
  const downstream = useMemo(
    () => hoveredId ? bfs(hoveredId, adj.down) : new Set(),
    [hoveredId, adj]
  );

  // d3 zoom + initial fit
  useEffect(() => {
    const svg = d3.select(svgRef.current);
    const canvas = d3.select(canvasRef.current);
    const zoom = d3.zoom()
      .scaleExtent([0.05, 4])
      .on('zoom', e => canvas.attr('transform', e.transform));

    svg.call(zoom).on('dblclick.zoom', null);

    const { graphWidth, graphHeight } = layout;
    const { clientWidth: vw, clientHeight: vh } = svgRef.current;
    const scale = Math.min((vw - 80) / graphWidth, (vh - 80) / graphHeight, 1);
    const tx = (vw - graphWidth * scale) / 2;
    const ty = (vh - graphHeight * scale) / 2;
    svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }, [layout]);

  function nodeState(id) {
    if (id === hoveredId) return 'hovered';
    if (downstream.has(id)) return 'downstream';
    if (upstream.has(id)) return 'upstream';
    if (searchIds?.size && searchIds.has(id)) return 'search';
    if (hoveredId || searchIds?.size) return 'dimmed';
    return 'default';
  }

  const stateStyles = {
    hovered:    { fill: '#3b82f6', stroke: '#1d4ed8', strokeWidth: 2, textFill: '#fff', opacity: 1 },
    downstream: { fill: '#ef4444', stroke: '#b91c1c', strokeWidth: 2, textFill: '#fff', opacity: 1 },
    upstream:   { fill: '#3b82f6', stroke: '#1d4ed8', strokeWidth: 1.5, textFill: '#fff', opacity: 1 },
    search:     { fill: '#f59e0b', stroke: '#d97706', strokeWidth: 2, textFill: '#fff', opacity: 1 },
    dimmed:     { fill: '#f1f5f9', stroke: '#e2e8f0', strokeWidth: 1, textFill: '#94a3b8', opacity: 0.4 },
    default:    { fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1, textFill: '#1e293b', opacity: 1 },
  };

  function edgeStyle(e) {
    const srcDown = e.source === hoveredId || downstream.has(e.source);
    const tgtDown = e.target === hoveredId || downstream.has(e.target);
    const srcUp = e.source === hoveredId || upstream.has(e.source);
    const tgtUp = e.target === hoveredId || upstream.has(e.target);

    if (hoveredId) {
      if (srcDown && tgtDown) return { stroke: '#ef4444', opacity: 1, width: 2 };
      if (srcUp && tgtUp) return { stroke: '#3b82f6', opacity: 1, width: 2 };
      return { stroke: '#e2e8f0', opacity: 0.3, width: 1 };
    }
    return { stroke: '#94a3b8', opacity: 0.6, width: 1.5 };
  }

  return (
    <svg
      ref={svgRef}
      style={{ width: '100%', height: '100%', display: 'block' }}
      onMouseLeave={() => setHoveredId(null)}
    >
      <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" />
        </marker>
        <marker id="arrow-blue" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#3b82f6" />
        </marker>
        <marker id="arrow-red" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#ef4444" />
        </marker>
      </defs>

      <g ref={canvasRef}>
        {/* Edges — rendered under nodes */}
        {layout.edges.map((e, i) => {
          const s = edgeStyle(e);
          const markerColor = s.stroke === '#3b82f6' ? 'blue' : s.stroke === '#ef4444' ? 'red' : '';
          return (
            <path
              key={i}
              d={edgePath(e.points)}
              fill="none"
              stroke={s.stroke}
              strokeWidth={s.width}
              opacity={s.opacity}
              markerEnd={`url(#arrow${markerColor ? '-' + markerColor : ''})`}
              style={{ transition: 'stroke 0.12s, opacity 0.12s' }}
            />
          );
        })}

        {/* Nodes */}
        {layout.nodes.map(n => {
          const s = stateStyles[nodeState(n.id)];
          const hue = modelHue(n.model);
          const x = n.x - NODE_W / 2;
          const y = n.y - NODE_H / 2;
          const isDefault = nodeState(n.id) === 'default';

          return (
            <g
              key={n.id}
              transform={`translate(${x},${y})`}
              style={{ cursor: 'pointer', transition: 'opacity 0.12s' }}
              opacity={s.opacity}
              onMouseEnter={() => setHoveredId(n.id)}
            >
              {/* Model color accent bar */}
              {isDefault && (
                <rect
                  width={4}
                  height={NODE_H}
                  rx={3}
                  fill={`hsl(${hue},60%,65%)`}
                />
              )}
              <rect
                x={isDefault ? 4 : 0}
                width={isDefault ? NODE_W - 4 : NODE_W}
                height={NODE_H}
                rx={6}
                fill={s.fill}
                stroke={s.stroke}
                strokeWidth={s.strokeWidth}
                style={{ transition: 'fill 0.12s, stroke 0.12s' }}
              />
              {/* Model label */}
              <text
                x={NODE_W / 2 + (isDefault ? 2 : 0)}
                y={15}
                textAnchor="middle"
                fontSize={10}
                fill={isDefault ? '#64748b' : 'rgba(255,255,255,0.75)'}
                fontFamily="ui-monospace, 'SF Mono', monospace"
                style={{ transition: 'fill 0.12s', userSelect: 'none' }}
              >
                {n.model}
              </text>
              {/* Column label */}
              <text
                x={NODE_W / 2 + (isDefault ? 2 : 0)}
                y={32}
                textAnchor="middle"
                fontSize={13}
                fontWeight="600"
                fill={s.textFill}
                fontFamily="ui-monospace, 'SF Mono', monospace"
                style={{ transition: 'fill 0.12s', userSelect: 'none' }}
              >
                {n.column}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
