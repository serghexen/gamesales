<template>
  <table ref="tableEl" class="table" :class="{ 'table--completed': dealShowCompleted, 'table--pending': !dealShowCompleted }">
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
            Регион
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(dealFilters.region_q) }"
                type="button"
                aria-label="Фильтр по региону"
                title="Фильтр по региону"
                @click.stop="setActiveDealFilter(activeDealFilter === 'region' ? '' : 'region')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по региону"
                title="Сортировка по региону"
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
          <div v-if="activeDealFilter === 'region'" class="filter-pop filter-pop--center" @click.stop>
            <div class="field">
              <span class="label">Регион</span>
              <div class="check-list check-list--compact">
                <label v-for="r in regions" :key="`deal-region-${r.code}`" class="check-item">
                  <input v-model="regionFilterValues" type="checkbox" :value="r.code" @change="applyDealMultiFilter" />
                  <span>{{ r.name }} ({{ r.code }})</span>
                </label>
              </div>
            </div>
          </div>
          <button
            class="table-col-resizer"
            type="button"
            aria-label="Изменить ширину колонки Регион"
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
            {{ dealShowCompleted ? 'Ответств.' : 'Ответ.' }}
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
        v-for="d in sortedDeals"
        :key="d.deal_id"
        class="clickable-row"
        :class="{ 'row-active': editDeal.open && editDeal.deal_id === d.deal_id, 'row-refund': d.is_refund }"
        @click="startEditDeal(d)"
      >
        <td class="cell--tight deal-col-type">{{ d.deal_type || '—' }}</td>
        <td class="deal-col-customer">{{ d.customer_nickname || '—' }}</td>
        <td class="cell--tight deal-col-region">{{ d.region_code || '—' }}</td>
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
          <button
            v-if="!dealShowCompleted"
            class="mini-btn mini-btn--complete"
            type="button"
            @click.stop="onMarkDealCompletedClick($event, d)"
            :disabled="dealSaving"
          >
            <span v-if="dealSaving && dealCompletingId === d.deal_id" class="spinner spinner--small" aria-hidden="true"></span>
            {{ dealSaving && dealCompletingId === d.deal_id ? 'Завершаем...' : 'Завершить' }}
          </button>
          <button
            v-else-if="d.deal_type_code === 'sale' && !d.is_refund"
            class="mini-btn mini-btn--danger"
            type="button"
            @click.stop="markDealReturned(d)"
            :disabled="dealSaving"
          >
            <span v-if="dealSaving && dealCompletingId === d.deal_id" class="spinner spinner--small" aria-hidden="true"></span>
            {{ dealSaving && dealCompletingId === d.deal_id ? 'Возвращаем...' : 'Возврат' }}
          </button>
          <span v-else class="muted">—</span>
        </td>
      </tr>
      <tr v-if="!sortedDeals.length">
        <td :colspan="emptyColspan" class="muted">Пока нет сделок.</td>
      </tr>
    </tbody>
  </table>
  <teleport to="body">
    <div ref="coinsContainerRef" class="deal-complete-coins-container" aria-hidden="true"></div>
  </teleport>
</template>

<script setup>
import { computed, ref } from 'vue'

import {
  parseMultiValueFilterQuery,
  stringifyMultiValueFilterQuery,
  parseResponsibleFilterQuery,
  stringifyResponsibleFilterQuery,
} from '../dealsFilterUtils.js'
import { useResizableTableColumns } from '../useResizableTableColumns'

const tableEl = ref(null)
const coinsContainerRef = ref(null)
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
  formatDateTimeMinutes: { type: Function, required: true },
  dealShowCompleted: { type: Boolean, required: true },
  markDealCompleted: { type: Function, required: true },
  markDealReturned: { type: Function, required: true },
  dealSaving: { type: Boolean, required: true },
  dealCompletingId: { type: [Number, null], default: null },
})

const emptyColspan = computed(() => 7)
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

const regionFilterValues = computed({
  get: () => parseMultiValueFilterQuery(props.dealFilters.region_q),
  set: (values) => {
    // Храним выбранные регионы в строке через запятую как и другие мультифильтры.
    props.dealFilters.region_q = stringifyMultiValueFilterQuery(values)
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
