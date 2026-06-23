import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  getSentimentDetail,
  getSentimentHistory,
  getSentimentSummary,
  getSentimentThemes,
} from '@/api/index'
import type {
  MainThemeHistoryPoint,
  SentimentDetail,
  SentimentHistoryPoint,
  SentimentSummary,
} from '@/types/sentiment'

const DEFAULT_SENTIMENT_DAYS = 120

export const useSentimentStore = defineStore('sentiment', () => {
  const summary = ref<SentimentSummary | null>(null)
  const history = ref<SentimentHistoryPoint[]>([])
  const themes = ref<MainThemeHistoryPoint[]>([])
  const detail = ref<SentimentDetail | null>(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref<string | null>(null)
  const currentDays = ref(DEFAULT_SENTIMENT_DAYS)

  async function fetchSummary() {
    try {
      const response = await getSentimentSummary()
      summary.value = response.data as SentimentSummary
      return summary.value
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载市场情绪摘要失败'
      throw e
    }
  }

  async function fetchDetail(tradeDate: string) {
    detailLoading.value = true
    try {
      const response = await getSentimentDetail(tradeDate)
      detail.value = response.data as SentimentDetail
      return detail.value
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载市场情绪详情失败'
      throw e
    } finally {
      detailLoading.value = false
    }
  }

  async function fetchPageData(days = currentDays.value) {
    loading.value = true
    error.value = null
    currentDays.value = days
    try {
      const [summaryRes, historyRes, themesRes] = await Promise.all([
        getSentimentSummary(),
        getSentimentHistory(days),
        getSentimentThemes(days),
      ])
      summary.value = summaryRes.data as SentimentSummary
      history.value = historyRes.data as SentimentHistoryPoint[]
      themes.value = themesRes.data as MainThemeHistoryPoint[]

      const detailTradeDate =
        history.value[history.value.length - 1]?.trade_date ?? summary.value?.trade_date ?? null
      if (detailTradeDate) {
        await fetchDetail(detailTradeDate)
      } else {
        detail.value = null
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载市场情绪失败'
    } finally {
      loading.value = false
    }
  }

  return {
    summary,
    history,
    themes,
    detail,
    loading,
    detailLoading,
    error,
    currentDays,
    fetchSummary,
    fetchDetail,
    fetchPageData,
  }
})
