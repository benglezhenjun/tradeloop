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

export { echarts }
export type ECharts = echarts.ECharts
