export interface Problem {
  id: number
  title: string
  slug?: string
  difficulty: '简单' | '中等' | '困难'
  category: string
  is_custom: boolean
  status?: string
  next_review?: string
  note?: string
}

export interface DashboardData {
  date: string
  is_weekend: boolean
  quota: number
  done_today: number[]
  solved_today: number[]
  reviewed_today: number[]
  due_review: DashboardItem[]
  today_new: DashboardItem[]
  extras_pool: DashboardItem[]
  todo_left: number
  counts: Record<string, number>
  total: number
  finish: {
    days_left: number | null
    finish_date: string | null
    reachable: boolean
  }
  skipped_yesterday?: {
    date: string
    review_count: number
  }
}

export interface DashboardItem {
  id: number
  title: string
  slug?: string
  difficulty: string
  category: string
  status?: string
  next_review?: string
  review_stage: number
  note: string
  is_overdue?: boolean
}

export interface Progress {
  problem_id: number
  status: string
  review_stage: number
  next_review?: string
  last_done?: string
  note: string
  cheatsheet: string
}

// Phase 2: AI Tutor
export interface HintResponse {
  content: string
  tokens_used: number
  latency_ms: number
}

export interface CodeReviewResponse {
  time_complexity: string
  space_complexity: string
  edge_cases: string[]
  style_suggestions: string[]
  optimization_hints: string[]
  rating: number
  overall_comment: string
  tokens_used: number
  latency_ms: number
}

// Phase 2: Learning Profile
export interface LearningProfile {
  user_id: number
  avg_solve_time_easy_ms: number
  avg_solve_time_medium_ms: number
  avg_solve_time_hard_ms: number
  hint_dependency_rate: number
  first_try_success_rate: number
  peak_hour_start: number
  peak_hour_end: number
  preferred_difficulty: string
  streak_days: number
  max_streak: number
  total_solved: number
  total_reviewed: number
  adaptive_quota_enabled: boolean
  custom_quota_weekday?: number
  custom_quota_weekend?: number
}

export interface AdaptiveRecommendation {
  quota_weekday: number
  quota_weekend: number
  new_ratio: number
  hard_ratio: number
  adaptive_enabled: boolean
  reasoning: string
  profile: {
    streak_days: number
    hint_dependency_rate: number
    first_try_success_rate: number
    preferred_difficulty: string
  }
}
