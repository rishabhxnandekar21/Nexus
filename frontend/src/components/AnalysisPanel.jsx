import { useCallback, useState } from 'react'

import client from '../api/client'
import Notice, { ErrorStrip } from '../components/Notice'

/**
 * Network impact simulation and link prediction. F9.
 *
 * The wording here is deliberate and should not be loosened. This removes nodes
 * from records that already exist and measures how the structure changes, and it
 * ranks pairs that are structurally likely to be connected but are not recorded
 * as connected. It is not crime prediction and must never be labelled as such -
 * PRD Section 4, N1.
 */

function Stat({ label, before, after }) {
  const delta = after - before
  const tone =
    delta === 0 ? 'text-slate-500' : delta > 0 ? 'text-amber-300' : 'text-sky-300'
  return (
    <div className="rounded border border-slate-700 bg-slate-900 px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 flex items-baseline gap-2">
        <span className="text-slate-400 line-through decoration-slate-600">{before}</span>
        <span className="text-slate-500">→</span>
        <span className="text-lg font-semibold text-white">{after}</span>
        {delta !== 0 && (
          <span className={`text-xs ${tone}`}>
            {delta > 0 ? '+' : ''}
            {delta}
          </span>
        )}
      </p>
    </div>
  )
}

export default function AnalysisPanel() {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)

  const [impact, setImpact] = useState(null)
  const [predictions, setPredictions] = useState(null)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)

  const search = useCallback(
    (event) => {
      event.preventDefault()
      if (!query.trim()) return
      setSearching(true)
      setError(null)
      client
        .get('/entities', { params: { q: query.trim(), limit: 8 } })
        .then((response) => setMatches(response.data))
        .catch((err) => setError(err.response?.data?.detail ?? 'Search failed.'))
        .finally(() => setSearching(false))
    },
    [query],
  )

  const choose = useCallback((entity) => {
    setSelected(entity)
    setMatches([])
    setImpact(null)
    setPredictions(null)
    setError(null)
  }, [])

  const simulate = useCallback(() => {
    if (!selected) return
    setBusy('impact')
    setError(null)
    client
      .post('/graph/whatif', { remove_entity_ids: [selected.id] })
      .then((response) => setImpact(response.data))
      .catch((err) =>
        setError(
          err.response?.data?.detail ??
            'Simulation failed. The /graph/whatif route still returns stub data — see the REQUEST in PROGRESS.md.',
        ),
      )
      .finally(() => setBusy(null))
  }, [selected])

  const predict = useCallback(() => {
    if (!selected) return
    setBusy('predict')
    setError(null)
    client
      .get('/graph/predict', { params: { entity_id: selected.id, k: 5 } })
      .then((response) => setPredictions(response.data.predictions))
      .catch((err) =>
        setError(
          err.response?.data?.detail ??
            'Prediction failed. The /graph/predict route still returns stub data — see the REQUEST in PROGRESS.md.',
        ),
      )
      .finally(() => setBusy(null))
  }, [selected])

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <form onSubmit={search} className="flex flex-wrap gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Find a person, phone, vehicle…"
            className="min-w-0 flex-1 rounded border border-slate-600 bg-slate-900 px-3 py-1.5 text-sm text-white placeholder:text-slate-500 focus:border-sky-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={searching}
            className="rounded bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50"
          >
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>

        {matches.length > 0 && (
          <ul className="mt-3 divide-y divide-slate-700 rounded border border-slate-700">
            {matches.map((entity) => (
              <li key={entity.id}>
                <button
                  type="button"
                  onClick={() => choose(entity)}
                  className="flex w-full flex-wrap items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-700/50"
                >
                  <span className="text-white">{entity.name}</span>
                  <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300">
                    {entity.entity_type}
                  </span>
                  <span className="rounded bg-sky-900 px-1.5 py-0.5 text-xs text-sky-200">
                    {entity.agency_code}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {selected && (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded border border-slate-700 bg-slate-900 px-3 py-2">
            <span className="text-sm text-slate-400">Selected</span>
            <span className="text-sm font-medium text-white">{selected.name}</span>
            <span className="text-xs text-slate-500">id {selected.id}</span>
            <div className="ml-auto flex flex-wrap gap-2">
              <button
                type="button"
                onClick={simulate}
                disabled={busy !== null}
                className="rounded bg-amber-800 px-3 py-1.5 text-sm text-white hover:bg-amber-700 disabled:opacity-50"
              >
                {busy === 'impact' ? 'Simulating…' : 'Simulate removal'}
              </button>
              <button
                type="button"
                onClick={predict}
                disabled={busy !== null}
                className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              >
                {busy === 'predict' ? 'Ranking…' : 'Suggest missing links'}
              </button>
            </div>
          </div>
        )}
      </section>

      {error && <ErrorStrip>{error}</ErrorStrip>}

      {impact && (
        <section className="space-y-3 rounded-lg border border-slate-700 bg-slate-800 p-4">
          <header>
            <h3 className="font-medium text-white">Network impact simulation</h3>
            <p className="mt-1 text-xs text-slate-400">
              Structure of the network you can see, with{' '}
              <span className="text-slate-300">{selected?.name}</span> removed. This
              measures existing records — it is not a forecast about any person.
            </p>
          </header>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Nodes" before={impact.before.node_count} after={impact.after.node_count} />
            <Stat label="Edges" before={impact.before.edge_count} after={impact.after.edge_count} />
            <Stat
              label="Separate components"
              before={impact.before.component_count}
              after={impact.after.component_count}
            />
            <Stat
              label="Largest component"
              before={impact.before.largest_component_size}
              after={impact.after.largest_component_size}
            />
          </div>

          {impact.after.component_count > impact.before.component_count ? (
            <p className="rounded border border-amber-900/60 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
              Removing this node <span className="font-medium">broke the network apart</span>
              . The largest group fell from {impact.before.largest_component_size} to{' '}
              {impact.after.largest_component_size} — it was holding the halves
              together.
            </p>
          ) : (
            <p className="text-sm text-slate-400">
              The network stayed in one piece. This node was not the only route
              between its neighbours.
            </p>
          )}

          <div>
            <h4 className="text-sm font-medium text-slate-300">
              Who has to be routed through now
            </h4>
            {impact.top_risers.length === 0 ? (
              <p className="mt-1 text-sm text-slate-500">
                No one gained importance — nothing was flowing through this node.
              </p>
            ) : (
              <ul className="mt-2 space-y-1">
                {impact.top_risers.map((riser) => (
                  <li
                    key={riser.entity_id}
                    className="flex flex-wrap items-baseline gap-2 rounded border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
                  >
                    <span className="text-white">{riser.name}</span>
                    <span className="ml-auto font-mono text-xs text-slate-500">
                      {riser.before.toFixed(6)} → {riser.after.toFixed(6)}
                    </span>
                    <span className="font-mono text-xs text-amber-300">
                      +{riser.delta.toFixed(6)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {predictions && (
        <section className="space-y-3 rounded-lg border border-slate-700 bg-slate-800 p-4">
          <header>
            <h3 className="font-medium text-white">Likely missing links</h3>
            <p className="mt-1 text-xs text-slate-400">
              Pairs that are structurally likely to be connected but have no record
              of a connection. Adamic-Adar weights a shared contact by how few
              connections it has, so a quiet contact in common counts for more than
              a hub everyone touches. Shown as dashed lines because{' '}
              <span className="text-slate-300">these are not evidence</span> — they
              are a suggestion of where to look.
            </p>
          </header>

          {predictions.length === 0 ? (
            <Notice tone="empty" title="Nothing to suggest">
              This entity shares no contacts with anyone it is not already linked to.
            </Notice>
          ) : (
            <ul className="space-y-2">
              {predictions.map((p) => (
                <li
                  key={p.target_entity_id}
                  className="rounded border border-dashed border-slate-600 bg-slate-900 px-3 py-2"
                >
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="text-sm text-white">{p.target_name}</span>
                    <span className="text-xs text-slate-500">id {p.target_entity_id}</span>
                    <span className="ml-auto font-mono text-xs text-slate-400">
                      Adamic-Adar {p.adamic_adar.toFixed(4)}
                    </span>
                    <span className="font-mono text-xs text-slate-500">
                      Jaccard {p.jaccard.toFixed(4)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    {p.shared_neighbour_names.length} in common:{' '}
                    {p.shared_neighbour_names.join(', ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {!selected && (
        <Notice tone="empty" title="Pick an entity to analyse">
          Search above, then simulate removing it to see whether the network holds
          together, or ask for links it probably has but no record shows.
        </Notice>
      )}
    </div>
  )
}
