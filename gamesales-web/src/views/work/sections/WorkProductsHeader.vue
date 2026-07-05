<template>
  <div class="panel__head">
    <div>
      <div class="toolbar-actions">
        <button v-if="canCreateProducts" class="deal-create-btn" type="button" @click="openCreateGameProductModal" aria-label="Добавить игру" title="Добавить игру">
          <span class="deal-create-btn__text">Игра</span>
          <span class="deal-create-btn__icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
              <line y2="19" y1="5" x2="12" x1="12"></line>
              <line y2="12" y1="12" x2="19" x1="5"></line>
            </svg>
          </span>
        </button>
        <button v-if="canCreateProducts" class="deal-create-btn deal-create-btn--sharing" type="button" @click="openCreateSubscriptionProductModal" aria-label="Добавить подписку" title="Добавить подписку">
          <span class="deal-create-btn__text">Подписка</span>
          <span class="deal-create-btn__icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
              <line y2="19" y1="5" x2="12" x1="12"></line>
              <line y2="12" y1="12" x2="19" x1="5"></line>
            </svg>
          </span>
        </button>
        <label class="field field--compact">
          <input
            v-model.trim="productFilters.q"
            class="input input--compact"
            placeholder="название товара"
            @keydown.enter.prevent="applyProductSearch"
          />
        </label>
        <button class="product-search-btn" type="button" @click="applyProductSearch" aria-label="Найти" title="Найти">
          <span class="product-search-btn__content">
            <svg class="product-search-btn__icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 21l-4.2-4.2" />
              <circle cx="11" cy="11" r="7" />
            </svg>
          </span>
        </button>
      </div>
    </div>
    <div class="toolbar-actions">
      <button
        class="product-import-btn"
        type="button"
        title="Импорт товаров"
        aria-label="Импорт товаров"
        @click="openProductImport"
      >
        <span class="product-import-btn__content">
          <svg class="product-import-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </span>
      </button>
      <button
        class="product-export-btn"
        type="button"
        title="Выгрузка товаров будет позже"
        aria-label="Выгрузка товаров будет позже"
        :disabled="true"
      >
        <span class="product-export-btn__content">
          <svg class="product-export-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </span>
      </button>
      <button
        class="product-refresh-btn"
        type="button"
        title="Обновить список"
        aria-label="Обновить список"
        @click="loadProducts"
        :disabled="productsLoading"
      >
        <span class="product-refresh-btn__content">
          <svg class="product-refresh-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 12a8 8 0 1 1-2.3-5.7" />
            <path d="M20 4v6h-6" />
          </svg>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  productFilters: { type: Object, required: true },
  applyProductSearch: { type: Function, required: true },
  canCreateProducts: { type: Boolean, default: true },
  openCreateGameProductModal: { type: Function, required: true },
  openCreateSubscriptionProductModal: { type: Function, required: true },
  openProductImport: { type: Function, required: true },
  loadProducts: { type: Function, required: true },
  productsLoading: { type: Boolean, required: true },
})
</script>
