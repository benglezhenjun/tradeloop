import type { TradeRecord } from '@/types/trade'

export type PositionStatus = 'holding' | 'closed'

export interface Position {
  id: number
  ts_code: string
  stock_name: string
  total_quantity: number
  avg_cost: number
  total_cost: number
  realized_pnl: number
  status: PositionStatus
  first_buy_date: string
  last_trade_date: string
  updated_at: string
  current_price?: number
  market_value?: number
  unrealized_pnl?: number
  quote_trade_date?: string | null
}

export interface PositionSummary {
  position_count: number
  holding_count: number
  closed_count: number
  total_market_value: number
  total_cost: number
  total_unrealized_pnl: number
  total_realized_pnl: number
}

export interface PositionListFilter {
  status?: PositionStatus
}

export interface PositionDetail {
  position: Position
  trades: TradeRecord[]
}
