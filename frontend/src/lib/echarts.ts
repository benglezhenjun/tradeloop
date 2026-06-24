import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
])

// 暗色玻璃主题：透明底 + 半透明轴线/文字，配合 theme.css 的极光背景。
// 各视图只需设置 series 的涨跌色，轴/网格/文字样式由主题统一接管。
const axisCommon = {
  axisLine: { lineStyle: { color: 'rgba(255,255,255,0.22)' } },
  axisTick: { lineStyle: { color: 'rgba(255,255,255,0.22)' } },
  axisLabel: { color: 'rgba(255,255,255,0.55)' },
  splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
}

echarts.registerTheme('tl-dark', {
  backgroundColor: 'transparent',
  textStyle: { color: 'rgba(255,255,255,0.72)' },
  title: { textStyle: { color: '#eceef5' }, subtextStyle: { color: 'rgba(255,255,255,0.5)' } },
  legend: { textStyle: { color: 'rgba(255,255,255,0.6)' } },
  categoryAxis: axisCommon,
  valueAxis: axisCommon,
  logAxis: axisCommon,
  timeAxis: axisCommon,
  tooltip: {
    backgroundColor: 'rgba(20,22,34,0.92)',
    borderColor: 'rgba(255,255,255,0.12)',
    textStyle: { color: '#eceef5' },
  },
})

export const TL_DARK_THEME = 'tl-dark'

export { echarts }
export type ECharts = echarts.ECharts
