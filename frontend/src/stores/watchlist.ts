/**
 * Watchlist state management
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listWatchlistGroups,
  getGroupStocks,
  getAllWatchlistStocks,
  createWatchlistGroup,
  deleteWatchlistGroup,
  addStockToGroup,
  removeStockFromGroup,
  batchAddStocks,
} from '@/api/index'
import type { BatchAddWatchlistResult, WatchlistGroup, WatchlistStock } from '@/types/watchlist'

export const useWatchlistStore = defineStore('watchlist', () => {
  const groups = ref<WatchlistGroup[]>([])
  const stocks = ref<WatchlistStock[]>([])
  const currentGroupId = ref<number | null>(null)
  const loading = ref(false)

  async function fetchGroups() {
    const res = await listWatchlistGroups()
    groups.value = res.data.groups
  }

  async function fetchStocks(groupId?: number | null) {
    loading.value = true
    try {
      if (groupId != null) {
        const res = await getGroupStocks(groupId)
        stocks.value = res.data.stocks
      } else {
        const res = await getAllWatchlistStocks()
        stocks.value = res.data.stocks
      }
    } finally {
      loading.value = false
    }
  }

  async function refreshAfterMutation() {
    const refreshTasks = [
      fetchGroups().catch((error: unknown) => error),
      fetchStocks(currentGroupId.value).catch((error: unknown) => error),
    ]
    const results = await Promise.all(refreshTasks)
    const refreshErrors = results.filter((result) => result !== undefined)

    if (refreshErrors.length > 0) {
      console.error('Watchlist refresh failed after mutation', refreshErrors)
    }
  }

  async function addGroup(name: string, description = ''): Promise<boolean> {
    try {
      await createWatchlistGroup(name, description)
      await refreshAfterMutation()
      return true
    } catch {
      return false
    }
  }

  async function removeGroup(id: number): Promise<boolean> {
    try {
      await deleteWatchlistGroup(id)
      if (currentGroupId.value === id) {
        currentGroupId.value = null
      }
      await refreshAfterMutation()
      return true
    } catch {
      return false
    }
  }

  async function addStock(groupId: number, tsCode: string, note = ''): Promise<boolean> {
    try {
      await addStockToGroup(groupId, tsCode, note)
      await refreshAfterMutation()
      return true
    } catch {
      return false
    }
  }

  async function removeStock(groupId: number, tsCode: string): Promise<boolean> {
    try {
      await removeStockFromGroup(groupId, tsCode)
      await refreshAfterMutation()
      return true
    } catch {
      return false
    }
  }

  async function batchAdd(groupId: number, tsCodes: string[]): Promise<BatchAddWatchlistResult> {
    const res = await batchAddStocks(groupId, tsCodes)
    await refreshAfterMutation()
    return res.data as BatchAddWatchlistResult
  }

  return {
    groups,
    stocks,
    currentGroupId,
    loading,
    fetchGroups,
    fetchStocks,
    addGroup,
    removeGroup,
    addStock,
    removeStock,
    batchAdd,
  }
})
