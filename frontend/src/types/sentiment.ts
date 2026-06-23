export interface SentimentSummary {
  trade_date: string | null
  max_limit_height: number
  max_limit_height_count: number
  max_limit_height_codes: string[]
  limit_up_count: number
  limit_broken_count: number
  broken_rate: number
  yday_limit_premium_avg: number
  yday_limit_premium_median: number
  yday_limit_red_rate: number
  yday_limit_sample_count: number
  high_board_threshold: number
  high_board_total: number
  high_board_advanced: number
  high_board_promotion_rate: number
  main_theme_code: string | null
  main_theme_name: string | null
  main_theme_score: number | null
  main_theme_streak_days: number
  notes?: Record<string, unknown>
}

export interface SentimentHistoryPoint extends SentimentSummary {}

export interface MainThemeHistoryPoint {
  trade_date: string
  main_theme_code: string | null
  main_theme_name: string | null
  main_theme_score: number | null
  main_theme_streak_days: number
}

export interface LimitEventSample {
  ts_code: string
  name: string | null
  limit_times: number
  up_stat?: string | null
}

export interface YdayLimitSample {
  ts_code: string
  name: string | null
  prev_limit_times?: number
  today_pct_chg: number | null
}

export interface HighBoardSample {
  ts_code: string
  name: string | null
  prev_limit_times: number
  current_limit_times: number | null
  is_advanced: boolean
}

export interface ThemeLeader {
  theme_code: string
  theme_name: string | null
  rank: number | null
  score: number | null
  up_stat?: string | null
}

export interface SentimentDetail {
  trade_date: string
  summary: SentimentSummary | null
  limit_up_samples: LimitEventSample[]
  limit_broken_samples: LimitEventSample[]
  yday_limit_samples: YdayLimitSample[]
  high_board_samples: HighBoardSample[]
  theme_leaders: ThemeLeader[]
}
