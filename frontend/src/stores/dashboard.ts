import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  getBreadthHistory,
  getIndustryHeat,
  getMarketOverview,
  getSentimentSummary,
} from '@/api/index'
import type {
  BreadthDay,
  MarketOverview,
  IndustryHeatItem,
  SentimentSummary,
} from '@/types/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref<MarketOverview | null>(null)
  const industryHeat = ref<IndustryHeatItem[]>([])
  const breadth = ref<BreadthDay[]>([])
  const sentimentSummary = ref<SentimentSummary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function toErrorMessage(reason: unknown): string {
    return reason instanceof Error ? reason.message : '加载失败'
  }

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      const [overviewRes, heatRes, breadthRes, sentimentRes] = await Promise.allSettled([
        getMarketOverview(),
        getIndustryHeat(),
        getBreadthHistory(30),
        getSentimentSummary(),
      ])
      const failures = [overviewRes, heatRes, breadthRes, sentimentRes]
        .filter((result): result is PromiseRejectedResult => result.status === 'rejected')
        .map((result) => toErrorMessage(result.reason))

      if (overviewRes.status === 'fulfilled') {
        overview.value = overviewRes.value.data as MarketOverview
      }

      if (heatRes.status === 'fulfilled') {
        industryHeat.value = heatRes.value.data as IndustryHeatItem[]
      }

      if (breadthRes.status === 'fulfilled') {
        breadth.value = breadthRes.value.data as BreadthDay[]
      }

      if (sentimentRes.status === 'fulfilled') {
        sentimentSummary.value = sentimentRes.value.data as SentimentSummary
      }

      error.value = failures.length > 0 ? failures.join(', ') : null
    } catch (e: unknown) {
      error.value = toErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  return { overview, industryHeat, breadth, sentimentSummary, loading, error, fetchAll }
})
