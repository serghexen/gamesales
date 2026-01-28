import { reactive } from 'vue'
import { apiGet, apiPost } from '../api/http'

const state = reactive({
  token: localStorage.getItem('auth_token') || null,
  user: localStorage.getItem('auth_user') || null,
  role: localStorage.getItem('auth_role') || null,
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
    state.role = res?.user?.role || null

    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_user', state.user)
    localStorage.setItem('auth_role', state.role || '')
  }

  async function loadMe() {
    if (!state.token) return
    const res = await apiGet('/auth/me', { token: state.token }).catch(() => null)
    if (!res) return
    state.user = res?.username || state.user
    state.role = res?.role || state.role
    if (state.user) localStorage.setItem('auth_user', state.user)
    if (state.role) localStorage.setItem('auth_role', state.role)
  }

  function logout() {
    state.token = null
    state.user = null
    state.role = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_role')
  }

  function isAuthed() {
    return !!(state.token || localStorage.getItem('auth_token'))
  }

  return { state, login, loadMe, logout, isAuthed }
}
