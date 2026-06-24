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

/** API 密钥（凭证）状态：后端只返回打码值，绝不返回完整 key。 */
export interface CredentialStatus {
  tushare: { configured: boolean; masked: string }
  llm: { configured: boolean; masked: string; provider: string; base_url: string; model: string }
}

/** 保存凭证：空字段=不改（避免清掉已存 key）。 */
export interface CredentialUpdate {
  tushare_token?: string
  llm_api_key?: string
  llm_base_url?: string
  llm_model?: string
}

/** 联网校验结果。 */
export interface CredentialCheck {
  tushare: { ok: boolean; reason?: string }
  llm: { ok: boolean; reason?: string }
}
