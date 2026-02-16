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


        <WorkProductsSection
          v-if="activeTab === 'products'"
          :ctx="productsSectionCtx"
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
              <button class="btn btn--danger" type="button" @click="answerUnsavedConfirm(true)">Закрыть</button>
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

    <teleport to="body">
      <div v-if="dealConfirm.open" class="work-page work-modal-root modal-backdrop unsaved-confirm" @click.self="answerDealConfirm(false)">
        <div class="modal modal--auto unsaved-confirm__modal">
          <div class="panel__head panel__head--tight unsaved-confirm__head">
            <h3 class="unsaved-confirm__title">{{ dealConfirm.title }}</h3>
          </div>
          <div class="modal__body">
            <p class="muted unsaved-confirm__text">{{ dealConfirm.message }}</p>
            <div class="toolbar-actions unsaved-confirm__actions">
              <button class="ghost" type="button" @click="answerDealConfirm(false)">{{ dealConfirm.cancelText }}</button>
              <button class="btn btn--danger" type="button" @click="answerDealConfirm(true)">{{ dealConfirm.confirmText }}</button>
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
import { API_BASE, apiGet, apiPost, apiDelete, apiPut, apiPostForm, apiGetFile } from '../api/http'
import {
  TAB_KEYS,
  TELEGRAM_DIALOGS_POLL_MS,
  TELEGRAM_MESSAGES_POLL_MS,
  TELEGRAM_DIALOGS_POLL_ERROR_MS,
  TELEGRAM_MESSAGES_POLL_ERROR_MS,
  PRODUCT_IMPORT_JOB_KEY,
  LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  PRODUCT_TYPE_PRIMARY,
  dealTypeOptions,
  dealFlowStatusOptions,
  minDate,
  maxPrice,
  maxProductTitleLength,
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
import { readDealFiltersSession, writeDealFiltersSession } from './work/dealsSessionFilters'
import { useDeals } from './work/useDeals'
import { useDealsActions } from './work/useDealsActions'
import { useDealsFlow } from './work/useDealsFlow'
import { useTelegram } from './work/useTelegram'
import { useImportFlow } from './work/useImportFlow'
import { useCatalogs } from './work/useCatalogs'
import { useAccountsFlow } from './work/useAccountsFlow'
import { useProductsFlow } from './work/useProductsFlow'
import { useProductsViewState } from './work/useProductsViewState'
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
import { createDeferredCall } from './work/deferredCall'
import { useWorkSectionContexts } from './work/useWorkSectionContexts'
import WorkDashboardHero from './work/sections/WorkDashboardHero.vue'
import WorkDashboardPanel from './work/sections/WorkDashboardPanel.vue'
import WorkAnalyticsSection from './work/sections/WorkAnalyticsSection.vue'
import WorkProfileSection from './work/sections/WorkProfileSection.vue'
import WorkUsersSection from './work/sections/WorkUsersSection.vue'
import WorkAccountsSection from './work/sections/WorkAccountsSection.vue'
import WorkProductsSection from './work/sections/WorkProductsSection.vue'
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
const loadProductSlotAssignmentsDeferred = createDeferredCall('loadProductSlotAssignments')

const closeDealModal = () => closeDealModalDeferred.call()
const loadAccountsAll = (...args) => loadAccountsAllDeferred.call(...args)
const loadAccountSlotAssignments = (...args) => loadAccountSlotAssignmentsDeferred.call(...args)
const loadProductSlotAssignments = (...args) => loadProductSlotAssignmentsDeferred.call(...args)
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
const dealConfirm = reactive({
  open: false,
  title: 'Подтверждение',
  message: '',
  confirmText: 'Ок',
  cancelText: 'Отмена',
  resolver: null,
})

function requestUnsavedConfirm(message) {
  // Показывает кастомное модальное подтверждение вместо системного confirm.
  return new Promise((resolve) => {
    unsavedConfirm.open = true
    unsavedConfirm.message = message || 'Закрыть без сохранения?'
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

function requestDealConfirm({
  title = 'Подтверждение',
  message = 'Подтвердите действие',
  confirmText = 'Ок',
  cancelText = 'Отмена',
} = {}) {
  // Все подтверждения для сделок показываем в едином фирменном стиле.
  return new Promise((resolve) => {
    dealConfirm.open = true
    dealConfirm.title = title
    dealConfirm.message = message
    dealConfirm.confirmText = confirmText
    dealConfirm.cancelText = cancelText
    dealConfirm.resolver = resolve
  })
}

function answerDealConfirm(accepted) {
  const resolve = dealConfirm.resolver
  dealConfirm.open = false
  dealConfirm.title = 'Подтверждение'
  dealConfirm.message = ''
  dealConfirm.confirmText = 'Ок'
  dealConfirm.cancelText = 'Отмена'
  dealConfirm.resolver = null
  if (typeof resolve === 'function') resolve(Boolean(accepted))
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
const productSaving = createBooleanFlag(false)
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
const productError = ref(null)
const productOk = ref(null)
const productLoading = ref(false)
const productAccounts = ref([])
const productAccountsLoading = ref(false)
const productAccountsError = ref(null)
const productSlotAssignments = ref([])
const productSlotAssignmentsLoading = ref(false)
const productSlotAssignmentsError = ref(null)
const dealGameAssignmentsNew = ref([])
const dealGameAssignmentsEdit = ref([])
const dealGameAssignmentsLoadingNew = ref(false)
const dealGameAssignmentsLoadingEdit = ref(false)
const productAccountsSort = ref({ key: 'free_slots', dir: 'desc' })
const productAccountsPage = ref(1)
const productAccountsPageSize = 15
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
const productEditMode = ref('view')
const setAccountEditMode = (mode) => {
  accountEditMode.value = mode
}
const setEditAccountProductSearch = (value) => {
  editAccountProductSearch.value = value
}
const setAccountProductSearch = (value) => {
  accountProductSearch.value = value
}
const setEditAccountProductType = (value) => {
  editAccountProductType.value = value
}
const setAccountProductType = (value) => {
  accountProductType.value = value
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
const dealEditingByDealId = ref({})

// Нормализует роль из сессии, чтобы проверки прав не зависели от регистра и вариантов названия.
function normalizeRole(value) {
  return String(value || '').trim().toLowerCase()
}

// Проверяет привилегированную роль для операций со сделками (admin/owner).
function hasCompletedDealsAccess(roleValue, usernameValue) {
  const role = normalizeRole(roleValue)
  const me = String(usernameValue || '').trim().toLowerCase()
  const privilegedRoles = new Set(['admin', 'administrator', 'owner'])
  const privilegedUsers = new Set(['admin', 'owner'])
  return privilegedRoles.has(role) || privilegedUsers.has(me)
}

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
  return hasCompletedDealsAccess(auth.state.role, auth.state.user)
})

const canEditCompletedDeals = computed(() => {
  // Завершенные сделки редактируют только администратор и владелец.
  return hasCompletedDealsAccess(auth.state.role, auth.state.user)
})

const currentUserResponsibleName = computed(() => {
  const me = String(auth.state.user || '').trim().toLowerCase()
  if (!me) return ''
  const row = responsibleUsers.value.find((user) => String(user?.username || '').trim().toLowerCase() === me)
  return String(row?.name || '').trim()
})

const topBarUserName = computed(() => {
  // В шапке показываем имя пользователя, а не роль.
  const byName = String(currentUserResponsibleName.value || '').trim()
  if (byName) return byName
  return String(auth.state.user || '').trim()
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
const productsAllLoadedOnce = ref(false)

const {
  getAccountLabelById,
  getRegionLabel,
  getDomainLabel,
  getAccountStatusLabel,
  getSourceLabelById,
  getFlowStatusLabel,
  getDealProductTitleDisplay,
  getDealProductTitleTooltip,
  formatProductPlatforms,
  formatSecret,
  formatDateOnly,
  formatDateTimeMinutes,
} = useWorkFormatters({
  accountsAll,
  regions,
  domains,
  sources,
  dealFlowStatusOptions,
  maxProductTitleLength,
})

const accountProductTitles = computed(() => {
  // Собирает список названий товаров для выбранного аккаунта.
  const productMap = new Map((productsAll.value || []).map((g) => [g.product_id, g.title]))
  return (editAccount.product_ids || []).map((id) => productMap.get(id)).filter(Boolean)
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

const activeProductChips = computed(() => {
  // Формирует "чипы" активных фильтров по товарам.
  const chips = []
  if (productFilters.q) {
    chips.push({ key: 'title', label: 'Товар', value: productFilters.q })
  }
  if (productFilters.type_code) {
    const typeLabel = productFilters.type_code === PRODUCT_TYPE_PRIMARY
      ? 'Игра'
      : (productFilters.type_code === 'subscription' ? 'Подписка' : productFilters.type_code)
    chips.push({ key: 'type', label: 'Тип', value: typeLabel })
  }
  if (productFilters.platform_code) {
    const platform = platforms.value.find((p) => p.code === productFilters.platform_code)
    chips.push({ key: 'platform', label: 'Платформа', value: platform?.name ? `${platform.name} (${platform.code})` : productFilters.platform_code })
  }
  if (productFilters.region_code) {
    const region = regions.value.find((r) => r.code === productFilters.region_code)
    chips.push({ key: 'region', label: 'Регион', value: region?.name ? `${region.name} (${region.code})` : productFilters.region_code })
  }
  return chips
})

const activeAccountChips = computed(() => {
  // Формирует "чипы" активных фильтров по аккаунтам.
  const chips = []
  if (accountFilters.search_q) chips.push({ key: 'search', label: 'Поиск', value: accountFilters.search_q })
  if (accountFilters.login_q) chips.push({ key: 'login', label: 'Логин', value: accountFilters.login_q })
  if (accountFilters.product_q) chips.push({ key: 'product', label: 'Товар', value: accountFilters.product_q })
  if (accountFilters.region_q) chips.push({ key: 'region', label: 'Регион', value: accountFilters.region_q })
  if (accountFilters.status_q) chips.push({ key: 'status', label: 'Статус', value: accountFilters.status_q })
  if (accountFilters.date_from || accountFilters.date_to) {
    const from = accountFilters.date_from ? formatDateOnly(accountFilters.date_from) : '—'
    const to = accountFilters.date_to ? formatDateOnly(accountFilters.date_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  return chips
})

const isAdmin = computed(() => {
  // Для admin-вкладок принимаем оба варианта кодов роли.
  const role = normalizeRole(auth.state.role)
  return role === 'admin' || role === 'administrator'
})
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
    if (dealConfirm.open) answerDealConfirm(false)
    closePwdModal()
    closeAccountImport()
    closeProductImport()
    closeSlotImport()
    closeProductModal()
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

const normalizeWorkTab = (tab) => {
  // Нормализует вкладку из URL и отбрасывает невалидные значения.
  const raw = String(tab || '').trim().toLowerCase()
  return TAB_KEYS.includes(raw) ? raw : 'deals'
}

const toRouteTab = (tab) => {
  // Для URL сохраняем нормализованный ключ вкладки.
  return tab
}

const setActiveTab = (tab) => {
  // Переключает вкладку и синхронизирует ее с query-параметром.
  const next = normalizeWorkTab(tab)
  activeTab.value = next
  const currentRouteTab = String(route.query.tab || '')
  const nextRouteTab = toRouteTab(next)
  if (currentRouteTab !== nextRouteTab) {
    router.replace({ name: 'work', query: { ...route.query, tab: nextRouteTab } })
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

const newProductState = reactive({
  type_code: PRODUCT_TYPE_PRIMARY,
  title: '',
  short_title: '',
  link: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
  provider: '',
  billing_period: '',
  subscription_notes: '',
})

const newDeal = reactive(createNewDealState())
const newDealResponsible = ref('')
const newDealCommentOpen = ref(false)

const editDeal = reactive(createEditDealState())
const editDealResponsible = ref('')

const products = ref([])
const productsAll = ref([])
const productsTotal = ref(0)
const productsLoading = ref(false)
const editProductState = reactive({
  open: false,
  product_id: null,
  type_code: PRODUCT_TYPE_PRIMARY,
  title: '',
  short_title: '',
  link: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
  provider: '',
  billing_period: '',
  subscription_notes: '',
})
const dealFilters = reactive(createDealFiltersState())
const dealShowCompleted = ref(false)

// Восстанавливает фильтры сделок из sessionStorage для текущего пользователя.
function restoreDealFiltersFromSession() {
  const saved = readDealFiltersSession(auth.state.user)
  if (!saved?.filters) return
  dealFilters.search_q = String(saved.filters.search_q || '')
  dealFilters.customer_q = String(saved.filters.customer_q || '')
  dealFilters.responsible_q = String(saved.filters.responsible_q || '')
  dealFilters.region_q = String(saved.filters.region_q || '')
  dealFilters.status_q = String(saved.filters.status_q || '')
  dealFilters.purchase_from = String(saved.filters.purchase_from || '')
  dealFilters.purchase_to = String(saved.filters.purchase_to || '')
  dealFilters.type_q = String(saved.filters.type_q || '')
  dealShowCompleted.value = Boolean(saved.showCompleted)
}

// Применяем сохраненные фильтры при открытии экрана и смене пользователя в сессии.
restoreDealFiltersFromSession()
watch(() => auth.state.user, () => restoreDealFiltersFromSession())

watch(
  [
    () => auth.state.user,
    () => dealShowCompleted.value,
    () => dealFilters.search_q,
    () => dealFilters.customer_q,
    () => dealFilters.responsible_q,
    () => dealFilters.region_q,
    () => dealFilters.status_q,
    () => dealFilters.purchase_from,
    () => dealFilters.purchase_to,
    () => dealFilters.type_q,
  ],
  () => {
    // Сохраняем фильтры в рамках текущей сессии браузера до logout.
    writeDealFiltersSession(auth.state.user, dealFilters, dealShowCompleted.value)
  },
)
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
const accountProductSearch = ref('')
const editAccountProductSearch = ref('')
const accountProductType = ref('')
const editAccountProductType = ref('')
const accountProductsLoading = ref(false)
const activeAccountFilter = ref('')
const accountFilterDraft = reactive({
  login: '',
  product: '',
  region: '',
  status: '',
  date_from: '',
  date_to: '',
})
const editAccount = reactive(createEditAccountState())
const showProductForm = ref(false)
const showProductFilters = ref(false)
const showChatsTab = ref(false)
const showDealForm = ref(false)
const activeDealFilter = ref('')
const activeProductFilter = ref('')
const productFilterDraft = reactive({
  title: '',
  type: '',
  platform: '',
  region: '',
})
const productFilters = reactive({
  q: '',
  type_code: '',
  platform_code: '',
  region_code: '',
})
useFilterPopouts({
  activeDealFilter,
  activeProductFilter,
  activeAccountFilter,
})
const telegram = reactive(createTelegramState())
const showProductImport = ref(false)
const showAccountImport = ref(false)
const showSlotImport = ref(false)
const productImportFile = ref(null)
const accountImportFile = ref(null)
const slotImportFile = ref(null)
const slotImportLimit = ref(10)
const productImportValidated = ref(false)
const accountImportValidated = ref(false)
const slotImportValidated = ref(false)
const productImportErrors = ref([])
const accountImportErrors = ref([])
const slotImportErrors = ref([])
const productImportWarnings = ref([])
const accountImportWarnings = ref([])
const slotImportWarnings = ref([])
const productImportTotal = ref(0)
const accountImportTotal = ref(0)
const slotImportTotal = ref(0)
const productImportLoading = ref(false)
const accountImportLoading = ref(false)
const slotImportLoading = ref(false)
const productImportMessage = ref('')
const accountImportMessage = ref('')
const slotImportMessage = ref('')
const slotImportError = ref('')
const slotImportAction = ref('')
const slotImportProgress = reactive({ current: 0, total: 0, phase: '' })
const slotImportJobId = ref('')
const slotImportStats = ref(null)
const productImportAction = ref('')
const accountImportAction = ref('')
const productImportStats = ref(null)
const accountImportStats = ref(null)
const productImportProgress = reactive({ current: 0, total: 0, phase: '' })
const accountImportProgress = reactive({ current: 0, total: 0, phase: '' })
const productImportJobId = ref('')
const accountImportJobId = ref('')
const importDetailsRef = ref(null)
const accountImportDetailsRef = ref(null)
const showDomainForm = ref(false)
const showSourceForm = ref(false)
const showPlatformForm = ref(false)
const showRegionForm = ref(false)
const accountFilters = reactive(createAccountFiltersState())
const accountSort = ref('login_asc')
const productsSort = ref({ key: 'title', dir: 'asc' })
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
const { createDeal, createDealDraft, updateDeal, updateDealDraft, deleteDeal, markDealCompleted, markDealReturned } = useDealsActions({
  auth,
  apiPost,
  apiPut,
  apiDelete,
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
  requestDealConfirm,
})
const usersSort = ref({ key: 'created_at', dir: 'desc' })
const domainsSortAsc = ref(true)
const sourcesSort = ref({ key: 'code', dir: 'asc' })
const platformsSort = ref({ key: 'code', dir: 'asc' })
const regionsSort = ref({ key: 'code', dir: 'asc' })
const productsPage = ref(1)
const productsPageInput = ref(1)
const productsPageSize = ref(20)

const newDealProductSearch = ref('')
const editDealProductSearch = ref('')
const dealAccountsForProductNew = ref([])
const dealAccountsForProductEdit = ref([])
const dealAccountsForProductLoading = ref(false)
const quickNewProduct = reactive({ title: '', platform_codes: [] })
const quickEditProduct = reactive({ title: '', platform_codes: [] })
const quickNewProductLoading = ref(false)
const quickEditProductLoading = ref(false)
const quickNewProductError = ref('')
const quickEditProductError = ref('')
const quickNewAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickEditAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickNewAccountLoading = ref(false)
const quickEditAccountLoading = ref(false)
const quickNewAccountError = ref('')
const quickEditAccountError = ref('')
const dealQuickAccountBusy = computed(() => quickNewAccountLoading.value || quickEditAccountLoading.value)
const dealQuickProductBusy = computed(() => quickNewProductLoading.value || quickEditProductLoading.value)
const {
  filteredNewDealProducts,
  filteredEditDealProducts,
  newDealProductNoMatches,
  editDealProductNoMatches,
  dealAccountsForNew,
  dealAccountsForEdit,
  dealProductAssignmentsForSelectedSlotNew,
  dealProductAssignmentsForSelectedSlotEdit,
  hasAnyProductAssignmentsNew,
  hasAnyProductAssignmentsEdit,
} = useDealsViewState({
  productsAll,
  newDeal,
  editDeal,
  newDealProductSearch,
  editDealProductSearch,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
})

const {
  sortedAccounts,
  filteredAccountProducts,
  filteredEditAccountProducts,
} = useAccountsDerivedState({
  accounts,
  productsAll,
  accountProductSearch,
  editAccountProductSearch,
  accountProductType,
  editAccountProductType,
})

const getDealTypeName = (code) => dealTypeOptions.find((t) => t.code === code)?.name || code || '—'
const maxDate = getMaxDate()

const {
  getSlotTypeLabel,
  formatAccountSlotStatusLine,
  getSortedSlotStatus,
  sortedAccountSlotAssignments,
  getAccountSlotStatusList,
  getProductLabelById,
  isSlotTypeSupportedForProduct,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  isDealSlotTypeUnsupported,
  hasFreeDealSlots,
} = useSlotHelpers({
  slotTypes,
  productsAll,
  newDeal,
  editDeal,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  hasAnyProductAssignmentsNew,
  hasAnyProductAssignmentsEdit,
  accountSlotAssignments,
  accountSlotAssignmentsSort,
})

const formatAccountProductsLine = (account) => {
  const list = Array.isArray(account?.product_titles) ? account.product_titles : []
  if (!list.length) return '—'
  return list.join(', ')
}

const {
  setProductsPageSizeFromEvent,
  setProductsPageInputFromEvent,
  getAccountSortClass,
  getProductsSortClass,
  getDealSortClass,
  getDomainsSortClass,
  getKeyedSortClass,
  getSlotAssignmentStatus,
  getNotesRows,
  getCompactNotesRows,
} = useWorkUiHelpers({
  productsPageSize,
  productsPageInput,
  accountSort,
  productsSort,
  dealSort,
  domainsSortAsc,
})

const editProduct = editProductState
const newProduct = newProductState

const {
  openProductAccounts,
  openCreateGameProductModal,
  openCreateSubscriptionProductModal,
  openCreateProductModal,
  closeProductModal,
  goToAccount,
  loadProducts,
  loadProductsAll,
  createProduct,
  updateProduct,
  toggleProductEditMode,
  archiveProduct,
} = useProductsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showProductForm,
  productEditMode,
  editProduct,
  newProduct,
  productError,
  productOk,
  productsLoading,
  productLoading,
  productSaving,
  products,
  productsAll,
  productsTotal,
  productsSort,
  productsPage,
  productsPageSize,
  productFilters,
  productFilterDraft,
  accountFilters,
  productAccounts,
  productAccountsLoading,
  productAccountsError,
  productAccountsPage,
  productSlotAssignments,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  loadProductSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  requestDealConfirm,
})

const {
  getReserveSecrets,
  loadAccounts,
  loadAccountsAll: loadAccountsAllFromAccountsFlow,
  startEditAccount,
  toggleAccountEditMode,
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
  accountProductSearch,
  editAccountProductSearch,
  accountProductType,
  editAccountProductType,
  accountProductsLoading,
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
  requestDealConfirm,
  showDealWarning,
})

loadAccountsAllDeferred.set(loadAccountsAllFromAccountsFlow)

// Логика формы сделки: быстрые создания, загрузки связей, слоты.
const {
  createQuickProduct,
  createQuickAccount,
  clearNewDealProduct,
  clearEditDealProduct,
  loadDealAccountsForProduct,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealProductAssignments,
  loadDealSlotAvailability,
  releaseSlotFromDeal,
} = useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  isSlotTypeSupportedForProduct,
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
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealAccountsForProductLoading,
  accountSlotReleaseLoading,
  dealSlotAutoAssign,
  dealError,
  quickNewProduct,
  quickEditProduct,
  quickNewProductLoading,
  quickEditProductLoading,
  quickNewProductError,
  quickEditProductError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountLoading,
  quickEditAccountLoading,
  quickNewAccountError,
  quickEditAccountError,
  newDealProductSearch,
  editDealProductSearch,
  loadProductsAll,
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
  newDealProductSearch,
  editDealProductSearch,
  quickNewProduct,
  quickEditProduct,
  quickNewProductError,
  quickEditProductError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountError,
  quickEditAccountError,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  nextTick,
  loadDealSlotAvailability,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  currentResponsibleName: currentUserResponsibleName,
  canEditCompletedDeal: canEditCompletedDeals,
  showDealWarning,
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
  userRoleName: topBarUserName,
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

// Импорт/валидация/отмена для игр, аккаунтов и слотов.
const {
  openProductImport,
  openAccountImport,
  openSlotImport,
  closeSlotImport,
  closeProductImport,
  closeAccountImport,
  stopProductImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  scrollToImportDetails,
  scrollToAccountImportDetails,
  onProductImportFile,
  onAccountImportFile,
  onSlotImportFile,
  downloadProductTemplate,
  downloadAccountTemplate,
  downloadProductImportReport,
  validateProductImport,
  downloadAccountImportReport,
  validateAccountImport,
  cleanSlotImport,
  validateSlotImport,
  uploadSlotImport,
  downloadSlotImportReport,
  cancelSlotImport,
  uploadProductImport,
  uploadAccountImport,
  cancelProductImport,
  cancelAccountImport,
} = useImportFlow({
  auth,
  API_BASE,
  apiGet,
  apiPost,
  apiPostForm,
  apiGetFile,
  mapApiError,
  PRODUCT_IMPORT_JOB_KEY,
  LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  closeAllModals,
  resetModalPos,
  showProductImport,
  showAccountImport,
  showSlotImport,
  productImportFile,
  accountImportFile,
  slotImportFile,
  slotImportLimit,
  productImportValidated,
  accountImportValidated,
  slotImportValidated,
  productImportErrors,
  accountImportErrors,
  slotImportErrors,
  productImportWarnings,
  accountImportWarnings,
  slotImportWarnings,
  productImportTotal,
  accountImportTotal,
  slotImportTotal,
  productImportLoading,
  accountImportLoading,
  slotImportLoading,
  productImportMessage,
  accountImportMessage,
  slotImportMessage,
  slotImportError,
  slotImportAction,
  slotImportProgress,
  slotImportJobId,
  slotImportStats,
  productImportAction,
  accountImportAction,
  productImportStats,
  accountImportStats,
  productImportProgress,
  accountImportProgress,
  productImportJobId,
  accountImportJobId,
  importDetailsRef,
  accountImportDetailsRef,
  loadProducts,
  loadProductsAll,
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
  productsTotalPages,
  sortedProducts,
  pagedProducts,
  productAccountsTotalPages,
  pagedProductAccounts,
} = useProductsViewState({
  products,
  productsTotal,
  productsPage,
  productsPageInput,
  productsPageSize,
  loadProducts,
  productAccounts,
  productAccountsSort,
  productAccountsPage,
  productAccountsPageSize,
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
  toggleProductsSort,
  toggleUsersSort,
  toggleDomainsSort,
  toggleSourcesSort,
  togglePlatformsSort,
  toggleRegionsSort,
  setProductsPage,
  jumpProductsPage,
  prevProductsPage,
  nextProductsPage,
  setAccountsPage,
  jumpAccountsPage,
  prevAccountsPage,
  nextAccountsPage,
  resetDealFilter,
  validateDealRange,
  dealFilterErrors,
  resetProductFilter,
  openProductFilter,
  applyProductFilter,
  resetAccountFilter,
  openAccountFilter,
  applyAccountFilter,
} = useWorkFilters({
  accountSort,
  accountsPage,
  accountsPageInput,
  accountsTotalPages,
  loadAccounts,
  productsSort,
  productsPage,
  productsPageInput,
  productsTotalPages,
  loadProducts,
  usersSort,
  domainsSortAsc,
  sourcesSort,
  platformsSort,
  regionsSort,
  activeDealFilter,
  dealFilters,
  loadDeals,
  activeProductFilter,
  productFilters,
  productFilterDraft,
  activeAccountFilter,
  accountFilters,
  accountFilterDraft,
})

// UI-действия экрана: поиск, открытие модалок, подгрузки деталей.
const {
  openAccountFromProduct,
  applyDealSearch,
  applyAccountSearch,
  applyProductSearch,
  syncNewDealProductSearch,
  syncEditDealProductSearch,
  onNewDealProductSearch,
  onEditDealProductSearch,
  loadAccountSlotAssignments: loadAccountSlotAssignmentsFromActions,
  loadProductSlotAssignments: loadProductSlotAssignmentsFromActions,
  releaseSlotAssignment,
  sortProductAccounts,
  nextProductAccountsPage,
  prevProductAccountsPage,
} = useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
  loadDeals,
  loadAccounts,
  loadProducts,
  accountsPage,
  accountsPageInput,
  productsPage,
  productsPageInput,
  newDeal,
  editDeal,
  newDealProductSearch,
  editDealProductSearch,
  quickNewProduct,
  quickEditProduct,
  quickNewProductError,
  quickEditProductError,
  accountSlotAssignments,
  accountSlotAssignmentsLoading,
  accountSlotAssignmentsError,
  productSlotAssignments,
  productSlotAssignmentsLoading,
  productSlotAssignmentsError,
  accountSlotReleaseLoading,
  editAccount,
  showDealForm,
  dealError,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealAccountsForProduct,
  loadDealProductAssignments,
  productAccountsSort,
  productAccountsPage,
  productAccountsTotalPages,
  closeProductModal,
  goToAccount,
})

loadAccountSlotAssignmentsDeferred.set(loadAccountSlotAssignmentsFromActions)
loadProductSlotAssignmentsDeferred.set(loadProductSlotAssignmentsFromActions)

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
  formatAccountProductsLine,
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
  toggleAccountEditMode,
  updateAccount,
  createAccount,
  deleteAccount,
  accountProductsLoading,
  getDomainLabel,
  domains,
  getRegionLabel,
  regions,
  getAccountStatusLabel,
  maxDate,
  accountProductTitles,
  editAccountProductSearch,
  setEditAccountProductSearch,
  editAccountProductType,
  setEditAccountProductType,
  filteredEditAccountProducts,
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
  getDealProductTitleTooltip,
  getDealProductTitleDisplay,
  formatDate: formatDateTimeMinutes,
  accountsError,
  accountsOk,
  newAccount,
  accountProductSearch,
  setAccountProductSearch,
  accountProductType,
  setAccountProductType,
  filteredAccountProducts,
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
  productEditorModalCtx,
  dealsSectionCtx,
  dealEditorModalShellCtx,
  dealEditorModalBodyCtx,
  dealEditorFormCtx,
  catalogsSectionCtx,
} = useWorkSectionContexts({
  editProduct,
  showProductForm,
  closeProductModal,
  modalRef,
  modalStyle,
  startModalDrag,
  productEditMode,
  updateProduct,
  toggleProductEditMode,
  productLoading,
  createProduct,
  archiveProduct,
  platforms,
  getRegionLabel,
  regions,
  productAccountsError,
  productAccountsLoading,
  productAccounts,
  productAccountsSort,
  pagedProductAccounts,
  sortProductAccounts,
  openAccountFromProduct,
  productAccountsTotalPages,
  productAccountsPage,
  prevProductAccountsPage,
  nextProductAccountsPage,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  productSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  productError,
  productOk,
  newProduct,
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
  dealEditingByDealId,
  currentUsername: computed(() => String(auth.state.user || '')),
  showDealWarning,
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
  markDealReturned,
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
  canEditCompletedDeal: canEditCompletedDeals,
  toggleDealEditMode,
  updateDeal,
  updateDealDraft,
  deleteDeal,
  dealLoading,
  dealBackgroundSync,
  createDeal,
  createDealDraft,
  dealQuickAccountBusy,
  dealQuickProductBusy,
  getDealTypeName,
  dealAccountsForProductLoading,
  isDealSlotTypeUnsupported,
  dealAccountsForEdit,
  dealSlotAvailabilityLoadingEdit,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  getAccountLabelById,
  hasFreeDealSlots,
  hasAnyProductAssignmentsEdit,
  dealGameAssignmentsLoadingEdit,
  dealProductAssignmentsForSelectedSlotEdit,
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
  editDealProductSearch,
  onEditDealProductSearch,
  filteredEditDealProducts,
  syncEditDealProductSearch,
  getProductLabelById,
  editDealProductNoMatches,
  clearEditDealProduct,
  quickEditProduct,
  quickEditProductLoading,
  createQuickProduct,
  quickEditProductError,
  getNotesRows,
  dealError,
  dealOk,
  newDeal,
  responsibleUserOptions,
  newDealResponsible,
  editDealResponsible,
  newDealProductSearch,
  onNewDealProductSearch,
  filteredNewDealProducts,
  newDealProductNoMatches,
  syncNewDealProductSearch,
  clearNewDealProduct,
  quickNewProduct,
  quickNewProductLoading,
  quickNewProductError,
  dealSlotAvailabilityLoadingNew,
  dealAccountsForNew,
  hasAnyProductAssignmentsNew,
  dealGameAssignmentsLoadingNew,
  dealProductAssignmentsForSelectedSlotNew,
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

// Контекст вкладки товаров: фильтры, таблица, пагинация, импорт и модалка.
const productsSectionCtx = asCtx({
  productFilters,
  applyProductSearch,
  openCreateGameProductModal,
  openCreateSubscriptionProductModal,
  openCreateProductModal,
  loadProducts,
  productsLoading,
  activeProductChips,
  resetProductFilter,
  openProductImport,
  closeProductImport,
  showProductImport,
  downloadProductTemplate,
  validateProductImport,
  uploadProductImport,
  cancelProductImport,
  scrollToImportDetails,
  onProductImportFile,
  importDetailsRef,
  downloadProductImportReport,
  modalRef,
  modalStyle,
  startModalDrag,
  productImportLoading,
  productImportFile,
  productImportAction,
  productImportValidated,
  productImportJobId,
  productImportProgress,
  productImportMessage,
  productImportErrors,
  productImportWarnings,
  productImportStats,
  sortedProducts,
  pagedProducts,
  activeProductFilter,
  productFilterDraft,
  openProductFilter,
  toggleProductsSort,
  getProductsSortClass,
  applyProductFilter,
  formatProductPlatforms,
  openProductAccounts,
  productsTotal,
  productsPageSize,
  setProductsPageSizeFromEvent,
  productsPage,
  setProductsPage,
  prevProductsPage,
  productsPageInput,
  setProductsPageInputFromEvent,
  productsTotalPages,
  jumpProductsPage,
  nextProductsPage,
  productEditorModalCtx,
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

// Контекст вкладки профиля: смена пароля и встраивание списка пользователей.
const profileSectionCtx = asCtx({
  isAdmin,
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
  usersSectionCtx,
})

useWorkLifecycle({
  auth,
  router,
  route,
  isAdmin,
  loadUsers,
  stopGameImportStatusPolling: stopProductImportStatusPolling,
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
  showProductForm,
  showProductFilters,
  showDealForm,
  showAccountFilters,
  activeProductFilter,
  activeAccountFilter,
  editProduct,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  slotTypesLoadedOnce,
  accountsAllLoadedOnce,
  productsAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  products,
  productsAll,
  accountsAll,
  productsPage,
  accountsPage,
  checkApi,
  loadUsers,
  loadCatalogs,
  loadDomains,
  loadSources,
  loadSlotTypes,
  loadProducts,
  loadProductsAll,
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
  normalizeWorkTab,
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
  loadDealAccountsForProduct,
  loadDealProductAssignments,
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
  editingByDealId: dealEditingByDealId,
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
