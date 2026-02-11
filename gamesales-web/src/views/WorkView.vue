<template>
  <div class="work-page page">
    <div class="shell">
      <WorkTopBar :ctx="topBarCtx" />

      <WorkDashboardHero v-if="showDashboard && activeTab === 'dashboard'" :ctx="dashboardSectionCtx" />

      <main class="main">
        <WorkDashboardPanel
          v-if="showDashboard && activeTab === 'dashboard'"
          :ctx="dashboardSectionCtx"
        />

        <WorkProfileSection
          v-if="activeTab === 'profile'"
          :ctx="profileSectionCtx"
        />

        <WorkAccountsSection
          v-if="activeTab === 'accounts'"
          :ctx="accountsSectionCtx"
        />


        <WorkGamesSection
          v-if="activeTab === 'games'"
          :ctx="gamesSectionCtx"
        />


        <WorkTelegramSection
          v-if="activeTab === 'telegram'"
          :ctx="telegramSectionCtx"
        />


        <WorkDealsArea
          v-if="activeTab === 'deals'"
          :ctx="dealsAreaCtx"
        />

        <WorkCatalogsSection
          v-if="isAdmin && activeTab === 'catalogs'"
          :ctx="catalogsSectionCtx"
        />

        <WorkAnalyticsSection
          v-if="activeTab === 'analytics'"
          :ctx="analyticsSectionCtx"
        />

        <WorkUsersSection
          v-if="isAdmin && activeTab === 'users'"
          :ctx="usersSectionCtx"
        />
      </main>
    </div>

    <!-- Единый confirm в стиле интерфейса для несохраненных изменений -->
    <teleport to="body">
      <div v-if="unsavedConfirm.open" class="work-page work-modal-root modal-backdrop unsaved-confirm" @click.self="answerUnsavedConfirm(false)">
        <div class="modal modal--auto unsaved-confirm__modal">
          <div class="panel__head panel__head--tight unsaved-confirm__head">
            <h3 class="unsaved-confirm__title">Несохраненные изменения</h3>
          </div>
          <div class="modal__body">
            <p class="muted unsaved-confirm__text">{{ unsavedConfirm.message }}</p>
            <div class="toolbar-actions unsaved-confirm__actions">
              <button class="ghost" type="button" @click="answerUnsavedConfirm(false)">Остаться</button>
              <button class="btn btn--danger" type="button" @click="answerUnsavedConfirm(true)">Закрыть без сохранения</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="dealWarning.open" class="work-page work-modal-root modal-backdrop unsaved-confirm deal-warning" @click.self="closeDealWarning">
        <div class="modal modal--auto unsaved-confirm__modal deal-warning__modal">
          <div class="panel__head panel__head--tight unsaved-confirm__head deal-warning__head">
            <h3 class="unsaved-confirm__title deal-warning__title">{{ dealWarning.title }}</h3>
          </div>
          <div class="modal__body deal-warning__body">
            <p class="muted unsaved-confirm__text deal-warning__text">{{ dealWarning.message }}</p>
            <div class="toolbar-actions unsaved-confirm__actions deal-warning__actions">
              <button class="btn btn--danger deal-warning__btn" type="button" @click="closeDealWarning">Ок</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, proxyRefs, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../stores/auth'
import { API_BASE, apiGet, apiPost, apiDelete, apiPut, apiPostForm, apiGetFile, apiPostFormWithProgress } from '../api/http'
import {
  TAB_KEYS,
  TELEGRAM_DIALOGS_POLL_MS,
  TELEGRAM_MESSAGES_POLL_MS,
  TELEGRAM_DIALOGS_POLL_ERROR_MS,
  TELEGRAM_MESSAGES_POLL_ERROR_MS,
  GAME_IMPORT_JOB_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  GAME_LOGO_CACHE_KEY,
  GAME_LOGO_CACHE_TTL_MS,
  dealTypeOptions,
  dealFlowStatusOptions,
  minDate,
  maxPrice,
  maxGameTitleLength,
  getMaxDate,
  clampPrice,
  formatPrice,
  formatPercent,
  toUtcDateTime,
  mapApiError,
} from './work/domainUtils'
import { useAnalytics } from './work/useAnalytics'
import {
  createTelegramState,
  formatTelegramSender,
  formatTelegramMessageHtml,
  showTelegramChannelLabel as showTelegramChannelLabelForList,
  isTelegramImage,
  isTelegramVideo,
} from './work/telegramUtils'
import { createNewAccountState, createEditAccountState, createAccountFiltersState, resolveAccountSort } from './work/accountUtils'
import { createNewDealState, createEditDealState, createDealFiltersState, resolveDealFlowStatusFilter } from './work/dealsUtils'
import { useDeals } from './work/useDeals'
import { useDealsActions } from './work/useDealsActions'
import { useDealsFlow } from './work/useDealsFlow'
import { useTelegram } from './work/useTelegram'
import { useImportFlow } from './work/useImportFlow'
import { useCatalogs } from './work/useCatalogs'
import { useAccountsFlow } from './work/useAccountsFlow'
import { useGamesFlow } from './work/useGamesFlow'
import { useGamesViewState } from './work/useGamesViewState'
import { useAccountsViewState } from './work/useAccountsViewState'
import { useAccountsDerivedState } from './work/useAccountsDerivedState'
import { useCatalogsViewState } from './work/useCatalogsViewState'
import { useDealsViewState } from './work/useDealsViewState'
import { useWorkFormatters } from './work/useWorkFormatters'
import { useFilterPopouts } from './work/useFilterPopouts'
import { useDealsWatchers } from './work/useDealsWatchers'
import { useDealsRealtime } from './work/useDealsRealtime'
import { useActiveTabWatcher } from './work/useActiveTabWatcher'
import { useWorkLifecycleWatchers } from './work/useWorkLifecycleWatchers'
import { useWorkLifecycle } from './work/useWorkLifecycle'
import { useModalDrag } from './work/useModalDrag'
import { useSlotHelpers } from './work/useSlotHelpers'
import { useWorkFilters } from './work/useWorkFilters'
import { useDealModalFlow } from './work/useDealModalFlow'
import { useUserProfileFlow } from './work/useUserProfileFlow'
import { useWorkActions } from './work/useWorkActions'
import { useWorkUiHelpers } from './work/useWorkUiHelpers'
import { useGameLogoCache } from './work/useGameLogoCache'
import { createDeferredCall } from './work/deferredCall'
import { useWorkSectionContexts } from './work/useWorkSectionContexts'
import WorkDashboardHero from './work/sections/WorkDashboardHero.vue'
import WorkDashboardPanel from './work/sections/WorkDashboardPanel.vue'
import WorkAnalyticsSection from './work/sections/WorkAnalyticsSection.vue'
import WorkProfileSection from './work/sections/WorkProfileSection.vue'
import WorkUsersSection from './work/sections/WorkUsersSection.vue'
import WorkAccountsSection from './work/sections/WorkAccountsSection.vue'
import WorkGamesSection from './work/sections/WorkGamesSection.vue'
import WorkDealsArea from './work/sections/WorkDealsArea.vue'
import WorkCatalogsSection from './work/sections/WorkCatalogsSection.vue'
import WorkTelegramSection from './work/sections/WorkTelegramSection.vue'
import WorkTopBar from './work/sections/WorkTopBar.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuth()
const asCtx = (ctx) => proxyRefs(ctx)
const createBooleanFlag = (initial = false) => {
  const state = ref(Boolean(initial))
  return computed({
    get: () => state.value,
    set: (next) => {
      state.value = Boolean(next)
    },
  })
}

// "Ленивые" мосты: позволяют безопасно вызывать функции после инициализации модулей.
const closeDealModalDeferred = createDeferredCall('closeDealModal')
const loadAccountsAllDeferred = createDeferredCall('loadAccountsAll')
const loadAccountSlotAssignmentsDeferred = createDeferredCall('loadAccountSlotAssignments')
const loadGameSlotAssignmentsDeferred = createDeferredCall('loadGameSlotAssignments')

const closeDealModal = () => closeDealModalDeferred.call()
const loadAccountsAll = (...args) => loadAccountsAllDeferred.call(...args)
const loadAccountSlotAssignments = (...args) => loadAccountSlotAssignmentsDeferred.call(...args)
const loadGameSlotAssignments = (...args) => loadGameSlotAssignmentsDeferred.call(...args)
const suppressUnsavedConfirm = ref(false)
const unsavedConfirm = reactive({
  open: false,
  message: '',
  resolver: null,
})
const dealWarning = reactive({
  open: false,
  title: 'Предупреждение',
  message: '',
})

function requestUnsavedConfirm(message) {
  // Показывает кастомное модальное подтверждение вместо системного confirm.
  return new Promise((resolve) => {
    unsavedConfirm.open = true
    unsavedConfirm.message = message || 'Есть несохраненные изменения. Закрыть без сохранения?'
    unsavedConfirm.resolver = resolve
  })
}

function answerUnsavedConfirm(accepted) {
  const resolve = unsavedConfirm.resolver
  unsavedConfirm.open = false
  unsavedConfirm.message = ''
  unsavedConfirm.resolver = null
  if (typeof resolve === 'function') resolve(Boolean(accepted))
}

function showDealWarning(message) {
  // Открываем компактное предупреждение в фирменном модальном стиле.
  dealWarning.open = true
  dealWarning.title = 'Предупреждение'
  dealWarning.message = message || 'Операция недоступна'
}

function closeDealWarning() {
  dealWarning.open = false
  dealWarning.title = 'Предупреждение'
  dealWarning.message = ''
}

// Основное состояние экрана: списки, флаги загрузки, ошибки, успехи.
const apiOk = ref(null)
const loading = ref(false)
const error = ref(null)
const accounts = ref([])
const accountsAll = ref([])
const accountsTotal = ref(0)
const accountsPage = ref(1)
const accountsPageInput = ref(1)
const accountsPageSize = ref(20)
const accountSecrets = ref({})
const accountsError = ref(null)
const accountsOk = ref(null)
const accountsLoading = ref(false)
const accountSaving = createBooleanFlag(false)
const accountDeals = ref([])
const accountDealsLoading = ref(false)
const accountDealsError = ref(null)
const accountSlotAssignments = ref([])
const accountSlotAssignmentsSort = ref({ key: 'slot', dir: 'asc' })
const accountSlotAssignmentsLoading = ref(false)
const accountSlotAssignmentsError = ref(null)
const accountSlotReleaseLoading = ref(false)
const dealSaving = createBooleanFlag(false)
const gameSaving = createBooleanFlag(false)
const catalogSaving = createBooleanFlag(false)
const tgMessagesList = ref(null)
const users = ref([])
const roles = ref([])
const responsibleUsers = ref([])
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
const showUserForm = ref(false)
const gameError = ref(null)
const gameOk = ref(null)
const gameLoading = ref(false)
const gameAccounts = ref([])
const gameAccountsLoading = ref(false)
const gameAccountsError = ref(null)
const gameSlotAssignments = ref([])
const gameSlotAssignmentsLoading = ref(false)
const gameSlotAssignmentsError = ref(null)
const dealGameAssignmentsNew = ref([])
const dealGameAssignmentsEdit = ref([])
const dealGameAssignmentsLoadingNew = ref(false)
const dealGameAssignmentsLoadingEdit = ref(false)
const gameAccountsSort = ref({ key: 'free_slots', dir: 'desc' })
const gameAccountsPage = ref(1)
const gameAccountsPageSize = 15
const dealError = ref(null)
const dealOk = ref(null)
const dealLoading = ref(false)
const dealBackgroundSync = ref(false)
const dealCompletingId = ref(null)
const dealInitLock = ref(false)
const pwdError = ref(null)
const pwdOk = ref(false)
const pwdLoading = ref(false)
const showPwdForm = ref(false)
const accountEditMode = ref('view')
const dealEditMode = ref('view')
const gameEditMode = ref('view')
const setAccountEditMode = (mode) => {
  accountEditMode.value = mode
}
const setEditAccountGameSearch = (value) => {
  editAccountGameSearch.value = value
}
const setAccountGameSearch = (value) => {
  accountGameSearch.value = value
}
const setSlotImportLimit = (value) => {
  slotImportLimit.value = value
}
const setDealShowCompleted = (value) => {
  dealShowCompleted.value = value
}
const setActiveDealFilter = (value) => {
  activeDealFilter.value = value
}
const dealsBootstrapped = ref(false)
const dealsRealtimeStatus = ref('offline')

// Загружает кандидатов для поля "Ответственный" в сделках.
async function loadResponsibleUsers() {
  try {
    const data = await apiGet('/users', { token: auth.state.token })
    responsibleUsers.value = Array.isArray(data) ? data : []
  } catch {
    // Если список не загрузился, оставляем только локальный fallback по текущему пользователю.
    responsibleUsers.value = []
  }
}

const canViewPrivilegedResponsible = computed(() => {
  const role = String(auth.state.role || '').trim().toLowerCase()
  const me = String(auth.state.user || '').trim().toLowerCase()
  return role === 'admin' || role === 'owner' || me === 'admin' || me === 'owner'
})

const currentUserResponsibleName = computed(() => {
  const me = String(auth.state.user || '').trim().toLowerCase()
  if (!me) return ''
  const row = responsibleUsers.value.find((user) => String(user?.username || '').trim().toLowerCase() === me)
  return String(row?.name || '').trim()
})

const topBarRoleName = computed(() => {
  // Показывает роль рядом с кнопкой профиля в человекочитаемом виде.
  const roleCode = String(auth.state.role || '').trim().toLowerCase()
  if (!roleCode) return ''
  const roleRow = roles.value.find((role) => String(role?.code || '').trim().toLowerCase() === roleCode)
  const roleName = String(roleRow?.name || '').trim()
  if (roleName) return roleName
  const fallbackNames = {
    admin: 'Администратор',
    owner: 'Владелец',
    manager: 'Менеджер',
    operator: 'Оператор',
  }
  return String(fallbackNames[roleCode] || roleCode).trim()
})

const defaultDealsResponsibleFilter = computed(() => {
  // Для manager/operator в сделках по умолчанию ставим фильтр по себе.
  const role = String(auth.state.role || '').trim().toLowerCase()
  if (role !== 'manager' && role !== 'operator') return ''
  // Фильтруем строго по name, без fallback на username.
  return String(currentUserResponsibleName.value || '').trim()
})

const responsibleUserOptions = computed(() => {
  // Строит список ответственных и скрывает admin/owner для остальных пользователей.
  const hiddenRoles = new Set(['admin', 'owner'])
  const seen = new Set()
  const options = []

  const pushName = (rawName, roleCode = '') => {
    const name = String(rawName || '').trim()
    if (!name) return
    const role = String(roleCode || '').trim().toLowerCase()
    const key = name.toLowerCase()
    if (seen.has(key)) return
    if (!canViewPrivilegedResponsible.value && hiddenRoles.has(role)) return
    seen.add(key)
    options.push(name)
  }

  for (const user of responsibleUsers.value) {
    pushName(user?.name, user?.role)
  }
  pushName(currentUserResponsibleName.value)
  return options
})
const catalogsLoadedOnce = ref(false)
const domainsLoadedOnce = ref(false)
const sourcesLoadedOnce = ref(false)
const slotTypesLoadedOnce = ref(false)
const accountsAllLoadedOnce = ref(false)
const gamesAllLoadedOnce = ref(false)

const {
  getAccountLabelById,
  getRegionLabel,
  getDomainLabel,
  getAccountStatusLabel,
  getSourceLabelById,
  getFlowStatusLabel,
  getDealGameTitleDisplay,
  getDealGameTitleTooltip,
  formatGamePlatforms,
  formatSecret,
  formatDateOnly,
  formatDateTimeMinutes,
} = useWorkFormatters({
  accountsAll,
  regions,
  domains,
  sources,
  dealFlowStatusOptions,
  maxGameTitleLength,
})

const accountGameTitles = computed(() => {
  // Собирает список названий игр для выбранного аккаунта.
  const gameMap = new Map((gamesAll.value || []).map((g) => [g.game_id, g.title]))
  return (editAccount.game_ids || []).map((id) => gameMap.get(id)).filter(Boolean)
})

const activeDealChips = computed(() => {
  // Формирует "чипы" активных фильтров по сделкам.
  const chips = []
  if (dealFilters.search_q) chips.push({ key: 'search', label: 'Поиск', value: dealFilters.search_q })
  if (dealFilters.type_q) {
    const label = dealTypeOptions.find((t) => t.code === dealFilters.type_q)?.name || dealFilters.type_q
    chips.push({ key: 'type', label: 'Тип', value: label })
  }
  if (dealFilters.customer_q) chips.push({ key: 'customer', label: 'Покупатель', value: dealFilters.customer_q })
  if (dealFilters.responsible_q) chips.push({ key: 'responsible', label: 'Ответств.', value: dealFilters.responsible_q })
  if (dealFilters.region_q) {
    const label = regions.value.find((r) => r.code === dealFilters.region_q)?.name || dealFilters.region_q
    chips.push({ key: 'region', label: 'Регион', value: label })
  }
  if (dealFilters.status_q) {
    const label = dealFlowStatusOptions.find((s) => s.code === dealFilters.status_q)?.name || dealFilters.status_q
    chips.push({ key: 'status', label: 'Статус', value: label })
  }
  if (dealFilters.purchase_from || dealFilters.purchase_to) {
    const from = dealFilters.purchase_from ? formatDateOnly(dealFilters.purchase_from) : '—'
    const to = dealFilters.purchase_to ? formatDateOnly(dealFilters.purchase_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  return chips
})

const activeGameChips = computed(() => {
  // Формирует "чипы" активных фильтров по играм.
  const chips = []
  if (gameFilters.q) {
    chips.push({ key: 'title', label: 'Игра', value: gameFilters.q })
  }
  if (gameFilters.platform_code) {
    const platform = platforms.value.find((p) => p.code === gameFilters.platform_code)
    chips.push({ key: 'platform', label: 'Платформа', value: platform?.name ? `${platform.name} (${platform.code})` : gameFilters.platform_code })
  }
  if (gameFilters.region_code) {
    const region = regions.value.find((r) => r.code === gameFilters.region_code)
    chips.push({ key: 'region', label: 'Регион', value: region?.name ? `${region.name} (${region.code})` : gameFilters.region_code })
  }
  return chips
})

const activeAccountChips = computed(() => {
  // Формирует "чипы" активных фильтров по аккаунтам.
  const chips = []
  if (accountFilters.search_q) chips.push({ key: 'search', label: 'Поиск', value: accountFilters.search_q })
  if (accountFilters.login_q) chips.push({ key: 'login', label: 'Логин', value: accountFilters.login_q })
  if (accountFilters.game_q) chips.push({ key: 'game', label: 'Игра', value: accountFilters.game_q })
  if (accountFilters.region_q) chips.push({ key: 'region', label: 'Регион', value: accountFilters.region_q })
  if (accountFilters.status_q) chips.push({ key: 'status', label: 'Статус', value: accountFilters.status_q })
  if (accountFilters.date_from || accountFilters.date_to) {
    const from = accountFilters.date_from ? formatDateOnly(accountFilters.date_from) : '—'
    const to = accountFilters.date_to ? formatDateOnly(accountFilters.date_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  return chips
})

const isAdmin = computed(() => auth.state.role === 'admin')
const mustPrefillDealsResponsible = computed(() => {
  const role = String(auth.state.role || '').trim().toLowerCase()
  return role === 'manager' || role === 'operator'
})
const showUsersTab = false
const showDashboard = false

const dealModalTitle = computed(() => {
  if (showDealForm.value) {
    const dealKind = newDeal.deal_type_code === 'sale' ? 'ПРОДАЖА' : 'ШЕРИНГ'
    return `НОВАЯ СДЕЛКА - ${dealKind}`
  }
  if (!editDeal.open) return 'СДЕЛКА'
  const dealKind = editDeal.deal_type_code === 'sale' ? 'ПРОДАЖА' : 'ШЕРИНГ'
  const dateLabel = formatDateOnly(editDeal.purchase_at || editDeal.created_at)
  return dateLabel === '—' ? `СДЕЛКА - ${dealKind}` : `СДЕЛКА (${dealKind}) - ${dateLabel}`
})

const {
  modalRef,
  modalStyle,
  resetModalPos,
  startModalDrag,
  onModalDrag,
  stopModalDrag,
} = useModalDrag()

// Закрывает все открытые модалки перед переключением на другой сценарий.
function closeAllModals() {
  suppressUnsavedConfirm.value = true
  try {
    if (unsavedConfirm.open) answerUnsavedConfirm(false)
    closePwdModal()
    closeAccountImport()
    closeGameImport()
    closeSlotImport()
    closeGameModal()
    closeDealModal()
    closeDomainModal()
    closeSourceModal()
    closePlatformModal()
    closeRegionModal()
    closeUserModal()
    cancelEditAccount()
  } finally {
    suppressUnsavedConfirm.value = false
  }
}

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

const activeTab = ref('deals')

const setActiveTab = (tab) => {
  // Переключает вкладку и синхронизирует ее с query-параметром.
  const next = TAB_KEYS.includes(tab) ? tab : 'deals'
  activeTab.value = next
  const current = String(route.query.tab || '')
  if (current !== next) {
    router.replace({ name: 'work', query: { ...route.query, tab: next } })
  }
}

watch(
  () => auth.state.token,
  async (token) => {
    // Подгружает список пользователей сразу после входа, чтобы имя в шапке не мигало username.
    if (!token || responsibleUsers.value.length) return
    await loadResponsibleUsers()
  },
  { immediate: true },
)

watch(
  [activeTab, () => auth.state.token],
  async ([tab, token]) => {
    // Подгружает список ответственных при входе в сделки.
    if (tab !== 'deals' || !token) return
    if (!responsibleUsers.value.length) {
      await loadResponsibleUsers()
    }
    // После загрузки users ставим фильтр "Ответств." по name для manager/operator.
    const role = String(auth.state.role || '').trim().toLowerCase()
    if ((role === 'manager' || role === 'operator') && !dealFilters.responsible_q) {
      const byName = String(currentUserResponsibleName.value || '').trim()
      if (byName) {
        dealFilters.responsible_q = byName
        await loadDeals(1)
      }
    }
  },
  { immediate: true },
)

const newGame = reactive({
  title: '',
  short_title: '',
  link: '',
  logo_url: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
})

const newDeal = reactive(createNewDealState())
const newDealResponsible = ref('')
const newDealCommentOpen = ref(false)

const editDeal = reactive(createEditDealState())
const editDealResponsible = ref('')

const games = ref([])
const gamesAll = ref([])
const gamesTotal = ref(0)
const gamesLoading = ref(false)
const editGame = reactive({
  open: false,
  game_id: null,
  title: '',
  short_title: '',
  link: '',
  logo_url: '',
  logo_b64: '',
  logo_mime: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
})
const dealFilters = reactive(createDealFiltersState())
const dealShowCompleted = ref(false)
const {
  analyticsFilters,
  analyticsTotals,
  analyticsByDay,
  analyticsByType,
  analyticsSourcesTopCount,
  analyticsSourcesTopRevenue,
  analyticsRepeatCustomers,
  analyticsLoaded,
  analyticsLoading,
  analyticsError,
  loadAnalytics,
} = useAnalytics({ auth, apiGet, mapApiError })
const slotTypes = ref([])
const accountSlotStatusNew = ref([])
const accountSlotStatusEdit = ref([])
const dealAccountAssignmentsNew = ref([])
const dealAccountAssignmentsEdit = ref([])
const dealAccountAssignmentsLoadingNew = ref(false)
const dealAccountAssignmentsLoadingEdit = ref(false)
const dealSlotAvailabilityNew = ref({})
const dealSlotAvailabilityEdit = ref({})
const dealSlotAvailabilityLoadingNew = ref(false)
const dealSlotAvailabilityLoadingEdit = ref(false)
const dealSlotAutoAssign = ref(false)

const newDomain = ref('')
const editDomain = reactive({ open: false, name: '', original: '' })
const domainEditMode = ref('view')
const newSource = reactive({
  code: '',
  name: '',
})
const editSource = reactive({ open: false, source_id: null, code: '', name: '' })
const sourceEditMode = ref('view')
const newPlatform = reactive({
  code: '',
  name: '',
  slot_capacity: 0,
})
const editPlatform = reactive({ open: false, code: '', name: '', slot_capacity: 0 })
const platformEditMode = ref('view')
const newRegion = reactive({
  code: '',
  name: '',
  purchase_cost_rate: 1,
})
const editRegion = reactive({ open: false, code: '', name: '', purchase_cost_rate: 1 })
const regionEditMode = ref('view')

const newAccount = reactive(createNewAccountState())

const accountModalMode = ref('edit')
const showAccountFilters = ref(false)
const accountGameSearch = ref('')
const editAccountGameSearch = ref('')
const accountGamesLoading = ref(false)
const activeAccountFilter = ref('')
const accountFilterDraft = reactive({
  login: '',
  game: '',
  region: '',
  status: '',
  date_from: '',
  date_to: '',
})
const editAccount = reactive(createEditAccountState())
const showGameForm = ref(false)
const showGameFilters = ref(false)
const showChatsTab = ref(false)
const showDealForm = ref(false)
const activeDealFilter = ref('')
const activeGameFilter = ref('')
const gameFilterDraft = reactive({
  title: '',
  platform: '',
  region: '',
})
const gameFilters = reactive({
  q: '',
  platform_code: '',
  region_code: '',
})
useFilterPopouts({
  activeDealFilter,
  activeGameFilter,
  activeAccountFilter,
})
const telegram = reactive(createTelegramState())
const showGameImport = ref(false)
const showAccountImport = ref(false)
const showSlotImport = ref(false)
const gameImportFile = ref(null)
const accountImportFile = ref(null)
const slotImportFile = ref(null)
const slotImportLimit = ref(10)
const gameImportValidated = ref(false)
const accountImportValidated = ref(false)
const slotImportValidated = ref(false)
const gameImportErrors = ref([])
const accountImportErrors = ref([])
const slotImportErrors = ref([])
const gameImportWarnings = ref([])
const accountImportWarnings = ref([])
const slotImportWarnings = ref([])
const gameImportTotal = ref(0)
const accountImportTotal = ref(0)
const slotImportTotal = ref(0)
const gameImportLoading = ref(false)
const accountImportLoading = ref(false)
const slotImportLoading = ref(false)
const gameImportMessage = ref('')
const accountImportMessage = ref('')
const slotImportMessage = ref('')
const slotImportError = ref('')
const slotImportAction = ref('')
const slotImportProgress = reactive({ current: 0, total: 0, phase: '' })
const slotImportJobId = ref('')
const slotImportStats = ref(null)
const gameImportAction = ref('')
const accountImportAction = ref('')
const gameImportStats = ref(null)
const accountImportStats = ref(null)
const gameImportProgress = reactive({ current: 0, total: 0, phase: '' })
const accountImportProgress = reactive({ current: 0, total: 0, phase: '' })
const gameImportJobId = ref('')
const accountImportJobId = ref('')
const importDetailsRef = ref(null)
const accountImportDetailsRef = ref(null)
const gameLogoLoading = ref(false)
const gameLogoCache = new Map()
const gameLogoUploading = ref(false)
const gameLogoProgress = ref(0)
const { readLogoCache, writeLogoCache, clearLogoCache } = useGameLogoCache({
  cacheKey: GAME_LOGO_CACHE_KEY,
  ttlMs: GAME_LOGO_CACHE_TTL_MS,
})
const showDomainForm = ref(false)
const showSourceForm = ref(false)
const showPlatformForm = ref(false)
const showRegionForm = ref(false)
const accountFilters = reactive(createAccountFiltersState())
const accountSort = ref('login_asc')
const gamesSort = ref({ key: 'title', dir: 'asc' })
const {
  dealListError,
  dealListLoading,
  dealPage,
  dealPageInput,
  dealPageSize,
  dealTotal,
  dealSort,
  totalPages,
  sortedDeals,
  toggleDealSort,
  setDealPage,
  jumpDealPage,
  prevDealPage,
  nextDealPage,
  loadDeals,
} = useDeals({
  auth,
  apiGet,
  mapApiError,
  resolveDealFlowStatusFilter,
  dealFilters,
  dealShowCompleted,
})
// Отдельно подключаем действия создания/обновления сделок.
const { createDeal, updateDeal, markDealCompleted } = useDealsActions({
  auth,
  apiPost,
  apiPut,
  mapApiError,
  toUtcDateTime,
  newDeal,
  editDeal,
  newDealResponsible,
  editDealResponsible,
  dealPage,
  dealError,
  dealOk,
  dealLoading,
  dealSaving,
  dealCompletingId,
  dealBackgroundSync,
  loadDeals,
  loadAccountsAll,
  closeDealModal,
  suppressUnsavedConfirm,
  showDealWarning,
})
const usersSort = ref({ key: 'created_at', dir: 'desc' })
const domainsSortAsc = ref(true)
const sourcesSort = ref({ key: 'code', dir: 'asc' })
const platformsSort = ref({ key: 'code', dir: 'asc' })
const regionsSort = ref({ key: 'code', dir: 'asc' })
const gamesPage = ref(1)
const gamesPageInput = ref(1)
const gamesPageSize = ref(20)

const newDealGameSearch = ref('')
const editDealGameSearch = ref('')
const dealAccountsForGameNew = ref([])
const dealAccountsForGameEdit = ref([])
const dealAccountsForGameLoading = ref(false)
const quickNewGame = reactive({ title: '', platform_codes: [] })
const quickEditGame = reactive({ title: '', platform_codes: [] })
const quickNewGameLoading = ref(false)
const quickEditGameLoading = ref(false)
const quickNewGameError = ref('')
const quickEditGameError = ref('')
const quickNewAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickEditAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickNewAccountLoading = ref(false)
const quickEditAccountLoading = ref(false)
const quickNewAccountError = ref('')
const quickEditAccountError = ref('')
const dealQuickAccountBusy = computed(() => quickNewAccountLoading.value || quickEditAccountLoading.value)
const dealQuickGameBusy = computed(() => quickNewGameLoading.value || quickEditGameLoading.value)
const {
  filteredNewDealGames,
  filteredEditDealGames,
  newDealGameNoMatches,
  editDealGameNoMatches,
  dealAccountsForNew,
  dealAccountsForEdit,
  dealGameAssignmentsForSelectedSlotNew,
  dealGameAssignmentsForSelectedSlotEdit,
  hasAnyGameAssignmentsNew,
  hasAnyGameAssignmentsEdit,
} = useDealsViewState({
  gamesAll,
  newDeal,
  editDeal,
  newDealGameSearch,
  editDealGameSearch,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
})

const {
  sortedAccounts,
  filteredAccountGames,
  filteredEditAccountGames,
} = useAccountsDerivedState({
  accounts,
  gamesAll,
  accountGameSearch,
  editAccountGameSearch,
})

const getDealTypeName = (code) => dealTypeOptions.find((t) => t.code === code)?.name || code || '—'
const maxDate = getMaxDate()

const {
  getSlotTypeLabel,
  formatAccountSlotStatusLine,
  getSortedSlotStatus,
  sortedAccountSlotAssignments,
  getAccountSlotStatusList,
  getGameLabelById,
  isSlotTypeSupportedForGame,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  isDealSlotTypeUnsupported,
  hasFreeDealSlots,
} = useSlotHelpers({
  slotTypes,
  gamesAll,
  newDeal,
  editDeal,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  hasAnyGameAssignmentsNew,
  hasAnyGameAssignmentsEdit,
  accountSlotAssignments,
  accountSlotAssignmentsSort,
})

const formatAccountGamesLine = (account) => {
  const list = Array.isArray(account?.game_titles) ? account.game_titles : []
  if (!list.length) return '—'
  return list.join(', ')
}

const {
  setGamesPageSizeFromEvent,
  setGamesPageInputFromEvent,
  getAccountSortClass,
  getGamesSortClass,
  getDealSortClass,
  getDomainsSortClass,
  getKeyedSortClass,
  getSlotAssignmentStatus,
  getNotesRows,
  getCompactNotesRows,
} = useWorkUiHelpers({
  gamesPageSize,
  gamesPageInput,
  accountSort,
  gamesSort,
  dealSort,
  domainsSortAsc,
})

const {
  openGameAccounts,
  openCreateGameModal,
  closeGameModal,
  onGameLogoSelected,
  removeGameLogo,
  goToAccount,
  loadGames,
  loadGamesAll,
  createGame,
  updateGame,
  deleteGame,
} = useGamesFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiPostFormWithProgress,
  mapApiError,
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showGameForm,
  gameEditMode,
  editGame,
  newGame,
  gameError,
  gameOk,
  gamesLoading,
  gameLoading,
  gameSaving,
  games,
  gamesAll,
  gamesTotal,
  gamesSort,
  gamesPage,
  gamesPageSize,
  gameFilters,
  gameFilterDraft,
  accountFilters,
  gameAccounts,
  gameAccountsLoading,
  gameAccountsError,
  gameAccountsPage,
  gameSlotAssignments,
  gameSlotAssignmentsError,
  gameSlotAssignmentsLoading,
  gameLogoLoading,
  gameLogoUploading,
  gameLogoProgress,
  gameLogoCache,
  readLogoCache,
  writeLogoCache,
  clearLogoCache,
  loadGameSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

const {
  getReserveSecrets,
  loadAccounts,
  loadAccountsAll: loadAccountsAllFromAccountsFlow,
  startEditAccount,
  openCreateAccountModal,
  cancelEditAccount,
  createAccount,
  updateAccount,
  deleteAccount,
} = useAccountsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  resolveAccountSort,
  closeAllModals,
  resetModalPos,
  accountModalMode,
  accountEditMode,
  editAccount,
  newAccount,
  accountGameSearch,
  editAccountGameSearch,
  accountGamesLoading,
  accountDeals,
  accountDealsError,
  accountDealsLoading,
  accountSlotAssignments,
  accountSlotAssignmentsError,
  accountSlotAssignmentsLoading,
  accounts,
  accountsAll,
  accountsTotal,
  accountsPage,
  accountsPageSize,
  accountFilters,
  accountSort,
  accountSecrets,
  accountsError,
  accountsOk,
  accountsLoading,
  accountSaving,
  loadAccountSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

loadAccountsAllDeferred.set(loadAccountsAllFromAccountsFlow)

// Логика формы сделки: быстрые создания, загрузки связей, слоты.
const {
  createQuickGame,
  createQuickAccount,
  clearNewDealGame,
  clearEditDealGame,
  loadDealAccountsForGame,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealGameAssignments,
  loadDealSlotAvailability,
  releaseSlotFromDeal,
} = useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  isSlotTypeSupportedForGame,
  slotTypes,
  accountsAll,
  showDealForm,
  editDeal,
  newDeal,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsLoadingEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
  dealGameAssignmentsLoadingNew,
  dealGameAssignmentsLoadingEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  dealSlotAvailabilityLoadingNew,
  dealSlotAvailabilityLoadingEdit,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealAccountsForGameLoading,
  accountSlotReleaseLoading,
  dealSlotAutoAssign,
  dealError,
  quickNewGame,
  quickEditGame,
  quickNewGameLoading,
  quickEditGameLoading,
  quickNewGameError,
  quickEditGameError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountLoading,
  quickEditAccountLoading,
  quickNewAccountError,
  quickEditAccountError,
  newDealGameSearch,
  editDealGameSearch,
  loadGamesAll,
  loadAccountsAll,
})

const {
  openCreateSaleModal,
  openCreateSharingModal,
  closeDealModal: closeDealModalFromFlow,
  startEditDeal,
  toggleDealEditMode,
} = useDealModalFlow({
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showDealForm,
  dealError,
  dealOk,
  newDeal,
  editDeal,
  dealEditMode,
  dealInitLock,
  newDealResponsible,
  editDealResponsible,
  newDealCommentOpen,
  newDealGameSearch,
  editDealGameSearch,
  quickNewGame,
  quickEditGame,
  quickNewGameError,
  quickEditGameError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountError,
  quickEditAccountError,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  nextTick,
  loadDealSlotAvailability,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  currentResponsibleName: currentUserResponsibleName,
})

closeDealModalDeferred.set(closeDealModalFromFlow)

// Вся логика вкладки Telegram.
const {
  loadTelegramStatus,
  tgAuthStart,
  tgAuthConfirm,
  tgAuthPassword,
  tgAuthDisconnect,
  setTelegramDialogFilter,
  selectTelegramDialog,
  onTelegramMessagesScroll,
  onTelegramMediaRendered,
  setTelegramActiveContact,
  toggleTelegramContactEdit,
  cancelTelegramContactEdit,
  saveTelegramContact,
  showTelegramChannelLabel,
  stopTelegramPolling,
  startTelegramPolling,
  handleTelegramActiveChatChange,
  sendTelegramMessage,
  setTelegramDialogStatus,
  revokeTelegramMediaUrls,
} = useTelegram({
  auth,
  telegram,
  activeTab,
  tgMessagesList,
  apiGet,
  apiPost,
  apiPut,
  apiGetFile,
  mapApiError,
  nextTick,
  showTelegramChannelLabelForList,
  TELEGRAM_DIALOGS_POLL_MS,
  TELEGRAM_MESSAGES_POLL_MS,
  TELEGRAM_DIALOGS_POLL_ERROR_MS,
  TELEGRAM_MESSAGES_POLL_ERROR_MS,
})

// Профиль пользователя, пользователи и проверка API.
const {
  checkApi,
  loadUsers,
  createUser,
  openUserModal,
  closeUserModal,
  changePassword,
  openPwdModal,
  closePwdModal,
  onLogout,
} = useUserProfileFlow({
  auth,
  router,
  isAdmin,
  apiGet,
  apiPost,
  mapApiError,
  closeAllModals,
  resetModalPos,
  apiOk,
  loading,
  error,
  users,
  roles,
  userError,
  userOk,
  userLoading,
  showUserForm,
  newUser,
  pwdError,
  pwdOk,
  pwdLoading,
  showPwdForm,
  pwdForm,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

// Контекст верхней панели: вкладки, пользователь и кнопка выхода.
const topBarCtx = asCtx({
  userRoleName: topBarRoleName,
  activeTab,
  routeQuery: computed(() => route.query || {}),
  isAdmin,
  showChatsTab,
  showUsersTab,
  onLogout,
})

// Контекст дашборда: статус API и кнопка проверки.
const dashboardSectionCtx = asCtx({
  apiOk,
  loading,
  checkApi,
})

// Контекст вкладки профиля: переход в users и смена пароля.
const profileSectionCtx = asCtx({
  isAdmin,
  setActiveTab,
  openPwdModal,
  showPwdForm,
  closePwdModal,
  modalRef,
  modalStyle,
  startModalDrag,
  pwdLoading,
  pwdForm,
  pwdError,
  pwdOk,
  changePassword,
})

// Импорт/валидация/отмена для игр, аккаунтов и слотов.
const {
  openGameImport,
  openAccountImport,
  openSlotImport,
  closeSlotImport,
  closeGameImport,
  closeAccountImport,
  stopGameImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  scrollToImportDetails,
  scrollToAccountImportDetails,
  onGameImportFile,
  onAccountImportFile,
  onSlotImportFile,
  downloadGameTemplate,
  downloadAccountTemplate,
  downloadGameImportReport,
  validateGameImport,
  downloadAccountImportReport,
  validateAccountImport,
  cleanSlotImport,
  validateSlotImport,
  uploadSlotImport,
  downloadSlotImportReport,
  cancelSlotImport,
  uploadGameImport,
  uploadAccountImport,
  cancelGameImport,
  cancelAccountImport,
} = useImportFlow({
  auth,
  API_BASE,
  apiGet,
  apiPost,
  apiPostForm,
  apiGetFile,
  mapApiError,
  GAME_IMPORT_JOB_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  closeAllModals,
  resetModalPos,
  showGameImport,
  showAccountImport,
  showSlotImport,
  gameImportFile,
  accountImportFile,
  slotImportFile,
  slotImportLimit,
  gameImportValidated,
  accountImportValidated,
  slotImportValidated,
  gameImportErrors,
  accountImportErrors,
  slotImportErrors,
  gameImportWarnings,
  accountImportWarnings,
  slotImportWarnings,
  gameImportTotal,
  accountImportTotal,
  slotImportTotal,
  gameImportLoading,
  accountImportLoading,
  slotImportLoading,
  gameImportMessage,
  accountImportMessage,
  slotImportMessage,
  slotImportError,
  slotImportAction,
  slotImportProgress,
  slotImportJobId,
  slotImportStats,
  gameImportAction,
  accountImportAction,
  gameImportStats,
  accountImportStats,
  gameImportProgress,
  accountImportProgress,
  gameImportJobId,
  accountImportJobId,
  importDetailsRef,
  accountImportDetailsRef,
  loadGames,
  loadGamesAll,
  loadAccounts,
  loadAccountsAll,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

// Работа со справочниками: платформы, регионы, источники, домены.
const {
  loadCatalogs,
  loadSlotTypes,
  loadDomains,
  loadSources,
  openEditDomain,
  openDomainModal,
  closeDomainModal,
  saveEditDomain,
  openEditSource,
  openSourceModal,
  closeSourceModal,
  saveEditSource,
  openEditPlatform,
  openPlatformModal,
  closePlatformModal,
  saveEditPlatform,
  openEditRegion,
  openRegionModal,
  closeRegionModal,
  saveEditRegion,
  createDomain,
  createSource,
  createPlatform,
  createRegion,
  deleteDomain,
  deleteSource,
  deletePlatform,
  deleteRegion,
} = useCatalogs({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  closeAllModals,
  resetModalPos,
  showDomainForm,
  showSourceForm,
  showPlatformForm,
  showRegionForm,
  newDomain,
  editDomain,
  domainEditMode,
  newSource,
  editSource,
  sourceEditMode,
  newPlatform,
  editPlatform,
  platformEditMode,
  newRegion,
  editRegion,
  regionEditMode,
  catalogsError,
  catalogsOk,
  catalogsLoading,
  catalogSaving,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  newDeal,
  editDeal,
  loadDealSlotAvailability,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

const {
  gamesTotalPages,
  sortedGames,
  pagedGames,
  gameAccountsTotalPages,
  pagedGameAccounts,
} = useGamesViewState({
  games,
  gamesTotal,
  gamesPage,
  gamesPageInput,
  gamesPageSize,
  loadGames,
  gameAccounts,
  gameAccountsSort,
  gameAccountsPage,
  gameAccountsPageSize,
})

// Пагинация и отображение аккаунтов.
const { accountsTotalPages } = useAccountsViewState({
  accountsTotal,
  accountsPage,
  accountsPageInput,
  accountsPageSize,
  loadAccounts,
})

const {
  sortedUsers,
  sortedDomains,
  sortedSources,
  sourcesByCode,
  sortedPlatforms,
  sortedRegions,
} = useCatalogsViewState({
  users,
  usersSort,
  domains,
  domainsSortAsc,
  sources,
  sourcesSort,
  platforms,
  platformsSort,
  regions,
  regionsSort,
})

// Общие фильтры, сортировки и переходы между страницами.
const {
  toggleAccountSort,
  toggleGamesSort,
  toggleUsersSort,
  toggleDomainsSort,
  toggleSourcesSort,
  togglePlatformsSort,
  toggleRegionsSort,
  setGamesPage,
  jumpGamesPage,
  prevGamesPage,
  nextGamesPage,
  setAccountsPage,
  jumpAccountsPage,
  prevAccountsPage,
  nextAccountsPage,
  resetDealFilter,
  validateDealRange,
  dealFilterErrors,
  resetGameFilter,
  openGameFilter,
  applyGameFilter,
  resetAccountFilter,
  openAccountFilter,
  applyAccountFilter,
} = useWorkFilters({
  accountSort,
  accountsPage,
  accountsPageInput,
  accountsTotalPages,
  loadAccounts,
  gamesSort,
  gamesPage,
  gamesPageInput,
  gamesTotalPages,
  loadGames,
  usersSort,
  domainsSortAsc,
  sourcesSort,
  platformsSort,
  regionsSort,
  activeDealFilter,
  dealFilters,
  loadDeals,
  activeGameFilter,
  gameFilters,
  gameFilterDraft,
  activeAccountFilter,
  accountFilters,
  accountFilterDraft,
})

// UI-действия экрана: поиск, открытие модалок, подгрузки деталей.
const {
  openAccountFromGame,
  applyDealSearch,
  applyAccountSearch,
  applyGameSearch,
  syncNewDealGameSearch,
  syncEditDealGameSearch,
  onNewDealGameSearch,
  onEditDealGameSearch,
  loadAccountSlotAssignments: loadAccountSlotAssignmentsFromActions,
  loadGameSlotAssignments: loadGameSlotAssignmentsFromActions,
  releaseSlotAssignment,
  sortGameAccounts,
  nextGameAccountsPage,
  prevGameAccountsPage,
} = useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
  loadDeals,
  loadAccounts,
  loadGames,
  accountsPage,
  accountsPageInput,
  gamesPage,
  gamesPageInput,
  newDeal,
  editDeal,
  newDealGameSearch,
  editDealGameSearch,
  quickNewGame,
  quickEditGame,
  quickNewGameError,
  quickEditGameError,
  accountSlotAssignments,
  accountSlotAssignmentsLoading,
  accountSlotAssignmentsError,
  gameSlotAssignments,
  gameSlotAssignmentsLoading,
  gameSlotAssignmentsError,
  accountSlotReleaseLoading,
  editAccount,
  showDealForm,
  dealError,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealAccountsForGame,
  loadDealGameAssignments,
  gameAccountsSort,
  gameAccountsPage,
  gameAccountsTotalPages,
  closeGameModal,
  goToAccount,
})

loadAccountSlotAssignmentsDeferred.set(loadAccountSlotAssignmentsFromActions)
loadGameSlotAssignmentsDeferred.set(loadGameSlotAssignmentsFromActions)

const gameLogoSrc = computed(() => {
  if (!editGame.logo_b64 || !editGame.logo_mime) return ''
  return `data:${editGame.logo_mime};base64,${editGame.logo_b64}`
})

// Контекст вкладки аккаунтов: фильтры, таблица, пагинация и модалки.
const accountsSectionCtx = asCtx({
  accountFilters,
  applyAccountSearch,
  openCreateAccountModal,
  openAccountImport,
  openSlotImport,
  loadAccounts,
  accountsLoading,
  activeAccountChips,
  resetAccountFilter,
  showAccountImport,
  closeAccountImport,
  modalRef,
  modalStyle,
  startModalDrag,
  accountImportLoading,
  downloadAccountTemplate,
  validateAccountImport,
  accountImportFile,
  accountImportAction,
  uploadAccountImport,
  accountImportValidated,
  accountImportJobId,
  cancelAccountImport,
  scrollToAccountImportDetails,
  accountImportProgress,
  onAccountImportFile,
  accountImportDetailsRef,
  accountImportMessage,
  accountImportErrors,
  accountImportWarnings,
  downloadAccountImportReport,
  accountImportStats,
  sortedAccounts,
  activeAccountFilter,
  accountFilterDraft,
  openAccountFilter,
  toggleAccountSort,
  getAccountSortClass,
  applyAccountFilter,
  startEditAccount,
  formatAccountGamesLine,
  getAccountSlotStatusList,
  formatAccountSlotStatusLine,
  formatSecret,
  getReserveSecrets,
  accountsTotal,
  accountsPageSize,
  setAccountsPage,
  accountsPage,
  prevAccountsPage,
  accountsPageInput,
  accountsTotalPages,
  jumpAccountsPage,
  nextAccountsPage,
  editAccount,
  cancelEditAccount,
  accountModalMode,
  accountEditMode,
  setAccountEditMode,
  updateAccount,
  createAccount,
  deleteAccount,
  accountGamesLoading,
  getDomainLabel,
  domains,
  getRegionLabel,
  regions,
  getAccountStatusLabel,
  maxDate,
  accountGameTitles,
  editAccountGameSearch,
  setEditAccountGameSearch,
  filteredEditAccountGames,
  accountSlotAssignmentsError,
  accountSlotAssignmentsLoading,
  accountSlotAssignments,
  sortedAccountSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  accountSlotReleaseLoading,
  releaseSlotAssignment,
  accountDealsError,
  accountDealsLoading,
  accountDeals,
  getDealGameTitleTooltip,
  getDealGameTitleDisplay,
  formatDate: formatDateTimeMinutes,
  accountsError,
  accountsOk,
  newAccount,
  accountGameSearch,
  setAccountGameSearch,
  filteredAccountGames,
  showSlotImport,
  closeSlotImport,
  slotImportLoading,
  validateSlotImport,
  slotImportFile,
  uploadSlotImport,
  slotImportValidated,
  slotImportAction,
  cleanSlotImport,
  slotImportJobId,
  cancelSlotImport,
  slotImportProgress,
  onSlotImportFile,
  slotImportLimit,
  setSlotImportLimit,
  slotImportErrors,
  slotImportWarnings,
  downloadSlotImportReport,
  slotImportTotal,
  slotImportStats,
  slotImportMessage,
  slotImportError,
})

// Контекст вкладки Telegram: состояния и действия для отдельной секции.
const telegramSectionCtx = asCtx({
  telegram,
  isAdmin,
  loadTelegramStatus,
  tgAuthStart,
  tgAuthConfirm,
  tgAuthPassword,
  tgAuthDisconnect,
  setTelegramDialogFilter,
  selectTelegramDialog,
  formatDateTimeMinutes,
  tgMessagesList,
  onTelegramMessagesScroll,
  setTelegramActiveContact,
  toggleTelegramContactEdit,
  cancelTelegramContactEdit,
  saveTelegramContact,
  setTelegramDialogStatus,
  onTelegramMediaRendered,
  showTelegramChannelLabel,
  formatTelegramMessageHtml,
  formatTelegramSender,
  isTelegramImage,
  isTelegramVideo,
  sendTelegramMessage,
})

const {
  gameEditorModalCtx,
  dealsSectionCtx,
  dealEditorModalShellCtx,
  dealEditorModalBodyCtx,
  dealEditorFormCtx,
  catalogsSectionCtx,
} = useWorkSectionContexts({
  editGame,
  showGameForm,
  closeGameModal,
  modalRef,
  modalStyle,
  startModalDrag,
  gameEditMode,
  updateGame,
  gameLoading,
  createGame,
  deleteGame,
  gameLogoSrc,
  gameLogoLoading,
  onGameLogoSelected,
  gameLogoUploading,
  gameLogoProgress,
  removeGameLogo,
  platforms,
  getRegionLabel,
  regions,
  gameAccountsError,
  gameAccountsLoading,
  pagedGameAccounts,
  sortGameAccounts,
  openAccountFromGame,
  gameAccountsTotalPages,
  gameAccountsPage,
  prevGameAccountsPage,
  nextGameAccountsPage,
  gameSlotAssignmentsError,
  gameSlotAssignmentsLoading,
  gameSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  gameError,
  gameOk,
  newGame,
  showDomainForm,
  editDomain,
  closeDomainModal,
  domainEditMode,
  saveEditDomain,
  catalogsLoading,
  deleteDomain,
  createDomain,
  newDomain,
  showSourceForm,
  editSource,
  closeSourceModal,
  sourceEditMode,
  saveEditSource,
  deleteSource,
  createSource,
  newSource,
  showPlatformForm,
  editPlatform,
  closePlatformModal,
  platformEditMode,
  saveEditPlatform,
  deletePlatform,
  createPlatform,
  newPlatform,
  showRegionForm,
  editRegion,
  closeRegionModal,
  regionEditMode,
  saveEditRegion,
  deleteRegion,
  createRegion,
  newRegion,
  isAdmin,
  dealsRealtimeStatus,
  dealFilters,
  applyDealSearch,
  openCreateSaleModal,
  openCreateSharingModal,
  dealShowCompleted,
  setDealShowCompleted,
  loadDeals,
  dealListLoading,
  dealListError,
  activeDealChips,
  resetDealFilter,
  sortedDeals,
  dealTypeOptions,
  dealFlowStatusOptions,
  activeDealFilter,
  setActiveDealFilter,
  toggleDealSort,
  getDealSortClass,
  validateDealRange,
  dealFilterErrors,
  minDate,
  maxDate,
  editDeal,
  startEditDeal,
  markDealCompleted,
  dealSaving,
  dealCompletingId,
  dealTotal,
  dealPageSize,
  setDealPage,
  dealPage,
  prevDealPage,
  dealPageInput,
  totalPages,
  jumpDealPage,
  nextDealPage,
  showDealForm,
  closeDealModal,
  dealModalTitle,
  dealEditMode,
  toggleDealEditMode,
  updateDeal,
  dealLoading,
  dealBackgroundSync,
  createDeal,
  dealQuickAccountBusy,
  dealQuickGameBusy,
  getDealTypeName,
  dealAccountsForGameLoading,
  isDealSlotTypeUnsupported,
  dealAccountsForEdit,
  dealSlotAvailabilityLoadingEdit,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  getAccountLabelById,
  hasFreeDealSlots,
  hasAnyGameAssignmentsEdit,
  dealGameAssignmentsLoadingEdit,
  dealGameAssignmentsForSelectedSlotEdit,
  accountSlotReleaseLoading,
  releaseSlotFromDeal,
  quickEditAccount,
  domains,
  quickEditAccountLoading,
  createQuickAccount,
  quickEditAccountError,
  accountSlotStatusEdit,
  slotTypes,
  getSortedSlotStatus,
  dealAccountAssignmentsLoadingEdit,
  dealAccountAssignmentsEdit,
  getSourceLabelById,
  sourcesByCode,
  maxPrice,
  clampPrice,
  getFlowStatusLabel,
  editDealGameSearch,
  onEditDealGameSearch,
  filteredEditDealGames,
  syncEditDealGameSearch,
  getGameLabelById,
  editDealGameNoMatches,
  clearEditDealGame,
  quickEditGame,
  quickEditGameLoading,
  createQuickGame,
  quickEditGameError,
  getNotesRows,
  dealError,
  dealOk,
  newDeal,
  responsibleUserOptions,
  newDealResponsible,
  editDealResponsible,
  newDealGameSearch,
  onNewDealGameSearch,
  filteredNewDealGames,
  newDealGameNoMatches,
  syncNewDealGameSearch,
  clearNewDealGame,
  quickNewGame,
  quickNewGameLoading,
  quickNewGameError,
  dealSlotAvailabilityLoadingNew,
  dealAccountsForNew,
  hasAnyGameAssignmentsNew,
  dealGameAssignmentsLoadingNew,
  dealGameAssignmentsForSelectedSlotNew,
  quickNewAccount,
  quickNewAccountLoading,
  quickNewAccountError,
  accountSlotStatusNew,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsNew,
  newDealCommentOpen,
  getCompactNotesRows,
  catalogsError,
  catalogsOk,
  openDomainModal,
  loadDomains,
  sortedDomains,
  toggleDomainsSort,
  getDomainsSortClass,
  openEditDomain,
  openSourceModal,
  loadSources,
  sortedSources,
  toggleSourcesSort,
  getKeyedSortClass,
  sourcesSort,
  openEditSource,
  openPlatformModal,
  loadCatalogs,
  sortedPlatforms,
  togglePlatformsSort,
  platformsSort,
  openEditPlatform,
  openRegionModal,
  sortedRegions,
  toggleRegionsSort,
  regionsSort,
  openEditRegion,
})

// Контекст вкладки игр: фильтры, таблица, пагинация, импорт и модалка.
const gamesSectionCtx = asCtx({
  gameFilters,
  applyGameSearch,
  openCreateGameModal,
  openGameImport,
  loadGames,
  gamesLoading,
  activeGameChips,
  resetGameFilter,
  showGameImport,
  closeGameImport,
  modalRef,
  modalStyle,
  startModalDrag,
  gameImportLoading,
  downloadGameTemplate,
  validateGameImport,
  gameImportFile,
  gameImportAction,
  uploadGameImport,
  gameImportValidated,
  gameImportJobId,
  cancelGameImport,
  scrollToImportDetails,
  gameImportProgress,
  onGameImportFile,
  importDetailsRef,
  gameImportMessage,
  gameImportErrors,
  gameImportWarnings,
  downloadGameImportReport,
  gameImportStats,
  sortedGames,
  pagedGames,
  activeGameFilter,
  gameFilterDraft,
  openGameFilter,
  toggleGamesSort,
  getGamesSortClass,
  applyGameFilter,
  formatGamePlatforms,
  openGameAccounts,
  gamesTotal,
  gamesPageSize,
  setGamesPageSizeFromEvent,
  gamesPage,
  setGamesPage,
  prevGamesPage,
  gamesPageInput,
  setGamesPageInputFromEvent,
  gamesTotalPages,
  jumpGamesPage,
  nextGamesPage,
  gameEditorModalCtx,
})

// Контекст вкладки сделок: список + модалка редактирования сделки.
const dealsAreaCtx = asCtx({
  dealsSectionCtx,
  dealEditorModalShellCtx,
  dealEditorModalBodyCtx,
  dealEditorFormCtx,
})

// Контекст вкладки аналитики: фильтры, таблицы и форматтеры.
const analyticsSectionCtx = asCtx({
  analyticsLoading,
  analyticsError,
  analyticsLoaded,
  analyticsFilters,
  maxDate,
  minDate,
  dealTypeOptions,
  regions,
  sourcesByCode,
  analyticsTotals,
  analyticsByDay,
  analyticsByType,
  analyticsSourcesTopCount,
  analyticsSourcesTopRevenue,
  analyticsRepeatCustomers,
  loadAnalytics,
  formatPrice,
  formatDateOnly,
  getDealTypeName,
  formatPercent,
})

// Контекст вкладки пользователей: список и модалка создания.
const usersSectionCtx = asCtx({
  openUserModal,
  loadUsers,
  userLoading,
  showUserForm,
  closeUserModal,
  modalRef,
  modalStyle,
  startModalDrag,
  newUser,
  roles,
  createUser,
  userError,
  userOk,
  sortedUsers,
  toggleUsersSort,
})

useWorkLifecycle({
  auth,
  router,
  route,
  isAdmin,
  loadUsers,
  stopGameImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  stopTelegramPolling,
  revokeTelegramMediaUrls,
  onModalDrag,
  stopModalDrag,
})

// Следит за активной вкладкой и подгружает данные по мере открытия вкладок.
useActiveTabWatcher({
  activeTab,
  isAdmin,
  dealFilters,
  defaultDealsResponsibleFilter,
  mustPrefillDealsResponsible,
  showUserForm,
  showGameForm,
  showGameFilters,
  showDealForm,
  showAccountFilters,
  activeGameFilter,
  activeAccountFilter,
  editGame,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  slotTypesLoadedOnce,
  accountsAllLoadedOnce,
  gamesAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  games,
  gamesAll,
  accountsAll,
  gamesPage,
  accountsPage,
  checkApi,
  loadUsers,
  loadCatalogs,
  loadDomains,
  loadSources,
  loadSlotTypes,
  loadGames,
  loadGamesAll,
  loadAccounts,
  loadAccountsAll,
  loadDeals,
  loadTelegramStatus,
  startTelegramPolling,
  stopTelegramPolling,
})

// Следит за route и служебными эффектами экрана.
useWorkLifecycleWatchers({
  route,
  TAB_KEYS,
  activeTab,
  telegram,
  startTelegramPolling,
  stopTelegramPolling,
  handleTelegramActiveChatChange,
  editAccount,
  domains,
  loadDomains,
  resetModalPos,
})

// Следит за формами сделок и связанными слотами/назначениями.
useDealsWatchers({
  newDeal,
  editDeal,
  dealInitLock,
  dealSlotAutoAssign,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  loadDealAccountsForGame,
  loadDealGameAssignments,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealSlotAvailability,
})

// Подключает realtime-обновления списка сделок через WebSocket.
useDealsRealtime({
  activeTab,
  auth,
  dealPage,
  editDeal,
  showDealForm,
  loadDeals,
  wsState: dealsRealtimeStatus,
})

</script>

<style src="./work/styles/work-core.css"></style>
<style src="./work/styles/work-analytics.css"></style>
<style src="./work/styles/work-deals.css"></style>
<style src="./work/styles/work-telegram.css"></style>
<style src="./work/styles/work-accounts.css"></style>
<style src="./work/styles/work-ui.css"></style>
<style src="./work/styles/work-forms.css"></style>
<style src="./work/styles/work-table.css"></style>
<style src="./work/styles/work-responsive.css"></style>
