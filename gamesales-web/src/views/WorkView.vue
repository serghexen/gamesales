<template>
  <div class="wrap">
    <header class="top">
      <div>
        <div class="title">GameSales — рабочая зона</div>
        <div class="sub">Пользователь: <b>{{ auth.state.user }}</b></div>
      </div>

      <div class="actions">
        <button class="ghost" @click="loadAccounts" :disabled="loading">
          {{ loading ? 'Загрузка…' : 'Проверить /accounts' }}
        </button>
        <button class="danger" @click="onLogout">Выйти</button>
      </div>
    </header>

    <main class="main">
      <div class="panel">
        <h2>Статус API</h2>
        <p v-if="apiOk === null">не проверяли</p>
        <p v-else-if="apiOk">OK</p>
        <p v-else class="bad">ошибка</p>
      </div>

      <div class="panel">
        <h2>Аккаунты (демо)</h2>
        <p v-if="error" class="bad">{{ error }}</p>
        <pre v-if="accountsJson">{{ accountsJson }}</pre>
        <p v-else class="muted">Нажмите “Проверить /accounts”.</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { apiGet } from '../api/http'

const router = useRouter()
const auth = useAuth()

const apiOk = ref(null)
const loading = ref(false)
const error = ref(null)
const accountsJson = ref('')

async function loadAccounts() {
  loading.value = true
  error.value = null
  accountsJson.value = ''
  try {
    await apiGet('/health')
    apiOk.value = true
    const data = await apiGet('/accounts') // без реальной авторизации пока
    accountsJson.value = JSON.stringify(data, null, 2)
  } catch (e) {
    apiOk.value = false
    error.value = e?.message || 'Ошибка'
  } finally {
    loading.value = false
  }
}

function onLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.wrap {
  min-height: 100vh;
  background: #0b0f19;
  color: #e8eefc;
  padding: 18px;
}
.top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  background: #121a2a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 16px;
}
.title { font-size: 18px; font-weight: 700; }
.sub { opacity: 0.85; font-size: 13px; margin-top: 4px; }
.actions { display: flex; gap: 10px; }
button {
  padding: 10px 12px;
  border-radius: 10px;
  border: 0;
  cursor: pointer;
  font-weight: 600;
}
.ghost { background: rgba(255,255,255,0.08); color: #e8eefc; }
.danger { background: #ff4d4d; color: white; }
.main {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
}
.panel {
  background: #121a2a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 16px;
}
h2 { margin: 0 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: .06em; opacity: .9; }
pre {
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 12px;
  overflow: auto;
  max-height: 60vh;
}
.bad { color: #ff7b7b; }
.muted { opacity: 0.75; }
@media (max-width: 960px) {
  .main { grid-template-columns: 1fr; }
}
</style>