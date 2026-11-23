import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, Boxes, ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import type { BomNode } from '../api'
import { Badge } from './ui'

export default function BomTree({ tree, editable, busy, remove }: { tree: BomNode; editable: boolean; busy: boolean; remove: (id: number) => void }) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const rows: { node: BomNode; depth: number; key: string }[] = []
  const branches: string[] = []
  function walk(node: BomNode, depth: number, key: string, visible: boolean) {
    if (node.children.length) branches.push(key)
    if (visible) rows.push({ node, depth, key })
    node.children.forEach(child => walk(child, depth + 1, `${key}/${child.line_id}`, visible && !collapsed.has(key)))
  }
  walk(tree, 0, 'root', true)
  function toggle(key: string) { setCollapsed(previous => { const next = new Set(previous); if (next.has(key)) next.delete(key); else next.add(key); return next }) }
  return <><div className="tree-tools"><span className="muted text-sm">Product structure</span><div><button onClick={() => setCollapsed(new Set())}>Expand all</button><span>·</span><button onClick={() => setCollapsed(new Set(branches))}>Collapse all</button></div></div><div className="table-scroll"><table className="bom-table"><thead><tr><th>Part / assembly</th><th>Revision</th><th>State</th><th className="text-right">Qty</th>{editable && <th><span className="sr-only">Actions</span></th>}</tr></thead><tbody>{rows.map(({ node, depth, key }) => <tr key={key} className={depth === 0 ? 'root-row' : ''}><td><div className="tree-part" style={{ paddingLeft: `${depth * 24}px` }}>{Array.from({ length: depth }, (_, i) => <span key={i} className={`tree-guide ${i === depth - 1 ? 'tree-branch' : ''}`} style={{ left: `${i * 24 + 8}px` }} />)}{node.children.length ? <button className="tree-toggle" onClick={() => toggle(key)} aria-expanded={!collapsed.has(key)} aria-label={`${collapsed.has(key) ? 'Expand' : 'Collapse'} ${node.part_number}`}>{collapsed.has(key) ? <ChevronRight size={16} /> : <ChevronDown size={16} />}</button> : <span className="tree-leaf" />}<div className={`tree-icon ${node.children.length || depth === 0 ? 'assembly-icon' : ''}`}>{node.children.length || depth === 0 ? <Boxes size={18} /> : <Box size={18} />}</div><div><Link className="part-number" to={`/parts/${node.part_id}`}>{node.part_number}</Link><p className="tree-name">{node.name}{node.cycle_detected && <span className="badge badge-rejected">Cycle stopped</span>}</p></div></div></td><td>{node.revision_id ? <Link to={`/revisions/${node.revision_id}`} className="revision-chip">Rev {node.revision_label}</Link> : <span className="muted">—</span>}</td><td><Badge state={node.state} /></td><td className="quantity">{node.quantity}</td>{editable && <td className="w-14">{depth === 1 && node.line_id !== null && <button className="icon-button danger" disabled={busy} onClick={() => remove(node.line_id!)} aria-label={`Remove ${node.part_number} from BOM`}><Trash2 size={17} /></button>}</td>}</tr>)}</tbody></table></div></>
}
