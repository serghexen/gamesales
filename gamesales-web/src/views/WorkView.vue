<template>
  <div class="page">
    <div class="shell">
      <header class="top">
        <div class="brand">
          <div class="logo">GS</div>
          <div>
            <div class="title">Рабочая зона</div>
            <div class="sub">Пользователь: <b>{{ auth.state.user }}</b></div>
          </div>
        </div>

        <div class="actions">
          <button class="ghost" @click="checkApi" :disabled="loading">
            {{ loading ? 'Загрузка…' : 'Проверить API' }}
          </button>
          <button class="danger" @click="onLogout">Выйти</button>
        </div>
      </header>

      <section class="hero">
        <div>
          <h1 class="hero__title">Операции в реальном времени</h1>
          <p class="hero__text">
            Контролируй слоты, выдачи и платежи, а система сама покажет статус
            API и свежие данные по аккаунтам.
          </p>
        </div>
        <div class="hero__cards">
          <div class="mini">
            <div class="mini__label">API</div>
            <div class="mini__value" :class="{ bad: apiOk === false }">
              <span v-if="apiOk === null">не проверяли</span>
              <span v-else-if="apiOk">OK</span>
              <span v-else>ошибка</span>
            </div>
          </div>
          <div class="mini">
            <div class="mini__label">Запросы</div>
            <div class="mini__value">{{ loading ? '...' : '200/мин' }}</div>
          </div>
        </div>
      </section>

      <main class="main">
        <section class="panel panel--wide">
          <button class="panel__toggle" @click="showStatus = !showStatus">
            <div>
              <h2>Статус API</h2>
              <p class="muted">Быстрый healthcheck перед работой с данными.</p>
            </div>
            <span class="chev" :class="{ open: showStatus }">⌄</span>
          </button>
          <div v-if="showStatus" class="panel__body">
            <div class="status">
              <div class="dot" :class="{ ok: apiOk, bad: apiOk === false }"></div>
              <span>
                <span v-if="apiOk === null">не проверяли</span>
                <span v-else-if="apiOk">OK</span>
                <span v-else>ошибка</span>
              </span>
            </div>
            <button class="btn" @click="checkApi" :disabled="loading">
              {{ loading ? 'Проверяем…' : 'Проверить API' }}
            </button>
          </div>
        </section>

        <section class="panel panel--wide">
          <button class="panel__toggle" @click="showProfile = !showProfile">
            <div>
              <h2>Профиль</h2>
              <p class="muted">Сменить пароль текущего пользователя.</p>
            </div>
            <span class="chev" :class="{ open: showProfile }">⌄</span>
          </button>
          <div v-if="showProfile" class="panel__body">
            <div class="form">
              <label class="field">
                <span class="label">Текущий пароль</span>
                <input v-model="pwdForm.current" class="input" type="password" />
              </label>
              <label class="field">
                <span class="label">Новый пароль</span>
                <input v-model="pwdForm.next" class="input" type="password" />
              </label>
              <label class="field">
                <span class="label">Повторите пароль</span>
                <input v-model="pwdForm.next2" class="input" type="password" />
              </label>
              <p v-if="pwdError" class="bad">{{ pwdError }}</p>
              <p v-if="pwdOk" class="ok">Пароль обновлён</p>
              <button class="btn" @click="changePassword" :disabled="pwdLoading">
                {{ pwdLoading ? 'Сохраняем…' : 'Сменить пароль' }}
              </button>
            </div>
          </div>
        </section>

        <section class="panel panel--wide">
          <button class="panel__toggle" @click="showAccounts = !showAccounts">
            <div>
              <h2>Аккаунты</h2>
              <p class="muted">Создание аккаунтов и контроль слотов.</p>
            </div>
            <span class="chev" :class="{ open: showAccounts }">⌄</span>
          </button>
          <div v-if="showAccounts" class="panel__body">
            <div class="panel__head">
              <div></div>
              <button class="ghost" @click="loadAccounts" :disabled="accountsLoading">
                {{ accountsLoading ? 'Обновляем…' : 'Обновить' }}
              </button>
            </div>

            <div class="form form--stack">
              <label class="field">
                <span class="label">Логин (без домена)</span>
                <input v-model.trim="newAccount.login_name" class="input" placeholder="user" />
              </label>
              <label class="field">
                <span class="label">Домен</span>
                <select v-model="newAccount.domain_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="d in domains" :key="d.code" :value="d.code">
                    {{ d.name }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Платформа</span>
                <select v-model="newAccount.platform_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Регион</span>
                <select v-model="newAccount.region_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="r in regions" :key="r.code" :value="r.code">
                    {{ r.name }} ({{ r.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Всего слотов</span>
                <input v-model.number="newAccount.slot_capacity" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Зарезервировано</span>
                <input v-model.number="newAccount.slot_reserved" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Комментарий</span>
                <input v-model.trim="newAccount.notes" class="input" placeholder="заметки" />
              </label>
              <p v-if="accountsError" class="bad">{{ accountsError }}</p>
              <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
              <button class="btn" @click="createAccount" :disabled="accountsLoading">
                {{ accountsLoading ? 'Создаём…' : 'Добавить аккаунт' }}
              </button>
            </div>

            <table v-if="accounts.length" class="table">
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>Платформа</th>
                  <th>Регион</th>
                  <th>Статус</th>
                  <th>Свободно</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in accounts" :key="a.account_id">
                  <td>{{ a.login_full || '—' }}</td>
                  <td>{{ a.platform_code }}</td>
                  <td>{{ a.region_code || '—' }}</td>
                  <td>{{ a.status }}</td>
                  <td>{{ a.free_slots }}/{{ a.slot_capacity }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет аккаунтов.</p>
          </div>
        </section>

        <section class="panel panel--wide">
          <button class="panel__toggle" @click="showGames = !showGames">
            <div>
              <h2>Игры</h2>
              <p class="muted">Добавление игр в справочник.</p>
            </div>
            <span class="chev" :class="{ open: showGames }">⌄</span>
          </button>
          <div v-if="showGames" class="panel__body">
            <div class="form form--stack">
              <label class="field">
                <span class="label">Название</span>
                <input v-model.trim="newGame.title" class="input" placeholder="Например, GTA V" />
              </label>
              <label class="field">
                <span class="label">Платформа (опционально)</span>
                <select v-model="newGame.platform_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Регион (опционально)</span>
                <select v-model="newGame.region_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="r in regions" :key="r.code" :value="r.code">
                    {{ r.name }} ({{ r.code }})
                  </option>
                </select>
              </label>
              <p v-if="gameError" class="bad">{{ gameError }}</p>
              <p v-if="gameOk" class="ok">{{ gameOk }}</p>
              <button class="btn" @click="createGame" :disabled="gameLoading">
                {{ gameLoading ? 'Сохраняем…' : 'Добавить игру' }}
              </button>
            </div>
          </div>
        </section>

        <section v-if="isAdmin" class="panel panel--wide">
          <button class="panel__toggle" @click="showCatalogs = !showCatalogs">
            <div>
              <h2>Справочники</h2>
              <p class="muted">Домены и источники клиентов.</p>
            </div>
            <span class="chev" :class="{ open: showCatalogs }">⌄</span>
          </button>
          <div v-if="showCatalogs" class="panel__body">
            <div class="form form--stack">
              <label class="field">
                <span class="label">Новый домен</span>
                <input v-model.trim="newDomain" class="input" placeholder="example.com" />
              </label>
              <button class="btn" @click="createDomain" :disabled="catalogsLoading">
                {{ catalogsLoading ? 'Сохраняем…' : 'Добавить домен' }}
              </button>
            </div>

            <div class="form form--stack">
              <label class="field">
                <span class="label">Источник (код)</span>
                <input v-model.trim="newSource.code" class="input" placeholder="tg" />
              </label>
              <label class="field">
                <span class="label">Источник (название)</span>
                <input v-model.trim="newSource.name" class="input" placeholder="Telegram" />
              </label>
              <button class="btn" @click="createSource" :disabled="catalogsLoading">
                {{ catalogsLoading ? 'Сохраняем…' : 'Добавить источник' }}
              </button>
            </div>

            <p v-if="catalogsError" class="bad">{{ catalogsError }}</p>
            <p v-if="catalogsOk" class="ok">{{ catalogsOk }}</p>

            <div class="grid-2">
              <div>
                <h3>Домены</h3>
                <ul class="list" v-if="domains.length">
                  <li v-for="d in domains" :key="d.code">{{ d.name }}</li>
                </ul>
                <p v-else class="muted">Пока нет доменов.</p>
              </div>
              <div>
                <h3>Источники</h3>
                <ul class="list" v-if="sources.length">
                  <li v-for="s in sources" :key="s.code">{{ s.code }} — {{ s.name }}</li>
                </ul>
                <p v-else class="muted">Пока нет источников.</p>
              </div>
            </div>
          </div>
        </section>

        <section v-if="isAdmin" class="panel panel--wide">
          <button class="panel__toggle" @click="showUsers = !showUsers">
            <div>
              <h2>Пользователи</h2>
              <p class="muted">Создание менеджеров и управление доступом.</p>
            </div>
            <span class="chev" :class="{ open: showUsers }">⌄</span>
          </button>
          <div v-if="showUsers" class="panel__body">
            <div class="panel__head">
              <div></div>
              <button class="ghost" @click="loadUsers" :disabled="userLoading">
                {{ userLoading ? 'Обновляем…' : 'Обновить' }}
              </button>
            </div>

            <div class="form form--stack">
              <label class="field">
                <span class="label">Логин</span>
                <input v-model.trim="newUser.username" class="input" placeholder="manager1" />
              </label>
              <label class="field">
                <span class="label">Пароль</span>
                <input v-model="newUser.password" class="input" type="password" />
              </label>
              <label class="field">
                <span class="label">Роль</span>
                <select v-model="newUser.role_code" class="input input--select">
                  <option v-for="r in roles" :key="r.code" :value="r.code">{{ r.name }}</option>
                </select>
              </label>
              <button class="btn" @click="createUser" :disabled="userLoading">
                {{ userLoading ? 'Создаём…' : 'Создать' }}
              </button>
            </div>

            <p v-if="userError" class="bad">{{ userError }}</p>
            <p v-if="userOk" class="ok">{{ userOk }}</p>
            <table v-if="users.length" class="table">
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>Роль</th>
                  <th>Создан</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in users" :key="u.username">
                  <td>{{ u.username }}</td>
                  <td>{{ u.role }}</td>
                  <td>{{ new Date(u.created_at).toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет пользователей.</p>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { apiGet, apiPost } from '../api/http'

const router = useRouter()
const auth = useAuth()

const apiOk = ref(null)
const loading = ref(false)
const error = ref(null)
const accounts = ref([])
const accountsError = ref(null)
const accountsOk = ref(null)
const accountsLoading = ref(false)
const users = ref([])
const roles = ref([])
const platforms = ref([])
const regions = ref([])
const domains = ref([])
const sources = ref([])
const catalogsError = ref(null)
const catalogsOk = ref(null)
const catalogsLoading = ref(false)
const userError = ref(null)
const userOk = ref(null)
const userLoading = ref(false)
const gameError = ref(null)
const gameOk = ref(null)
const gameLoading = ref(false)
const pwdError = ref(null)
const pwdOk = ref(false)
const pwdLoading = ref(false)

const isAdmin = computed(() => auth.state.role === 'admin')

const newUser = reactive({
  username: '',
  password: '',
  role_code: 'manager',
})

const pwdForm = reactive({
  current: '',
  next: '',
  next2: '',
})

const showStatus = ref(true)
const showProfile = ref(false)
const showAccounts = ref(true)
const showUsers = ref(true)
const showGames = ref(false)
const showCatalogs = ref(false)

const newGame = reactive({
  title: '',
  platform_code: '',
  region_code: '',
})

const newDomain = ref('')
const newSource = reactive({
  code: '',
  name: '',
})

const newAccount = reactive({
  login_name: '',
  domain_code: '',
  platform_code: '',
  region_code: '',
  slot_capacity: 1,
  slot_reserved: 0,
  notes: '',
})

async function checkApi() {
  loading.value = true
  error.value = null
  try {
    await apiGet('/health', { token: auth.state.token })
    apiOk.value = true
  } catch (e) {
    apiOk.value = false
    error.value = e?.message || 'Ошибка'
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  if (!isAdmin.value) return
  userLoading.value = true
  userError.value = null
  try {
    const rolesData = await apiGet('/user-roles', { token: auth.state.token })
    roles.value = rolesData || []
    const data = await apiGet('/users', { token: auth.state.token })
    users.value = data || []
  } catch (e) {
    userError.value = e?.message || 'Ошибка'
  } finally {
    userLoading.value = false
  }
}

async function loadCatalogs() {
  try {
    const [p, r] = await Promise.all([
      apiGet('/platforms', { token: auth.state.token }),
      apiGet('/regions', { token: auth.state.token }),
    ])
    platforms.value = p || []
    regions.value = r || []
  } catch {
    platforms.value = []
    regions.value = []
  }
}

async function loadDomains() {
  try {
    const d = await apiGet('/domains', { token: auth.state.token })
    domains.value = d || []
  } catch {
    domains.value = []
  }
}

async function loadSources() {
  try {
    const s = await apiGet('/sources', { token: auth.state.token })
    sources.value = s || []
  } catch {
    sources.value = []
  }
}

async function loadAccounts() {
  accountsLoading.value = true
  accountsError.value = null
  accountsOk.value = null
  try {
    const data = await apiGet('/accounts', { token: auth.state.token })
    accounts.value = data || []
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
  } finally {
    accountsLoading.value = false
  }
}

async function createAccount() {
  accountsError.value = null
  accountsOk.value = null
  if (!newAccount.login_name || !newAccount.domain_code || !newAccount.platform_code) {
    accountsError.value = 'Укажите логин, домен и платформу'
    return
  }
  accountsLoading.value = true
  try {
    await apiPost(
      '/accounts',
      {
        platform_code: newAccount.platform_code,
        region_code: newAccount.region_code || null,
        login_name: newAccount.login_name || null,
        domain_code: newAccount.domain_code || null,
        slot_capacity: newAccount.slot_capacity,
        slot_reserved: newAccount.slot_reserved,
        notes: newAccount.notes || null,
      },
      { token: auth.state.token }
    )
    accountsOk.value = `Аккаунт ${newAccount.login_name}@${newAccount.domain_code} создан`
    newAccount.login_name = ''
    newAccount.domain_code = ''
    newAccount.platform_code = ''
    newAccount.region_code = ''
    newAccount.slot_capacity = 1
    newAccount.slot_reserved = 0
    newAccount.notes = ''
    await loadAccounts()
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
  } finally {
    accountsLoading.value = false
  }
}

async function createUser() {
  userError.value = null
  userOk.value = null
  if (!newUser.username || !newUser.password) {
    userError.value = 'Заполните логин и пароль'
    return
  }
  userLoading.value = true
  try {
    await apiPost('/users', newUser, { token: auth.state.token })
    userOk.value = `Пользователь ${newUser.username} создан`
    newUser.username = ''
    newUser.password = ''
    await loadUsers()
  } catch (e) {
    userError.value = e?.message || 'Ошибка'
  } finally {
    userLoading.value = false
  }
}

async function changePassword() {
  pwdError.value = null
  pwdOk.value = false
  if (!pwdForm.current || !pwdForm.next || !pwdForm.next2) {
    pwdError.value = 'Заполните все поля'
    return
  }
  if (pwdForm.next !== pwdForm.next2) {
    pwdError.value = 'Пароли не совпадают'
    return
  }
  pwdLoading.value = true
  try {
    await apiPost(
      '/auth/change-password',
      { current_password: pwdForm.current, new_password: pwdForm.next },
      { token: auth.state.token }
    )
    pwdOk.value = true
    pwdForm.current = ''
    pwdForm.next = ''
    pwdForm.next2 = ''
  } catch (e) {
    pwdError.value = e?.message || 'Ошибка'
  } finally {
    pwdLoading.value = false
  }
}

async function createGame() {
  gameError.value = null
  gameOk.value = null
  if (!newGame.title) {
    gameError.value = 'Укажите название игры'
    return
  }
  gameLoading.value = true
  try {
    await apiPost(
      '/games',
      {
        title: newGame.title,
        platform_code: newGame.platform_code || null,
        region_code: newGame.region_code || null,
      },
      { token: auth.state.token }
    )
    gameOk.value = `Игра “${newGame.title}” добавлена`
    newGame.title = ''
    newGame.platform_code = ''
    newGame.region_code = ''
  } catch (e) {
    gameError.value = e?.message || 'Ошибка'
  } finally {
    gameLoading.value = false
  }
}

async function createDomain() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newDomain.value) {
    catalogsError.value = 'Введите домен'
    return
  }
  catalogsLoading.value = true
  try {
    await apiPost('/domains', { name: newDomain.value }, { token: auth.state.token })
    catalogsOk.value = `Домен ${newDomain.value} добавлен`
    newDomain.value = ''
    await loadDomains()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function createSource() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newSource.code || !newSource.name) {
    catalogsError.value = 'Введите код и название источника'
    return
  }
  catalogsLoading.value = true
  try {
    await apiPost('/sources', newSource, { token: auth.state.token })
    catalogsOk.value = `Источник ${newSource.code} добавлен`
    newSource.code = ''
    newSource.name = ''
    await loadSources()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

function onLogout() {
  auth.logout()
  router.replace('/login')
}

onMounted(async () => {
  await auth.loadMe()
  if (isAdmin.value) {
    await loadUsers()
  }
})

watch(showGames, async (open) => {
  if (!open) return
  if (!platforms.value.length || !regions.value.length) {
    await loadCatalogs()
  }
})

watch(showAccounts, async (open) => {
  if (!open) return
  if (!platforms.value.length || !regions.value.length) {
    await loadCatalogs()
  }
  if (!domains.value.length) {
    await loadDomains()
  }
  await loadAccounts()
})

watch(showCatalogs, async (open) => {
  if (!open) return
  await Promise.all([loadDomains(), loadSources()])
})
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

.page {
  min-height: 100svh;
  padding:
    max(18px, env(safe-area-inset-top))
    max(18px, env(safe-area-inset-right))
    max(18px, env(safe-area-inset-bottom))
    max(18px, env(safe-area-inset-left));
  background:
    radial-gradient(900px 520px at 12% 10%, rgba(62, 232, 181, 0.16), transparent 70%),
    radial-gradient(900px 520px at 88% 12%, rgba(247, 185, 85, 0.18), transparent 70%),
    linear-gradient(135deg, var(--bg-1), var(--bg-2) 55%, var(--bg-3));
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
}

.shell {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px 18px;
  backdrop-filter: blur(12px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
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
  font-size: 20px;
  font-weight: 700;
}

.sub {
  opacity: 0.8;
  font-size: 13px;
  margin-top: 4px;
}

.actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 10px 14px;
  border-radius: 12px;
  border: 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}

.ghost {
  background: rgba(255, 255, 255, 0.08);
  color: #e8eefc;
}

.danger {
  background: #ff6b6b;
  color: white;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
}

.hero__title {
  margin: 0 0 8px;
  font-family: 'Fraunces', serif;
  font-size: clamp(22px, 4.2vw, 32px);
}

.hero__text {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.hero__cards {
  display: grid;
  gap: 12px;
  min-width: 200px;
}

.mini {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(10, 16, 32, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mini__label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--muted);
}

.mini__value {
  margin-top: 6px;
  font-weight: 700;
  font-size: 18px;
}

.main {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.panel {
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(10px);
}

.panel--wide {
  min-height: 0;
  grid-column: auto;
}

.panel__toggle {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  color: var(--ink);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}

.panel__body {
  margin-top: 10px;
}

.chev {
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: transform 0.2s ease;
}

.chev.open {
  transform: rotate(180deg);
}

.panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

h2 {
  margin: 0 0 8px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.85;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 12px;
}

.list {
  margin: 0;
  padding-left: 16px;
  color: var(--ink);
}

h3 {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.7;
}

.form {
  display: grid;
  gap: 10px;
}

.form--stack {
  grid-template-columns: 1fr;
  margin-bottom: 10px;
}

.field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.label {
  font-size: 12px;
  color: var(--muted);
}

.input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(8, 12, 24, 0.6);
  color: var(--ink);
  outline: none;
  font-size: 14px;
}

.form--inline .btn {
  width: 100%;
  height: 44px;
}

.input--select {
  appearance: none;
}

.ok {
  color: #3ee8b5;
  font-size: 13px;
}

table.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 13px;
}

.table th,
.table td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 16px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #9aa4b8;
}

.dot.ok {
  background: #3ee8b5;
}

.dot.bad {
  background: #ff9aa2;
}

.btn {
  height: 44px;
  border-radius: 12px;
  border: 0;
  background: linear-gradient(135deg, #3ee8b5, #7df0c6);
  color: #0b0f19;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
}

pre {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px;
  overflow: auto;
  max-height: 60vh;
}

.bad {
  color: #ff9aa2;
}

.muted {
  opacity: 0.7;
}

@media (max-width: 980px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .main {
    grid-template-columns: 1fr;
  }

  .panel--wide {
    grid-column: span 1;
  }
}
</style>
