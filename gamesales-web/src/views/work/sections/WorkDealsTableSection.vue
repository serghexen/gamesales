<template>
  <table class="table" :class="{ 'table--completed': dealShowCompleted, 'table--pending': !dealShowCompleted }">
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
            <label class="field">
              <span class="label">Тип</span>
              <select v-model="dealFilters.type_q" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="t in dealTypeOptions" :key="t.code" :value="t.code">
                  {{ t.name }}
                </option>
              </select>
            </label>
            <button class="ghost ghost--small" type="button" @click="loadDeals(1); setActiveDealFilter('')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('type')">Сбросить</button>
          </div>
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
            <label class="field">
              <span class="label">Регион</span>
              <select v-model="dealFilters.region_q" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="r in regions" :key="r.code" :value="r.code">
                  {{ r.name }} ({{ r.code }})
                </option>
              </select>
            </label>
            <button class="ghost ghost--small" type="button" @click="loadDeals(1); setActiveDealFilter('')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('region')">Сбросить</button>
          </div>
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
            <label class="field">
              <span class="label">Статус</span>
              <select v-model="dealFilters.status_q" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="s in dealFlowStatusOptions" :key="s.code" :value="s.code">
                  {{ s.name }}
                </option>
              </select>
            </label>
            <button class="ghost ghost--small" type="button" @click="loadDeals(1); setActiveDealFilter('')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('status')">Сбросить</button>
          </div>
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
                  <input v-model="responsibleFilterValues" type="checkbox" :value="name" />
                  <span>{{ name }}</span>
                </label>
              </div>
            </div>
            <button class="ghost ghost--small" type="button" @click="loadDeals(1); setActiveDealFilter('')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetDealFilter('responsible')">Сбросить</button>
          </div>
        </th>
        <th v-if="!dealShowCompleted" class="cell--tight deal-col-action">Действие</th>
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
              <div><span class="muted">Создана:</span> {{ formatDateTimeMinutes(d.purchase_at || d.created_at) }}</div>
              <div><span class="muted">Завершена:</span> {{ d.completed_at ? formatDateTimeMinutes(d.completed_at) : '—' }}</div>
            </div>
          </template>
          <template v-else>
            {{ formatDateTimeMinutes(d.purchase_at || d.created_at) }}
          </template>
        </td>
        <td class="cell--tight deal-col-status">{{ d.flow_status || '—' }}</td>
        <td class="cell--tight deal-col-responsible">{{ d.responsible_username || '—' }}</td>
        <td v-if="!dealShowCompleted" class="cell--tight deal-col-action">
          <button class="mini-btn" type="button" @click.stop="markDealCompleted(d)" :disabled="dealSaving">
            <span v-if="dealSaving && dealCompletingId === d.deal_id" class="spinner spinner--small" aria-hidden="true"></span>
            {{ dealSaving && dealCompletingId === d.deal_id ? 'Завершаем...' : 'Завершить' }}
          </button>
        </td>
      </tr>
      <tr v-if="!sortedDeals.length">
        <td :colspan="emptyColspan" class="muted">Пока нет сделок.</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
import { computed } from 'vue'

import { parseResponsibleFilterQuery, stringifyResponsibleFilterQuery } from '../dealsFilterUtils.js'

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
  dealSaving: { type: Boolean, required: true },
  dealCompletingId: { type: [Number, null], default: null },
})

const emptyColspan = computed(() => (props.dealShowCompleted ? 6 : 7))
const responsibleFilterValues = computed({
  get: () => parseResponsibleFilterQuery(props.dealFilters.responsible_q),
  set: (values) => {
    props.dealFilters.responsible_q = stringifyResponsibleFilterQuery(values)
  },
})
</script>
