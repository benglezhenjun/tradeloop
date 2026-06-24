<template>
  <div v-if="error" class="error-boundary">
    <el-result icon="error" title="页面出错了" :sub-title="error.message || '渲染时发生未预期错误'">
      <template #extra>
        <el-button type="primary" @click="reset">重试</el-button>
        <el-button @click="reload">刷新页面</el-button>
      </template>
    </el-result>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { onErrorCaptured, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

// 渲染级错误边界：某个视图在渲染/生命周期里抛错时，降级为可恢复的提示，
// 而不是整页白屏。配合 main.ts 的全局 errorHandler / router.onError 形成兜底。
const error = ref<Error | null>(null)
const route = useRoute()

onErrorCaptured((err) => {
  error.value = err instanceof Error ? err : new Error(String(err))
  return false
})

// 切换路由时自动清错，让用户能离开出错页
watch(
  () => route.fullPath,
  () => {
    error.value = null
  },
)

function reset() {
  error.value = null
}

function reload() {
  window.location.reload()
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  justify-content: center;
  padding-top: 40px;
}
</style>
