import AnalysisPanel from '../components/AnalysisPanel'
import NLQueryBox from '../components/NLQueryBox'

/** Hosts the two tools for interrogating the network: asking a question in plain
 *  English, and simulating what happens if a node is removed.
 *
 *  Neither has a page assigned in PRD Section 11 - NLQueryBox and AnalysisPanel
 *  are both listed as components. They share a screen rather than adding two nav
 *  entries, and rather than being wedged into Stats, which answers a different
 *  question, or Dashboard, which is Krish's file. */
export default function Analysis() {
  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <header>
          <h2 className="text-xl font-semibold text-white">Ask a question</h2>
          <p className="mt-1 text-sm text-slate-400">
            Plain English in, filters out, and the query runs here against the
            records your agency can see.
          </p>
        </header>
        <NLQueryBox />
      </section>

      <section className="space-y-4">
        <header>
          <h2 className="text-xl font-semibold text-white">Network impact</h2>
          <p className="mt-1 text-sm text-slate-400">
            Remove a node and see whether the network holds together, or rank the
            links an entity structurally ought to have. Both read existing records
            — neither forecasts anyone&apos;s behaviour.
          </p>
        </header>
        <AnalysisPanel />
      </section>
    </div>
  )
}
