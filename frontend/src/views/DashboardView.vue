<template>
  <div class="dashboard-view" v-loading="store.loading">
    <el-empty
      v-if="!store.loading && store.overview?.trade_date === null"
      description="暂无行情数据，请先在设置页触发数据同步"
      :image-size="120"
    >
      <el-button type="primary" @click="$router.push('/settings')">前往设置</el-button>
    </el-empty>

    <template v-else-if="store.overview !== null">
      <div class="dashboard-header">
        <span class="date-label">
          {{ store.overview.trade_date ? formatDate(store.overview.trade_date) : '' }}
          &nbsp;市场概览
        </span>
        <el-button size="small" :loading="store.loading" @click="store.fetchAll()">刷新</el-button>
      </div>

      <el-card v-if="store.sentimentSummary" shadow="never" class="section-card sentiment-section">
        <template #header>
          <div class="section-header">
            <span class="section-title">市场情绪摘要</span>
            <span class="section-meta">
              {{ store.sentimentSummary.trade_date ? formatDate(store.sentimentSummary.trade_date) : '暂无日期' }}
            </span>
          </div>
        </template>

        <div class="sentiment-grid">
          <div v-for="item in sentimentTiles" :key="item.key" class="sentiment-tile" :class="item.theme">
            <div class="sentiment-label">{{ item.label }}</div>
            <div class="sentiment-value">{{ item.value }}</div>
            <div v-if="item.note" class="sentiment-note">{{ item.note }}</div>
          </div>
        </div>
      </el-card>

      <el-row :gutter="12" class="overview-row">
        <el-col :xs="12" :sm="8" :md="4">
          <el-card shadow="never" class="ov-card up-card is-hover-lift">
            <div class="ov-value num">{{ store.overview.up_count.toLocaleString() }}</div>
            <div class="ov-label">上涨</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <el-card shadow="never" class="ov-card down-card is-hover-lift">
            <div class="ov-value num">{{ store.overview.down_count.toLocaleString() }}</div>
            <div class="ov-label">下跌</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <el-card shadow="never" class="ov-card limit-up-card is-hover-lift">
            <div class="ov-value num">{{ store.overview.limit_up_count.toLocaleString() }}</div>
            <div class="ov-label">涨停</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <el-card shadow="never" class="ov-card limit-down-card is-hover-lift">
            <div class="ov-value num">{{ store.overview.limit_down_count.toLocaleString() }}</div>
            <div class="ov-label">跌停</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <el-card shadow="never" class="ov-card is-hover-lift">
            <div class="ov-value num">{{ store.overview.total_amount_yi.toFixed(0) }}亿</div>
            <div class="ov-label">成交额</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <el-card
            shadow="never"
            class="ov-card is-hover-lift"
            :class="store.overview.avg_pct_chg >= 0 ? 'up-card' : 'down-card'"
          >
            <div class="ov-value num">
              {{ store.overview.avg_pct_chg >= 0 ? '+' : '' }}{{ store.overview.avg_pct_chg.toFixed(2) }}%
            </div>
            <div class="ov-label">平均涨跌幅</div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="section-card" v-if="store.industryHeat.length > 0">
        <template #header>
          <span class="section-title">行业热度（按今日平均涨跌幅排序）</span>
        </template>
        <div ref="industryChartRef" :style="{ height: industryChartHeight + 'px' }" />
      </el-card>

      <el-card shadow="never" class="section-card" v-if="store.breadth.length > 0">
        <template #header>
          <span class="section-title">市场宽度趋势（近 {{ store.breadth.length }} 个交易日）</span>
        </template>
        <div ref="breadthChartRef" style="height: 280px" />
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { useEChart } from '@/composables/useEChart'
import { useDashboardStore } from '@/stores/dashboard'

const UP = '#ff5a6e'
const DOWN = '#25d0a0'
const FLAT = '#8a90a2'
const LABEL = 'rgba(255,255,255,0.5)'

const store = useDashboardStore()

const industryChartRef = ref<HTMLElement | null>(null)
const breadthChartRef = ref<HTMLElement | null>(null)

const industryChart = useEChart(industryChartRef)
const breadthChart = useEChart(breadthChartRef)

const industryChartHeight = computed(() => Math.max(400, store.industryHeat.length * 28))

const sentimentTiles = computed(() => {
  const summary = store.sentimentSummary
  if (!summary) return []

  return [
    {
      key: 'max-limit-height',
      label: '连板高度',
      value: `${summary.max_limit_height} 板`,
      note: summary.max_limit_height_count > 0 ? `共 ${summary.max_limit_height_count} 只高标` : '暂无高标',
      theme: 'theme-red',
    },
    {
      key: 'broken-rate',
      label: '炸板率',
      value: formatRatio(summary.broken_rate),
      note: `炸板 ${summary.limit_broken_count} / 封板 ${summary.limit_up_count}`,
      theme: 'theme-green',
    },
    {
      key: 'yday-premium',
      label: '昨日涨停溢价',
      value: formatSignedPercent(summary.yday_limit_premium_avg),
      note: `中位数 ${formatSignedPercent(summary.yday_limit_premium_median)}，样本 ${summary.yday_limit_sample_count} 只`,
      theme: 'theme-gold',
    },
    {
      key: 'high-board',
      label: '高位晋级率',
      value: formatRatio(summary.high_board_promotion_rate),
      note: `晋级 ${summary.high_board_advanced} / ${summary.high_board_total}，阈值 ${summary.high_board_threshold} 板`,
      theme: 'theme-blue',
    },
    {
      key: 'main-theme',
      label: '主线主题',
      value: summary.main_theme_name || '暂无',
      note: summary.main_theme_name
        ? `${summary.main_theme_streak_days} 日连贯${
            summary.main_theme_score !== null ? ` · 热度 ${summary.main_theme_score.toFixed(1)}` : ''
          }`
        : '等待情绪数据',
      theme: 'theme-violet',
    },
  ]
})

function formatDate(d: string) {
  return d.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

function formatRatio(value: number) {
  return `${(value * 100).toFixed(2)}%`
}

function formatSignedPercent(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function renderIndustryChart() {
  if (store.industryHeat.length === 0) return

  const data = [...store.industryHeat].reverse()
  const industries = data.map((d) => d.industry)
  const values = data.map((d) => d.avg_pct_chg)

  industryChart.setOption({
    grid: { left: 80, right: 60, top: 16, bottom: 16, containLabel: false },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: Array<{ name?: string }>) => {
        const p = params[0]
        if (!p) return ''
        const idx = data.findIndex((d) => d.industry === p.name)
        const item = idx >= 0 ? data[idx] : null
        if (!item) return ''
        return (
          `<b>${item.industry}</b><br/>` +
          `平均涨跌幅：${item.avg_pct_chg >= 0 ? '+' : ''}${item.avg_pct_chg.toFixed(2)}%<br/>` +
          `成交额：${item.total_amount_yi.toFixed(1)}亿<br/>` +
          `上涨：${item.up_count} / 下跌：${item.down_count}`
        )
      },
    },
    xAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => (v >= 0 ? `+${v}%` : `${v}%`) },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: industries,
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v) => ({
          value: v,
          itemStyle: { color: v >= 0 ? UP : DOWN, borderRadius: [0, 3, 3, 0] },
        })),
        label: {
          show: true,
          position: (v: { data: { value: number } }) => (v.data.value >= 0 ? 'right' : 'left'),
          formatter: (p: { data: { value: number } }) => `${p.data.value >= 0 ? '+' : ''}${p.data.value.toFixed(2)}%`,
          fontSize: 11,
          color: LABEL,
        },
      },
    ],
  })
}

function renderBreadthChart() {
  if (store.breadth.length === 0) return

  const dates = store.breadth.map((d) => d.trade_date.replace(/(\d{4})(\d{2})(\d{2})/, '$2/$3'))
  const upData = store.breadth.map((d) => d.up_count)
  const downData = store.breadth.map((d) => d.down_count)
  const flatData = store.breadth.map((d) => d.flat_count)

  breadthChart.setOption({
    grid: { left: 50, right: 16, top: 16, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['上涨', '下跌', '平盘'] },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: 'value', name: '家数' },
    series: [
      {
        name: '上涨',
        type: 'line',
        data: upData,
        smooth: true,
        areaStyle: { opacity: 0.12 },
        lineStyle: { color: UP },
        itemStyle: { color: UP },
      },
      {
        name: '下跌',
        type: 'line',
        data: downData,
        smooth: true,
        areaStyle: { opacity: 0.12 },
        lineStyle: { color: DOWN },
        itemStyle: { color: DOWN },
      },
      {
        name: '平盘',
        type: 'line',
        data: flatData,
        smooth: true,
        lineStyle: { color: FLAT, type: 'dashed' },
        itemStyle: { color: FLAT },
      },
    ],
  })
}

watch(
  () => [store.industryHeat, store.breadth],
  async () => {
    await nextTick()
    renderIndustryChart()
    renderBreadthChart()
  },
  { deep: true },
)

onMounted(async () => {
  await store.fetchAll()
  await nextTick()
  renderIndustryChart()
  renderBreadthChart()
})
</script>

<style scoped>
.dashboard-view {
  max-width: 1100px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.date-label {
  font-size: 17px;
  font-weight: 600;
  color: var(--tl-text);
}

.overview-row {
  margin-bottom: 20px;
  row-gap: 12px;
}

.sentiment-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.section-meta {
  font-size: 12px;
  color: var(--tl-text-tertiary);
}

.sentiment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.sentiment-tile {
  border-radius: 12px;
  padding: 14px 16px;
  min-height: 98px;
  background:
    radial-gradient(120% 120% at 100% 0%, rgba(255, 255, 255, 0.06), transparent 55%),
    var(--tl-glass);
  border: 1px solid var(--tl-border);
  border-top-color: var(--tl-border-strong);
  transition: transform var(--tl-transition), border-color var(--tl-transition);
}

.sentiment-tile:hover {
  transform: translateY(-2px);
  border-color: var(--tl-border-strong);
}

.sentiment-label {
  font-size: 12px;
  color: var(--tl-text-secondary);
  margin-bottom: 10px;
}

.sentiment-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--tl-text);
  word-break: break-word;
}

.sentiment-note {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--tl-text-secondary);
}

.theme-red .sentiment-value {
  color: var(--up-color);
}

.theme-green .sentiment-value {
  color: var(--down-color);
}

.theme-gold .sentiment-value {
  color: #fbbf24;
}

.theme-blue .sentiment-value {
  color: #818cf8;
}

.theme-violet .sentiment-value {
  color: #c4b5fd;
}

.ov-card {
  text-align: center;
  padding: 4px 0;
}

.ov-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--tl-text);
}

.ov-label {
  font-size: 12px;
  color: var(--tl-text-secondary);
  margin-top: 4px;
}

.up-card .ov-value {
  color: var(--up-color);
}

.down-card .ov-value {
  color: var(--down-color);
}

.limit-up-card .ov-value {
  color: var(--up-strong);
}

.limit-down-card .ov-value {
  color: var(--down-strong);
}

.section-card {
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tl-text);
}
</style>
