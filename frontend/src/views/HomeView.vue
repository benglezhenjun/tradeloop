<template>
  <div class="home-view">
    <div class="welcome-section">
      <h2 class="welcome-title">A股交易辅助系统 V2</h2>
      <p class="welcome-desc">个人交易研究工作台 · 自选股管理 · K线图表 · 策略筛选引擎</p>
    </div>

    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.stock_count.toLocaleString() }}</div>
          <div class="stat-label">股票数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ (stats.quote_count / 10000).toFixed(0) }}万</div>
          <div class="stat-label">行情记录</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.strategy_count }}</div>
          <div class="stat-label">启用策略</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">
            {{ stats.latest_trade_date ? formatDate(stats.latest_trade_date) : '暂无数据' }}
          </div>
          <div class="stat-label">最新数据日期</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="nav-row">
      <el-col :span="6">
        <el-card shadow="hover" class="nav-card" @click="$router.push('/watchlist')">
          <el-icon size="32" color="#F56C6C"><Star /></el-icon>
          <div class="nav-card-title">自选股</div>
          <div class="nav-card-desc">管理关注的股票，分组整理，查看K线走势</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="nav-card" @click="$router.push('/screening')">
          <el-icon size="32" color="#409EFF"><Search /></el-icon>
          <div class="nav-card-title">策略筛选</div>
          <div class="nav-card-desc">选择策略、运行筛选，找出符合条件的候选股</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="nav-card" @click="$router.push('/strategies')">
          <el-icon size="32" color="#67C23A"><List /></el-icon>
          <div class="nav-card-title">策略管理</div>
          <div class="nav-card-desc">创建和编辑策略，自由配置筛选条件与参数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="nav-card" @click="$router.push('/settings')">
          <el-icon size="32" color="#E6A23C"><Setting /></el-icon>
          <div class="nav-card-title">设置 & 数据</div>
          <div class="nav-card-desc">查看同步状态，手动触发数据更新</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Star, Search, List, Setting } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const stats = computed(() => appStore.stats)

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}
</script>

<style scoped>
.home-view { max-width: 960px; }
.welcome-section { margin-bottom: 24px; }
.welcome-title { font-size: 22px; font-weight: 600; margin: 0 0 8px; color: var(--tl-text); }
.welcome-desc { color: var(--tl-text-tertiary); margin: 0; font-size: 14px; }

.stats-row, .nav-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-value { font-size: 26px; font-weight: 700; color: var(--tl-text); }
.stat-label { font-size: 13px; color: var(--tl-text-tertiary); margin-top: 4px; }

.nav-card {
  cursor: pointer;
  text-align: center;
  padding: 8px 0;
  transition: transform 0.15s;
}
.nav-card:hover { transform: translateY(-2px); }
.nav-card-title { font-size: 15px; font-weight: 600; margin: 10px 0 6px; color: var(--tl-text); }
.nav-card-desc { font-size: 13px; color: var(--tl-text-tertiary); line-height: 1.5; }
</style>
