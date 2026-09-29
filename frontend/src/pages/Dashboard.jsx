import { useCallback, useEffect, useState } from 'react'

import client from '../api/client'
import EntityPanel from '../components/EntityPanel'
import GraphView from '../components/GraphView'
import SearchBar from '../components/SearchBar'
import { useAuth } from '../context/AuthContext'

const EMPTY = { nodes: [], edges: [] }

/** The main graph screen - F3.
 *
 *  Everything it shows is agency-scoped by build_graph() on the server, so the
 *  same query here renders a different network depending on who is logged in.
 *  That is demo criterion S2 and it is the point of the screen. */
export default function Dashboard() {
  const { user } = useAuth()
  const [centerId, setCenterId] = useState(null)
  const [depth, setDepth] = useState(2)
  const [selectedId, setSelectedId] = useState(null)
  // One piece of state, stamped with the request it answers. "Loading" is then
  // derived at render time - the answer we hold is not for the query we are
  // asking - rather than set at the top of the effect, which costs an extra
  // render and makes the effect the source of truth for something the props
  // already determine.
  const [answer, setAnswer] = useState(null)
  const requestKey = `${centerId ?? 'all'}|${depth}`
  const current = answer?.key === requestKey ? answer : null
  const loading = current === null
  // `data` is the same object identity until a new response lands, which is
  // what keeps GraphView's useMemo from re-running the layout every render.
  const graph = current?.data ?? EMPTY
  const error = current?.error ?? ''

  useEffect(() => {
    let cancelled = false
    client
      .get('/graph', {
        params: { depth, ...(centerId != null ? { center: centerId } : {}) },
      })
      .then((response) => {
        if (cancelled) return
        const body = response.data
        // A 200 is not proof of the right body: a stale dev proxy answers
        // /api/* with index.html and axios reports success.
        if (!body || !Array.isArray(body.nodes) || !Array.isArray(body.edges)) {
          setAnswer({
            key: requestKey,
            data: EMPTY,
            error: 'The server returned an unexpected response. Is the /api proxy up?',
          })
          return
        }
        setAnswer({
          key: requestKey,
          data: { nodes: body.nodes, edges: body.edges },
          error: '',
        })
      })
      .catch((err) => {
        if (cancelled) return
        setAnswer({
          key: requestKey,
          data: EMPTY,
          error:
            err.response?.status === 404
              ? 'That centre is not available to your agency.'
              : 'Could not load the graph.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [centerId, depth, requestKey])

  const recentre = useCallback((id) => {
    setCenterId(id)
    setSelectedId(id)
  }, [])

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">Network</h2>
          <p className="mt-1 text-sm text-slate-400">
            Scoped to {user.agency_code}
            {user.role === 'admin' ? ' — as an admin you see every agency.' : ' and anything shared with it.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-400">
            {graph.nodes.length} nodes · {graph.edges.length} edges
          </span>
          {centerId != null && (
            <button
              type="button"
              onClick={() => { setCenterId(null); setSelectedId(null) }}
              className="rounded border border-slate-600 px-2.5 py-1 text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Show whole network
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <SearchBar onPick={recentre} />
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-slate-400">Depth</span>
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDepth(d)}
              aria-pressed={depth === d}
              disabled={centerId == null}
              className={`rounded px-2.5 py-1 text-sm disabled:opacity-40 ${
                depth === d
                  ? 'bg-sky-700 text-white'
                  : 'border border-slate-600 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
        {centerId == null && (
          <span className="text-xs text-slate-500">
            Depth applies once a centre is chosen.
          </span>
        )}
      </div>

      {error && (
        <p role="alert" className="rounded bg-red-950 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
        <div>
          {loading ? (
            <div className="flex h-[32rem] items-center justify-center rounded-lg border border-slate-700 bg-slate-900">
              <p className="text-sm text-slate-400">Loading graph…</p>
            </div>
          ) : (
            <GraphView
              elements={graph}
              selectedId={selectedId}
              centerId={centerId}
              onSelect={setSelectedId}
              onRecentre={recentre}
            />
          )}
        </div>
        {/* key remounts on a new selection, so the panel's initial state is
            derived rather than reset inside its effect. */}
        <EntityPanel key={selectedId ?? 'none'} entityId={selectedId} onRecentre={recentre} />
      </div>

      <p className="text-xs text-slate-500">
        Synthetic data only — 650 entities and 940 relationships generated by
        seed.py from a fixed seed. No real personal data is used anywhere.
      </p>
    </div>
  )
}
