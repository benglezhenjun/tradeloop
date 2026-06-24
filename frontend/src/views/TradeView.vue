<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import TradeForm from '@/components/trade/TradeForm.vue'
import { useTradeStore } from '@/stores/trade'
import type { TradeCreateData, TradeDirection, TradeRecord } from '@/types/trade'

const route = useRoute()
const router = useRouter()
const tradeStore = useTradeStore()

const filters = ref<{
  ts_code: string
  direction: TradeDirection | ''
}>({
  ts_code: '',
  direction: '',
})

const showForm = ref(false)
const showDetail = ref(false)
const submitting = ref(false)
const lockIdentity = ref(false)
const maxQuantity = ref<number | null>(null)
const formTitle = ref('手动录入交易')
const formInitialData = ref<Partial<TradeCreateData>>({})

function todayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function emptyDraft(): Partial<TradeCreateData> {
  return {
    direction: 'buy',
    quantity: 100,
    trade_date: todayString(),
    fee: null,
  }
}

const filteredTradeCount = computed(() => tradeStore.trades.length)

function directionLabel(direction: TradeDirection) {
  return direction === 'buy' ? '买入' : '卖出'
}

function directionType(direction: TradeDirection) {
  return direction === 'buy' ? 'success' : 'danger'
}

function amountLabel(trade: TradeRecord) {
  return trade.amount.toFixed(2)
}

async function loadTrades() {
  await tradeStore.fetchTrades({
    ts_code: filters.value.ts_code.trim() || undefined,
    direction: filters.value.direction || undefined,
  })
}

function openManualCreate() {
  formTitle.value = '手动录入交易'
  formInitialData.value = emptyDraft()
  lockIdentity.value = false
  maxQuantity.value = null
  showForm.value = true
}

function clearRoutePrefill() {
  if (route.query.action !== 'create') {
    return
  }
  router.replace({ name: 'trade' })
}

function parseNumberQuery(key: string): number | null {
  const raw = route.query[key]
  if (typeof raw !== 'string' || raw.trim() === '') {
    return null
  }
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}

function openPrefillFromRoute() {
  if (route.query.action !== 'create') {
    return
  }

  const mode = typeof route.query.mode === 'string' ? route.query.mode : 'manual'
  formInitialData.value = {
    ...emptyDraft(),
    ts_code: typeof route.query.ts_code === 'string' ? route.query.ts_code : '',
    stock_name: typeof route.query.stock_name === 'string' ? route.query.stock_name : '',
    direction: route.query.direction === 'sell' ? 'sell' : 'buy',
    price: parseNumberQuery('price') ?? 0,
    quantity: parseNumberQuery('quantity') ?? 100,
    plan_id: parseNumberQuery('plan_id'),
    note: typeof route.query.note === 'string' ? route.query.note : null,
  }
  lockIdentity.value = mode === 'from-plan' || mode === 'from-position'
  maxQuantity.value = mode === 'from-position' ? parseNumberQuery('max_quantity') : null
  formTitle.value =
    mode === 'from-plan'
      ? '从交易计划预填'
      : mode === 'from-position'
        ? '从持仓页预填卖出'
        : '录入交易'
  showForm.value = true
}

async function handleCreateTrade(payload: TradeCreateData) {
  submitting.value = true
  try {
    const result = await tradeStore.createTrade(payload)
    if (!result) {
      ElMessage.error(tradeStore.error ?? '保存交易失败')
      return
    }
    ElMessage.success('交易记录已保存')
    showForm.value = false
    clearRoutePrefill()
    await loadTrades()
  } finally {
    submitting.value = false
  }
}

async function handleViewDetail(trade: TradeRecord) {
  const detail = await tradeStore.fetchTradeDetail(trade.id)
  if (!detail) {
    ElMessage.error(tradeStore.error ?? '加载交易详情失败')
    return
  }
  showDetail.value = true
}

async function handleDelete(trade: TradeRecord) {
  await ElMessageBox.confirm(
    `确定删除 ${trade.stock_name} ${trade.trade_date} 的这笔${directionLabel(trade.direction)}记录吗？`,
    '删除确认',
  )
  const ok = await tradeStore.removeTrade(trade.id)
  if (!ok) {
    ElMessage.error(tradeStore.error ?? '删除交易失败')
    return
  }
  ElMessage.success('交易记录已删除')
  await loadTrades()
}

function resetFilters() {
  filters.value = { ts_code: '', direction: '' }
  loadTrades()
}

watch(
  () => route.fullPath,
  () => {
    openPrefillFromRoute()
  },
)

onMounted(async () => {
  await loadTrades()
  openPrefillFromRoute()
})
</script>

<template>
  <div class="trade-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">交易记录</h2>
        <p class="page-desc">统一管理手动成交记录，支持从交易计划和持仓页面预填录入。</p>
      </div>
      <el-button type="primary" @click="openManualCreate">手动录入</el-button>
    </div>

    <el-alert
      v-if="route.query.action === 'create'"
      title="当前表单来自页面预填，你可以直接核对后提交，也可以继续调整价格、数量和备注。"
      type="info"
      :closable="false"
      class="page-alert"
    />

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="股票代码">
          <el-input v-model="filters.ts_code" placeholder="如 600000.SH" clearable />
        </el-form-item>
        <el-form-item label="交易方向">
          <el-select v-model="filters.direction" placeholder="全部" clearable style="width: 120px">
            <el-option label="买入" value="buy" />
            <el-option label="卖出" value="sell" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTrades">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-text type="info">当前 {{ filteredTradeCount }} 条记录</el-text>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert
      v-if="tradeStore.error"
      :title="tradeStore.error"
      type="error"
      :closable="false"
      class="page-alert"
    />

    <el-card shadow="never">
      <el-empty v-if="!tradeStore.loading && tradeStore.trades.length === 0" description="暂无交易记录" />
      <el-table v-else v-loading="tradeStore.loading" :data="tradeStore.trades" stripe>
        <el-table-column label="交易日期" min-width="110">
          <template #default="{ row }">{{ row.trade_date }}</template>
        </el-table-column>
        <el-table-column label="股票" min-width="180">
          <template #default="{ row }">
            <div class="stock-cell">
              <span>{{ row.stock_name }}</span>
              <span class="stock-code">{{ row.ts_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="方向" width="90">
          <template #default="{ row }">
            <el-tag :type="directionType(row.direction)" size="small">{{ directionLabel(row.direction) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="100">
          <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="数量" width="100" prop="quantity" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">{{ amountLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="费用" width="100">
          <template #default="{ row }">{{ row.fee.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" prop="note" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="handleViewDetail(row)">详情</el-button>
            <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="showForm"
      :title="formTitle"
      width="760px"
      destroy-on-close
      @closed="clearRoutePrefill"
    >
      <TradeForm
        :initial-data="formInitialData"
        :loading="submitting"
        :lock-identity="lockIdentity"
        :max-quantity="maxQuantity"
        submit-text="保存交易"
        @submit="handleCreateTrade"
        @cancel="showForm = false"
      />
    </el-dialog>

    <el-dialog v-model="showDetail" title="交易详情" width="560px">
      <el-descriptions v-if="tradeStore.currentTrade" :column="1" border size="small">
        <el-descriptions-item label="股票">
          {{ tradeStore.currentTrade.stock_name }}（{{ tradeStore.currentTrade.ts_code }}）
        </el-descriptions-item>
        <el-descriptions-item label="方向">
          {{ directionLabel(tradeStore.currentTrade.direction) }}
        </el-descriptions-item>
        <el-descriptions-item label="成交日期">{{ tradeStore.currentTrade.trade_date }}</el-descriptions-item>
        <el-descriptions-item label="成交时间">
          {{ tradeStore.currentTrade.trade_time || '未填写' }}
        </el-descriptions-item>
        <el-descriptions-item label="价格">{{ tradeStore.currentTrade.price.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="数量">{{ tradeStore.currentTrade.quantity }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ tradeStore.currentTrade.amount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="费用">{{ tradeStore.currentTrade.fee.toFixed(4) }}</el-descriptions-item>
        <el-descriptions-item label="计划 ID">
          {{ tradeStore.currentTrade.plan_id ?? '未关联' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注">
          {{ tradeStore.currentTrade.note || '无' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<style scoped>
.trade-view {
  max-width: 1240px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: var(--tl-text);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--tl-text-tertiary);
}

.page-alert,
.filter-card {
  margin-bottom: 16px;
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stock-code {
  font-size: 12px;
  color: var(--tl-text-tertiary);
  font-family: monospace;
}
</style>
