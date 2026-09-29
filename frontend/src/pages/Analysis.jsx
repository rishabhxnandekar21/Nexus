import AnalysisPanel from '../components/AnalysisPanel'

/** Hosts AnalysisPanel. F9's UI has no page assigned to it in PRD Section 11 -
 *  AnalysisPanel is listed as a component and Stats as a page - so it gets a
 *  screen of its own rather than being wedged into Stats, which is a different
 *  question, or into Dashboard, which is Krish's file. */
export default function Analysis() {
  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-xl font-semibold text-white">Network analysis</h2>
        <p className="mt-1 text-sm text-slate-400">
          Remove a node and see whether the network holds together, or rank the
          links an entity structurally ought to have. Both read existing records —
          neither forecasts anyone&apos;s behaviour.
        </p>
      </header>
      <AnalysisPanel />
    </div>
  )
}
