<template>
  <div class="analysis-view">

    <!-- LLM 未配置 -->
    <el-alert
      v-if="store.llmStatus && !store.llmStatus.configured"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    >
      <template #title>
        LLM 未配置，分析功能不可用。请在
        <code>config/local.toml</code> 的 <code>[llm]</code> 节填写 <code>api_key</code>
        后重启后端。
      </template>
    </el-alert>

    <el-row :gutter="16">

      <!-- 左侧：控制区 + 历史列表 -->
      <el-col :span="6">
        <!-- LLM 状态 -->
        <el-card shadow="never" class="status-card" v-if="store.llmStatus">
          <div class="status-row">
            <el-badge :is-dot="true" :type="store.llmStatus.configured ? 'success' : 'danger'">
              <span class="status-label">
                {{ store.llmStatus.configured ? '已配置' : '未配置' }}
              </span>
            </el-badge>
            <span class="status-model" v-if="store.llmStatus.configured">
              {{ store.llmStatus.provider }} / {{ store.llmStatus.model }}
            </span>
          </div>
        </el-card>

        <!-- 生成按钮 -->
        <el-button
          type="primary"
          :loading="store.generating"
          :disabled="!store.llmStatus?.configured"
          class="generate-btn"
          @click="handleGenerate"
        >
          {{ store.generating ? '生成中（请耐心等待）…' : '生成今日日报' }}
        </el-button>

        <el-divider>历史报告</el-divider>

        <!-- 历史列表 -->
        <div v-loading="store.loadingHistory">
          <el-empty v-if="store.historyList.length === 0" description="暂无历史记录" :image-size="60" />
          <div
            v-for="item in store.historyList"
            :key="item.id"
            class="history-item"
            :class="{ active: selectedId === item.id }"
            @click="loadHistory(item.id)"
          >
            <div class="history-date">{{ formatDate(item.generated_at) }}</div>
            <div class="history-type">{{ item.report_type === 'daily' ? '日报' : `个股 ${item.ts_code ?? ''}` }}</div>
          </div>
        </div>
      </el-col>

      <!-- 右侧：报告内容 -->
      <el-col :span="18">
        <!-- 生成结果 Tab 视图 -->
        <el-card shadow="never" v-if="activeReport">
          <template #header>
            <span class="section-title">
              {{ activeReport.generated_at ? formatDate(activeReport.generated_at) : '' }} 分析报告
            </span>
          </template>

          <el-tabs v-model="activeTab">
            <el-tab-pane label="综合日报" name="summary">
              <div class="md-content" v-html="renderMd(sections?.summary ?? fullContent)" />
            </el-tab-pane>
            <el-tab-pane label="市场环境" name="market" v-if="sections?.market">
              <div class="md-content" v-html="renderMd(sections.market)" />
            </el-tab-pane>
            <el-tab-pane label="行业热度" name="industry" v-if="sections?.industry">
              <div class="md-content" v-html="renderMd(sections.industry)" />
            </el-tab-pane>
            <el-tab-pane label="自选股动态" name="watchlist" v-if="sections?.watchlist">
              <div class="md-content" v-html="renderMd(sections.watchlist)" />
            </el-tab-pane>
            <el-tab-pane label="筛选回顾" name="screening" v-if="sections?.screening">
              <div class="md-content" v-html="renderMd(sections.screening)" />
            </el-tab-pane>
          </el-tabs>
        </el-card>

        <!-- 空状态 -->
        <el-empty
          v-else-if="!store.generating"
          description="点击左侧「生成今日日报」开始分析"
          :image-size="100"
        />

        <!-- 生成中占位 -->
        <div v-if="store.generating" class="generating-placeholder">
          <el-icon class="is-loading" size="32"><Loading /></el-icon>
          <p>正在调用 LLM 分析市场数据，预计 30-90 秒…</p>
        </div>

        <!-- 错误提示 -->
        <el-alert
          v-if="store.error"
          type="error"
          :title="store.error"
          show-icon
          :closable="false"
          style="margin-top: 16px"
        />
      </el-col>

    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { marked } from 'marked'
import { Loading } from '@element-plus/icons-vue'
import { useAnalysisStore } from '@/stores/analysis'
import type { ReportDetail, DailyReportResult } from '@/types/analysis'

const store = useAnalysisStore()

const activeTab = ref('summary')
const selectedId = ref<number | null>(null)

// 当前展示的报告（新生成的或历史加载的）
const activeReport = computed<DailyReportResult | ReportDetail | null>(() => {
  if (store.historyDetail && selectedId.value !== null) return store.historyDetail
  if (store.currentReport) return store.currentReport
  return null
})

const sections = computed<Record<string, string> | null>(() => {
  const r = activeReport.value
  if (!r) return null
  if ('sections' in r && r.sections) return r.sections as Record<string, string>
  return null
})

const fullContent = computed<string>(() => {
  const r = activeReport.value
  if (!r) return ''
  if ('report' in r) return r.report   // DailyReportResult
  if ('content' in r) return r.content // ReportDetail
  return ''
})

function renderMd(text: string): string {
  return marked.parse(text) as string
}

function formatDate(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16)
}

async function handleGenerate() {
  selectedId.value = null
  store.historyDetail = null
  activeTab.value = 'summary'
  await store.generateReport()
}

async function loadHistory(id: number) {
  selectedId.value = id
  store.currentReport = null
  activeTab.value = 'summary'
  await store.loadHistoryDetail(id)
}

onMounted(async () => {
  await store.fetchLlmStatus()
  await store.fetchHistory('daily')
})
</script>

<style scoped>
.analysis-view {
  max-width: 1200px;
}

.status-card {
  margin-bottom: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  font-size: 13px;
  font-weight: 600;
}

.status-model {
  font-size: 12px;
  color: #909399;
}

.generate-btn {
  width: 100%;
  margin-bottom: 8px;
}

.history-item {
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  border-left: 3px solid transparent;
  margin-bottom: 4px;
  transition: background 0.15s;
}

.history-item:hover {
  background: #f5f7fa;
}

.history-item.active {
  background: #ecf5ff;
  border-left-color: #409eff;
}

.history-date {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.history-type {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
}

.md-content {
  line-height: 1.8;
  font-size: 14px;
  color: #303133;
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
}

.md-content :deep(p) {
  margin: 8px 0;
}

.md-content :deep(ul),
.md-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.md-content :deep(blockquote) {
  border-left: 4px solid #dcdfe6;
  padding: 4px 12px;
  color: #909399;
  margin: 8px 0;
  background: #f5f7fa;
}

.md-content :deep(strong) {
  color: #303133;
}

.generating-placeholder {
  text-align: center;
  padding: 60px 0;
  color: #909399;
}

.generating-placeholder p {
  margin-top: 16px;
  font-size: 14px;
}
</style>
