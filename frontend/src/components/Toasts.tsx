import { useEffect, useState } from 'react'
import { AlertCircle, X } from 'lucide-react'

export default function Toasts() {
  const [toast, setToast] = useState<{ message: string; key: number } | null>(null)
  useEffect(() => {
    const show = (event: Event) => setToast({ message: (event as CustomEvent<string>).detail, key: Date.now() })
    window.addEventListener('revisionhub:error', show)
    return () => window.removeEventListener('revisionhub:error', show)
  }, [])
  useEffect(() => { if (toast) { const timer = window.setTimeout(() => setToast(null), 7000); return () => clearTimeout(timer) } }, [toast])
  return toast && <div className="toast" role="alert"><AlertCircle size={20} /><span>{toast.message}</span><button onClick={() => setToast(null)} aria-label="Dismiss notification"><X size={18} /></button></div>
}
