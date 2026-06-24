/**
 * 通用 API 类型。
 */

/**
 * 列表端点统一信封（见后端 app/api/envelope.py 与重构计划 3.3）。
 * 所有返回领域实体集合的列表端点都用此结构：`{ items, total }`。
 * total 为本次返回条目数（当前未做服务端分页，恒等于 items.length）。
 */
export interface ListEnvelope<T> {
  items: T[]
  total: number
}
