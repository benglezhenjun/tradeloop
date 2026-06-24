<template>
  <div class="strategies-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">策略管理</h2>
        <p class="page-desc">查看和管理筛选策略，每个策略由多个条件组合而成</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        + 新建策略
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="s in strategyStore.strategies" :key="s.id" :span="12">
        <el-card shadow="hover" class="strategy-card">
          <template #header>
            <div class="card-header">
              <div class="strategy-name">
                {{ s.name }}
                <el-tag v-if="!s.is_enabled" size="small" type="info">已停用</el-tag>
              </div>
              <div class="card-actions">
                <el-button size="small" @click="$router.push(`/strategies/${s.id}`)">
                  编辑条件
                </el-button>
                <el-button size="small" type="danger" plain @click="confirmDelete(s)">
                  删除
                </el-button>
              </div>
            </div>
          </template>

          <p class="strategy-desc">{{ s.description || '暂无说明' }}</p>
          <div class="strategy-meta">
            <el-tag size="small" type="info">{{ s.condition_count }} 个条件</el-tag>
            <span class="create-time">创建于 {{ formatDate(s.created_at) }}</span>
          </div>
          <div style="margin-top: 12px;">
            <el-button
              type="primary"
              size="small"
              @click="goScreening(s.id)"
            >
              立即筛选
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建策略对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建策略" width="500px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="策略名称">
          <el-input v-model="createForm.name" placeholder="如：成长股动量策略" />
        </el-form-item>
        <el-form-item label="策略说明">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述这个策略的逻辑和适用场景"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useStrategyStore } from '@/stores/strategy'
import { createStrategy, deleteStrategy } from '@/api/index'
import type { Strategy } from '@/types/strategy'

const router = useRouter()
const strategyStore = useStrategyStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

onMounted(() => strategyStore.fetchStrategies())

function formatDate(d: string) {
  return d ? d.substring(0, 10) : '-'
}

function goScreening(id: number) {
  router.push({ path: '/screening', query: { strategyId: id } })
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入策略名称')
    return
  }
  creating.value = true
  try {
    await createStrategy({ name: createForm.value.name, description: createForm.value.description })
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    await strategyStore.fetchStrategies()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    creating.value = false
  }
}

async function confirmDelete(s: Strategy) {
  try {
    await ElMessageBox.confirm(`确定删除策略「${s.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      confirmButtonClass: 'el-button--danger',
    })
    await deleteStrategy(s.id)
    ElMessage.success('已删除')
    await strategyStore.fetchStrategies()
  } catch {
    // 用户取消，忽略
  }
}
</script>

<style scoped>
.strategies-view { max-width: 1000px; }
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title { font-size: 20px; font-weight: 600; margin: 0 0 6px; color: var(--tl-text); }
.page-desc { color: var(--tl-text-tertiary); margin: 0; font-size: 13px; }

.strategy-card { margin-bottom: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.strategy-name { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
.card-actions { display: flex; gap: 8px; }
.strategy-desc { color: var(--tl-text-secondary); font-size: 13px; margin: 0 0 12px; line-height: 1.5; }
.strategy-meta { display: flex; align-items: center; gap: 12px; }
.create-time { font-size: 12px; color: var(--tl-text-tertiary); }
</style>
