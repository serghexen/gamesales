<template>
  <div class="panel__head">
    <div class="panel__head-col">
      <div class="deal-head-row">
        <div class="toolbar-actions toolbar-actions--deal-create">
          <button class="deal-create-btn" type="button" @click="openCreateSaleModal" aria-label="Новая продажа" title="Новая продажа">
            <span class="deal-create-btn__text">Продажа</span>
            <span class="deal-create-btn__icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                <line y2="19" y1="5" x2="12" x1="12"></line>
                <line y2="12" y1="12" x2="19" x1="5"></line>
              </svg>
            </span>
          </button>
          <button class="deal-create-btn deal-create-btn--sharing" type="button" @click="openCreateSharingModal" aria-label="Новый шеринг" title="Новый шеринг">
            <span class="deal-create-btn__text">Шеринг</span>
            <span class="deal-create-btn__icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                <line y2="19" y1="5" x2="12" x1="12"></line>
                <line y2="12" y1="12" x2="19" x1="5"></line>
              </svg>
            </span>
          </button>
        </div>
        <div class="toolbar-actions toolbar-actions--deal-search">
          <label class="field field--compact">
            <input
              v-model.trim="dealFilters.search_q"
              class="input input--compact input--deal-search"
              placeholder="покупатель, регион, дата, статус, тип"
              @keydown.enter.prevent="applyDealSearch"
            />
          </label>
          <button class="btn btn--icon btn--glow btn--glow-filter" type="button" @click="applyDealSearch" aria-label="Найти" title="Найти">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 21l-4.2-4.2" />
              <circle cx="11" cy="11" r="7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div class="toolbar-actions">
      <div class="switch-wrap">
        <label class="switch">
          <input v-model="dealShowCompletedModel" type="checkbox" @change="loadDeals(1)" />
          <div class="slider">
            <div class="circle">
              <svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true">
                <path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path>
              </svg>
              <svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path>
              </svg>
            </div>
          </div>
        </label>
        <span class="switch-label">Показать завершенные</span>
      </div>
      <button
        class="btn btn--icon btn--glow btn--glow-refresh"
        title="Обновить список"
        aria-label="Обновить список"
        @click="loadDeals(1)"
        :disabled="dealListLoading"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 12a8 8 0 1 1-2.3-5.7" />
          <path d="M20 4v6h-6" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isAdmin: { type: Boolean, default: false },
  dealsRealtimeStatus: { type: String, default: 'offline' },
  dealFilters: { type: Object, required: true },
  applyDealSearch: { type: Function, required: true },
  openCreateSaleModal: { type: Function, required: true },
  openCreateSharingModal: { type: Function, required: true },
  dealShowCompleted: { type: Boolean, required: true },
  setDealShowCompleted: { type: Function, required: true },
  loadDeals: { type: Function, required: true },
  dealListLoading: { type: Boolean, required: true },
})

const dealShowCompletedModel = computed({
  get: () => props.dealShowCompleted,
  set: (value) => props.setDealShowCompleted(value),
})

</script>
