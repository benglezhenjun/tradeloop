/**
 * 统一错误消息提取。
 *
 * axios 实例的响应拦截器已把后端 `detail` / 网络错误整理成 `Error`（见 api/index.ts），
 * 这里只做最后一层兜底：是 Error 就取 message，否则用调用方给的 fallback 文案。
 */
export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
