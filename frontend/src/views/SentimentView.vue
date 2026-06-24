<template>
  <div class="sentiment-view" v-loading="pageBusy">
    <section class="hero-strip">
      <div class="hero-copy">
        <div class="eyebrow">Market Sentiment</div>
        <h1>市场情绪</h1>
        <p>
          最新交易日 <strong>{{ latestDateLabel }}</strong>
          <span v-if="summary">
            ，主线为 <strong>{{ summary.main_theme_name || '暂无' }}</strong>
          </span>
        </p>
      </div>

      <div class="hero-meta">
        <div class="meta-chip">
          <span class="meta-label">覆盖窗口</span>
          <strong>{{ store.currentDays }} 天</strong>
        </div>
        <div class="meta-chip">
          <span class="meta-label">快照状态</span>
          <strong>{{ pageBusy ? '更新中' : '已就绪' }}</strong>
        </div>
        <el-radio-group
          class="window-switch"
          :model-value="store.currentDays"
          size="small"
          @change="handleDaysChange"
        >
          <el-radio-button v-for="days in dayOptions" :key="days" :label="days">
            {{ days }} 天
          </el-radio-button>
        </el-radio-group>
        <el-button class="refresh-btn" :loading="pageBusy" @click="refreshPage">刷新数据</el-button>
      </div>
    </section>

    <section class="summary-strip">
      <article
        v-for="(card, index) in summaryCards"
        :key="card.key"
        class="summary-card"
        :style="{ '--accent': card.accent, '--delay': `${index * 90}ms` }"
      >
        <div class="summary-label">{{ card.label }}</div>
        <div class="summary-value">{{ card.value }}</div>
        <div class="summary-note">{{ card.note }}</div>
      </article>
    </section>

    <section class="section-shell">
      <div class="section-head">
        <div>
          <h2>5 指标走势图</h2>
          <p>以最近 {{ store.currentDays }} 天数据回看市场强弱变化，快速捕捉情绪拐点。</p>
        </div>
        <div class="section-badge">{{ latestDateLabel }}</div>
      </div>

      <div v-if="store.history.length" class="trend-grid">
        <article
          v-for="(metric, index) in trendMetrics"
          :key="metric.key"
          class="trend-panel"
          :style="{ '--accent': metric.accent, '--delay': `${index * 70}ms` }"
        >
          <div class="trend-head">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.currentText }}</strong>
          </div>
          <div class="trend-chart" :ref="bindTrendRef(metric.key)"></div>
        </article>
      </div>
      <div v-else class="empty-state trend-empty">暂无情绪趋势数据</div>
    </section>

    <section class="lower-grid">
      <section class="section-shell theme-shell">
        <div class="section-head compact">
          <div>
            <h2>主线演化区</h2>
            <p>展示近期主线的切换与持续天数，便于识别资金偏好变化。</p>
          </div>
        </div>

        <div v-if="themeHistory.length" class="theme-track">
          <article v-for="item in themeHistory" :key="item.trade_date" class="theme-item">
            <div class="theme-date">{{ formatDate(item.trade_date) }}</div>
            <div class="theme-name">{{ item.main_theme_name || item.main_theme_code || '无主线' }}</div>
            <div class="theme-meta">
              <span>连续 {{ item.main_theme_streak_days }} 天</span>
              <span v-if="item.main_theme_score !== null">强度 {{ formatPlainNumber(item.main_theme_score) }}</span>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">暂无主线历史数据</div>
      </section>

      <section class="section-shell detail-shell">
        <div class="section-head compact">
          <div>
            <h2>分项解释区域</h2>
            <p>将涨停、炸板、昨日溢价和高位晋级样本拆开，方便人工复核当天情绪结构。</p>
          </div>
        </div>

        <div v-if="detail" class="detail-grid">
          <article class="detail-block">
            <div class="detail-title">涨停样本</div>
            <ul class="sample-list">
              <li v-for="item in detail.limit_up_samples || []" :key="item.ts_code">
                <span class="sample-code">{{ item.ts_code }}</span>
                <span class="sample-main">{{ item.name || item.ts_code }}</span>
                <span class="sample-sub">连板 {{ item.limit_times }} 次</span>
              </li>
              <li v-if="!(detail.limit_up_samples || []).length" class="sample-empty">暂无样本</li>
            </ul>
          </article>

          <article class="detail-block">
            <div class="detail-title">炸板样本</div>
            <ul class="sample-list">
              <li v-for="item in detail.limit_broken_samples || []" :key="item.ts_code">
                <span class="sample-code">{{ item.ts_code }}</span>
                <span class="sample-main">{{ item.name || item.ts_code }}</span>
                <span class="sample-sub">封板失败</span>
              </li>
              <li v-if="!(detail.limit_broken_samples || []).length" class="sample-empty">暂无样本</li>
            </ul>
          </article>

          <article class="detail-block">
            <div class="detail-title">昨日涨停溢价</div>
            <ul class="sample-list">
              <li v-for="item in detail.yday_limit_samples || []" :key="item.ts_code">
                <span class="sample-code">{{ item.ts_code }}</span>
                <span class="sample-main">{{ item.name || item.ts_code }}</span>
                <span class="sample-sub">
                  {{ item.prev_limit_times ?? '--' }} 次连板，今日 {{ formatPercentValue(item.today_pct_chg) }}
                </span>
              </li>
              <li v-if="!(detail.yday_limit_samples || []).length" class="sample-empty">暂无样本</li>
            </ul>
          </article>

          <article class="detail-block">
            <div class="detail-title">高位晋级</div>
            <ul class="sample-list">
              <li v-for="item in detail.high_board_samples || []" :key="item.ts_code">
                <span class="sample-code">{{ item.ts_code }}</span>
                <span class="sample-main">{{ item.name || item.ts_code }}</span>
                <span class="sample-sub">
                  {{ item.prev_limit_times ?? '--' }} -> {{ item.current_limit_times ?? '--' }}
                  <strong>{{ item.is_advanced ? '晋级成功' : '未晋级' }}</strong>
                </span>
              </li>
              <li v-if="!(detail.high_board_samples || []).length" class="sample-empty">暂无样本</li>
            </ul>
          </article>

          <article class="detail-block detail-block-wide">
            <div class="detail-title">题材领涨</div>
            <ul class="theme-leader-list">
              <li v-for="item in detail.theme_leaders || []" :key="item.theme_code">
                <div class="leader-main">
                  <span class="sample-code">{{ item.theme_code }}</span>
                  <strong>{{ item.theme_name || item.theme_code }}</strong>
                </div>
                <div class="leader-meta">
                  <span>Rank {{ item.rank ?? '--' }}</span>
                  <span>Score {{ formatPlainNumber(item.score) }}</span>
                  <span v-if="item.up_stat">{{ item.up_stat }}</span>
                </div>
              </li>
              <li v-if="!(detail.theme_leaders || []).length" class="sample-empty">暂无题材领涨数据</li>
            </ul>
          </article>
        </div>

        <div v-else class="empty-state">暂无分项解释</div>
      </section>
    </section>

    <el-alert
      v-if="store.error"
      class="error-alert"
      type="error"
      :title="store.error"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, watch, type ComponentPublicInstance } from 'vue'

import { echarts, type ECharts, TL_DARK_THEME } from '@/lib/echarts'
import { useSentimentStore } from '@/stores/sentiment'
import type { MainThemeHistoryPoint, SentimentDetail, SentimentHistoryPoint, SentimentSummary } from '@/types/sentiment'

type TrendMetricKey =
  | 'max_limit_height'
  | 'broken_rate'
  | 'yday_limit_premium_avg'
  | 'high_board_promotion_rate'
  | 'main_theme_score'

type TrendMetricConfig = {
  key: TrendMetricKey
  label: string
  accent: string
  currentText: string
  seriesValues: (row: SentimentHistoryPoint) => number
  yAxisFormatter: (value: number) => string
}

type TrendMetricRow = SentimentSummary | SentimentHistoryPoint

const store = useSentimentStore()
const dayOptions = [30, 60, 120] as const
const trendChartInstances = new Map<TrendMetricKey, ECharts>()
const trendChartRefs = reactive<Partial<Record<TrendMetricKey, HTMLElement | null>>>({})

const detail = computed<SentimentDetail | null>(() => store.detail)
const pageBusy = computed(() => store.loading || store.detailLoading)
const summary = computed<SentimentSummary | null>(() => store.summary ?? null)
const themeHistory = computed<MainThemeHistoryPoint[]>(() => store.themes.slice(-12))

const trendMetricConfigs: TrendMetricConfig[] = [
  {
    key: 'max_limit_height',
    label: '连板高度',
    accent: '#ea580c',
    currentText: '',
    seriesValues: (row) => Number(row.max_limit_height ?? 0),
    yAxisFormatter: (value) => `${value.toFixed(0)}板`,
  },
  {
    key: 'broken_rate',
    label: '炸板率',
    accent: '#0f766e',
    currentText: '',
    seriesValues: (row) => Number((row.broken_rate ?? 0) * 100),
    yAxisFormatter: (value) => `${value.toFixed(1)}%`,
  },
  {
    key: 'yday_limit_premium_avg',
    label: '昨日涨停溢价',
    accent: '#2563eb',
    currentText: '',
    seriesValues: (row) => Number(row.yday_limit_premium_avg ?? 0),
    yAxisFormatter: (value) => `${value.toFixed(2)}%`,
  },
  {
    key: 'high_board_promotion_rate',
    label: '高位晋级率',
    accent: '#7c3aed',
    currentText: '',
    seriesValues: (row) => Number((row.high_board_promotion_rate ?? 0) * 100),
    yAxisFormatter: (value) => `${value.toFixed(1)}%`,
  },
  {
    key: 'main_theme_score',
    label: '主线强度',
    accent: '#d946ef',
    currentText: '',
    seriesValues: (row) => Number(row.main_theme_score ?? 0),
    yAxisFormatter: (value) => `${value.toFixed(0)}`,
  },
]

const summaryCards = computed(() => [
  {
    key: 'max_limit_height',
    label: '连板高度',
    value: summary.value ? `${summary.value.max_limit_height ?? 0} 板` : '--',
    note: summary.value ? `${summary.value.max_limit_height_count ?? 0} 只达到最高板` : '等待数据',
    accent: '#ea580c',
  },
  {
    key: 'broken_rate',
    label: '炸板率',
    value: summary.value ? formatPercentRatio(summary.value.broken_rate) : '--',
    note: summary.value
      ? `${summary.value.limit_broken_count ?? 0} / ${summary.value.limit_up_count + summary.value.limit_broken_count}`
      : '等待数据',
    accent: '#0f766e',
  },
  {
    key: 'yday_limit_premium_avg',
    label: '昨日涨停溢价',
    value: summary.value ? formatPercentValue(summary.value.yday_limit_premium_avg) : '--',
    note: summary.value ? `${summary.value.yday_limit_sample_count ?? 0} 个样本` : '等待数据',
    accent: '#2563eb',
  },
  {
    key: 'high_board_promotion_rate',
    label: '高位晋级率',
    value: summary.value ? formatPercentRatio(summary.value.high_board_promotion_rate) : '--',
    note: summary.value
      ? `${summary.value.high_board_advanced ?? 0} / ${summary.value.high_board_total ?? 0}`
      : '等待数据',
    accent: '#7c3aed',
  },
  {
    key: 'main_theme_name',
    label: '主线主题',
    value: summary.value?.main_theme_name || summary.value?.main_theme_code || '--',
    note: summary.value ? `连续 ${summary.value.main_theme_streak_days ?? 0} 天` : '等待数据',
    accent: '#d946ef',
  },
])

const trendMetrics = computed(() =>
  trendMetricConfigs.map((metric) => ({
    ...metric,
    currentText: summary.value ? formatMetricValue(metric.key, summary.value) : '--',
  })),
)

const latestDateLabel = computed(() =>
  formatDate(summary.value?.trade_date ?? store.history[store.history.length - 1]?.trade_date ?? null),
)

function formatDate(date: string | null | undefined) {
  if (!date) return '--'
  return date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

function formatPlainNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })
}

function formatPercentRatio(value: number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${(Number(value) * 100).toFixed(1)}%`
}

function formatPercentValue(value: number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(2)}%`
}

function formatMetricValue(key: TrendMetricKey, row: TrendMetricRow) {
  switch (key) {
    case 'max_limit_height':
      return `${Number(row.max_limit_height ?? 0).toFixed(0)} 板`
    case 'broken_rate':
      return formatPercentRatio(row.broken_rate)
    case 'yday_limit_premium_avg':
      return formatPercentValue(row.yday_limit_premium_avg)
    case 'high_board_promotion_rate':
      return formatPercentRatio(row.high_board_promotion_rate)
    case 'main_theme_score':
      return formatPlainNumber(row.main_theme_score)
    default:
      return '--'
  }
}

function bindTrendRef(key: TrendMetricKey) {
  return (el: Element | ComponentPublicInstance | null) => {
    trendChartRefs[key] = el instanceof HTMLElement ? el : null
  }
}

function renderTrendChart(metric: TrendMetricConfig) {
  const el = trendChartRefs[metric.key]
  if (!el || !store.history.length) return

  let chart = trendChartInstances.get(metric.key)
  if (!chart) {
    chart = echarts.init(el, TL_DARK_THEME)
    trendChartInstances.set(metric.key, chart)
  }

  const xLabels = store.history.map((row) => formatDate(row.trade_date))
  const values = store.history.map(metric.seriesValues)
  const isRatioChart = metric.key === 'broken_rate' || metric.key === 'high_board_promotion_rate'

  chart.setOption({
    animationDuration: 700,
    grid: { left: 46, right: 16, top: 18, bottom: 26, containLabel: false },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] : null
        if (!item || typeof item !== 'object') return ''
        const data = item as { name?: string; value?: number }
        const raw = Number(data.value ?? 0)
        const valueText = isRatioChart ? `${raw.toFixed(1)}%` : metric.yAxisFormatter(raw)
        return `<strong>${data.name ?? ''}</strong><br/>${metric.label}：${valueText}`
      },
    },
    xAxis: {
      type: 'category',
      data: xLabels,
      boundaryGap: false,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => (isRatioChart ? `${value.toFixed(0)}%` : metric.yAxisFormatter(value)),
      },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [
      {
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 3, color: metric.accent },
        itemStyle: { color: metric.accent },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `${metric.accent}40` },
            { offset: 1, color: `${metric.accent}08` },
          ]),
        },
      },
    ],
  })
}

function renderCharts() {
  trendMetricConfigs.forEach((metric) => renderTrendChart(metric))
}

function resizeCharts() {
  trendChartInstances.forEach((chart) => chart.resize())
}

async function refreshPage() {
  await store.fetchPageData(store.currentDays)
  await nextTick()
  renderCharts()
}

async function handleDaysChange(value: string | number | boolean) {
  const days = Number(value)
  if (!Number.isFinite(days) || days <= 0 || days === store.currentDays) {
    return
  }

  await store.fetchPageData(days)
  await nextTick()
  renderCharts()
}

watch(
  () => [store.summary, store.history, store.themes, store.detail],
  async () => {
    await nextTick()
    renderCharts()
  },
  { deep: true },
)

onMounted(async () => {
  await refreshPage()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChartInstances.forEach((chart) => chart.dispose())
  trendChartInstances.clear()
})
</script>

<style scoped>
.sentiment-view {
  position: relative;
  overflow: hidden;
  padding: 4px 4px 24px;
  background:
    radial-gradient(circle at top right, rgba(217, 70, 239, 0.1), transparent 26%),
    radial-gradient(circle at left center, rgba(37, 99, 235, 0.1), transparent 22%),
    transparent;
}

.sentiment-view::before,
.sentiment-view::after {
  content: '';
  position: absolute;
  inset: auto;
  pointer-events: none;
  border-radius: 999px;
  filter: blur(40px);
  opacity: 0.8;
}

.sentiment-view::before {
  width: 180px;
  height: 180px;
  right: -40px;
  top: 80px;
  background: rgba(14, 116, 144, 0.08);
}

.sentiment-view::after {
  width: 220px;
  height: 220px;
  left: -50px;
  bottom: 120px;
  background: rgba(234, 88, 12, 0.08);
}

.hero-strip,
.summary-strip,
.section-shell,
.lower-grid {
  position: relative;
  z-index: 1;
}

.hero-strip {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px 20px;
  margin-bottom: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.1), rgba(37, 99, 235, 0.06));
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.04);
}

.eyebrow {
  color: #2dd4bf;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 700;
}

.hero-copy h1 {
  margin: 6px 0 8px;
  font-size: 32px;
  line-height: 1.1;
  color: var(--tl-text);
}

.hero-copy p {
  margin: 0;
  color: var(--tl-text-secondary);
  font-size: 14px;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-chip {
  min-width: 118px;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}

.meta-label {
  display: block;
  color: var(--tl-text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}

.meta-chip strong {
  color: var(--tl-text);
  font-size: 14px;
}

.refresh-btn {
  align-self: stretch;
}

.window-switch {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 999px;
  padding: 2px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.summary-card,
.trend-panel,
.detail-block,
.theme-shell,
.detail-shell {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}

.summary-card {
  min-height: 114px;
  border-radius: 18px;
  padding: 16px 16px 14px;
  border-top: 3px solid var(--accent);
  animation: rise 0.45s ease both;
  animation-delay: var(--delay);
}

.summary-label {
  color: var(--tl-text-secondary);
  font-size: 12px;
  margin-bottom: 12px;
}

.summary-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--tl-text);
  line-height: 1.1;
}

.summary-note {
  margin-top: 10px;
  color: var(--tl-text-secondary);
  font-size: 12px;
}

.section-shell {
  padding: 18px;
  border-radius: 22px;
  margin-bottom: 16px;
}

.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-head.compact {
  margin-bottom: 12px;
}

.section-head h2 {
  margin: 0;
  font-size: 18px;
  color: var(--tl-text);
}

.section-head p {
  margin: 6px 0 0;
  color: var(--tl-text-secondary);
  font-size: 13px;
}

.section-badge {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.08);
  color: #2dd4bf;
  font-size: 12px;
  font-weight: 700;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.trend-panel {
  padding: 14px;
  border-radius: 18px;
  border-top: 3px solid var(--accent);
  animation: rise 0.45s ease both;
  animation-delay: var(--delay);
}

.trend-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--tl-text);
}

.trend-head span {
  font-size: 13px;
  color: var(--tl-text-secondary);
  font-weight: 600;
}

.trend-head strong {
  font-size: 15px;
  color: var(--tl-text);
}

.trend-chart {
  height: 180px;
  width: 100%;
}

.lower-grid {
  display: grid;
  grid-template-columns: 1fr 1.25fr;
  gap: 16px;
}

.theme-shell,
.detail-shell {
  border-radius: 22px;
  padding: 18px;
}

.theme-track {
  display: grid;
  gap: 12px;
}

.theme-item {
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid var(--tl-border);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04));
}

.theme-date {
  color: var(--tl-text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}

.theme-name {
  color: var(--tl-text);
  font-size: 15px;
  font-weight: 700;
}

.theme-meta,
.leader-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
  color: var(--tl-text-secondary);
  font-size: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-block {
  border-radius: 16px;
  padding: 14px;
}

.detail-block-wide {
  grid-column: 1 / -1;
}

.detail-title {
  color: var(--tl-text);
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 10px;
}

.sample-list,
.theme-leader-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.sample-list li,
.theme-leader-list li {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--tl-border);
}

.sample-code {
  display: inline-block;
  margin-right: 8px;
  color: #2dd4bf;
  font-size: 12px;
  font-weight: 700;
}

.sample-main {
  color: var(--tl-text);
  font-size: 13px;
  font-weight: 600;
}

.sample-sub {
  display: block;
  margin-top: 4px;
  color: var(--tl-text-secondary);
  font-size: 12px;
}

.sample-empty,
.empty-state {
  color: var(--tl-text-tertiary);
  font-size: 13px;
  text-align: center;
  padding: 24px 0;
}

.trend-empty {
  min-height: 180px;
  display: grid;
  place-items: center;
}

.leader-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.leader-main strong {
  color: var(--tl-text);
}

.error-alert {
  margin-top: 10px;
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1200px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .lower-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-strip {
    flex-direction: column;
    align-items: stretch;
  }

  .summary-strip,
  .trend-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .hero-copy h1 {
    font-size: 28px;
  }
}
</style>
