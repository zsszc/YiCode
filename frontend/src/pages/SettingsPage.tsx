import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Flame, Brain, Target, TrendingUp } from 'lucide-react'
import { profileApi } from '@/services/api'
import type { LearningProfile } from '@/types'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => profileApi.get(),
  })

  const { data: adaptive } = useQuery({
    queryKey: ['adaptive'],
    queryFn: () => profileApi.adaptive(),
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<LearningProfile>) => profileApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      queryClient.invalidateQueries({ queryKey: ['adaptive'] })
    },
  })

  if (isLoading) return <div className="text-journal-muted">加载中...</div>
  if (!profile) return null

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-hand font-bold text-journal-ink">设置</h1>

      {/* 学习画像卡片 */}
      <div className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-5">
        <div className="mb-4 flex items-center gap-2">
          <Brain size={20} className="text-journal-accent" />
          <h2 className="text-lg font-hand font-semibold text-journal-ink">学习画像</h2>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <StatCard
            icon={<Flame size={16} className="text-orange-500" />}
            label="连续打卡"
            value={`${profile.streak_days} 天`}
            sub={`最高 ${profile.max_streak} 天`}
          />
          <StatCard
            icon={<Target size={16} className="text-blue-500" />}
            label="总解题数"
            value={`${profile.total_solved}`}
          />
          <StatCard
            icon={<TrendingUp size={16} className="text-green-500" />}
            label="首次成功率"
            value={`${(profile.first_try_success_rate * 100).toFixed(0)}%`}
          />
          <StatCard
            icon={<Brain size={16} className="text-purple-500" />}
            label="提示依赖率"
            value={`${(profile.hint_dependency_rate * 100).toFixed(0)}%`}
          />
          <StatCard
            label="活跃时段"
            value={`${profile.peak_hour_start}:00 - ${profile.peak_hour_end}:00`}
          />
          <StatCard
            label="平均用时(简单)"
            value={profile.avg_solve_time_easy_ms > 0
              ? `${(profile.avg_solve_time_easy_ms / 60000).toFixed(1)} min`
              : '—'}
          />
        </div>
      </div>

      {/* AI 自适应建议 */}
      {adaptive && (
        <div className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-5">
          <div className="mb-3 flex items-center gap-2">
            <SparklesIcon />
            <h2 className="text-lg font-hand font-semibold text-journal-ink">AI 自适应建议</h2>
          </div>
          <p className="mb-3 text-sm text-journal-muted">{adaptive.reasoning}</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-journal-accentLight/20 p-3 text-center">
              <div className="text-lg font-bold text-journal-accent">{adaptive.quota_weekday}</div>
              <div className="text-xs text-journal-muted">工作日配额</div>
            </div>
            <div className="rounded-lg bg-journal-accentLight/20 p-3 text-center">
              <div className="text-lg font-bold text-journal-accent">{adaptive.quota_weekend}</div>
              <div className="text-xs text-journal-muted">周末配额</div>
            </div>
            <div className="rounded-lg bg-journal-accentLight/20 p-3 text-center">
              <div className="text-lg font-bold text-journal-accent">{(adaptive.new_ratio * 100).toFixed(0)}%</div>
              <div className="text-xs text-journal-muted">新题比例</div>
            </div>
            <div className="rounded-lg bg-journal-accentLight/20 p-3 text-center">
              <div className="text-lg font-bold text-journal-accent">{(adaptive.hard_ratio * 100).toFixed(0)}%</div>
              <div className="text-xs text-journal-muted">困难题比例</div>
            </div>
          </div>
        </div>
      )}

      {/* 偏好设置 */}
      <div className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-5">
        <div className="mb-4 flex items-center gap-2">
          <Settings size={20} className="text-journal-accent" />
          <h2 className="text-lg font-hand font-semibold text-journal-ink">偏好设置</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-journal-ink">难度偏好</label>
            <select
              value={profile.preferred_difficulty}
              onChange={e => updateMutation.mutate({ preferred_difficulty: e.target.value })}
              className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
            >
              <option value="easy">优先简单题</option>
              <option value="balanced">均衡分布</option>
              <option value="challenging">挑战困难题</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-journal-ink">自适应配额</div>
              <div className="text-xs text-journal-muted">AI 根据你的表现自动调整每日配额</div>
            </div>
            <button
              onClick={() => updateMutation.mutate({ adaptive_quota_enabled: !profile.adaptive_quota_enabled })}
              className={`relative h-6 w-11 rounded-full transition-colors ${
                profile.adaptive_quota_enabled ? 'bg-brand' : 'bg-surface-hover'
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                  profile.adaptive_quota_enabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-journal-ink">工作日配额</label>
              <input
                type="number"
                min={1}
                max={20}
                value={profile.custom_quota_weekday || 3}
                onChange={e => updateMutation.mutate({ custom_quota_weekday: Number(e.target.value) })}
                className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-journal-ink">周末配额</label>
              <input
                type="number"
                min={1}
                max={20}
                value={profile.custom_quota_weekend || 6}
                onChange={e => updateMutation.mutate({ custom_quota_weekend: Number(e.target.value) })}
                className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, sub }: { icon?: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg bg-journal-accentLight/20 p-3">
      <div className="mb-1 flex items-center gap-1.5">
        {icon}
        <span className="text-xs text-journal-muted">{label}</span>
      </div>
      <div className="text-lg font-bold text-journal-ink">{value}</div>
      {sub && <div className="text-xs text-journal-muted">{sub}</div>}
    </div>
  )
}

function SparklesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-journal-accent">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" />
    </svg>
  )
}
