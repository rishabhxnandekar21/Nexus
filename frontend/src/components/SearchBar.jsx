import { useEffect, useRef, useState } from 'react'

import client from '../api/client'

const TYPES = [
  '', 'person', 'vehicle', 'phone', 'location', 'organization', 'crime_event',
]

/** Entity search - F4. Selecting a result centres the graph on it. */
export default function SearchBar({ onPick }) {
  const [term, setTerm] = useState('')
  const [type, setType] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const boxRef = useRef(null)

  const active = Boolean(term.trim() || type)
  // Derived, not cleared in an effect: with no query there is nothing to show,
  // which is a render-time fact rather than a state transition.
  const visible = active ? results : []

  useEffect(() => {
    if (!active) return
    // Debounced: one request after typing stops, not one per keystroke.
    const timer = setTimeout(() => {
      let cancelled = false
      client
        .get('/entities', { params: { q: term.trim() || undefined, type: type || undefined, limit: 10 } })
        .then((response) => {
          if (cancelled) return
          setResults(Array.isArray(response.data) ? response.data : [])
          setError('')
          setOpen(true)
        })
        .catch(() => {
          if (!cancelled) setError('Search failed.')
        })
      return () => {
        cancelled = true
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [term, type, active])

  useEffect(() => {
    function onDocumentClick(event) {
      if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocumentClick)
    return () => document.removeEventListener('mousedown', onDocumentClick)
  }, [])

  function pick(entity) {
    onPick(entity.id)
    setOpen(false)
    setTerm(entity.name)
  }

  return (
    <div ref={boxRef} className="relative flex flex-wrap items-center gap-2">
      <div className="relative min-w-56 flex-1">
        <label htmlFor="entity-search" className="sr-only">
          Search entities
        </label>
        <input
          id="entity-search"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onFocus={() => visible.length && setOpen(true)}
          placeholder="Search people, phones, vehicles…"
          className="w-full rounded border border-slate-600 bg-slate-900 px-3 py-1.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-sky-500"
        />
        {open && (
          <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded border border-slate-600 bg-slate-800 shadow-lg">
            {visible.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-400">No matches.</li>
            ) : (
              visible.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() => pick(r)}
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
                  >
                    <span>{r.name}</span>
                    <span className="shrink-0 text-xs text-slate-400">
                      {r.entity_type} · {r.agency_code}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </div>

      <label htmlFor="entity-type" className="sr-only">
        Entity type
      </label>
      <select
        id="entity-type"
        value={type}
        onChange={(e) => setType(e.target.value)}
        className="rounded border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-white"
      >
        {TYPES.map((t) => (
          <option key={t || 'all'} value={t}>
            {t ? t.replace('_', ' ') : 'All types'}
          </option>
        ))}
      </select>

      {error && <span className="text-xs text-red-300">{error}</span>}
    </div>
  )
}
