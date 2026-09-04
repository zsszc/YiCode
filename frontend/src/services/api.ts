import axios from 'axios'
import type {
  DashboardData,
  Problem,
  Progress,
  HintResponse,
  CodeReviewResponse,
  LearningProfile,
  AdaptiveRecommendation,
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
