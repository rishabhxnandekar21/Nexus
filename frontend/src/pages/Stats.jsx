import { useCallback, useEffect, useState } from 'react'

import client from '../api/client'
import Notice, { ErrorStrip } from '../components/Notice'

/** F11. Counts by entity type, relationships by agency, a year histogram and the
 *  audit-chain status. Everything here is scoped to the caller, so the numbers
 *  change with the login - which makes the agency-scoping point a third time,
 *  before any graph is drawn. */

const TYPE_COLOURS = {
  person: 'bg-sky-600',
  phone: 'bg-emerald-600',
  vehicle: 'bg-amber-600',
  location: 'bg-violet-600',
  crime_event: 'bg-rose-600',
  organization: 'bg-teal-600',
}

function Tile({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

/** Horizontal bars. Deliberately CSS rather than a charting library - the PRD
 *  rules out dependencies that are not in CLAUDE.md Section 3, and four bars do
 *  not justify one. */
function Bars({ rows, labelOf, valueOf, colourOf }) {
  const max = Math.max(...rows.map(valueOf), 1)
  return (
    <ul className="space-y-1.5">
      {rows.map((row) => (
        <li key={labelOf(row)} className="flex items-center gap-2 text-sm">
          <span className="w-28 shrink-0 truncate text-slate-400" title={labelOf(row)}>
            {labelOf(row)}
          </span>
          <span className="h-4 min-w-0 flex-1 overflow-hidden rounded bg-slate-900">
            <span
              className={`block h-full rounded ${colourOf ? colourOf(row) : 'bg-sky-600'}`}
              style={{ width: `${Math.max((valueOf(row) / max) * 100, 2)}%` }}
            />
          </span>
          <span className="w-12 shrink-0 text-right font-mono text-xs text-slate-300">
            {valueOf(row)}
          </span>
        </li>
      ))}
    </ul>
  )
}

export default function Stats() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    client
      .get('/stats')
      .then((response) => {
        setData(response.data)
        setError(null)
      })
      .catch((err) => setError(err.response?.data?.detail ?? 'Could not load the stats.'))
      .finally(() => setLoading(false))
  }, [attempt])

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    setAttempt((n) => n + 1)
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <Header />
        <Notice tone="loading" title="Counting…" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Header />
        <ErrorStrip onRetry={reload}>{error ?? 'No data returned.'}</ErrorStrip>
      </div>
    )
  }

  const chain = data.chain

  return (
    <div className="space-y-6">
      <Header scope={data.scope} />

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Entities" value={data.entities} hint="records you can see" />
        <Tile label="Relationships" value={data.relationships} hint="links you can see" />
        <Tile label="Agencies" value={data.agencies} hint="sources in the system" />
        <Tile
          label="Audit rows"
          value={chain.rows}
          hint={chain.admin_only ? 'chain status is admin only' : 'hash-chained'}
        />
      </section>

      <section
        className={`rounded-lg border px-4 py-3 ${
          chain.admin_only
            ? 'border-slate-700 bg-slate-800'
            : chain.valid
              ? 'border-emerald-900/60 bg-emerald-950/30'
              : 'border-red-900/60 bg-red-950/40'
        }`}
      >
        <p className="text-xs uppercase tracking-wide text-slate-500">Audit chain</p>
        {chain.admin_only ? (
          <p className="mt-1 text-sm text-slate-400">
            {chain.rows} rows recorded. Verification is an admin action, so the chain
            has not been checked for you.
          </p>
        ) : chain.valid ? (
          <p className="mt-1 text-sm text-emerald-200">
            Intact — all {chain.checked} rows recomputed and matched. No row has been
            altered since it was written.
          </p>
        ) : (
          <p className="mt-1 text-sm text-red-200">
            BROKEN at seq {chain.broken_at_seq}, after checking {chain.checked} rows.
            Everything from that row onward is untrustworthy.
          </p>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h3 className="mb-2 font-medium text-white">Records by type</h3>
          {data.by_entity_type.length === 0 ? (
            <Notice tone="empty" title="Nothing to count" />
          ) : (
            <Bars
              rows={data.by_entity_type}
              labelOf={(r) => r.entity_type.replace(/_/g, ' ')}
              valueOf={(r) => r.count}
              colourOf={(r) => TYPE_COLOURS[r.entity_type] ?? 'bg-slate-600'}
            />
          )}
        </section>

        <section>
          <h3 className="mb-2 font-medium text-white">Relationships by source agency</h3>
          {data.relationships_by_agency.length === 0 ? (
            <Notice tone="empty" title="No relationships in scope">
              Your agency has no relationship records visible here.
            </Notice>
          ) : (
            <Bars
              rows={data.relationships_by_agency}
              labelOf={(r) => r.agency_code}
              valueOf={(r) => r.count}
            />
          )}
        </section>
      </div>

      <section>
        <h3 className="mb-2 font-medium text-white">When the links were made</h3>
        {data.relationships_by_year.length === 0 ? (
          <Notice tone="empty" title="No dated links in scope" />
        ) : (
          <Bars
            rows={data.relationships_by_year}
            labelOf={(r) => String(r.year)}
            valueOf={(r) => r.count}
          />
        )}
        <p className="mt-2 text-xs text-slate-500">
          By the year a relationship began. The timeline on the dashboard replays
          this.
        </p>
      </section>

      {!chain.admin_only && (
        <section className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Resolution queue
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {data.resolution_pending === 0
              ? 'Nothing waiting for review.'
              : `${data.resolution_pending} possible duplicate${
                  data.resolution_pending === 1 ? '' : 's'
                } waiting for a human decision.`}
          </p>
        </section>
      )}

      <p className="text-xs text-slate-500">
        All data is synthetic, generated by <span className="font-mono">seed.py</span>{' '}
        with a fixed random seed. No real personal data is used anywhere in this
        system.
      </p>
    </div>
  )
}

function Header({ scope }) {
  return (
    <header>
      <h2 className="text-xl font-semibold text-white">Stats</h2>
      <p className="mt-1 text-sm text-slate-400">
        What is in the system, as you are entitled to see it
        {scope ? (
          <>
            {' '}
            — scope:{' '}
            <span className="rounded bg-sky-900 px-1.5 py-0.5 text-xs text-sky-200">
              {scope}
            </span>
          </>
        ) : null}
        .
      </p>
    </header>
  )
}
