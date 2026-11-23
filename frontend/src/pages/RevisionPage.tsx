import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, ChevronRight, GitBranch, Layers3, Package, Plus } from 'lucide-react'
import { api, saveBlob, type BomNode, type Part, type RevisionDetail } from '../api'
import { Badge, Breadcrumb, ErrorMessage, Loading, Modal, formatDate, messageOf } from '../components/ui'
import BomTree from '../components/BomTree'
import Attachments from '../components/Attachments'
import PreviousCompare from '../components/PreviousCompare'

export default function RevisionPage() {
  const { id = '' } = useParams()
  const [data, setData] = useState<{ revision: RevisionDetail; tree: BomNode; parts: Part[] } | null>(null)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [modal, setModal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    let active = true; setError('')
    Promise.all([api.revision(id), api.tree(id), api.parts()]).then(([revision, tree, parts]) => { if (active) setData({ revision, tree, parts }) }).catch(error => { if (active) setError(messageOf(error)) })
    return () => { active = false }
  }, [id, refresh])
  // Prevent rendering stale data when navigating between revisions.
  const current = data && String(data.revision.id) === id ? data : null
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    setBusy(true); setActionError('')
    try { await api.addLine(id, Number(form.get('child')), Number(form.get('quantity'))); setModal(false); setRefresh(value => value + 1) } catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  async function remove(lineId: number) {
    setBusy(true); setActionError('')
    try { await api.removeLine(id, lineId); setRefresh(value => value + 1) } catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  async function exportCsv() {
    setBusy(true); setActionError('')
    try { saveBlob(await api.exportCsv(id), `${current!.revision.part.part_number}-rev-${current!.revision.label}-bom.csv`) }
    catch (error) { setActionError(messageOf(error)) } finally { setBusy(false) }
  }
  if (error) return <><Breadcrumb>Revision</Breadcrumb><ErrorMessage message={error} /></>
  if (!current) return <Loading />
  const { revision, tree, parts } = current
  const editable = revision.state === 'DRAFT'
  const available = parts.filter(part => part.id !== revision.part_id && !revision.bom_lines.some(line => line.child_part_id === part.id))
  return <>
    <Breadcrumb><Link to={`/parts/${revision.part_id}`}>{revision.part.part_number}</Link><ChevronRight size={14} /><span className="font-mono">Revision {revision.label}</span></Breadcrumb>
    <div className="page-heading"><div><div className="eyebrow">{revision.part.part_number} / REVISION {revision.label}</div><h1>{revision.part.name} <span className="heading-revision">Rev {revision.label}</span></h1><p>{revision.change_note || 'Product structure and multi-level bill of materials.'}</p></div><Badge state={revision.state} /></div>
    <div className="detail-strip"><span><span className="muted">Created</span><strong>{formatDate(revision.created_at)}</strong></span><span><span className="muted">Released</span><strong>{revision.released_at ? formatDate(revision.released_at) : 'Not released'}</strong></span><span><span className="muted">Direct BOM lines</span><strong>{revision.bom_lines.length}</strong></span></div>
    <div className="info-banner">{editable ? <GitBranch size={18} /> : <Check size={18} />}<span>{editable ? 'Draft is editable. Quantities are per parent assembly.' : <><span className="font-mono">Rev {revision.label}</span> is locked{revision.state === 'IN_REVIEW' ? ' while in review.' : '. Create a new revision to change the structure.'}</>}</span></div>
    {!modal && <ErrorMessage message={actionError} />}
    <div className="revision-actions"><PreviousCompare partId={revision.part_id} revisionId={revision.id} /><button className="button secondary small" disabled={busy} onClick={exportCsv}>{busy ? 'Working…' : 'Export CSV'}</button></div>
    <section className="panel"><div className="panel-toolbar"><div className="section-heading"><Layers3 size={20} /><h2>Bill of materials</h2></div>{editable && <button className="button primary small" disabled={busy || available.length === 0} onClick={() => { setActionError(''); setModal(true) }}><Plus size={16} />Add BOM line</button>}</div>
      <BomTree key={id} tree={tree} editable={editable} busy={busy} remove={remove} />
      <div className="panel-footer"><span>Child parts use their latest released revision, or latest available.</span><span>Quantities are per parent</span></div>
    </section>
    {revision.bom_lines.length === 0 && <div className="workspace-note"><Package size={18} /><span>{editable ? 'No BOM lines yet. Add a part to start defining this structure.' : 'This revision has no child parts.'}</span></div>}
    <Attachments key={id} revisionId={id} editable={editable} />
    {modal && <Modal title="Add BOM line" description="Add a direct child part to this draft revision." onClose={() => setModal(false)}><form onSubmit={add} className="form-stack"><ErrorMessage message={actionError} /><label>Child part<select name="child" required autoFocus defaultValue=""><option value="" disabled>Select a part…</option>{available.map(part => <option value={part.id} key={part.id}>{part.part_number} · {part.name}</option>)}</select></label><label>Quantity<input name="quantity" type="number" required min={1} max={2147483647} step={1} defaultValue={1} /></label><p className="muted text-sm">Self references and circular structures are automatically rejected.</p><div className="modal-actions"><button className="button secondary" type="button" onClick={() => setModal(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Adding…' : 'Add BOM line'}</button></div></form></Modal>}
  </>
}
