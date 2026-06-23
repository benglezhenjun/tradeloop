/**
 * 应用全局状态
 * 存放不属于某个特定业务模块的全局信息，如后端连接状态、数据统计
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { checkHealth, getDataStats } from '@/api/index'

export const useAppStore = defineStore('app', () => {
  const backendOnline = ref(false)
  const stats = ref({
    stock_count: 0,
    quote_count: 0,
    financial_count: 0,
    latest_trade_date: null as string | null,
    strategy_count: 0,
  })

  async function checkBackend() {
    try {
      await checkHealth()
      backendOnline.value = true
    } catch {
      backendOnline.value = false
    }
  }

  async function fetchStats() {
    try {
      const res = await getDataStats()
      stats.value = res.data
    } catch {
      // 静默失败，不影响其他功能
    }
  }

  return { backendOnline, stats, checkBackend, fetchStats }
})
