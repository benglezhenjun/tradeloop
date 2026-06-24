import { defineStore } from 'pinia'
import { ref } from 'vue'

import { createTrade, deleteTrade, getTrade, listTrades } from '@/api/index'
import type { TradeCreateData, TradeListFilter, TradeRecord } from '@/types/trade'

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

export const useTradeStore = defineStore('trade', () => {
  const trades = ref<TradeRecord[]>([])
  const currentTrade = ref<TradeRecord | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function clearError() {
    error.value = null
  }

  function upsertTrade(updated: TradeRecord) {
    const index = trades.value.findIndex((trade) => trade.id === updated.id)
    if (index >= 0) {
      trades.value[index] = updated
    } else {
      trades.value = [updated, ...trades.value]
    }

    if (currentTrade.value?.id === updated.id) {
      currentTrade.value = updated
    }
  }

  async function fetchTrades(filter?: TradeListFilter) {
    loading.value = true
    clearError()
    try {
      const res = await listTrades(filter)
      trades.value = res.data.items ?? []
      return trades.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载交易记录失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchTradeDetail(tradeId: number) {
    loading.value = true
    clearError()
    try {
      const res = await getTrade(tradeId)
      currentTrade.value = res.data.trade
      return currentTrade.value
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '加载交易详情失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function createNewTrade(data: TradeCreateData) {
    clearError()
    try {
      const res = await createTrade(data)
      if (res.data?.trade) {
        upsertTrade(res.data.trade)
      }
      return res.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '保存交易失败')
      return null
    }
  }

  async function removeTrade(tradeId: number) {
    clearError()
    try {
      await deleteTrade(tradeId)
      trades.value = trades.value.filter((trade) => trade.id !== tradeId)
      if (currentTrade.value?.id === tradeId) {
        currentTrade.value = null
      }
      return true
    } catch (err: unknown) {
      error.value = getErrorMessage(err, '删除交易失败')
      return false
    }
  }

  return {
    trades,
    currentTrade,
    loading,
    error,
    clearError,
    fetchTrades,
    fetchTradeDetail,
    createTrade: createNewTrade,
    removeTrade,
  }
})
