import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import ErrorBoundary from './components/ErrorBoundary'
import Notice from './components/Notice'
import Placeholder from './components/Placeholder'
import { useAuth } from './context/AuthContext'
import AuditLog from './pages/AuditLog'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Resolution from './pages/Resolution'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/resolution', label: 'Resolution' },
  { to: '/audit', label: 'Audit log' },
  { to: '/stats', label: 'Stats' },
]

function RequireAuth({ children }) {
  const { user, loading, unreachable, retry } = useAuth()
  const location = useLocation()

  // Wait for /auth/me before deciding. Without this a refresh on any page
  // flashes the login screen even though the token is perfectly good.
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
        <Notice tone="loading" title="Signing you in…" className="w-full max-w-sm" />
      </div>
    )
  }
  // Server down while holding a valid token: hold the session and offer a
  // retry, rather than bouncing to login and making them type credentials
  // back in because uvicorn was restarting.
  if (!user && unreachable) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
        <Notice
          tone="error"
          title="Cannot reach the server"
          className="w-full max-w-sm"
          action={
            <button
              type="button"
              onClick={retry}
              className="mt-1 rounded bg-sky-700 px-3 py-1.5 text-sm text-white hover:bg-sky-600"
            >
              Try again
            </button>
          }
        >
          You are still signed in. The backend is not answering — check that it
          is running on port 8000.
        </Notice>
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

function Shell({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="border-b border-slate-700 bg-slate-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <span className="font-semibold text-white">CrimeNet AI</span>

          <nav className="flex flex-wrap gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm ${
                    isActive
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* ml-auto pushes this right when it fits; flex-wrap on the row and
              here lets it drop to its own line instead of overflowing the
              header, which clipped the agency badge and the logout button at
              tablet width. */}
          <div className="ml-auto flex flex-wrap items-center justify-end gap-2 text-sm">
            <span className="flex flex-wrap items-center gap-1.5 text-slate-300">
              <span className="truncate">{user.username}</span>
              <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                {user.role}
              </span>
              <span className="rounded bg-sky-900 px-2 py-0.5 text-xs text-sky-200">
                {user.agency_code}
              </span>
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded border border-slate-600 px-3 py-1.5 text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      {/* A second boundary inside the shell: a crash on one page keeps the
          nav and the other screens reachable, instead of blanking the app.
          Keyed on the path so navigating away actually clears it - without
          that the error screen follows you to every other page, which makes
          "the rest of the application is fine" untrue. */}
      <main className="mx-auto max-w-6xl px-4 py-8">
        <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <Shell>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/resolution" element={<Resolution />} />
                <Route path="/audit" element={<AuditLog />} />
                <Route
                  path="/stats"
                  element={
                    <Placeholder
                      title="Stats"
                      owner="Rishabh"
                      week="W6–W7"
                      description="Counts by entity type, relationships by agency, and the audit chain status."
                    />
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Shell>
          </RequireAuth>
        }
      />
    </Routes>
  )
}
