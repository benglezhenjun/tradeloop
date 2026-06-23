<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import PlanEditor from '@/components/plan/PlanEditor.vue'
import { usePlanStore } from '@/stores/plan'
import {
  DIRECTION_LABELS,
  STATUS_LABELS,
  TIER_LABELS,
  type EditablePlanDraft,
  type PlanEditorMode,
  type PlanStatus,
  type TradingPlan,
} from '@/types/plan'
import {
  buildPlanCreateData,
  buildPlanUpdateData,
  createEmptyPlanDraft,
  draftFromPlan,
  formatLocalDateTime,
  formatPlanTierLabel,
  isEditablePlan,
} from '@/utils/plan'

const store = usePlanStore()
const router = useRouter()

const activeTab = ref<'all' | PlanStatus>('all')
const showDetail = ref(false)
const showEditor = ref(false)
const editorMode = ref<PlanEditorMode>('manual-create')
const editingPlanId = ref<number | null>(null)
const editorDraft = ref<EditablePlanDraft>(createEmptyPlanDraft())
const submitting = ref(false)

const editorTitle = computed(() => (editorMode.value === 'manual-create' ? '手动创建交易计划' : '编辑交易计划'))
const editorSubmitText = computed(() => (editorMode.value === 'manual-create' ? '创建计划' : '保存修改'))

function tierType(tierLabel: TradingPlan['tier_label']): 'danger' | 'warning' | 'success' | 'info' {
  if (tierLabel === 'aggressive') {
    return 'danger'
  }
  if (tierLabel === 'balanced') {
    return 'warning'
  }
  if (tierLabel === 'conservative') {
    return 'success'
  }
  return 'info'
}

function statusType(status: PlanStatus): '' | 'success' | 'info' {
  if (status === 'executed') {
    return 'success'
  }
  if (status === 'abandoned') {
    return 'info'
  }
  return ''
}

async function loadPlans() {
  const status = activeTab.value === 'all' ? undefined : activeTab.value
  await store.fetchPlans(status ? { status } : undefined)
}

function openManualCreate() {
  store.clearError()
  editorMode.value = 'manual-create'
  editingPlanId.value = null
  editorDraft.value = createEmptyPlanDraft()
  showEditor.value = true
}

function openPlanEditor(plan: TradingPlan) {
  if (!isEditablePlan(plan)) {
    ElMessage.warning('只有待执行状态的计划可以编辑')
    return
  }

  store.clearError()
  editorMode.value = 'existing-edit'
  editingPlanId.value = plan.id
  editorDraft.value = draftFromPlan(plan)
  showEditor.value = true
}

function openTradeEntry(plan: TradingPlan) {
  router.push({
    name: 'trade',
    query: {
      action: 'create',
      mode: 'from-plan',
      ts_code: plan.ts_code,
      stock_name: plan.stock_name,
      direction: plan.direction,
      plan_id: String(plan.id),
      price: String(plan.target_price),
      note: '从交易计划预填',
    },
  })
}

function closeEditor() {
  showEditor.value = false
  editingPlanId.value = null
  submitting.value = false
}

async function handleEditorSubmit(draft: EditablePlanDraft) {
  submitting.value = true
  try {
    const result =
      editorMode.value === 'manual-create'
        ? await store.savePlan(buildPlanCreateData(draft, { source: 'manual' }))
        : editingPlanId.value !== null
          ? await store.editPlan(editingPlanId.value, buildPlanUpdateData(draft))
          : null

    if (!result) {
      ElMessage.error(store.error ?? '计划保存失败')
      return
    }

    ElMessage.success(editorMode.value === 'manual-create' ? '计划已创建' : '计划已更新')
    closeEditor()
    await loadPlans()
  } finally {
    submitting.value = false
  }
}

async function viewDetail(plan: TradingPlan) {
  const detail = await store.fetchPlanDetail(plan.id)
  if (!detail) {
    ElMessage.error(store.error ?? '加载计划详情失败')
    return
  }
  showDetail.value = true
}

async function handleStatusChange(plan: TradingPlan, newStatus: PlanStatus) {
  const label = STATUS_LABELS[newStatus]
  await ElMessageBox.confirm(`确定将 ${plan.stock_name} 标记为“${label}”吗？`, '状态变更')
  const result = await store.changeStatus(plan.id, newStatus)
  if (!result) {
    ElMessage.error(store.error ?? '状态更新失败')
    return
  }
  ElMessage.success(`已标记为${label}`)
}

async function handleDelete(plan: TradingPlan) {
  await ElMessageBox.confirm(`确定删除 ${plan.stock_name} 的这条交易计划吗？`, '删除确认')
  const ok = await store.removePlan(plan.id)
  if (!ok) {
    ElMessage.error(store.error ?? '删除计划失败')
    return
  }

  if (store.currentPlan?.id === plan.id) {
    showDetail.value = false
  }
  ElMessage.success('计划已删除')
}

onMounted(async () => {
  await loadPlans()
})
</script>

<template>
  <div class="plan-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">交易计划</h2>
        <p class="page-desc">管理计划、跟踪状态，并支持一键从计划跳转录入成交记录。</p>
      </div>
      <el-button type="primary" @click="openManualCreate">手动创建</el-button>
    </div>

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      show-icon
      :closable="false"
      class="page-alert"
    />

    <el-tabs v-model="activeTab" class="filter-tabs" @tab-change="loadPlans">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="待执行" name="pending" />
      <el-tab-pane label="已执行" name="executed" />
      <el-tab-pane label="已放弃" name="abandoned" />
    </el-tabs>

    <div v-loading="store.loading">
      <el-empty v-if="store.plans.length === 0 && !store.loading" description="暂无交易计划" />

      <div v-else class="plan-grid">
        <el-card
          v-for="plan in store.plans"
          :key="plan.id"
          shadow="hover"
          class="plan-card"
          @click="viewDetail(plan)"
        >
          <div class="card-top">
            <div class="card-title">
              <span class="stock-name">{{ plan.stock_name }}</span>
              <span class="stock-code">{{ plan.ts_code }}</span>
            </div>
            <el-tag :type="statusType(plan.status)" size="small">
              {{ STATUS_LABELS[plan.status] }}
            </el-tag>
          </div>

          <div class="card-tags">
            <el-tag :type="plan.direction === 'buy' ? 'success' : 'danger'" size="small">
              {{ DIRECTION_LABELS[plan.direction] }}
            </el-tag>
            <el-tag :type="tierType(plan.tier_label)" size="small">
              {{ plan.tier_label ? TIER_LABELS[plan.tier_label] : '手动' }}
            </el-tag>
            <el-tag v-if="plan.source === 'llm_generated'" type="warning" size="small">AI</el-tag>
          </div>

          <div class="card-prices">
            <div class="price-item">
              <span class="price-label">目标价</span>
              <span class="price-value">{{ plan.target_price.toFixed(2) }}</span>
            </div>
            <div class="price-item">
              <span class="price-label">止损价</span>
              <span class="price-value danger">{{ plan.stop_loss_price.toFixed(2) }}</span>
            </div>
            <div class="price-item">
              <span class="price-label">仓位</span>
              <span class="price-value">{{ (plan.position_ratio * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <div class="card-footer" @click.stop>
            <span class="card-date">{{ formatLocalDateTime(plan.created_at) }}</span>
            <div class="card-actions">
              <el-button size="small" type="primary" text @click="openTradeEntry(plan)">录入交易</el-button>
              <el-button
                v-if="plan.status === 'pending'"
                size="small"
                type="primary"
                text
                @click="openPlanEditor(plan)"
              >
                编辑
              </el-button>
              <el-button
                v-if="plan.status === 'pending'"
                size="small"
                type="success"
                text
                @click="handleStatusChange(plan, 'executed')"
              >
                执行
              </el-button>
              <el-button
                v-if="plan.status === 'pending'"
                size="small"
                type="warning"
                text
                @click="handleStatusChange(plan, 'abandoned')"
              >
                放弃
              </el-button>
              <el-button size="small" type="danger" text @click="handleDelete(plan)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <el-drawer v-model="showDetail" title="计划详情" size="540px" @closed="store.currentPlan = null">
      <template v-if="store.currentPlan">
        <div class="detail-actions">
          <el-button type="primary" plain @click="openTradeEntry(store.currentPlan)">录入交易</el-button>
          <el-button
            v-if="isEditablePlan(store.currentPlan)"
            type="primary"
            plain
            @click="openPlanEditor(store.currentPlan)"
          >
            编辑计划
          </el-button>
        </div>

        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="股票">
            {{ store.currentPlan.stock_name }}（{{ store.currentPlan.ts_code }}）
          </el-descriptions-item>
          <el-descriptions-item label="方向">
            {{ DIRECTION_LABELS[store.currentPlan.direction] }}
          </el-descriptions-item>
          <el-descriptions-item label="目标价">
            {{ store.currentPlan.target_price.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="止损价">
            {{ store.currentPlan.stop_loss_price.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="仓位比例">
            {{ (store.currentPlan.position_ratio * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="方案类型">
            {{ formatPlanTierLabel(store.currentPlan.tier_label) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ STATUS_LABELS[store.currentPlan.status] }}
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ store.currentPlan.source === 'llm_generated' ? 'AI 生成' : '手动创建' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="store.currentPlan.expiry_date" label="有效期">
            {{ store.currentPlan.expiry_date }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatLocalDateTime(store.currentPlan.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatLocalDateTime(store.currentPlan.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 class="section-title">分批止盈</h4>
        <el-table :data="store.currentPlan.take_profit" size="small" border>
          <el-table-column label="档位" type="index" width="60" />
          <el-table-column label="止盈价" prop="price">
            <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="卖出比例" prop="ratio">
            <template #default="{ row }">{{ (row.ratio * 100).toFixed(0) }}%</template>
          </el-table-column>
          <el-table-column label="说明" prop="note" />
        </el-table>

        <h4 v-if="store.currentPlan.reasoning" class="section-title">计划理由</h4>
        <p v-if="store.currentPlan.reasoning" class="section-text">{{ store.currentPlan.reasoning }}</p>

        <h4 v-if="store.currentPlan.risk_comment" class="section-title">风险提示</h4>
        <el-alert
          v-if="store.currentPlan.risk_comment"
          :title="store.currentPlan.risk_comment"
          type="warning"
          :closable="false"
        />

        <template v-if="(store.currentPlan.alternatives ?? []).length > 0">
          <h4 class="section-title">备选方案</h4>
          <el-collapse>
            <el-collapse-item
              v-for="(alternative, index) in store.currentPlan.alternatives ?? []"
              :key="index"
              :title="`${formatPlanTierLabel(alternative.tier_label)} · 目标价 ${alternative.target_price}`"
            >
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="方向">
                  {{ DIRECTION_LABELS[alternative.direction] }}
                </el-descriptions-item>
                <el-descriptions-item label="目标价">{{ alternative.target_price }}</el-descriptions-item>
                <el-descriptions-item label="止损价">{{ alternative.stop_loss_price }}</el-descriptions-item>
                <el-descriptions-item label="仓位">
                  {{ (alternative.position_ratio * 100).toFixed(0) }}%
                </el-descriptions-item>
                <el-descriptions-item label="理由">{{ alternative.reasoning }}</el-descriptions-item>
                <el-descriptions-item label="风控">{{ alternative.risk_comment }}</el-descriptions-item>
              </el-descriptions>
            </el-collapse-item>
          </el-collapse>
        </template>
      </template>
    </el-drawer>

    <el-dialog v-model="showEditor" :title="editorTitle" width="720px" destroy-on-close>
      <PlanEditor
        :initial-draft="editorDraft"
        :mode="editorMode"
        :submit-text="editorSubmitText"
        :loading="submitting"
        :lock-identity="editorMode !== 'manual-create'"
        @submit="handleEditorSubmit"
        @cancel="closeEditor"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.plan-view {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 4px;
  color: #303133;
}

.page-desc {
  color: #909399;
  margin: 0;
  font-size: 13px;
}

.page-alert {
  margin-bottom: 16px;
}

.filter-tabs {
  margin-bottom: 16px;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.plan-card {
  cursor: pointer;
  transition: transform 0.15s;
}

.plan-card:hover {
  transform: translateY(-2px);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stock-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.stock-code {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.card-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.card-prices {
  display: flex;
  gap: 16px;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price-label {
  font-size: 11px;
  color: #909399;
}

.price-value {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  font-family: monospace;
}

.price-value.danger {
  color: #f56c6c;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.card-date {
  font-size: 11px;
  color: #c0c4cc;
}

.card-actions {
  display: flex;
  gap: 4px;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-text {
  font-size: 13px;
  color: #606266;
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
