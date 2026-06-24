<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { renderMarkdown as renderSafeMarkdown } from '@/utils/markdown'

import PatternCard from '@/components/review/PatternCard.vue'
import ScoreRadar from '@/components/review/ScoreRadar.vue'
import { useReviewStore } from '@/stores/review'
import type { PatternStatus, ReviewScores, TradeReview } from '@/types/review'

const DIMENSION_LABELS: Record<keyof ReviewScores, string> = {
  entry_timing: '入场时机',
  exit_timing: '离场时机',
  stop_loss: '止损纪律',
  take_profit: '止盈执行',
  position_sizing: '仓位管理',
  holding_period: '持仓周期',
  discipline: '交易纪律',
  risk_reward: '盈亏比',
}

const store = useReviewStore()
const route = useRoute()
const router = useRouter()

const activeTab = ref('reviews')
const showDetail = ref(false)
const draftNotes = ref('')
const savingNotes = ref(false)

const selectedTsCode = computed(() => (typeof route.query.ts_code === 'string' ? route.query.ts_code : undefined))
const currentReview = computed(() => store.currentReview)
const currentScores = computed(() => currentReview.value?.scores ?? null)
const dimensionRows = computed(() => {
  const scores = currentScores.value
  if (!scores) {
    return []
  }

  return (Object.keys(DIMENSION_LABELS) as Array<keyof ReviewScores>).map((key) => ({
    key,
    label: DIMENSION_LABELS[key],
    score: scores[key],
  }))
})

const bestDimensionLabel = computed(() => {
  const key = store.stats?.best_dimension as keyof ReviewScores | undefined
  return key ? DIMENSION_LABELS[key] : '--'
})

const worstDimensionLabel = computed(() => {
  const key = store.stats?.worst_dimension as keyof ReviewScores | undefined
  return key ? DIMENSION_LABELS[key] : '--'
})

function pnlClass(value: number) {
  if (value > 0) {
    return 'profit'
  }
  if (value < 0) {
    return 'loss'
  }
  return 'neutral'
}

function renderMarkdown(text: string | null | undefined) {
  if (!text) {
    return '<p>暂无内容</p>'
  }
  return renderSafeMarkdown(text)
}

async function loadPage(tsCode?: string) {
  await Promise.all([
    store.fetchReviews(tsCode),
    store.fetchStats(),
    store.fetchPatterns(),
  ])
}

async function handleViewDetail(review: TradeReview) {
  const detail = await store.fetchReviewDetail(review.id)
  if (!detail) {
    ElMessage.error(store.error ?? '加载复盘详情失败')
    return
  }

  draftNotes.value = detail.user_notes ?? ''
  showDetail.value = true
}

async function handleDelete(review: TradeReview) {
  await ElMessageBox.confirm(`确定删除 ${review.stock_name} 的这条复盘记录吗？`, '删除确认')
  const ok = await store.removeReview(review.id)
  if (!ok) {
    ElMessage.error(store.error ?? '删除复盘失败')
    return
  }

  ElMessage.success('复盘记录已删除')
  await Promise.all([store.fetchStats(), store.fetchPatterns()])
}

async function handleSaveNotes() {
  if (!currentReview.value) {
    return
  }

  savingNotes.value = true
  try {
    const result = await store.saveNotes(currentReview.value.id, draftNotes.value)
    if (!result) {
      ElMessage.error(store.error ?? '保存复盘反思失败')
      return
    }
    ElMessage.success('复盘反思已保存')
  } finally {
    savingNotes.value = false
  }
}

async function handleRefreshPatterns() {
  const result = await store.refreshPatterns()
  if (!result) {
    ElMessage.error(store.error ?? '刷新行为模式失败')
    return
  }
  ElMessage.success('行为模式已刷新')
}

async function handleUpdatePatternStatus(id: number, status: PatternStatus) {
  const result = await store.updatePatternStatus(id, status)
  if (!result) {
    ElMessage.error(store.error ?? '更新行为模式状态失败')
    return
  }
  ElMessage.success(status === 'resolved' ? '已标记为解决' : '已忽略该模式')
}

function handleCloseDetail() {
  store.currentReview = null
  draftNotes.value = ''
}

watch(selectedTsCode, async (tsCode) => {
  await store.fetchReviews(tsCode)
})

onMounted(async () => {
  await loadPage(selectedTsCode.value)
})
</script>

<template>
  <div class="review-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">交易复盘</h2>
        <p class="page-desc">
          复盘计划与执行偏差，观察自己的强项和弱点，并把经验沉淀为可追踪的行为模式。
        </p>
      </div>
      <el-button v-if="selectedTsCode" @click="router.push({ name: 'review' })">查看全部复盘</el-button>
    </div>

    <el-alert
      v-if="selectedTsCode"
      :title="`当前仅显示 ${selectedTsCode} 的复盘记录`"
      type="info"
      :closable="false"
      class="page-alert"
    />

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      :closable="false"
      class="page-alert"
    />

    <div class="stats-grid">
      <el-card shadow="never">
        <el-statistic title="复盘总数" :value="store.stats?.total_reviews ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="平均评分" :precision="1" :value="store.stats?.avg_overall_score ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic
          :title="`最强维度 · ${bestDimensionLabel}`"
          :precision="1"
          :value="store.stats?.avg_scores?.[store.stats.best_dimension as keyof ReviewScores] ?? 0"
        />
      </el-card>
      <el-card shadow="never">
        <el-statistic
          :title="`最弱维度 · ${worstDimensionLabel}`"
          :precision="1"
          :value="store.stats?.avg_scores?.[store.stats.worst_dimension as keyof ReviewScores] ?? 0"
        />
      </el-card>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="复盘列表" name="reviews">
        <el-empty
          v-if="!store.loading && store.reviews.length === 0"
          description="暂无复盘记录，前往持仓页面生成复盘"
        />

        <div v-else v-loading="store.loading" class="review-grid">
          <el-card v-for="review in store.reviews" :key="review.id" shadow="hover" class="review-card">
            <div class="card-head">
              <div>
                <div class="card-title">{{ review.stock_name }}</div>
                <div class="card-code">{{ review.ts_code }}</div>
              </div>
              <div class="score-pill">{{ review.overall_score.toFixed(1) }} / 10</div>
            </div>

            <div class="card-meta">
              <span>{{ review.first_trade_date }} ~ {{ review.last_trade_date }}</span>
              <span>持仓 {{ review.holding_days }} 天</span>
              <span>交易 {{ review.trade_count }} 笔</span>
            </div>

            <div class="card-body">
              <ScoreRadar :scores="review.scores" :size="170" />
              <div class="card-side">
                <div class="metric-label">已实现盈亏</div>
                <div class="metric-value" :class="pnlClass(review.realized_pnl)">
                  {{ review.realized_pnl.toFixed(2) }}
                </div>
                <div class="metric-label">总买入 / 总卖出</div>
                <div class="metric-sub">{{ review.total_buy_amount.toFixed(2) }} / {{ review.total_sell_amount.toFixed(2) }}</div>
              </div>
            </div>

            <div class="card-actions">
              <el-button type="primary" plain @click="handleViewDetail(review)">查看详情</el-button>
              <el-popconfirm title="确定删除这条复盘吗？" @confirm="handleDelete(review)">
                <template #reference>
                  <el-button type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="行为模式" name="patterns">
        <div class="pattern-toolbar">
          <div class="toolbar-copy">
            从多次复盘中提取重复出现的优势与弱点，帮助你把“感觉”变成可追踪的行为信号。
          </div>
          <el-button type="primary" :loading="store.patternLoading" @click="handleRefreshPatterns">
            刷新行为模式分析
          </el-button>
        </div>

        <el-empty
          v-if="!store.patternLoading && store.patterns.length === 0"
          description="需至少 3 条复盘记录才能分析行为模式"
        />

        <div v-else v-loading="store.patternLoading" class="pattern-grid">
          <PatternCard
            v-for="pattern in store.patterns"
            :key="pattern.id"
            :pattern="pattern"
            @update-status="handleUpdatePatternStatus"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showDetail" title="复盘详情" width="980px" @closed="handleCloseDetail">
      <template v-if="currentReview && currentScores">
        <div class="detail-layout">
          <div class="detail-radar">
            <ScoreRadar :scores="currentScores" :size="320" />
          </div>
          <div class="detail-summary">
            <div class="summary-badge">{{ currentReview.stock_name }} · {{ currentReview.ts_code }}</div>
            <div class="summary-score">{{ currentReview.overall_score.toFixed(1) }} / 10</div>
            <div class="summary-range">
              {{ currentReview.first_trade_date }} ~ {{ currentReview.last_trade_date }}，持仓 {{ currentReview.holding_days }} 天
            </div>
            <div class="summary-pnl" :class="pnlClass(currentReview.realized_pnl)">
              已实现盈亏 {{ currentReview.realized_pnl.toFixed(2) }}
            </div>
          </div>
        </div>

        <el-table :data="dimensionRows" size="small" border class="dimension-table">
          <el-table-column label="维度" prop="label" min-width="120" />
          <el-table-column label="评分" min-width="220">
            <template #default="{ row }">
              <div class="dimension-score">
                <span>{{ row.score }} / 10</span>
                <el-progress :percentage="row.score * 10" :stroke-width="10" />
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="markdown-panel">
          <h4>综合分析</h4>
          <div class="markdown-body" v-html="renderMarkdown(currentReview.analysis)" />
        </div>

        <div class="markdown-panel">
          <h4>改进建议</h4>
          <div class="markdown-body" v-html="renderMarkdown(currentReview.improvement)" />
        </div>

        <div class="notes-panel">
          <h4>用户反思</h4>
          <el-input v-model="draftNotes" type="textarea" :rows="5" placeholder="记录这次交易后你自己的复盘心得" />
          <div class="notes-actions">
            <el-button type="primary" :loading="savingNotes" @click="handleSaveNotes">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.review-view {
  max-width: 1280px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: var(--tl-text);
}

.page-desc {
  margin: 0;
  max-width: 760px;
  line-height: 1.7;
  color: var(--tl-text-secondary);
}

.page-alert {
  margin-bottom: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.review-grid,
.pattern-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.review-card {
  border-radius: 18px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--tl-text);
}

.card-code {
  margin-top: 4px;
  font-family: monospace;
  color: var(--tl-text-tertiary);
}

.score-pill {
  min-width: 88px;
  height: 34px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(99,102,241,0.14), rgba(37,208,160,0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--tl-brand);
}

.card-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.card-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.card-side {
  flex: 1;
}

.metric-label {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.metric-value {
  margin: 6px 0 12px;
  font-size: 28px;
  font-weight: 700;
}

.metric-sub {
  line-height: 1.7;
  color: var(--tl-text-secondary);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.pattern-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-copy {
  max-width: 720px;
  line-height: 1.7;
  color: var(--tl-text-secondary);
}

.detail-layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
}

.detail-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-badge {
  font-size: 15px;
  font-weight: 600;
  color: var(--tl-text-secondary);
}

.summary-score {
  font-size: 42px;
  font-weight: 800;
  color: var(--tl-text);
}

.summary-range {
  color: var(--tl-text-tertiary);
}

.summary-pnl {
  font-size: 18px;
  font-weight: 700;
}

.dimension-table {
  margin-bottom: 20px;
}

.dimension-score {
  display: flex;
  align-items: center;
  gap: 12px;
}

.markdown-panel,
.notes-panel {
  margin-bottom: 20px;
}

.markdown-panel h4,
.notes-panel h4 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 700;
  color: var(--tl-text);
}

.markdown-body {
  line-height: 1.8;
  color: var(--tl-text);
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 18px;
}

.notes-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
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

@media (max-width: 960px) {
  .stats-grid,
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .pattern-toolbar,
  .page-header,
  .card-body {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
