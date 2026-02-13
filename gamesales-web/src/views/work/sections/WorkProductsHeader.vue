<template>
  <div class="panel__head">
    <div>
      <div class="toolbar-actions">
        <button class="deal-create-btn" type="button" @click="openCreateProductModal" aria-label="Добавить товар" title="Добавить товар">
          <span class="deal-create-btn__text">Товар</span>
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
        <button class="btn btn--icon btn--glow btn--glow-filter" type="button" @click="applyProductSearch" aria-label="Найти" title="Найти">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 21l-4.2-4.2" />
            <circle cx="11" cy="11" r="7" />
          </svg>
        </button>
      </div>
    </div>
    <div class="toolbar-actions">
      <button
        class="btn btn--icon btn--glow btn--glow-import"
        title="Импорт товаров"
        aria-label="Импорт товаров"
        @click="openProductImport"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3v12" />
          <path d="M7 10l5 5 5-5" />
          <path d="M5 21h14" />
        </svg>
      </button>
      <button
        class="btn btn--icon btn--glow btn--glow-export"
        title="Выгрузка товаров будет позже"
        aria-label="Выгрузка товаров будет позже"
        :disabled="true"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 21V9" />
          <path d="M7 14l5-5 5 5" />
          <path d="M5 3h14" />
        </svg>
      </button>
      <button
        class="btn btn--icon btn--glow btn--glow-refresh"
        title="Обновить список"
        aria-label="Обновить список"
        @click="loadProducts"
        :disabled="productsLoading"
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
defineProps({
  productFilters: { type: Object, required: true },
  applyProductSearch: { type: Function, required: true },
  openCreateProductModal: { type: Function, required: true },
  openProductImport: { type: Function, required: true },
  loadProducts: { type: Function, required: true },
  productsLoading: { type: Boolean, required: true },
})
</script>
