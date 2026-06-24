import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vitest/config'

// 单元测试独立配置：只测 store / api 等纯逻辑，不加载 vue/devtools 插件，
// 默认 node 环境（store 测试 mock 掉 @/api，无需 DOM），保持轻量快速。
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.spec.ts'],
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
