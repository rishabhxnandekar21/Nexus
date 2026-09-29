import { useCallback, useEffect, useState } from 'react'

import client from '../api/client'
import Notice, { ErrorStrip } from '../components/Notice'
import { useAuth } from '../context/AuthContext'

const TABS = [
  { key: 'pending', label: 'Pending' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'rejected', label: 'Rejected' },
]

/** Score band. Deliberately not a pass/fail: the whole point is that a person
 *  decides, so the colour is a hint about strength, not a verdict. */
function scoreTone(score) {
  if (score >= 0.8) return 'bg-amber-900/60 text-amber-100'
  if (score >= 0.7) return 'bg-amber-950/60 text-amber-200/90'
  return 'bg-slate-700 text-slate-300'
}

function RecordCard({ entity, label }) {
  const attrs = entity.attributes ?? {}
  const rows = [
    ['Agency', entity.agency_code],
    ['Source ref', entity.source_ref ?? '—'],
    ['Date of birth', attrs.dob ?? '—'],
    ['Alias', attrs.alias ?? '—'],
    ['Address', attrs.address ?? '—'],
    ['City', attrs.city ?? '—'],
  ]
  return (
    <div className="flex-1 rounded border border-slate-700 bg-slate-900 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">
        {label} · id {entity.id}
      </p>
      <p className="mt-1 font-medium text-white">{entity.name}</p>
      <dl className="mt-2 space-y-1 text-sm">
        {rows.map(([key, value]) => (
          <div key={key} className="flex gap-2">
            <dt className="w-28 shrink-0 text-slate-500">{key}</dt>
            <dd className="break-words text-slate-300">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function Candidate({ candidate, onAction, busy }) {
  const [confirming, setConfirming] = useState(false)
  const pending = candidate.status === 'pending'

  return (
    <article className="space-y-3 rounded-lg border border-slate-700 bg-slate-800 p-4">
      <header className="flex flex-wrap items-center gap-3">
        <span className={`rounded px-2 py-1 text-sm font-semibold ${scoreTone(candidate.score)}`}>
          {(candidate.score * 100).toFixed(1)}% match
        </span>
        <p className="text-sm text-slate-300">{candidate.reason}</p>
        {!pending && (
          <span className="ml-auto rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
            {candidate.status}
          </span>
        )}
      </header>

      <div className="flex flex-col gap-3 sm:flex-row">
        <RecordCard entity={candidate.entity_a} label="Record A — kept" />
        <RecordCard entity={candidate.entity_b} label="Record B — merged away" />
      </div>

      <div className="overflow-x-auto rounded border border-slate-700">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-1.5">Signal</th>
              <th className="px-3 py-1.5">Weight</th>
              <th className="px-3 py-1.5">Contributed</th>
              <th className="px-3 py-1.5">Why</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {candidate.features.map((f) => (
              <tr key={f.name} className={f.matched ? '' : 'text-slate-500'}>
                <td className="px-3 py-1.5">
                  <span className={f.matched ? 'text-emerald-300' : 'text-slate-500'}>
                    {f.matched ? '✓' : '·'}
                  </span>{' '}
                  {f.name.replace(/_/g, ' ')}
                </td>
                <td className="px-3 py-1.5 font-mono text-xs">{f.weight.toFixed(2)}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{f.contribution.toFixed(4)}</td>
                <td className="px-3 py-1.5 text-slate-400">{f.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pending && !confirming && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => setConfirming(true)}
            className="rounded bg-emerald-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            Confirm — same person
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onAction(candidate.id, 'reject')}
            className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
          >
            Reject — different people
          </button>
        </div>
      )}

      {pending && confirming && (
        // A merge deletes a record and rewires its relationships. It is the one
        // irreversible action in the app, so it asks twice - and the second ask
        // spells out exactly what happens.
        <div className="rounded border border-amber-900/60 bg-amber-950/30 p-3">
          <p className="text-sm text-amber-100">
            Merge <span className="font-medium">{candidate.entity_b.name}</span> into{' '}
            <span className="font-medium">{candidate.entity_a.name}</span>?
          </p>
          <p className="mt-1 text-xs text-amber-200/70">
            Record B&apos;s relationships move onto record A and record B is removed
            from the graph. This cannot be undone. The merge is written to the audit
            log naming both ids.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => onAction(candidate.id, 'confirm')}
              className="rounded bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
            >
              {busy ? 'Merging…' : 'Yes, merge them'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirming(false)}
              className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </article>
  )
}

export default function Resolution() {
  const { user } = useAuth()
  const [tab, setTab] = useState('pending')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [forbidden, setForbidden] = useState(false)
  const [attempt, setAttempt] = useState(0)

  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [actionNote, setActionNote] = useState(null)

  useEffect(() => {
    client
      .get('/resolution/candidates', { params: { status: tab } })
      .then((response) => {
        setItems(response.data)
        setError(null)
        setForbidden(false)
      })
      .catch((err) => {
        if (err.response?.status === 403) setForbidden(true)
        else setError(err.response?.data?.detail ?? 'Could not load the queue.')
      })
      .finally(() => setLoading(false))
  }, [tab, attempt])

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    setAttempt((n) => n + 1)
  }, [])

  const runScoring = useCallback(() => {
    setRunning(true)
    setRunResult(null)
    setError(null)
    client
      .post('/resolution/run')
      .then((response) => {
        setRunResult(response.data)
        setAttempt((n) => n + 1)
      })
      .catch((err) => setError(err.response?.data?.detail ?? 'Scoring failed.'))
      .finally(() => setRunning(false))
  }, [])

  const act = useCallback((id, what) => {
    setBusyId(id)
    setActionNote(null)
    client
      .post(`/resolution/${id}/${what}`)
      .then((response) => {
        const data = response.data
        setActionNote(
          what === 'confirm'
            ? `Merged into record ${data.merged_into_id}. ${data.relationships_rewired} relationship${
                data.relationships_rewired === 1 ? '' : 's'
              } rewired.`
            : `Pair ${data.candidate_id} rejected. It will not be proposed again.`,
        )
        setAttempt((n) => n + 1)
      })
      .catch((err) => setError(err.response?.data?.detail ?? `Could not ${what} the pair.`))
      .finally(() => setBusyId(null))
  }, [])

  if (forbidden) {
    return (
      <div className="space-y-4">
        <Header />
        <Notice tone="empty" title="Admin only">
          The resolution queue is a supervisor view. You are signed in as{' '}
          <span className="text-slate-300">{user.role}</span> for{' '}
          <span className="text-slate-300">{user.agency_code}</span>.
        </Notice>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Header />

      <section className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-700 bg-slate-800 p-4">
        <button
          type="button"
          onClick={runScoring}
          disabled={running}
          className="rounded bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50"
        >
          {running ? 'Scoring…' : 'Run scoring'}
        </button>
        {runResult && (
          <span className="text-sm text-slate-300">
            Scored {runResult.pairs_scored} pairs, queued{' '}
            <span className="font-medium text-white">{runResult.candidates_created}</span>{' '}
            above the threshold.
          </span>
        )}
        <div className="ml-auto flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => {
                setTab(t.key)
                setLoading(true)
              }}
              className={`rounded px-3 py-1.5 text-sm ${
                tab === t.key
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </section>

      {actionNote && (
        <p className="rounded border border-emerald-900/60 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200">
          {actionNote}
        </p>
      )}
      {error && <ErrorStrip onRetry={reload}>{error}</ErrorStrip>}

      {loading ? (
        <Notice tone="loading" title="Loading the queue…" />
      ) : items.length === 0 ? (
        <Notice tone="empty" title={`No ${tab} candidates`}>
          {tab === 'pending'
            ? 'Run scoring to look for duplicate identities across the agencies.'
            : `Nothing has been ${tab} yet.`}
        </Notice>
      ) : (
        <div className="space-y-4">
          {items.map((candidate) => (
            <Candidate
              key={candidate.id}
              candidate={candidate}
              busy={busyId === candidate.id}
              onAction={act}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function Header() {
  return (
    <header>
      <h2 className="text-xl font-semibold text-white">Resolution queue</h2>
      <p className="mt-1 text-sm text-slate-400">
        Records that may refer to the same person, each with the signals that
        produced its score. <span className="text-slate-300">Nothing merges on its
        own</span> — a person confirms every one.
      </p>
    </header>
  )
}
