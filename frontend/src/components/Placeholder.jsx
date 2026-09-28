/** Stands in for a page that is not written yet.
 *
 *  Resolution.jsx, AuditLog.jsx and Stats.jsx are Rishabh's files in the
 *  ownership table, so W1-8 does not create them - their routes point here
 *  instead. When he writes a page, he adds it under src/pages/ and swaps the
 *  one line in App.jsx that names this component. */
export default function Placeholder({ title, owner, week, description }) {
  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-xl font-semibold text-white">{title}</h2>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </header>
      <div className="rounded-lg border border-dashed border-slate-600 bg-slate-800/50 p-8 text-center">
        <p className="text-sm text-slate-400">
          Not built yet — {owner}, {week}.
        </p>
      </div>
    </div>
  )
}
