import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type ChangeRequest, type Dashboard } from '../api'
import { useAuth } from '../auth'
import { Badge, ErrorMessage, Loading, formatDate, messageOf } from '../components/ui'

function StateChart({ title, counts }: { title: string; counts: Record<string, number> }) {
  const data = Object.entries(counts).map(([state, count]) => ({ state: state.toLowerCase().replaceAll('_', ' '), count }))
  return <section className="panel"><div className="panel-toolbar"><h2>{title}</h2></div><div className="chart" role="img" aria-label={`${title}: ${data.map(d => `${d.state} ${d.count}`).join(', ')}`}><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 14, bottom: 0, left: -20 }}><CartesianGrid vertical={false} stroke="#e5e7eb" /><XAxis dataKey="state" tick={{ fontSize: 11, fill: '#626973' }} axisLine={false} tickLine={false} interval={0} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ fill: '#f3f4f6' }} /><Bar isAnimationActive={false} name="Records" dataKey="count" fill="#858e9a" maxBarSize={24} /></BarChart></ResponsiveContainer></div></section>
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState<Dashboard | null>(null)
  const [changes, setChanges] = useState<ChangeRequest[]>([])
  const [error, setError] = useState('')
  useEffect(() => { let active = true; Promise.all([api.dashboard(), api.changes()]).then(([d, c]) => { if (active) { setData(d); setChanges(c) } }).catch(e => { if (active) setError(messageOf(e)) }); return () => { active = false } }, [])
  if (error) return <ErrorMessage message={error} />
  if (!data) return <Loading />
  const waiting = changes.filter(c => user?.role === 'ENGINEER' ? c.created_by === user.id && ['DRAFT', 'REJECTED'].includes(c.status) : c.created_by !== user?.id && c.status === 'IN_REVIEW' && (user?.role === 'REVIEWER' ? !c.review_passed : c.review_passed))
  return <>
    <div className="page-heading"><div><div className="eyebrow">WORKSPACE / OVERVIEW</div><h1>Engineering overview</h1><p>Review queue and latest changes to the product record.</p></div><Link to="/changes" className="button secondary">All change requests</Link></div>
    <section className="panel queue-panel"><div className="panel-toolbar"><div className="section-heading"><h2>ECRs waiting on you</h2><span className="count">{waiting.length}</span></div><span className="muted">{user?.role.toLowerCase()} queue</span></div>{waiting.length ? <div className="table-scroll"><table><thead><tr><th>Request</th><th>Proposed change</th><th>Part / revision</th><th>State</th><th>Updated</th></tr></thead><tbody>{waiting.map(c => <tr key={c.id}><td><Link className="part-number" to={`/changes/${c.id}`}>{c.number}</Link></td><td className="note-cell"><Link to={`/changes/${c.id}`}>{c.title}</Link></td><td><Link className="part-number" to={`/parts/${c.part_id}`}>{c.part.part_number}</Link><span className="revision-chip ml-2">Rev {c.draft_revision.label}</span></td><td><Badge state={c.status} /></td><td>{formatDate(c.updated_at)}</td></tr>)}</tbody></table></div> : <div className="compact-empty">No open ECRs for your role.</div>}</section>
    <div className="dashboard-main"><section className="panel"><div className="panel-toolbar"><h2>Recent activity</h2><span className="muted">Latest 10 events</span></div><div className="table-scroll"><table><thead><tr><th>Event / record</th><th>Actor</th><th>Date</th></tr></thead><tbody>{data.recent_activity.map(entry => <tr key={entry.id}><td><div>{entry.action.toLowerCase().replaceAll('_', ' ')}</div><Link className="part-number" to={`/${entry.entity_type === 'CHANGE_REQUEST' ? 'changes' : entry.entity_type === 'REVISION' ? 'revisions' : 'parts'}/${entry.entity_id}`}>{entry.details.change_number || entry.details.number || `${entry.entity_type.toLowerCase().replaceAll('_', ' ')} #${entry.entity_id}`}</Link></td><td>{entry.actor.full_name}</td><td className="font-mono">{formatDate(entry.timestamp)}</td></tr>)}</tbody></table></div></section><aside className="overview-aside"><section className="panel"><div className="panel-toolbar"><h2>Product register</h2></div><dl className="register-summary"><div><dt>Parts</dt><dd>{data.parts}</dd></div><div><dt>Revisions</dt><dd>{Object.values(data.revisions_by_state).reduce((a, b) => a + b, 0)}</dd></div><div><dt>Currently released</dt><dd>{data.revisions_by_state.RELEASED}</dd></div><div><dt>ECRs in review</dt><dd>{data.ecrs_by_status.IN_REVIEW}</dd></div><div><dt>Mean release time</dt><dd>{data.average_release_hours === null ? '—' : `${data.average_release_hours} h`}</dd></div></dl><p className="summary-note">First submission to release · {data.released_ecr_sample_size} completed requests</p></section><StateChart title="Revision states" counts={data.revisions_by_state} /><StateChart title="ECR states" counts={data.ecrs_by_status} /></aside></div>
  </>
}
