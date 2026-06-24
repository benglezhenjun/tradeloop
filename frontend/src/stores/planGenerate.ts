import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { generatePlans, getConfig, setConfig } from '@/api/index'
import type { GeneratePlansManualFallback, GeneratePlansResponse, GeneratePlansSuccess } from '@/types/plan'
import { getErrorMessage } from '@/utils/error'

export const usePlanGenerateStore = defineStore('plan-generate', () => {
  const generateResult = ref<GeneratePlansResponse | null>(null)
  const totalCapital = ref(0)
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)

  const proposals = computed(() => {
    if (generateResult.value?.status !== 'ok') {
      return []
    }
    return generateResult.value.plans
  })

  const manualFallback = computed<GeneratePlansManualFallback | null>(() => {
    if (generateResult.value?.status !== 'manual_fallback') {
      return null
    }
    return generateResult.value
  })

  const generationStatus = computed<GeneratePlansSuccess['status'] | GeneratePlansManualFallback['status'] | null>(
    () => generateResult.value?.status ?? null,
  )

  function clearError() {
    error.value = null
  }

  function clearGenerateResult() {
    generateResult.value = null
  }

  async function generate(tsCode: string) {
    generating.value = true
    clearError()
    clearGenerateResult()
    try {
      const res = await generatePlans(tsCode)
      generateResult.value = res.data
      return generateResult.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '生成计划失败')
      return null
    } finally {
      generating.value = false
    }
  }

  async function fetchTotalCapital() {
    loading.value = true
    clearError()
    try {
      const res = await getConfig('total_capital')
      const parsed = Number.parseFloat(res.data.value)
      totalCapital.value = Number.isNaN(parsed) ? 0 : parsed
      return totalCapital.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载总资金失败')
      totalCapital.value = 0
      return null
    } finally {
      loading.value = false
    }
  }

  async function saveTotalCapital(amount: number) {
    loading.value = true
    clearError()
    try {
      await setConfig('total_capital', String(amount))
      totalCapital.value = amount
      return true
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '保存总资金失败')
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    generateResult,
    totalCapital,
    loading,
    generating,
    error,
    proposals,
    manualFallback,
    generationStatus,
    clearError,
    clearGenerateResult,
    generate,
    fetchTotalCapital,
    saveTotalCapital,
  }
})
