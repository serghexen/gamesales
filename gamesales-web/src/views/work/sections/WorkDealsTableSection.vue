<template>
  <div class="deals-table-wrap">
    <table
      ref="tableEl"
      class="table deals-table"
      :class="{ 'table--completed': dealShowCompleted, 'table--pending': !dealShowCompleted }"
    >
    <colgroup>
      <col :style="getColumnStyle('type')" />
      <col :style="getColumnStyle('customer')" />
      <col :style="getColumnStyle('region')" />
      <col :style="getColumnStyle('date')" />
      <col :style="getColumnStyle('status')" />
      <col :style="getColumnStyle('responsible')" />
      <col :style="getColumnStyle('action')" />
    </colgroup>
    <thead>
      <tr>
        <th class="cell--tight deal-col-type">
          <span class="th-title th-title--filter">
            Тип
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.type_q) }"
                type="button"
                aria-label="Фильтр по типу"
                title="Фильтр по типу"
                @click.stop="setActiveDealFilter(activeDealFilter === 'type' ? '' : 'type')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по типу"
                title="Сортировка по типу"
                @click.stop="toggleDealSort('type')"
                :class="getDealSortClass('type')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeDealFilter === 'type'" class="filter-pop filter-pop--left" @click.stop>
            <div class="field">
              <span class="label">Тип</span>
              <div class="check-list check-list--compact">
                <label v-for="t in dealTypeOptions" :key="`deal-type-${t.code}`" class="check-item">
                  <input v-model="typeFilterValues" type="checkbox" :value="t.code" @change="applyDealMultiFilter" />
                  <span>{{ t.name }}</span>
                </label>
              </div>
            </div>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Тип"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'type')"
          />
        </th>
        <th class="deal-col-customer">
          <span class="th-title th-title--filter">
            Покупатель
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.customer_q) }"
                type="button"
                aria-label="Фильтр по покупателю"
                title="Фильтр по покупателю"
                @click.stop="setActiveDealFilter(activeDealFilter === 'customer' ? '' : 'customer')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по покупателю"
                title="Сортировка по покупателю"
                @click.stop="toggleDealSort('customer')"
                :class="getDealSortClass('customer')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeDealFilter === 'customer'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Покупатель</span>
              <input
                v-model.trim="dealFilters.customer_q"
                class="input"
                placeholder="покупатель"
                @keydown.enter.prevent="loadDeals(1); setActiveDealFilter('')"
              />
            </label>
            <button class="ghost ghost--small" type="button" @click="loadDeals(1); setActiveDealFilter('')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('customer')">Сбросить</button>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Покупатель"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'customer')"
          />
        </th>
        <th class="cell--tight deal-col-region">
          <span class="th-title th-title--filter">
            Товар
            <span class="th-actions">
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по товару"
                title="Сортировка по товару"
                @click.stop="toggleDealSort('region')"
                :class="getDealSortClass('region')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Товар"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'region')"
          />
        </th>
        <th class="deal-col-date">
          <span class="th-title th-title--filter">
            Дата/время
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.purchase_from || dealFilters.purchase_to) }"
                type="button"
                aria-label="Фильтр по дате"
                title="Фильтр по дате"
                @click.stop="setActiveDealFilter(activeDealFilter === 'date' ? '' : 'date')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по дате"
                title="Сортировка по дате"
                @click.stop="toggleDealSort('date')"
                :class="getDealSortClass('date')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeDealFilter === 'date'" class="filter-pop filter-pop--right" @click.stop>
            <label class="field">
              <span class="label">С</span>
              <input
                v-model="dealFilters.purchase_from"
                class="input"
                type="date"
                :min="minDate"
                :max="maxDate"
                @keydown.enter.prevent="validateDealRange('date') && (loadDeals(1), setActiveDealFilter(''))"
              />
            </label>
            <label class="field">
              <span class="label">По</span>
              <input
                v-model="dealFilters.purchase_to"
                class="input"
                type="date"
                :min="minDate"
                :max="maxDate"
                @keydown.enter.prevent="validateDealRange('date') && (loadDeals(1), setActiveDealFilter(''))"
              />
            </label>
            <p v-if="dealFilterErrors.date" class="bad">{{ dealFilterErrors.date }}</p>
            <button
              class="ghost ghost--small"
              type="button"
              @click="validateDealRange('date') && (loadDeals(1), setActiveDealFilter(''))"
            >
              Применить
            </button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('date')">Сбросить</button>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Дата и время"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'date')"
          />
        </th>
        <th class="cell--tight deal-col-status">
          <span class="th-title th-title--filter">
            Статус
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.status_q) }"
                type="button"
                aria-label="Фильтр по статусу"
                title="Фильтр по статусу"
                @click.stop="setActiveDealFilter(activeDealFilter === 'status' ? '' : 'status')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по статусу"
                title="Сортировка по статусу"
                @click.stop="toggleDealSort('status')"
                :class="getDealSortClass('status')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeDealFilter === 'status'" class="filter-pop filter-pop--right" @click.stop>
            <div class="field">
              <span class="label">Статус</span>
              <div class="check-list check-list--compact">
                <label v-for="s in dealFlowStatusOptions" :key="`deal-status-${s.code}`" class="check-item">
                  <input v-model="statusFilterValues" type="checkbox" :value="s.code" @change="applyDealMultiFilter" />
                  <span>{{ s.name }}</span>
                </label>
              </div>
            </div>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Статус"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'status')"
          />
        </th>
        <th class="cell--tight deal-col-responsible">
          <span class="th-title th-title--filter">
            {{ dealShowCompleted ? 'Ответств.' : 'Ответств.' }}
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.responsible_q) }"
                type="button"
                aria-label="Фильтр по ответственному"
                title="Фильтр по ответственному"
                @click.stop="setActiveDealFilter(activeDealFilter === 'responsible' ? '' : 'responsible')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по ответственному"
                title="Сортировка по ответственному"
                @click.stop="toggleDealSort('responsible')"
                :class="getDealSortClass('responsible')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeDealFilter === 'responsible'" class="filter-pop filter-pop--center" @click.stop>
            <div class="field">
              <span class="label">Ответственный</span>
              <div class="check-list check-list--compact">
                <label v-for="name in responsibleOptions" :key="`deal-responsible-${name}`" class="check-item">
                  <input v-model="responsibleFilterValues" type="checkbox" :value="name" @change="applyDealMultiFilter" />
                  <span>{{ name }}</span>
                </label>
              </div>
            </div>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Ответственный"
            title="Потяните для изменения ширины"
            @mousedown.stop.prevent="startResize($event, 'responsible')"
          />
        </th>
        <th class="cell--tight deal-col-action">Действие</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="d in animatedDeals"
        :key="d.deal_id"
        class="clickable-row"
        :data-deal-id="d.deal_id"
        :data-lock-label="getDealLockLabel(d.deal_id)"
        :class="{
          'row-active': editDeal.open && editDeal.deal_id === d.deal_id,
          'row-refund': d.is_refund,
          'deal-row-flip-in': !isRemovingDealRow(d.deal_id) && isNewDealRow(d.deal_id),
          'deal-row-flip-out': isRemovingDealRow(d.deal_id),
          'deal-row-locked': isDealEditedByAnotherUser(d.deal_id),
        }"
        @click="onDealRowClick(d)"
      >
        <td
          :class="[
            'cell--tight',
            'deal-col-type',
            getDealTypeToneClass(d),
          ]"
        >
          {{ getDealTypeCellLabel(d) }}
        </td>
        <td class="deal-col-customer">{{ d.customer_nickname || '—' }}</td>
        <td class="cell--tight deal-col-region">{{ getDealProductCellLabel(d) }}</td>
        <td class="deal-col-date">
          <template v-if="dealShowCompleted">
            <div class="deal-date-lines">
              <div><span class="muted">Соз.:</span> {{ formatDateTimeMinutes(d.purchase_at || d.created_at) }}</div>
              <div><span class="muted">Зав.:</span> {{ d.completed_at ? formatDateTimeMinutes(d.completed_at) : '—' }}</div>
            </div>
          </template>
          <template v-else>
            {{ formatDateTimeMinutes(d.purchase_at || d.created_at) }}
          </template>
        </td>
        <td class="cell--tight deal-col-status">{{ d.flow_status || '—' }}</td>
        <td class="cell--tight deal-col-responsible">{{ d.responsible_username || '—' }}</td>
        <td class="cell--tight deal-col-action">
          <span
            v-if="isDealEditedByAnotherUser(d.deal_id)"
            class="deal-row-lock-label"
          >
            {{ getDealLockLabel(d.deal_id) }}
          </span>
          <button
            v-else-if="!dealShowCompleted && String(d.flow_status_code || '').toLowerCase() !== 'draft' && canCompleteDeal"
            class="mini-btn mini-btn--complete"
            type="button"
            @click.stop="onMarkDealCompletedClick($event, d)"
            :disabled="dealSaving || isDealEditedByAnotherUser(d.deal_id)"
          >
            <span v-if="dealSaving && dealCompletingId === d.deal_id" class="spinner spinner--small" aria-hidden="true"></span>
            {{ dealSaving && dealCompletingId === d.deal_id ? 'Завершаем...' : 'Завершить' }}
          </button>
          <button
            v-else-if="dealShowCompleted && canPressReturn && (d.deal_type_code === 'sale' || d.deal_type_code === 'rental') && !d.is_refund"
            class="mini-btn mini-btn--danger"
            type="button"
            @click.stop="markDealReturned(d)"
            :disabled="dealSaving || isDealEditedByAnotherUser(d.deal_id)"
          >
            <span v-if="dealSaving && dealCompletingId === d.deal_id" class="spinner spinner--small" aria-hidden="true"></span>
            {{ dealSaving && dealCompletingId === d.deal_id ? 'Возвращаем...' : 'Возврат' }}
          </button>
          <span v-else class="muted">—</span>
        </td>
      </tr>
      <tr v-if="!animatedDeals.length">
        <td :colspan="emptyColspan" class="muted">Пока нет сделок.</td>
      </tr>
    </tbody>
    </table>
  </div>
  <teleport to="body">
    <div ref="coinsContainerRef" class="deal-complete-coins-container" aria-hidden="true"></div>
  </teleport>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'

import {
  parseMultiValueFilterQuery,
  stringifyMultiValueFilterQuery,
  parseResponsibleFilterQuery,
  stringifyResponsibleFilterQuery,
} from '../dealsFilterUtils.js'
import { useResizableTableColumns } from '../useResizableTableColumns'

const tableEl = ref(null)
const coinsContainerRef = ref(null)
const highlightedDealRows = ref({})
const removingDealRows = ref({})
const removingDeals = ref([])
const knownDealsById = ref({})
const rowEnterTimers = new Map()
const rowLeaveTimers = new Map()
const knownDealIds = ref([])
const handledRealtimeTick = ref(0)
const { getColumnStyle, startResize } = useResizableTableColumns({
  tableRef: tableEl,
  storageKey: 'work.deals.columns.v1',
  columns: [
    { key: 'type', defaultWidth: 10, minWidth: 8 },
    { key: 'customer', defaultWidth: 23, minWidth: 16 },
    { key: 'region', defaultWidth: 10, minWidth: 8 },
    { key: 'date', defaultWidth: 17, minWidth: 12 },
    { key: 'status', defaultWidth: 12, minWidth: 9 },
    { key: 'responsible', defaultWidth: 14, minWidth: 10 },
    { key: 'action', defaultWidth: 14, minWidth: 10 },
  ],
})

const props = defineProps({
  sortedDeals: { type: Array, required: true },
  dealFilters: { type: Object, required: true },
  dealTypeOptions: { type: Array, required: true },
  dealFlowStatusOptions: { type: Array, required: true },
  responsibleOptions: { type: Array, required: true },
  regions: { type: Array, required: true },
  activeDealFilter: { type: String, default: '' },
  setActiveDealFilter: { type: Function, required: true },
  toggleDealSort: { type: Function, required: true },
  getDealSortClass: { type: Function, required: true },
  loadDeals: { type: Function, required: true },
  resetDealFilter: { type: Function, required: true },
  validateDealRange: { type: Function, required: true },
  dealFilterErrors: { type: Object, required: true },
  minDate: { type: String, required: true },
  maxDate: { type: String, required: true },
  editDeal: { type: Object, required: true },
  startEditDeal: { type: Function, required: true },
  dealEditingByDealId: { type: Object, default: () => ({}) },
  currentUsername: { type: String, default: '' },
  responsibleNameByUsername: { type: Object, default: () => ({}) },
  showDealWarning: { type: Function, default: null },
  formatDateTimeMinutes: { type: Function, required: true },
  dealShowCompleted: { type: Boolean, required: true },
  canDoAction: { type: Function, default: () => false },
  markDealCompleted: { type: Function, required: true },
  markDealReturned: { type: Function, required: true },
  dealSaving: { type: Boolean, required: true },
  dealCompletingId: { type: [Number, null], default: null },
  realtimeAnimationTick: { type: Number, default: 0 },
})

const emptyColspan = computed(() => 7)
const canCompleteDeal = computed(() => props.canDoAction('deals_active.change_status'))
const canPressReturn = computed(() => props.canDoAction('deals_completed.press_return'))
const animatedDeals = computed(() => {
  const base = Array.isArray(props.sortedDeals) ? props.sortedDeals : []
  if (!removingDeals.value.length) return base
  const present = new Set(base.map((deal) => deal?.deal_id).filter(Boolean))
  const leaving = removingDeals.value.filter((deal) => !present.has(deal?.deal_id))
  return [...base, ...leaving]
})

watch(
  () => props.sortedDeals,
  (nextDeals) => {
    // Анимации строк запускаем только когда список обновился после websocket-события.
    const allowRealtimeAnimation = Number(props.realtimeAnimationTick || 0) !== Number(handledRealtimeTick.value || 0)
    handledRealtimeTick.value = Number(props.realtimeAnimationTick || 0)
    const deals = Array.isArray(nextDeals) ? nextDeals : []
    const currentIds = deals.map((deal) => deal?.deal_id).filter(Boolean)
    const nextCache = { ...knownDealsById.value }
    for (const deal of deals) {
      if (deal?.deal_id) nextCache[deal.deal_id] = deal
    }
    knownDealsById.value = nextCache

    // На первом рендере только запоминаем текущий набор id без анимации.
    if (!knownDealIds.value.length) {
      knownDealIds.value = currentIds
      return
    }

    const previous = new Set(knownDealIds.value)
    const incoming = currentIds.filter((id) => !previous.has(id))
    const currentSet = new Set(currentIds)
    const removed = knownDealIds.value.filter((id) => !currentSet.has(id))

    if (!allowRealtimeAnimation) {
      // Для обычных обновлений (фильтры/переключения вкладок) отключаем визуальные эффекты.
      highlightedDealRows.value = {}
      removingDealRows.value = {}
      removingDeals.value = []
      for (const timer of rowEnterTimers.values()) clearTimeout(timer)
      for (const timer of rowLeaveTimers.values()) clearTimeout(timer)
      rowEnterTimers.clear()
      rowLeaveTimers.clear()
      knownDealIds.value = currentIds
      return
    }

    for (const id of incoming) {
      // Если строка вернулась до конца анимации удаления, отменяем удаление.
      const leaveTimer = rowLeaveTimers.get(id)
      if (leaveTimer) {
        clearTimeout(leaveTimer)
        rowLeaveTimers.delete(id)
      }
      if (removingDealRows.value[id]) {
        const nextRemoving = { ...removingDealRows.value }
        delete nextRemoving[id]
        removingDealRows.value = nextRemoving
        removingDeals.value = removingDeals.value.filter((deal) => deal?.deal_id !== id)
      }
      highlightedDealRows.value = { ...highlightedDealRows.value, [id]: true }
      const prevTimer = rowEnterTimers.get(id)
      if (prevTimer) clearTimeout(prevTimer)
      const timer = setTimeout(() => {
        const next = { ...highlightedDealRows.value }
        delete next[id]
        highlightedDealRows.value = next
        rowEnterTimers.delete(id)
      }, 1800)
      rowEnterTimers.set(id, timer)
    }

    for (const id of removed) {
      if (removingDealRows.value[id]) continue
      const removedDeal = knownDealsById.value[id]
      if (!removedDeal) continue

      removingDealRows.value = { ...removingDealRows.value, [id]: true }
      removingDeals.value = [...removingDeals.value, removedDeal]

      const prevLeaveTimer = rowLeaveTimers.get(id)
      if (prevLeaveTimer) clearTimeout(prevLeaveTimer)
      const leaveTimer = setTimeout(() => {
        const nextRemoving = { ...removingDealRows.value }
        delete nextRemoving[id]
        removingDealRows.value = nextRemoving
        removingDeals.value = removingDeals.value.filter((deal) => deal?.deal_id !== id)
        rowLeaveTimers.delete(id)
      }, 820)
      rowLeaveTimers.set(id, leaveTimer)
    }

    knownDealIds.value = currentIds
  },
  { immediate: true, deep: false },
)

onBeforeUnmount(() => {
  // Чистим таймеры входа/выхода строк при размонтировании таблицы.
  for (const timer of rowEnterTimers.values()) clearTimeout(timer)
  for (const timer of rowLeaveTimers.values()) clearTimeout(timer)
  rowEnterTimers.clear()
  rowLeaveTimers.clear()
})
const responsibleFilterValues = computed({
  get: () => parseResponsibleFilterQuery(props.dealFilters.responsible_q),
  set: (values) => {
    props.dealFilters.responsible_q = stringifyResponsibleFilterQuery(values)
  },
})

const typeFilterValues = computed({
  get: () => parseMultiValueFilterQuery(props.dealFilters.type_q),
  set: (values) => {
    // Держим в фильтре строку кодов, чтобы API получил единый формат.
    props.dealFilters.type_q = stringifyMultiValueFilterQuery(values)
  },
})

const statusFilterValues = computed({
  get: () => parseMultiValueFilterQuery(props.dealFilters.status_q),
  set: (values) => {
    // Формируем мультифильтр статусов для flow_status_q на уровне загрузки списка.
    props.dealFilters.status_q = stringifyMultiValueFilterQuery(values)
  },
})

// Применяет мультифильтр сразу после клика по чекбоксу, без отдельной кнопки.
function applyDealMultiFilter() {
  props.loadDeals(1)
}

function isNewDealRow(dealId) {
  return Boolean(highlightedDealRows.value?.[dealId])
}

function isRemovingDealRow(dealId) {
  return Boolean(removingDealRows.value?.[dealId])
}

function onDealRowClick(deal) {
  // Пока строка уходит с анимацией удаления, блокируем открытие модалки редактирования.
  if (isRemovingDealRow(deal?.deal_id)) return
  // Не даем открывать редактирование, если строку уже редактирует другой пользователь.
  if (isDealEditedByAnotherUser(deal?.deal_id)) {
    if (typeof props.showDealWarning === 'function') {
      props.showDealWarning(`Сделку сейчас редактирует ${getDealEditingActor(deal?.deal_id) || 'другой пользователь'}`)
    }
    return
  }
  props.startEditDeal(deal)
}

function getDealEditingActorUsername(dealId) {
  return String(props.dealEditingByDealId?.[dealId]?.actor || '').trim()
}

function getDealEditingActor(dealId) {
  const username = getDealEditingActorUsername(dealId)
  if (!username) return ''
  const byUsername = props.responsibleNameByUsername?.[username] || props.responsibleNameByUsername?.[username.toLowerCase()]
  const mapped = String(byUsername || '').trim()
  return mapped || username
}

function getDealLockLabel(dealId) {
  // Подпись для визуальной маски заблокированной строки в таблице.
  const actor = getDealEditingActor(dealId)
  return actor ? `Редактирует: ${actor}` : ''
}

function isDealEditedByAnotherUser(dealId) {
  const actorUsername = getDealEditingActorUsername(dealId)
  if (!actorUsername) return false
  const me = String(props.currentUsername || '').trim().toLowerCase()
  return actorUsername.toLowerCase() !== me
}

// Форматирует дату срока подписки в вид dd.mm.yyyy для колонки "Товар" в списке сделок.
function formatSubscriptionValidUntil(value) {
  if (!value) return ''
  const raw = String(value).trim()
  if (!raw) return ''
  const datePart = raw.includes('T') ? raw.slice(0, 10) : raw
  const chunks = datePart.split('-')
  if (chunks.length !== 3) return ''
  const [year, month, day] = chunks
  if (!year || !month || !day) return ''
  return `${day.padStart(2, '0')}.${month.padStart(2, '0')}.${year}`
}

// Собирает подпись товара в таблице: для подписки добавляем срок, чтобы менеджер видел нужную позицию сразу.
function getDealProductCellLabel(deal) {
  const title = String(deal?.product_title || '').trim()
  if (!title) return '—'
  const isRental = String(deal?.deal_type_code || '').toLowerCase() === 'rental'
  const hasTerm = Number(deal?.subscription_term_id || 0) > 0
  if (!isRental || !hasTerm) return title
  const validUntil = formatSubscriptionValidUntil(deal?.subscription_valid_until)
  if (!validUntil) return title
  return `${title} до ${validUntil}`
}

// Формирует подпись типа сделки: для покупки добавляем регион, для шеринга регион не показываем.
function getDealTypeCellLabel(deal) {
  const typeLabel = String(deal?.deal_type || '').trim() || '—'
  if (typeLabel === '—') return typeLabel
  const typeCode = String(deal?.deal_type_code || '').trim().toLowerCase()
  if (typeCode !== 'sale') return typeLabel
  const regionCode = String(deal?.region_code || '').trim().toUpperCase()
  if (!regionCode) return typeLabel
  return `${typeLabel} ${regionCode}`
}

// Возвращает класс цветовой подсветки типа сделки для колонки "Тип".
function getDealTypeToneClass(deal) {
  const typeCode = String(deal?.deal_type_code || '').trim().toLowerCase()
  if (typeCode === 'rental') return 'deal-type-cell--rental'
  if (typeCode === 'sale') return 'deal-type-cell--sale'
  return 'deal-type-cell--other'
}

function spawnCompletionCoins(originPoint) {
  const container = coinsContainerRef.value
  if (!container || !originPoint) return

  const buttonCenterX = Number(originPoint.x || 0)
  const buttonTop = Number(originPoint.y || 0)
  if (!buttonCenterX && !buttonTop) return
  const coinCount = 15 + Math.floor(Math.random() * 11)

  for (let i = 0; i < coinCount; i += 1) {
    setTimeout(() => {
      // Создаем "монету" и разбрасываем ее по дуге для эффекта завершения сделки.
      const coin = document.createElement('div')
      coin.className = 'deal-complete-coin'

      const spreadAngle = (Math.random() - 0.5) * Math.PI * 0.9
      const startOffset = (Math.random() - 0.5) * 20
      const upHeight = -100 - Math.random() * 80
      const midX = Math.sin(spreadAngle) * (50 + Math.random() * 60)
      const horizontalDistance = midX + (Math.sin(spreadAngle) * (30 + Math.random() * 40))
      const fallDistance = 350 + Math.random() * 150
      const midFallDistance = fallDistance * 0.5
      const duration = 1.2 + Math.random() * 0.6

      coin.style.left = `${buttonCenterX}px`
      coin.style.top = `${buttonTop}px`
      coin.style.setProperty('--start-x', `${startOffset}px`)
      coin.style.setProperty('--up-y', `${upHeight}px`)
      coin.style.setProperty('--mid-x', `${midX}px`)
      coin.style.setProperty('--fall-x', `${horizontalDistance}px`)
      coin.style.setProperty('--fall-y-mid', `${midFallDistance}px`)
      coin.style.setProperty('--fall-y', `${fallDistance}px`)
      coin.style.setProperty('--fall-x-end', `${horizontalDistance + ((Math.random() - 0.5) * 40)}px`)
      coin.style.setProperty('--fall-duration', `${duration}s`)

      container.appendChild(coin)
      setTimeout(() => coin.remove(), duration * 1000)
    }, i * 10)
  }
}

async function onMarkDealCompletedClick(event, deal) {
  // Координаты кнопки сохраняем до await, чтобы после ответа backend анимация знала точку старта.
  const triggerEl = event?.currentTarget
  const rect = triggerEl?.getBoundingClientRect?.()
  const originPoint = rect
    ? { x: rect.left + (rect.width / 2), y: rect.top }
    : null

  // Монеты запускаем только после успешного ответа backend о завершении сделки.
  const completedOk = await props.markDealCompleted(deal)
  if (completedOk) spawnCompletionCoins(originPoint)
}
</script>
