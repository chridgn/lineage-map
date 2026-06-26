import { useState, useEffect, useCallback } from 'react';
import Graph from './Graph.jsx';

const SEARCH_DEBOUNCE_MS = 200;

export default function App() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [searchIds, setSearchIds] = useState(new Set());

  useEffect(() => {
    fetch('/api/graph')
      .then(r => r.json())
      .then(setGraph)
      .catch(() => setError('Could not load graph. Is the server running?'));
  }, []);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setSearchIds(new Set());
      return;
    }
    const t = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => setSearchIds(new Set(data.ids)));
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  if (error) return <ErrorState message={error} />;
  if (!graph) return <LoadingState />;

  return (
    <div style={styles.shell}>
      <header style={styles.header}>
        <span style={styles.logo}>LineageMap</span>
        <input
          style={styles.search}
          type="text"
          placeholder="Search column or model…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          spellCheck={false}
        />
        <span style={styles.meta}>
          {graph.nodes.length} columns · {graph.edges.length} edges
        </span>
      </header>
      <div style={styles.canvas}>
        <Graph nodes={graph.nodes} edges={graph.edges} searchIds={searchIds} />
      </div>
      <footer style={styles.hint}>
        Hover a node to trace lineage &nbsp;·&nbsp; Scroll to zoom &nbsp;·&nbsp; Drag to pan
      </footer>
    </div>
  );
}

function LoadingState() {
  return (
    <div style={styles.center}>
      <span style={{ color: '#64748b', fontSize: 14 }}>Loading graph…</span>
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div style={styles.center}>
      <span style={{ color: '#ef4444', fontSize: 14 }}>{message}</span>
    </div>
  );
}

const styles = {
  shell: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    height: '100%',
    background: '#f8fafc',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '0 20px',
    height: 52,
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    flexShrink: 0,
    zIndex: 10,
  },
  logo: {
    fontSize: 15,
    fontWeight: 700,
    color: '#1e293b',
    letterSpacing: '-0.02em',
    fontFamily: 'ui-monospace, monospace',
    flexShrink: 0,
  },
  search: {
    flex: '1 1 auto',
    maxWidth: 320,
    height: 32,
    padding: '0 12px',
    borderRadius: 6,
    border: '1px solid #e2e8f0',
    background: '#f8fafc',
    fontSize: 13,
    color: '#1e293b',
    outline: 'none',
    fontFamily: 'ui-monospace, monospace',
  },
  meta: {
    marginLeft: 'auto',
    fontSize: 12,
    color: '#94a3b8',
    flexShrink: 0,
  },
  canvas: {
    flex: '1 1 0',
    overflow: 'hidden',
    position: 'relative',
  },
  hint: {
    textAlign: 'center',
    padding: '6px 0',
    fontSize: 11,
    color: '#94a3b8',
    background: '#f8fafc',
    borderTop: '1px solid #e2e8f0',
    flexShrink: 0,
  },
  center: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
  },
};
