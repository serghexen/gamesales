<template>
  <div class="panel__head">
    <div>
      <div class="account-head-row">
        <div class="toolbar-actions toolbar-actions--account-create">
          <button class="deal-create-btn" type="button" @click="openCreateAccountModal" aria-label="Новый аккаунт" title="Новый аккаунт">
            <span class="deal-create-btn__text">Аккаунт</span>
            <span class="deal-create-btn__icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                <line y2="19" y1="5" x2="12" x1="12"></line>
                <line y2="12" y1="12" x2="19" x1="5"></line>
              </svg>
            </span>
          </button>
        </div>
        <div class="toolbar-actions toolbar-actions--account-search">
          <label class="field field--compact">
            <input
              v-model.trim="accountFilters.search_q"
              class="input input--compact input--account-search"
              placeholder="почта, домен, регион, игра"
              @keydown.enter.prevent="applyAccountSearch"
            />
          </label>
          <button
            class="btn btn--icon btn--glow btn--glow-filter"
            type="button"
            @click="applyAccountSearch"
            aria-label="Найти"
            title="Найти"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 21l-4.2-4.2" />
              <circle cx="11" cy="11" r="7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div class="toolbar-actions">
      <button
        class="btn btn--icon btn--glow btn--glow-import"
        title="Импорт аккаунтов"
        aria-label="Импорт аккаунтов"
        @click="openAccountImport"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3v12" />
          <path d="M7 10l5 5 5-5" />
          <path d="M5 21h14" />
        </svg>
      </button>
      <button
        class="btn btn--icon btn--glow btn--glow-import-slots"
        title="Импорт слотов"
        aria-label="Импорт слотов"
        @click="openSlotImport"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3v12" />
          <path d="M7 10l5 5 5-5" />
          <path d="M5 21h14" />
        </svg>
      </button>
      <button
        class="btn btn--icon btn--glow btn--glow-refresh"
        aria-label="Обновить список"
        title="Обновить список"
        @click="loadAccounts"
        :disabled="accountsLoading"
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
  accountFilters: { type: Object, required: true },
  applyAccountSearch: { type: Function, required: true },
  openCreateAccountModal: { type: Function, required: true },
  openAccountImport: { type: Function, required: true },
  openSlotImport: { type: Function, required: true },
  loadAccounts: { type: Function, required: true },
  accountsLoading: { type: Boolean, required: true },
})
</script>
