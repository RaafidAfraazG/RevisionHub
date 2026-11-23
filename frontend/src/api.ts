export type PartType = 'ASSEMBLY' | 'COMPONENT'
export type RevisionState = 'DRAFT' | 'IN_REVIEW' | 'RELEASED' | 'OBSOLETE'
export type Role = 'ENGINEER' | 'REVIEWER' | 'APPROVER'
export type ChangeStatus = 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'RELEASED'
export interface User { id: number; username: string; full_name: string; role: Role }
export interface LoginResponse { access_token: string; token_type: string; user: User }

export const tokenStorage = {
  get: () => localStorage.getItem('revisionhub_token'),
  set: (token: string) => localStorage.setItem('revisionhub_token', token),
  clear: () => localStorage.removeItem('revisionhub_token'),
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'ApiError' }
}

export interface Revision {
  id: number
  part_id: number
  label: string
  state: RevisionState
  change_note: string
  created_at: string
  released_at: string | null
}

export interface Part {
  id: number
  part_number: string
  name: string
  description: string
  part_type: PartType
  created_at: string
  latest_revision?: Revision | null
}

export interface PartDetail extends Part { revisions: Revision[] }
export interface BomLine {
  id: number
  parent_revision_id: number
  child_part_id: number
  quantity: number
  child_part: Part
}
export interface RevisionDetail extends Revision { part: Part; bom_lines: BomLine[] }
export interface BomNode {
  part_id: number
  revision_id: number | null
  line_id: number | null
  part_number: string
  name: string
  revision_label: string | null
  state: RevisionState | null
  quantity: number
  children: BomNode[]
  cycle_detected: boolean
}
export type NewPart = Pick<Part, 'part_number' | 'name' | 'description' | 'part_type'>

export interface ChangeRequest {
  id: number
  number: string
  title: string
  description: string
  reason: string
  part_id: number
  part: Part
  draft_revision_id: number
  draft_revision: Revision
  status: ChangeStatus
  created_by: number
  creator: User
  created_at: string
  updated_at: string
  review_cycle: number
  review_passed: boolean
}
export interface ChangeDecision {
  id: number
  actor_id: number
  actor: User
  stage: 'REVIEW' | 'APPROVAL'
  decision: 'APPROVE' | 'REJECT'
  comment: string
  cycle: number
  created_at: string
}
export interface AuditEntry {
  id: number
  timestamp: string
  actor_id: number
  actor: User
  action: string
  entity_type: string
  entity_id: number
  details: Record<string, string | number | null>
}
export interface ChangeDetail extends ChangeRequest { decisions: ChangeDecision[]; timeline: AuditEntry[] }
export interface NewChange { part_id: number; draft_revision_id?: number; title: string; reason: string; description: string }

function reportError(message: string) {
  window.dispatchEvent(new CustomEvent('revisionhub:error', { detail: message }))
}

async function request<T>(path: string, options?: RequestInit, asBlob = false): Promise<T> {
  const token = tokenStorage.get()
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { ...(options?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options?.headers },
  }).catch(() => { const message = 'Cannot reach the server. Check your connection and try again.'; reportError(message); throw new ApiError(message, 0) })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((error: { loc: (string | number)[]; msg: string }) => `${error.loc.slice(1).join('.')}: ${error.msg}`).join('; ')
      : `Request failed (${response.status}). Please try again.`
    if (response.status === 401 && token && path !== '/auth/login') {
      tokenStorage.clear()
      window.dispatchEvent(new Event('revisionhub:unauthorized'))
    }
    reportError(message)
    throw new ApiError(message, response.status)
  }
  if (asBlob) return await response.blob() as T
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

export const api = {
  login: (username: string, password: string) => request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request<User>('/auth/me'),
  parts: (q = '') => request<Part[]>(`/parts?q=${encodeURIComponent(q)}`),
  part: (id: string) => request<PartDetail>(`/parts/${id}`),
  createPart: (part: NewPart) => request<Part>('/parts', { method: 'POST', body: JSON.stringify(part) }),
  createRevision: (partId: number, changeNote: string) => request<Revision>(`/parts/${partId}/revisions`, {
    method: 'POST', body: JSON.stringify({ change_note: changeNote }),
  }),
  revision: (id: string) => request<RevisionDetail>(`/revisions/${id}`),
  tree: (id: string) => request<BomNode>(`/revisions/${id}/bom-tree`),
  addLine: (id: string, childId: number, quantity: number) => request<BomLine>(`/revisions/${id}/bom`, {
    method: 'POST', body: JSON.stringify({ child_part_id: childId, quantity }),
  }),
  removeLine: (id: string, lineId: number) => request<void>(`/revisions/${id}/bom/${lineId}`, { method: 'DELETE' }),
  changes: (filters: { status?: ChangeStatus; mine?: boolean } = {}) => {
    const query = new URLSearchParams()
    if (filters.status) query.set('status', filters.status)
    if (filters.mine) query.set('mine', 'true')
    return request<ChangeRequest[]>(`/changes?${query}`)
  },
  change: (id: string) => request<ChangeDetail>(`/changes/${id}`),
  createChange: (change: NewChange) => request<ChangeDetail>('/changes', { method: 'POST', body: JSON.stringify(change) }),
  submitChange: (id: number) => request<ChangeDetail>(`/changes/${id}/submit`, { method: 'POST' }),
  decide: (id: number, stage: 'review' | 'approve', decision: 'APPROVE' | 'REJECT', comment: string) =>
    request<ChangeDetail>(`/changes/${id}/${stage}`, { method: 'POST', body: JSON.stringify({ decision, comment }) }),
  partAudit: (id: string) => request<AuditEntry[]>(`/parts/${id}/audit`),
  compare: (oldId: number, newId: number) => request<Comparison>(`/revisions/${oldId}/compare/${newId}`),
  dashboard: () => request<Dashboard>('/dashboard'),
  attachments: (id: string) => request<Attachment[]>(`/revisions/${id}/attachments`),
  upload: (id: string, file: File) => { const body = new FormData(); body.append('file', file); return request<Attachment>(`/revisions/${id}/attachments`, { method: 'POST', body }) },
  deleteAttachment: (id: number) => request<void>(`/attachments/${id}`, { method: 'DELETE' }),
  exportCsv: (id: string) => request<Blob>(`/revisions/${id}/bom.csv`, undefined, true),
}

export type DiffKind = 'ADDED' | 'REMOVED' | 'QTY_CHANGED' | 'REVISION_CHANGED'
export interface BomPath { path: string[]; quantity: number; total_quantity: number }
export interface DiffItem {
  part_number: string; name: string; total_quantity?: number; revisions?: (string | null)[]; paths?: BomPath[]
  old_qty?: number; new_qty?: number; old_revision?: (string | null)[]; new_revision?: (string | null)[]
  old_paths?: BomPath[]; new_paths?: BomPath[]
}
export type Comparison = Record<DiffKind, DiffItem[]> & { summary: Record<DiffKind, number>; old_revision_id: number; new_revision_id: number }
export interface Attachment { id: number; revision_id: number; filename: string; file_type: string; size: number; uploaded_by: number; uploaded_at: string }
export interface Dashboard { parts: number; revisions_by_state: Record<RevisionState, number>; ecrs_by_status: Record<ChangeStatus, number>; average_release_hours: number | null; released_ecr_sample_size: number; recent_activity: AuditEntry[] }

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a'); link.href = url; link.download = filename
  document.body.appendChild(link); link.click(); link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
