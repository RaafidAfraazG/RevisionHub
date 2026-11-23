import { useEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ChevronRight, LoaderCircle, X } from 'lucide-react'
import type { ChangeStatus, RevisionState } from '../api'

const stateNames: Record<RevisionState | ChangeStatus, string> = { DRAFT: 'Draft', IN_REVIEW: 'In review', RELEASED: 'Released', OBSOLETE: 'Obsolete', APPROVED: 'Approved', REJECTED: 'Rejected' }

export function Badge({ state }: { state: RevisionState | ChangeStatus | null }) {
  return state ? <span className={`badge badge-${state.toLowerCase()}`}><span className="badge-dot" />{stateNames[state]}</span> : <span className="muted">No revision</span>
}

export function ErrorMessage({ message }: { message: string }) {
  return message ? <div role="alert" className="error"><AlertCircle size={18} /><span>{message}</span></div> : null
}

export function Loading() { return <div className="empty"><LoaderCircle className="animate-spin" size={24} /><p>Loading workspace…</p></div> }
export function formatDate(value: string) { return new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) }
export function messageOf(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please try again.' }

export function Modal({ title, description, onClose, children }: { title: string; description: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = ref.current!; dialog.showModal(); return () => dialog.close() }, [])
  return <dialog ref={ref} onCancel={onClose} onClick={event => { if (event.target === ref.current) onClose() }} aria-labelledby="modal-title" className="modal">
    <div className="modal-heading"><div><h2 id="modal-title">{title}</h2><p className="muted mt-1">{description}</p></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20} /></button></div>
    {children}
  </dialog>
}

export function Breadcrumb({ children }: { children: ReactNode }) { return <nav aria-label="Breadcrumb" className="breadcrumb"><Link to="/parts">Parts library</Link><ChevronRight size={14} />{children}</nav> }
