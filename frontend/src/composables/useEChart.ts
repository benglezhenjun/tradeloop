/**
 * ECharts 生命周期 composable。
 *
 * 统一解决此前各视图 `echarts.init` 后「从不 dispose、窗口/容器变化不 resize」的问题：
 * - 首次 setOption 时按容器懒初始化（兼容 v-if 延迟挂载的图表容器）
 * - ResizeObserver 跟随容器尺寸变化自动 resize（侧边栏折叠、窄屏都生效）
 * - 组件卸载时自动 dispose，杜绝内存泄漏
 * - 默认套用暗色玻璃主题 tl-dark
 */
import { onBeforeUnmount, type Ref } from 'vue'

import { echarts, type ECharts, TL_DARK_THEME } from '@/lib/echarts'

type EChartsOption = Parameters<ECharts['setOption']>[0]
type SetOptionOpts = Parameters<ECharts['setOption']>[1]

export function useEChart(elRef: Ref<HTMLElement | null>) {
  let chart: ECharts | null = null
  let ro: ResizeObserver | null = null

  function ensure(): ECharts | null {
    if (!elRef.value) return null
    if (!chart) {
      chart = echarts.init(elRef.value, TL_DARK_THEME)
      ro = new ResizeObserver(() => chart?.resize())
      ro.observe(elRef.value)
    }
    return chart
  }

  function setOption(option: EChartsOption, opts?: SetOptionOpts) {
    const instance = ensure()
    if (instance) instance.setOption(option, opts)
  }

  function dispose() {
    ro?.disconnect()
    ro = null
    chart?.dispose()
    chart = null
  }

  onBeforeUnmount(dispose)

  return {
    setOption,
    resize: () => chart?.resize(),
    getChart: () => chart,
    dispose,
  }
}
