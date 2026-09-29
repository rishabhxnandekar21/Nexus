import { useCallback, useState } from 'react'

import client from '../api/client'
import Notice, { ErrorStrip } from '../components/Notice'

/**
 * Natural-language query and case brief. F10.
 *
 * The model only ever returns filters; the backend runs the query against the
 * caller's own agency scope. So the results here are already scoped - an
 * investigator cannot phrase their way into another agency's records.
 *
 * The four examples are the scripted demo queries, and they have committed
 * cached responses, so they answer with the network unplugged.
 */

const EXAMPLES = [
  'Which people are on record with the police since 2023?',
  'Find everyone named Rakesh',
  'Show me the telecom call records between 2020 and 2022',
  'Which vehicles are registered at a known address?',
]

function FilterChips({ filters }) {
  const shown = Object.entries(filters).filter(([, v]) =>
    Array.isArray(v) ? v.length > 0 : v !== null && v !== undefined && v !== '',
  )
  if (shown.length === 0) {
    return <span className="text-xs text-slate-500">no filters derived</span>
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map(([key, value]) => (
        <span
          key={key}
          className="rounded bg-slate-700 px-2 py-0.5 font-mono text-xs text-slate-300"
        >
          {key}: {Array.isArray(value) ? value.join(', ') : String(value)}
        </span>
      ))}
    </div>
  )
}

export default function NLQueryBox() {
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const [briefFor, setBriefFor] = useState(null)
  const [brief, setBrief] = useState(null)
  const [briefBusy, setBriefBusy] = useState(false)

  const ask = useCallback((text) => {
    const asked = (text ?? '').trim()
    if (!asked) return
    setAsking(true)
    setError(null)
    setBrief(null)
    setBriefFor(null)
    client
      .post('/query/nl', { question: asked })
      .then((response) => setResult(response.data))
      .catch((err) => setError(err.response?.data?.detail ?? 'The query failed.'))
      .finally(() => setAsking(false))
  }, [])

  const fetchBrief = useCallback((entityId) => {
    setBriefBusy(true)
    setBriefFor(entityId)
    setBrief(null)
    client
      .post('/query/brief', { entity_id: entityId })
      .then((response) => setBrief(response.data))
      .catch((err) => setError(err.response?.data?.detail ?? 'Could not write the brief.'))
      .finally(() => setBriefBusy(false))
  }, [])

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            ask(question)
          }}
          className="flex flex-wrap gap-2"
        >
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about the network in plain English…"
            className="min-w-0 flex-1 rounded border border-slate-600 bg-slate-900 px-3 py-1.5 text-sm text-white placeholder:text-slate-500 focus:border-sky-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={asking}
            className="rounded bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50"
          >
            {asking ? 'Asking…' : 'Ask'}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setQuestion(example)
                ask(example)
              }}
              disabled={asking}
              className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>

        <p className="mt-3 text-xs text-slate-500">
          The model returns filters only — it never writes a query and never touches
          the database. Results are scoped to your agency before you see them.
        </p>
      </section>

      {error && <ErrorStrip onRetry={() => ask(question)}>{error}</ErrorStrip>}

      {result && (
        <section className="space-y-3 rounded-lg border border-slate-700 bg-slate-800 p-4">
          <header className="flex flex-wrap items-baseline gap-2">
            <h3 className="font-medium text-white">Interpretation</h3>
            {result.from_cache && (
              <span
                className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300"
                title="No model was reached, so the committed demo cache answered. The counts below are still live from the database."
              >
                offline · from cache
              </span>
            )}
          </header>
          <p className="text-sm text-slate-300">{result.interpretation}</p>

          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Filters run</p>
            <div className="mt-1">
              <FilterChips filters={result.filters} />
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Answer</p>
            <p className="mt-1 text-sm text-slate-200">{result.answer}</p>
          </div>

          {result.entity_ids.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {result.entity_ids.length} matching record
                {result.entity_ids.length === 1 ? '' : 's'}
              </p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {result.entity_ids.slice(0, 40).map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => fetchBrief(id)}
                    title="Write a case brief for this record"
                    className={`rounded px-2 py-0.5 font-mono text-xs ${
                      briefFor === id
                        ? 'bg-sky-800 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    #{id}
                  </button>
                ))}
                {result.entity_ids.length > 40 && (
                  <span className="text-xs text-slate-500">
                    +{result.entity_ids.length - 40} more
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Click an id for a written case brief of that record&apos;s network.
              </p>
            </div>
          )}
        </section>
      )}

      {briefBusy && <Notice tone="loading" title="Writing the brief…" />}

      {brief && (
        <section className="rounded-lg border border-slate-700 bg-slate-800 p-4">
          <header className="flex flex-wrap items-baseline gap-2">
            <h3 className="font-medium text-white">Case brief — record #{brief.entity_id}</h3>
            {brief.from_cache && (
              <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                composed locally
              </span>
            )}
          </header>
          <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-200">
            {brief.brief}
          </p>
        </section>
      )}
    </div>
  )
}
