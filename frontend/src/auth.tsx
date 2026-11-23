import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokenStorage, type User } from './api'

interface AuthContextValue {
  user: User | null
  loading: boolean
  error: string
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!tokenStorage.get())
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    if (tokenStorage.get()) {
      api.me().then(user => { if (active) setUser(user) }).catch(error => {
        if (active) setError(error instanceof Error ? error.message : 'Could not restore your session.')
      }).finally(() => { if (active) setLoading(false) })
    }
    function unauthorized() { setUser(null); setError('Your session expired. Please log in again.') }
    function storage(event: StorageEvent) {
      if (event.key === 'revisionhub_token') {
        setUser(null)
        if (event.newValue) window.location.reload()
      }
    }
    window.addEventListener('revisionhub:unauthorized', unauthorized)
    window.addEventListener('storage', storage)
    return () => { active = false; window.removeEventListener('revisionhub:unauthorized', unauthorized); window.removeEventListener('storage', storage) }
  }, [])
  async function login(username: string, password: string) {
    const result = await api.login(username, password)
    tokenStorage.set(result.access_token)
    setUser(result.user)
    setError('')
  }
  function logout() { tokenStorage.clear(); setUser(null); setError('') }
  return <AuthContext.Provider value={{ user, loading, error, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
