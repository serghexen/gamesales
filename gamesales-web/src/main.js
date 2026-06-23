import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import stagingLogoSrc from './assets/logo-staging.jpg'

function setPageIcon(href) {
  // Меняем иконки страницы для тестового стенда, чтобы вкладка сразу отличалась от production.
  const iconLinks = document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]')
  iconLinks.forEach((link) => {
    link.setAttribute('href', href)
    link.setAttribute('type', 'image/jpeg')
  })
}

// Добавляем версию в title вкладки, чтобы после релиза сразу видеть актуальную сборку.
const rawAppVersion = String(import.meta.env.VITE_APP_VERSION || '').trim()
const appVersion = rawAppVersion.replace(/^(\d+)\.(\d+)\.0$/, '$1.$2')
document.title = appVersion ? `AsatWork v${appVersion}` : 'AsatWork'

if (String(import.meta.env.VITE_APP_ENV || '').trim().toLowerCase() === 'staging') {
  setPageIcon(stagingLogoSrc)
}

createApp(App).use(router).mount('#app')
