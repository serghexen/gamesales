import { reactive } from 'vue'
import { apiGet } from '../api/http'

const state = reactive({
  token: localStorage.getItem('auth_token') || null,
  user: localStorage.getItem('auth_user') || null,
})

export function useAuth() {
  async function login({ username, password }) {
    // Пока заглушка: проверяем, что API живой, и пускаем.
    // Позже заменим на: apiPost('/auth/login', {username, password})
    await apiGet('/health').catch(() => {
      throw new Error('API недоступен (healthcheck не прошёл)')
    })

    // Условный "токен" для прототипа
    const token = `demo-${Date.now()}`
    state.token = token
    state.user = username || 'user'

    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_user', state.user)
  }

  function logout() {
    state.token = null
    state.user = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }

  function isAuthed() {
    return !!(state.token || localStorage.getItem('auth_token'))
  }

  return { state, login, logout, isAuthed }
}
