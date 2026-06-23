export interface LlmStatus {
  configured: boolean
  provider: string
  model: string
  base_url: string
}

export interface DailyReportResult {
  id: number
  report: string
  sections: {
    market: string
    industry: string
    watchlist: string
    screening: string
    summary: string
  }
  generated_at: string
}

export interface StockAnalysisResult {
  id: number
  ts_code: string
  analysis: string
  generated_at: string
}

export interface ReportListItem {
  id: number
  report_type: 'daily' | 'stock'
  ts_code: string | null
  generated_at: string
}

export interface ReportDetail {
  id: number
  report_type: 'daily' | 'stock'
  ts_code: string | null
  content: string
  sections: Record<string, string> | null
  generated_at: string
}
