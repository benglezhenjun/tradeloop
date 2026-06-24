<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

import { analyzeStock, getKline, getLlmStatus, getPosition, getStockInfo } from '@/api/index'
import KlineChart from '@/components/KlineChart.vue'
import { useWatchlistStore } from '@/stores/watchlist'
import type { Position } from '@/types/position'
import type { KlineItem } from '@/types/watchlist'

type TimeRange = '3m' | '6m' | '1y'

const route = useRoute()
const router = useRouter()
const watchlistStore = useWatchlistStore()

const stockInfo = ref<{
  ts_code: string
  name: string
  industry: string
  market: string
  list_date: string
} | null>(null)
const klines = ref<KlineItem[]>([])
const loading = ref(false)
const timeRange = ref<TimeRange>('6m')

const showAddDialog = ref(false)
const selectedGroupId = ref<number | null>(null)

const llmConfigured = ref(false)
const analysisText = ref<string | null>(null)
const analyzing = ref(false)

const positionSummary = ref<Position | null>(null)

function getTsCode(): string {
  return route.params.tsCode as string
}

function getStartDate(range: TimeRange): string {
  const now = new Date()
  const monthsMap: Record<TimeRange, number> = { '3m': 3, '6m': 6, '1y': 12 }
  now.setMonth(now.getMonth() - monthsMap[range])
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

function pnlClass(value: number | undefined) {
  if (value == null || value === 0) {
    return 'neutral'
  }
  return value > 0 ? 'profit' : 'loss'
}

function renderMd(text: string): string {
  return marked.parse(text) as string
}

async function loadPositionSummary(tsCode: string) {
  try {
    const res = await getPosition(tsCode)
    positionSummary.value = res.data.position
  } catch (error: unknown) {
    if (error instanceof Error && error.message.includes('持仓不存在')) {
      positionSummary.value = null
      return
    }
    positionSummary.value = null
    ElMessage.error(error instanceof Error ? error.message : '加载持仓摘要失败')
  }
}

async function loadData() {
  loading.value = true
  try {
    const tsCode = getTsCode()
    const [infoRes, klineRes] = await Promise.all([
      getStockInfo(tsCode),
      getKline(tsCode, getStartDate(timeRange.value)),
    ])

    stockInfo.value = infoRes.data.basic
    klines.value = klineRes.data.klines
    await loadPositionSummary(tsCode)
  } catch {
    ElMessage.error('加载股票数据失败')
  } finally {
    loading.value = false
  }
}

async function loadKline() {
  try {
    const res = await getKline(getTsCode(), getStartDate(timeRange.value))
    klines.value = res.data.klines
  } catch {
    ElMessage.error('加载 K 线数据失败')
  }
}

async function handleAddToWatchlist() {
  if (selectedGroupId.value == null) {
    ElMessage.warning('请选择分组')
    return
  }

  try {
    const added = await watchlistStore.addStock(selectedGroupId.value, getTsCode())
    if (!added) {
      ElMessage.error('添加失败')
      return
    }
    ElMessage.success('已加入自选股')
    showAddDialog.value = false
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '添加失败')
  }
}

async function handleAnalyze() {
  analyzing.value = true
  analysisText.value = null
  try {
    const res = await analyzeStock(getTsCode())
    analysisText.value = res.data.analysis as string
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : 'LLM 分析失败')
  } finally {
    analyzing.value = false
  }
}

function handleOpenSellTrade() {
  if (!positionSummary.value) {
    return
  }

  router.push({
    name: 'trade',
    query: {
      action: 'create',
      mode: 'from-position',
      ts_code: positionSummary.value.ts_code,
      stock_name: positionSummary.value.stock_name,
      direction: 'sell',
      price: String(positionSummary.value.current_price ?? positionSummary.value.avg_cost),
      quantity: String(positionSummary.value.total_quantity),
      max_quantity: String(positionSummary.value.total_quantity),
      note: '从个股详情页预填',
    },
  })
}

function handleOpenTradeEntry() {
  router.push({
    name: 'trade',
    query: {
      action: 'create',
      mode: 'manual',
      ts_code: stockInfo.value?.ts_code ?? getTsCode(),
      stock_name: stockInfo.value?.name ?? '',
      direction: 'buy',
    },
  })
}

watch(timeRange, () => {
  loadKline()
})

onMounted(async () => {
  await loadData()
  await watchlistStore.fetchGroups()
  try {
    const res = await getLlmStatus()
    llmConfigured.value = (res.data as { configured: boolean }).configured
  } catch {
    llmConfigured.value = false
  }
})
</script>

<template>
  <div class="stock-detail-view" v-loading="loading">
    <div v-if="stockInfo" class="page-header">
      <div class="stock-title">
        <h2 class="page-title">{{ stockInfo.name }}</h2>
        <span class="stock-code">{{ stockInfo.ts_code }}</span>
        <el-tag size="small" type="info">{{ stockInfo.industry }}</el-tag>
        <el-tag size="small">{{ stockInfo.market }}</el-tag>
      </div>

      <div class="header-actions">
        <el-button v-if="llmConfigured" :loading="analyzing" @click="handleAnalyze">
          {{ analyzing ? 'LLM 分析中...' : 'LLM 分析' }}
        </el-button>
        <el-button
          v-if="llmConfigured"
          type="warning"
          @click="router.push({ name: 'plan-generate', params: { tsCode: getTsCode() } })"
        >
          生成交易计划
        </el-button>
        <el-button type="primary" @click="showAddDialog = true">加入自选</el-button>
      </div>
    </div>

    <el-card shadow="never" class="position-card">
      <template #header>持仓摘要</template>
      <template v-if="positionSummary">
        <div class="position-grid">
          <div class="position-item">
            <span class="position-label">当前持仓</span>
            <span class="position-value">{{ positionSummary.total_quantity }}</span>
          </div>
          <div class="position-item">
            <span class="position-label">平均成本</span>
            <span class="position-value">{{ positionSummary.avg_cost.toFixed(2) }}</span>
          </div>
          <div class="position-item">
            <span class="position-label">当前价格</span>
            <span class="position-value">{{ (positionSummary.current_price ?? 0).toFixed(2) }}</span>
          </div>
          <div class="position-item">
            <span class="position-label">持仓市值</span>
            <span class="position-value">{{ (positionSummary.market_value ?? 0).toFixed(2) }}</span>
          </div>
          <div class="position-item">
            <span class="position-label">浮动盈亏</span>
            <span class="position-value" :class="pnlClass(positionSummary.unrealized_pnl)">
              {{ (positionSummary.unrealized_pnl ?? 0).toFixed(2) }}
            </span>
          </div>
          <div class="position-item">
            <span class="position-label">已实现盈亏</span>
            <span class="position-value" :class="pnlClass(positionSummary.realized_pnl)">
              {{ positionSummary.realized_pnl.toFixed(2) }}
            </span>
          </div>
        </div>

        <div class="position-actions">
          <el-button @click="router.push({ name: 'position' })">查看持仓页</el-button>
          <el-button v-if="positionSummary.status === 'holding'" type="danger" @click="handleOpenSellTrade">
            录入卖出
          </el-button>
        </div>
      </template>

      <template v-else>
        <el-empty description="当前股票暂无持仓记录">
          <el-button type="primary" @click="handleOpenTradeEntry">录入交易</el-button>
        </el-empty>
      </template>
    </el-card>

    <div class="time-range-bar">
      <el-radio-group v-model="timeRange" size="small">
        <el-radio-button value="3m">3个月</el-radio-button>
        <el-radio-button value="6m">半年</el-radio-button>
        <el-radio-button value="1y">1年</el-radio-button>
      </el-radio-group>
    </div>

    <el-card shadow="never" class="chart-card">
      <KlineChart :klines="klines" />
    </el-card>

    <el-card v-if="analysisText || analyzing" shadow="never" class="analysis-card">
      <template #header>
        <span class="section-title">LLM 分析</span>
      </template>
      <div v-if="analyzing" class="analysis-loading">正在分析，预计 15 到 40 秒...</div>
      <div v-else class="md-content" v-html="renderMd(analysisText ?? '')" />
    </el-card>

    <el-dialog v-model="showAddDialog" title="加入自选股分组" width="400px">
      <div v-if="watchlistStore.groups.length === 0" class="no-group-tip">
        还没有分组，请先到自选股页面创建分组。
      </div>
      <el-select v-else v-model="selectedGroupId" placeholder="选择分组" style="width: 100%">
        <el-option
          v-for="group in watchlistStore.groups"
          :key="group.id"
          :label="`${group.name}（${group.stock_count}只）`"
          :value="group.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :disabled="watchlistStore.groups.length === 0" @click="handleAddToWatchlist">
          确认添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stock-detail-view {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.stock-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 22px;
}

.stock-code {
  color: var(--tl-text-tertiary);
  font-size: 14px;
  font-family: monospace;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.position-card,
.chart-card,
.analysis-card {
  margin-bottom: 16px;
}

.position-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
}

.position-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.position-label {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.position-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--tl-text);
}

.position-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.time-range-bar {
  margin-bottom: 12px;
}

.section-title {
  font-weight: 600;
}

.analysis-loading {
  padding: 30px;
  text-align: center;
  color: var(--tl-text-tertiary);
}

.no-group-tip {
  padding: 20px 0;
  text-align: center;
  color: var(--tl-text-tertiary);
}

.profit {
  color: var(--up-color);
}

.loss {
  color: var(--down-color);
}

.neutral {
  color: var(--tl-text);
}

.md-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--tl-text);
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3) {
  margin: 12px 0 6px;
  font-weight: 600;
}

.md-content :deep(p) {
  margin: 6px 0;
}

.md-content :deep(ul),
.md-content :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.md-content :deep(blockquote) {
  margin: 6px 0;
  padding: 4px 12px;
  border-left: 4px solid var(--tl-border);
  background: rgba(255,255,255,0.04);
  color: var(--tl-text-tertiary);
}
</style>
