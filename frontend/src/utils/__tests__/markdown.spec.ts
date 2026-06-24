// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { renderMarkdown } from '@/utils/markdown'

describe('renderMarkdown', () => {
  it('正常渲染 Markdown', () => {
    const html = renderMarkdown('**粗体** 与 `代码`')
    expect(html).toContain('<strong>粗体</strong>')
    expect(html).toContain('<code>代码</code>')
  })

  it('净化掉可执行 <script>（XSS 防护）', () => {
    const html = renderMarkdown('正常文本\n\n<script>alert(1)</script>')
    // 不应出现可执行的 script 标签（被转义成 &lt;script&gt; 文本则安全）
    expect(html).not.toContain('<script')
  })

  it('净化掉事件处理器属性', () => {
    const html = renderMarkdown('<img src=x onerror="alert(1)">')
    expect(html).not.toContain('onerror')
  })

  it('空/null 返回空串', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
  })
})
