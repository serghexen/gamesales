<template>
  <div class="page">
    <div class="shell">
      <div class="card" role="region" aria-label="Авторизация">
        <div class="card__head">
          <div class="logo">GS</div>
          <div>
            <h2 class="title">Вход в панель</h2>
            <p class="subtitle">Введите логин и пароль для продолжения</p>
          </div>
        </div>

        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="label">Логин</span>
            <input
              v-model.trim="username"
              class="input"
              autocomplete="username"
              inputmode="text"
              required
            />
          </label>

          <label class="field">
            <span class="label">Пароль</span>
            <input
              v-model="password"
              class="input"
              type="password"
              autocomplete="current-password"
              required
            />
          </label>

          <p v-if="error" class="error" role="alert">{{ error }}</p>

          <button class="btn" type="submit" :disabled="loading">
            <span v-if="loading">Входим…</span>
            <span v-else>Войти</span>
          </button>
        </form>
      </div>
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,650&display=swap');

:root {
  --bg-1: #0c1024;
  --bg-2: #151b35;
  --bg-3: #0f2431;
  --accent: #3ee8b5;
  --accent-2: #f7b955;
  --ink: #eef2ff;
  --muted: rgba(238, 242, 255, 0.7);
  --card: rgba(10, 16, 32, 0.6);
  --stroke: rgba(255, 255, 255, 0.12);
}

/* Mobile-first */
.page {
  min-height: 100svh;
  display: grid;
  place-items: center;
  padding:
    max(18px, env(safe-area-inset-top))
    max(18px, env(safe-area-inset-right))
    max(18px, env(safe-area-inset-bottom))
    max(18px, env(safe-area-inset-left));
  background:
    radial-gradient(800px 420px at 10% 10%, rgba(62, 232, 181, 0.15), transparent 70%),
    radial-gradient(900px 520px at 90% 10%, rgba(247, 185, 85, 0.18), transparent 70%),
    linear-gradient(135deg, var(--bg-1), var(--bg-2) 55%, var(--bg-3));
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
  position: relative;
  overflow: hidden;
}

.page::before,
.page::after {
  content: '';
  position: absolute;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.35;
  z-index: 0;
}

.page::before {
  background: #3ee8b5;
  top: -120px;
  left: -120px;
}

.page::after {
  background: #f7b955;
  bottom: -160px;
  right: -120px;
}

.shell {
  width: min(980px, 100%);
  display: grid;
  gap: 20px;
  position: relative;
  z-index: 1;
}

.card {
  width: 100%;
  max-width: 460px;
  border-radius: 20px;
  background: var(--card);
  border: 1px solid var(--stroke);
  padding: clamp(18px, 3.5vw, 28px);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
  animation: rise 0.7s ease 0.1s both;
}

.card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.logo {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(62, 232, 181, 0.3), rgba(247, 185, 85, 0.3));
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-weight: 700;
}

.title {
  margin: 0;
  font-size: clamp(20px, 4.6vw, 26px);
  line-height: 1.15;
}

.subtitle {
  margin: 6px 0 0;
  opacity: 0.8;
  font-size: clamp(12px, 3.4vw, 14px);
}

.form {
  display: grid;
  gap: 14px;
}

.field {
  display: grid;
  gap: 6px;
  animation: fadeIn 0.6s ease both;
}

.field:nth-of-type(1) {
  animation-delay: 0.05s;
}

.field:nth-of-type(2) {
  animation-delay: 0.12s;
}

.label {
  font-size: clamp(12px, 3.4vw, 13px);
  color: var(--muted);
}

.input {
  width: 100%;
  height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(8, 12, 24, 0.6);
  color: var(--ink);
  outline: none;
  font-size: 16px;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input::placeholder {
  color: rgba(238, 242, 255, 0.45);
}

.input:focus {
  border-color: rgba(62, 232, 181, 0.75);
  box-shadow: 0 0 0 3px rgba(62, 232, 181, 0.2);
}

.error {
  margin: 2px 0 0;
  color: #ff9aa2;
  font-size: 13px;
}

.btn {
  margin-top: 6px;
  height: 48px;
  border-radius: 14px;
  border: 0;
  background: linear-gradient(135deg, #3ee8b5, #7df0c6);
  color: #0b0f19;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.2s ease;
  box-shadow: 0 12px 22px rgba(62, 232, 181, 0.18);
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(62, 232, 181, 0.25);
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}


@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (min-width: 900px) {
  .shell {
    align-items: center;
    justify-items: center;
  }

  .card {
    border-radius: 22px;
  }
}
</style>
