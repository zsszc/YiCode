import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useProblems } from '@/hooks/useDashboard'
import { Search, Code2, ChevronRight } from 'lucide-react'

const DIFFICULTIES = ['全部', '简单', '中等', '困难'] as const

const DIFF_STYLE: Record<string, string> = {
  简单: 'text-easy bg-easy/10 border-easy/25',
  中等: 'text-medium bg-medium/10 border-medium/25',
  困难: 'text-hard bg-hard/10 border-hard/25',
}

export default function ProblemsPage() {
  const [keyword, setKeyword] = useState('')
  const [difficulty, setDifficulty] = useState<string>('全部')
  const [category, setCategory] = useState<string>('全部')

  const { data: problems, isLoading } = useProblems({ keyword: keyword || undefined })

  const categories = useMemo(
    () => ['全部', ...Array.from(new Set((problems ?? []).map(p => p.category)))],
    [problems]
  )

  const filtered = useMemo(
    () =>
      (problems ?? []).filter(
        p =>
          (difficulty === '全部' || p.difficulty === difficulty) &&
          (category === '全部' || p.category === category)
      ),
    [problems, difficulty, category]
  )

  const stats = useMemo(() => {
    const all = problems ?? []
    const done = all.filter(p => p.status && p.status !== 'todo').length
    return {
      total: all.length,
      done,
      pct: all.length ? Math.round((done / all.length) * 100) : 0,
      easy: all.filter(p => p.difficulty === '简单').length,
      medium: all.filter(p => p.difficulty === '中等').length,
      hard: all.filter(p => p.difficulty === '困难').length,
    }
  }, [problems])

  return (
    <div className="space-y-5">
      {/* 头部统计 */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="bg-gradient-to-r from-white via-white to-brand-light bg-clip-text text-2xl font-bold text-transparent">
            题库
          </h1>
          <p className="mt-1 text-sm text-journal-muted">
            LeetCode Hot 100 · 站内编码 + AI 辅助学习
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-journal-muted">共 <b className="text-white">{stats.total}</b> 题</span>
          <span className="text-easy">简单 {stats.easy}</span>
          <span className="text-medium">中等 {stats.medium}</span>
          <span className="text-hard">困难 {stats.hard}</span>
        </div>
      </div>

      {/* 总进度 */}
      <div className="flex items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3">
        <span className="text-xs font-medium text-journal-muted">总进度</span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-black/40">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand to-[#4f8ef7] transition-all duration-700"
            style={{ width: `${stats.pct}%` }}
          />
        </div>
        <span className="text-xs font-semibold text-brand-light">
          {stats.done}/{stats.total} · {stats.pct}%
        </span>
      </div>

      {/* 搜索与筛选 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-journal-muted" />
          <input
            type="text"
            placeholder="搜索题号或题名..."
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            className="w-64 rounded-lg border border-line bg-surface py-2 pl-9 pr-3 text-sm text-journal-ink outline-none transition-colors placeholder:text-journal-muted/60 focus:border-brand"
          />
        </div>
        <div className="flex gap-1 rounded-lg border border-line bg-surface p-1">
          {DIFFICULTIES.map(d => (
            <button
              key={d}
              onClick={() => setDifficulty(d)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                difficulty === d
                  ? 'bg-brand text-white'
                  : 'text-journal-muted hover:text-journal-ink'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* 分类标签 */}
      <div className="flex flex-wrap gap-1.5">
        {categories.map(c => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
              category === c
                ? 'border-brand/50 bg-brand-dim text-brand-light'
                : 'border-line bg-surface text-journal-muted hover:border-brand/30 hover:text-journal-ink'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* 题目卡片 */}
      {isLoading ? (
        <div className="py-20 text-center text-journal-muted">加载中...</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map(p => (
            <Link
              key={p.id}
              to={`/problems/${p.id}`}
              className="group rounded-xl border border-line bg-surface p-4 transition-all hover:border-brand/40 hover:bg-surface-raised hover:shadow-card"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${
                    DIFF_STYLE[p.difficulty] ?? 'text-journal-muted bg-surface'
                  }`}
                >
                  {p.difficulty}
                </span>
                <span className="text-xs text-journal-muted">{p.category}</span>
              </div>
              <h3 className="mt-2.5 font-semibold text-journal-ink transition-colors group-hover:text-brand-light">
                <span className="mr-1.5 font-mono text-sm text-journal-muted">#{p.id}</span>
                {p.title}
              </h3>
              <div className="mt-3 flex items-center justify-between border-t border-line/60 pt-3">
                <span className="flex items-center gap-1.5 text-xs text-journal-muted">
                  <Code2 size={13} className="text-brand-light" />
                  站内编码 · AI 辅导
                </span>
                <ChevronRight
                  size={15}
                  className="text-journal-muted transition-all group-hover:translate-x-0.5 group-hover:text-brand-light"
                />
              </div>
            </Link>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-16 text-center text-sm text-journal-muted">
              没有匹配的题目，换个关键词或筛选条件试试
            </div>
          )}
        </div>
      )}
    </div>
  )
}
