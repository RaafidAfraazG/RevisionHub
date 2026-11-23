import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ClipboardList, Inbox, Layers3, LayoutDashboard, LogOut, Package } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { AuthProvider, useAuth } from './auth'
import { Loading } from './components/ui'
import PartsPage from './pages/PartsPage'
import PartPage from './pages/PartPage'
import RevisionPage from './pages/RevisionPage'
import LoginPage from './pages/LoginPage'
import ChangesPage from './pages/ChangesPage'
import ChangePage from './pages/ChangePage'
import NewChangePage from './pages/NewChangePage'
import ComparePage from './pages/ComparePage'
import Toasts from './components/Toasts'

const DashboardPage = lazy(() => import('./pages/DashboardPage'))

function ProtectedRoutes() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Loading />
  return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
}

function Workspace() {
  const { user, logout } = useAuth()
  return <div className={`workspace ${user ? '' : 'signed-out'}`}>
    <header className="navbar"><div className="nav-inner">
      <Link to="/" className="brand"><span className="brand-mark"><Layers3 size={23} /></span>Revision<span className="brand-light">Hub</span></Link>
      {user && <><div className="sidebar-caption">PRODUCT LIFECYCLE</div><nav className="nav-links" aria-label="Main navigation"><NavLink to="/" end className="nav-item"><LayoutDashboard size={17} />Overview</NavLink><NavLink to="/parts" className="nav-item"><Package size={17} />Parts register</NavLink><NavLink to="/changes" className="nav-item"><ClipboardList size={17} />Change requests</NavLink><NavLink to="/inbox" className="nav-item"><Inbox size={17} />My inbox</NavLink></nav><div className="sidebar-note">REVISION CONTROL<br /><span>Parts · Structures · Decisions</span></div></>}
      {user && <div className="user-menu"><div className="user-label"><strong>{user.full_name}</strong><span>{user.role.toLowerCase()}</span></div><button className="logout-button" onClick={logout} aria-label="Logout"><LogOut size={17} /><span>Logout</span></button></div>}
    </div></header>
    <Toasts /><main className="main"><Suspense fallback={<Loading />}><Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoutes />}>
        <Route path="/" element={<DashboardPage />} /><Route path="/dashboard" element={<Navigate to="/" replace />} /><Route path="/parts" element={<PartsPage />} />
        <Route path="/parts/:id/compare" element={<ComparePage />} />
        <Route path="/parts/:id" element={<PartPage />} /><Route path="/revisions/:id" element={<RevisionPage />} />
        <Route path="/changes" element={<ChangesPage />} /><Route path="/changes/new" element={<NewChangePage />} />
        <Route path="/changes/:id" element={<ChangePage />} /><Route path="/inbox" element={<ChangesPage inbox />} />
        <Route path="*" element={<div className="empty"><h1>Page not found</h1><Link className="text-link" to="/">Return to dashboard</Link></div>} />
      </Route>
    </Routes></Suspense></main>
    <footer className="app-footer"><span>RevisionHub / Engineering records</span><span>Revision-controlled product data</span></footer>
  </div>
}

export default function App() { return <AuthProvider><Workspace /></AuthProvider> }
