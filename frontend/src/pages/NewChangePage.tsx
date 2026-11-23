import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { GitBranch, Plus } from 'lucide-react'
import { api, type Part, type PartDetail } from '../api'
import { useAuth } from '../auth'
import { ErrorMessage, Loading, messageOf } from '../components/ui'

export default function NewChangePage() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  const [parts, setParts] = useState<Part[]>([])
  const [partId, setPartId] = useState(params.get('part') || '')
  const [part, setPart] = useState<PartDetail | null>(null)
  const [revisionId, setRevisionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => { let active = true; api.parts().then(parts => { if (active) setParts(parts) }).catch(error => { if (active) setError(messageOf(error)) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [])
  useEffect(() => {
    let active = true; setPart(null); setRevisionId('')
    if (partId) api.part(partId).then(part => { if (active) setPart(part) }).catch(error => { if (active) setError(messageOf(error)) })
    return () => { active = false }
  }, [partId])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      const change = await api.createChange({ part_id: Number(partId), ...(revisionId ? { draft_revision_id: Number(revisionId) } : {}), title: String(form.get('title')), reason: String(form.get('reason')), description: String(form.get('description')) })
      navigate(`/changes/${change.id}`)
    } catch (error) { setError(messageOf(error)) } finally { setBusy(false) }
  }
  if (user?.role !== 'ENGINEER') return <ErrorMessage message="Only engineers can create change requests." />
  if (loading) return <Loading />
  return <>
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link to="/changes">Change requests</Link><span>/</span><span>New request</span></nav>
    <div className="page-heading"><div><div className="eyebrow">PROPOSE A CHANGE</div><h1>New Change Request</h1><p>Capture what needs to change and why. Prepare the draft BOM before submitting.</p></div></div>
    <div className="new-change-layout"><section className="panel form-panel"><form className="form-stack" onSubmit={submit}><ErrorMessage message={error} />
      <label>Part<select name="part" required value={partId} onChange={event => setPartId(event.target.value)}><option value="" disabled>Select a part…</option>{parts.map(part => <option key={part.id} value={part.id}>{part.part_number} · {part.name}</option>)}</select></label>
      <label>Proposed revision<select value={revisionId} onChange={event => setRevisionId(event.target.value)} disabled={!part}><option value="">Use an available draft or create the next revision</option>{part?.revisions.filter(revision => revision.state === 'DRAFT').map(revision => <option key={revision.id} value={revision.id}>Rev {revision.label} · Draft</option>)}</select></label>
      <label>Title<input name="title" placeholder="Summarize the proposed change" required maxLength={200} /></label>
      <label>Reason<textarea name="reason" placeholder="Why is this change needed?" required maxLength={10000} rows={3} /></label>
      <label>Description <span className="optional">optional</span><textarea name="description" placeholder="Describe the scope and intended outcome" maxLength={10000} rows={4} /></label>
      <div className="modal-actions"><Link className="button secondary" to="/changes">Cancel</Link><button className="button primary" disabled={busy || !part}><Plus size={16} />{busy ? 'Creating…' : 'Create draft request'}</button></div>
    </form></section><aside className="change-help"><GitBranch size={27} /><h2>Start with a draft</h2><p>An available draft revision will be linked to this request. If there isn’t one, a new revision is created with an empty BOM.</p><p>Open the linked revision to edit its BOM. Submitting the request locks that revision for review.</p><p>Already linked drafts stay with their existing ECR throughout rejection and resubmission.</p></aside></div>
  </>
}
