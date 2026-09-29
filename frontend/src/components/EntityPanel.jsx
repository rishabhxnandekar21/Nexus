import { useEffect, useState } from 'react'

import client from '../api/client'

/** Side panel for the selected node - attributes, relationships, neighbours.
 *  F3: "clicking a node opens a side panel with its attributes and its
 *  relationships". F4: the detail also names the source agency. */
export default function EntityPanel({ entityId, onRecentre }) {
  // Derived at mount rather than corrected inside the effect. Dashboard gives
  // this component key={entityId}, so a different selection remounts it and
  // the initial state is right again without a reset render.
  const [state, setState] = useState(() =>
    entityId == null
      ? { status: 'idle', data: null, error: '' }
      : { status: 'loading', data: null, error: '' },
  )

  useEffect(() => {
    if (entityId == null) return
    let cancelled = false
    client
      .get(`/entities/${entityId}`)
      .then((response) => {
        if (cancelled) return
        const data = response.data
        if (!data || !data.entity) {
          setState({ status: 'error', data: null, error: 'Unexpected response.' })
          return
        }
        setState({ status: 'ready', data, error: '' })
      })
      .catch((err) => {
        if (cancelled) return
        setState({
          status: 'error',
          data: null,
          error:
            err.response?.status === 404
              ? 'That record is not available to your agency.'
              : 'Could not load this entity.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [entityId])

  if (state.status === 'idle') {
    return (
      <aside className="rounded-lg border border-dashed border-slate-600 bg-slate-800/50 p-6">
        <p className="text-sm text-slate-400">Select a node to see its details.</p>
      </aside>
    )
  }

  if (state.status === 'loading') {
    return (
      <aside className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p className="text-sm text-slate-400">Loading…</p>
      </aside>
    )
  }

  if (state.status === 'error') {
    return (
      <aside className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p role="alert" className="text-sm text-red-300">
          {state.error}
        </p>
      </aside>
    )
  }

  const { entity, relationships, neighbours } = state.data
  const attributes = Object.entries(entity.attributes ?? {}).filter(
    ([key]) => !key.startsWith('_'),
  )

  return (
    <aside className="space-y-5 rounded-lg border border-slate-700 bg-slate-800 p-5">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {entity.entity_type.replace('_', ' ')}
        </p>
        <h3 className="mt-0.5 text-lg font-semibold text-white">{entity.name}</h3>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="rounded bg-sky-900 px-2 py-0.5 text-xs text-sky-200">
            {entity.agency_code}
          </span>
          {entity.is_shared && (
            <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
              shared
            </span>
          )}
          {entity.source_ref && (
            <span className="text-xs text-slate-500">{entity.source_ref}</span>
          )}
        </div>
      </header>

      {attributes.length > 0 && (
        <section>
          <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
            Attributes
          </h4>
          <dl className="space-y-1 text-sm">
            {attributes.map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <dt className="min-w-24 text-slate-400">{key}</dt>
                <dd className="text-slate-200">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section>
        <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
          Relationships ({relationships.length})
        </h4>
        {relationships.length === 0 ? (
          <p className="text-sm text-slate-500">
            None visible to your agency.
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {relationships.map((rel) => {
              const outgoing = rel.src_entity_id === entity.id
              const otherId = outgoing ? rel.dst_entity_id : rel.src_entity_id
              const otherName = outgoing ? rel.dst_name : rel.src_name
              return (
                <li key={rel.id} className="text-slate-300">
                  <span className="text-slate-400">
                    {outgoing ? '→' : '←'} {rel.rel_type.replace(/_/g, ' ')}
                  </span>{' '}
                  <button
                    type="button"
                    onClick={() => onRecentre(otherId)}
                    className="underline decoration-slate-600 underline-offset-2 hover:text-white"
                  >
                    {otherName}
                  </button>
                  <span className="ml-1 text-xs text-slate-500">
                    {rel.valid_from}
                    {rel.valid_to ? ` → ${rel.valid_to}` : ' → present'}
                    {rel.source_case ? ` · ${rel.source_case}` : ''}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {neighbours.length > 0 && (
        <section>
          <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
            Neighbours ({neighbours.length})
          </h4>
          <ul className="flex flex-wrap gap-1.5">
            {neighbours.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => onRecentre(n.id)}
                  className="rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white"
                >
                  {n.name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  )
}
