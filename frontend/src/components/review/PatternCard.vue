<script setup lang="ts">
import { computed } from 'vue'

import type { BehaviorPattern, PatternStatus } from '@/types/review'

const props = defineProps<{
  pattern: BehaviorPattern
}>()

const emit = defineEmits<{
  (event: 'update-status', id: number, status: PatternStatus): void
}>()

const patternTypeTag = computed(() => (props.pattern.pattern_type === 'strength' ? 'success' : 'danger'))
const patternTypeLabel = computed(() => (props.pattern.pattern_type === 'strength' ? '优势' : '弱点'))
const statusTag = computed(() => {
  if (props.pattern.status === 'resolved') {
    return 'success'
  }
  if (props.pattern.status === 'dismissed') {
    return 'info'
  }
  return 'warning'
})
const statusLabel = computed(() => {
  if (props.pattern.status === 'resolved') {
    return '已解决'
  }
  if (props.pattern.status === 'dismissed') {
    return '已忽略'
  }
  return '进行中'
})
</script>

<template>
  <el-card shadow="hover" class="pattern-card">
    <div class="card-header">
      <div class="title-row">
        <h4 class="card-title">{{ pattern.title }}</h4>
        <el-tag :type="patternTypeTag" size="small">{{ patternTypeLabel }}</el-tag>
      </div>
      <el-tag :type="statusTag" effect="plain" size="small">{{ statusLabel }}</el-tag>
    </div>

    <p class="card-description">{{ pattern.description }}</p>

    <div class="card-meta">
      <span>关联维度：{{ pattern.dimension || '综合' }}</span>
      <span>证据数：{{ pattern.evidence_ids.length }}</span>
    </div>

    <div v-if="pattern.status === 'active'" class="card-actions">
      <el-button size="small" type="success" plain @click="emit('update-status', pattern.id, 'resolved')">
        标记已解决
      </el-button>
      <el-button size="small" @click="emit('update-status', pattern.id, 'dismissed')">
        忽略
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.pattern-card {
  border-radius: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--tl-text);
}

.card-description {
  margin: 12px 0;
  line-height: 1.7;
  color: var(--tl-text-secondary);
}

.card-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
</style>
