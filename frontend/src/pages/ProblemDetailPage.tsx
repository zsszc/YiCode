import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ArrowLeft, Sparkles, BookOpen, Star, Clock, Lightbulb } from 'lucide-react'
import { problemsApi, tutorApi, reviewApi, profileApi } from '@/services/api'
import type { CodeReviewResponse } from '@/types'

export default function ProblemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const problemId = Number(id)

  const { data: problem, isLoading } = useQuery({
    queryKey: ['problem', problemId],
    queryFn: () => problemsApi.get(problemId),
  })

  const [hintLevel, setHintLevel] = useState(1)
  const [hintContent, setHintContent] = useState('')
  const [isHintLoading, setIsHintLoading] = useState(false)
  const [userCode, setUserCode] = useState('')
  const [reviewResult, setReviewResult] = useState<CodeReviewResponse | null>(null)
  const [isReviewLoading, setIsReviewLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'hint' | 'review'>('hint')

  const handleGetHint = async () => {
    setIsHintLoading(true)
    setHintContent('')
    try {
      await profileApi.recordBehavior(problemId, 'hint', { hint_level: hintLevel })
      const result = await tutorApi.hint(problemId, hintLevel)
      setHintContent(result.content)
    } finally {
      setIsHintLoading(false)
    }
  }

  const handleReviewCode = async () => {
    if (!userCode.trim()) return
    setIsReviewLoading(true)
    setReviewResult(null)
    try {
      const result = await tutorApi.reviewCode(problemId, userCode)
      setReviewResult(result)
    } finally {
      setIsReviewLoading(false)
    }
  }

  if (isLoading) return <div className="text-journal-muted">加载中...</div>
  if (!problem) return <div className="text-journal-danger">题目不存在</div>

  const diffColor = {
    简单: 'bg-green-100 text-green-700',
    中等: 'bg-yellow-100 text-yellow-700',
    困难: 'bg-red-100 text-red-700',
  }[problem.difficulty] || 'bg-gray-100 text-gray-700'

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* 左侧：题目信息 */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-center gap-2">
          <Link to="/problems" className="text-journal-muted hover:text-journal-ink">
            <ArrowLeft size={20} />
          </Link>
          <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${diffColor}`}>
            {problem.difficulty}
          </span>
          <span className="text-sm text-journal-muted">{problem.category}</span>
        </div>

        <h1 className="text-2xl font-hand font-bold text-journal-ink">
          #{problem.id} {problem.title}
        </h1>

        <div className="flex gap-3">
          <a
            href={`https://leetcode.cn/problems/${problem.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-journal-accentLight/40 px-4 py-2 text-sm font-medium text-journal-accent transition-colors hover:bg-journal-accentLight/60"
          >
            <BookOpen size={16} />
            去 LeetCode 刷题 →
          </a>
        </div>

        {/* 笔记区域 */}
        <div className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-4">
          <h3 className="mb-2 font-hand font-semibold text-journal-ink">📝 我的笔记</h3>
          <NoteEditor problemId={problemId} />
        </div>
      </div>

      {/* 右侧：AI Tutor 面板 */}
      <div className="space-y-4">
        <div className="rounded-xl border border-journal-accentLight/40 bg-journal-paper p-4">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles size={18} className="text-journal-accent" />
            <h3 className="font-hand font-semibold text-journal-ink">AI Tutor</h3>
          </div>

          {/* Tab 切换 */}
          <div className="mb-3 flex rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setActiveTab('hint')}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                activeTab === 'hint' ? 'bg-white text-journal-ink shadow-sm' : 'text-journal-muted'
              }`}
            >
              <Lightbulb size={14} className="mr-1 inline" />
              解题提示
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                activeTab === 'review' ? 'bg-white text-journal-ink shadow-sm' : 'text-journal-muted'
              }`}
            >
              <Star size={14} className="mr-1 inline" />
              代码审查
            </button>
          </div>

          {activeTab === 'hint' && (
            <div className="space-y-3">
              <div className="flex gap-1">
                {[1, 2, 3].map(level => (
                  <button
                    key={level}
                    onClick={() => setHintLevel(level)}
                    className={`flex-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                      hintLevel === level
                        ? 'bg-journal-accent text-white'
                        : 'bg-gray-100 text-journal-muted hover:bg-gray-200'
                    }`}
                  >
                    L{level}
                  </button>
                ))}
              </div>
              <p className="text-xs text-journal-muted">
                {hintLevel === 1 && '思路引导：只给方向'}
                {hintLevel === 2 && '算法框架：说明适用数据结构'}
                {hintLevel === 3 && '关键代码：提供核心逻辑'}
              </p>
              <button
                onClick={handleGetHint}
                disabled={isHintLoading}
                className="w-full rounded-lg bg-journal-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-journal-accent/90 disabled:opacity-50"
              >
                {isHintLoading ? '思考中...' : '获取提示'}
              </button>
              {hintContent && (
                <div className="rounded-lg bg-journal-accentLight/20 p-3 text-sm text-journal-ink whitespace-pre-wrap">
                  {hintContent}
                </div>
              )}
            </div>
          )}

          {activeTab === 'review' && (
            <div className="space-y-3">
              <textarea
                value={userCode}
                onChange={e => setUserCode(e.target.value)}
                placeholder="粘贴你的代码..."
                className="w-full rounded-lg border border-gray-200 bg-white p-3 font-mono text-xs text-journal-ink focus:border-journal-accent focus:outline-none"
                rows={8}
              />
              <button
                onClick={handleReviewCode}
                disabled={isReviewLoading || !userCode.trim()}
                className="w-full rounded-lg bg-journal-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-journal-accent/90 disabled:opacity-50"
              >
                {isReviewLoading ? '审查中...' : '代码审查'}
              </button>
              {reviewResult && (
                <div className="space-y-2 rounded-lg bg-journal-accentLight/20 p-3 text-sm">
                  <div className="flex items-center gap-1">
                    <Star size={14} className="text-yellow-500" />
                    <span className="font-medium">{'⭐'.repeat(reviewResult.rating)}</span>
                  </div>
                  <div className="flex gap-3 text-xs text-journal-muted">
                    <span><Clock size={12} className="mr-1 inline" />{reviewResult.time_complexity}</span>
                    <span>💾 {reviewResult.space_complexity}</span>
                  </div>
                  <p className="text-journal-ink">{reviewResult.overall_comment}</p>
                  {reviewResult.optimization_hints.length > 0 && (
                    <div className="rounded bg-yellow-50 p-2 text-xs">
                      <strong>优化建议：</strong>
                      {reviewResult.optimization_hints.map((h, i) => (
                        <p key={i}>• {h}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function NoteEditor({ problemId }: { problemId: number }) {
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState(false)

  const saveNote = useMutation({
    mutationFn: (content: string) => reviewApi.updateNote(problemId, content),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  return (
    <div className="space-y-2">
      <textarea
        value={note}
        onChange={e => setNote(e.target.value)}
        placeholder="记录解题思路、易错点..."
        className="w-full rounded-lg border border-gray-200 bg-white p-3 text-sm text-journal-ink focus:border-journal-accent focus:outline-none"
        rows={4}
      />
      <div className="flex items-center justify-between">
        <button
          onClick={() => saveNote.mutate(note)}
          className="rounded-lg bg-journal-accentLight/40 px-3 py-1.5 text-xs font-medium text-journal-accent transition-colors hover:bg-journal-accentLight/60"
        >
          保存笔记
        </button>
        {saved && <span className="text-xs text-green-600">已保存 ✓</span>}
      </div>
    </div>
  )
}
