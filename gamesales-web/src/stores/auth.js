import { reactive } from 'vue'
import { apiGet, apiPost } from '../api/http'

const state = reactive({
  token: localStorage.getItem('auth_token') || null,
  user: localStorage.getItem('auth_user') || null,
})

export function useAuth() {
  async function login({ username, password }) {
    const res = await apiPost('/auth/login', { username, password }).catch(() => {
      throw new Error('API недоступен или неверные данные')
    })

    const token = res?.access_token
    if (!token) throw new Error('Не удалось получить токен')
    state.token = token
    state.user = res?.user?.username || username || 'user'

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
