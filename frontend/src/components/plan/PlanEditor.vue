<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { searchStocks } from '@/api/index'
import type { EditablePlanDraft, PlanEditorMode, PlanTierLabel } from '@/types/plan'
import type { StockSearchResult } from '@/types/watchlist'
import { clonePlanDraft, createDefaultTakeProfitTier, getTakeProfitRatioTotal } from '@/utils/plan'

interface Props {
  initialDraft: EditablePlanDraft
  mode: PlanEditorMode
  submitText?: string
  cancelText?: string
  loading?: boolean
  lockIdentity?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  submitText: '保存计划',
  cancelText: '取消',
  loading: false,
  lockIdentity: false,
})

const emit = defineEmits<{
  submit: [draft: EditablePlanDraft]
  cancel: []
}>()

const form = ref<EditablePlanDraft>(clonePlanDraft(props.initialDraft))
const stockOptions = ref<StockSearchResult[]>([])
const searchLoading = ref(false)

watch(
  () => props.initialDraft,
  (value) => {
    form.value = clonePlanDraft(value)
    stockOptions.value = []
  },
  { immediate: true, deep: true },
)

const tierOptions: Array<{ value: PlanTierLabel; label: string }> = [
  { value: 'aggressive', label: '激进' },
  { value: 'balanced', label: '稳健' },
  { value: 'conservative', label: '保守' },
]

const takeProfitRatioTotal = computed(() => getTakeProfitRatioTotal(form.value.take_profit))
const takeProfitRatioOk = computed(() => Math.abs(takeProfitRatioTotal.value - 1) <= 0.01)
const sliderMarks = {
  0.1: '10%',
  0.2: '20%',
  0.3: '30%',
  0.4: '40%',
}

async function handleStockSearch(query: string) {
  if (props.lockIdentity) {
    return
  }

  const keyword = query.trim()
  if (!keyword) {
    stockOptions.value = []
    return
  }

  searchLoading.value = true
  try {
    stockOptions.value = await searchStocks(keyword, 10)
  } finally {
    searchLoading.value = false
  }
}

function handleStockSelect(tsCode: string) {
  const matched = stockOptions.value.find((stock) => stock.ts_code === tsCode)
  if (!matched) {
    return
  }

  form.value = {
    ...form.value,
    ts_code: matched.ts_code,
    stock_name: matched.name,
  }
}

function addTier() {
  form.value = {
    ...form.value,
    take_profit: [...form.value.take_profit, createDefaultTakeProfitTier()],
  }
}

function removeTier(index: number) {
  if (form.value.take_profit.length <= 1) {
    return
  }

  form.value = {
    ...form.value,
    take_profit: form.value.take_profit.filter((_, tierIndex) => tierIndex !== index),
  }
}

function updateTier(
  index: number,
  patch: Partial<{ price: number; ratio: number; note: string }>,
) {
  form.value = {
    ...form.value,
    take_profit: form.value.take_profit.map((tier, tierIndex) =>
      tierIndex === index
        ? {
            ...tier,
            ...patch,
          }
        : tier,
    ),
  }
}

function validateDraft(): string | null {
  if (!form.value.ts_code || !form.value.stock_name) {
    return '请先选择股票'
  }

  if (form.value.target_price <= 0 || form.value.stop_loss_price <= 0) {
    return '目标价和止损价必须大于 0'
  }

  if (form.value.position_ratio <= 0 || form.value.position_ratio > 0.4) {
    return '仓位比例必须在 0 到 40% 之间'
  }

  if (!form.value.take_profit.length) {
    return '请至少填写一个止盈档位'
  }

  const invalidTier = form.value.take_profit.some((tier) => tier.price <= 0 || tier.ratio <= 0)
  if (invalidTier) {
    return '止盈档位中的价格和比例都必须大于 0'
  }

  if (!takeProfitRatioOk.value) {
    return '所有止盈档位的比例之和必须等于 1.0'
  }

  return null
}

function handleSubmit() {
  const error = validateDraft()
  if (error) {
    ElMessage.warning(error)
    return
  }

  emit('submit', clonePlanDraft(form.value))
}
</script>

<template>
  <div class="plan-editor">
    <el-form label-width="92px" size="default">
      <el-form-item label="股票">
        <template v-if="!lockIdentity">
          <el-select
            v-model="form.ts_code"
            filterable
            remote
            reserve-keyword
            :remote-method="handleStockSearch"
            :loading="searchLoading"
            placeholder="输入股票代码或名称"
            style="width: 100%"
            @change="handleStockSelect"
          >
            <el-option
              v-for="stock in stockOptions"
              :key="stock.ts_code"
              :label="`${stock.name}（${stock.ts_code}）`"
              :value="stock.ts_code"
            />
          </el-select>
        </template>
        <template v-else>
          <div class="identity-lock">
            <el-input :model-value="form.stock_name" disabled />
            <el-input :model-value="form.ts_code" disabled />
          </div>
        </template>
      </el-form-item>

      <el-form-item label="方向">
        <el-radio-group v-model="form.direction">
          <el-radio value="buy">买入</el-radio>
          <el-radio value="sell">卖出</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="方案类型">
        <el-select v-model="form.tier_label" clearable placeholder="可选">
          <el-option
            v-for="option in tierOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="目标价">
        <el-input-number v-model="form.target_price" :min="0.01" :step="0.1" :precision="2" />
      </el-form-item>

      <el-form-item label="止损价">
        <el-input-number v-model="form.stop_loss_price" :min="0.01" :step="0.1" :precision="2" />
      </el-form-item>

      <el-form-item label="仓位比例">
        <div class="slider-field">
          <el-slider
            v-model="form.position_ratio"
            :min="0.01"
            :max="0.4"
            :step="0.01"
            :marks="sliderMarks"
            :format-tooltip="(value: number) => `${(value * 100).toFixed(0)}%`"
          />
          <span class="slider-value">{{ (form.position_ratio * 100).toFixed(0) }}%</span>
        </div>
      </el-form-item>

      <el-form-item label="止盈档位">
        <div class="tier-list">
          <div v-for="(tier, index) in form.take_profit" :key="index" class="tier-row">
            <el-input-number
              :model-value="tier.price"
              :min="0.01"
              :step="0.1"
              :precision="2"
              size="small"
              placeholder="价格"
              @update:model-value="(value: number | undefined) => updateTier(index, { price: value ?? 0 })"
            />
            <el-input-number
              :model-value="tier.ratio"
              :min="0.01"
              :max="1"
              :step="0.01"
              :precision="2"
              size="small"
              placeholder="比例"
              @update:model-value="(value: number | undefined) => updateTier(index, { ratio: value ?? 0 })"
            />
            <el-input
              :model-value="tier.note ?? ''"
              placeholder="说明"
              size="small"
              style="width: 160px"
              @update:model-value="(value: string) => updateTier(index, { note: value })"
            />
            <el-button
              size="small"
              text
              type="danger"
              :disabled="form.take_profit.length <= 1"
              @click="removeTier(index)"
            >
              删除
            </el-button>
          </div>
          <div class="tier-actions">
            <el-button size="small" @click="addTier">添加档位</el-button>
            <el-tag :type="takeProfitRatioOk ? 'success' : 'danger'" size="small">
              比例合计 {{ takeProfitRatioTotal.toFixed(2) }}
            </el-tag>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="计划理由">
        <el-input v-model="form.reasoning" type="textarea" :rows="3" />
      </el-form-item>

      <el-form-item label="风控评语">
        <el-input v-model="form.risk_comment" type="textarea" :rows="2" />
      </el-form-item>

      <el-form-item label="有效期">
        <el-date-picker
          v-model="form.expiry_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="可选"
        />
      </el-form-item>
    </el-form>

    <el-alert
      v-if="!takeProfitRatioOk"
      title="止盈档位比例之和必须等于 1.0，保存前请先调整。"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="editor-actions">
      <el-button @click="emit('cancel')">{{ cancelText }}</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">{{ submitText }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.plan-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.identity-lock {
  display: grid;
  grid-template-columns: 1fr 160px;
  gap: 8px;
  width: 100%;
}

.slider-field {
  display: flex;
  align-items: center;
  gap: 12px;
  width: min(100%, 520px);
}

.slider-field :deep(.el-slider) {
  flex: 1;
}

.slider-value {
  width: 48px;
  color: #606266;
  font-size: 13px;
  text-align: right;
}

.tier-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.tier-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tier-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 768px) {
  .identity-lock {
    grid-template-columns: 1fr;
  }
}
</style>
