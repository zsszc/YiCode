import { useState } from 'react'
import { useDashboard } from '@/hooks/useDashboard'
import { dashboardApi, reviewApi } from '@/services/api'
import { useQueryClient } from '@tanstack/react-query'
import type { DashboardItem } from '@/types'

export default function DashboardPage() {
  const { data, isLoading, error } = useDashboard()
  const queryClient = useQueryClient()
  const [undoId, setUndoId] = useState<number | null>(null)

  if (isLoading) return <div className="text-journal-muted">加载中...</div>
  if (error) return <div className="text-journal-danger">加载失败</div>
  if (!data) return null

  const handleReview = async (problemId: number, score: 'easy' | 'ok' | 'hard') => {
    await reviewApi.review(problemId, score)
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const handleShiftForward = async () => {
    await dashboardApi.shiftForward()
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  return (
    <div className="space-y-6">
      {/* 日期与统计 */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-hand font-bold text-journal-ink">
            {data.date} {data.is_weekend ? '· 周末' : '· 工作日'}
          </h1>
          <p className="text-sm text-journal-muted mt-1">
            配额 {data.quota} 道 · 已做 {data.done_today.length} 道 · 剩余 {data.todo_left} 道未刷
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <StatBadge label="未刷" count={data.counts.todo} color="bg-gray-100 text-gray-600" />
          <StatBadge label="遗忘" count={data.counts.forgot} color="bg-red-50 text-red-600" />
          <StatBadge label="磕绊" count={data.counts.shaky} color="bg-yellow-50 text-yellow-600" />
          <StatBadge label="稳固" count={data.counts.solid} color="bg-green-50 text-green-600" />
          <StatBadge label="归档" count={data.counts.archived} color="bg-blue-50 text-blue-600" />
        </div>
      </div>

      {/* 昨日空档提示 */}
      {data.skipped_yesterday && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3">
          <p className="text-sm text-yellow-800">
            昨天有 {data.skipped_yesterday.review_count} 道复习题到期但没做，
            <button onClick={handleShiftForward} className="ml-1 underline font-medium hover:text-yellow-900">
              全部顺延到今天 →
            </button>
          </p>
        </div>
      )}

      {/* 到期复习 */}
      {data.due_review.length > 0 && (
        <section>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-hand font-semibold text-journal-ink">
            <span>🔄</span> 今日到期复习 ({data.due_review.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.due_review.map(item => (
              <ProblemCard key={item.id} item={item} onReview={handleReview} />
            ))}
          </div>
        </section>
      )}

      {/* 今日新题 */}
      {data.today_new.length > 0 && (
        <section>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-hand font-semibold text-journal-ink">
            <span>✨</span> 今日新题 ({data.today_new.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.today_new.map(item => (
              <ProblemCard key={item.id} item={item} isNew />
            ))}
          </div>
        </section>
      )}

      {/* 完成状态 */}
      {data.todo_left === 0 && data.due_review.length === 0 && (
        <div className="rounded-xl border-2 border-dashed border-journal-accent/30 bg-journal-accent/5 p-12 text-center">
          <div className="text-4xl mb-3">🎉</div>
          <h2 className="text-xl font-hand font-bold text-journal-ink">Hot 100 全部完成！</h2>
          <p className="text-journal-muted mt-2">继续保持复习节奏，把会做一次练成随时会做。</p>
        </div>
      )}
    </div>
  )
}

function StatBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${color}`}>
      {label} {count}
    </span>
  )
}

function ProblemCard({
  item,
  isNew,
  onReview,
}: {
  item: DashboardItem
  isNew?: boolean
  onReview?: (id: number, score: 'easy' | 'ok' | 'hard') => void
}) {
  const diffColor = {
    简单: 'bg-green-100 text-green-700',
    中等: 'bg-yellow-100 text-yellow-700',
    困难: 'bg-red-100 text-red-700',
  }[item.difficulty] || 'bg-gray-100 text-gray-700'

  return (
    <div className={`rounded-xl border bg-journal-paper p-4 shadow-sm transition-shadow hover:shadow-md ${
      item.is_overdue ? 'border-red-300' : 'border-journal-accentLight/40'
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${diffColor}`}>
              {item.difficulty}
            </span>
            <span className="text-xs text-journal-muted">{item.category}</span>
          </div>
          <h3 className="mt-1.5 truncate font-hand font-semibold text-journal-ink">
            #{item.id} {item.title}
          </h3>
          {item.next_review && (
            <p className={`mt-1 text-xs ${item.is_overdue ? 'text-red-500 font-medium' : 'text-journal-muted'}`}>
              到期: {item.next_review} {item.is_overdue && '(已逾期)'}
            </p>
          )}
        </div>
      </div>

      {!isNew && onReview && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onReview(item.id, 'easy')}
            className="flex-1 rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 transition-colors hover:bg-green-100"
          >
            😄 秒A
          </button>
          <button
            onClick={() => onReview(item.id, 'ok')}
            className="flex-1 rounded-lg bg-yellow-50 px-3 py-1.5 text-xs font-medium text-yellow-700 transition-colors hover:bg-yellow-100"
          >
            🙂 磕绊
          </button>
          <button
            onClick={() => onReview(item.id, 'hard')}
            className="flex-1 rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            😩 卡住
          </button>
        </div>
      )}

      {isNew && (
        <div className="mt-3">
          <a
            href={`https://leetcode.cn/problems/${item.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-lg bg-journal-accentLight/40 px-3 py-1.5 text-xs font-medium text-journal-accent transition-colors hover:bg-journal-accentLight/60"
          >
            去刷题 →
          </a>
        </div>
      )}
    </div>
  )
}
