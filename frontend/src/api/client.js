import axios from 'axios'

/** Where the JWT lives. localStorage is XSS-vulnerable and that is an accepted
 *  MVP trade-off, named in CLAUDE.md Section 8 - production would use an
 *  httpOnly refresh cookie. Exported so AuthContext and the interceptors
 *  cannot drift on the key name. */
export const TOKEN_KEY = 'crimenet_token'

/** Relative baseURL, so the Vite /api proxy handles it in dev and a reverse
 *  proxy would handle it anywhere else. Nothing hardcodes localhost:8000. */
const client = axios.create({ baseURL: '/api' })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    // A 401 from anywhere means the token is gone, expired or invalid - drop it
    // and send the user to login. The login call itself opts out with
    // skipAuthRedirect: a wrong password is a form error, not a dead session,
    // and redirecting on it would blank the page the user is typing into.
    const status = error.response?.status
    if (status === 401 && !error.config?.skipAuthRedirect) {
      localStorage.removeItem(TOKEN_KEY)
      if (window.location.pathname !== '/login') {
        window.location.replace('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default client
