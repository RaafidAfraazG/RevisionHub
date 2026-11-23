import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, ClipboardCheck, ClipboardList, Inbox, Plus } from 'lucide-react'
import { api, type ChangeRequest, type ChangeStatus } from '../api'
import { useAuth } from '../auth'
import { Badge, ErrorMessage, Loading, formatDate, messageOf } from '../components/ui'

function inboxDescription(role: string) {
  if (role === 'ENGINEER') return 'Your draft and rejected requests, ready for the next step.'
  if (role === 'REVIEWER') return 'Submitted changes waiting for your engineering review.'
  return 'Reviewed changes waiting for your final approval and release.'
}

export default function ChangesPage({ inbox = false }: { inbox?: boolean }) {
  const { user } = useAuth()
  const [changes, setChanges] = useState<ChangeRequest[]>([])
  const [status, setStatus] = useState<ChangeStatus | ''>('')
  const [mine, setMine] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true; setLoading(true); setError('')
    api.changes(inbox ? user?.role === 'ENGINEER' ? { mine: true } : { status: 'IN_REVIEW' } : { status: status || undefined, mine })
      .then(data => {
        if (!active) return
        setChanges(inbox ? data.filter(change => {
          if (user?.role === 'ENGINEER') return change.status === 'DRAFT' || change.status === 'REJECTED'
          if (change.created_by === user?.id) return false
          return user?.role === 'REVIEWER' ? !change.review_passed : change.review_passed
        }) : data)
      }).catch(error => { if (active) setError(messageOf(error)) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [inbox, status, mine, user?.id, user?.role])
  return <>
    <div className="eyebrow"><span className="tiny-line" />CHANGE MANAGEMENT</div>
    <div className="page-heading"><div><h1>{inbox ? 'My Inbox' : 'Change requests'}</h1><p>{inbox ? inboxDescription(user?.role || '') : 'Engineering proposals, review decisions and release records.'}</p></div>{user?.role === 'ENGINEER' && <Link className="button primary" to="/changes/new"><Plus size={18} />New Change Request</Link>}</div>
    <section className="panel"><div className="panel-toolbar"><div className="section-heading">{inbox ? <Inbox size={20} /> : <ClipboardList size={20} />}<h2>{inbox ? 'Waiting for you' : 'All change requests'}</h2><span className="count">{changes.length}</span></div>{!inbox && <div className="change-filters"><label className="checkbox-label"><input type="checkbox" checked={mine} onChange={event => setMine(event.target.checked)} />Created by me</label><label className="sr-only" htmlFor="status-filter">Filter by status</label><select id="status-filter" className="compact-select" value={status} onChange={event => setStatus(event.target.value as ChangeStatus | '')}><option value="">All statuses</option><option value="DRAFT">Draft</option><option value="IN_REVIEW">In review</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option><option value="RELEASED">Released</option></select></div>}</div>
      <ErrorMessage message={error} />
      {loading ? <Loading /> : error ? null : changes.length === 0 ? <div className="empty"><ClipboardCheck size={32} /><h3>{inbox ? 'No open ECRs' : 'No matching ECRs'}</h3><p>{inbox ? 'Requests waiting for your role will appear here.' : 'Create a request or adjust your filters.'}</p></div> : <div className="table-scroll"><table><thead><tr><th>Number / title</th><th>Part</th><th>Status</th><th>Created by</th><th>Date</th><th /></tr></thead><tbody>{changes.map(change => <tr key={change.id}><td><Link className="part-number" to={`/changes/${change.id}`}>{change.number}</Link><p className="change-title">{change.title}</p></td><td><Link className="text-link" to={`/parts/${change.part_id}`}>{change.part.part_number}</Link><p className="tree-name">{change.part.name} · <span className="font-mono">Rev {change.draft_revision.label}</span></p></td><td><Badge state={change.status} />{change.status === 'IN_REVIEW' && <p className="tree-name">{change.review_passed ? 'Awaiting approval' : 'Awaiting review'}</p>}</td><td><span>{change.creator.full_name}</span><p className="tree-name">{change.creator.username}</p></td><td>{formatDate(change.created_at)}</td><td><Link className="icon-button" to={`/changes/${change.id}`} aria-label={`Open ${change.number}`}><ChevronRight size={18} /></Link></td></tr>)}</tbody></table></div>}
      <div className="panel-footer"><span>{changes.length} {changes.length === 1 ? 'request' : 'requests'}</span><span>Decisions retained by review cycle</span></div>
    </section>
  </>
}
