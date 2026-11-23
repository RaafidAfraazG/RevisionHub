import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { GitCompareArrows } from 'lucide-react'
import { api, type Revision } from '../api'

export default function PreviousCompare({ partId, revisionId }: { partId: number; revisionId: number }) {
  const [previous, setPrevious] = useState<Revision | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let active = true; setPrevious(null); setFailed(false)
    api.part(String(partId)).then(part => { if (active) setPrevious([...part.revisions].filter(r => r.id < revisionId).sort((a, b) => b.id - a.id)[0] || null) })
      .catch(() => { if (active) setFailed(true) })
    return () => { active = false }
  }, [partId, revisionId])
  if (failed) return <Link className="button secondary small" to={`/parts/${partId}/compare`}>Choose revisions to compare</Link>
  return previous ? <Link className="button secondary small" to={`/parts/${partId}/compare?old=${previous.id}&new=${revisionId}`}><GitCompareArrows size={16} />Compare with previous revision</Link> : null
}
