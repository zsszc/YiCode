import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import { BookOpen, BookMarked, LayoutDashboard, Settings, LogOut, User, TrendingUp } from 'lucide-react'
import { useState, useEffect } from 'react'
import DashboardPage from './pages/DashboardPage'
import ProblemsPage from './pages/ProblemsPage'
import ProblemDetailPage from './pages/ProblemDetailPage'
import SettingsPage from './pages/SettingsPage'
import AuthPage from './pages/AuthPage'
import LearningCurvePage from './pages/LearningCurvePage'
import TemplatesPage from './pages/TemplatesPage'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('yicode_token'))
  const [user, setUser] = useState<{ id: number; username: string } | null>(null)

  useEffect(() => {
    if (token) {
      fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.json())
        .then(data => {
          if (data.id) setUser(data)
        })
        .catch(() => {
          localStorage.removeItem('yicode_token')
          setToken(null)
        })
    }
  }, [token])

  const handleLogin = (newToken: string, newUser: { id: number; username: string }) => {
    setToken(newToken)
    setUser(newUser)
  }

  const handleLogout = () => {
    localStorage.removeItem('yicode_token')
    setToken(null)
    setUser(null)
  }

  if (!token) {
    return <AuthPage onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen bg-journal-bg">
      <nav className="sticky top-0 z-50 border-b border-line bg-journal-bg/85 backdrop-blur-fix-md">
        <div className="mx-auto max-w-[1600px] px-4">
          <div className="flex h-14 items-center justify-between">
            <Link to="/" className="group flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand to-[#4f8ef7] text-base shadow-glow transition-transform group-hover:scale-105">
                🐇
              </span>
              <span className="bg-gradient-to-r from-white to-brand-light bg-clip-text text-lg font-bold tracking-wide text-transparent">
                忆码 YiCode
              </span>
            </Link>
            <div className="flex items-center gap-1">
              <NavLink to="/" icon={<LayoutDashboard size={17} />} label="看板" />
              <NavLink to="/problems" icon={<BookOpen size={17} />} label="题库" />
              <NavLink to="/templates" icon={<BookMarked size={17} />} label="模板" />
              <NavLink to="/learning-curve" icon={<TrendingUp size={17} />} label="曲线" />
              <NavLink to="/settings" icon={<Settings size={17} />} label="设置" />
              {user && (
                <div className="ml-2 flex items-center gap-2 border-l border-line pl-3">
                  <span className="flex items-center gap-1.5 text-xs text-journal-muted">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-dim text-brand-light">
                      <User size={13} />
                    </span>
                    {user.username}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="rounded-md p-1.5 text-journal-muted transition-colors hover:bg-surface-hover hover:text-journal-danger"
                    title="退出登录"
                  >
                    <LogOut size={15} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-[1600px] px-4 py-5">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/problems" element={<ProblemsPage />} />
          <Route path="/problems/:id" element={<ProblemDetailPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/learning-curve" element={<LearningCurvePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}

function NavLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  const location = useLocation()
  const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
  return (
    <Link
      to={to}
      className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors ${
        active
          ? 'bg-brand-dim text-brand-light'
          : 'text-journal-muted hover:bg-surface-hover hover:text-journal-ink'
      }`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </Link>
  )
}

export default App
