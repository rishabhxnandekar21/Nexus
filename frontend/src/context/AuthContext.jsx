import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import client, { TOKEN_KEY } from '../api/client'

const AuthContext = createContext(null)

function storedToken() {
  // localStorage throws in a private window with site data blocked. No token
  // is the right answer there, not a crash on first paint.
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Distinguishes "your token was rejected" from "the server did not answer".
  // Only the first should log you out.
  const [unreachable, setUnreachable] = useState(false)
  const [attempt, setAttempt] = useState(0)
  // Derived, not corrected in an effect: we are only "loading" if there is a
  // token whose user still has to be resolved. On a refresh we hold a token
  // but not yet a user, and routing before /auth/me answers would bounce a
  // logged-in user to the login page.
  const [loading, setLoading] = useState(() => Boolean(storedToken()))

  useEffect(() => {
    if (!storedToken()) return
    // The token survives a refresh; the user object does not. Re-resolve it
    // from the server rather than trusting anything cached in the browser.
    client
      .get('/auth/me')
      .then((response) => {
        setUser(response.data)
        setUnreachable(false)
      })
      .catch((err) => {
        // Only a 401 means the token is actually no good. A network error or
        // a 5xx means the backend is down or restarting, and throwing the
        // token away for that would silently sign the user out mid-demo -
        // which is exactly what happened before this distinction existed.
        if (err.response?.status === 401) {
          localStorage.removeItem(TOKEN_KEY)
          setUnreachable(false)
        } else {
          setUnreachable(true)
        }
      })
      .finally(() => setLoading(false))
  }, [attempt])

  const login = useCallback(async (username, password) => {
    // The backend takes an OAuth2 form body, not JSON - CLAUDE.md Section 6.
    const body = new URLSearchParams({ username, password })
    const { data } = await client.post('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      skipAuthRedirect: true,
    })
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  /** Re-run the /auth/me check - for the "server unreachable" retry. */
  const retry = useCallback(() => {
    setLoading(true)
    setUnreachable(false)
    setAttempt((n) => n + 1)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setUnreachable(false)
  }, [])

  const value = useMemo(
    () => ({ user, loading, unreachable, login, logout, retry }),
    [user, loading, unreachable, login, logout, retry],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// The hook ships beside its provider deliberately. Splitting it would need a
// third file to hold the context object, and CLAUDE.md Section 4 names one
// AuthContext.jsx. The only cost is that editing this file does a full reload
// in dev instead of a hot one.
// oxlint-disable-next-line react/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }
  return context
}
