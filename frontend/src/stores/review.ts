import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  deleteReview as deleteReviewApi,
  generateReview as generateReviewApi,
  getReview,
  getReviewStats,
  listPatterns as listPatternsApi,
  listReviews as listReviewsApi,
  refreshPatterns as refreshPatternsApi,
  updatePatternStatus as updatePatternStatusApi,
  updateReviewNotes as updateReviewNotesApi,
} from '@/api/index'
import type { BehaviorPattern, PatternStatus, ReviewStats, TradeReview } from '@/types/review'
import { getErrorMessage } from '@/utils/error'

export const useReviewStore = defineStore('review', () => {
  const reviews = ref<TradeReview[]>([])
  const stats = ref<ReviewStats | null>(null)
  const patterns = ref<BehaviorPattern[]>([])
  const currentReview = ref<TradeReview | null>(null)
  const fetching = ref(false)
  const creating = ref(false)
  const saving = ref(false)
  const removing = ref(false)
  const loading = computed(() => fetching.value || creating.value || saving.value || removing.value)
  const patternLoading = ref(false)
  const error = ref<string | null>(null)

  function clearError() {
    error.value = null
  }

  function upsertReview(updated: TradeReview) {
    const index = reviews.value.findIndex((review) => review.id === updated.id)
    if (index >= 0) {
      reviews.value[index] = updated
    } else {
      reviews.value = [updated, ...reviews.value]
    }

    if (currentReview.value?.id === updated.id) {
      currentReview.value = updated
    }
  }

  async function fetchReviews(tsCode?: string) {
    fetching.value = true
    clearError()
    try {
      const res = await listReviewsApi(tsCode)
      reviews.value = res.data.items ?? []
      return reviews.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载复盘列表失败')
      return null
    } finally {
      fetching.value = false
    }
  }

  async function fetchReviewDetail(id: number) {
    fetching.value = true
    clearError()
    try {
      const res = await getReview(id)
      currentReview.value = res.data
      return currentReview.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载复盘详情失败')
      return null
    } finally {
      fetching.value = false
    }
  }

  async function createReview(tsCode: string) {
    creating.value = true
    clearError()
    try {
      const res = await generateReviewApi(tsCode)
      upsertReview(res.data)
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '生成复盘失败')
      return null
    } finally {
      creating.value = false
    }
  }

  async function saveNotes(id: number, notes: string) {
    saving.value = true
    clearError()
    try {
      const res = await updateReviewNotesApi(id, notes)
      upsertReview(res.data)
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '保存复盘反思失败')
      return null
    } finally {
      saving.value = false
    }
  }

  async function removeReview(id: number) {
    removing.value = true
    clearError()
    try {
      await deleteReviewApi(id)
      reviews.value = reviews.value.filter((review) => review.id !== id)
      if (currentReview.value?.id === id) {
        currentReview.value = null
      }
      return true
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '删除复盘失败')
      return false
    } finally {
      removing.value = false
    }
  }

  async function fetchStats() {
    fetching.value = true
    clearError()
    try {
      const res = await getReviewStats()
      stats.value = res.data
      return stats.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载复盘统计失败')
      return null
    } finally {
      fetching.value = false
    }
  }

  async function fetchPatterns(status?: PatternStatus) {
    patternLoading.value = true
    clearError()
    try {
      const res = await listPatternsApi(status)
      patterns.value = res.data.items ?? []
      return patterns.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载行为模式失败')
      return null
    } finally {
      patternLoading.value = false
    }
  }

  async function refreshPatterns() {
    patternLoading.value = true
    clearError()
    try {
      const res = await refreshPatternsApi()
      patterns.value = res.data.items ?? []
      return patterns.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '刷新行为模式失败')
      return null
    } finally {
      patternLoading.value = false
    }
  }

  async function changePatternStatus(id: number, status: PatternStatus) {
    patternLoading.value = true
    clearError()
    try {
      const res = await updatePatternStatusApi(id, status)
      const index = patterns.value.findIndex((pattern) => pattern.id === id)
      if (index >= 0) {
        patterns.value[index] = res.data
      } else {
        patterns.value = [res.data, ...patterns.value]
      }
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '更新行为模式状态失败')
      return null
    } finally {
      patternLoading.value = false
    }
  }

  return {
    reviews,
    stats,
    patterns,
    currentReview,
    fetching,
    creating,
    saving,
    removing,
    loading,
    patternLoading,
    error,
    clearError,
    fetchReviews,
    fetchReviewDetail,
    generateReview: createReview,
    saveNotes,
    removeReview,
    fetchStats,
    fetchPatterns,
    refreshPatterns,
    updatePatternStatus: changePatternStatus,
  }
})
