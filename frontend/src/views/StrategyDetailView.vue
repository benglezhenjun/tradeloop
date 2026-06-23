<template>
  <div class="strategy-detail-view">
    <div class="page-header">
      <div>
        <el-button text @click="$router.push('/strategies')">← 返回策略列表</el-button>
        <h2 class="page-title">{{ detail?.name ?? '加载中...' }}</h2>
        <p class="page-desc">{{ detail?.description }}</p>
      </div>
    </div>

    <el-card v-if="detail" shadow="never">
      <template #header>
        <div class="conditions-header">
          <span>筛选条件</span>
          <el-button type="primary" size="small" @click="showAddDialog = true">+ 添加条件</el-button>
        </div>
      </template>

      <div v-if="detail.conditions.length === 0" class="empty-conditions">
        暂无条件，点击「添加条件」开始配置
      </div>

      <div v-for="(cond, idx) in detail.conditions" :key="cond.id ?? idx" class="condition-row">
        <div class="condition-info">
          <div class="condition-name">
            <el-tag size="small" type="info">{{ cond.category }}</el-tag>
            {{ cond.condition_name }}
          </div>
          <div class="condition-params">
            <span v-for="(val, key) in cond.params" :key="key" class="param-item">
              {{ cond.param_schema[key]?.label ?? key }}: <strong>{{ formatParamValue(key, val, cond) }}</strong>
            </span>
          </div>
        </div>
        <div class="condition-actions">
          <el-switch
            v-model="cond.is_enabled"
            size="small"
            @change="saveConditions"
          />
          <el-button
            size="small"
            text
            @click="editCondition(idx)"
          >编辑</el-button>
          <el-button
            size="small"
            text
            type="danger"
            @click="removeCondition(idx)"
          >删除</el-button>
        </div>
      </div>

      <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee;">
        <el-button type="primary" :loading="saving" @click="saveConditions">保存条件</el-button>
        <el-text type="info" size="small" style="margin-left: 12px;">
          条件按顺序依次过滤（AND 关系），越严格的条件建议放后面
        </el-text>
      </div>
    </el-card>

    <!-- 添加/编辑条件对话框 -->
    <el-dialog v-model="showAddDialog" :title="editingIdx !== null ? '编辑条件参数' : '添加筛选条件'" width="600px">
      <!-- 新增时才显示条件选择器；编辑时只显示当前条件名 -->
      <div v-if="editingIdx === null" class="condition-picker">
        <div
          v-for="cond in strategyStore.allConditions"
          :key="cond.code"
          class="condition-option"
          :class="{ selected: pendingCondition?.code === cond.code }"
          @click="selectCondition(cond)"
        >
          <div class="option-header">
            <el-tag size="small" type="info">{{ cond.category }}</el-tag>
            <span class="option-name">{{ cond.name }}</span>
          </div>
          <div class="option-desc">{{ cond.description }}</div>
        </div>
      </div>
      <div v-else class="editing-label">
        <el-tag size="small" type="info">{{ pendingCondition?.category }}</el-tag>
        <span style="margin-left: 8px; font-weight: 500;">{{ pendingCondition?.name }}</span>
      </div>

      <!-- 参数编辑区 -->
      <el-divider v-if="pendingCondition" />
      <div v-if="pendingCondition">
        <p style="font-weight: 600; margin-bottom: 12px;">配置参数：{{ pendingCondition.name }}</p>
        <el-form label-width="160px" size="small">
          <el-form-item
            v-for="(schema, key) in pendingCondition.params"
            :key="key"
            :label="schema.label"
          >
            <el-input-number
              v-if="schema.type === 'number' || schema.type === 'int'"
              v-model="pendingParams[key]"
              :precision="schema.type === 'int' ? 0 : 6"
              style="width: 200px"
            />
            <el-select
              v-else-if="schema.type === 'select'"
              v-model="pendingParams[key]"
              style="width: 200px"
            >
              <el-option label="宽松模式（MA5/10/30在MA60上方）" value="loose" />
              <el-option label="严格模式（完整多头排列）" value="strict" />
            </el-select>
            <div class="param-hint">{{ schema.description }}</div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :disabled="!pendingCondition" @click="confirmCondition">
          {{ editingIdx !== null ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getStrategy, updateStrategyConditions } from '@/api/index'
import { useStrategyStore } from '@/stores/strategy'
import type { StrategyDetail, StrategyCondition, ConditionDef } from '@/types/strategy'

const route = useRoute()
const strategyStore = useStrategyStore()

const strategyId = Number(route.params.id)
const detail = ref<StrategyDetail | null>(null)
const saving = ref(false)
const showAddDialog = ref(false)
const editingIdx = ref<number | null>(null)
const pendingCondition = ref<ConditionDef | null>(null)
const pendingParams = ref<Record<string, number | string | boolean>>({})

onMounted(async () => {
  await strategyStore.fetchAllConditions()
  const res = await getStrategy(strategyId)
  detail.value = res.data
})

function selectCondition(cond: ConditionDef) {
  pendingCondition.value = cond
  // 设置默认参数值
  const defaults: Record<string, number | string> = {}
  for (const [key, schema] of Object.entries(cond.params)) {
    defaults[key] = schema.default as number | string
  }
  pendingParams.value = defaults
}

function editCondition(idx: number) {
  if (!detail.value) return
  const cond = detail.value.conditions[idx]
  if (!cond) return
  // 从 allConditions 里找到完整的 ConditionDef（含 param_schema）
  const def = strategyStore.allConditions.find(c => c.code === cond.condition_code)
  if (!def) return
  editingIdx.value = idx
  pendingCondition.value = def
  pendingParams.value = { ...cond.params }
  showAddDialog.value = true
}

function closeDialog() {
  showAddDialog.value = false
  editingIdx.value = null
  pendingCondition.value = null
}

function confirmCondition() {
  if (!pendingCondition.value || !detail.value) return

  if (editingIdx.value !== null) {
    // 编辑模式：只更新 params
    const target = detail.value.conditions[editingIdx.value]
    if (target) {
      target.params = { ...pendingParams.value }
    }
  } else {
    // 新增模式
    const newCond: StrategyCondition = {
      condition_code: pendingCondition.value.code,
      condition_name: pendingCondition.value.name,
      category: pendingCondition.value.category,
      params: { ...pendingParams.value },
      param_schema: pendingCondition.value.params,
      is_enabled: true,
      sort_order: detail.value.conditions.length + 1,
    }
    detail.value.conditions.push(newCond)
  }

  closeDialog()
}

function removeCondition(idx: number) {
  detail.value?.conditions.splice(idx, 1)
}

async function saveConditions() {
  if (!detail.value) return
  saving.value = true
  try {
    await updateStrategyConditions(
      strategyId,
      detail.value.conditions.map((c, i) => ({
        condition_code: c.condition_code,
        params: c.params,
        is_enabled: c.is_enabled,
        sort_order: i + 1,
      })),
    )
    ElMessage.success('条件已保存')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function formatParamValue(key: string, val: number | string | boolean, cond: StrategyCondition) {
  // 将大数字转为可读格式
  if (typeof val === 'number') {
    if (Math.abs(val) >= 1e9) return (val / 1e9).toFixed(0) + '亿'
    if (Math.abs(val) >= 1e4) return (val / 1e4).toFixed(0) + '万'
    if (key.includes('deviation') || key.includes('slope') || key.includes('rise')) {
      return (val * 100).toFixed(1) + '%'
    }
  }
  return String(val)
}
</script>

<style scoped>
.strategy-detail-view { max-width: 800px; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 20px; font-weight: 600; margin: 8px 0 4px; color: #303133; }
.page-desc { color: #909399; margin: 0; font-size: 13px; }

.conditions-header { display: flex; align-items: center; justify-content: space-between; }
.empty-conditions { text-align: center; padding: 30px; color: #c0c4cc; font-size: 14px; }

.condition-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f2f2f2;
}
.condition-row:last-of-type { border-bottom: none; }
.condition-name { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; margin-bottom: 4px; }
.condition-params { display: flex; flex-wrap: wrap; gap: 12px; }
.param-item { font-size: 12px; color: #909399; }
.condition-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* 条件选择器 */
.condition-picker { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.condition-option {
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.condition-option:hover { border-color: #409eff; background: #ecf5ff; }
.condition-option.selected { border-color: #409eff; background: #ecf5ff; }
.option-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.option-name { font-weight: 500; font-size: 13px; }
.option-desc { font-size: 12px; color: #909399; }
.param-hint { font-size: 11px; color: #c0c4cc; margin-top: 2px; }
.editing-label { padding: 10px 12px; background: #f5f7fa; border-radius: 6px; display: flex; align-items: center; }
</style>
