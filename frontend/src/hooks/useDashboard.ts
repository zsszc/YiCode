import { useQuery } from '@tanstack/react-query'
import { dashboardApi, problemsApi } from '@/services/api'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => dashboardApi.getToday(),
  })
}

export function useProblems(params?: { keyword?: string; category?: string; difficulty?: string }) {
  return useQuery({
    queryKey: ['problems', params],
    queryFn: () => problemsApi.list(params),
  })
}
