/**
 * 筛选状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { runScreening, getAvailableDates } from '@/api/index'
import type { ScreeningResult } from '@/types/strategy'

export const useScreeningStore = defineStore('screening', () => {
  const result = ref<ScreeningResult | null>(null)
  const availableDates = ref<string[]>([])
  const selectedDate = ref<string | null>(null)
  const selectedStrategyId = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchDates() {
    const res = await getAvailableDates()
    availableDates.value = res.data.dates
    if (!selectedDate.value && availableDates.value.length > 0) {
      selectedDate.value = availableDates.value[0] ?? null
    }
  }

  async function run(strategyId: number, tradeDate?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await runScreening(strategyId, tradeDate)
      result.value = res.data
      selectedStrategyId.value = strategyId
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '筛选失败'
      result.value = null
    } finally {
      loading.value = false
    }
  }

  return { result, availableDates, selectedDate, selectedStrategyId, loading, error, fetchDates, run }
})
