<script setup lang="ts">
/**
 * K线图组件
 *
 * 使用 ECharts 绘制：上方蜡烛图+均线，下方成交量柱状图。
 * A股配色：涨红跌绿。
 */
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
} from 'echarts/components'
import { TL_DARK_THEME } from '@/lib/echarts'
import type { KlineItem } from '@/types/watchlist'

// 按需注册 ECharts 组件（减小打包体积）
use([
  CanvasRenderer,
  CandlestickChart,
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
])

const props = defineProps<{
  klines: KlineItem[]
}>()

// A股配色
const UP_COLOR = '#ec0000' // 涨 = 红
const DOWN_COLOR = '#00da3c' // 跌 = 绿

/** 计算简单移动平均线 */
function calcMA(data: (number | null)[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
      continue
    }
    let sum = 0
    let valid = true
    for (let j = 0; j < period; j++) {
      const val = data[i - j]
      if (val == null) {
        valid = false
        break
      }
      sum += val
    }
    result.push(valid ? Math.round((sum / period) * 100) / 100 : null)
  }
  return result
}

const chartOption = computed(() => {
  const klines = props.klines
  if (klines.length === 0) return {}

  const dates = klines.map((k) => k.date)
  const closes = klines.map((k) => k.close)
  // ECharts candlestick 数据格式: [open, close, low, high]
  const ohlc = klines.map((k) => [k.open, k.close, k.low, k.high])
  const volumes = klines.map((k, i) => {
    const cur = klines[i]
    // 判断涨跌来决定柱子颜色：收盘 >= 开盘为涨
    const isUp = (cur?.close ?? 0) >= (cur?.open ?? 0)
    return {
      value: cur?.vol ?? 0,
      itemStyle: { color: isUp ? UP_COLOR : DOWN_COLOR, opacity: 0.6 },
    }
  })

  const ma5 = calcMA(closes, 5)
  const ma10 = calcMA(closes, 10)
  const ma20 = calcMA(closes, 20)
  const ma60 = calcMA(closes, 60)

  return {
    animation: false,
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'],
      top: 0,
      textStyle: { fontSize: 11 },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: [
      { left: 60, right: 20, top: 40, height: '55%' }, // 主图（K线）
      { left: 60, right: 20, top: '75%', height: '15%' }, // 副图（成交量）
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        gridIndex: 0,
        axisLabel: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        boundaryGap: true,
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 1,
        axisLabel: { fontSize: 10 },
        axisTick: { show: false },
        splitLine: { show: false },
        boundaryGap: true,
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        splitArea: { show: true, areaStyle: { color: ['transparent', 'rgba(255,255,255,0.02)'] } },
        axisLabel: { fontSize: 10 },
        scale: true,
      },
      {
        type: 'value',
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: Math.max(0, 100 - Math.min(100, (60 / klines.length) * 100)),
        end: 100,
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        top: '93%',
        height: 20,
        start: Math.max(0, 100 - Math.min(100, (60 / klines.length) * 100)),
        end: 100,
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: UP_COLOR, // 涨的填充色
          color0: DOWN_COLOR, // 跌的填充色
          borderColor: UP_COLOR,
          borderColor0: DOWN_COLOR,
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: ma5,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#f5a623' },
      },
      {
        name: 'MA10',
        type: 'line',
        data: ma10,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#4a90d9' },
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#e96ead' },
      },
      {
        name: 'MA60',
        type: 'line',
        data: ma60,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#50c878' },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
  }
})
</script>

<template>
  <div class="kline-chart-wrapper">
    <VChart
      v-if="klines.length > 0"
      :option="chartOption"
      :theme="TL_DARK_THEME"
      autoresize
      style="width: 100%; height: 100%"
    />
    <div v-else class="empty-state">暂无K线数据</div>
  </div>
</template>

<style scoped>
.kline-chart-wrapper {
  width: 100%;
  height: 500px;
  min-height: 400px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 14px;
}
</style>
