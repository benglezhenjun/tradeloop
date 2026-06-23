<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getConfig, setConfig, triggerSync } from '@/api/index'
import { useAppStore } from '@/stores/app'
import { usePlanGenerateStore } from '@/stores/planGenerate'

const appStore = useAppStore()
const planGenerateStore = usePlanGenerateStore()

const syncing = ref(false)
const capitalInput = ref(0)
const savingCapital = ref(false)
const savingRates = ref(false)

const rateForm = reactive({
  commission_rate: 0.00025,
  stamp_tax_rate: 0.001,
  transfer_fee_rate: 0.00002,
})

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

async function loadTradeRates() {
  try {
    const [commissionRes, stampTaxRes, transferFeeRes] = await Promise.all([
      getConfig('commission_rate'),
      getConfig('stamp_tax_rate'),
      getConfig('transfer_fee_rate'),
    ])

    rateForm.commission_rate = Number(commissionRes.data.value) || rateForm.commission_rate
    rateForm.stamp_tax_rate = Number(stampTaxRes.data.value) || rateForm.stamp_tax_rate
    rateForm.transfer_fee_rate = Number(transferFeeRes.data.value) || rateForm.transfer_fee_rate
  } catch {
    ElMessage.warning('交易费率读取失败，已使用默认值')
  }
}

async function handleSaveCapital() {
  if (capitalInput.value <= 0) {
    ElMessage.warning('请输入有效的总资金金额')
    return
  }

  savingCapital.value = true
  try {
    const ok = await planGenerateStore.saveTotalCapital(capitalInput.value)
    if (ok) {
      ElMessage.success('总资金已保存')
    }
  } finally {
    savingCapital.value = false
  }
}

async function handleSaveRates() {
  if (Object.values(rateForm).some((value) => value < 0)) {
    ElMessage.warning('费率不能小于 0')
    return
  }

  savingRates.value = true
  try {
    await Promise.all([
      setConfig('commission_rate', String(rateForm.commission_rate)),
      setConfig('stamp_tax_rate', String(rateForm.stamp_tax_rate)),
      setConfig('transfer_fee_rate', String(rateForm.transfer_fee_rate)),
    ])
    ElMessage.success('交易费率已保存')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '保存交易费率失败')
  } finally {
    savingRates.value = false
  }
}

async function triggerDailySync() {
  syncing.value = true
  try {
    const res = await triggerSync()
    if (res.data.status === 'already_running') {
      ElMessage.warning(res.data.message)
    } else {
      ElMessage.info(res.data.message)
    }
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '触发同步失败')
  } finally {
    syncing.value = false
  }
}

onMounted(async () => {
  await Promise.all([appStore.fetchStats(), planGenerateStore.fetchTotalCapital(), loadTradeRates()])
  capitalInput.value = planGenerateStore.totalCapital
})
</script>

<template>
  <div class="settings-view">
    <div class="page-header">
      <h2 class="page-title">设置与数据管理</h2>
      <p class="page-desc">集中管理系统状态、总资金和交易费率配置。</p>
    </div>

    <el-card shadow="never" class="section-card">
      <template #header>系统状态</template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="后端状态">
          <el-tag :type="appStore.backendOnline ? 'success' : 'danger'">
            {{ appStore.backendOnline ? '在线' : '离线' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="最新交易日">
          {{ appStore.stats.latest_trade_date ? formatDate(appStore.stats.latest_trade_date) : '暂无数据' }}
        </el-descriptions-item>
        <el-descriptions-item label="股票数量">
          {{ appStore.stats.stock_count.toLocaleString() }} 只
        </el-descriptions-item>
        <el-descriptions-item label="行情记录">
          {{ (appStore.stats.quote_count / 10000).toFixed(1) }} 万条
        </el-descriptions-item>
        <el-descriptions-item label="财务数据">
          {{ appStore.stats.financial_count.toLocaleString() }} 条
        </el-descriptions-item>
        <el-descriptions-item label="启用策略">
          {{ appStore.stats.strategy_count }} 个
        </el-descriptions-item>
      </el-descriptions>

      <div class="action-row">
        <el-button @click="appStore.fetchStats()">刷新统计</el-button>
        <el-button type="primary" :loading="syncing" @click="triggerDailySync">
          {{ syncing ? '同步中...' : '手动触发每日同步' }}
        </el-button>
        <el-text type="warning" size="small">首次使用前，请先完成全量数据导入。</el-text>
      </div>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>资金配置</template>
      <el-form :inline="true">
        <el-form-item label="总资金（元）">
          <el-input-number
            v-model="capitalInput"
            :min="0"
            :step="10000"
            :precision="0"
            style="width: 220px"
            placeholder="输入总可用资金"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingCapital" @click="handleSaveCapital">保存</el-button>
        </el-form-item>
      </el-form>
      <el-text type="info" size="small">
        交易计划生成会参考这个总资金来计算仓位，单笔默认不超过 40%。
      </el-text>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>交易费率</template>
      <el-form label-width="140px" class="rate-form">
        <el-form-item label="佣金费率">
          <el-input-number
            v-model="rateForm.commission_rate"
            :min="0"
            :step="0.00001"
            :precision="6"
            style="width: 220px"
          />
          <span class="field-note">买入卖出都会参与自动计算</span>
        </el-form-item>
        <el-form-item label="印花税费率">
          <el-input-number
            v-model="rateForm.stamp_tax_rate"
            :min="0"
            :step="0.0001"
            :precision="6"
            style="width: 220px"
          />
          <span class="field-note">仅卖出时参与自动计算</span>
        </el-form-item>
        <el-form-item label="过户费费率">
          <el-input-number
            v-model="rateForm.transfer_fee_rate"
            :min="0"
            :step="0.00001"
            :precision="6"
            style="width: 220px"
          />
          <span class="field-note">仅沪市股票自动计算</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingRates" @click="handleSaveRates">保存费率</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        class="hint-alert"
        title="录入交易时默认按这里的费率自动计算，你也可以在表单里手动覆盖最终费用。"
      />
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>配置说明</template>
      <el-alert type="info" :closable="false" class="hint-alert">
        <template #title>
          token 等私密配置放在 <code>config/local.toml</code> 中，这个文件不会上传到 Git。
        </template>
      </el-alert>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="配置文件位置">
          <code>stock-assistant/config/local.toml</code>
        </el-descriptions-item>
        <el-descriptions-item label="自动同步时间">
          每个工作日 15:35 自动同步最新收盘数据。
        </el-descriptions-item>
        <el-descriptions-item label="数据库位置">
          <code>stock-assistant/data/stock.db</code>
        </el-descriptions-item>
        <el-descriptions-item label="API 文档">
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">http://localhost:8000/docs</a>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>首次全量导入</template>
      <el-alert
        type="warning"
        :closable="false"
        class="hint-alert"
        title="首次使用需要导入近三年历史数据，通常耗时 2 到 4 小时，只需要执行一次。"
      />
      <p class="command-label">在命令行中执行：</p>
      <el-input
        readonly
        :value="`cd stock-assistant/backend && uv run python -m app.services.data_sync`"
        class="command-input"
      />
    </el-card>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 920px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.section-card {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
  flex-wrap: wrap;
}

.rate-form {
  max-width: 560px;
}

.field-note {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.hint-alert {
  margin-top: 12px;
}

.command-label {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}

.command-input {
  font-family: monospace;
}

code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}
</style>
