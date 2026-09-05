import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { linter, lintGutter } from '@codemirror/lint'
import type { Diagnostic as CMDiagnostic } from '@codemirror/lint'
import ReactMarkdown from 'react-markdown'
import {
  ArrowLeft,
  Play,
  FlaskConical,
  Sparkles,
  RotateCcw,
  CheckCircle2,
  XCircle,
  StickyNote,
  FileText,
  Terminal,
  PartyPopper,
  Wand2,
} from 'lucide-react'
import { problemsApi, reviewApi, codeApi, profileApi } from '@/services/api'
import type { CodeRunResponse, RunTestsResponse } from '@/types'
import TutorPanel from '@/components/TutorPanel'
import { aiCompletion } from '@/editor/aiCompletion'

const DIFF_STYLE: Record<string, string> = {
  简单: 'text-easy bg-easy/10 border-easy/25',
  中等: 'text-medium bg-medium/10 border-medium/25',
  困难: 'text-hard bg-hard/10 border-hard/25',
}

export default function ProblemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const problemId = Number(id)
  const storageKey = `yicode_code_${problemId}`

  const { data: problem, isLoading } = useQuery({
    queryKey: ['problem', problemId],
    queryFn: () => problemsApi.get(problemId),
  })

  const [code, setCode] = useState('')
  const [leftTab, setLeftTab] = useState<'desc' | 'note'>('desc')
  const [consoleTab, setConsoleTab] = useState<'tests' | 'output'>('tests')
  const [runResult, setRunResult] = useState<CodeRunResponse | null>(null)
  const [judgeResult, setJudgeResult] = useState<RunTestsResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [searchParams] = useSearchParams()
  const [tutorOpen, setTutorOpen] = useState(searchParams.get('tutor') === '1')
  const [solved, setSolved] = useState(false)
  const [aiCompleteOn, setAiCompleteOn] = useState(
    () => localStorage.getItem('yicode_ai_complete') === '1',
  )
  const aiCompleteRef = useRef(aiCompleteOn)
  aiCompleteRef.current = aiCompleteOn

  const toggleAiComplete = () => {
    setAiCompleteOn(v => {
      localStorage.setItem('yicode_ai_complete', v ? '0' : '1')
      return !v
    })
  }

  // 静态诊断：波浪线 + hover 报错（后端 AST 分析，700ms 防抖由 linter 内置）
  const lintExtension = useMemo(
    () => [
      linter(
        async (view): Promise<CMDiagnostic[]> => {
          try {
            const diags = await codeApi.lint(view.state.doc.toString())
            const doc = view.state.doc
            return diags.map(d => {
              const fromLine = doc.line(Math.min(d.line, doc.lines))
              const toLine = doc.line(Math.min(d.end_line, doc.lines))
              const from = Math.min(fromLine.from + d.col, fromLine.to)
              const to = Math.max(from + 1, Math.min(toLine.from + d.end_col, toLine.to))
              return { from, to, severity: d.severity, message: d.message }
            })
          } catch {
            return []
          }
        },
        { delay: 700 },
      ),
      lintGutter(),
    ],
    [],
  )

  // AI 内联补全（ghost text，Tab 接受 / Esc 拒绝）
  const completionExtension = useMemo(
    () =>
      aiCompletion({
        enabled: () => aiCompleteRef.current,
        fetchCompletion: (code, line, col) => codeApi.complete(code, line, col, problemId),
      }),
    [problemId],
  )

  // 初始化代码：优先本地草稿，否则用模板
  useEffect(() => {
    if (!problem) return
    const draft = localStorage.getItem(storageKey)
    setCode(draft ?? problem.starter_code ?? '# 在这里编写你的解法\n')
    setJudgeResult(null)
    setRunResult(null)
    setSolved(false)
  }, [problem, storageKey])

  const updateCode = (v: string) => {
    setCode(v)
    localStorage.setItem(storageKey, v)
  }

  const resetCode = () => {
    if (!problem?.starter_code) return
    if (!window.confirm('确定重置为初始代码模板？当前代码将被清除。')) return
    updateCode(problem.starter_code)
  }

  const handleRun = async () => {
    setRunning(true)
    setConsoleTab('output')
    try {
      const r = await codeApi.run(code)
      setRunResult(r)
    } catch {
      setRunResult({ stdout: '', stderr: '请求失败：请确认后端服务已启动', exit_code: -1, duration_ms: 0, timed_out: false })
    } finally {
      setRunning(false)
    }
  }

  const handleJudge = async () => {
    setRunning(true)
    setConsoleTab('tests')
    setJudgeResult(null)
    try {
      const r = await codeApi.runTests(problemId, code)
      setJudgeResult(r)
      if (r.total > 0 && r.passed === r.total) {
        setSolved(true)
        profileApi.recordBehavior(problemId, 'judge_pass', { duration_ms: r.duration_ms }).catch(() => {})
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? '判题请求失败，请确认后端服务已启动'
      setJudgeResult({ passed: 0, total: 0, cases: [], stdout: '', stderr: String(msg), duration_ms: 0, timed_out: false, sandbox_blocked: false })
    } finally {
      setRunning(false)
    }
  }

  const hasTests = useMemo(() => {
    if (!problem?.test_cases) return false
    try {
      return (JSON.parse(problem.test_cases).tests ?? []).length > 0
    } catch {
      return false
    }
  }, [problem])

  if (isLoading) return <div className="py-20 text-center text-journal-muted">加载中...</div>
  if (!problem) return <div className="py-20 text-center text-journal-danger">题目不存在</div>

  return (
    <div className="flex gap-0 -mx-4 -my-5" style={{ height: 'calc(100vh - 3.5rem)' }}>
      {/* 左栏：描述 / 笔记 */}
      <div className="flex w-[42%] min-w-[380px] flex-col border-r border-line">
        <div className="border-b border-line px-4 pt-3">
          <div className="flex items-center gap-2 pb-3">
            <Link to="/problems" className="rounded-md p-1 text-journal-muted transition-colors hover:bg-surface-hover hover:text-white">
              <ArrowLeft size={17} />
            </Link>
            <span className={`rounded-md border px-2 py-0.5 text-xs font-medium ${DIFF_STYLE[problem.difficulty]}`}>
              {problem.difficulty}
            </span>
            <span className="text-xs text-journal-muted">{problem.category}</span>
          </div>
          <h1 className="pb-3 text-lg font-bold text-white">
            <span className="mr-1.5 font-mono text-journal-muted">#{problem.id}</span>
            {problem.title}
          </h1>
          <div className="flex gap-1">
            <TabButton active={leftTab === 'desc'} onClick={() => setLeftTab('desc')} icon={<FileText size={14} />} label="题目描述" />
            <TabButton active={leftTab === 'note'} onClick={() => setLeftTab('note')} icon={<StickyNote size={14} />} label="我的笔记" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {leftTab === 'desc' ? (
            <div className="prose-dark">
              <ReactMarkdown>{problem.description || '本题题面整理中，可以先看右侧代码模板动手尝试，或问 AI Tutor 获取题目讲解。'}</ReactMarkdown>
            </div>
          ) : (
            <NoteEditor problemId={problemId} />
          )}
        </div>
      </div>

      {/* 中栏：编辑器 + 控制台 */}
      <div className="flex flex-1 flex-col">
        {/* 工具栏 */}
        <div className="flex items-center justify-between border-b border-line px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="rounded-md border border-line bg-surface px-2 py-1 font-mono text-xs text-journal-muted">Python 3</span>
            <button
              onClick={resetCode}
              title="重置为模板"
              className="rounded-md p-1.5 text-journal-muted transition-colors hover:bg-surface-hover hover:text-white"
            >
              <RotateCcw size={14} />
            </button>
            <button
              onClick={toggleAiComplete}
              title={aiCompleteOn ? 'AI 补全已开启（Tab 接受建议）' : '开启 AI 自动补全'}
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                aiCompleteOn
                  ? 'bg-brand-dim text-brand-light'
                  : 'text-journal-muted hover:bg-surface-hover hover:text-white'
              }`}
            >
              <Wand2 size={13} />
              补全{aiCompleteOn ? '开' : '关'}
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-journal-ink transition-colors hover:bg-surface-hover disabled:opacity-50"
            >
              <Play size={13} />
              运行
            </button>
            <button
              onClick={handleJudge}
              disabled={running || !hasTests}
              title={hasTests ? '运行全部测试用例' : '本题暂无自动判题'}
              className="flex items-center gap-1.5 rounded-lg bg-easy/90 px-3 py-1.5 text-xs font-semibold text-black transition-colors hover:bg-easy disabled:opacity-40"
            >
              <FlaskConical size={13} />
              提交判题
            </button>
            <button
              onClick={() => setTutorOpen(v => !v)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                tutorOpen
                  ? 'bg-brand text-white shadow-glow'
                  : 'bg-brand-dim text-brand-light hover:bg-brand/30'
              }`}
            >
              <Sparkles size={13} />
              AI Tutor
            </button>
          </div>
        </div>

        {/* 编辑器 */}
        <div className="min-h-0 flex-1 overflow-hidden bg-[#0d1017]">
          <CodeMirror
            value={code}
            onChange={updateCode}
            extensions={[python(), lintExtension, completionExtension]}
            theme="dark"
            height="100%"
            style={{ height: '100%' }}
            basicSetup={{ lineNumbers: true, autocompletion: true, foldGutter: true }}
          />
        </div>

        {/* 控制台 */}
        <div className="flex h-[34%] min-h-[180px] flex-col border-t border-line">
          <div className="flex items-center gap-1 border-b border-line px-3 py-1.5">
            <TabButton active={consoleTab === 'tests'} onClick={() => setConsoleTab('tests')} icon={<FlaskConical size={13} />} label="测试结果" />
            <TabButton active={consoleTab === 'output'} onClick={() => setConsoleTab('output')} icon={<Terminal size={13} />} label="运行输出" />
            {judgeResult && consoleTab === 'tests' && judgeResult.total > 0 && (
              <span className={`ml-auto text-xs font-medium ${judgeResult.passed === judgeResult.total ? 'text-easy' : 'text-hard'}`}>
                通过 {judgeResult.passed}/{judgeResult.total} · {judgeResult.duration_ms}ms
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {consoleTab === 'tests' ? (
              <JudgeView result={judgeResult} running={running} hasTests={hasTests} />
            ) : (
              <OutputView result={runResult} running={running} />
            )}
          </div>
        </div>

        {/* 全部通过后：标记掌握 */}
        {solved && (
          <SolvedBar problemId={problemId} onDone={() => setSolved(false)} />
        )}
      </div>

      {/* 右栏：AI Tutor */}
      {tutorOpen && (
        <div className="w-[380px] shrink-0">
          <TutorPanel
            problemId={problemId}
            problemTitle={problem.title}
            getCode={() => code}
            onClose={() => setTutorOpen(false)}
          />
        </div>
      )}
    </div>
  )
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
        active ? 'bg-brand-dim text-brand-light' : 'text-journal-muted hover:text-journal-ink'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

function JudgeView({ result, running, hasTests }: { result: RunTestsResponse | null; running: boolean; hasTests: boolean }) {
  if (running && !result) return <div className="py-6 text-center text-xs text-journal-muted">判题中...</div>
  if (!result) {
    return (
      <div className="py-6 text-center text-xs text-journal-muted">
        {hasTests ? '点击「提交判题」运行全部测试用例' : '本题暂不支持自动判题，可用「运行」自由调试'}
      </div>
    )
  }
  if (result.sandbox_blocked || (result.total === 0 && result.stderr)) {
    return (
      <div className="rounded-lg border border-hard/30 bg-hard/10 p-3">
        <p className="text-xs font-medium text-hard">运行被拦截或出错</p>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-xs text-journal-ink">{result.stderr}</pre>
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {result.passed === result.total && result.total > 0 ? (
        <div className="flex items-center gap-2 rounded-lg border border-easy/30 bg-easy/10 px-3 py-2 text-sm font-medium text-easy">
          <PartyPopper size={16} />
          全部通过！太棒了
        </div>
      ) : null}
      {result.cases.map((c, i) => (
        <div
          key={i}
          className={`rounded-lg border p-3 ${c.ok ? 'border-line bg-surface' : 'border-hard/40 bg-hard/5'}`}
        >
          <div className="flex items-center gap-2 text-xs font-medium">
            {c.ok ? <CheckCircle2 size={14} className="text-easy" /> : <XCircle size={14} className="text-hard" />}
            <span className={c.ok ? 'text-easy' : 'text-hard'}>用例 {i + 1}</span>
          </div>
          <div className="mt-1.5 space-y-1 font-mono text-xs">
            <p className="text-journal-muted">输入: <span className="text-journal-ink">{c.input}</span></p>
            {!c.ok && (
              <>
                <p className="text-journal-muted">期望: <span className="text-easy">{c.expected}</span></p>
                <p className="text-journal-muted">实际: <span className="text-hard">{c.actual}</span></p>
              </>
            )}
          </div>
        </div>
      ))}
      {result.stderr && result.cases.length > 0 === false && (
        <pre className="whitespace-pre-wrap font-mono text-xs text-hard">{result.stderr}</pre>
      )}
      {result.stderr && result.cases.length === 0 && (
        <pre className="whitespace-pre-wrap font-mono text-xs text-hard">{result.stderr}</pre>
      )}
    </div>
  )
}

function OutputView({ result, running }: { result: CodeRunResponse | null; running: boolean }) {
  if (running && !result) return <div className="py-6 text-center text-xs text-journal-muted">运行中...</div>
  if (!result) return <div className="py-6 text-center text-xs text-journal-muted">点击「运行」执行代码（可在代码中用 print 输出调试信息）</div>
  return (
    <div className="space-y-2 font-mono text-xs">
      {result.stdout && (
        <pre className="whitespace-pre-wrap rounded-lg border border-line bg-black/40 p-3 text-journal-ink">{result.stdout}</pre>
      )}
      {result.stderr && (
        <pre className="whitespace-pre-wrap rounded-lg border border-hard/30 bg-hard/10 p-3 text-hard">{result.stderr}</pre>
      )}
      <p className="text-journal-muted">
        退出码 {result.exit_code} · {result.duration_ms}ms{result.timed_out ? ' · 已超时终止' : ''}
      </p>
    </div>
  )
}

function SolvedBar({ problemId, onDone }: { problemId: number; onDone: () => void }) {
  const mark = useMutation({
    mutationFn: (status: 'forgot' | 'shaky' | 'solid') => reviewApi.firstSolve(problemId, status),
    onSuccess: onDone,
  })
  return (
    <div className="flex items-center justify-between border-t border-easy/30 bg-easy/10 px-4 py-2.5">
      <span className="text-xs font-medium text-easy">🎉 全部用例通过！记录一下这次的掌握程度：</span>
      <div className="flex gap-2">
        {([
          ['solid', '😄 秒A', 'bg-easy/20 text-easy hover:bg-easy/30'],
          ['shaky', '🙂 磕绊', 'bg-medium/20 text-medium hover:bg-medium/30'],
          ['forgot', '😩 卡住', 'bg-hard/20 text-hard hover:bg-hard/30'],
        ] as const).map(([status, label, cls]) => (
          <button
            key={status}
            onClick={() => mark.mutate(status)}
            disabled={mark.isPending}
            className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${cls}`}
          >
            {label}
          </button>
        ))}
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
        placeholder="记录解题思路、易错点、复杂度分析..."
        className="h-56 w-full resize-none rounded-lg border border-line bg-journal-bg p-3 text-sm text-journal-ink outline-none transition-colors placeholder:text-journal-muted/60 focus:border-brand"
      />
      <div className="flex items-center justify-between">
        <button
          onClick={() => saveNote.mutate(note)}
          disabled={saveNote.isPending}
          className="rounded-lg bg-brand px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand/90 disabled:opacity-50"
        >
          保存笔记
        </button>
        {saved && <span className="text-xs text-easy">已保存 ✓</span>}
      </div>
    </div>
  )
}
