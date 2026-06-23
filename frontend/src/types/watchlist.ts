// Watchlist-related TypeScript types

export interface WatchlistGroup {
  id: number
  name: string
  description: string
  sort_order: number
  stock_count: number
  created_at: string | null
}

export interface WatchlistStock {
  ts_code: string
  name: string
  industry: string
  close: number | null
  pct_chg: number | null
  amount_yi: number | null
  total_mv_yi: number | null
  note: string
  added_at: string | null
  group_id: number
}

export interface BatchAddWatchlistResult {
  added: number
  skipped: number
  skipped_existing: number
  skipped_invalid: number
  invalid_codes: string[]
}

export interface KlineItem {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  vol: number | null
  amount_yi: number | null
  pct_chg: number | null
}

export interface StockKline {
  ts_code: string
  name: string
  industry: string
  klines: KlineItem[]
}

export interface StockSearchResult {
  ts_code: string
  name: string
  industry: string
}
