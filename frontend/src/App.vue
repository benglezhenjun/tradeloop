<template>
  <el-config-provider :locale="zhCn">
    <el-container class="app-root">
      <AppSidebar :is-narrow="isNarrow" :open="drawerOpen" @navigate="drawerOpen = false" />

      <div v-if="isNarrow && drawerOpen" class="sidebar-backdrop" @click="drawerOpen = false" />

      <el-container class="main-container" :class="{ 'is-narrow': isNarrow }">
        <el-header class="app-header glass">
          <div class="header-left">
            <el-button
              v-if="isNarrow"
              class="menu-toggle"
              text
              :icon="Menu"
              aria-label="打开导航菜单"
              @click="drawerOpen = true"
            />
            <el-text type="info" size="small">
              {{ appStore.stats.latest_trade_date
                ? `最新数据：${formatDate(appStore.stats.latest_trade_date)}`
                : '数据库无数据' }}
            </el-text>
          </div>
          <div class="header-right">
            <el-text size="small" type="info">
              {{ appStore.stats.stock_count.toLocaleString() }} 只股票 ·
              {{ (appStore.stats.quote_count / 10000).toFixed(0) }} 万条行情
            </el-text>
          </div>
        </el-header>
        <el-main class="app-main">
          <RouterView v-slot="{ Component, route }">
            <component :is="Component" :key="route.path" class="tl-fade-in" />
          </RouterView>
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Menu } from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { RouterView } from 'vue-router'

import AppSidebar from '@/components/AppSidebar.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const isNarrow = ref(false)
const drawerOpen = ref(false)
const mql = window.matchMedia('(max-width: 768px)')
function syncNarrow(e: MediaQueryList | MediaQueryListEvent) {
  isNarrow.value = e.matches
  if (!e.matches) drawerOpen.value = false
}

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

onMounted(async () => {
  syncNarrow(mql)
  mql.addEventListener('change', syncNarrow)
  await appStore.checkBackend()
  if (appStore.backendOnline) {
    await appStore.fetchStats()
  }
})

onBeforeUnmount(() => mql.removeEventListener('change', syncNarrow))
</script>

<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.app-root {
  height: 100vh;
}

.main-container {
  margin-left: var(--tl-sidebar-w);
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--tl-transition);
}

.main-container.is-narrow {
  margin-left: 0;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px !important;
  flex-shrink: 0;
  border-radius: 0 !important;
  border-left: none;
  border-right: none;
  border-top: none;
  position: sticky;
  top: 0;
  z-index: 20;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.menu-toggle {
  font-size: 20px;
}

.app-main {
  padding: 22px 24px;
  overflow-y: auto;
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
}
</style>
