<template>
  <div class="work-page page">
    <div class="shell">
      <WorkTopBar :ctx="topBarCtx" />

      <WorkDashboardHero v-if="canViewDashboardSection && activeTab === 'dashboard'" :ctx="dashboardSectionCtx" />

      <main class="main">
        <WorkDashboardPanel
          v-if="canViewDashboardSection && activeTab === 'dashboard'"
          :ctx="dashboardSectionCtx"
        />

        <WorkProfileSection
          v-if="canViewProfileSection && activeTab === 'profile'"
          :ctx="profileSectionCtx"
        />

        <WorkAccountsSection
          v-if="canViewAccountsSection && activeTab === 'accounts'"
          :ctx="accountsSectionCtx"
        />


        <WorkProductsSection
          v-if="canViewProductsSection && activeTab === 'products'"
          :ctx="productsSectionCtx"
        />

        <WorkNsGiftSection
          v-if="canViewNsGiftSection && activeTab === 'ns-gift'"
          :ctx="nsGiftSectionCtx"
        />


        <WorkTelegramSection
          v-if="canViewTelegramSection && activeTab === 'telegram'"
          :ctx="telegramSectionCtx"
        />


        <WorkDealsArea
          v-if="canViewDealsSection && activeTab === 'deals'"
          :ctx="dealsAreaCtx"
        />

        <WorkCatalogsSection
          v-if="canViewCatalogsSection && activeTab === 'catalogs'"
          :ctx="catalogsSectionCtx"
        />

        <WorkAnalyticsSection
          v-if="canViewAnalyticsSection && activeTab === 'analytics'"
          :ctx="analyticsSectionCtx"
        />

        <WorkFinanceSection
          v-if="canViewFinanceSection && activeTab === 'finance'"
          :ctx="financeSectionCtx"
        />

        <WorkUsersSection
          v-if="canViewUsersSection && activeTab === 'users'"
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
      <div
        v-if="dealConfirm.open"
        :class="[
          'work-page work-modal-root modal-backdrop unsaved-confirm deal-confirm',
          { 'deal-confirm--force-duplicate': isForceDuplicateDealConfirm },
        ]"
        @click.self="answerDealConfirm(false)"
      >
        <div class="modal modal--auto unsaved-confirm__modal deal-confirm__modal">
          <div class="panel__head panel__head--tight unsaved-confirm__head">
            <h3 class="unsaved-confirm__title">{{ dealConfirm.title }}</h3>
          </div>
          <div class="modal__body">
            <p class="muted unsaved-confirm__text deal-confirm__text">{{ dealConfirm.message }}</p>
            <div class="toolbar-actions unsaved-confirm__actions deal-confirm__actions">
              <button class="ghost deal-confirm__btn" type="button" @click="answerDealConfirm(false)">{{ dealConfirm.cancelText }}</button>
              <button class="btn btn--danger deal-confirm__btn deal-confirm__btn--confirm" type="button" @click="answerDealConfirm(true)">{{ dealConfirm.confirmText }}</button>
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
import { useFinanceReports } from './work/useFinanceReports'
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
import { useManagersLoad } from './work/useManagersLoad'
import { useWorkActions } from './work/useWorkActions'
import { useWorkUiHelpers } from './work/useWorkUiHelpers'
import { createDeferredCall } from './work/deferredCall'
import { useWorkSectionContexts } from './work/useWorkSectionContexts'
import WorkDashboardHero from './work/sections/WorkDashboardHero.vue'
import WorkDashboardPanel from './work/sections/WorkDashboardPanel.vue'
import WorkAnalyticsSection from './work/sections/WorkAnalyticsSection.vue'
import WorkFinanceSection from './work/sections/WorkFinanceSection.vue'
import WorkProfileSection from './work/sections/WorkProfileSection.vue'
import WorkUsersSection from './work/sections/WorkUsersSection.vue'
import WorkAccountsSection from './work/sections/WorkAccountsSection.vue'
import WorkProductsSection from './work/sections/WorkProductsSection.vue'
import WorkDealsArea from './work/sections/WorkDealsArea.vue'
import WorkCatalogsSection from './work/sections/WorkCatalogsSection.vue'
import WorkTelegramSection from './work/sections/WorkTelegramSection.vue'
import WorkTopBar from './work/sections/WorkTopBar.vue'
import WorkNsGiftSection from './work/sections/WorkNsGiftSection.vue'
import './work/styles/work-bundle.css'

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

const isForceDuplicateDealConfirm = computed(() => {
  // Выделяем confirm принудительного дубля отдельным классом, чтобы оформить его более читаемо.
  const title = String(dealConfirm.title || '').trim().toLowerCase()
  const confirmText = String(dealConfirm.confirmText || '').trim().toLowerCase()
  return title.includes('принудительный дубль') || confirmText.includes('снять и продолжить')
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
const messengers = ref([])
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
const productAccountOptions = ref([])
const productSlotAssignments = ref([])
const productSlotAssignmentsLoading = ref(false)
const productSlotAssignmentsError = ref(null)
const productSubscriptionTerms = ref([])
const productSubscriptionTermsLoading = ref(false)
const productSubscriptionTermsError = ref(null)
const dealGameAssignmentsNew = ref([])
const dealGameAssignmentsEdit = ref([])
const dealGameAssignmentsLoadingNew = ref(false)
const dealGameAssignmentsLoadingEdit = ref(false)
const productAccountsSort = ref({ key: 'deal_date', dir: 'desc' })
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
const dealsRealtimeAnimationTick = ref(0)
let managersRealtimeRefreshTimer = null
let managersRealtimeRefreshQueued = false
let managersRealtimeRefreshLastAt = 0
const MANAGERS_REALTIME_REFRESH_MIN_MS = 1000

// Нормализует роль из сессии, чтобы проверки прав не зависели от регистра и вариантов названия.
function normalizeRole(value) {
  return String(value || '').trim().toLowerCase()
}

// Проверяет привилегированную роль для операций со сделками (admin/owner).
function hasCompletedDealsAccess(roleValue, usernameValue) {
  const role = normalizeRole(roleValue)
  const me = String(usernameValue || '').trim().toLowerCase()
  const privilegedRoles = new Set(['admin', 'owner'])
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
  // В шапке показываем человекочитаемое имя пользователя, а логин используем как fallback.
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

// Выполняет фактическое обновление блока менеджеров и сбрасывает внутренние флаги coalescing.
function runManagersRealtimeRefresh() {
  managersRealtimeRefreshQueued = false
  managersRealtimeRefreshTimer = null
  managersRealtimeRefreshLastAt = Date.now()
  refreshManagersWorkload()
}

// Перезагружает блок менеджеров по WS-событиям сделок не чаще заданного интервала.
function scheduleManagersRealtimeRefresh() {
  managersRealtimeRefreshQueued = true
  const elapsed = Date.now() - managersRealtimeRefreshLastAt
  if (!managersRealtimeRefreshTimer && elapsed >= MANAGERS_REALTIME_REFRESH_MIN_MS) {
    runManagersRealtimeRefresh()
    return
  }
  if (managersRealtimeRefreshTimer) return
  const waitMs = Math.max(50, MANAGERS_REALTIME_REFRESH_MIN_MS - elapsed)
  managersRealtimeRefreshTimer = setTimeout(() => {
    if (!managersRealtimeRefreshQueued) {
      managersRealtimeRefreshTimer = null
      return
    }
    runManagersRealtimeRefresh()
  }, waitMs)
}

// Реагируем только на события, которые меняют состав/статус сделок.
function handleDealsRealtimeEvent(payload) {
  const eventType = String(payload?.event || '').trim().toLowerCase()
  if (eventType !== 'deal_created' && eventType !== 'deal_updated' && eventType !== 'deal_deleted') return
  scheduleManagersRealtimeRefresh()
}

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

const responsibleNameByUsername = computed(() => {
  // Карта username -> name для UI, чтобы в блокировках показывать человекочитаемое имя.
  const map = {}
  for (const user of responsibleUsers.value) {
    const username = String(user?.username || '').trim().toLowerCase()
    const name = String(user?.name || '').trim()
    if (!username) continue
    map[username] = name || String(user?.username || '').trim()
  }
  return map
})
const catalogsLoadedOnce = ref(false)
const domainsLoadedOnce = ref(false)
const sourcesLoadedOnce = ref(false)
const messengersLoadedOnce = ref(false)
const slotTypesLoadedOnce = ref(false)
const productsAllLoadedOnce = ref(false)

const {
  getAccountLabelById,
  getRegionLabel,
  getDomainLabel,
  getAccountStatusLabel,
  getSourceLabelById,
  getMessengerLabelById,
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
  messengers,
  dealFlowStatusOptions,
  maxProductTitleLength,
})

const accountProductTitles = computed(() => {
  // В карточке аккаунта приоритет у названий из /accounts/{id}/products:
  // для подписок там уже добавлен срок ("Название до DD/MM/YY").
  const apiTitles = Array.isArray(editAccount.product_titles) ? editAccount.product_titles.filter(Boolean) : []
  if (apiTitles.length) return apiTitles
  // Fallback нужен только когда API-список еще не догрузился.
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
  // Для административных разделов приравниваем владельца к админу.
  const role = normalizeRole(auth.state.role)
  return role === 'admin' || role === 'owner'
})
const canManageRolePermissions = computed(() => {
  // Ролевой моделью управляют владелец и администратор.
  const role = normalizeRole(auth.state.role)
  const username = String(auth.state.user || '').trim().toLowerCase()
  return role === 'admin' || role === 'owner' || username === 'owner'
})
const mustPrefillDealsResponsible = computed(() => {
  const role = String(auth.state.role || '').trim().toLowerCase()
  return role === 'manager' || role === 'operator'
})
const canToggleAccountDeactivation = computed(() => {
  // Оператор видит статус, но не может менять признак деактивации.
  return normalizeRole(auth.state.role) !== 'operator'
})
const showUsersTab = false
const showDashboard = true
const showRolePermissionsPanel = computed(() => canManageRolePermissions.value)

const roleSectionDefaults = {
  privileged_only: new Set(['analytics', 'catalogs', 'finance', 'users', 'dashboard']),
}

const mySectionPermissionsMap = ref({})
const rolePermissionsRoles = ref([])
const rolePermissionsRoleCode = ref('')
const rolePermissionsItems = ref([])
const rolePermissionsLoading = ref(false)
const rolePermissionsSaving = ref(false)
const rolePermissionsError = ref('')
const rolePermissionsOk = ref('')

// Возвращает дефолтную видимость секции, если для роли еще нет явной записи в таблице прав.
function defaultSectionVisibilityByRole(sectionCode, roleCode) {
  const role = normalizeRole(roleCode)
  if (role === 'admin' || role === 'owner') return true
  return !roleSectionDefaults.privileged_only.has(String(sectionCode || '').trim())
}

// Проверяет доступ к разделу с учетом явной настройки роли и fallback по умолчанию.
function canViewSection(sectionCode) {
  const code = String(sectionCode || '').trim()
  if (!code) return false
  const map = mySectionPermissionsMap.value || {}
  if (Object.prototype.hasOwnProperty.call(map, code)) {
    return Boolean(map[code])
  }
  return defaultSectionVisibilityByRole(code, auth.state.role)
}

const canViewDealsSection = computed(() => canViewSection('deals'))
const canViewAccountsSection = computed(() => canViewSection('accounts'))
const canViewProductsSection = computed(() => canViewSection('products'))
const canViewNsGiftSection = computed(() => canViewSection('ns-gift'))
const canViewTelegramSection = computed(() => canViewSection('telegram'))
const canViewAnalyticsSection = computed(() => canViewSection('analytics'))
const canViewCatalogsSection = computed(() => canViewSection('catalogs'))
const canViewFinanceSection = computed(() => canViewSection('finance'))
const canViewUsersSection = computed(() => canViewSection('users'))
const canViewUsersTab = computed(() => showUsersTab && canViewUsersSection.value)
const canViewProfileSection = computed(() => canViewSection('profile'))
const canViewDashboardSection = computed(() => canViewSection('dashboard'))

// Берем предзагруженные права из auth-store, чтобы не показывать лишние вкладки до первого запроса.
mySectionPermissionsMap.value = {
  ...(auth.state.sections && typeof auth.state.sections === 'object' ? auth.state.sections : {}),
}

// Возвращает список вкладок, которые реально доступны пользователю в текущем UI.
function getAllowedTabs() {
  const tabs = []
  if (canViewDealsSection.value) tabs.push('deals')
  if (canViewAccountsSection.value) tabs.push('accounts')
  if (canViewProductsSection.value) tabs.push('products')
  if (canViewNsGiftSection.value) tabs.push('ns-gift')
  if (canViewTelegramSection.value) tabs.push('telegram')
  if (canViewAnalyticsSection.value) tabs.push('analytics')
  if (canViewCatalogsSection.value) tabs.push('catalogs')
  if (canViewFinanceSection.value) tabs.push('finance')
  if (canViewUsersTab.value) tabs.push('users')
  if (canViewProfileSection.value) tabs.push('profile')
  if (canViewDashboardSection.value) tabs.push('dashboard')
  return tabs
}

// Гарантирует, что активная вкладка всегда входит в доступные по текущей ролевой модели.
function ensureAllowedActiveTab() {
  const allowed = getAllowedTabs()
  if (!allowed.length) return
  if (allowed.includes(activeTab.value)) return
  setActiveTab(allowed[0])
}

// Загружает права для текущего пользователя и строит карту section_code -> can_view.
async function loadMySectionPermissions() {
  if (!auth.state.token) {
    mySectionPermissionsMap.value = {}
    return
  }
  // Если store умеет подгружать права, используем его как единый источник для login/work.
  if (typeof auth.loadMySections === 'function') {
    const loaded = await auth.loadMySections()
    mySectionPermissionsMap.value = {
      ...(loaded && typeof loaded === 'object' ? loaded : {}),
    }
    return
  }
  // Fallback для совместимости со старым store без метода loadMySections.
  mySectionPermissionsMap.value = {
    ...(auth.state.sections && typeof auth.state.sections === 'object' ? auth.state.sections : {}),
  }
}

// Загружает список ролей для формы управления ролевой моделью в профиле.
async function loadRolePermissionsRoles() {
  if (!showRolePermissionsPanel.value || !auth.state.token) {
    rolePermissionsRoles.value = []
    return
  }
  try {
    const data = await apiGet('/user-roles', { token: auth.state.token })
    rolePermissionsRoles.value = Array.isArray(data) ? data : []
    if (!rolePermissionsRoleCode.value) {
      const roleCode = String(auth.state.role || '').trim().toLowerCase()
      const firstRole = rolePermissionsRoles.value[0]?.code || ''
      const hasCurrentRole = rolePermissionsRoles.value.some((item) => String(item?.code || '').trim().toLowerCase() === roleCode)
      // Если роль из токена отсутствует в списке, безопасно переключаемся на первую доступную.
      rolePermissionsRoleCode.value = hasCurrentRole ? roleCode : firstRole
    }
  } catch (e) {
    rolePermissionsError.value = mapApiError(e?.message)
  }
}

// Загружает права выбранной роли для редактирования в профиле.
async function loadRolePermissionsByRole(roleCode) {
  const code = String(roleCode || '').trim()
  if (!showRolePermissionsPanel.value || !code || !auth.state.token) {
    rolePermissionsItems.value = []
    return
  }
  rolePermissionsLoading.value = true
  rolePermissionsError.value = ''
  try {
    const res = await apiGet(`/rbac/roles/${encodeURIComponent(code)}/sections`, { token: auth.state.token })
    rolePermissionsItems.value = Array.isArray(res?.items)
      ? res.items.map((item) => ({
          section_code: String(item?.section_code || ''),
          section_name: String(item?.section_name || ''),
          can_view: Boolean(item?.can_view),
        }))
      : []
  } catch (e) {
    rolePermissionsItems.value = []
    rolePermissionsError.value = mapApiError(e?.message)
  } finally {
    rolePermissionsLoading.value = false
  }
}

// Меняет активную роль в форме ролевой модели и перезагружает настройки.
function setRolePermissionsRoleCode(value) {
  rolePermissionsRoleCode.value = String(value || '').trim()
  if (rolePermissionsRoleCode.value) {
    loadRolePermissionsByRole(rolePermissionsRoleCode.value)
  }
}

// Обновляет локальный чекбокс видимости раздела в списке прав выбранной роли.
function setRolePermissionItem(sectionCode, canView) {
  const code = String(sectionCode || '').trim()
  if (!code) return
  rolePermissionsItems.value = rolePermissionsItems.value.map((item) => {
    if (item.section_code !== code) return item
    return { ...item, can_view: Boolean(canView) }
  })
}

// Сохраняет права выбранной роли и при необходимости обновляет права текущего пользователя.
async function saveRolePermissions() {
  const code = String(rolePermissionsRoleCode.value || '').trim()
  if (!showRolePermissionsPanel.value || !code) return
  rolePermissionsSaving.value = true
  rolePermissionsError.value = ''
  rolePermissionsOk.value = ''
  try {
    const payload = {
      items: rolePermissionsItems.value.map((item) => ({
        section_code: String(item.section_code || ''),
        can_view: Boolean(item.can_view),
      })),
    }
    const res = await apiPut(`/rbac/roles/${encodeURIComponent(code)}/sections`, payload, { token: auth.state.token })
    const savedItems = Array.isArray(res?.items) ? res.items : []
    rolePermissionsItems.value = savedItems.map((item) => ({
      section_code: String(item?.section_code || ''),
      section_name: String(item?.section_name || ''),
      can_view: Boolean(item?.can_view),
    }))
    rolePermissionsOk.value = 'Права роли сохранены'
    if (normalizeRole(code) === normalizeRole(auth.state.role)) {
      await loadMySectionPermissions()
      ensureAllowedActiveTab()
    }
  } catch (e) {
    rolePermissionsError.value = mapApiError(e?.message)
  } finally {
    rolePermissionsSaving.value = false
  }
}

// Подгружает данные формы доступов перед показом панели, чтобы пользователь не видел "пустой экран".
async function ensureRolePermissionsFormDataLoaded() {
  if (!showRolePermissionsPanel.value || !auth.state.token) return
  rolePermissionsError.value = ''
  if (!rolePermissionsRoles.value.length) {
    await loadRolePermissionsRoles()
  }
  if (rolePermissionsRoleCode.value && !rolePermissionsItems.value.length) {
    await loadRolePermissionsByRole(rolePermissionsRoleCode.value)
  }
}

const dealModalTitle = computed(() => {
  if (showDealForm.value) {
    const dealKind = newDeal.deal_type_code === 'sale' ? 'УСЛУГА' : 'ШЕРИНГ'
    return `НОВАЯ СДЕЛКА - ${dealKind}`
  }
  if (!editDeal.open) return 'СДЕЛКА'
  const dealKind = editDeal.deal_type_code === 'sale' ? 'УСЛУГА' : 'ШЕРИНГ'
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
  name: '',
  role_code: 'manager',
})

const userFormMode = ref('create')
const editUser = reactive({
  username: '',
  name: '',
  role_code: 'manager',
  created_at: '',
})
const editUserInitial = ref({ username: '', name: '', role_code: 'manager', created_at: '' })

const pwdForm = reactive({
  current: '',
  next: '',
  next2: '',
})

const activeTab = ref('deals')

const normalizeWorkTab = (tab) => {
  // Нормализует вкладку из URL и отбрасывает невалидные значения.
  const raw = String(tab || '').trim().toLowerCase()
  if (!TAB_KEYS.includes(raw)) return getAllowedTabs()[0] || 'deals'
  return raw
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
  () => auth.state.token,
  async (token) => {
    // После входа подгружаем права секций и держим активную вкладку в допустимом диапазоне.
    if (!token) {
      mySectionPermissionsMap.value = {}
      rolePermissionsRoles.value = []
      rolePermissionsItems.value = []
      rolePermissionsRoleCode.value = ''
      return
    }
    await loadMySectionPermissions()
    if (showRolePermissionsPanel.value) {
      await loadRolePermissionsRoles()
      if (rolePermissionsRoleCode.value) {
        await loadRolePermissionsByRole(rolePermissionsRoleCode.value)
      }
    }
    ensureAllowedActiveTab()
  },
  { immediate: true },
)

watch(
  () => route.query.tab,
  () => {
    // Если в URL пришла недоступная вкладка, возвращаем пользователя на разрешенную.
    ensureAllowedActiveTab()
  },
)

watch(
  () => JSON.stringify(mySectionPermissionsMap.value || {}),
  () => {
    // При обновлении карты прав синхронизируем активную вкладку с новым набором доступов.
    ensureAllowedActiveTab()
  },
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
  account_ids: [],
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
const editDealCommentOpen = ref(false)

const editDeal = reactive(createEditDealState())
const editDealResponsible = ref('')

const products = ref([])
const productsAll = ref([])
const productsTotal = ref(0)
const productsLoading = ref(false)
const nsGiftLoading = ref(false)
const nsGiftError = ref('')
const nsGiftOk = ref('')
const nsGiftBalance = ref(0)
const nsGiftCategories = ref([])
const nsGiftSelectedCategory = ref('')
const nsGiftSelectedCategoryId = ref(null)
const nsGiftServices = ref([])
const nsGiftServicesLoading = ref(false)
const nsGiftServicesSearch = ref('')
const nsGiftSteamMode = ref(false)
const nsGiftSteamLogin = ref('')
const nsGiftSteamAmount = ref('1')
const nsGiftSteamCurrencyRate = ref({
  date: '',
  rubUsd: 0,
  kztUsd: 0,
  uahUsd: 0,
})
const nsGiftSteamRateLoading = ref(false)
const editProductState = reactive({
  open: false,
  product_id: null,
  type_code: PRODUCT_TYPE_PRIMARY,
  account_ids: [],
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

// Приводит Date к строке YYYY-MM-DD для полей фильтра даты.
function toInputDate(value) {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// Для admin/owner по умолчанию выставляет период "последние 24 часа" как диапазон дат.
function applyPrivilegedDealsDatePreset() {
  const role = normalizeRole(auth.state.role)
  if (role !== 'admin' && role !== 'owner') return
  if (String(dealFilters.purchase_from || '').trim() || String(dealFilters.purchase_to || '').trim()) return
  const now = new Date()
  const from = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  dealFilters.purchase_from = toInputDate(from)
  dealFilters.purchase_to = toInputDate(now)
}

// Восстанавливает фильтры сделок из sessionStorage для текущего пользователя.
function restoreDealFiltersFromSession() {
  const saved = readDealFiltersSession(auth.state.user)
  if (saved?.filters) {
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
  applyPrivilegedDealsDatePreset()
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
const {
  financeFilters,
  financeNewEntry,
  financeEntryFilters,
  financeNewSection,
  financeNewType,
  financeNewOperation,
  financeNewProject,
  financeOperations,
  financeTypes,
  financeSections,
  financeProjects,
  financeRegions,
  financeSources,
  financeStatuses,
  financeEntries,
  financeEntriesTotal,
  financeReportTotals,
  financeReportItems,
  financeCatalogsLoaded,
  financeLoaded,
  financeEntriesLoaded,
  financeLoading,
  financeEntriesLoading,
  financeEntrySaving,
  financeCatalogSaving,
  financeError,
  financeEntriesError,
  financeEntryError,
  financeCatalogError,
  financeCatalogOk,
  financeEntryOk,
  loadFinanceBootstrap,
  loadFinanceEntries,
  createFinanceEntry,
  createFinanceSection,
  createFinanceType,
  updateFinanceType,
  archiveFinanceType,
  archiveFinanceSection,
  updateFinanceSection,
  createFinanceOperation,
  archiveFinanceOperation,
  updateFinanceOperation,
  createFinanceProject,
  archiveFinanceProject,
  updateFinanceProject,
  loadFinanceProjectsReport,
} = useFinanceReports({ auth, apiGet, apiPost, apiPut, apiDelete, mapApiError })

watch(
  [activeTab, () => auth.state.token],
  async ([tab, token]) => {
    // При первом открытии вкладки "Финансы" подгружаем справочники, журнал и отчет.
    if (tab !== 'finance' || !token) return
    if (!financeCatalogsLoaded.value) {
      await loadFinanceBootstrap()
    }
    if (!financeEntriesLoaded.value) {
      await loadFinanceEntries()
    }
    if (!financeLoaded.value) {
      await loadFinanceProjectsReport()
    }
  },
)
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
const newMessenger = reactive({
  code: '',
  name: '',
})
const editMessenger = reactive({ open: false, messenger_id: null, code: '', name: '' })
const messengerEditMode = ref('view')
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
const accountProductType = ref('game')
const editAccountProductType = ref('game')
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
const showChatsTab = ref(true)
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
const showMessengerForm = ref(false)
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

// Возвращает тип товара по id для валидации шеринга при сохранении сделки.
function resolveProductTypeCode(productId) {
  const targetId = Number(productId || 0)
  if (!targetId) return ''
  const found = (productsAll.value || []).find((item) => Number(item?.product_id || 0) === targetId)
  return String(found?.type_code || '').trim().toLowerCase()
}
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
  resolveProductTypeCode,
})
const usersSort = ref({ key: 'created_at', dir: 'desc' })
const domainsSortAsc = ref(true)
const sourcesSort = ref({ key: 'code', dir: 'asc' })
const messengersSort = ref({ key: 'code', dir: 'asc' })
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
const quickNewAccount = reactive({ login_name: '', domain_code: '', platform_codes: [], password: '', notes: '', subscription_product_id: '' })
const quickEditAccount = reactive({ login_name: '', domain_code: '', platform_codes: [], password: '', notes: '', subscription_product_id: '' })
const quickNewAccountLoading = ref(false)
const quickEditAccountLoading = ref(false)
const quickNewAccountError = ref('')
const quickEditAccountError = ref('')
const quickNewAccountProduct = reactive({ title: '', platform_codes: [] })
const quickNewAccountProductLoading = ref(false)
const quickNewAccountProductError = ref('')
const quickEditAccountProduct = reactive({ title: '', platform_codes: [] })
const quickEditAccountProductLoading = ref(false)
const quickEditAccountProductError = ref('')
const quickNewProductAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickEditProductAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickNewProductAccountLoading = ref(false)
const quickEditProductAccountLoading = ref(false)
const quickNewProductAccountError = ref('')
const quickEditProductAccountError = ref('')
// Дает дефолт даты срока подписки как сегодня + 1 год.
const getDefaultSubscriptionTermDate = () => {
  const nextYearDate = new Date()
  nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
  const year = nextYearDate.getFullYear()
  const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
  const day = String(nextYearDate.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const subscriptionFreeProductIdsNew = ref([])
const subscriptionFreeProductIdsEdit = ref([])
const subscriptionFreeProductIdsLoadingNew = ref(false)
const subscriptionFreeProductIdsLoadingEdit = ref(false)
const subscriptionTermsNew = ref([])
const subscriptionTermsEdit = ref([])
const subscriptionTermsLoadingNew = ref(false)
const subscriptionTermsLoadingEdit = ref(false)
const subscriptionAvailableItemsNew = ref([])
const subscriptionAvailableItemsEdit = ref([])
const subscriptionAvailableItemsLoadingNew = ref(false)
const subscriptionAvailableItemsLoadingEdit = ref(false)
const quickNewSubscriptionTerm = reactive({ account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' })
const quickEditSubscriptionTerm = reactive({ account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' })
const quickNewSubscriptionTermLoading = ref(false)
const quickEditSubscriptionTermLoading = ref(false)
const quickNewSubscriptionTermError = ref('')
const quickEditSubscriptionTermError = ref('')
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
  createQuickProductAccount,
  createQuickProductSubscriptionTerm,
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
  productAccountOptions,
  productAccountsPage,
  productSlotAssignments,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  productSubscriptionTerms,
  productSubscriptionTermsLoading,
  productSubscriptionTermsError,
  loadProductSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  requestDealConfirm,
  loadAccountsAll,
  quickNewProductAccount,
  quickNewProductAccountLoading,
  quickNewProductAccountError,
  quickEditProductAccount,
  quickEditProductAccountLoading,
  quickEditProductAccountError,
})

function clearNsGiftMessages() {
  // Сбрасываем прошлые сообщения перед новым запросом к NS Gift.
  nsGiftError.value = ''
  nsGiftOk.value = ''
}

function normalizeNsGiftCategories(payload) {
  // Нормализует категории из API в единый формат { category_id, name }.
  if (!Array.isArray(payload)) return []
  return payload
    .map((item) => {
      if (item && typeof item === 'object') {
        return {
          category_id: Number.isFinite(Number(item?.category_id)) ? Number(item.category_id) : null,
          name: String(item?.name || '').trim(),
        }
      }
      return {
        category_id: null,
        name: String(item || '').trim(),
      }
    })
    .filter((item) => item.name)
    .filter((item) => {
      // Убираем спец-категорию Steam Games | CIS, т.к. для нее есть отдельная форма.
      return String(item?.name || '').trim().toLowerCase() !== 'steam games | cis'
    })
}

function normalizeNsGiftServices(payload) {
  // Нормализует список услуг NS Gift для таблицы.
  if (!Array.isArray(payload)) return []
  return payload
    .map((item) => {
      // Берем имя и остаток из корневых полей или из raw, чтобы покрыть оба формата ответа.
      const raw = item && typeof item === 'object' ? item.raw : null
      const title = String(item?.service_name || item?.title || raw?.service_name || '').trim()
      const inStockValue = Number(item?.in_stock ?? raw?.in_stock ?? 0)
      return {
        service_id: Number(item?.service_id || 0),
        title,
        price: Number(item?.price || 0),
        // Принудительно используем USD, потому что у провайдера сейчас приходит некорректная валюта.
        currency: 'USD',
        in_stock: Number.isFinite(inStockValue) ? inStockValue : 0,
      }
    })
    .filter((item) => item.service_id > 0)
}

function readNsGiftNumber(value, fallback = 0) {
  // Преобразует строку/число вида "76.93" или "76,93" в number.
  const text = String(value ?? '').trim().replace(',', '.')
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : fallback
}

function normalizeNsGiftSteamCurrencyRate(payload) {
  // Нормализует ответ /steam/get_currency_rate в удобный для UI формат.
  const data = payload && typeof payload === 'object' ? payload : {}
  return {
    date: String(data?.date || ''),
    rubUsd: readNsGiftNumber(data?.['rub/usd'], 0),
    kztUsd: readNsGiftNumber(data?.['kzt/usd'], 0),
    uahUsd: readNsGiftNumber(data?.['uah/usd'], 0),
  }
}

function clearNsGiftSteamData() {
  // Сбрасывает данные Steam-формы при выходе из категории 68.
  nsGiftSteamCurrencyRate.value = { date: '', rubUsd: 0, kztUsd: 0, uahUsd: 0 }
}

function resetNsGiftSteamFormFields() {
  // Полностью очищает поля Steam-формы при сворачивании.
  nsGiftSteamLogin.value = ''
  nsGiftSteamAmount.value = '1'
  clearNsGiftSteamData()
}

async function toggleNsGiftSteamMode() {
  // Переключает Steam-форму по кнопке: открыть/закрыть.
  if (nsGiftSteamMode.value) {
    nsGiftSteamMode.value = false
    resetNsGiftSteamFormFields()
    return
  }
  nsGiftSteamMode.value = true
  await loadNsGiftSteamCurrencyRate()
}

async function loadNsGiftSteamCurrencyRate() {
  // Загружает курсы валют Steam для специальной формы category_id=68.
  nsGiftSteamRateLoading.value = true
  try {
    const data = await apiGet('/integrations/ns-gift/steam/currency-rate', { token: auth.state.token })
    nsGiftSteamCurrencyRate.value = normalizeNsGiftSteamCurrencyRate(data)
  } catch (err) {
    nsGiftError.value = mapApiError(err?.message || 'Не удалось загрузить курсы Steam')
  } finally {
    nsGiftSteamRateLoading.value = false
  }
}

async function loadNsGiftBalance() {
  // Загружает баланс NS Gift и обновляет поле в компактной форме.
  clearNsGiftMessages()
  nsGiftLoading.value = true
  try {
    const data = await apiGet('/integrations/ns-gift/balance', { token: auth.state.token })
    nsGiftBalance.value = Number(data?.balance || 0)
  } catch (err) {
    nsGiftError.value = mapApiError(err?.message || 'Не удалось загрузить баланс NS Gift')
  } finally {
    nsGiftLoading.value = false
  }
}

async function loadNsGiftCategories() {
  // Загружает категории NS Gift для выпадающего списка с поиском.
  clearNsGiftMessages()
  nsGiftLoading.value = true
  try {
    const data = await apiGet('/integrations/ns-gift/categories', { token: auth.state.token })
    const categories = normalizeNsGiftCategories(data)
    nsGiftCategories.value = categories
    if (nsGiftSelectedCategory.value) {
      const selected = categories.find((item) => item.name === nsGiftSelectedCategory.value)
      nsGiftSelectedCategoryId.value = selected?.category_id ?? null
    }
    nsGiftOk.value = `Загружено категорий: ${categories.length}`
    if (nsGiftSelectedCategoryId.value) {
      await loadNsGiftServicesByCategory()
    }
  } catch (err) {
    nsGiftError.value = mapApiError(err?.message || 'Не удалось загрузить категории NS Gift')
  } finally {
    nsGiftLoading.value = false
  }
}

async function reloadNsGiftData() {
  // Обновляет баланс и список категорий одним действием из вкладки NS Gift.
  clearNsGiftMessages()
  nsGiftLoading.value = true
  try {
    const [balanceData, categoriesData] = await Promise.all([
      apiGet('/integrations/ns-gift/balance', { token: auth.state.token }),
      apiGet('/integrations/ns-gift/categories', { token: auth.state.token }),
    ])
    nsGiftBalance.value = Number(balanceData?.balance || 0)
    const categories = normalizeNsGiftCategories(categoriesData)
    nsGiftCategories.value = categories
    if (nsGiftSelectedCategory.value) {
      const selected = categories.find((item) => item.name === nsGiftSelectedCategory.value)
      nsGiftSelectedCategoryId.value = selected?.category_id ?? null
    }
    nsGiftOk.value = `Категорий: ${categories.length}`
    if (nsGiftSelectedCategoryId.value) {
      await loadNsGiftServicesByCategory()
    }
  } catch (err) {
    nsGiftError.value = mapApiError(err?.message || 'Не удалось обновить данные NS Gift')
  } finally {
    nsGiftLoading.value = false
  }
}

async function loadNsGiftServicesByCategory() {
  // Загружает услуги NS Gift по выбранной категории.
  const categoryId = Number(nsGiftSelectedCategoryId.value || 0)
  if (!Number.isFinite(categoryId) || categoryId <= 0) {
    nsGiftServices.value = []
    clearNsGiftSteamData()
    return
  }
  nsGiftSteamMode.value = false
  clearNsGiftSteamData()
  // Перед новой загрузкой убираем старую ошибку, чтобы не показывать устаревший текст.
  nsGiftError.value = ''
  nsGiftServicesLoading.value = true
  try {
    const data = await apiGet(`/integrations/ns-gift/services?category_id=${categoryId}`, { token: auth.state.token })
    nsGiftServices.value = normalizeNsGiftServices(data?.items)
  } catch (err) {
    const rawMessage = String(err?.message || '')
    // Для 500 по категории скрываем ошибку в UI и просто показываем пустой список.
    if (/\b500\b/.test(rawMessage)) {
      nsGiftServices.value = []
      nsGiftError.value = ''
      return
    }
    nsGiftError.value = mapApiError(err?.message || 'Не удалось загрузить услуги NS Gift')
    nsGiftServices.value = []
  } finally {
    nsGiftServicesLoading.value = false
  }
}

function setNsGiftSelectedCategoryFromEvent(event) {
  // Сохраняет выбранную категорию из поля с автопоиском.
  const value = String(event?.target?.value || '').trim()
  nsGiftSelectedCategory.value = value
  const selected = nsGiftCategories.value.find((item) => item?.name === value)
  nsGiftSelectedCategoryId.value = selected?.category_id ?? null
  nsGiftSteamMode.value = false
  if (!selected) {
    nsGiftServices.value = []
    resetNsGiftSteamFormFields()
  }
}

function selectNsGiftCategoryText(value) {
  // По клику на плашку подставляем текст в строку поиска, без выбора конкретной категории.
  const text = String(value || '').trim()
  nsGiftSelectedCategory.value = text
  nsGiftSelectedCategoryId.value = null
  nsGiftSteamMode.value = false
  nsGiftServices.value = []
  resetNsGiftSteamFormFields()
}

function selectNsGiftCategoryOption(value) {
  // Явно выбирает категорию из выпадающего списка и сохраняет её id.
  const text = String(value || '').trim()
  nsGiftSelectedCategory.value = text
  const selected = nsGiftCategories.value.find((item) => item?.name === text)
  nsGiftSelectedCategoryId.value = selected?.category_id ?? null
  nsGiftSteamMode.value = false
  if (!selected) resetNsGiftSteamFormFields()
  void loadNsGiftServicesByCategory()
}

function setNsGiftServicesSearchFromEvent(event) {
  // Обновляет строку поиска для фильтрации таблицы услуг.
  nsGiftServicesSearch.value = String(event?.target?.value || '').trim()
}

function setNsGiftSteamLoginFromEvent(event) {
  // Сохраняет логин Steam для отдельной формы категории 68.
  nsGiftSteamLogin.value = String(event?.target?.value || '').trim()
}

function setNsGiftSteamAmountFromEvent(event) {
  // Сохраняет дробный amount для локального расчета по курсам.
  const raw = String(event?.target?.value || '').trim().replace(',', '.')
  nsGiftSteamAmount.value = raw
}

const {
  getAccountSecret,
  getReserveSecrets,
  getReserveSecretEntries,
  ensureAccountSecretsLoaded,
  loadAccounts,
  loadAccountsAll: loadAccountsAllFromAccountsFlow,
  refreshOpenAccountFromDb,
  startEditAccount,
  toggleAccountEditMode,
  openCreateAccountModal,
  cancelEditAccount,
  createAccount,
  createQuickAccountProduct,
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
  quickNewAccountProduct,
  quickNewAccountProductLoading,
  quickNewAccountProductError,
  quickEditAccountProduct,
  quickEditAccountProductLoading,
  quickEditAccountProductError,
  loadProductsAll,
})

loadAccountsAllDeferred.set(loadAccountsAllFromAccountsFlow)

// Восстанавливает карточку аккаунта по id после закрытия сделки, открытой из аккаунтов.
async function reopenAccountByIdFromDealReturn(accountId) {
  const targetId = Number(accountId || 0)
  if (!targetId) return
  setActiveTab('accounts')
  await loadAccountsAll([targetId])
  const fromLabels = (accountsAll.value || []).find((item) => Number(item?.account_id || 0) === targetId)
  const fallbackAccount = fromLabels || {
    account_id: targetId,
    login_name: '',
    domain_code: '',
    region_code: '',
    status: 'active',
    is_deactivated: false,
    deactivated_at: '',
    next_activation_at: '',
    notes: '',
    account_date: '',
  }
  startEditAccount(fallbackAccount)
}

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
  loadSubscriptionFreeProductIds,
  loadAvailableSubscriptionItems,
  loadSubscriptionTerms,
  createQuickSubscriptionTerm,
  releaseSlotFromDeal,
} = useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  requestDealConfirm,
  isSlotTypeSupportedForProduct,
  slotTypes,
  productsAll,
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
  subscriptionFreeProductIdsNew,
  subscriptionFreeProductIdsEdit,
  subscriptionFreeProductIdsLoadingNew,
  subscriptionFreeProductIdsLoadingEdit,
  subscriptionTermsNew,
  subscriptionTermsEdit,
  subscriptionTermsLoadingNew,
  subscriptionTermsLoadingEdit,
  subscriptionAvailableItemsNew,
  subscriptionAvailableItemsEdit,
  subscriptionAvailableItemsLoadingNew,
  subscriptionAvailableItemsLoadingEdit,
  quickNewSubscriptionTerm,
  quickEditSubscriptionTerm,
  quickNewSubscriptionTermLoading,
  quickEditSubscriptionTermLoading,
  quickNewSubscriptionTermError,
  quickEditSubscriptionTermError,
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
  dealLoading,
  newDeal,
  editDeal,
  dealEditMode,
  dealInitLock,
  newDealResponsible,
  editDealResponsible,
  newDealCommentOpen,
  editDealCommentOpen,
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
  quickNewSubscriptionTerm,
  quickEditSubscriptionTerm,
  quickNewSubscriptionTermError,
  quickEditSubscriptionTermError,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  ensureAccountSecretsLoaded,
  accountsAll,
  loadAccountsAll,
  nextTick,
  loadDealAccountsForProduct,
  loadDealProductAssignments,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealSlotAvailability,
  loadSubscriptionTerms,
  loadAvailableSubscriptionItems,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  currentResponsibleName: currentUserResponsibleName,
  canEditCompletedDeal: canEditCompletedDeals,
  showDealWarning,
  reopenAccountByIdFromDealReturn,
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
  updateUser,
  submitUserForm,
  openUserModal,
  openUserViewModal,
  openUserRoleModal,
  startUserEdit,
  closeUserModal,
  changePassword,
  openPwdModal,
  closePwdModal,
  onLogout,
} = useUserProfileFlow({
  auth,
  router,
  isAdmin,
  canViewUsersSection,
  apiGet,
  apiPost,
  apiPut,
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
  userFormMode,
  newUser,
  editUser,
  editUserInitial,
  pwdError,
  pwdOk,
  pwdLoading,
  showPwdForm,
  pwdForm,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

// Виджет дашборда: менеджеры/операторы с количеством заявок в ожидании и online-статусом.
const {
  managersLoadItems,
  managersLoadOnlineCount,
  managersLoadDate,
  managersLoadTimezone,
  managersLoadLoading,
  managersLoadError,
  refreshManagersWorkload,
  stopManagersWorkloadPolling,
  startPresenceHeartbeatPolling,
  stopPresenceHeartbeatPolling,
} = useManagersLoad({
  auth,
  apiGet,
  apiPost,
  mapApiError,
})

// Контекст верхней панели: вкладки, пользователь и кнопка выхода.
const topBarCtx = asCtx({
  userRoleName: topBarUserName,
  activeTab,
  routeQuery: computed(() => route.query || {}),
  isAdmin,
  canViewDealsSection,
  canViewAccountsSection,
  canViewProductsSection,
  canViewNsGiftSection,
  canViewTelegramSection,
  canViewUsersSection: canViewUsersTab,
  canViewProfileSection,
  canViewDashboardSection,
  showChatsTab,
  showUsersTab,
  showDashboard,
  managersLoadItems,
  managersLoadOnlineCount,
  managersLoadLoading,
  onLogout,
})

// Контекст дашборда: статус API и кнопка проверки.
const dashboardSectionCtx = asCtx({
  apiOk,
  loading,
  checkApi,
  managersLoadItems,
  managersLoadOnlineCount,
  managersLoadDate,
  managersLoadTimezone,
  managersLoadLoading,
  managersLoadError,
  refreshManagersWorkload,
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
  downloadAccountImportExport,
  downloadProductImportReport,
  validateProductImport,
  downloadAccountImportReport,
  validateAccountSlotsCheck,
  validateAccountDealsCheck,
  fillAccountDealsOrderNumbers,
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
  accounts,
  ensureAccountSecretsLoaded,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
})

// Работа со справочниками: платформы, регионы, источники, домены.
const {
  loadCatalogs,
  loadSlotTypes,
  loadDomains,
  loadSources,
  loadMessengers,
  openEditDomain,
  openDomainModal,
  closeDomainModal,
  saveEditDomain,
  openEditSource,
  openSourceModal,
  closeSourceModal,
  saveEditSource,
  openEditMessenger,
  openMessengerModal,
  closeMessengerModal,
  saveEditMessenger,
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
  createMessenger,
  createPlatform,
  createRegion,
  deleteDomain,
  deleteSource,
  deleteMessenger,
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
  showMessengerForm,
  showPlatformForm,
  showRegionForm,
  newDomain,
  editDomain,
  domainEditMode,
  newSource,
  editSource,
  sourceEditMode,
  newMessenger,
  editMessenger,
  messengerEditMode,
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
  messengers,
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
  sortedMessengers,
  messengersByCode,
  sortedPlatforms,
  sortedRegions,
} = useCatalogsViewState({
  users,
  usersSort,
  domains,
  domainsSortAsc,
  sources,
  sourcesSort,
  messengers,
  messengersSort,
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
  toggleMessengersSort,
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
  messengersSort,
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
  restoreSlotAssignment,
  sortProductAccounts,
  nextProductAccountsPage,
  prevProductAccountsPage,
} = useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
  requestDealConfirm,
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
  accountSaving,
  activeAccountChips,
  resetAccountFilter,
  showAccountImport,
  closeAccountImport,
  modalRef,
  modalStyle,
  startModalDrag,
  accountImportLoading,
  downloadAccountTemplate,
  downloadAccountImportExport,
  validateAccountSlotsCheck,
  validateAccountDealsCheck,
  fillAccountDealsOrderNumbers,
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
  ensureAccountSecretsLoaded,
  getReserveSecretEntries,
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
  canToggleAccountDeactivation,
  cancelEditAccount,
  accountModalMode,
  accountEditMode,
  setAccountEditMode,
  toggleAccountEditMode,
  refreshOpenAccountFromDb,
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
  restoreSlotAssignment,
  accountDealsError,
  accountDealsLoading,
  accountDeals,
  startEditDeal,
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
  createQuickAccountProduct,
  quickNewAccountProduct,
  quickNewAccountProductLoading,
  quickNewAccountProductError,
  quickEditAccountProduct,
  quickEditAccountProductLoading,
  quickEditAccountProductError,
  platforms,
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
  productAccountOptions,
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
  productSubscriptionTerms,
  productSubscriptionTermsLoading,
  productSubscriptionTermsError,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  productError,
  productOk,
  newProduct,
  accountsAll,
  createQuickProductAccount,
  createQuickProductSubscriptionTerm,
  quickNewProductAccount,
  quickNewProductAccountLoading,
  quickNewProductAccountError,
  quickEditProductAccount,
  quickEditProductAccountLoading,
  quickEditProductAccountError,
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
  showMessengerForm,
  editMessenger,
  closeMessengerModal,
  messengerEditMode,
  saveEditMessenger,
  deleteMessenger,
  createMessenger,
  newMessenger,
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
  activeTab,
  routeQuery: computed(() => route.query || {}),
  canViewProfileSection,
  canViewUsersSection,
  canViewAnalyticsSection,
  canViewCatalogsSection,
  canViewFinanceSection,
  canManageRolePermissions,
  dealsRealtimeStatus,
  dealEditingByDealId,
  dealsRealtimeAnimationTick,
  currentUsername: computed(() => String(auth.state.user || '')),
  responsibleNameByUsername,
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
  getAccountSecret,
  getReserveSecrets,
  getReserveSecretEntries,
  accountSecrets,
  ensureAccountSecretsLoaded,
  loadAccountsAll,
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
  quickEditSubscriptionTerm,
  quickEditSubscriptionTermLoading,
  quickEditSubscriptionTermError,
  createQuickSubscriptionTerm,
  accountSlotStatusEdit,
  slotTypes,
  getSortedSlotStatus,
  dealAccountAssignmentsLoadingEdit,
  dealAccountAssignmentsEdit,
  getSourceLabelById,
  getMessengerLabelById,
  sourcesByCode,
  messengersByCode,
  maxPrice,
  clampPrice,
  getFlowStatusLabel,
  editDealProductSearch,
  onEditDealProductSearch,
  filteredEditDealProducts,
  subscriptionFreeProductIdsEdit,
  subscriptionFreeProductIdsLoadingEdit,
  subscriptionTermsEdit,
  subscriptionTermsLoadingEdit,
  subscriptionAvailableItemsEdit,
  subscriptionAvailableItemsLoadingEdit,
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
  subscriptionFreeProductIdsNew,
  subscriptionFreeProductIdsLoadingNew,
  subscriptionTermsNew,
  subscriptionTermsLoadingNew,
  subscriptionAvailableItemsNew,
  subscriptionAvailableItemsLoadingNew,
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
  quickNewSubscriptionTerm,
  quickNewSubscriptionTermLoading,
  quickNewSubscriptionTermError,
  accountSlotStatusNew,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsNew,
  newDealCommentOpen,
  editDealCommentOpen,
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
  openMessengerModal,
  loadMessengers,
  sortedMessengers,
  toggleMessengersSort,
  messengersSort,
  openEditMessenger,
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

// Контекст вкладки NS Gift: баланс и выбор категории.
const nsGiftSectionCtx = asCtx({
  loading: nsGiftLoading,
  error: nsGiftError,
  ok: nsGiftOk,
  balance: nsGiftBalance,
  categories: nsGiftCategories,
  selectedCategory: nsGiftSelectedCategory,
  selectedCategoryId: nsGiftSelectedCategoryId,
  steamMode: nsGiftSteamMode,
  services: nsGiftServices,
  servicesLoading: nsGiftServicesLoading,
  servicesSearch: nsGiftServicesSearch,
  steamLogin: nsGiftSteamLogin,
  steamAmount: nsGiftSteamAmount,
  steamCurrencyRate: nsGiftSteamCurrencyRate,
  steamLoading: nsGiftSteamRateLoading,
  loadNsGiftBalance,
  loadNsGiftCategories,
  reloadNsGiftData,
  activateSteamMode: toggleNsGiftSteamMode,
  toggleSteamMode: toggleNsGiftSteamMode,
  loadServicesByCategory: loadNsGiftServicesByCategory,
  setSelectedCategoryFromEvent: setNsGiftSelectedCategoryFromEvent,
  selectCategoryText: selectNsGiftCategoryText,
  selectCategoryOption: selectNsGiftCategoryOption,
  setServicesSearchFromEvent: setNsGiftServicesSearchFromEvent,
  setSteamLoginFromEvent: setNsGiftSteamLoginFromEvent,
  setSteamAmountFromEvent: setNsGiftSteamAmountFromEvent,
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
  activeTab,
  routeQuery: computed(() => route.query || {}),
  canViewProfileSection,
  canViewUsersSection,
  canViewAnalyticsSection,
  canViewCatalogsSection,
  canViewFinanceSection,
  canManageRolePermissions,
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

// Контекст вкладки финансов: фильтры, итоги и таблица по проектам.
const financeSectionCtx = asCtx({
  activeTab,
  routeQuery: computed(() => route.query || {}),
  canViewProfileSection,
  canViewUsersSection,
  canViewAnalyticsSection,
  canViewCatalogsSection,
  canViewFinanceSection,
  canManageRolePermissions,
  financeNewEntry,
  financeEntryFilters,
  financeNewSection,
  financeNewType,
  financeNewOperation,
  financeNewProject,
  financeOperations,
  financeTypes,
  financeSections,
  financeLoading,
  financeEntriesLoading,
  financeEntrySaving,
  financeCatalogSaving,
  financeError,
  financeEntriesError,
  financeEntryError,
  financeCatalogError,
  financeCatalogOk,
  financeEntryOk,
  financeLoaded,
  financeEntriesTotal,
  financeFilters,
  financeProjects,
  financeRegions,
  financeSources,
  financeStatuses,
  financeEntries,
  financeReportTotals,
  financeReportItems,
  loadFinanceEntries,
  createFinanceEntry,
  createFinanceSection,
  createFinanceType,
  updateFinanceType,
  archiveFinanceType,
  archiveFinanceSection,
  updateFinanceSection,
  createFinanceOperation,
  archiveFinanceOperation,
  updateFinanceOperation,
  createFinanceProject,
  archiveFinanceProject,
  updateFinanceProject,
  loadFinanceProjectsReport,
  maxDate,
  minDate,
  formatPrice,
  formatPercent,
})

// Контекст вкладки пользователей: список и модалка создания.
const usersSectionCtx = asCtx({
  openUserModal,
  openUserViewModal,
  openUserRoleModal,
  startUserEdit,
  loadUsers,
  userLoading,
  showUserForm,
  userFormMode,
  closeUserModal,
  modalRef,
  modalStyle,
  startModalDrag,
  newUser,
  editUser,
  roles,
  createUser,
  updateUser,
  submitUserForm,
  userError,
  userOk,
  sortedUsers,
  toggleUsersSort,
})

// Контекст вкладки профиля: смена пароля и встраивание списка пользователей.
const profileSectionCtx = asCtx({
  isAdmin,
  canManageRolePermissions,
  canViewAnalyticsSection,
  canViewCatalogsSection,
  canViewFinanceSection,
  canViewUsersSection,
  routeQuery: computed(() => route.query || {}),
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
  rolePermissionsRoles,
  rolePermissionsRoleCode,
  rolePermissionsItems,
  rolePermissionsLoading,
  rolePermissionsSaving,
  rolePermissionsError,
  rolePermissionsOk,
  ensureRolePermissionsFormDataLoaded,
  setRolePermissionsRoleCode,
  setRolePermissionItem,
  saveRolePermissions,
})

useWorkLifecycle({
  auth,
  router,
  route,
  canViewUsersSection,
  loadUsers,
  refreshManagersWorkload,
  cleanupManagersRealtimeRefresh: () => {
    if (managersRealtimeRefreshTimer) {
      clearTimeout(managersRealtimeRefreshTimer)
      managersRealtimeRefreshTimer = null
    }
    managersRealtimeRefreshQueued = false
  },
  startPresenceHeartbeatPolling,
  stopGameImportStatusPolling: stopProductImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  stopManagersWorkloadPolling,
  stopPresenceHeartbeatPolling,
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
  productFilters,
  accountFilters,
  productFilterDraft,
  accountFilterDraft,
  defaultDealsResponsibleFilter,
  mustPrefillDealsResponsible,
  showUserForm,
  showProductForm,
  showProductFilters,
  showDealForm,
  showAccountFilters,
  activeProductFilter,
  activeAccountFilter,
  nsGiftOk,
  nsGiftError,
  editProduct,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  messengersLoadedOnce,
  slotTypesLoadedOnce,
  productsAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  messengers,
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
  loadMessengers,
  loadSlotTypes,
  loadProducts,
  loadProductsAll,
  loadAccounts,
  loadDeals,
  loadNsGiftBalance,
  loadNsGiftCategories,
  reloadNsGiftData,
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
  productsAll,
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
  loadSubscriptionFreeProductIds,
  loadAvailableSubscriptionItems,
  loadSubscriptionTerms,
  ensureAccountSecretsLoaded,
})

// Подключает realtime-обновления списка сделок через WebSocket.
useDealsRealtime({
  activeTab,
  auth,
  dealPage,
  editDeal,
  dealEditMode,
  showDealForm,
  loadDeals,
  onDealEvent: handleDealsRealtimeEvent,
  wsState: dealsRealtimeStatus,
  editingByDealId: dealEditingByDealId,
  realtimeAnimationTick: dealsRealtimeAnimationTick,
})

</script>
