import axios from 'axios'
import type { DashboardData, Problem, Progress } from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
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
