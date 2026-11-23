import { History } from 'lucide-react'
import type { AuditEntry } from '../api'

function actionLabel(action: string) {
  return action.toLowerCase().split('_').map(word => word === 'ecr' ? 'ECR' : word === 'bom' ? 'BOM' : word).join(' ')
}

export default function AuditTimeline({ entries }: { entries: AuditEntry[] }) {
  if (!entries.length) return <div className="empty"><History size={26} /><p>No recorded activity yet.</p></div>
  return <ol className="audit-timeline">{entries.map(entry => <li key={entry.id}>
    <span className="timeline-dot"><History size={14} /></span>
    <div className="audit-body"><div className="audit-heading"><strong>{actionLabel(entry.action)}</strong><time dateTime={entry.timestamp}>{new Date(/Z$|[+-]\d\d:\d\d$/.test(entry.timestamp) ? entry.timestamp : `${entry.timestamp}Z`).toLocaleString()}</time></div>
      <p>{entry.actor.full_name} <span className="muted">· {entry.actor.role.toLowerCase()} · {entry.entity_type.toLowerCase().replaceAll('_', ' ')} #{entry.entity_id}</span></p>
      {entry.details.from_state && <p className="audit-detail">{entry.details.from_state} → {entry.details.to_state}</p>}
      {entry.details.comment && <blockquote>{entry.details.comment}</blockquote>}
      {entry.details.child_part_id && <p className="audit-detail">Child part #{entry.details.child_part_id} · Quantity {entry.details.quantity}</p>}
      {entry.details.cycle && <p className="audit-detail">Review cycle {entry.details.cycle}</p>}
    </div>
  </li>)}</ol>
}
