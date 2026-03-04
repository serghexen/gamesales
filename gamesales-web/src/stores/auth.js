import { reactive } from 'vue'
import { apiGet, apiPost } from '../api/http'

const AUTH_SECTIONS_KEY = 'auth_sections'
const readStoredSections = () => {
  // Читаем кеш прав из localStorage, чтобы после логина не показывать лишние вкладки до первого запроса.
  try {
    const raw = localStorage.getItem(AUTH_SECTIONS_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed
  } catch {
    return {}
  }
}

const state = reactive({
  token: localStorage.getItem('auth_token') || null,
  user: localStorage.getItem('auth_user') || null,
  role: localStorage.getItem('auth_role') || null,
  sections: readStoredSections(),
})
const DEAL_FILTERS_SESSION_KEY_PREFIX = 'gamesales:deal-filters:'

export function useAuth() {
  function saveSections(sectionsMap) {
    // Сохраняем карту доступов в state и localStorage единым путем.
    const safeMap = sectionsMap && typeof sectionsMap === 'object' && !Array.isArray(sectionsMap) ? sectionsMap : {}
    state.sections = safeMap
    localStorage.setItem(AUTH_SECTIONS_KEY, JSON.stringify(safeMap))
  }

  async function loadMySections() {
    // Загружаем права UI-секций для текущего пользователя сразу после авторизации.
    if (!state.token) {
      saveSections({})
      return {}
    }
    try {
      const res = await apiGet('/rbac/my-sections', { token: state.token })
      const map = {}
      const items = Array.isArray(res?.items) ? res.items : []
      for (const item of items) {
        const code = String(item?.section_code || '').trim()
        if (!code) continue
        map[code] = Boolean(item?.can_view)
      }
      saveSections(map)
      return map
    } catch {
      // Если RBAC недоступен, не ломаем вход и используем fallback по роли.
      saveSections({})
      return {}
    }
  }

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
    await loadMySections()
  }

  async function loadMe() {
    if (!state.token) return
    try {
      const res = await apiGet('/auth/me', { token: state.token })
      if (!res) return false
      state.user = res?.username || state.user
      state.role = res?.role || state.role
      if (state.user) localStorage.setItem('auth_user', state.user)
      if (state.role) localStorage.setItem('auth_role', state.role)
      await loadMySections()
      return true
    } catch (e) {
      const msg = String(e?.message || '').toLowerCase()
      if (e?.status === 401 || msg.includes('invalid token') || msg.includes('not authenticated')) {
        logout()
      }
      return false
    }
  }

  function logout() {
    // При logout чистим сессионные фильтры, чтобы новый вход начинался с чистого состояния.
    try {
      const keys = []
      for (let i = 0; i < sessionStorage.length; i += 1) {
        const key = sessionStorage.key(i)
        if (key && key.startsWith(DEAL_FILTERS_SESSION_KEY_PREFIX)) keys.push(key)
      }
      for (const key of keys) sessionStorage.removeItem(key)
    } catch {
      // Если sessionStorage недоступен, пропускаем очистку без падения.
    }
    state.token = null
    state.user = null
    state.role = null
    state.sections = {}
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_role')
    localStorage.removeItem(AUTH_SECTIONS_KEY)
  }

  function isAuthed() {
    return !!(state.token || localStorage.getItem('auth_token'))
  }

  return { state, login, loadMe, loadMySections, logout, isAuthed }
}
