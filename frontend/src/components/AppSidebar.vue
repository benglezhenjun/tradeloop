<template>
  <el-aside class="sidebar" width="200px">
    <div class="sidebar-logo">
      <span class="logo-text">A股工作台</span>
      <el-tag size="small" type="warning">V7</el-tag>
    </div>

    <el-menu
      :default-active="currentPath"
      router
      class="sidebar-menu"
      background-color="#1a1a2e"
      text-color="#c0c4cc"
      active-text-color="#409EFF"
    >
      <el-menu-item index="/">
        <el-icon><House /></el-icon>
        <span>仪表盘</span>
      </el-menu-item>

      <el-menu-item index="/watchlist">
        <el-icon><Star /></el-icon>
        <span>自选股</span>
      </el-menu-item>

      <el-menu-item index="/screening">
        <el-icon><Search /></el-icon>
        <span>策略筛选</span>
      </el-menu-item>

      <el-menu-item index="/strategies">
        <el-icon><List /></el-icon>
        <span>策略管理</span>
      </el-menu-item>

      <el-menu-item index="/analysis">
        <el-icon><DataAnalysis /></el-icon>
        <span>智能分析</span>
      </el-menu-item>

      <el-menu-item index="/sentiment">
        <el-icon><DataAnalysis /></el-icon>
        <span>市场情绪</span>
      </el-menu-item>

      <el-menu-item index="/plan">
        <el-icon><Notebook /></el-icon>
        <span>交易计划</span>
      </el-menu-item>

      <el-menu-item index="/trade">
        <el-icon><Tickets /></el-icon>
        <span>交易记录</span>
      </el-menu-item>

      <el-menu-item index="/position">
        <el-icon><Coin /></el-icon>
        <span>持仓</span>
      </el-menu-item>

      <el-menu-item index="/review">
        <el-icon><DataAnalysis /></el-icon>
        <span>交易复盘</span>
      </el-menu-item>

      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <span>设置</span>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <el-badge :is-dot="!appStore.backendOnline" type="danger">
        <span class="status-text" :class="{ online: appStore.backendOnline }">
          {{ appStore.backendOnline ? '后端在线' : '后端离线' }}
        </span>
      </el-badge>
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
} from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()

const currentPath = computed(() => route.path)
</script>

<style scoped>
.sidebar {
  background-color: #1a1a2e;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-bottom: 1px solid #2a2a4a;
}

.logo-text {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: #2a2a4a !important;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background-color: #22223a !important;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #2a2a4a;
  text-align: center;
}

.status-text {
  font-size: 12px;
  color: #f56c6c;
}

.status-text.online {
  color: #67c23a;
}
</style>
