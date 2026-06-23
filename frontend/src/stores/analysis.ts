import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLlmStatus, generateDailyReport, listReports, getReport } from '@/api/index'
import type { LlmStatus, DailyReportResult, ReportListItem, ReportDetail } from '@/types/analysis'

export const useAnalysisStore = defineStore('analysis', () => {
  const llmStatus = ref<LlmStatus | null>(null)
  const currentReport = ref<DailyReportResult | null>(null)
  const historyList = ref<ReportListItem[]>([])
  const historyDetail = ref<ReportDetail | null>(null)
  const generating = ref(false)
  const loadingHistory = ref(false)
  const error = ref<string | null>(null)

  async function fetchLlmStatus() {
    try {
      const res = await getLlmStatus()
      llmStatus.value = res.data as LlmStatus
    } catch {
      llmStatus.value = { configured: false, provider: '', model: '', base_url: '' }
    }
  }

  async function generateReport() {
    generating.value = true
    error.value = null
    try {
      const res = await generateDailyReport()
      currentReport.value = res.data as DailyReportResult
      // 刷新历史列表
      await fetchHistory('daily')
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '生成失败'
    } finally {
      generating.value = false
    }
  }

  async function fetchHistory(reportType?: string) {
    loadingHistory.value = true
    try {
      const res = await listReports(reportType)
      historyList.value = res.data as ReportListItem[]
    } finally {
      loadingHistory.value = false
    }
  }

  async function loadHistoryDetail(id: number) {
    const res = await getReport(id)
    historyDetail.value = res.data as ReportDetail
  }

  return {
    llmStatus, currentReport, historyList, historyDetail,
    generating, loadingHistory, error,
    fetchLlmStatus, generateReport, fetchHistory, loadHistoryDetail,
  }
})
