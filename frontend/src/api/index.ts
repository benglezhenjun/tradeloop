/**
 * API 基础配置
 *
 * 所有请求都通过这个 axios 实例发送，统一处理错误。
 */
import axios from 'axios'

import type { Position, PositionDetail, PositionListFilter, PositionSummary } from '@/types/position'
import type {
  GeneratePlansResponse,
  PlanCreateData,
  PlanListFilter,
  PlanStatus,
  PlanUpdateData,
  TradingPlan,
} from '@/types/plan'
import type { BehaviorPattern, ReviewStats, TradeReview } from '@/types/review'
import type {
  MainThemeHistoryPoint,
  SentimentDetail,
  SentimentHistoryPoint,
  SentimentSummary,
} from '@/types/sentiment'
import type { TradeCreateData, TradeDetailResponse, TradeListFilter, TradeListResponse } from '@/types/trade'
import type { StockSearchResult } from '@/types/watchlist'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    console.error('API错误:', msg)
    return Promise.reject(new Error(msg))
  },
)

// ---- 健康检查 ----
export const checkHealth = () => http.get('/api/health')

// ---- 数据 ----
export const getDataStats = () => http.get('/api/data/stats')
export const getAvailableDates = () => http.get('/api/data/dates')
export const triggerSync = () => http.post('/api/data/sync/trigger')

// ---- 策略 ----
export const listStrategies = () => http.get('/api/strategies')
export const getStrategy = (id: number) => http.get(`/api/strategies/${id}`)
export const getAllConditions = () => http.get('/api/strategies/conditions/all')
export const createStrategy = (data: { name: string; description?: string }) =>
  http.post('/api/strategies', data)
export const updateStrategy = (
  id: number,
  data: { name?: string; description?: string; is_enabled?: boolean },
) => http.patch(`/api/strategies/${id}`, data)
export const deleteStrategy = (id: number) => http.delete(`/api/strategies/${id}`)
export const updateStrategyConditions = (id: number, conditions: object[]) =>
  http.put(`/api/strategies/${id}/conditions`, { conditions })

// ---- 筛选 ----
export const runScreening = (strategyId: number, tradeDate?: string) =>
  http.post(`/api/screening/run/${strategyId}`, null, {
    params: tradeDate ? { trade_date: tradeDate } : {},
  })
export const getScreeningHistory = (strategyId: number) =>
  http.get(`/api/screening/history/${strategyId}`)

// ---- 个股 ----
export const getStockInfo = (tsCode: string) => http.get(`/api/stocks/${tsCode}`)
export async function searchStocks(q: string, limit = 10): Promise<StockSearchResult[]> {
  const res = await http.get<{ stocks: StockSearchResult[] }>('/api/stocks/search', {
    params: { q, limit },
  })
  return res.data.stocks
}

// ---- K线 ----
export const getKline = (tsCode: string, startDate?: string, endDate?: string) =>
  http.get(`/api/kline/${tsCode}`, {
    params: { ...(startDate ? { start_date: startDate } : {}), ...(endDate ? { end_date: endDate } : {}) },
  })

// ---- LLM 分析 ----
export const getLlmStatus = () => http.get('/api/analysis/llm_status')
export const generateDailyReport = () => http.post('/api/analysis/daily_report', null, { timeout: 180_000 })
export const analyzeStock = (tsCode: string) =>
  http.post(`/api/analysis/stock/${tsCode}`, null, { timeout: 120_000 })
export const listReports = (reportType?: string) =>
  http.get('/api/analysis/reports', { params: reportType ? { report_type: reportType } : {} })
export const getReport = (id: number) => http.get(`/api/analysis/reports/${id}`)

// ---- 交易计划 (V5) ----
export const generatePlans = (tsCode: string) =>
  http.post<GeneratePlansResponse>(`/api/plan/generate/${tsCode}`, null, { timeout: 180_000 })
export const createPlan = (data: PlanCreateData) => http.post<TradingPlan>('/api/plan', data)
export const listPlans = (params?: PlanListFilter) => http.get<TradingPlan[]>('/api/plan', { params })
export const getPlan = (id: number) => http.get<TradingPlan>(`/api/plan/${id}`)
export const updatePlan = (id: number, data: PlanUpdateData) => http.put<TradingPlan>(`/api/plan/${id}`, data)
export const updatePlanStatus = (id: number, status: PlanStatus) =>
  http.patch<TradingPlan>(`/api/plan/${id}/status`, { status })
export const deletePlan = (id: number) => http.delete(`/api/plan/${id}`)

// ---- 交易记录 (V6) ----
export const createTrade = (data: TradeCreateData) => http.post('/api/trade', data)
export const listTrades = (params?: TradeListFilter) =>
  http.get<TradeListResponse>('/api/trade', { params })
export const getTrade = (id: number) => http.get<TradeDetailResponse>(`/api/trade/${id}`)
export const deleteTrade = (id: number) => http.delete(`/api/trade/${id}`)

// ---- 持仓 (V6) ----
export const listPositions = (params?: PositionListFilter) =>
  http.get<{ positions: Position[] }>('/api/position', { params })
export const getPosition = (tsCode: string) => http.get<PositionDetail>(`/api/position/${tsCode}`)
export const getPositionSummary = () => http.get<PositionSummary>('/api/position/summary')
export const recalculatePosition = (tsCode: string) =>
  http.post<{ position: Position | null }>(`/api/position/${tsCode}/recalc`)

// ---- 交易复盘 (V7) ----
export const generateReview = (tsCode: string) =>
  http.post<TradeReview>(`/api/review/generate/${tsCode}`, null, { timeout: 120_000 })
export const listReviews = (tsCode?: string) =>
  http.get<{ reviews: TradeReview[] }>('/api/review', { params: tsCode ? { ts_code: tsCode } : {} })
export const getReview = (id: number) => http.get<TradeReview>(`/api/review/${id}`)
export const updateReviewNotes = (id: number, notes: string) =>
  http.put<TradeReview>(`/api/review/${id}/notes`, { notes })
export const deleteReview = (id: number) => http.delete(`/api/review/${id}`)
export const getReviewStats = () => http.get<ReviewStats>('/api/review/stats')

// ---- 行为模式 (V7) ----
export const listPatterns = (status?: string) =>
  http.get<{ patterns: BehaviorPattern[] }>('/api/review/patterns', { params: status ? { status } : {} })
export const refreshPatterns = () =>
  http.post<{ patterns: BehaviorPattern[] }>('/api/review/patterns/refresh', null, { timeout: 120_000 })
export const updatePatternStatus = (id: number, status: string) =>
  http.patch<BehaviorPattern>(`/api/review/patterns/${id}/status`, { status })

// ---- 用户配置 (V5/V6) ----
export const getConfig = (key: string) => http.get(`/api/config/${key}`)
export const setConfig = (key: string, value: string) =>
  http.put(`/api/config/${key}`, { value })

// ---- 仪表盘 ----
export const getMarketOverview = () => http.get('/api/dashboard/overview')
export const getIndustryHeat = () => http.get('/api/dashboard/industry_heat')
export const getBreadthHistory = (days = 30) =>
  http.get('/api/dashboard/breadth', { params: { days } })

// ---- 市场情绪 ----
export const getSentimentSummary = () =>
  http.get<SentimentSummary>('/api/dashboard/sentiment/summary')
export const getSentimentHistory = (days = 120) =>
  http.get<SentimentHistoryPoint[]>('/api/dashboard/sentiment/history', { params: { days } })
export const getSentimentThemes = (days = 120) =>
  http.get<MainThemeHistoryPoint[]>('/api/dashboard/sentiment/themes', { params: { days } })
export const getSentimentDetail = (tradeDate: string) =>
  http.get<SentimentDetail>(`/api/dashboard/sentiment/detail/${tradeDate}`)

// ---- 自选股 ----
export const listWatchlistGroups = () => http.get('/api/watchlist/groups')
export const createWatchlistGroup = (name: string, description = '') =>
  http.post('/api/watchlist/groups', { name, description })
export const updateWatchlistGroup = (id: number, data: { name?: string; description?: string; sort_order?: number }) =>
  http.patch(`/api/watchlist/groups/${id}`, data)
export const deleteWatchlistGroup = (id: number) => http.delete(`/api/watchlist/groups/${id}`)
export const getGroupStocks = (groupId: number) => http.get(`/api/watchlist/groups/${groupId}/stocks`)
export const addStockToGroup = (groupId: number, tsCode: string, note = '') =>
  http.post(`/api/watchlist/groups/${groupId}/stocks`, { ts_code: tsCode, note })
export const removeStockFromGroup = (groupId: number, tsCode: string) =>
  http.delete(`/api/watchlist/groups/${groupId}/stocks/${tsCode}`)
export const getAllWatchlistStocks = () => http.get('/api/watchlist/stocks')
export const batchAddStocks = (groupId: number, tsCodes: string[]) =>
  http.post('/api/watchlist/stocks/batch', { group_id: groupId, ts_codes: tsCodes })
