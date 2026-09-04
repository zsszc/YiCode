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
