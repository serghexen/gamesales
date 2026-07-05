<template>
  <div class="panel__head panel__head--accounts">
    <div class="account-head-primary">
      <div class="account-head-row">
        <div class="toolbar-actions toolbar-actions--account-create">
          <button v-if="canCreateAccount" class="deal-create-btn" type="button" @click="openCreateAccountModal" aria-label="Новый аккаунт" title="Новый аккаунт">
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
              placeholder="покупатель, номер заказа, почта, домен, регион, игра"
              @keydown.enter.prevent="applyAccountSearch"
            />
          </label>
          <button
            class="account-search-btn"
            type="button"
            @click="applyAccountSearch"
            aria-label="Найти"
            title="Найти"
          >
            <span class="account-search-btn__content">
              <svg class="account-search-btn__icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 21l-4.2-4.2" />
                <circle cx="11" cy="11" r="7" />
              </svg>
            </span>
          </button>
        </div>
      </div>
    </div>
    <div class="toolbar-actions toolbar-actions--account-tools">
      <span
        v-if="slotsExportMessage || slotsExportError"
        class="account-export-status"
        :class="{ 'account-export-status--error': slotsExportError }"
        role="status"
        aria-live="polite"
      >
        {{ slotsExportError || slotsExportMessage }}
      </span>
      <button
        class="account-import-btn account-import-btn--accounts"
        type="button"
        title="Импорт аккаунтов"
        aria-label="Импорт аккаунтов"
        @click="openAccountImport"
      >
        <span class="account-import-btn__content">
          <svg class="account-import-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </span>
      </button>
      <button
        class="account-import-btn account-import-btn--slots"
        type="button"
        title="Импорт слотов"
        aria-label="Импорт слотов"
        @click="openSlotImport"
      >
        <span class="account-import-btn__content">
          <svg class="account-import-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </span>
      </button>
      <button
        class="account-import-btn account-import-btn--slots-export"
        type="button"
        :title="slotsExportLoading ? 'Формируем XLSX…' : 'Выгрузить историю слотов'"
        :aria-label="slotsExportLoading ? 'Формируется выгрузка слотов' : 'Выгрузить историю слотов'"
        :disabled="slotsExportLoading"
        :aria-busy="slotsExportLoading"
        @click="downloadSlotsExport"
      >
        <span class="account-import-btn__content">
          <span v-if="slotsExportLoading" class="spinner spinner--small" aria-hidden="true"></span>
          <svg v-else class="account-import-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </span>
      </button>
      <button
        class="account-refresh-btn"
        type="button"
        aria-label="Обновить список"
        title="Обновить список"
        @click="loadAccounts"
        :disabled="accountsLoading"
      >
        <span class="account-refresh-btn__content">
          <svg class="account-refresh-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
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
  accountFilters: { type: Object, required: true },
  applyAccountSearch: { type: Function, required: true },
  canCreateAccount: { type: Boolean, default: true },
  openCreateAccountModal: { type: Function, required: true },
  openAccountImport: { type: Function, required: true },
  openSlotImport: { type: Function, required: true },
  downloadSlotsExport: { type: Function, required: true },
  slotsExportLoading: { type: Boolean, required: true },
  slotsExportMessage: { type: String, default: '' },
  slotsExportError: { type: String, default: '' },
  loadAccounts: { type: Function, required: true },
  accountsLoading: { type: Boolean, required: true },
})
</script>
