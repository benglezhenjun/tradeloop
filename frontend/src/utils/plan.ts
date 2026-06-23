import type {
  EditablePlanDraft,
  ManualPlanPrefill,
  PlanCreateData,
  PlanProposal,
  PlanSource,
  PlanTierLabel,
  PlanUpdateData,
  TakeProfitTier,
  TradingPlan,
} from '@/types/plan'

export function createDefaultTakeProfitTier(): TakeProfitTier {
  return {
    price: 0,
    ratio: 1,
    note: '',
  }
}

export function cloneTakeProfitTiers(tiers: TakeProfitTier[]): TakeProfitTier[] {
  return tiers.map((tier) => ({
    price: tier.price,
    ratio: tier.ratio,
    note: tier.note ?? '',
  }))
}

export function clonePlanProposal(proposal: PlanProposal): PlanProposal {
  return {
    ...proposal,
    take_profit: cloneTakeProfitTiers(proposal.take_profit),
    risk_comment: proposal.risk_comment ?? null,
  }
}

export function createEmptyPlanDraft(prefill?: Partial<ManualPlanPrefill>): EditablePlanDraft {
  return {
    ts_code: prefill?.ts_code ?? '',
    stock_name: prefill?.stock_name ?? '',
    direction: 'buy',
    target_price: 0,
    stop_loss_price: 0,
    take_profit: [createDefaultTakeProfitTier()],
    position_ratio: 0.2,
    reasoning: '',
    risk_comment: '',
    tier_label: null,
    expiry_date: '',
  }
}

export function clonePlanDraft(draft: EditablePlanDraft): EditablePlanDraft {
  return {
    ...draft,
    risk_comment: draft.risk_comment ?? '',
    expiry_date: draft.expiry_date ?? '',
    take_profit: cloneTakeProfitTiers(draft.take_profit),
  }
}

export function draftFromProposal(proposal: PlanProposal): EditablePlanDraft {
  return {
    ts_code: proposal.ts_code,
    stock_name: proposal.stock_name,
    direction: proposal.direction,
    target_price: proposal.target_price,
    stop_loss_price: proposal.stop_loss_price,
    take_profit: cloneTakeProfitTiers(proposal.take_profit),
    position_ratio: proposal.position_ratio,
    reasoning: proposal.reasoning,
    risk_comment: proposal.risk_comment ?? '',
    tier_label: proposal.tier_label,
    expiry_date: '',
  }
}

export function draftFromPlan(plan: TradingPlan): EditablePlanDraft {
  return {
    ts_code: plan.ts_code,
    stock_name: plan.stock_name,
    direction: plan.direction,
    target_price: plan.target_price,
    stop_loss_price: plan.stop_loss_price,
    take_profit: cloneTakeProfitTiers(plan.take_profit),
    position_ratio: plan.position_ratio,
    reasoning: plan.reasoning,
    risk_comment: plan.risk_comment ?? '',
    tier_label: plan.tier_label,
    expiry_date: plan.expiry_date ?? '',
  }
}

export function buildPlanCreateData(
  draft: EditablePlanDraft,
  options: { source: PlanSource; alternatives?: PlanProposal[] },
): PlanCreateData {
  const riskComment = draft.risk_comment?.trim() ? draft.risk_comment : null

  return {
    ts_code: draft.ts_code,
    stock_name: draft.stock_name,
    direction: draft.direction,
    target_price: draft.target_price,
    stop_loss_price: draft.stop_loss_price,
    take_profit: cloneTakeProfitTiers(draft.take_profit),
    position_ratio: draft.position_ratio,
    reasoning: draft.reasoning,
    risk_comment: riskComment,
    tier_label: draft.tier_label ?? undefined,
    source: options.source,
    expiry_date: draft.expiry_date || undefined,
    alternatives: options.alternatives?.map(clonePlanProposal),
  }
}

export function buildPlanUpdateData(draft: EditablePlanDraft): PlanUpdateData {
  const riskComment = draft.risk_comment?.trim() ? draft.risk_comment : null

  return {
    direction: draft.direction,
    target_price: draft.target_price,
    stop_loss_price: draft.stop_loss_price,
    take_profit: cloneTakeProfitTiers(draft.take_profit),
    position_ratio: draft.position_ratio,
    reasoning: draft.reasoning,
    risk_comment: riskComment,
    tier_label: draft.tier_label,
    expiry_date: draft.expiry_date || undefined,
  }
}

export function getTakeProfitRatioTotal(tiers: TakeProfitTier[]): number {
  return tiers.reduce((sum, tier) => sum + tier.ratio, 0)
}

export function isEditablePlan(plan: TradingPlan): boolean {
  return plan.status === 'pending'
}

export function formatPlanTierLabel(tierLabel: PlanTierLabel | null): string {
  if (!tierLabel) {
    return '手动'
  }

  const labels: Record<PlanTierLabel, string> = {
    aggressive: '激进',
    balanced: '稳健',
    conservative: '保守',
  }
  return labels[tierLabel]
}

export function formatLocalDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(parsed)
}
