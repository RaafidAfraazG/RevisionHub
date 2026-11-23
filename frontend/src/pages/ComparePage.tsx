import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { GitCompareArrows } from 'lucide-react'
import { api, type Comparison, type DiffKind, type PartDetail } from '../api'
import { Breadcrumb, ErrorMessage, Loading, messageOf } from '../components/ui'

const kinds: DiffKind[] = ['ADDED', 'REMOVED', 'QTY_CHANGED', 'REVISION_CHANGED']
const labels: Record<DiffKind, string> = { ADDED: 'Added', REMOVED: 'Removed', QTY_CHANGED: 'Quantity changed', REVISION_CHANGED: 'Revision changed' }

export default function ComparePage() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const [part, setPart] = useState<PartDetail | null>(null)
  const [diff, setDiff] = useState<Comparison | null>(null)
  const [error, setError] = useState('')
  const [comparing, setComparing] = useState(false)
  useEffect(() => { let active = true; setPart(null); setError(''); api.part(id).then(p => { if (active) setPart(p) }).catch(e => { if (active) setError(messageOf(e)) }); return () => { active = false } }, [id])
  const revisions = part?.revisions || []
  const oldId = Number(params.get('old')) || revisions.at(-2)?.id || revisions[0]?.id || 0
  const newId = Number(params.get('new')) || revisions.at(-1)?.id || 0
  useEffect(() => {
    if (!part || revisions.length < 2) return
    let active = true; setDiff(null); setError(''); setComparing(true)
    if (![oldId, newId].every(id => revisions.some(r => r.id === id))) {
      setError('Choose two revisions of this part.'); setComparing(false); return
    }
    api.compare(oldId, newId).then(result => { if (active) setDiff(result) }).catch(e => { if (active) setError(messageOf(e)) }).finally(() => { if (active) setComparing(false) })
    return () => { active = false }
  }, [part, oldId, newId])
  if (!part) return error ? <ErrorMessage message={error} /> : <Loading />
  const rows = diff ? kinds.flatMap(kind => diff[kind].map(item => ({ kind, item }))) : []
  return <>
    <Breadcrumb><Link to={`/parts/${part.id}`}>{part.part_number}</Link><span>/ Compare</span></Breadcrumb>
    <div className="page-heading"><div><div className="eyebrow">PRODUCT STRUCTURE / COMPARE</div><h1>Compare revisions</h1><p><span className="font-mono">{part.part_number}</span> · {part.name} · Full multi-level BOM comparison</p></div><GitCompareArrows size={32} color="#596273" /></div>
    {revisions.length < 2 ? <section className="panel empty"><h2>Two revisions needed</h2><p>Create another revision to compare product structures.</p><Link to={`/parts/${part.id}`} className="text-link">Open part</Link></section> : <>
      <section className="panel compare-picker form-stack"><label>Baseline<select aria-label="Baseline revision" value={oldId} onChange={e => setParams({ old: e.target.value, new: String(newId) })}>{revisions.map(r => <option key={r.id} value={r.id}>Rev {r.label} · {r.state.replaceAll('_', ' ')}</option>)}</select></label><span className="muted">compared with</span><label>Proposed<select aria-label="Proposed revision" value={newId} onChange={e => setParams({ old: String(oldId), new: e.target.value })}>{revisions.map(r => <option key={r.id} value={r.id}>Rev {r.label} · {r.state.replaceAll('_', ' ')}</option>)}</select></label><button className="button secondary" onClick={() => setParams({ old: String(newId), new: String(oldId) })}>Swap revisions</button></section>
      <ErrorMessage message={error} />
      {comparing ? <Loading /> : diff && <>
        <div className="stats-grid compare-stats">{kinds.map(kind => <div key={kind} className={`stat diff-${kind.toLowerCase()}`}><div><div className="stat-label">{labels[kind]}</div><strong>{diff.summary[kind]}</strong></div></div>)}</div>
        <section className="panel"><div className="panel-toolbar"><h2>Bill of materials diff</h2><span className="muted text-sm">Effective quantities across all paths</span></div>{rows.length === 0 ? <div className="empty"><GitCompareArrows size={28} /><h3>No BOM differences</h3><p>Both revisions contain the same parts, quantities and resolved child revisions.</p></div> : <div className="table-scroll"><table className="diff-table"><thead><tr><th>Change</th><th>Part</th><th>Baseline</th><th>Proposed</th><th>Paths</th></tr></thead><tbody>{rows.map(({ kind, item }) => <tr key={`${kind}-${item.part_number}`} className={`diff-${kind.toLowerCase()}`}><td><span className="diff-label">{labels[kind]}</span></td><td><strong className="part-number">{item.part_number}</strong><div className="tree-name">{item.name}</div></td><td>{kind === 'REVISION_CHANGED' ? item.old_revision?.map(r => r || 'None').join(', ') : kind === 'ADDED' ? '—' : kind === 'REMOVED' ? item.total_quantity : item.old_qty}</td><td>{kind === 'REVISION_CHANGED' ? item.new_revision?.map(r => r || 'None').join(', ') : kind === 'REMOVED' ? '—' : kind === 'ADDED' ? item.total_quantity : item.new_qty}</td><td className="diff-paths">{(item.paths ? [{ label: '', paths: item.paths }] : [{ label: 'Before: ', paths: item.old_paths || [] }, { label: 'After: ', paths: item.new_paths || [] }]).map(group => <div key={group.label}>{group.paths.map((p, index) => <div key={index}>{group.label}{p.path.join(' / ')} <span className="muted">(×{p.total_quantity})</span></div>)}</div>)}</td></tr>)}</tbody></table></div>}</section>
        <p className="workspace-note">Historical revisions resolve child releases at their release date. Drafts use current releases. A part can have both quantity and revision changes.</p>
      </>}
    </>}
  </>
}
