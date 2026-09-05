import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Sparkles, Lightbulb, Star, Send, Loader2, X } from 'lucide-react'
import { tutorApi, profileApi } from '@/services/api'
import type { ChatMsg, CodeReviewResponse } from '@/types'

interface Props {
  problemId: number
  problemTitle: string
  getCode: () => string
  onClose: () => void
}

export default function TutorPanel({ problemId, problemTitle, getCode, onClose }: Props) {
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: 'assistant',
      content: `你好！我是你的 AI 刷题导师 🐇\n\n我们正在攻克 **#${problemId} ${problemTitle}**。你可以：\n- 点击下方「解题提示」逐级获取思路\n- 直接问我任何问题（比如"这题怎么做"、"帮我看看代码"）\n- 写完代码后点「审查代码」让我点评`,
    },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const push = (msg: ChatMsg) => setMessages(prev => [...prev, msg])

  /** 向最后一条 assistant 消息追加文本（流式打字机） */
  const appendToLast = (chunk: string) =>
    setMessages(prev => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content: last.content + chunk }
      }
      return next
    })

  const sendChat = async (text: string) => {
    if (!text.trim() || busy) return
    const userMsg: ChatMsg = { role: 'user', content: text.trim() }
    push(userMsg)
    setInput('')
    setBusy(true)
    // 先放一条空的 assistant 消息，流式往里填
    push({ role: 'assistant', content: '' })
    try {
      const history = [...messages, userMsg].slice(-10)
      await tutorApi.chatStream(
        problemId,
        userMsg.content,
        history,
        getCode() || undefined,
        chunk => appendToLast(chunk),
      )
    } catch (e) {
      appendToLast(`⚠️ ${e instanceof Error ? e.message : '请求失败，请确认后端服务已启动后重试。'}`)
    } finally {
      setBusy(false)
    }
  }

  const getHint = async (level: number) => {
    if (busy) return
    push({ role: 'user', content: `给我 L${level} 级别的提示` })
    setBusy(true)
    // 先放占位气泡，流式往里填
    push({ role: 'assistant', content: `**💡 L${level} 提示**\n\n` })
    try {
      await profileApi.recordBehavior(problemId, 'hint', { hint_level: level })
      await tutorApi.hintStream(problemId, level, chunk => appendToLast(chunk))
    } catch (e) {
      appendToLast(`\n\n⚠️ ${e instanceof Error ? e.message : '获取提示失败，请确认后端服务已启动。'}`)
    } finally {
      setBusy(false)
    }
  }

  const reviewMyCode = async () => {
    const code = getCode()
    if (busy) return
    if (!code.trim() || code.includes('pass\n')) {
      push({ role: 'assistant', content: '你还没怎么写代码呢～先在编辑器里写出你的解法，再来找我审查吧。' })
      return
    }
    push({ role: 'user', content: '帮我审查一下当前代码' })
    setBusy(true)
    try {
      const r: CodeReviewResponse = await tutorApi.reviewCode(problemId, code)
      const lines = [
        `**⭐ 评分：${r.rating}/5**`,
        `- ⏱ 时间复杂度：\`${r.time_complexity}\``,
        `- 💾 空间复杂度：\`${r.space_complexity}\``,
        '',
        r.overall_comment,
      ]
      if (r.optimization_hints.length)
        lines.push('', '**优化建议**', ...r.optimization_hints.map(h => `- ${h}`))
      if (r.style_suggestions.length)
        lines.push('', '**风格建议**', ...r.style_suggestions.map(s => `- ${s}`))
      push({ role: 'assistant', content: lines.join('\n') })
    } catch {
      push({ role: 'assistant', content: '⚠️ 代码审查失败，请确认后端服务已启动。' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col border-l border-line bg-surface">
      {/* 头部 */}
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-dim">
            <Sparkles size={15} className="text-brand-light" />
          </span>
          <span className="text-sm font-semibold text-white">AI Tutor</span>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-journal-muted transition-colors hover:bg-surface-hover hover:text-white"
        >
          <X size={16} />
        </button>
      </div>

      {/* 消息列表 */}
      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm ${
                m.role === 'user'
                  ? 'rounded-br-sm bg-brand text-white'
                  : 'rounded-bl-sm border border-line bg-surface-raised'
              }`}
            >
              {m.role === 'assistant' ? (
                <div className="prose-dark">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                  {busy && i === messages.length - 1 && m.content !== '' && (
                    <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse rounded-sm bg-brand-light align-text-bottom" />
                  )}
                </div>
              ) : (
                <span className="whitespace-pre-wrap">{m.content}</span>
              )}
            </div>
          </div>
        ))}
        {busy && (messages[messages.length - 1]?.role !== 'assistant' || messages[messages.length - 1]?.content === '') && (
          <div className="flex items-center gap-2 text-xs text-journal-muted">
            <Loader2 size={14} className="animate-spin text-brand-light" />
            AI 正在思考...
          </div>
        )}
      </div>

      {/* 快捷操作 */}
      <div className="flex flex-wrap gap-1.5 border-t border-line px-3 pt-2.5">
        {[1, 2, 3].map(l => (
          <button
            key={l}
            onClick={() => getHint(l)}
            disabled={busy}
            className="flex items-center gap-1 rounded-full border border-line bg-surface-raised px-2.5 py-1 text-xs text-journal-muted transition-colors hover:border-brand/40 hover:text-brand-light disabled:opacity-50"
          >
            <Lightbulb size={12} />
            提示 L{l}
          </button>
        ))}
        <button
          onClick={reviewMyCode}
          disabled={busy}
          className="flex items-center gap-1 rounded-full border border-line bg-surface-raised px-2.5 py-1 text-xs text-journal-muted transition-colors hover:border-brand/40 hover:text-brand-light disabled:opacity-50"
        >
          <Star size={12} />
          审查代码
        </button>
      </div>

      {/* 输入框 */}
      <div className="flex items-end gap-2 p-3">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendChat(input)
            }
          }}
          placeholder="向 AI 导师提问...（Enter 发送）"
          rows={2}
          className="flex-1 resize-none rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink outline-none transition-colors placeholder:text-journal-muted/60 focus:border-brand"
        />
        <button
          onClick={() => sendChat(input)}
          disabled={busy || !input.trim()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand text-white transition-colors hover:bg-brand/90 disabled:opacity-40"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}
