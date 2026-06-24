<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { LegendComponent, RadarComponent, TooltipComponent } from 'echarts/components'

import { TL_DARK_THEME } from '@/lib/echarts'
import type { ReviewScores } from '@/types/review'

use([CanvasRenderer, RadarChart, RadarComponent, TooltipComponent, LegendComponent])

const DIMENSIONS: Array<{ key: keyof ReviewScores; label: string }> = [
  { key: 'entry_timing', label: '入场时机' },
  { key: 'exit_timing', label: '离场时机' },
  { key: 'stop_loss', label: '止损纪律' },
  { key: 'take_profit', label: '止盈执行' },
  { key: 'position_sizing', label: '仓位管理' },
  { key: 'holding_period', label: '持仓周期' },
  { key: 'discipline', label: '交易纪律' },
  { key: 'risk_reward', label: '盈亏比' },
]

const props = withDefaults(
  defineProps<{
    scores: ReviewScores
    size?: number
  }>(),
  {
    size: 300,
  },
)

const values = computed(() => DIMENSIONS.map((dimension) => props.scores[dimension.key]))
const averageScore = computed(() => values.value.reduce((sum, value) => sum + value, 0) / DIMENSIONS.length)

const palette = computed(() => {
  if (averageScore.value >= 7) {
    return {
      line: 'rgba(103, 194, 58, 0.9)',
      area: 'rgba(103, 194, 58, 0.3)',
    }
  }
  if (averageScore.value >= 4) {
    return {
      line: 'rgba(64, 158, 255, 0.9)',
      area: 'rgba(64, 158, 255, 0.3)',
    }
  }
  return {
    line: 'rgba(245, 108, 108, 0.9)',
    area: 'rgba(245, 108, 108, 0.3)',
  }
})

const chartStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

const chartOption = computed(() => ({
  animation: false,
  tooltip: {
    trigger: 'item',
  },
  radar: {
    radius: '64%',
    splitNumber: 5,
    indicator: DIMENSIONS.map((dimension) => ({
      name: dimension.label,
      max: 10,
    })),
    axisName: {
      color: 'rgba(255,255,255,0.7)',
      fontSize: 12,
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(255,255,255,0.12)',
      },
    },
    splitArea: {
      areaStyle: {
        color: ['rgba(255,255,255,0.03)', 'rgba(255,255,255,0.05)'],
      },
    },
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: values.value,
          areaStyle: {
            color: palette.value.area,
          },
          lineStyle: {
            color: palette.value.line,
            width: 2,
          },
          itemStyle: {
            color: palette.value.line,
          },
        },
      ],
    },
  ],
}))
</script>

<template>
  <VChart :option="chartOption" :theme="TL_DARK_THEME" :style="chartStyle" autoresize />
</template>
