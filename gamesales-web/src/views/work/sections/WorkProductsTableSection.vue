<template>
  <table v-if="sortedProducts.length" class="table table--compact">
    <thead>
      <tr>
        <th>
          <span class="th-title th-title--filter">
            Товар
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(productFilters.q) }"
                type="button"
                aria-label="Фильтр по товару"
                title="Фильтр по товару"
                @click.stop="openProductFilter('title')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по товару"
                title="Сортировка по товару"
                @click.stop="toggleProductsSort('title')"
                :class="getProductsSortClass('title')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeProductFilter === 'title'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Товар</span>
              <input v-model.trim="productFilterDraft.title" class="input" placeholder="товар" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyProductFilter('title')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetProductFilter('title')">Сбросить</button>
          </div>
        </th>
        <th>
          <span class="th-title th-title--filter">
            Тип
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(productFilters.type_code) }"
                type="button"
                aria-label="Фильтр по типу"
                title="Фильтр по типу"
                @click.stop="openProductFilter('type')"
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
                @click.stop="toggleProductsSort('type')"
                :class="getProductsSortClass('type')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeProductFilter === 'type'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Тип</span>
              <select v-model="productFilterDraft.type" class="input input--select">
                <option value="">— любой —</option>
                <option :value="PRODUCT_TYPE_PRIMARY">Игра</option>
                <option value="subscription">Подписка</option>
              </select>
            </label>
            <button class="ghost ghost--small" type="button" @click="applyProductFilter('type')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetProductFilter('type')">Сбросить</button>
          </div>
        </th>
        <th>Короткое</th>
        <th>
          <span class="th-title th-title--filter">
            Платформа
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(productFilters.platform_code) }"
                type="button"
                aria-label="Фильтр по платформе"
                title="Фильтр по платформе"
                @click.stop="openProductFilter('platform')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по платформе"
                title="Сортировка по платформе"
                @click.stop="toggleProductsSort('platform')"
                :class="getProductsSortClass('platform')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeProductFilter === 'platform'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Платформа</span>
              <input v-model.trim="productFilterDraft.platform" class="input" placeholder="платформа" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyProductFilter('platform')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetProductFilter('platform')">Сбросить</button>
          </div>
        </th>
        <th>
          <span class="th-title th-title--filter">
            Регион
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(productFilters.region_code) }"
                type="button"
                aria-label="Фильтр по региону"
                title="Фильтр по региону"
                @click.stop="openProductFilter('region')"
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
                @click.stop="toggleProductsSort('region')"
                :class="getProductsSortClass('region')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeProductFilter === 'region'" class="filter-pop filter-pop--right" @click.stop>
            <label class="field">
              <span class="label">Регион</span>
              <input v-model.trim="productFilterDraft.region" class="input" placeholder="регион" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyProductFilter('region')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetProductFilter('region')">Сбросить</button>
          </div>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="g in pagedProducts" :key="g.product_id" class="clickable-row" @click="openProductAccounts(g)">
        <td>{{ g.title }}</td>
        <td>{{ formatTypeLabel(g.type_code) }}</td>
        <td>{{ g.short_title || '—' }}</td>
        <td>{{ formatProductPlatforms(g.platform_codes) }}</td>
        <td>{{ g.region_code || '—' }}</td>
      </tr>
    </tbody>
  </table>
  <p v-else class="muted">Пока нет товаров.</p>
</template>

<script setup>
import { PRODUCT_TYPE_PRIMARY } from '../domainUtils'

function formatTypeLabel(typeCode) {
  if (typeCode === PRODUCT_TYPE_PRIMARY) return 'Игра'
  if (typeCode === 'subscription') return 'Подписка'
  return typeCode || '—'
}

defineProps({
  sortedProducts: { type: Array, required: true },
  pagedProducts: { type: Array, required: true },
  productFilters: { type: Object, required: true },
  activeProductFilter: { type: String, default: '' },
  productFilterDraft: { type: Object, required: true },
  openProductFilter: { type: Function, required: true },
  toggleProductsSort: { type: Function, required: true },
  getProductsSortClass: { type: Function, required: true },
  applyProductFilter: { type: Function, required: true },
  resetProductFilter: { type: Function, required: true },
  formatProductPlatforms: { type: Function, required: true },
  openProductAccounts: { type: Function, required: true },
})
</script>
