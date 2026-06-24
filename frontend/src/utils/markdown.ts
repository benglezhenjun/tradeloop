/**
 * 安全 Markdown 渲染：marked 解析 + DOMPurify 净化。
 *
 * AI 报告/复盘等内容来自 LLM，直接 `v-html` 渲染 marked 输出存在 XSS 风险
 * （Markdown 允许内嵌 HTML，LLM 可能产出或被注入 <script>/onerror 等）。
 * 统一经此函数净化后再渲染。
 */
import DOMPurify from 'dompurify'
import { marked } from 'marked'

export function renderMarkdown(text: string | null | undefined): string {
  if (!text) return ''
  const html = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(html)
}
