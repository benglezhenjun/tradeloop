<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { getConfig } from '@/api/index'
import type { TradeCreateData, TradeDirection } from '@/types/trade'

interface TradeFormState {
  ts_code: string
  stock_name: string
  direction: TradeDirection
  price: number
  quantity: number
  trade_date: string
  trade_time: string | null
  note: string
  plan_id: number | null
}

const props = withDefaults(
  defineProps<{
    initialData?: Partial<TradeCreateData>
    loading?: boolean
    submitText?: string
    lockIdentity?: boolean
    maxQuantity?: number | null
  }>(),
  {
    initialData: () => ({}),
    loading: false,
    submitText: '保存交易',
    lockIdentity: false,
    maxQuantity: null,
  },
)

const emit = defineEmits<{
  submit: [payload: TradeCreateData]
  cancel: []
}>()

const feeRates = ref({
  commission_rate: 0.00025,
  stamp_tax_rate: 0.001,
  transfer_fee_rate: 0.00002,
})

const manualFeeMode = ref(false)
const manualFee = ref(0)
const loadingRates = ref(false)

const form = reactive<TradeFormState>(createDefaultState())

function todayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function createDefaultState(): TradeFormState {
  return {
    ts_code: '',
    stock_name: '',
    direction: 'buy',
    price: 0,
    quantity: 100,
    trade_date: todayString(),
    trade_time: null,
    note: '',
    plan_id: null,
  }
}

function applyInitialData() {
  const next = createDefaultState()
  Object.assign(next, props.initialData ?? {})

  form.ts_code = next.ts_code ?? ''
  form.stock_name = next.stock_name ?? ''
  form.direction = next.direction ?? 'buy'
  form.price = next.price ?? 0
  form.quantity = next.quantity ?? 100
  form.trade_date = next.trade_date ?? todayString()
  form.trade_time = next.trade_time ?? null
  form.note = next.note ?? ''
  form.plan_id = next.plan_id ?? null

  manualFeeMode.value = props.initialData?.fee != null
  manualFee.value = props.initialData?.fee ?? 0
}

const amount = computed(() => Number((form.price * form.quantity).toFixed(2)))

const calculatedFee = computed(() => {
  const commission = amount.value * feeRates.value.commission_rate
  const stampTax = form.direction === 'sell' ? amount.value * feeRates.value.stamp_tax_rate : 0
  const transferFee = form.ts_code.toUpperCase().endsWith('.SH')
    ? amount.value * feeRates.value.transfer_fee_rate
    : 0
  return Number((commission + stampTax + transferFee).toFixed(4))
})

const finalFee = computed(() => (manualFeeMode.value ? manualFee.value : calculatedFee.value))

const maxQuantityHint = computed(() => {
  if (form.direction !== 'sell' || props.maxQuantity == null) {
    return null
  }
  return `当前最多可卖 ${props.maxQuantity} 股`
})

async function loadRates() {
  loadingRates.value = true
  try {
    const [commissionRes, stampTaxRes, transferFeeRes] = await Promise.all([
      getConfig('commission_rate'),
      getConfig('stamp_tax_rate'),
      getConfig('transfer_fee_rate'),
    ])
    feeRates.value = {
      commission_rate: Number(commissionRes.data.value) || feeRates.value.commission_rate,
      stamp_tax_rate: Number(stampTaxRes.data.value) || feeRates.value.stamp_tax_rate,
      transfer_fee_rate: Number(transferFeeRes.data.value) || feeRates.value.transfer_fee_rate,
    }
  } catch {
    ElMessage.warning('交易费率读取失败，已使用默认费率')
  } finally {
    loadingRates.value = false
  }
}

function handleSubmit() {
  if (!form.ts_code.trim() || !form.stock_name.trim()) {
    ElMessage.warning('请先填写股票代码和股票名称')
    return
  }
  if (form.price <= 0 || form.quantity <= 0) {
    ElMessage.warning('价格和数量必须大于 0')
    return
  }
  if (form.direction === 'sell' && props.maxQuantity != null && form.quantity > props.maxQuantity) {
    ElMessage.warning(`卖出数量不能超过当前持仓 ${props.maxQuantity} 股`)
    return
  }

  emit('submit', {
    ts_code: form.ts_code.trim(),
    stock_name: form.stock_name.trim(),
    direction: form.direction,
    price: form.price,
    quantity: form.quantity,
    trade_date: form.trade_date,
    trade_time: form.trade_time,
    fee: finalFee.value,
    note: form.note.trim() || null,
    plan_id: form.plan_id,
  })
}

watch(
  () => props.initialData,
  () => {
    applyInitialData()
  },
  { deep: true, immediate: true },
)

onMounted(async () => {
  await loadRates()
})
</script>

<template>
  <div class="trade-form" v-loading="loadingRates">
    <el-form label-width="96px" @submit.prevent>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="股票代码">
            <el-input v-model="form.ts_code" :disabled="lockIdentity" placeholder="如 600000.SH" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="股票名称">
            <el-input v-model="form.stock_name" :disabled="lockIdentity" placeholder="如 浦发银行" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="交易方向">
            <el-segmented
              v-model="form.direction"
              :options="[
                { label: '买入', value: 'buy' },
                { label: '卖出', value: 'sell' },
              ]"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计划 ID">
            <el-input-number v-model="form.plan_id" :min="1" :step="1" controls-position="right" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="成交价格">
            <el-input-number v-model="form.price" :min="0" :step="0.01" :precision="2" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="成交数量">
            <el-input-number
              v-model="form.quantity"
              :min="1"
              :max="maxQuantity ?? undefined"
              :step="100"
              :precision="0"
              style="width: 100%"
            />
            <div v-if="maxQuantityHint" class="field-hint">{{ maxQuantityHint }}</div>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="交易日期">
            <el-date-picker
              v-model="form.trade_date"
              type="date"
              value-format="YYYY-MM-DD"
              format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="交易时间">
            <el-time-picker
              v-model="form.trade_time"
              value-format="HH:mm:ss"
              format="HH:mm:ss"
              placeholder="可选"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="成交金额">
            <el-input :model-value="amount.toFixed(2)" readonly />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="交易费用">
            <div class="fee-box">
              <el-switch v-model="manualFeeMode" inline-prompt active-text="手填" inactive-text="自动" />
              <el-input-number
                v-model="manualFee"
                :disabled="!manualFeeMode"
                :min="0"
                :step="0.01"
                :precision="4"
                style="width: 160px"
              />
              <span v-if="!manualFeeMode" class="fee-note">自动计算：{{ calculatedFee.toFixed(4) }}</span>
            </div>
          </el-form-item>
        </el-col>
      </el-row>

      <el-alert type="info" :closable="false" class="fee-alert">
        当前费率：佣金 {{ feeRates.commission_rate }} / 印花税 {{ feeRates.stamp_tax_rate }} / 过户费
        {{ feeRates.transfer_fee_rate }}（仅沪市）
      </el-alert>

      <el-form-item label="备注">
        <el-input
          v-model="form.note"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          placeholder="可记录成交来源、策略说明或补充备注"
        />
      </el-form-item>
    </el-form>

    <div class="form-footer">
      <el-button @click="emit('cancel')">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">{{ submitText }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.trade-form {
  padding-top: 8px;
}

.field-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.fee-box {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.fee-note {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.fee-alert {
  margin-bottom: 16px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}
</style>
