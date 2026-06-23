import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, '/')

          // Keep the main entry slimmer by splitting heavy shared vendors.
          if (
            normalizedId.includes('node_modules/vue') ||
            normalizedId.includes('node_modules/pinia') ||
            normalizedId.includes('node_modules/vue-router') ||
            normalizedId.includes('node_modules/axios')
          ) {
            return 'vendor-core'
          }
          if (normalizedId.includes('node_modules/marked')) {
            return 'vendor-utils'
          }
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
