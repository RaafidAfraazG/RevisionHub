import { lazy, Suspense, useEffect, useState, type FormEvent } from 'react'
import { Download, Paperclip, Trash2, Upload } from 'lucide-react'
import { api, type Attachment } from '../api'
import { ErrorMessage, Loading, formatDate, messageOf } from './ui'

const StlViewer = lazy(() => import('./StlViewer'))
export default function Attachments({ revisionId, editable }: { revisionId: string; editable: boolean }) {
  const [files, setFiles] = useState<Attachment[] | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let active = true; setFiles(null); setSelected(null); setError('')
    api.attachments(revisionId).then(files => { if (active) { setFiles(files); setSelected(files[0]?.id || null) } }).catch(e => { if (active) setError(messageOf(e)) })
    return () => { active = false }
  }, [revisionId])
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget
    const file = new FormData(form).get('file') as File | null
    if (!file?.size) { setError('Choose a nonempty attachment.'); return }
    if (file.size > 20 * 1024 * 1024) { setError('Maximum attachment size is 20 MB.'); return }
    setBusy(true); setError('')
    try { const attachment = await api.upload(revisionId, file); setFiles(old => [attachment, ...(old || [])]); setSelected(attachment.id); form.reset() }
    catch (e) { setError(messageOf(e)) } finally { setBusy(false) }
  }
  async function remove(file: Attachment) {
    setBusy(true); setError('')
    try { await api.deleteAttachment(file.id); const remaining = (files || []).filter(item => item.id !== file.id); setFiles(remaining); if (selected === file.id) setSelected(remaining[0]?.id || null) }
    catch (e) { setError(messageOf(e)) } finally { setBusy(false) }
  }
  const preview = files?.find(file => file.id === selected)
  return <section className="panel attachments-panel"><div className="panel-toolbar"><div className="section-heading"><Paperclip size={20} /><h2>Attachments</h2><span className="count">{files?.length || 0}</span></div><span className="muted text-sm">{editable ? 'STL, STEP, PDF, PNG, JPG · Max 20 MB' : 'Read-only revision'}</span></div>
    {editable && <form onSubmit={upload} className="upload-form"><label><span className="sr-only">Choose attachment</span><input name="file" type="file" required accept=".stl,.step,.stp,.pdf,.png,.jpg" disabled={busy || !files} /></label><button className="button secondary small" disabled={busy || !files}><Upload size={15} />{busy ? 'Saving…' : 'Upload file'}</button></form>}
    <div className="attachment-error"><ErrorMessage message={error} /></div>
    {!files ? !error && <Loading /> : files.length === 0 ? <div className="empty"><Paperclip size={27} /><h3>No attachments yet</h3><p>{editable ? 'Upload a model, drawing or supporting image.' : 'No files were attached to this revision.'}</p></div> : <div className="attachments-layout"><ul className="attachment-list">{files.map(file => <li key={file.id} className={selected === file.id ? 'selected' : ''}><button className="attachment-select" onClick={() => setSelected(file.id)} aria-pressed={selected === file.id}><strong>{file.filename}</strong><span>{(file.size / 1024).toFixed(1)} KB · {formatDate(file.uploaded_at)}</span></button><div className="attachment-actions"><a href={`/api/attachments/${file.id}/download`} className="text-link" download><Download size={14} />Download</a>{editable && <button disabled={busy} className="icon-button danger" aria-label={`Delete ${file.filename}`} onClick={() => remove(file)}><Trash2 size={16} /></button>}</div></li>)}</ul><div className="attachment-preview">{preview?.file_type === '.stl' ? <Suspense fallback={<Loading />}><StlViewer key={preview.id} attachmentId={preview.id} /></Suspense> : preview && ['.png', '.jpg'].includes(preview.file_type) ? <ImagePreview key={preview.id} file={preview} /> : <div className="empty"><Paperclip size={30} /><h3>{preview?.filename}</h3><p>{preview && ['.step', '.stp'].includes(preview.file_type) ? 'STEP preview not supported, download to open in CAD' : 'Download this document to open it.'}</p>{preview && <a className="button secondary small" href={`/api/attachments/${preview.id}/download`} download>Download file</a>}</div>}</div></div>}
  </section>
}

function ImagePreview({ file }: { file: Attachment }) {
  const [failed, setFailed] = useState(false)
  return failed ? <ErrorMessage message="Image preview unavailable. Download the attachment to inspect it." /> : <img className="attachment-image" src={`/api/attachments/${file.id}/download`} alt={file.filename} onError={() => setFailed(true)} />
}
