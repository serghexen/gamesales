import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Добавляем версию в title вкладки, чтобы после релиза сразу видеть актуальную сборку.
const rawAppVersion = String(import.meta.env.VITE_APP_VERSION || '').trim()
const appVersion = rawAppVersion.replace(/^(\d+)\.(\d+)\.0$/, '$1.$2')
document.title = appVersion ? `GameSales v${appVersion}` : 'GameSales'

createApp(App).use(router).mount('#app')
