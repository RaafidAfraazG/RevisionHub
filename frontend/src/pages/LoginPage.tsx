import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Layers3, LockKeyhole } from 'lucide-react'
import { useAuth } from '../auth'
import { ErrorMessage, Loading, messageOf } from '../components/ui'

export default function LoginPage() {
  const { user, loading, error: sessionError, login } = useAuth()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  if (loading) return <Loading />
  if (user) return <Navigate to={from?.startsWith('/') && !from.startsWith('//') && !from.startsWith('/login') ? from : '/'} replace />
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try { await login(String(form.get('username')).trim(), String(form.get('password'))) }
    catch (error) { setError(messageOf(error)) } finally { setBusy(false) }
  }
  return <div className="login-layout">
    <div className="login-intro"><div className="login-symbol"><Layers3 size={35} /></div><div className="eyebrow">ENGINEERING CHANGE MANAGEMENT</div><h1>Control the product record.</h1><p>Manage bicycle and gearbox structures, inspect revision differences, and route engineering changes for review.</p><div className="login-flow"><span>Draft</span><span>Review</span><span>Approval</span><span>Release</span></div></div>
    <section className="panel login-panel"><div className="login-heading"><LockKeyhole size={22} /><h2>Sign in</h2><p>Use your assigned engineering account.</p></div>
      <form onSubmit={submit} className="form-stack"><ErrorMessage message={error || sessionError} /><label>Username<input name="username" required autoComplete="username" autoFocus placeholder="e.g. engineer1" maxLength={80} /></label><label>Password<input name="password" type="password" required autoComplete="current-password" placeholder="Enter your password" maxLength={200} /></label><button disabled={busy} className="button primary">{busy ? 'Signing in…' : 'Sign in'}</button></form>
      <div className="demo-logins"><strong>Local demo accounts</strong><p>engineer1 · reviewer1 · approver1</p><p>Password for all: <code>password123</code></p></div>
    </section>
  </div>
}
