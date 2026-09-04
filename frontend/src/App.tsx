import { Routes, Route, Link } from 'react-router-dom'
import { BookOpen, LayoutDashboard, Settings } from 'lucide-react'
import DashboardPage from './pages/DashboardPage'
import ProblemsPage from './pages/ProblemsPage'
import ProblemDetailPage from './pages/ProblemDetailPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <div className="min-h-screen bg-journal-bg">
      {/* 顶部导航 */}
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
              <NavLink to="/settings" icon={<Settings size={18} />} label="设置" />
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容 */}
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/problems" element={<ProblemsPage />} />
          <Route path="/problems/:id" element={<ProblemDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
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
