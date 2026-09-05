import axios from 'axios'
import type {
  DashboardData,
  Problem,
  Progress,
  HintResponse,
  CodeReviewResponse,
  LearningProfile,
  AdaptiveRecommendation,
  ChatMsg,
  ChatResponse,
  CodeRunResponse,
  RunTestsResponse,
  Diagnostic,
  CompleteResponse,
  TemplateSummary,
  TemplateDetail,
} from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：自动附加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('yicode_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const dashboardApi = {
  getToday: () => api.get<DashboardData>('/dashboard').then(r => r.data),
  shiftForward: () => api.post<{ shifted_count: number; message: string }>('/dashboard/shift-forward').then(r => r.data),
}

export const problemsApi = {
  list: (params?: { keyword?: string; category?: string; difficulty?: string }) =>
    api.get<Problem[]>('/problems', { params }).then(r => r.data),
  get: (id: number) => api.get<Problem>(`/problems/${id}`).then(r => r.data),
  create: (data: Partial<Problem>) => api.post<Problem>('/problems', data).then(r => r.data),
}

export const reviewApi = {
  firstSolve: (problemId: number, status: 'forgot' | 'shaky' | 'solid') =>
    api.post<Progress>(`/review/first-solve/${problemId}`, { status }).then(r => r.data),
  review: (problemId: number, score: 'easy' | 'ok' | 'hard') =>
    api.post<Progress>(`/review/${problemId}`, { score }).then(r => r.data),
  updateNote: (problemId: number, note: string) =>
    api.put<Progress>(`/review/${problemId}/note`, { note }).then(r => r.data),
}

// Phase 2: AI Tutor
export const tutorApi = {
  hint: (problemId: number, hintLevel: number = 1, userCode?: string) =>
    api.post<HintResponse>('/tutor/hint', {
      problem_id: problemId,
      hint_level: hintLevel,
      user_code: userCode,
    }).then(r => r.data),
  reviewCode: (problemId: number, code: string, language: string = 'python') =>
    api.post<CodeReviewResponse>('/tutor/review-code', {
      problem_id: problemId,
      code,
      language,
    }).then(r => r.data),
  logs: (limit: number = 20) =>
    api.get('/tutor/logs', { params: { limit } }).then(r => r.data),
  chat: (problemId: number | null, message: string, history: ChatMsg[], userCode?: string) =>
    api.post<ChatResponse>('/tutor/chat', {
      problem_id: problemId,
      message,
      history,
      user_code: userCode,
    }).then(r => r.data),
  /** SSE 流式聊天：每收到一段文本回调一次 onChunk，出错抛异常 */
  chatStream: async (
    problemId: number | null,
    message: string,
    history: ChatMsg[],
    userCode: string | undefined,
    onChunk: (text: string) => void,
  ): Promise<void> => {
    await readSSE('/api/v1/tutor/chat-stream', onChunk, {
      method: 'POST',
      body: JSON.stringify({
        problem_id: problemId,
        message,
        history,
        user_code: userCode,
      }),
    })
  },
  /** SSE 流式提示：GET 接口，打字机渲染 */
  hintStream: async (
    problemId: number,
    level: number,
    onChunk: (text: string) => void,
  ): Promise<void> => {
    await readSSE(`/api/v1/tutor/hint-stream/${problemId}?level=${level}`, onChunk)
  },
}

// Phase 5: 在线代码运行 / 判题
export const codeApi = {
  run: (code: string, stdin?: string) =>
    api.post<CodeRunResponse>('/code/run', { code, stdin }).then(r => r.data),
  runTests: (problemId: number, code: string, mode: 'function' | 'acm' = 'function') =>
    api.post<RunTestsResponse>('/code/run-tests', { problem_id: problemId, code, mode }).then(r => r.data),
  /** 静态诊断：波浪线数据源 */
  lint: (code: string) =>
    api.post<{ diagnostics: Diagnostic[] }>('/code/lint', { code }).then(r => r.data.diagnostics),
  /** AI 内联补全 */
  complete: (code: string, cursorLine: number, cursorCol: number, problemId?: number) =>
    api.post<CompleteResponse>('/code/complete', {
      code,
      cursor_line: cursorLine,
      cursor_col: cursorCol,
      problem_id: problemId,
    }).then(r => r.data.completion),
}

// Phase 6: 模板刷题（面试背诵模式）
export const templatesApi = {
  list: () => api.get<TemplateSummary[]>('/templates').then(r => r.data),
  get: (slug: string) => api.get<TemplateDetail>(`/templates/${slug}`).then(r => r.data),
  /** AI 变式出题：生成原创练习题并落库，返回新题 ID */
  generateVariant: (slug: string) =>
    api.post<{ id: number; title: string; template: string }>(`/templates/${slug}/variant`).then(r => r.data),
}

/** 通用 SSE 流读取器：逐段回调文本，遇错误帧抛错 */
export async function readSSE(
  url: string,
  onChunk: (text: string) => void,
  init?: RequestInit,
): Promise<void> {
  const token = localStorage.getItem('yicode_token')
  const resp = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`请求失败 (${resp.status})，请确认后端服务已启动`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const ev of events) {
      const line = ev.split('\n').find(l => l.startsWith('data: '))
      if (!line) continue
      const payload = line.slice(6)
      if (payload === '[DONE]') return
      const parsed = JSON.parse(payload)
      if (parsed && typeof parsed === 'object' && 'error' in parsed) {
        throw new Error(parsed.error)
      }
      onChunk(parsed)
    }
  }
}

// Phase 2: Learning Profile
export const profileApi = {
  get: () => api.get<LearningProfile>('/profile').then(r => r.data),
  update: (data: Partial<LearningProfile>) =>
    api.put<LearningProfile>('/profile', data).then(r => r.data),
  adaptive: () => api.get<AdaptiveRecommendation>('/profile/adaptive').then(r => r.data),
  recordBehavior: (problemId: number, actionType: string, actionData?: object) =>
    api.post('/profile/behaviors', {
      problem_id: problemId,
      action_type: actionType,
      action_data: actionData,
    }).then(r => r.data),
}

// Phase 3: Auth
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }).then(r => r.data),
  register: (username: string, password: string, email?: string) =>
    api.post('/auth/register', { username, password, email }).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
}
