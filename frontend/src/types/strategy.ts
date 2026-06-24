// 策略相关 TypeScript 类型定义

export interface ParamSchema {
  label: string
  type: 'number' | 'int' | 'bool' | 'select'
  default: number | boolean | string
  description: string
}

export interface ConditionDef {
  code: string
  name: string
  category: string
  description: string
  params: Record<string, ParamSchema>
}

export interface StrategyCondition {
  id?: number
  condition_code: string
  condition_name: string
  category: string
  params: Record<string, number | boolean | string>
  param_schema: Record<string, ParamSchema>
  is_enabled: boolean
  sort_order: number
}

export interface Strategy {
  id: number
  name: string
  description: string
  is_enabled: boolean
  condition_count: number
  created_at: string
}

export interface StrategyDetail {
  id: number
  name: string
  description: string
  is_enabled: boolean
  conditions: StrategyCondition[]
}

export interface ScreeningCandidate {
  ts_code: string
  name: string
  industry: string
  close: number | null
  amount_yi: number | null
  total_mv_yi: number | null
  pct_chg: number | null
  rank: number
}

export interface ScreeningResult {
  run_id: number
  trade_date: string
  strategy_name: string
  count: number
  duration_ms: number
  candidates: ScreeningCandidate[]
}

export interface ScreeningRunHistory {
  run_id: number
  strategy_name: string
  trade_date: string
  run_at: string
  result_count: number
  duration_ms: number
}
