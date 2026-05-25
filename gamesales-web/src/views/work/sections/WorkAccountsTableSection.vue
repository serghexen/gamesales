<template>
  <div v-if="sortedAccounts.length" class="accounts-table-wrap">
    <table ref="tableEl" class="table table--compact accounts-table">
      <colgroup>
        <col :style="getColumnStyle('login')" />
        <col :style="getColumnStyle('products')" />
        <col :style="getColumnStyle('slots')" />
        <col :style="getColumnStyle('reserve')" />
      </colgroup>
      <thead>
        <tr>
          <th class="cell--account">
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
          <th class="account-col-products">
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
          <th class="account-col-slots">
            Слоты
            <button
              class="table-col-resizer"
              type="button"
              aria-label="Изменить ширину колонки Слоты"
              title="Потяните для изменения ширины"
              @mousedown.stop.prevent="startResize($event, 'slots')"
            />
          </th>
          <th class="account-col-reserve">Резерв</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in sortedAccounts" :key="a.account_id" class="clickable-row" @click="startEditAccount(a)">
          <td class="cell--account">{{ a.login_full || '—' }}</td>
          <td class="account-col-products">{{ formatAccountProductsLine(a) }}</td>
          <td class="cell--slots account-col-slots">
            <span v-if="!getAccountSlotStatusList(a).length" class="slot-line">—</span>
            <span v-for="s in getAccountSlotStatusList(a)" :key="s.slot_type_code" class="slot-line">
              {{ formatAccountSlotStatusLine(s) }}
            </span>
          </td>
          <td
            class="cell--selectable account-col-reserve"
            @click.stop
            @mouseenter="ensureAccountSecretsLoaded(a.account_id)"
          >
            {{ formatSecret(getReserveSecrets(a.account_id)) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else class="muted">Пока нет аккаунтов.</p>
</template>

<script setup>
import { ref, watch } from 'vue'

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
  formatAccountProductsLine: { type: Function, required: true },
  getAccountSlotStatusList: { type: Function, required: true },
  formatAccountSlotStatusLine: { type: Function, required: true },
  formatSecret: { type: Function, required: true },
  getReserveSecrets: { type: Function, required: true },
  ensureAccountSecretsLoaded: { type: Function, required: true },
})

// Догружает секреты для видимых аккаунтов сразу после рендера таблицы, чтобы колонка "Резерв" не зависела от hover.
function preloadVisibleAccountSecrets(list) {
  const ids = [...new Set((Array.isArray(list) ? list : [])
    .map((item) => Number(item?.account_id || 0))
    .filter((id) => id > 0))]
  for (const accountId of ids) {
    void Promise.resolve(props.ensureAccountSecretsLoaded(accountId)).catch(() => {})
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
