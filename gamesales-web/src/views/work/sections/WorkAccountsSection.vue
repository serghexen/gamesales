<template>
  <section class="panel panel--wide">
    <WorkAccountsHeader
      :account-filters="ctx.accountFilters"
      :apply-account-search="ctx.applyAccountSearch"
      :open-create-account-modal="ctx.openCreateAccountModal"
      :open-account-import="ctx.openAccountImport"
      :open-slot-import="ctx.openSlotImport"
      :load-accounts="ctx.loadAccounts"
      :accounts-loading="ctx.accountsLoading"
    />
    <div class="panel__body">
      <div v-if="ctx.accountsLoading" class="loader-wrap loader-overlay">
        <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster">
          <div class="wheel"></div>
          <div class="hamster">
            <div class="hamster__body">
              <div class="hamster__head">
                <div class="hamster__ear"></div>
                <div class="hamster__eye"></div>
                <div class="hamster__nose"></div>
              </div>
              <div class="hamster__limb hamster__limb--fr"></div>
              <div class="hamster__limb hamster__limb--fl"></div>
              <div class="hamster__limb hamster__limb--br"></div>
              <div class="hamster__limb hamster__limb--bl"></div>
              <div class="hamster__tail"></div>
            </div>
          </div>
          <div class="spoke"></div>
        </div>
      </div>

      <WorkAccountFilterChips
        v-else-if="ctx.activeAccountChips.length"
        :active-account-chips="ctx.activeAccountChips"
        :reset-account-filter="ctx.resetAccountFilter"
      />

      <WorkAccountImportModal
        :show-account-import="ctx.showAccountImport"
        :close-account-import="ctx.closeAccountImport"
        :modal-ref="ctx.modalRef"
        :modal-style="ctx.modalStyle"
        :start-modal-drag="ctx.startModalDrag"
        :account-import-loading="ctx.accountImportLoading"
        :download-account-template="ctx.downloadAccountTemplate"
        :validate-account-import="ctx.validateAccountImport"
        :account-import-file="ctx.accountImportFile"
        :account-import-action="ctx.accountImportAction"
        :upload-account-import="ctx.uploadAccountImport"
        :account-import-validated="ctx.accountImportValidated"
        :account-import-job-id="ctx.accountImportJobId"
        :cancel-account-import="ctx.cancelAccountImport"
        :scroll-to-account-import-details="ctx.scrollToAccountImportDetails"
        :account-import-progress="ctx.accountImportProgress"
        :on-account-import-file="ctx.onAccountImportFile"
        :account-import-details-ref="ctx.accountImportDetailsRef"
        :account-import-message="ctx.accountImportMessage"
        :account-import-errors="ctx.accountImportErrors"
        :account-import-warnings="ctx.accountImportWarnings"
        :download-account-import-report="ctx.downloadAccountImportReport"
        :account-import-stats="ctx.accountImportStats"
      />

      <WorkAccountsTableSection
        :sorted-accounts="ctx.sortedAccounts"
        :account-filters="ctx.accountFilters"
        :active-account-filter="ctx.activeAccountFilter"
        :account-filter-draft="ctx.accountFilterDraft"
        :open-account-filter="ctx.openAccountFilter"
        :toggle-account-sort="ctx.toggleAccountSort"
        :get-account-sort-class="ctx.getAccountSortClass"
        :apply-account-filter="ctx.applyAccountFilter"
        :reset-account-filter="ctx.resetAccountFilter"
        :start-edit-account="ctx.startEditAccount"
        :format-account-products-line="ctx.formatAccountProductsLine"
        :get-account-slot-status-list="ctx.getAccountSlotStatusList"
        :format-account-slot-status-line="ctx.formatAccountSlotStatusLine"
        :format-secret="ctx.formatSecret"
        :get-reserve-secrets="ctx.getReserveSecrets"
      />
      <div v-if="ctx.accountsTotal > 0" class="pager">
        <span class="muted">Всего: {{ ctx.accountsTotal }}</span>
        <label class="pager__size">
          <span class="muted">Показывать</span>
          <select v-model.number="ctx.accountsPageSize" class="input input--select input--compact">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </label>
        <button class="ghost" @click="ctx.setAccountsPage(1)" :disabled="ctx.accountsPage <= 1">
          «
        </button>
        <button class="ghost" @click="ctx.prevAccountsPage" :disabled="ctx.accountsPage <= 1">
          ← Назад
        </button>
        <label class="pager__jump">
          <span class="muted">Стр.</span>
          <input
            v-model.number="ctx.accountsPageInput"
            class="input input--compact input--page"
            type="number"
            min="1"
            :max="ctx.accountsTotalPages"
            @keydown.enter.prevent="ctx.jumpAccountsPage"
            @blur="ctx.jumpAccountsPage"
          />
        </label>
        <span class="muted">из {{ ctx.accountsTotalPages }}</span>
        <button class="ghost" @click="ctx.nextAccountsPage" :disabled="ctx.accountsPage >= ctx.accountsTotalPages">
          Вперёд →
        </button>
        <button class="ghost" @click="ctx.setAccountsPage(ctx.accountsTotalPages)" :disabled="ctx.accountsPage >= ctx.accountsTotalPages">
          »
        </button>
      </div>

      <div class="divider"></div>

      <WorkAccountEditorModal
        :edit-account="ctx.editAccount"
        :can-toggle-deactivation="ctx.canToggleAccountDeactivation"
        :cancel-edit-account="ctx.cancelEditAccount"
        :modal-ref="ctx.modalRef"
        :modal-style="ctx.modalStyle"
        :start-modal-drag="ctx.startModalDrag"
        :account-modal-mode="ctx.accountModalMode"
        :account-edit-mode="ctx.accountEditMode"
        :set-account-edit-mode="ctx.setAccountEditMode"
        :toggle-account-edit-mode="ctx.toggleAccountEditMode"
        :update-account="ctx.updateAccount"
        :accounts-loading="ctx.accountsLoading"
        :account-saving="ctx.accountSaving"
        :create-account="ctx.createAccount"
        :delete-account="ctx.deleteAccount"
        :account-products-loading="ctx.accountProductsLoading"
        :get-domain-label="ctx.getDomainLabel"
        :domains="ctx.domains"
        :get-region-label="ctx.getRegionLabel"
        :regions="ctx.regions"
        :get-account-status-label="ctx.getAccountStatusLabel"
        :max-date="ctx.maxDate"
        :account-product-titles="ctx.accountProductTitles"
        :edit-account-product-search="ctx.editAccountProductSearch"
        :set-edit-account-product-search="ctx.setEditAccountProductSearch"
        :edit-account-product-type="ctx.editAccountProductType"
        :set-edit-account-product-type="ctx.setEditAccountProductType"
        :filtered-edit-account-products="ctx.filteredEditAccountProducts"
        :account-slot-assignments-error="ctx.accountSlotAssignmentsError"
        :account-slot-assignments-loading="ctx.accountSlotAssignmentsLoading"
        :account-slot-assignments="ctx.accountSlotAssignments"
        :sorted-account-slot-assignments="ctx.sortedAccountSlotAssignments"
        :get-slot-type-label="ctx.getSlotTypeLabel"
        :get-slot-assignment-status="ctx.getSlotAssignmentStatus"
        :format-date-time-minutes="ctx.formatDateTimeMinutes"
        :account-slot-release-loading="ctx.accountSlotReleaseLoading"
        :release-slot-assignment="ctx.releaseSlotAssignment"
        :account-deals-error="ctx.accountDealsError"
        :account-deals-loading="ctx.accountDealsLoading"
        :account-deals="ctx.accountDeals"
        :get-deal-product-title-tooltip="ctx.getDealProductTitleTooltip"
        :get-deal-product-title-display="ctx.getDealProductTitleDisplay"
        :format-date="ctx.formatDate"
        :accounts-error="ctx.accountsError"
        :accounts-ok="ctx.accountsOk"
        :new-account="ctx.newAccount"
        :account-product-search="ctx.accountProductSearch"
        :set-account-product-search="ctx.setAccountProductSearch"
        :account-product-type="ctx.accountProductType"
        :set-account-product-type="ctx.setAccountProductType"
        :filtered-account-products="ctx.filteredAccountProducts"
      />

      <WorkSlotImportModal
        :show-slot-import="ctx.showSlotImport"
        :close-slot-import="ctx.closeSlotImport"
        :modal-ref="ctx.modalRef"
        :modal-style="ctx.modalStyle"
        :start-modal-drag="ctx.startModalDrag"
        :slot-import-loading="ctx.slotImportLoading"
        :validate-slot-import="ctx.validateSlotImport"
        :slot-import-file="ctx.slotImportFile"
        :upload-slot-import="ctx.uploadSlotImport"
        :slot-import-validated="ctx.slotImportValidated"
        :slot-import-action="ctx.slotImportAction"
        :clean-slot-import="ctx.cleanSlotImport"
        :slot-import-job-id="ctx.slotImportJobId"
        :cancel-slot-import="ctx.cancelSlotImport"
        :slot-import-progress="ctx.slotImportProgress"
        :on-slot-import-file="ctx.onSlotImportFile"
        :slot-import-limit="ctx.slotImportLimit"
        :set-slot-import-limit="ctx.setSlotImportLimit"
        :slot-import-errors="ctx.slotImportErrors"
        :slot-import-warnings="ctx.slotImportWarnings"
        :download-slot-import-report="ctx.downloadSlotImportReport"
        :slot-import-total="ctx.slotImportTotal"
        :slot-import-stats="ctx.slotImportStats"
        :slot-import-message="ctx.slotImportMessage"
        :slot-import-error="ctx.slotImportError"
      />
    </div>
  </section>
</template>

<script setup>
import WorkAccountsHeader from './WorkAccountsHeader.vue'
import WorkAccountFilterChips from './WorkAccountFilterChips.vue'
import WorkAccountImportModal from './WorkAccountImportModal.vue'
import WorkAccountsTableSection from './WorkAccountsTableSection.vue'
import WorkAccountEditorModal from './WorkAccountEditorModal.vue'
import WorkSlotImportModal from './WorkSlotImportModal.vue'

// Контекст секции аккаунтов: таблица, фильтры, пагинация и модалки.
defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})
</script>
