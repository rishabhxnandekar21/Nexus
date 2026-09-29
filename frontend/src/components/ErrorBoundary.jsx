import { Component } from 'react'

/**
 * Catches a render crash in the tree below it and shows something readable
 * instead of a blank page - the PRD Week 6 exit criterion is that no screen
 * shows a raw error.
 *
 * This is not hypothetical. Twice during W3 a single bad assumption in
 * Dashboard - reading `.nodes` off a body that was actually HTML, because a
 * stale dev proxy answered /api/* with index.html and axios reported a 200 -
 * blanked the entire application. React unmounts the whole tree on an
 * uncaught render error, so one component's mistake takes the nav, the router
 * and every other screen with it.
 *
 * A class component because that is the only way to implement
 * componentDidCatch; there is no hook equivalent.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Kept to the console rather than shipped anywhere: there is no error
    // reporting service in this project and inventing one is out of scope.
    console.error('Unhandled render error:', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
        <div className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h1 className="text-lg font-semibold text-white">Something broke on this screen</h1>
          <p className="mt-2 text-sm text-slate-400">
            The rest of the application is fine. Reloading usually clears it; if
            it comes back every time, the details below are what to report.
          </p>
          <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-400">
            {String(error?.message ?? error)}
          </pre>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
              className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded bg-sky-700 px-3 py-1.5 text-sm text-white hover:bg-sky-600"
            >
              Reload
            </button>
          </div>
        </div>
      </div>
    )
  }
}
