export type PlanDirection = 'buy' | 'sell'
export type PlanTierLabel = 'aggressive' | 'balanced' | 'conservative'
export type PlanStatus = 'pending' | 'executed' | 'abandoned'
export type PlanSource = 'llm_generated' | 'manual'
export type PlanEditorMode = 'manual-create' | 'generate-edit' | 'existing-edit'

export interface TakeProfitTier {
  price: number
  ratio: number
  note?: string
}

export interface ManualPlanPrefill {
  ts_code: string
  stock_name: string
}

export interface PlanProposal extends ManualPlanPrefill {
  tier_label: PlanTierLabel
  direction: PlanDirection
  target_price: number
  stop_loss_price: number
  take_profit: TakeProfitTier[]
  position_ratio: number
  reasoning: string
  risk_comment: string | null
}

export interface EditablePlanDraft extends ManualPlanPrefill {
  direction: PlanDirection
  target_price: number
  stop_loss_price: number
  take_profit: TakeProfitTier[]
  position_ratio: number
  reasoning: string
  risk_comment: string | null
  tier_label: PlanTierLabel | null
  expiry_date: string
}

export interface TradingPlan {
  id: number
  ts_code: string
  stock_name: string
  direction: PlanDirection
  target_price: number
  stop_loss_price: number
  take_profit: TakeProfitTier[]
  position_ratio: number
  reasoning: string
  risk_comment: string | null
  tier_label: PlanTierLabel | null
  source: PlanSource
  status: PlanStatus
  expiry_date: string | null
  alternatives?: PlanProposal[]
  created_at: string
  updated_at: string
}

export interface PlanCreateData extends ManualPlanPrefill {
  direction: PlanDirection
  target_price: number
  stop_loss_price: number
  take_profit: TakeProfitTier[]
  position_ratio: number
  reasoning: string
  risk_comment: string | null
  tier_label?: PlanTierLabel | null
  source: PlanSource
  expiry_date?: string
  alternatives?: PlanProposal[]
}

export interface PlanUpdateData {
  direction?: PlanDirection
  target_price?: number
  stop_loss_price?: number
  take_profit?: TakeProfitTier[]
  position_ratio?: number
  reasoning?: string
  risk_comment?: string | null
  tier_label?: PlanTierLabel | null
  expiry_date?: string
}

export interface GeneratePlansSuccess {
  status: 'ok'
  plans: PlanProposal[]
}

export interface GeneratePlansManualFallback {
  status: 'manual_fallback'
  message: string
  prefill: ManualPlanPrefill
  raw_response?: string
}

export type GeneratePlansResponse = GeneratePlansSuccess | GeneratePlansManualFallback

export interface PlanListFilter {
  status?: PlanStatus
  ts_code?: string
}

export const TIER_LABELS: Record<PlanTierLabel, string> = {
  aggressive: '激进',
  balanced: '稳健',
  conservative: '保守',
}

export const STATUS_LABELS: Record<PlanStatus, string> = {
  pending: '待执行',
  executed: '已执行',
  abandoned: '已放弃',
}

export const DIRECTION_LABELS: Record<PlanDirection, string> = {
  buy: '买入',
  sell: '卖出',
}
