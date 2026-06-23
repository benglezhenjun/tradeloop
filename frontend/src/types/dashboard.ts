export interface MarketOverview {
  trade_date: string | null
  up_count: number
  down_count: number
  flat_count: number
  limit_up_count: number
  limit_down_count: number
  total_amount_yi: number
  avg_pct_chg: number
}

export interface IndustryHeatItem {
  industry: string
  stock_count: number
  avg_pct_chg: number
  total_amount_yi: number
  up_count: number
  down_count: number
}

export interface BreadthDay {
  trade_date: string
  up_count: number
  down_count: number
  flat_count: number
}

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
}
