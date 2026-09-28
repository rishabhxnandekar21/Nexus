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
      .then((response) => setUser(response.data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

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

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout])

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
