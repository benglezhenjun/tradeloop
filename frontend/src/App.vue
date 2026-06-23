<template>
  <el-config-provider :locale="zhCn">
    <el-container class="app-root">
      <AppSidebar />
      <el-container class="main-container">
        <el-header class="app-header">
          <div class="header-left">
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
          <RouterView />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { RouterView } from 'vue-router'

import AppSidebar from '@/components/AppSidebar.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

onMounted(async () => {
  await appStore.checkBackend()
  if (appStore.backendOnline) {
    await appStore.fetchStats()
  }
})
</script>

<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: #f5f7fa;
}

.app-root {
  height: 100vh;
}

.main-container {
  margin-left: 200px;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 48px !important;
  flex-shrink: 0;
}

.app-main {
  padding: 20px 24px;
  overflow-y: auto;
}
</style>
