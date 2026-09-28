import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Placeholder from './components/Placeholder'
import { useAuth } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/resolution', label: 'Resolution' },
  { to: '/audit', label: 'Audit log' },
  { to: '/stats', label: 'Stats' },
]

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  // Wait for /auth/me before deciding. Without this a refresh on any page
  // flashes the login screen even though the token is perfectly good.
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <p className="text-sm text-slate-400">Loading…</p>
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

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="border-b border-slate-700 bg-slate-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <span className="font-semibold text-white">CrimeNet AI</span>

          <nav className="flex gap-1">
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

          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-slate-300">
              {user.username}
              <span className="ml-2 rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                {user.role}
              </span>
              <span className="ml-1 rounded bg-sky-900 px-2 py-0.5 text-xs text-sky-200">
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

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
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
                <Route
                  path="/resolution"
                  element={
                    <Placeholder
                      title="Resolution queue"
                      owner="Rishabh"
                      week="W3–W4"
                      description="Proposed duplicate identities, reviewed and confirmed by a human. Nothing ever auto-merges."
                    />
                  }
                />
                <Route
                  path="/audit"
                  element={
                    <Placeholder
                      title="Audit log"
                      owner="Rishabh"
                      week="W3"
                      description="The SHA-256 hash chain, with a verify button that reports the exact row if it has been tampered with."
                    />
                  }
                />
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
