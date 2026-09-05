import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookMarked, Eye, EyeOff, Copy, Check, Zap, Target, AlertTriangle, ExternalLink } from 'lucide-react'
import { templatesApi, problemsApi } from '@/services/api'
import type { TemplateSummary } from '@/types'

export default function TemplatesPage() {
  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: templatesApi.list,
  })
  const [activeSlug, setActiveSlug] = useState<string | null>(null)
  const active = templates?.find(t => t.slug === activeSlug) ?? templates?.[0] ?? null

  return (
    <div className="flex gap-0 -mx-4 -my-5" style={{ height: 'calc(100vh - 3.5rem)' }}>
      {/* 左栏：模板列表 */}
      <div className="flex w-[320px] shrink-0 flex-col border-r border-line">
        <div className="border-b border-line px-4 py-3.5">
          <h1 className="flex items-center gap-2 text-base font-bold text-white">
            <BookMarked size={17} className="text-brand-light" />
            模板速记
          </h1>
          <p className="mt-1 text-xs leading-5 text-journal-muted">
            面试突击专用：背熟 {templates?.length ?? ''} 个高频模板，覆盖 80% 的面试题型
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {isLoading && <div className="py-10 text-center text-xs text-journal-muted">加载中...</div>}
          {templates?.map(t => (
            <TemplateCard
              key={t.slug}
              tpl={t}
              active={active?.slug === t.slug}
              onClick={() => setActiveSlug(t.slug)}
            />
          ))}
        </div>
      </div>

      {/* 右栏：模板详情 */}
      <div className="min-w-0 flex-1 overflow-y-auto">
        {active ? <TemplateDetailView slug={active.slug} /> : null}
      </div>
    </div>
  )
}

function TemplateCard({ tpl, active, onClick }: { tpl: TemplateSummary; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`mb-1.5 w-full rounded-xl border p-3 text-left transition-all ${
        active
          ? 'border-brand/50 bg-brand-dim/60 shadow-glow'
          : 'border-line bg-surface hover:border-brand/30 hover:bg-surface-hover'
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={`text-sm font-semibold ${active ? 'text-brand-light' : 'text-white'}`}>
          {tpl.name}
        </span>
        <span className="rounded-full bg-black/30 px-2 py-0.5 text-[10px] text-journal-muted">
          {tpl.problem_ids.length} 题
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-xs leading-5 text-journal-muted">{tpl.scenario}</p>
    </button>
  )
}

function TemplateDetailView({ slug }: { slug: string }) {
  const { data: tpl } = useQuery({
    queryKey: ['template', slug],
    queryFn: () => templatesApi.get(slug),
  })
  // 关联题目（拿标题）
  const { data: problems } = useQuery({
    queryKey: ['problems-all'],
    queryFn: () => problemsApi.list(),
    staleTime: 60_000,
  })
  const [revealed, setRevealed] = useState(true)
  const [copied, setCopied] = useState(false)

  if (!tpl) return <div className="py-20 text-center text-xs text-journal-muted">加载中...</div>

  const related = (tpl.problem_ids ?? [])
    .map(id => problems?.find(p => p.id === id))
    .filter(Boolean)

  const copyCode = async () => {
    await navigator.clipboard.writeText(tpl.code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      {/* 头部 */}
      <div className="mb-5">
        <h2 className="text-xl font-bold text-white">{tpl.name}</h2>
        <p className="mt-1.5 flex items-start gap-1.5 text-sm text-journal-muted">
          <Target size={14} className="mt-1 shrink-0 text-brand-light" />
          {tpl.scenario}
        </p>
      </div>

      {/* 记忆口诀 */}
      <div className="mb-5 rounded-xl border border-brand/30 bg-gradient-to-r from-brand-dim/70 to-transparent px-4 py-3">
        <div className="flex items-center gap-2">
          <Zap size={14} className="shrink-0 text-brand-light" />
          <span className="text-xs font-medium text-brand-light">记忆口诀</span>
        </div>
        <p className="mt-1.5 font-hand text-lg text-white">{tpl.mnemonic}</p>
      </div>

      {/* 模板代码（支持遮挡背诵模式） */}
      <div className="mb-5 overflow-hidden rounded-xl border border-line bg-black/40">
        <div className="flex items-center justify-between border-b border-line px-4 py-2">
          <span className="font-mono text-xs text-journal-muted">template.py</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setRevealed(v => !v)}
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                revealed
                  ? 'text-journal-muted hover:bg-surface-hover hover:text-white'
                  : 'bg-brand-dim text-brand-light'
              }`}
              title={revealed ? '遮住代码，默写自测' : '显示代码'}
            >
              {revealed ? <EyeOff size={13} /> : <Eye size={13} />}
              {revealed ? '遮挡默写' : '已遮挡 · 点击显示'}
            </button>
            <button
              onClick={copyCode}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-journal-muted transition-colors hover:bg-surface-hover hover:text-white"
            >
              {copied ? <Check size={13} className="text-easy" /> : <Copy size={13} />}
              {copied ? '已复制' : '复制'}
            </button>
          </div>
        </div>
        <div className="relative">
          <pre
            className={`overflow-x-auto p-4 font-mono text-[13px] leading-6 text-journal-ink transition-all duration-300 ${
              revealed ? '' : 'select-none blur-md'
            }`}
          >
            {tpl.code}
          </pre>
          {!revealed && (
            <button
              onClick={() => setRevealed(true)}
              className="absolute inset-0 flex items-center justify-center"
            >
              <span className="rounded-lg border border-brand/40 bg-journal-bg/80 px-4 py-2 text-xs font-medium text-brand-light backdrop-blur-sm">
                🧠 先在脑中默写一遍，点击核对
              </span>
            </button>
          )}
        </div>
      </div>

      {/* 易错点 */}
      <div className="mb-5 rounded-xl border border-line bg-surface p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle size={14} className="text-medium" />
          <span className="text-sm font-semibold text-white">易错点</span>
        </div>
        <ul className="mt-2.5 space-y-2">
          {tpl.key_points.map((p, i) => (
            <li key={i} className="flex items-start gap-2 text-[13px] leading-5 text-journal-ink">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-medium" />
              {p}
            </li>
          ))}
        </ul>
      </div>

      {/* 关联题目 */}
      {related.length > 0 && (
        <div className="rounded-xl border border-line bg-surface p-4">
          <div className="text-sm font-semibold text-white">🎯 背完去练（{related.length} 题）</div>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {related.map(p => (
              <Link
                key={p!.id}
                to={`/problems/${p!.id}`}
                className="group flex items-center gap-1.5 rounded-lg border border-line bg-journal-bg px-3 py-1.5 text-xs text-journal-ink transition-colors hover:border-brand/40 hover:text-brand-light"
              >
                <span className="font-mono text-journal-muted">#{p!.id}</span>
                {p!.title}
                <ExternalLink size={11} className="opacity-0 transition-opacity group-hover:opacity-60" />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
