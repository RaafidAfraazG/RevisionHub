import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, ChevronRight, ClipboardCheck, GitBranch, History, Send } from 'lucide-react'
import { api, type ChangeDetail } from '../api'
import { useAuth } from '../auth'
import AuditTimeline from '../components/AuditTimeline'
import PreviousCompare from '../components/PreviousCompare'
import { Badge, ErrorMessage, Loading, formatDate, messageOf } from '../components/ui'

function WorkflowStepper({ change }: { change: ChangeDetail }) {
  const current = change.status === 'RELEASED' ? 3 : change.review_passed ? 2 : change.status === 'IN_REVIEW' ? 1 : 0
  return <ol className="workflow-stepper" aria-label="Change request progress">{['Draft', 'In Review', 'Review Passed', 'Released'].map((label, index) => <li key={label} className={index < current ? 'complete' : index === current ? 'current' : ''} aria-current={index === current ? 'step' : undefined}><span className="step-marker">{index < current ? <Check size={16} /> : index + 1}</span><span>{label}</span></li>)}</ol>
}

export default function ChangePage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const [change, setChange] = useState<ChangeDetail | null>(null)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let active = true; setChange(null); setError(''); setActionError(''); setComment('')
    api.change(id).then(change => { if (active) setChange(change) }).catch(error => { if (active) setError(messageOf(error)) })
    return () => { active = false }
  }, [id])
  async function submitChange() {
    if (!change) return
    setBusy(true); setActionError('')
    try { setChange(await api.submitChange(change.id)) } catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  async function decide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!change || !stage) return
    const decision = ((event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null)?.value as 'APPROVE' | 'REJECT' | undefined
    if (!decision) return
    if (decision === 'REJECT' && !comment.trim()) { setActionError('Please explain why this request needs changes. A rejection comment is required.'); return }
    setBusy(true); setActionError('')
    try { setChange(await api.decide(change.id, stage, decision, comment)); setComment('') } catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  if (error) return <ErrorMessage message={error} />
  if (!change) return <Loading />
  const own = user?.id === change.created_by
  const canSubmit = user?.role === 'ENGINEER' && own && ['DRAFT', 'REJECTED'].includes(change.status)
  const stage = !own && change.status === 'IN_REVIEW'
    ? user?.role === 'REVIEWER' && !change.review_passed ? 'review'
      : user?.role === 'APPROVER' && change.review_passed ? 'approve' : null
    : null
  const draft = change.draft_revision.state === 'DRAFT'
  return <>
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link to="/changes">Change requests</Link><ChevronRight size={14} /><span>{change.number}</span></nav>
    <div className="page-heading"><div><div className="eyebrow">{change.number}</div><h1>{change.title}</h1><p>Proposed by {change.creator.full_name} · {formatDate(change.created_at)}</p></div><Badge state={change.status} /></div>
    <WorkflowStepper change={change} />
    <div className="revision-actions"><PreviousCompare partId={change.part_id} revisionId={change.draft_revision_id} /></div>
    {change.status === 'REJECTED' && <div className="rejection-banner"><strong>Changes requested</strong><p>The revision is back in Draft. Address the decision comments, update its BOM, then resubmit for a fresh review.</p></div>}
    <div className="change-detail-grid"><section className="panel change-info"><div className="panel-toolbar"><div className="section-heading"><GitBranch size={20} /><h2>Change proposal</h2></div></div><div className="proposal-content"><dl className="proposal-fields"><div><dt>Part</dt><dd><Link className="part-number" to={`/parts/${change.part_id}`}>{change.part.part_number}</Link><span>{change.part.name}</span></dd></div><div><dt>Proposed revision</dt><dd><Link className="revision-chip" to={`/revisions/${change.draft_revision_id}`}>Rev {change.draft_revision.label}</Link><Badge state={change.draft_revision.state} /></dd></div><div><dt>Reason</dt><dd className="prose-text">{change.reason}</dd></div><div><dt>Description</dt><dd className="prose-text">{change.description || 'No additional description.'}</dd></div></dl><Link className="button secondary" to={`/revisions/${change.draft_revision_id}`}><GitBranch size={17} />{draft ? 'Edit draft BOM' : 'View revision BOM'}</Link></div></section>
      <section className="panel action-panel"><div className="panel-toolbar"><div className="section-heading"><ClipboardCheck size={20} /><h2>Next step</h2></div></div><div className="action-content"><ErrorMessage message={actionError} />
        {canSubmit ? <><h3>{change.status === 'REJECTED' ? 'Ready for another review?' : 'Prepare, then submit'}</h3><p>Finish editing the proposed revision before submitting. Its BOM will be locked during review.</p><button className="button primary" disabled={busy} onClick={submitChange}><Send size={16} />{busy ? 'Submitting…' : change.status === 'REJECTED' ? 'Resubmit for review' : 'Submit for review'}</button></> : stage ? <form onSubmit={decide} className="form-stack"><h3>{stage === 'review' ? 'Engineering review' : 'Final approval'}</h3><p>{stage === 'review' ? 'Review the proposal and linked BOM before passing it to the approver.' : 'Approval immediately releases this revision and obsoletes the previous release.'}</p><label>Decision comment <span className="optional">required to reject</span><textarea value={comment} onChange={event => setComment(event.target.value)} rows={4} maxLength={10000} placeholder="Explain your decision…" /></label><button className="button primary" value="APPROVE" disabled={busy}>{busy ? 'Saving…' : stage === 'review' ? 'Approve review' : 'Final approve & release'}</button><button className="button reject-button" value="REJECT" disabled={busy}>{stage === 'review' ? 'Reject review' : 'Reject request'}</button></form> : <><h3>{change.status === 'RELEASED' ? 'Change released' : change.status === 'IN_REVIEW' ? change.review_passed ? 'Awaiting final approval' : 'Awaiting engineering review' : 'Waiting for the engineer'}</h3><p>{change.status === 'RELEASED' ? 'The proposed revision is released. Its previous release is now obsolete.' : own && user?.role !== 'ENGINEER' ? 'You cannot review or approve a request you created.' : 'This request has no action waiting for your current role.'}</p><Link className="text-link" to="/inbox">Go to My Inbox</Link></>}
      </div></section>
    </div>
    <section className="panel decisions-panel"><div className="panel-toolbar"><div className="section-heading"><ClipboardCheck size={20} /><h2>Decisions</h2><span className="count">{change.decisions.length}</span></div><span className="muted text-sm">Current cycle {change.review_cycle || 'not started'}</span></div>{change.decisions.length === 0 ? <div className="compact-empty">Review and approval decisions will appear here.</div> : <div className="decision-list">{[...change.decisions].reverse().map(decision => <article key={decision.id}><div className="decision-heading"><strong>{decision.actor.full_name}</strong><span className={`decision-result ${decision.decision.toLowerCase()}`}>{decision.decision === 'APPROVE' ? 'Approved' : 'Rejected'}</span></div><p className="muted text-sm">{decision.stage === 'REVIEW' ? 'Engineering review' : 'Final approval'} · Cycle {decision.cycle} · {formatDate(decision.created_at)}</p><p className="prose-text">{decision.comment || 'No comment added.'}</p></article>)}</div>}</section>
    <section className="panel"><div className="panel-toolbar"><div className="section-heading"><History size={20} /><h2>Audit timeline</h2></div><span className="muted text-sm">Newest first</span></div><AuditTimeline entries={change.timeline} /></section>
  </>
}
