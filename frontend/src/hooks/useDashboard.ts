import { useQuery } from '@tanstack/react-query'
import { dashboardApi, problemsApi, profileApi } from '@/services/api'

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

export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => profileApi.get(),
  })
}

export function useAdaptive() {
  return useQuery({
    queryKey: ['adaptive'],
    queryFn: () => profileApi.adaptive(),
  })
}
