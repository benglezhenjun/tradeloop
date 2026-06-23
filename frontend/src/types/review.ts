export interface ReviewScores {
  entry_timing: number
  exit_timing: number
  stop_loss: number
  take_profit: number
  position_sizing: number
  holding_period: number
  discipline: number
  risk_reward: number
}

export interface TradeReview {
  id: number
  ts_code: string
  stock_name: string
  plan_id: number | null
  total_buy_amount: number
  total_sell_amount: number
  total_fee: number
  realized_pnl: number
  trade_count: number
  first_trade_date: string
  last_trade_date: string
  holding_days: number
  scores: ReviewScores
  overall_score: number
  analysis: string
  improvement: string | null
  user_notes: string | null
  created_at: string
  updated_at: string
}

export interface ReviewStats {
  total_reviews: number
  avg_overall_score: number
  avg_scores: ReviewScores
  best_dimension: string
  worst_dimension: string
  win_count: number
  loss_count: number
  total_reviewed_pnl: number
}

export type PatternType = 'strength' | 'weakness'
export type PatternStatus = 'active' | 'resolved' | 'dismissed'

export interface BehaviorPattern {
  id: number
  pattern_type: PatternType
  title: string
  description: string
  dimension: string | null
  evidence_ids: number[]
  status: PatternStatus
  created_at: string
  updated_at: string
}
