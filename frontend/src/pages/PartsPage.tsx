import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Box, Boxes, ChevronRight, GitBranch, Layers3, Package, Plus, Search, X } from 'lucide-react'
import { api, type NewPart, type Part } from '../api'
import { Badge, ErrorMessage, Loading, Modal, messageOf } from '../components/ui'

function NewPartModal({ onClose, onCreated }: { onClose: () => void; onCreated: (part: Part) => void }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const part: NewPart = { part_number: String(data.get('part_number')).trim(), name: String(data.get('name')).trim(), description: String(data.get('description')).trim(), part_type: data.get('part_type') as NewPart['part_type'] }
    setBusy(true); setError('')
    try { onCreated(await api.createPart(part)) } catch (error) { setError(messageOf(error)) } finally { setBusy(false) }
  }
  return <Modal title="Create a part" description="Start with a part number and a few details." onClose={onClose}>
    <form onSubmit={submit} className="form-stack"><ErrorMessage message={error} />
      <label>Part number<input name="part_number" placeholder="e.g. BIKE-002" required maxLength={80} autoFocus /></label>
      <label>Name<input name="name" placeholder="e.g. Touring Bicycle" required maxLength={200} /></label>
      <label>Part type<select name="part_type"><option value="COMPONENT">Component</option><option value="ASSEMBLY">Assembly</option></select></label>
      <label>Description <span className="optional">optional</span><textarea name="description" placeholder="What is this part used for?" rows={3} maxLength={10000} /></label>
      <div className="modal-actions"><button type="button" className="button secondary" onClick={onClose}>Cancel</button><button disabled={busy} className="button primary">{busy ? 'Creating…' : 'Create part'}</button></div>
    </form>
  </Modal>
}

export default function PartsPage() {
  const [parts, setParts] = useState<Part[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(false)
  const navigate = useNavigate()
  useEffect(() => {
    let active = true
    const timer = setTimeout(() => {
      setLoading(true)
      api.parts(query).then(data => { if (active) { setParts(data); setError('') } }).catch(error => { if (active) setError(messageOf(error)) }).finally(() => { if (active) setLoading(false) })
    }, 180)
    return () => { active = false; clearTimeout(timer) }
  }, [query])
  const assemblies = parts.filter(part => part.part_type === 'ASSEMBLY').length
  return <>
    <div className="eyebrow"><span className="tiny-line" />PRODUCT DATA</div>
    <div className="page-heading"><div><h1>Parts library</h1><p>Released components, assemblies and working revisions.</p></div><button className="button primary" onClick={() => setModal(true)}><Plus size={18} />New Part</button></div>
    <div className="stats-grid">
      <Stat icon={<Package size={21} />} label={query ? 'Matching parts' : 'Total parts'} value={parts.length} detail="In your parts library" />
      <Stat icon={<Boxes size={21} />} label="Assemblies" value={assemblies} detail="Built from other parts" />
      <Stat icon={<Box size={21} />} label="Components" value={parts.length - assemblies} detail="Purchased and manufactured items" />
    </div>
    <section className="panel">
      <div className="panel-toolbar"><div className="section-heading"><h2>All parts</h2><span className="count">{parts.length}</span></div><label className="search"><Search size={18} /><input aria-label="Search parts" placeholder="Search by part number or name…" value={query} onChange={event => setQuery(event.target.value)} />{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={16} /></button>}</label></div>
      <ErrorMessage message={error} />
      {loading ? <Loading /> : error ? <div className="empty"><p>Could not load parts. Check that the backend is running.</p></div> : parts.length === 0 ? <div className="empty"><Package size={32} /><h3>{query ? 'No matching parts' : 'No parts registered'}</h3><p>{query ? 'Try a different number or name.' : 'Create your first part, or run the sample seed script.'}</p></div> : <div className="table-scroll"><table>
        <thead><tr><th>Part number</th><th>Name</th><th>Type</th><th>Latest revision</th><th>State</th><th><span className="sr-only">Open part</span></th></tr></thead>
        <tbody>{parts.map(part => <tr key={part.id}><td><Link className="part-number" to={`/parts/${part.id}`}>{part.part_number}</Link></td><td className="font-medium">{part.name}</td><td><span className="type-label">{part.part_type === 'ASSEMBLY' ? <Boxes size={16} /> : <Box size={16} />}{part.part_type === 'ASSEMBLY' ? 'Assembly' : 'Component'}</span></td><td>{part.latest_revision ? <Link className="revision-chip" to={`/revisions/${part.latest_revision.id}`}>Rev {part.latest_revision.label}</Link> : <span className="muted">—</span>}</td><td><Badge state={part.latest_revision?.state ?? null} /></td><td><Link className="icon-button" to={`/parts/${part.id}`} aria-label={`Open ${part.part_number}`}><ChevronRight size={18} /></Link></td></tr>)}</tbody>
      </table></div>}
      <div className="panel-footer"><span>{parts.length} {parts.length === 1 ? 'part' : 'parts'}{query ? ' matching your search' : ' in your library'}</span><span className="flex items-center gap-2"><Layers3 size={14} />Parts, revisions & changes</span></div>
    </section>
    <div className="workspace-note"><GitBranch size={17} /><span>Select a part number to inspect revisions and product structure.</span></div>
    {modal && <NewPartModal onClose={() => setModal(false)} onCreated={part => navigate(`/parts/${part.id}`)} />}
  </>
}

function Stat({ icon, label, value, detail }: { icon: ReactNode; label: string; value: number; detail: string }) {
  return <div className="stat"><div><p className="stat-label">{label}</p><strong>{value.toString().padStart(2, '0')}</strong><p className="stat-detail">{detail}</p></div><div className="stat-icon">{icon}</div></div>
}
