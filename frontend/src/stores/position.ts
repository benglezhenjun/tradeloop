import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getPosition, getPositionSummary, listPositions, recalculatePosition } from '@/api/index'
import type { Position, PositionDetail, PositionListFilter, PositionSummary } from '@/types/position'
import type { TradeRecord } from '@/types/trade'
import { getErrorMessage } from '@/utils/error'

export const usePositionStore = defineStore('position', () => {
  const positions = ref<Position[]>([])
  const currentPosition = ref<Position | null>(null)
  const currentTrades = ref<TradeRecord[]>([])
  const summary = ref<PositionSummary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const holdingPositions = computed(() => positions.value.filter((position) => position.status === 'holding'))
  const closedPositions = computed(() => positions.value.filter((position) => position.status === 'closed'))

  function clearError() {
    error.value = null
  }

  function upsertPosition(updated: Position) {
    const index = positions.value.findIndex((position) => position.ts_code === updated.ts_code)
    if (index >= 0) {
      positions.value[index] = updated
    } else {
      positions.value = [updated, ...positions.value]
    }

    if (currentPosition.value?.ts_code === updated.ts_code) {
      currentPosition.value = updated
    }
  }

  async function fetchPositions(filter?: PositionListFilter) {
    loading.value = true
    clearError()
    try {
      const res = await listPositions(filter)
      positions.value = res.data.items ?? []
      return positions.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载持仓失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchPositionDetail(tsCode: string) {
    loading.value = true
    clearError()
    try {
      const res = await getPosition(tsCode)
      const detail = res.data as PositionDetail
      currentPosition.value = detail.position
      currentTrades.value = detail.trades
      return detail
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载持仓详情失败')
      currentPosition.value = null
      currentTrades.value = []
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary() {
    loading.value = true
    clearError()
    try {
      const res = await getPositionSummary()
      summary.value = res.data
      return summary.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载持仓汇总失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function recalc(tsCode: string) {
    clearError()
    try {
      const res = await recalculatePosition(tsCode)
      if (res.data?.position) {
        upsertPosition(res.data.position)
      }
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '重算持仓失败')
      return null
    }
  }

  return {
    positions,
    currentPosition,
    currentTrades,
    summary,
    loading,
    error,
    holdingPositions,
    closedPositions,
    clearError,
    fetchPositions,
    fetchPositionDetail,
    fetchSummary,
    recalc,
  }
})
