import { useState } from 'react'
import { useProblems } from '@/hooks/useDashboard'

export default function ProblemsPage() {
  const [keyword, setKeyword] = useState('')
  const { data: problems, isLoading } = useProblems({ keyword: keyword || undefined })

  if (isLoading) return <div className="text-journal-muted">加载中...</div>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-hand font-bold text-journal-ink">题库</h1>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="搜索题目..."
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          className="rounded-lg border border-journal-accentLight/50 bg-journal-paper px-4 py-2 text-sm text-journal-ink outline-none focus:border-journal-accent focus:ring-1 focus:ring-journal-accent"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {problems?.map(p => (
          <div key={p.id} className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                p.difficulty === '简单' ? 'bg-green-100 text-green-700' :
                p.difficulty === '中等' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                {p.difficulty}
              </span>
              <span className="text-xs text-journal-muted">{p.category}</span>
            </div>
            <h3 className="mt-2 font-hand font-semibold text-journal-ink">
              #{p.id} {p.title}
            </h3>
            {p.slug && (
              <a
                href={`https://leetcode.cn/problems/${p.slug}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-xs text-journal-accent hover:underline"
              >
                LeetCode →
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
