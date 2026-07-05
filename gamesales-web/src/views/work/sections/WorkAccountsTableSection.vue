<template>
  <div v-if="sortedAccounts.length && hasVisibleColumns" class="accounts-table-wrap">
    <table ref="tableEl" class="table table--compact accounts-table">
      <colgroup>
        <col v-if="canViewEmail" :style="getColumnStyle('login')" />
        <col v-if="canViewGames" :style="getColumnStyle('products')" />
        <col v-if="canViewSlots" :style="getColumnStyle('slots')" />
        <col v-if="canViewReserves" :style="getColumnStyle('reserve')" />
      </colgroup>
      <thead>
        <tr>
          <th v-if="canViewEmail" class="cell--account">
          <span class="th-title th-title--filter">
            Почта
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(accountFilters.login_q) }"
                type="button"
                aria-label="Фильтр по почте"
                title="Фильтр по почте"
                @click.stop="openAccountFilter('login')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по почте"
                title="Сортировка по почте"
                @click.stop="toggleAccountSort('login')"
                :class="getAccountSortClass('login')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeAccountFilter === 'login'" class="filter-pop filter-pop--left" @click.stop>
            <label class="field">
              <span class="label">Почта</span>
              <input v-model.trim="accountFilterDraft.login" class="input" placeholder="почта" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyAccountFilter('login')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetAccountFilter('login')">Сбросить</button>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Почта"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'login')"
          />
          </th>
          <th v-if="canViewGames" class="account-col-products">
          <span class="th-title th-title--filter">
            Товары
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(accountFilters.product_q) }"
                type="button"
                aria-label="Фильтр по товарам"
                title="Фильтр по товарам"
                @click.stop="openAccountFilter('product')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по товарам"
                title="Сортировка по товарам"
                @click.stop="toggleAccountSort('products')"
                :class="getAccountSortClass('products')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeAccountFilter === 'product'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Товар</span>
              <input v-model.trim="accountFilterDraft.product" class="input" placeholder="название товара" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyAccountFilter('product')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetAccountFilter('product')">Сбросить</button>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Товары"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'products')"
          />
          </th>
          <th v-if="canViewSlots" class="account-col-slots">
            Слоты
            <button
              class="table-col-resizer"
              type="button"
              aria-label="Изменить ширину колонки Слоты"
              title="Потяните для изменения ширины"
              @mousedown.stop.prevent="startResize($event, 'slots')"
            />
          </th>
          <th v-if="canViewReserves" class="account-col-reserve">Резерв</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="a in sortedAccounts"
          :key="a.account_id"
          :class="{ 'clickable-row': canOpenAccountCard }"
          @click="onAccountRowClick(a)"
        >
          <td v-if="canViewEmail" class="cell--account">{{ a.login_full || '—' }}</td>
          <td v-if="canViewGames" class="account-col-products">{{ formatAccountProductsLine(a) }}</td>
          <td v-if="canViewSlots" class="cell--slots account-col-slots">
            <span v-if="!getAccountSlotStatusList(a).length" class="slot-line">—</span>
            <span v-for="s in getAccountSlotStatusList(a)" :key="s.slot_type_code" class="slot-line">
              {{ formatAccountSlotStatusLine(s) }}
            </span>
          </td>
          <td
            v-if="canViewReserves"
            class="cell--selectable account-col-reserve"
            @click.stop
            @mouseenter="preloadAccountReserveData(a.account_id)"
          >
            {{ formatSecret(getMaskedReserveSecrets(a.account_id)) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else-if="sortedAccounts.length" class="muted">Нет доступных колонок аккаунтов.</p>
  <p v-else class="muted">Пока нет аккаунтов.</p>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'

const tableEl = ref(null)
const { getColumnStyle, startResize } = useResizableTableColumns({
  tableRef: tableEl,
  storageKey: 'work.accounts.columns.v1',
  columns: [
    { key: 'login', defaultWidth: 30, minWidth: 20 },
    { key: 'products', defaultWidth: 34, minWidth: 20 },
    { key: 'slots', defaultWidth: 20, minWidth: 12 },
    { key: 'reserve', defaultWidth: 16, minWidth: 10 },
  ],
})

const props = defineProps({
  sortedAccounts: { type: Array, required: true },
  accountFilters: { type: Object, required: true },
  activeAccountFilter: { type: String, default: '' },
  accountFilterDraft: { type: Object, required: true },
  openAccountFilter: { type: Function, required: true },
  toggleAccountSort: { type: Function, required: true },
  getAccountSortClass: { type: Function, required: true },
  applyAccountFilter: { type: Function, required: true },
  resetAccountFilter: { type: Function, required: true },
  startEditAccount: { type: Function, required: true },
  canViewEmail: { type: Boolean, default: false },
  canViewGames: { type: Boolean, default: false },
  canViewSlots: { type: Boolean, default: false },
  canViewReserves: { type: Boolean, default: false },
  canEditAccount: { type: Boolean, default: false },
  formatAccountProductsLine: { type: Function, required: true },
  getAccountSlotStatusList: { type: Function, required: true },
  formatAccountSlotStatusLine: { type: Function, required: true },
  formatSecret: { type: Function, required: true },
  getReserveSecrets: { type: Function, required: true },
  getReserveSecretEntries: { type: Function, required: true },
  ensureAccountSecretsLoaded: { type: Function, required: true },
  loadAccountUsedReserveKeys: { type: Function, required: true },
})

const accountUsedReserveKeys = ref({})
const hasVisibleColumns = computed(() => props.canViewEmail || props.canViewGames || props.canViewSlots || props.canViewReserves)
const canOpenAccountCard = computed(() => hasVisibleColumns.value)

// Открывает карточку аккаунта на просмотр, даже если редактирование роли запрещено.
function onAccountRowClick(account) {
  if (!canOpenAccountCard.value) return
  props.startEditAccount(account)
}

// Нормализует ключ резерва к формату reserveN для надежного сравнения в таблице.
function normalizeReserveKey(value) {
  const raw = String(value || '').trim().toLowerCase()
  if (!/^reserve\d+$/.test(raw)) return ''
  return `reserve${Number(raw.replace('reserve', ''))}`
}

// Догружает секреты и отметки занятости одного аккаунта для безопасного отображения резервов.
async function preloadAccountReserveData(accountId) {
  const targetId = Number(accountId || 0)
  if (!targetId) return
  await Promise.resolve(props.ensureAccountSecretsLoaded(targetId)).catch(() => {})
  if (Object.prototype.hasOwnProperty.call(accountUsedReserveKeys.value || {}, targetId)) return
  const keys = await Promise.resolve(props.loadAccountUsedReserveKeys(targetId)).catch(() => [])
  accountUsedReserveKeys.value = {
    ...(accountUsedReserveKeys.value || {}),
    [targetId]: (Array.isArray(keys) ? keys : []).map(normalizeReserveKey).filter(Boolean),
  }
}

// Показывает резервы после загрузки usage, чтобы список не мигал до проверки занятости.
function getMaskedReserveSecrets(accountId) {
  const targetId = Number(accountId || 0)
  if (!Object.prototype.hasOwnProperty.call(accountUsedReserveKeys.value || {}, targetId)) return ''
  return props.getReserveSecretEntries(targetId)
    .map((item) => item?.value)
    .filter(Boolean)
    .join(' ')
}

// Догружает данные для видимых аккаунтов сразу после рендера таблицы, чтобы колонка "Резерв" не зависела от hover.
function preloadVisibleAccountSecrets(list) {
  if (!props.canViewReserves) return
  const ids = [...new Set((Array.isArray(list) ? list : [])
    .map((item) => Number(item?.account_id || 0))
    .filter((id) => id > 0))]
  for (const accountId of ids) {
    void preloadAccountReserveData(accountId)
  }
}

watch(
  () => props.sortedAccounts,
  (list) => {
    preloadVisibleAccountSecrets(list)
  },
  { immediate: true }
)
</script>
