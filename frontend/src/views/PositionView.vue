<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { usePositionStore } from '@/stores/position'
import { useReviewStore } from '@/stores/review'
import type { Position, PositionStatus } from '@/types/position'
import type { TradeReview } from '@/types/review'

const router = useRouter()
const positionStore = usePositionStore()
const reviewStore = useReviewStore()

const activeTab = ref<PositionStatus>('holding')
const showDetail = ref(false)

const positions = computed(() => positionStore.positions)
const reviewMap = computed<Record<string, TradeReview>>(() => {
  const map: Record<string, TradeReview> = {}
  for (const review of reviewStore.reviews) {
    const current = map[review.ts_code]
    if (!current || review.created_at > current.created_at) {
      map[review.ts_code] = review
    }
  }
  return map
})

function latestReviewFor(tsCode: string) {
  return reviewMap.value[tsCode]
}

function statusLabel(status: PositionStatus) {
  return status === 'holding' ? '当前持仓' : '已清仓'
}

function statusType(status: PositionStatus) {
  return status === 'holding' ? 'success' : 'info'
}

function directionType(direction: 'buy' | 'sell') {
  return direction === 'buy' ? 'success' : 'danger'
}

function pnlClass(value: number | undefined) {
  if (value == null || value === 0) {
    return 'neutral'
  }
  return value > 0 ? 'profit' : 'loss'
}

async function loadPage() {
  await Promise.all([
    positionStore.fetchPositions({ status: activeTab.value }),
    positionStore.fetchSummary(),
    reviewStore.fetchReviews(),
  ])
}

async function handleViewDetail(position: Position) {
  const detail = await positionStore.fetchPositionDetail(position.ts_code)
  if (!detail) {
    ElMessage.error(positionStore.error ?? '加载持仓详情失败')
    return
  }
  showDetail.value = true
}

async function handleRecalc(position: Position) {
  const result = await positionStore.recalc(position.ts_code)
  if (!result) {
    ElMessage.error(positionStore.error ?? '重算持仓失败')
    return
  }
  ElMessage.success('持仓已按交易记录重算')
  await loadPage()
}

function handleSell(position: Position) {
  router.push({
    name: 'trade',
    query: {
      action: 'create',
      mode: 'from-position',
      ts_code: position.ts_code,
      stock_name: position.stock_name,
      direction: 'sell',
      price: String(position.current_price ?? position.avg_cost),
      quantity: String(position.total_quantity),
      max_quantity: String(position.total_quantity),
      note: '从持仓页预填',
    },
  })
}

async function handleGenerateReview(position: Position) {
  const result = await reviewStore.generateReview(position.ts_code)
  if (!result) {
    ElMessage.error(reviewStore.error ?? '生成复盘失败')
    return
  }

  ElMessage.success('复盘已生成')
  router.push({ name: 'review', query: { ts_code: position.ts_code } })
}

function handleViewReview(position: Position) {
  router.push({ name: 'review', query: { ts_code: position.ts_code } })
}

function handleCloseDetail() {
  positionStore.currentPosition = null
  positionStore.currentTrades = []
}

watch(activeTab, () => {
  loadPage()
})

onMounted(async () => {
  await loadPage()
})
</script>

<template>
  <div class="position-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">持仓</h2>
        <p class="page-desc">查看当前持仓、已清仓记录和按交易记录重算后的结果。</p>
      </div>
      <el-button type="primary" @click="router.push({ name: 'trade' })">去录入交易</el-button>
    </div>

    <el-alert
      v-if="positionStore.error"
      :title="positionStore.error"
      type="error"
      :closable="false"
      class="page-alert"
    />

    <div class="summary-grid">
      <el-card shadow="never">
        <div class="summary-label">当前持仓数</div>
        <div class="summary-value">{{ positionStore.summary?.holding_count ?? 0 }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-label">持仓市值</div>
        <div class="summary-value">{{ (positionStore.summary?.total_market_value ?? 0).toFixed(2) }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-label">浮动盈亏</div>
        <div class="summary-value" :class="pnlClass(positionStore.summary?.total_unrealized_pnl)">
          {{ (positionStore.summary?.total_unrealized_pnl ?? 0).toFixed(2) }}
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-label">累计已实现</div>
        <div class="summary-value" :class="pnlClass(positionStore.summary?.total_realized_pnl)">
          {{ (positionStore.summary?.total_realized_pnl ?? 0).toFixed(2) }}
        </div>
      </el-card>
    </div>

    <el-tabs v-model="activeTab" class="position-tabs">
      <el-tab-pane label="当前持仓" name="holding" />
      <el-tab-pane label="已清仓" name="closed" />
    </el-tabs>

    <el-empty v-if="!positionStore.loading && positions.length === 0" :description="`暂无${statusLabel(activeTab)}`" />

    <div v-else v-loading="positionStore.loading" class="position-grid">
      <el-card v-for="position in positions" :key="position.ts_code" shadow="hover" class="position-card">
        <div class="card-top">
          <div>
            <div class="card-title">{{ position.stock_name }}</div>
            <div class="card-subtitle">{{ position.ts_code }}</div>
          </div>
          <el-tag :type="statusType(position.status)">{{ statusLabel(position.status) }}</el-tag>
        </div>

        <div class="metric-grid">
          <div class="metric-item">
            <span class="metric-label">持仓数量</span>
            <span class="metric-value">{{ position.total_quantity }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">持仓成本</span>
            <span class="metric-value">{{ position.avg_cost.toFixed(2) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">当前价格</span>
            <span class="metric-value">{{ (position.current_price ?? 0).toFixed(2) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">持仓市值</span>
            <span class="metric-value">{{ (position.market_value ?? 0).toFixed(2) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">浮动盈亏</span>
            <span class="metric-value" :class="pnlClass(position.unrealized_pnl)">
              {{ (position.unrealized_pnl ?? 0).toFixed(2) }}
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">已实现盈亏</span>
            <span class="metric-value" :class="pnlClass(position.realized_pnl)">
              {{ (position.realized_pnl ?? 0).toFixed(2) }}
            </span>
          </div>
        </div>

        <div class="card-footer">
          <div class="card-date">最近交易：{{ position.last_trade_date }}</div>
          <div class="card-actions">
            <template v-if="position.status === 'closed'">
              <el-tag v-if="latestReviewFor(position.ts_code)" size="small" effect="plain" type="success">
                复盘 {{ latestReviewFor(position.ts_code)?.overall_score?.toFixed(1) ?? '--' }}/10
              </el-tag>
              <el-button
                v-if="latestReviewFor(position.ts_code)"
                size="small"
                text
                type="primary"
                @click="handleViewReview(position)"
              >
                查看复盘
              </el-button>
              <el-button
                v-else
                size="small"
                text
                type="primary"
                @click="handleGenerateReview(position)"
              >
                生成复盘
              </el-button>
            </template>
            <el-button size="small" text type="primary" @click="handleViewDetail(position)">交易时间线</el-button>
            <el-button size="small" text @click="handleRecalc(position)">重算</el-button>
            <el-button
              v-if="position.status === 'holding'"
              size="small"
              text
              type="danger"
              @click="handleSell(position)"
            >
              卖出
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-drawer v-model="showDetail" title="持仓详情" size="560px" @closed="handleCloseDetail">
      <template v-if="positionStore.currentPosition">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="股票">
            {{ positionStore.currentPosition.stock_name }}（{{ positionStore.currentPosition.ts_code }}）
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ statusLabel(positionStore.currentPosition.status) }}
          </el-descriptions-item>
          <el-descriptions-item label="持仓数量">
            {{ positionStore.currentPosition.total_quantity }}
          </el-descriptions-item>
          <el-descriptions-item label="平均成本">
            {{ positionStore.currentPosition.avg_cost.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="当前价格">
            {{ (positionStore.currentPosition.current_price ?? 0).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="持仓市值">
            {{ (positionStore.currentPosition.market_value ?? 0).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="浮动盈亏">
            {{ (positionStore.currentPosition.unrealized_pnl ?? 0).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="已实现盈亏">
            {{ (positionStore.currentPosition.realized_pnl ?? 0).toFixed(2) }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 class="section-title">交易时间线</h4>
        <el-table :data="positionStore.currentTrades" size="small" border>
          <el-table-column label="日期" prop="trade_date" width="110" />
          <el-table-column label="方向" width="90">
            <template #default="{ row }">
              <el-tag :type="directionType(row.direction)" size="small">{{ row.direction === 'buy' ? '买入' : '卖出' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" width="90">
            <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="数量" prop="quantity" width="90" />
          <el-table-column label="费用" width="90">
            <template #default="{ row }">{{ row.fee.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column label="备注" prop="note" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.position-view {
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
.position-tabs {
  margin-bottom: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.summary-label {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.summary-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 600;
  color: var(--tl-text);
}

.position-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.position-card {
  min-height: 244px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--tl-text);
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--tl-text-tertiary);
  font-family: monospace;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  padding: 12px 0;
  border-top: 1px solid var(--tl-border);
  border-bottom: 1px solid var(--tl-border);
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--tl-text);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.card-date {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.card-actions {
  display: flex;
  gap: 4px;
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

.section-title {
  margin: 18px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--tl-text);
}
</style>
