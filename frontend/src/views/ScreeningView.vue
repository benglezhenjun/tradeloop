<template>
  <div class="screening-view">
    <div class="page-header">
      <h2 class="page-title">策略筛选</h2>
      <p class="page-desc">选择策略并运行筛选，查看符合条件的候选股票</p>
    </div>

    <el-card shadow="never" class="control-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <div class="form-label">选择策略</div>
          <el-select
            v-model="selectedStrategyId"
            placeholder="请选择策略"
            style="width: 100%"
            :loading="strategyStore.loading"
          >
            <el-option
              v-for="s in strategyStore.strategies.filter((s) => s.is_enabled)"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </el-col>
        <el-col :span="7">
          <div class="form-label">交易日期</div>
          <el-select v-model="selectedDate" placeholder="默认最新交易日" style="width: 100%">
            <el-option
              v-for="d in screeningStore.availableDates"
              :key="d"
              :label="formatDate(d)"
              :value="d"
            />
          </el-select>
        </el-col>
        <el-col :span="9" style="display: flex; align-items: flex-end; gap: 8px;">
          <div style="height: 22px;" />
          <el-button
            type="primary"
            :loading="screeningStore.loading"
            :disabled="!selectedStrategyId"
            @click="runScreening"
            size="large"
          >
            {{ screeningStore.loading ? '筛选中...' : '运行筛选' }}
          </el-button>
          <el-button
            v-if="selectedStrategyId"
            @click="$router.push(`/strategies/${selectedStrategyId}`)"
          >
            编辑策略
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-alert
      v-if="screeningStore.error"
      :title="screeningStore.error"
      type="error"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-card v-if="screeningStore.result" shadow="never" class="result-card">
      <template #header>
        <div class="result-header">
          <div>
            <span class="result-title">「{{ screeningStore.result.strategy_name }}」筛选结果</span>
            <span class="result-meta">
              {{ formatDate(screeningStore.result.trade_date) }}
              · 共 <strong>{{ screeningStore.result.count }}</strong> 只
              · 耗时 {{ screeningStore.result.duration_ms }}ms
            </span>
          </div>
          <div class="result-actions">
            <el-button
              size="small"
              type="primary"
              :disabled="screeningStore.result.candidates.length === 0"
              @click="openBatchAddToWatchlist"
            >
              批量加入自选
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="screeningStore.result.candidates"
        stripe
        size="small"
        style="width: 100%"
      >
        <el-table-column prop="rank" label="排名" width="60" align="center" />
        <el-table-column label="代码" width="110">
          <template #default="{ row }">
            <a class="stock-link" @click="$router.push(`/stock/${row.ts_code}`)">{{ row.ts_code }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="100" />
        <el-table-column prop="industry" label="行业" width="90" show-overflow-tooltip />
        <el-table-column prop="close" label="收盘价" width="90" align="right">
          <template #default="{ row }">{{ row.close?.toFixed(2) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="90" align="right">
          <template #default="{ row }">
            <span :class="row.pct_chg > 0 ? 'up' : row.pct_chg < 0 ? 'down' : ''">
              {{ row.pct_chg != null ? (row.pct_chg > 0 ? '+' : '') + row.pct_chg.toFixed(2) + '%' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成交额(亿)" width="100" align="right">
          <template #default="{ row }">{{ row.amount_yi?.toFixed(2) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="总市值(亿)" width="100" align="right">
          <template #default="{ row }">{{ row.total_mv_yi?.toFixed(0) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openAddToWatchlist(row.ts_code)">
              加自选
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="screeningStore.result.count === 0" class="empty-result">
        本次筛选无结果，可以尝试放宽条件参数。
      </div>
    </el-card>

    <el-empty
      v-else-if="!screeningStore.loading && !screeningStore.error"
      description="选择策略并点击运行筛选。"
      :image-size="100"
    />

    <el-dialog v-model="showAddWatchlist" title="加入自选股分组" width="400px" @close="resetSingleAddDialog">
      <p v-if="addingTsCode">将 <strong>{{ addingTsCode }}</strong> 加入：</p>
      <div v-if="watchlistStore.groups.length === 0" class="no-group-tip">
        还没有分组，请先到自选股页面创建分组
      </div>
      <el-select v-else v-model="addTargetGroupId" placeholder="选择分组" style="width: 100%">
        <el-option
          v-for="g in watchlistStore.groups"
          :key="g.id"
          :label="`${g.name}（${g.stock_count}只）`"
          :value="g.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showAddWatchlist = false">取消</el-button>
        <el-button type="primary" @click="handleAddToWatchlist" :disabled="!addTargetGroupId">
          确定
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showBatchAddWatchlist"
      title="批量加入自选股分组"
      width="420px"
      @close="resetBatchAddDialog"
    >
      <p class="batch-tip">
        当前结果共 <strong>{{ screeningStore.result?.candidates.length ?? 0 }}</strong> 只，将一次加入所选分组。
      </p>
      <div v-if="watchlistStore.groups.length === 0" class="no-group-tip">
        还没有分组，请先到自选股页面创建分组
      </div>
      <el-select v-else v-model="batchTargetGroupId" placeholder="选择分组" style="width: 100%">
        <el-option
          v-for="g in watchlistStore.groups"
          :key="g.id"
          :label="`${g.name}（${g.stock_count}只）`"
          :value="g.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showBatchAddWatchlist = false">取消</el-button>
        <el-button
          type="primary"
          :loading="batchAddLoading"
          :disabled="watchlistStore.groups.length === 0 || batchAddLoading || !batchTargetGroupId"
          @click="handleBatchAddToWatchlist"
        >
          确定批量加入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useStrategyStore } from '@/stores/strategy'
import { useScreeningStore } from '@/stores/screening'
import { useWatchlistStore } from '@/stores/watchlist'
import type { BatchAddWatchlistResult } from '@/types/watchlist'

const route = useRoute()
const strategyStore = useStrategyStore()
const screeningStore = useScreeningStore()
const watchlistStore = useWatchlistStore()

const selectedStrategyId = ref<number | null>(null)
const selectedDate = ref<string | null>(null)

const showAddWatchlist = ref(false)
const addingTsCode = ref('')
const addTargetGroupId = ref<number | null>(null)

const showBatchAddWatchlist = ref(false)
const batchTargetGroupId = ref<number | null>(null)
const batchAddLoading = ref(false)

onMounted(async () => {
  await Promise.all([strategyStore.fetchStrategies(), screeningStore.fetchDates()])

  const queryId = route.query.strategyId ? Number(route.query.strategyId) : null
  if (queryId) {
    selectedStrategyId.value = queryId
  } else {
    const firstEnabled = strategyStore.strategies.find((s) => s.is_enabled)
    if (firstEnabled) {
      selectedStrategyId.value = firstEnabled.id
    }
  }

  await watchlistStore.fetchGroups()
})

async function runScreening() {
  if (!selectedStrategyId.value) return
  await screeningStore.run(selectedStrategyId.value, selectedDate.value ?? undefined)
}

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

async function loadWatchlistGroups(): Promise<boolean> {
  try {
    await watchlistStore.fetchGroups()
    return true
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '加载分组失败')
    return false
  }
}

async function openAddToWatchlist(tsCode: string) {
  addingTsCode.value = tsCode
  addTargetGroupId.value = null
  if (!(await loadWatchlistGroups())) return
  showAddWatchlist.value = true
}

async function openBatchAddToWatchlist() {
  if (!screeningStore.result || screeningStore.result.candidates.length === 0) return
  batchTargetGroupId.value = null
  if (!(await loadWatchlistGroups())) return
  showBatchAddWatchlist.value = true
}

function resetSingleAddDialog() {
  addingTsCode.value = ''
  addTargetGroupId.value = null
}

function resetBatchAddDialog() {
  batchTargetGroupId.value = null
  batchAddLoading.value = false
}

function formatBatchAddSummary(result: BatchAddWatchlistResult): string {
  return `成功 ${result.added}，只已存在 ${result.skipped_existing}，只无效 ${result.skipped_invalid}`
}

async function handleAddToWatchlist() {
  if (!addTargetGroupId.value) return
  try {
    const added = await watchlistStore.addStock(addTargetGroupId.value, addingTsCode.value)
    if (!added) {
      ElMessage.error('添加失败')
      return
    }
    ElMessage.success(`已添加 ${addingTsCode.value}`)
    showAddWatchlist.value = false
    resetSingleAddDialog()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '添加失败')
  }
}

async function handleBatchAddToWatchlist() {
  if (!batchTargetGroupId.value || !screeningStore.result) return
  const codes = screeningStore.result.candidates.map((candidate) => candidate.ts_code)
  batchAddLoading.value = true
  try {
    const result = await watchlistStore.batchAdd(batchTargetGroupId.value, codes)
    const message = formatBatchAddSummary(result)
    if (result.added > 0) {
      ElMessage.success(message)
    } else {
      ElMessage.warning(message)
    }
    showBatchAddWatchlist.value = false
    resetBatchAddDialog()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '批量加入失败')
  } finally {
    batchAddLoading.value = false
  }
}
</script>

<style scoped>
.screening-view {
  max-width: 1100px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 6px;
  color: var(--tl-text);
}

.page-desc {
  color: var(--tl-text-tertiary);
  margin: 0;
  font-size: 13px;
}

.control-card {
  margin-bottom: 16px;
}

.form-label {
  font-size: 12px;
  color: var(--tl-text-tertiary);
  margin-bottom: 6px;
}

.result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.result-title {
  font-weight: 600;
  font-size: 14px;
}

.result-meta {
  display: block;
  font-size: 13px;
  color: var(--tl-text-tertiary);
  margin-top: 4px;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.up {
  color: var(--up-color);
}

.down {
  color: var(--down-color);
}

.empty-result {
  text-align: center;
  padding: 20px;
  color: var(--tl-text-tertiary);
  font-size: 13px;
}

.no-group-tip {
  color: var(--tl-text-tertiary);
  text-align: center;
  padding: 12px 0;
}

.batch-tip {
  margin: 0 0 12px;
  color: var(--tl-text-secondary);
  line-height: 1.6;
}

.stock-link {
  color: var(--tl-brand);
  cursor: pointer;
  font-family: monospace;
}

.stock-link:hover {
  text-decoration: underline;
}
</style>
