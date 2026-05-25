import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const appVersion = process.env.VITE_APP_VERSION || process.env.npm_package_version || 'dev'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.vitest.test.js'],
  },
})
