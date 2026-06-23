/**
 * 策略状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listStrategies, getAllConditions } from '@/api/index'
import type { Strategy, ConditionDef } from '@/types/strategy'

export const useStrategyStore = defineStore('strategy', () => {
  const strategies = ref<Strategy[]>([])
  const allConditions = ref<ConditionDef[]>([])
  const loading = ref(false)

  async function fetchStrategies() {
    loading.value = true
    try {
      const res = await listStrategies()
      strategies.value = res.data.strategies
    } finally {
      loading.value = false
    }
  }

  async function fetchAllConditions() {
    if (allConditions.value.length > 0) return // 已加载则跳过
    const res = await getAllConditions()
    allConditions.value = res.data.conditions
  }

  return { strategies, allConditions, loading, fetchStrategies, fetchAllConditions }
})
