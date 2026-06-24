<template>
  <el-aside
    class="sidebar"
    :class="{ 'is-narrow': isNarrow, 'is-open': open }"
    width="210px"
  >
    <div class="sidebar-logo">
      <span class="logo-mark"><i class="logo-dot" />知行</span>
      <div class="logo-text">
        <span class="logo-name">TradeLoop</span>
        <span class="logo-sub">知行盘</span>
      </div>
      <el-tag size="small" class="logo-tag" effect="dark" round>V8</el-tag>
    </div>

    <el-menu
      :default-active="currentPath"
      router
      class="sidebar-menu"
      background-color="transparent"
      text-color="rgba(255,255,255,0.62)"
      active-text-color="#a5b4fc"
      @select="emit('navigate')"
    >
      <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <span class="status" :class="{ online: appStore.backendOnline }">
        <span class="status-dot" />
        {{ appStore.backendOnline ? '后端在线' : '后端离线' }}
      </span>
    </div>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Coin,
  DataAnalysis,
  House,
  List,
  Notebook,
  Search,
  Setting,
  Star,
  Tickets,
  TrendCharts,
} from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'

defineProps<{ isNarrow: boolean; open: boolean }>()
const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const appStore = useAppStore()

const currentPath = computed(() => route.path)

const navItems = [
  { path: '/', label: '仪表盘', icon: House },
  { path: '/watchlist', label: '自选股', icon: Star },
  { path: '/screening', label: '策略筛选', icon: Search },
  { path: '/strategies', label: '策略管理', icon: List },
  { path: '/analysis', label: '智能分析', icon: DataAnalysis },
  { path: '/sentiment', label: '市场情绪', icon: TrendCharts },
  { path: '/plan', label: '交易计划', icon: Notebook },
  { path: '/trade', label: '交易记录', icon: Tickets },
  { path: '/position', label: '持仓', icon: Coin },
  { path: '/review', label: '交易复盘', icon: DataAnalysis },
  { path: '/settings', label: '设置', icon: Setting },
]
</script>

<style scoped>
.sidebar {
  background: rgba(12, 14, 22, 0.72);
  backdrop-filter: blur(22px) saturate(140%);
  -webkit-backdrop-filter: blur(22px) saturate(140%);
  border-right: 1px solid var(--tl-border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
  transition: transform var(--tl-transition);
}

.sidebar.is-narrow {
  transform: translateX(-100%);
}

.sidebar.is-narrow.is-open {
  transform: translateX(0);
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.5);
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--tl-border);
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  padding: 5px 9px;
  border-radius: 9px;
}

.logo-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c7d2fe;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-name {
  font-size: 13px;
  font-weight: 600;
  color: #eceef5;
  letter-spacing: 0.3px;
}

.logo-sub {
  font-size: 11px;
  color: var(--tl-text-tertiary);
}

.logo-tag {
  margin-left: auto;
  background: rgba(99, 102, 241, 0.2) !important;
  border-color: rgba(99, 102, 241, 0.4) !important;
  color: #c7d2fe !important;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 8px 10px;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 42px;
  border-radius: 10px;
  margin-bottom: 2px;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: rgba(99, 102, 241, 0.16) !important;
  color: #c7d2fe !important;
}

.sidebar-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, #818cf8, #6366f1);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.05) !important;
  color: #eceef5 !important;
}

.sidebar-footer {
  padding: 14px 16px;
  border-top: 1px solid var(--tl-border);
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--up-color);
}

.status.online {
  color: var(--down-color);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
}
</style>
