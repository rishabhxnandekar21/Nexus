import { useEffect, useRef } from 'react'

/**
 * Dual-handle year range with a play button - F6.
 *
 * Years rather than dates: the seeded relationships span 2019-2025, the play
 * button steps in years per the PRD, and a day-level handle would give the
 * viewer 2,500 positions that all look the same. Two overlapping range inputs
 * rather than a slider library - no new dependency, and both handles stay
 * keyboard-reachable.
 *
 * This only reports the range. Filtering happens in Dashboard, in a useMemo
 * keyed on the debounced value, so dragging never refetches.
 */

const PLAY_INTERVAL_MS = 900

export default function Timeline({ min, max, value, onChange, playing, onPlayingChange }) {
  const [from, to] = value
  const tick = useRef(null)

  useEffect(() => {
    if (!playing) return undefined
    tick.current = setInterval(() => {
      onChange(([currentFrom, currentTo]) => {
        if (currentTo >= max) {
          onPlayingChange(false)
          return [currentFrom, currentTo]
        }
        return [currentFrom, currentTo + 1]
      })
    }, PLAY_INTERVAL_MS)
    return () => clearInterval(tick.current)
  }, [playing, max, onChange, onPlayingChange])

  function play() {
    if (playing) {
      onPlayingChange(false)
      return
    }
    // Restarting from the end would play nothing, so rewind first.
    if (to >= max) onChange([min, min])
    onPlayingChange(true)
  }

  const span = Math.max(1, max - min)
  const leftPct = ((from - min) / span) * 100
  const rightPct = ((to - min) / span) * 100

  return (
    <section
      className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3"
      aria-label="Time range"
    >
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={play}
          aria-pressed={playing}
          className="rounded bg-sky-700 px-3 py-1 text-sm text-white hover:bg-sky-600"
        >
          {playing ? '❚❚ Pause' : '▶ Play'}
        </button>
        <span className="text-sm text-slate-300">
          {from} – {to}
        </span>
        <button
          type="button"
          onClick={() => { onPlayingChange(false); onChange([min, max]) }}
          disabled={from === min && to === max}
          className="ml-auto rounded border border-slate-600 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-40"
        >
          Whole period
        </button>
      </div>

      <div className="relative mt-4 h-6">
        {/* Track, and the selected span on top of it. */}
        <div className="absolute inset-x-0 top-2.5 h-1 rounded bg-slate-600" />
        <div
          className="absolute top-2.5 h-1 rounded bg-sky-500"
          style={{ left: `${leftPct}%`, width: `${Math.max(0, rightPct - leftPct)}%` }}
        />
        {/* Both inputs span the full track; pointer-events are re-enabled on
            the thumbs only, so the lower one is still grabbable. */}
        <input
          type="range"
          min={min}
          max={max}
          value={from}
          aria-label="Range start year"
          onChange={(e) => {
            onPlayingChange(false)
            onChange([Math.min(Number(e.target.value), to), to])
          }}
          className="timeline-range absolute inset-x-0 top-0 h-6 w-full appearance-none bg-transparent"
        />
        <input
          type="range"
          min={min}
          max={max}
          value={to}
          aria-label="Range end year"
          onChange={(e) => {
            onPlayingChange(false)
            onChange([from, Math.max(Number(e.target.value), from)])
          }}
          className="timeline-range absolute inset-x-0 top-0 h-6 w-full appearance-none bg-transparent"
        />
      </div>

      <div className="mt-1 flex justify-between text-xs text-slate-500">
        {Array.from({ length: max - min + 1 }, (_, i) => min + i).map((year) => (
          <span key={year}>{year}</span>
        ))}
      </div>
    </section>
  )
}
