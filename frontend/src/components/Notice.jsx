/**
 * The three non-content states - loading, empty, error - in one place.
 *
 * Each screen had grown its own markup for these, so the same condition
 * looked different depending on where you hit it. One component means an
 * empty graph and an empty panel read as the same kind of thing, and the
 * error styling cannot drift apart screen by screen.
 *
 * `tone` picks the treatment: a dashed border for "nothing here", a solid one
 * for "working on it", red for "this failed".
 */
export default function Notice({ tone = 'empty', title, children, action, className = '' }) {
  const frame = {
    empty: 'border-dashed border-slate-600 bg-slate-800/50',
    loading: 'border-slate-700 bg-slate-900',
    error: 'border-red-900/60 bg-red-950/40',
  }[tone]

  return (
    <div
      role={tone === 'error' ? 'alert' : undefined}
      aria-busy={tone === 'loading' || undefined}
      className={`flex flex-col items-center justify-center gap-2 rounded-lg border p-6 text-center ${frame} ${className}`}
    >
      {title && (
        <p className={`text-sm font-medium ${tone === 'error' ? 'text-red-200' : 'text-slate-300'}`}>
          {title}
        </p>
      )}
      {children && (
        <p className={`text-sm ${tone === 'error' ? 'text-red-300/80' : 'text-slate-400'}`}>
          {children}
        </p>
      )}
      {action}
    </div>
  )
}

/** Inline variant for a strip above content, rather than a whole panel. */
export function ErrorStrip({ children, onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-200"
    >
      <span>{children}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="ml-auto rounded border border-red-800 px-2 py-0.5 text-xs text-red-200 hover:bg-red-900/60"
        >
          Retry
        </button>
      )}
    </div>
  )
}
