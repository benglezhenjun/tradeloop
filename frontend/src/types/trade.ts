export type TradeDirection = 'buy' | 'sell'

export interface TradeRecord {
  id: number
  ts_code: string
  stock_name: string
  plan_id: number | null
  direction: TradeDirection
  price: number
  quantity: number
  amount: number
  fee: number
  trade_date: string
  trade_time: string | null
  note: string | null
  created_at: string
}

export interface TradeCreateData {
  ts_code: string
  stock_name: string
  direction: TradeDirection
  price: number
  quantity: number
  trade_date: string
  trade_time?: string | null
  fee?: number | null
  note?: string | null
  plan_id?: number | null
}

export interface TradeListFilter {
  ts_code?: string
  direction?: TradeDirection
}

export interface TradeDetailResponse {
  trade: TradeRecord
}
