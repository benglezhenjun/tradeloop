<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

import PlanEditor from '@/components/plan/PlanEditor.vue'
import { usePlanGenerateStore } from '@/stores/planGenerate'
import { usePlanStore } from '@/stores/plan'
import { DIRECTION_LABELS, TIER_LABELS, type EditablePlanDraft, type PlanProposal } from '@/types/plan'
import { buildPlanCreateData, createEmptyPlanDraft, draftFromProposal } from '@/utils/plan'

type PageState = 'loading' | 'compare' | 'editor' | 'manual-fallback'

const route = useRoute()
const router = useRouter()
const planStore = usePlanStore()
const generateStore = usePlanGenerateStore()

const pageState = ref<PageState>('loading')
const selectedIndex = ref<number | null>(null)
const editorDraft = ref<EditablePlanDraft>(createEmptyPlanDraft())
const saving = ref(false)

const tsCode = computed(() => (typeof route.params.tsCode === 'string' ? route.params.tsCode : ''))
const generatedPlans = computed(() => generateStore.proposals)
const manualFallback = computed(() => generateStore.manualFallback)

const editorMode = computed(() => (pageState.value === 'manual-fallback' ? 'manual-create' : 'generate-edit'))
const editorSubmitText = computed(() => (pageState.value === 'manual-fallback' ? '保存为手动计划' : '保存所选方案'))

function proposalAt(index: number): PlanProposal | null {
  return generatedPlans.value[index] ?? null
}

function tierColor(tierLabel: PlanProposal['tier_label']): string {
  if (tierLabel === 'aggressive') {
    return '#f56c6c'
  }
  if (tierLabel === 'balanced') {
    return '#e6a23c'
  }
  return '#67c23a'
}

async function loadPage() {
  pageState.value = 'loading'
  selectedIndex.value = null
  editorDraft.value = createEmptyPlanDraft()
  planStore.clearError()
  generateStore.clearError()
  generateStore.clearGenerateResult()

  if (!tsCode.value) {
    ElMessage.warning('缺少股票代码')
    await router.push({ name: 'plan' })
    return
  }

  await generateStore.fetchTotalCapital()
  if (generateStore.totalCapital <= 0) {
    ElMessage.warning('请先在设置页设置总资金')
    await router.push({ name: 'settings' })
    return
  }

  const result = await generateStore.generate(tsCode.value)
  if (!result) {
    pageState.value = 'compare'
    return
  }

  if (result.status === 'manual_fallback') {
    editorDraft.value = createEmptyPlanDraft(result.prefill)
    pageState.value = 'manual-fallback'
    return
  }

  pageState.value = 'compare'
}

function handleSelect(index: number) {
  const proposal = proposalAt(index)
  if (!proposal) {
    ElMessage.error('未找到对应的方案')
    return
  }

  selectedIndex.value = index
  editorDraft.value = draftFromProposal(proposal)
  pageState.value = 'editor'
}

function handleEditorCancel() {
  if (pageState.value === 'manual-fallback') {
    router.push({ name: 'plan' })
    return
  }

  selectedIndex.value = null
  pageState.value = 'compare'
}

async function handleSave(draft: EditablePlanDraft) {
  saving.value = true
  try {
    const payload =
      pageState.value === 'manual-fallback'
        ? buildPlanCreateData(draft, { source: 'manual' })
        : (() => {
            const currentIndex = selectedIndex.value
            if (currentIndex === null) {
              return null
            }

            const alternatives = generatedPlans.value.filter((_, index) => index !== currentIndex)
            return buildPlanCreateData(draft, {
              source: 'llm_generated',
              alternatives,
            })
          })()

    if (!payload) {
      ElMessage.error('未找到当前选中的方案')
      return
    }

    const result = await planStore.savePlan(payload)
    if (!result) {
      ElMessage.error(planStore.error ?? '保存计划失败')
      return
    }

    ElMessage.success('交易计划已保存')
    await router.push({ name: 'plan' })
  } finally {
    saving.value = false
  }
}

watch(tsCode, async () => {
  await loadPage()
})

onMounted(async () => {
  await loadPage()
})

onBeforeUnmount(() => {
  generateStore.clearGenerateResult()
  generateStore.clearError()
  planStore.clearError()
})
</script>

<template>
  <div class="plan-generate-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">生成交易方案</h2>
        <p class="page-desc">AI 先给出三套候选方案，你再选择、编辑并保存为正式计划。</p>
      </div>
      <el-button @click="router.back()">返回</el-button>
    </div>

    <el-alert
      v-if="(generateStore.error || planStore.error) && !generateStore.generating"
      :title="generateStore.error ?? planStore.error ?? ''"
      type="error"
      show-icon
      :closable="false"
      class="page-alert"
    />

    <el-alert
      v-if="manualFallback"
      :title="manualFallback.message"
      type="warning"
      show-icon
      :closable="false"
      class="page-alert"
    />

    <div v-if="generateStore.generating || pageState === 'loading'" class="loading-container">
      <el-icon class="is-loading" :size="40" style="color: #409eff">
        <Loading />
      </el-icon>
      <p class="loading-text">AI 正在分析，预计 30-90 秒。</p>
    </div>

    <template v-else>
      <div v-if="pageState === 'compare' && generatedPlans.length === 3" class="proposals-grid">
        <el-card
          v-for="(proposal, index) in generatedPlans"
          :key="index"
          shadow="hover"
          class="proposal-card"
          :style="{ borderTop: `3px solid ${tierColor(proposal.tier_label)}` }"
        >
          <div class="proposal-header">
            <el-tag :color="tierColor(proposal.tier_label)" effect="dark" size="large">
              {{ TIER_LABELS[proposal.tier_label] }}
            </el-tag>
            <span class="proposal-stock">{{ proposal.stock_name }}</span>
          </div>

          <el-descriptions :column="1" size="small" border class="proposal-info">
            <el-descriptions-item label="方向">
              <el-tag :type="proposal.direction === 'buy' ? 'success' : 'danger'" size="small">
                {{ DIRECTION_LABELS[proposal.direction] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="目标价">{{ proposal.target_price }}</el-descriptions-item>
            <el-descriptions-item label="止损价">{{ proposal.stop_loss_price }}</el-descriptions-item>
            <el-descriptions-item label="仓位">
              {{ (proposal.position_ratio * 100).toFixed(0) }}%
            </el-descriptions-item>
          </el-descriptions>

          <h4 class="section-title">分批止盈</h4>
          <div v-for="(tier, tierIndex) in proposal.take_profit" :key="tierIndex" class="tp-item">
            <span>第 {{ tierIndex + 1 }} 档：{{ tier.price }} 元，卖出 {{ (tier.ratio * 100).toFixed(0) }}%</span>
            <span v-if="tier.note" class="tp-note">{{ tier.note }}</span>
          </div>

          <h4 class="section-title">入场理由</h4>
          <p class="reasoning-text">{{ proposal.reasoning }}</p>

          <div v-if="proposal.risk_comment" class="risk-box">
            <strong>风控：</strong>{{ proposal.risk_comment }}
          </div>

          <el-button type="primary" class="select-btn" @click="handleSelect(index)">
            选择此方案
          </el-button>
        </el-card>
      </div>

      <el-empty
        v-else-if="pageState === 'compare'"
        description="未拿到可比较的三套方案，请返回重试。"
      />

      <el-card v-else shadow="never" class="edit-card">
        <template #header>
          <div class="editor-header">
            <div>
              <span class="editor-title">
                {{ pageState === 'manual-fallback' ? '手动补建计划' : '编辑所选方案' }}
              </span>
              <p class="editor-desc">
                {{
                  pageState === 'manual-fallback'
                    ? '本次 AI 输出不可直接使用，已切换为手动创建模式，股票信息已预填。'
                    : '选中方案后，可以继续微调价格、仓位、止盈分配和风控评语。'
                }}
              </p>
            </div>
            <el-button size="small" @click="handleEditorCancel">
              {{ pageState === 'manual-fallback' ? '返回计划列表' : '返回方案对比' }}
            </el-button>
          </div>
        </template>

        <PlanEditor
          :initial-draft="editorDraft"
          :mode="editorMode"
          :submit-text="editorSubmitText"
          :loading="saving"
          :lock-identity="true"
          @submit="handleSave"
          @cancel="handleEditorCancel"
        />
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.plan-generate-view {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
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

.loading-container {
  text-align: center;
  padding: 60px 0;
}

.loading-text {
  color: #909399;
  margin-top: 12px;
}

.proposals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.proposal-card {
  position: relative;
}

.proposal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.proposal-stock {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.proposal-info {
  margin-bottom: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin: 12px 0 6px;
  color: #606266;
}

.tp-item {
  font-size: 13px;
  color: #303133;
  margin-bottom: 4px;
}

.tp-note {
  color: #909399;
  margin-left: 8px;
  font-size: 12px;
}

.reasoning-text {
  font-size: 13px;
  color: #606266;
  margin: 0;
  line-height: 1.6;
}

.risk-box {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  font-size: 13px;
  color: #e6a23c;
}

.select-btn {
  width: 100%;
  margin-top: 16px;
}

.edit-card {
  max-width: 760px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.editor-title {
  font-weight: 600;
  color: #303133;
}

.editor-desc {
  color: #909399;
  margin: 6px 0 0;
  font-size: 13px;
}

@media (max-width: 1000px) {
  .proposals-grid {
    grid-template-columns: 1fr;
  }

  .editor-header {
    flex-direction: column;
  }
}
</style>
