import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { GitBranch, History, Plus } from 'lucide-react'
import { api, type AuditEntry, type PartDetail } from '../api'
import { useAuth } from '../auth'
import AuditTimeline from '../components/AuditTimeline'
import { Badge, Breadcrumb, ErrorMessage, Loading, Modal, formatDate, messageOf } from '../components/ui'

export default function PartPage() {
  const { id = '' } = useParams()
  const [part, setPart] = useState<PartDetail | null>(null)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [tab, setTab] = useState<'revisions' | 'audit'>('revisions')
  const { user } = useAuth()
  const navigate = useNavigate()
  useEffect(() => { let active = true; setPart(null); setError(''); setTab('revisions'); Promise.all([api.part(id), api.partAudit(id)]).then(([part, audit]) => { if (active) { setPart(part); setAudit(audit) } }).catch(error => { if (active) setError(messageOf(error)) }); return () => { active = false } }, [id])
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!part) return
    const note = String(new FormData(event.currentTarget).get('change_note'))
    setBusy(true); setActionError('')
    try { const revision = await api.createRevision(part.id, note); navigate(`/revisions/${revision.id}`) } catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  if (error) return <><Breadcrumb>Part</Breadcrumb><ErrorMessage message={error} /></>
  if (!part) return <Loading />
  return <>
    <Breadcrumb><span>{part.part_number}</span></Breadcrumb>
    <div className="page-heading"><div><div className="eyebrow">{part.part_number}</div><h1>{part.name}</h1><p>{part.description || 'No description added yet.'}</p></div><div className="heading-actions">{user?.role === 'ENGINEER' && <Link className="button primary" to={`/changes/new?part=${part.id}`}><Plus size={18} />New Change Request</Link>}<button className="button secondary" onClick={() => { setActionError(''); setModal(true) }}>Create Next Revision</button></div></div>
    <div className="detail-strip"><span><span className="muted">Type</span><strong>{part.part_type === 'ASSEMBLY' ? 'Assembly' : 'Component'}</strong></span><span><span className="muted">Created</span><strong>{formatDate(part.created_at)}</strong></span><span><span className="muted">Revisions</span><strong>{part.revisions.length}</strong></span>{part.revisions.length >= 2 && <Link className="button secondary small" to={`/parts/${part.id}/compare`}>Compare revisions</Link>}</div>
    <div className="part-tabs" role="tablist" aria-label="Part details"><button id="revisions-tab" role="tab" aria-selected={tab === 'revisions'} aria-controls="revisions-panel" onClick={() => setTab('revisions')}><GitBranch size={17} />Revisions <span className="count">{part.revisions.length}</span></button><button id="audit-tab" role="tab" aria-selected={tab === 'audit'} aria-controls="audit-panel" onClick={() => setTab('audit')}><History size={17} />Audit</button></div>
    {tab === 'audit' ? <section id="audit-panel" role="tabpanel" aria-labelledby="audit-tab" className="panel"><div className="panel-toolbar"><h2>Part activity</h2><span className="muted text-sm">Includes revisions, BOM edits and change requests</span></div><AuditTimeline entries={audit} /></section> : <section id="revisions-panel" role="tabpanel" aria-labelledby="revisions-tab" className="panel"><div className="panel-toolbar"><div className="section-heading"><GitBranch size={20} /><h2>Revision history</h2><span className="count">{part.revisions.length}</span></div><span className="muted text-sm">Newest first</span></div>
      {part.revisions.length === 0 ? <div className="empty"><GitBranch size={30} /><h3>Ready for revision A</h3><p>Create the first revision to start building this part’s BOM.</p></div> : <div className="table-scroll"><table><thead><tr><th>Revision</th><th>State</th><th>Change note</th><th>Created</th><th>Released</th><th /></tr></thead><tbody>{[...part.revisions].reverse().map(revision => <tr key={revision.id}><td><Link className="part-number" to={`/revisions/${revision.id}`}>Rev {revision.label}</Link></td><td><Badge state={revision.state} /></td><td className="note-cell">{revision.change_note || '—'}</td><td>{formatDate(revision.created_at)}</td><td>{revision.released_at ? formatDate(revision.released_at) : '—'}</td><td><Link className="text-link" to={`/revisions/${revision.id}`}>View BOM</Link></td></tr>)}</tbody></table></div>}
    </section>}
    {modal && <Modal title="Create next revision" description="A new revision starts in Draft with an empty BOM." onClose={() => setModal(false)}><form className="form-stack" onSubmit={create}><ErrorMessage message={actionError} /><label>Change note <span className="optional">optional</span><textarea name="change_note" placeholder="Describe the reason for this revision…" maxLength={10000} rows={4} autoFocus /></label><div className="modal-actions"><button type="button" className="button secondary" onClick={() => setModal(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Creating…' : 'Create revision'}</button></div></form></Modal>}
  </>
}
