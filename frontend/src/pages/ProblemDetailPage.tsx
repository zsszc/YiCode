import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { keymap } from '@codemirror/view'
import { indentUnit } from '@codemirror/language'
import { indentWithTab } from '@codemirror/commands'
import { linter, lintGutter } from '@codemirror/lint'
import type { Diagnostic as CMDiagnostic } from '@codemirror/lint'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
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
  Code2,
  TerminalSquare,
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

type CodeMode = 'function' | 'acm'

const ACM_DEFAULT_CODE = `# ACM 模式：自己用 input() 读入、print() 输出
n = int(input())
arr = list(map(int, input().split()))
`

export default function ProblemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const problemId = Number(id)
  const [mode, setMode] = useState<CodeMode>(
    () => (localStorage.getItem(`yicode_mode_${problemId}`) === 'acm' ? 'acm' : 'function'),
  )
  const storageKey = `yicode_code_${problemId}_${mode}`

  const { data: problem, isLoading } = useQuery({
    queryKey: ['problem', problemId],
    queryFn: () => problemsApi.get(problemId),
  })

  const queryClient = useQueryClient()

  // 全量题目 id 列表（上一题/下一题导航用）
  const { data: allProblems } = useQuery({
    queryKey: ['problems', 'all-ids'],
    queryFn: () => problemsApi.list(),
    staleTime: 60_000,
  })
  const { prevId, nextId } = useMemo(() => {
    if (!allProblems) return { prevId: undefined, nextId: undefined } as const
    const idx = allProblems.findIndex(p => p.id === problemId)
    return {
      prevId: idx > 0 ? allProblems[idx - 1].id : undefined,
      nextId: idx >= 0 && idx < allProblems.length - 1 ? allProblems[idx + 1].id : undefined,
    }
  }, [allProblems, problemId])

  // 切换题目（上一题/下一题）时恢复该题的模式选择
  useEffect(() => {
    setMode(localStorage.getItem(`yicode_mode_${problemId}`) === 'acm' ? 'acm' : 'function')
  }, [problemId])

  const [code, setCode] = useState('')
  const [stdin, setStdin] = useState('')
  const [leftTab, setLeftTab] = useState<'desc' | 'note'>('desc')
  const [consoleTab, setConsoleTab] = useState<'tests' | 'output' | 'stdin'>('tests')
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

  // 静态扩展必须记忆化：每次渲染新建实例会导致编辑器重配置，
  // ghost text 的 StateField 被重置，表现为「幽灵文本在但 Tab 接受了缩进」
  const staticExtensions = useMemo(
    () => [python(), indentUnit.of('    '), keymap.of([indentWithTab])],
    [],
  )

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

  // 解析 ACM 模式资源（变式题自带 acm_starter / io_tests）
  const acmSpec = useMemo(() => {
    if (!problem?.test_cases) return { starter: '', hasIoTests: false }
    try {
      const spec = JSON.parse(problem.test_cases)
      const io = Array.isArray(spec.io_tests) ? spec.io_tests : []
      return { starter: spec.acm_starter ?? '', hasIoTests: io.length > 0 }
    } catch {
      return { starter: '', hasIoTests: false }
    }
  }, [problem])

  const starterFor = (m: CodeMode) =>
    m === 'acm'
      ? acmSpec.starter || ACM_DEFAULT_CODE
      : problem?.starter_code ?? '# 在这里编写你的解法\n'

  // 初始化代码：优先本地草稿（按模式分开存），否则用对应模式的模板
  useEffect(() => {
    if (!problem) return
    const draft = localStorage.getItem(storageKey)
    setCode(draft ?? starterFor(mode))
    setJudgeResult(null)
    setRunResult(null)
    setSolved(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problem, storageKey, mode])

  const switchMode = (m: CodeMode) => {
    if (m === mode) return
    localStorage.setItem(`yicode_mode_${problemId}`, m)
    setMode(m) // 草稿按模式分开存，切换不会丢代码
    if (m === 'function') setConsoleTab(t => (t === 'stdin' ? 'tests' : t))
  }

  const updateCode = (v: string) => {
    setCode(v)
    localStorage.setItem(storageKey, v)
  }

  const resetCode = () => {
    if (!window.confirm('确定重置为初始代码模板？当前代码将被清除。')) return
    updateCode(starterFor(mode))
  }

  const handleRun = async () => {
    setRunning(true)
    setConsoleTab('output')
    try {
      const r = await codeApi.run(code, mode === 'acm' ? stdin : undefined)
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
    setSolved(false) // 重新判题时先收起上次的通过记录条
    try {
      const r = await codeApi.runTests(problemId, code, mode)
      setJudgeResult(r)
      if (r.total > 0 && r.passed === r.total) {
        setSolved(true)
        profileApi.recordBehavior(problemId, 'judge_pass', { duration_ms: r.duration_ms }).catch(() => {})
        // 全部通过自动记一条进度（默认「磕绊」，可在下方结果条上修正），让题库/看板进度即时更新
        reviewApi.firstSolve(problemId, 'shaky')
          .then(() => {
            queryClient.invalidateQueries({ queryKey: ['problems'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          })
          .catch(() => {})
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
      const spec = JSON.parse(problem.test_cases)
      if (mode === 'acm') return (spec.io_tests ?? []).length > 0
      return (spec.tests ?? []).length > 0
    } catch {
      return false
    }
  }, [problem, mode])

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
            {/* 上一题 / 下一题 */}
            <div className="flex items-center rounded-md border border-line">
              {prevId ? (
                <Link to={`/problems/${prevId}`} title="上一题" className="p-1 text-journal-muted transition-colors hover:bg-surface-hover hover:text-white">
                  <ChevronLeft size={15} />
                </Link>
              ) : (
                <span className="p-1 text-journal-muted/30"><ChevronLeft size={15} /></span>
              )}
              <span className="h-4 w-px bg-line" />
              {nextId ? (
                <Link to={`/problems/${nextId}`} title="下一题" className="p-1 text-journal-muted transition-colors hover:bg-surface-hover hover:text-white">
                  <ChevronRight size={15} />
                </Link>
              ) : (
                <span className="p-1 text-journal-muted/30"><ChevronRight size={15} /></span>
              )}
            </div>
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
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{problem.description || '本题题面整理中，可以先看右侧代码模板动手尝试，或问 AI Tutor 获取题目讲解。'}</ReactMarkdown>
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
            {/* 模式切换：核心代码 / ACM */}
            <div className="flex rounded-lg border border-line bg-surface p-0.5">
              <button
                onClick={() => switchMode('function')}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  mode === 'function' ? 'bg-brand text-white' : 'text-journal-muted hover:text-journal-ink'
                }`}
              >
                <Code2 size={12} />
                核心代码
              </button>
              <button
                onClick={() => switchMode('acm')}
                title={acmSpec.hasIoTests ? 'ACM 模式：自己读输入、写输出' : 'ACM 模式（本题暂无 ACM 判题用例，可自由调试）'}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  mode === 'acm' ? 'bg-brand text-white' : 'text-journal-muted hover:text-journal-ink'
                }`}
              >
                <TerminalSquare size={12} />
                ACM
              </button>
            </div>
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
            extensions={[...staticExtensions, lintExtension, completionExtension]}
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
            {mode === 'acm' && (
              <TabButton active={consoleTab === 'stdin'} onClick={() => setConsoleTab('stdin')} icon={<TerminalSquare size={13} />} label="自定义输入" />
            )}
            {judgeResult && consoleTab === 'tests' && judgeResult.total > 0 && (
              <span className={`ml-auto text-xs font-medium ${judgeResult.passed === judgeResult.total ? 'text-easy' : 'text-hard'}`}>
                通过 {judgeResult.passed}/{judgeResult.total} · {judgeResult.duration_ms}ms
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {consoleTab === 'stdin' && mode === 'acm' ? (
              <div className="flex h-full flex-col gap-2">
                <p className="text-xs text-journal-muted">
                  ACM 模式的自定义标准输入（点「运行」时作为 stdin 传给程序；「提交判题」使用内置用例）：
                </p>
                <textarea
                  value={stdin}
                  onChange={e => setStdin(e.target.value)}
                  spellCheck={false}
                  placeholder={'例如：\n3\n1 2 3'}
                  className="min-h-0 flex-1 resize-none rounded-lg border border-line bg-black/40 p-3 font-mono text-xs text-journal-ink outline-none placeholder:text-journal-muted/50 focus:border-brand"
                />
              </div>
            ) : consoleTab === 'tests' ? (
              <JudgeView result={judgeResult} running={running} hasTests={hasTests} acm={mode === 'acm'} />
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

function JudgeView({ result, running, hasTests, acm }: { result: RunTestsResponse | null; running: boolean; hasTests: boolean; acm: boolean }) {
  if (running && !result) return <div className="py-6 text-center text-xs text-journal-muted">判题中...</div>
  if (!result) {
    return (
      <div className="py-6 text-center text-xs text-journal-muted">
        {hasTests
          ? acm
            ? '点击「提交判题」用内置 stdin/stdout 用例判题'
            : '点击「提交判题」运行全部测试用例'
          : acm
            ? '本题暂无 ACM 判题用例，可用「自定义输入 + 运行」自由调试'
            : '本题暂不支持自动判题，可用「运行」自由调试'}
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
            <div className="text-journal-muted">
              输入:
              <pre className="mt-0.5 whitespace-pre-wrap rounded bg-black/30 px-2 py-1 text-journal-ink">{c.input}</pre>
            </div>
            {!c.ok && (
              <>
                <div className="text-journal-muted">
                  期望:
                  <pre className="mt-0.5 whitespace-pre-wrap rounded bg-black/30 px-2 py-1 text-easy">{c.expected}</pre>
                </div>
                <div className="text-journal-muted">
                  实际:
                  <pre className="mt-0.5 whitespace-pre-wrap rounded bg-black/30 px-2 py-1 text-hard">{c.actual}</pre>
                </div>
              </>
            )}
          </div>
        </div>
      ))}
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
  const queryClient = useQueryClient()
  const mark = useMutation({
    mutationFn: (status: 'forgot' | 'shaky' | 'solid') => reviewApi.firstSolve(problemId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['problems'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onDone()
    },
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
