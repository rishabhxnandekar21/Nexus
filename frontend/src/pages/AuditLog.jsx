import { useCallback, useEffect, useState } from 'react'

import client from '../api/client'
import Notice, { ErrorStrip } from '../components/Notice'
import { useAuth } from '../context/AuthContext'

const LIMIT = 100

/** First 10 and last 6 of a 64-char hash. Enough to compare two by eye during
 *  the demo without the table turning into a wall of hex. */
function shortHash(value) {
  if (!value) return '—'
  return `${value.slice(0, 10)}…${value.slice(-6)}`
}

function formatTime(iso) {
  // Stored naive UTC - see models.py. Label it rather than silently rendering it
  // as local time, which would make the chain look out of order next to a
  // timestamp from anywhere else.
  return `${iso.replace('T', ' ').slice(0, 19)}Z`
}

export default function AuditLog() {
  const { user } = useAuth()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [forbidden, setForbidden] = useState(false)
  // Bumped to re-run the fetch. Same shape as AuthContext: the effect owns the
  // request and every setState sits in a .then/.catch/.finally, so nothing is
  // set synchronously on the way into the effect.
  const [attempt, setAttempt] = useState(0)

  const [result, setResult] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [verifyError, setVerifyError] = useState(null)

  useEffect(() => {
    client
      .get('/audit', { params: { limit: LIMIT } })
      .then((response) => {
        setEntries(response.data)
        setError(null)
        setForbidden(false)
      })
      .catch((err) => {
        // 403 is not a failure, it is the access rule working. The audit log is
        // an admin view per PRD Section 5, so say that instead of showing a
        // generic error to an investigator who did nothing wrong.
        if (err.response?.status === 403) setForbidden(true)
        else setError(err.response?.data?.detail ?? 'Could not load the audit log.')
      })
      .finally(() => setLoading(false))
  }, [attempt])

  /** Re-fetch the table. Called from events, never from an effect. */
  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    setAttempt((n) => n + 1)
  }, [])

  const runVerify = useCallback(() => {
    setVerifying(true)
    setVerifyError(null)
    client
      .get('/audit/verify')
      .then((response) => {
        setResult(response.data)
        // Verifying appends a row of its own, so the table is now one behind.
        setAttempt((n) => n + 1)
      })
      .catch((err) => {
        setVerifyError(err.response?.data?.detail ?? 'Verification request failed.')
      })
      .finally(() => setVerifying(false))
  }, [])

  if (forbidden) {
    return (
      <div className="space-y-4">
        <Header />
        <Notice tone="empty" title="Admin only">
          The audit log is a supervisor view. You are signed in as{' '}
          <span className="text-slate-300">{user.role}</span> for{' '}
          <span className="text-slate-300">{user.agency_code}</span>. Sign in as an
          admin to read the chain.
        </Notice>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Header />

      <section className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={runVerify}
            disabled={verifying}
            className="rounded bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50"
          >
            {verifying ? 'Verifying…' : 'Verify chain'}
          </button>

          {result && (
            <span
              className={`rounded px-2 py-1 text-sm font-medium ${
                result.valid
                  ? 'bg-emerald-900/60 text-emerald-200'
                  : 'bg-red-900/60 text-red-200'
              }`}
            >
              {result.valid
                ? `Chain valid — ${result.checked} rows recomputed`
                : `Chain BROKEN at seq ${result.broken_at_seq} — ${result.checked} rows checked`}
            </span>
          )}

          <p className="ml-auto text-xs text-slate-500">
            Recomputes every SHA-256 in seq order and reports the first mismatch.
          </p>
        </div>

        {verifyError && (
          <div className="mt-3">
            <ErrorStrip onRetry={runVerify}>{verifyError}</ErrorStrip>
          </div>
        )}

        {result && !result.valid && (
          <p className="mt-3 rounded border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            Row <span className="font-mono">{result.broken_at_seq}</span> does not
            match its recomputed hash, or its{' '}
            <span className="font-mono">prev_hash</span> no longer points at the row
            before it. Everything from that row onward is untrustworthy. It is
            highlighted below if it is on this page.
          </p>
        )}
      </section>

      {error && <ErrorStrip onRetry={reload}>{error}</ErrorStrip>}

      {loading ? (
        <Notice tone="loading" title="Loading the chain…" />
      ) : entries.length === 0 ? (
        <Notice tone="empty" title="No audit rows yet">
          Nothing has been accessed. Open the dashboard and the first rows appear
          here.
        </Notice>
      ) : (
        <section className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="bg-slate-800 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-3 py-2">Seq</th>
                <th className="px-3 py-2">Time (UTC)</th>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Resource</th>
                <th className="px-3 py-2">prev_hash</th>
                <th className="px-3 py-2">hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900">
              {entries.map((row) => {
                const broken =
                  result && !result.valid && row.seq === result.broken_at_seq
                return (
                  <tr
                    key={row.id}
                    className={broken ? 'bg-red-950/50' : 'hover:bg-slate-800/50'}
                  >
                    <td className="px-3 py-2 font-mono text-slate-300">
                      {row.seq}
                      {broken && (
                        <span className="ml-2 rounded bg-red-900/70 px-1.5 py-0.5 text-xs text-red-200">
                          broken
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-400">
                      {formatTime(row.timestamp)}
                    </td>
                    <td className="px-3 py-2 text-slate-300">{row.username ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-300">{row.action}</td>
                    <td className="px-3 py-2 text-slate-400">
                      {row.resource_type ?? '—'}
                      {row.resource_id ? ` #${row.resource_id}` : ''}
                    </td>
                    <td
                      className="px-3 py-2 font-mono text-xs text-slate-500"
                      title={row.prev_hash}
                    >
                      {shortHash(row.prev_hash)}
                    </td>
                    <td
                      className="px-3 py-2 font-mono text-xs text-slate-400"
                      title={row.hash}
                    >
                      {shortHash(row.hash)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}

      {entries.length > 0 && (
        <p className="text-xs text-slate-500">
          Showing the {entries.length} most recent rows, newest first. Each
          row&apos;s <span className="font-mono">prev_hash</span> is the previous
          row&apos;s <span className="font-mono">hash</span> — that is the chain.
          Hover a hash to see it in full.
        </p>
      )}
    </div>
  )
}

function Header() {
  return (
    <header>
      <h2 className="text-xl font-semibold text-white">Audit log</h2>
      <p className="mt-1 text-sm text-slate-400">
        Append-only and hash-chained. Every row commits to the one before it, so
        editing any field anywhere is detectable — and the exact row is named.
      </p>
    </header>
  )
}
