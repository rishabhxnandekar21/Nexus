import { useCallback, useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import EntityPanel from '../components/EntityPanel'
import GraphView from '../components/GraphView'
import { ErrorStrip } from '../components/Notice'
import Notice from '../components/Notice'
import SearchBar from '../components/SearchBar'
import Timeline from '../components/Timeline'
import { useAuth } from '../context/AuthContext'

const EMPTY = { nodes: [], edges: [] }
const NO_METRICS = { metrics: [], top_connectors: [], community_count: 0 }
// Used only if the loaded graph carries no dated edges at all.
const FALLBACK_SPAN = [2019, 2025]
const DEBOUNCE_MS = 150

/** Holds a value back until it stops changing - the slider updates its handle
 *  every pixel, but the graph should only re-filter once you pause. */
function useDebounced(value, ms) {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return settled
}
const SIZE_OPTIONS = [
  ['degree', 'Degree'],
  ['betweenness', 'Betweenness'],
  ['pagerank', 'PageRank'],
]

/** The main graph screen - F3, and the F5 analytics on top of it.
 *
 *  Everything is agency-scoped by build_graph() on the server, so the same
 *  query renders a different network - and different centrality - depending
 *  on who is logged in. That is demo criterion S2. */
export default function Dashboard() {
  const { user } = useAuth()
  const [centerId, setCenterId] = useState(null)
  const [depth, setDepth] = useState(2)
  const [selectedId, setSelectedId] = useState(null)
  const [colourBy, setColourBy] = useState('type')
  const [sizeBy, setSizeBy] = useState('degree')
  const [pathEnds, setPathEnds] = useState({ from: null, to: null })
  const [range, setRange] = useState(null)
  const [playing, setPlaying] = useState(false)
  // Bumping this refires the fetch effect, so a failed load is recoverable
  // without a page reload - the backend may simply have been restarting.
  const [reloads, setReloads] = useState(0)

  // One piece of state per request, stamped with the request it answers, so
  // "loading" is derived at render time rather than set at the top of an
  // effect. `data` keeps its object identity until a new response lands,
  // which is what stops GraphView re-running the layout on every render.
  const [answer, setAnswer] = useState(null)
  const [stats, setStats] = useState(null)
  const [pathAnswer, setPathAnswer] = useState(null)

  const requestKey = `${centerId ?? 'all'}|${depth}`
  const current = answer?.key === requestKey ? answer : null
  const loading = current === null
  const graph = current?.data ?? EMPTY
  const error = current?.error ?? ''
  const analytics = stats?.key === requestKey ? stats.data : NO_METRICS

  useEffect(() => {
    let cancelled = false
    const params = { depth, ...(centerId != null ? { center: centerId } : {}) }

    client
      .get('/graph', { params })
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
        setAnswer({ key: requestKey, data: { nodes: body.nodes, edges: body.edges }, error: '' })
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

    // Analytics is a second, slower request on purpose. The graph should not
    // wait on betweenness to draw.
    client
      .get('/graph/analytics', { params })
      .then((response) => {
        if (cancelled) return
        const body = response.data
        setStats({
          key: requestKey,
          data: Array.isArray(body?.metrics) ? body : NO_METRICS,
        })
      })
      .catch(() => {
        if (!cancelled) setStats({ key: requestKey, data: NO_METRICS })
      })

    return () => {
      cancelled = true
    }
  }, [centerId, depth, requestKey, reloads])

  // Shortest path, whenever both ends are set. Same keyed-answer shape as the
  // graph: with only one end picked there is simply no path to show, which is
  // a render-time fact rather than a state transition.
  const pathKey =
    pathEnds.from != null && pathEnds.to != null ? `${pathEnds.from}->${pathEnds.to}` : null
  const path = pathKey && pathAnswer?.key === pathKey ? pathAnswer.data : null

  useEffect(() => {
    if (!pathKey) return
    let cancelled = false
    const [from, to] = pathKey.split('->')
    client
      .get('/graph/path', { params: { from, to } })
      .then((r) => !cancelled && setPathAnswer({ key: pathKey, data: r.data }))
      .catch(
        () =>
          !cancelled &&
          setPathAnswer({ key: pathKey, data: { found: false, entity_ids: [], names: [] } }),
      )
    return () => {
      cancelled = true
    }
  }, [pathKey])

  const metrics = useMemo(
    () => new Map(analytics.metrics.map((m) => [m.entity_id, m])),
    [analytics],
  )

  // Communities ranked by size: only the largest few get their own colour,
  // because there is no shape channel left to fall back on for them.
  const topCommunities = useMemo(() => {
    const sizes = new Map()
    analytics.metrics.forEach((m) => sizes.set(m.community, (sizes.get(m.community) ?? 0) + 1))
    return [...sizes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([id]) => id)
  }, [analytics])

  // --- timeline (F6) -------------------------------------------------------
  // The span comes from the data rather than a hardcoded 2019-2025, so a
  // centred subgraph gets a slider that covers what it actually contains.
  const [minYear, maxYear] = useMemo(() => {
    const years = graph.edges
      .map((e) => Number(String(e.data.valid_from).slice(0, 4)))
      .filter(Number.isFinite)
    return years.length ? [Math.min(...years), Math.max(...years)] : FALLBACK_SPAN
  }, [graph])

  const clamp = (year) => Math.min(maxYear, Math.max(minYear, year))
  const fromYear = range ? clamp(range[0]) : minYear
  const toYear = range ? clamp(range[1]) : maxYear
  const settled = useDebounced(`${fromYear}|${toYear}`, DEBOUNCE_MS)

  // Filtering is client-side, per CLAUDE.md Phase 6: the server date filter
  // exists and is tested, but refetching on every drag would make the slider
  // crawl and the play animation stutter. Same overlap predicate as the
  // backend - an edge that began before the window and never ended is still
  // true inside it.
  const visible = useMemo(() => {
    const [start, end] = settled.split('|').map(Number)
    if (start <= minYear && end >= maxYear) return graph
    const lower = `${start}-01-01`
    const upper = `${end}-12-31`
    const edges = graph.edges.filter(
      (e) => e.data.valid_from <= upper && (!e.data.valid_to || e.data.valid_to >= lower),
    )
    const inWindow = new Set(edges.flatMap((e) => [e.data.source, e.data.target]))
    // A node with no edges at all carries no dates, so it should not blink in
    // and out as the window moves - it is simply always there.
    const everLinked = new Set(graph.edges.flatMap((e) => [e.data.source, e.data.target]))
    return {
      nodes: graph.nodes.filter(
        (n) => inWindow.has(n.data.id) || !everLinked.has(n.data.id),
      ),
      edges,
    }
  }, [graph, settled, minYear, maxYear])

  const recentre = useCallback((id) => {
    setCenterId(id)
    setSelectedId(id)
  }, [])

  const pathIds = path?.found ? path.entity_ids : []

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">Network</h2>
          <p className="mt-1 text-sm text-slate-400">
            Scoped to {user.agency_code}
            {user.role === 'admin'
              ? ' — as an admin you see every agency.'
              : ' and anything shared with it.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-400">
            {visible.nodes.length} nodes · {visible.edges.length} edges
            {analytics.community_count > 0 && ` · ${analytics.community_count} communities`}
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

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <SearchBar onPick={recentre} />
        <Control label="Depth">
          {[1, 2, 3].map((d) => (
            <Toggle key={d} on={depth === d} onClick={() => setDepth(d)} disabled={centerId == null}>
              {d}
            </Toggle>
          ))}
        </Control>
        <Control label="Colour by">
          <Toggle on={colourBy === 'type'} onClick={() => setColourBy('type')}>Type</Toggle>
          <Toggle on={colourBy === 'community'} onClick={() => setColourBy('community')}>
            Community
          </Toggle>
        </Control>
        <Control label="Size by">
          {SIZE_OPTIONS.map(([value, label]) => (
            <Toggle key={value} on={sizeBy === value} onClick={() => setSizeBy(value)}>
              {label}
            </Toggle>
          ))}
        </Control>
      </div>

      {error && (
        <ErrorStrip onRetry={() => setReloads((n) => n + 1)}>{error}</ErrorStrip>
      )}

      {(pathEnds.from != null || pathEnds.to != null) && (
        <PathStrip
          path={path}
          ends={pathEnds}
          onClear={() => setPathEnds({ from: null, to: null })}
        />
      )}

      <Timeline
        min={minYear}
        max={maxYear}
        value={[fromYear, toYear]}
        onChange={(next) =>
          setRange((prev) =>
            typeof next === 'function' ? next(prev ?? [minYear, maxYear]) : next,
          )
        }
        playing={playing}
        onPlayingChange={setPlaying}
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
        <div>
          {loading ? (
            <Notice tone="loading" title="Loading graph…" className="h-[32rem]">
              Building the network you are allowed to see.
            </Notice>
          ) : (
            <GraphView
              elements={visible}
              metrics={metrics}
              colourBy={colourBy}
              sizeBy={sizeBy}
              topCommunities={topCommunities}
              pathIds={pathIds}
              selectedId={selectedId}
              centerId={centerId}
              onSelect={setSelectedId}
              onRecentre={recentre}
            />
          )}
        </div>

        <div className="space-y-5">
          <TopConnectors
            items={analytics.top_connectors}
            onPick={recentre}
            wholePeriod={fromYear > minYear || toYear < maxYear}
          />
          {/* key remounts on a new selection, so the panel's initial state is
              derived rather than reset inside its effect. */}
          <EntityPanel
            key={selectedId ?? 'none'}
            entityId={selectedId}
            onRecentre={recentre}
            onSetPathEnd={(end, id) => setPathEnds((prev) => ({ ...prev, [end]: id }))}
          />
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Synthetic data only — 650 entities and 940 relationships generated by
        seed.py from a fixed seed. No real personal data is used anywhere.
      </p>
    </div>
  )
}

function Control({ label, children }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-sm text-slate-400">{label}</span>
      {children}
    </div>
  )
}

function Toggle({ on, onClick, disabled, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      disabled={disabled}
      className={`rounded px-2.5 py-1 text-sm disabled:opacity-40 ${
        on ? 'bg-sky-700 text-white' : 'border border-slate-600 text-slate-300 hover:bg-slate-700'
      }`}
    >
      {children}
    </button>
  )
}

/** Five highest-betweenness nodes in view, per PRD F5. */
function TopConnectors({ items, onPick, wholePeriod }) {
  if (!items.length) return null
  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <h3 className="text-xs font-medium uppercase tracking-wide text-slate-400">
        Top connectors
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Most shortest paths run through these. Removing one fragments the network most.
      </p>
      {wholePeriod && (
        <p className="mt-1 text-xs text-amber-300/80">
          Computed over the whole period, not the selected years — recomputing
          betweenness on every drag would stall the slider.
        </p>
      )}
      <ol className="mt-2 space-y-1">
        {items.map((item, index) => (
          <li key={item.entity_id} className="flex items-baseline gap-2 text-sm">
            <span className="w-4 shrink-0 text-right text-xs text-slate-500">{index + 1}</span>
            <button
              type="button"
              onClick={() => onPick(item.entity_id)}
              className="flex-1 truncate text-left text-slate-200 underline decoration-slate-600 underline-offset-2 hover:text-white"
            >
              {item.name}
            </button>
            <span className="shrink-0 text-xs text-slate-400">
              {formatScore(item.betweenness)}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

/** Fragmented views give real but tiny betweenness. Three decimals renders
 *  those as "0.000", which reads as broken rather than small. */
function formatScore(value) {
  if (value >= 0.001) return value.toFixed(3)
  return value.toPrecision(2)
}

function PathStrip({ path, ends, onClear }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-sm">
      <span className="font-medium text-amber-200">Shortest path</span>
      {ends.from == null || ends.to == null ? (
        <span className="text-slate-300">
          {ends.from == null ? 'Pick a start node.' : 'Now pick an end node.'}
        </span>
      ) : path == null ? (
        <span className="text-slate-400">Finding…</span>
      ) : path.found ? (
        <span className="text-slate-200">
          {path.names.join(' → ')}{' '}
          <span className="text-xs text-slate-400">
            ({path.length} {path.length === 1 ? 'hop' : 'hops'})
          </span>
        </span>
      ) : (
        <span className="text-slate-300">
          No route between them through the records you can see.
        </span>
      )}
      <button
        type="button"
        onClick={onClear}
        className="ml-auto rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white"
      >
        Clear
      </button>
    </div>
  )
}
