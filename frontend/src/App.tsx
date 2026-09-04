import { Routes, Route, Link, Navigate } from 'react-router-dom'
import { BookOpen, LayoutDashboard, Settings, LogOut, User, TrendingUp } from 'lucide-react'
import { useState, useEffect } from 'react'
import DashboardPage from './pages/DashboardPage'
import ProblemsPage from './pages/ProblemsPage'
import ProblemDetailPage from './pages/ProblemDetailPage'
import SettingsPage from './pages/SettingsPage'
import AuthPage from './pages/AuthPage'
import LearningCurvePage from './pages/LearningCurvePage'

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
      <nav className="sticky top-0 z-50 border-b border-journal-accentLight/50 bg-journal-paper/80 backdrop-blur-sm">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex h-14 items-center justify-between">
            <Link to="/" className="flex items-center gap-2 text-journal-primary font-hand font-bold text-lg">
              <span className="text-2xl">🐇</span>
              <span>忆码 YiCode</span>
            </Link>
            <div className="flex items-center gap-1">
              <NavLink to="/" icon={<LayoutDashboard size={18} />} label="看板" />
              <NavLink to="/problems" icon={<BookOpen size={18} />} label="题库" />
              <NavLink to="/learning-curve" icon={<TrendingUp size={18} />} label="曲线" />
              <NavLink to="/settings" icon={<Settings size={18} />} label="设置" />
              {user && (
                <div className="flex items-center gap-2 ml-2 pl-2 border-l border-gray-200">
                  <span className="flex items-center gap-1 text-xs text-journal-muted">
                    <User size={14} />
                    {user.username}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="text-journal-muted hover:text-red-500 transition-colors"
                    title="退出登录"
                  >
                    <LogOut size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/problems" element={<ProblemsPage />} />
          <Route path="/problems/:id" element={<ProblemDetailPage />} />
          <Route path="/learning-curve" element={<LearningCurvePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}

function NavLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-journal-muted transition-colors hover:bg-journal-accentLight/30 hover:text-journal-ink"
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </Link>
  )
}

export default App
