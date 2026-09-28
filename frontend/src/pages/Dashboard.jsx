import { useEffect, useState } from 'react'

import client from '../api/client'

/** The main graph screen. W1-8 leaves it as a placeholder - GraphView.jsx and
 *  the Cytoscape canvas are W3, F3b.
 *
 *  It does call GET /api/graph, though, rather than rendering a static box:
 *  that is what proves the whole chain end to end - Vite proxy, JWT
 *  interceptor, protected route, stub router - is actually wired. */
export default function Dashboard() {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' })

  useEffect(() => {
    let cancelled = false
    client
      .get('/graph', { params: { depth: 2 } })
      .then((response) => {
        if (cancelled) return
        // A 200 is not proof of the right body. If the dev proxy is
        // misconfigured or restarting, Vite answers /api/* with index.html and
        // axios reports success - reading .nodes off that threw and blanked
        // the whole page. Check the shape before trusting it.
        const data = response.data
        if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
          setState({
            status: 'error',
            data: null,
            error: 'The server returned an unexpected response. Is the /api proxy up?',
          })
          return
        }
        setState({ status: 'ready', data, error: '' })
      })
      .catch((err) => {
        if (!cancelled) {
          setState({ status: 'error', data: null, error: err.message ?? 'Request failed' })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold text-white">Dashboard</h2>
        <p className="mt-1 text-sm text-slate-400">
          The graph canvas lands in Week 3. This page currently just confirms the
          backend is reachable through the proxy with a valid token.
        </p>
      </header>

      {state.status === 'loading' && <p className="text-sm text-slate-400">Loading graph…</p>}

      {state.status === 'error' && (
        <p role="alert" className="rounded bg-red-950 px-3 py-2 text-sm text-red-300">
          Could not load the graph: {state.error}
        </p>
      )}

      {state.status === 'ready' && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Nodes" value={state.data.nodes.length} />
            <Stat label="Edges" value={state.data.edges.length} />
            <Stat label="Depth" value={state.data.depth} />
          </div>
          {state.data.nodes.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-600 bg-slate-800/50 p-8 text-center">
              <p className="text-sm text-slate-400">
                No entities visible yet. The graph endpoint is real as of W2 — the
                database is simply empty until seed.py runs.
              </p>
            </div>
          )}
        </>
      )}

      <p className="text-xs text-slate-500">
        Live data, agency-scoped by build_graph(). Counts stay at zero until seed.py
        populates the database.
      </p>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  )
}
