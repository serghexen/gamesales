<template>
  <div class="page">
    <div class="card" role="region" aria-label="Авторизация">
      <h1 class="title">Вход</h1>
      <p class="subtitle">Введите логин и пароль</p>

      <form class="form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="label">Логин</span>
          <input
            v-model.trim="username"
            class="input"
            autocomplete="username"
            inputmode="text"
            placeholder="например: serghey"
          />
        </label>

        <label class="field">
          <span class="label">Пароль</span>
          <input
            v-model="password"
            class="input"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
          />
        </label>

        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <button class="btn" type="submit" :disabled="loading">
          <span v-if="loading">Входим…</span>
          <span v-else>Войти</span>
        </button>
      </form>

      <p class="hint">
        Прототип: вход проходит, если API отвечает на <code>/health</code>.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'

const username = ref('')
const password = ref('')
const error = ref(null)
const loading = ref(false)

const route = useRoute()
const router = useRouter()
const { login } = useAuth()

async function onSubmit() {
  error.value = null
  loading.value = true
  try {
    await login({ username: username.value, password: password.value })
    const next = route.query.next || '/'
    router.replace(String(next))
  } catch (e) {
    error.value = e?.message || 'Ошибка входа'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Mobile-first */
.page {
  min-height: 100svh; /* лучше на мобилках */
  display: grid;
  place-items: center;
  padding:
    max(16px, env(safe-area-inset-top))
    max(16px, env(safe-area-inset-right))
    max(16px, env(safe-area-inset-bottom))
    max(16px, env(safe-area-inset-left));
  background: #0b0f19;
}

.card {
  width: 100%;
  max-width: 440px;          /* на десктопе карточка не разъедется */
  border-radius: 16px;
  background: #121a2a;
  border: 1px solid rgba(255, 255, 255, 0.10);
  padding: clamp(16px, 3.5vw, 24px);
  color: #e8eefc;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
}

.title {
  margin: 0;
  font-size: clamp(20px, 5.2vw, 26px);
  line-height: 1.15;
}

.subtitle {
  margin: 8px 0 16px;
  opacity: 0.85;
  font-size: clamp(12px, 3.6vw, 14px);
}

.form {
  display: grid;
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
}

.label {
  font-size: clamp(12px, 3.4vw, 13px);
  opacity: 0.9;
}

.input {
  width: 100%;
  height: 46px;             /* удобно пальцем */
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.22);
  color: #e8eefc;
  outline: none;
  font-size: 16px;          /* важно: iOS перестаёт зумить input */
}

.input:focus {
  border-color: rgba(43, 108, 255, 0.65);
  box-shadow: 0 0 0 3px rgba(43, 108, 255, 0.18);
}

.error {
  margin: 2px 0 0;
  color: #ff7b7b;
  font-size: 13px;
}

.btn {
  margin-top: 4px;
  height: 48px;             /* удобно пальцем */
  border-radius: 12px;
  border: 0;
  background: #2b6cff;
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.hint {
  margin: 14px 0 0;
  opacity: 0.75;
  font-size: 12px;
  line-height: 1.35;
  word-break: break-word;
}

code {
  opacity: 0.95;
}

/* Чуть шире на больших экранах — больше воздуха */
@media (min-width: 900px) {
  .card {
    border-radius: 18px;
  }
}
</style>