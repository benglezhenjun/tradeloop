import { ref } from 'vue'
import { defineStore } from 'pinia'

import { createPlan, deletePlan, getPlan, listPlans, updatePlan, updatePlanStatus } from '@/api/index'
import type { PlanCreateData, PlanListFilter, PlanStatus, PlanUpdateData, TradingPlan } from '@/types/plan'
import { getErrorMessage } from '@/utils/error'

export const usePlanStore = defineStore('plan', () => {
  const plans = ref<TradingPlan[]>([])
  const currentPlan = ref<TradingPlan | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function clearError() {
    error.value = null
  }

  function upsertPlan(updated: TradingPlan) {
    const index = plans.value.findIndex((plan) => plan.id === updated.id)
    if (index >= 0) {
      plans.value[index] = updated
    } else {
      plans.value = [updated, ...plans.value]
    }

    if (currentPlan.value?.id === updated.id) {
      currentPlan.value = updated
    }
  }

  async function fetchPlans(filters?: PlanListFilter) {
    loading.value = true
    clearError()
    try {
      const res = await listPlans(filters)
      plans.value = res.data.items
      return plans.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载计划失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchPlanDetail(id: number) {
    loading.value = true
    clearError()
    try {
      const res = await getPlan(id)
      currentPlan.value = res.data
      return currentPlan.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载计划详情失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function savePlan(data: PlanCreateData) {
    clearError()
    try {
      const res = await createPlan(data)
      upsertPlan(res.data)
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '保存计划失败')
      return null
    }
  }

  async function editPlan(id: number, data: PlanUpdateData) {
    clearError()
    try {
      const res = await updatePlan(id, data)
      upsertPlan(res.data)
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '更新计划失败')
      return null
    }
  }

  async function changeStatus(id: number, status: PlanStatus) {
    clearError()
    try {
      const res = await updatePlanStatus(id, status)
      upsertPlan(res.data)
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '状态更新失败')
      return null
    }
  }

  async function removePlan(id: number) {
    clearError()
    try {
      await deletePlan(id)
      plans.value = plans.value.filter((plan) => plan.id !== id)
      if (currentPlan.value?.id === id) {
        currentPlan.value = null
      }
      return true
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '删除计划失败')
      return false
    }
  }

  return {
    plans,
    currentPlan,
    loading,
    error,
    clearError,
    fetchPlans,
    fetchPlanDetail,
    savePlan,
    editPlan,
    changeStatus,
    removePlan,
  }
})
