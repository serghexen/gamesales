<template>
  <section class="panel panel--wide">
    <WorkDealsHeader
      :is-admin="ctx.isAdmin"
      :deals-realtime-status="ctx.dealsRealtimeStatus"
      :deal-filters="ctx.dealFilters"
      :apply-deal-search="ctx.applyDealSearch"
      :can-create-deals="canDoAction('deals_active.create')"
      :can-create-sale-deals="canDoAction('deals_active.create') && canDoAction('deals_active.new.sale.create')"
      :can-create-sharing-deals="canDoAction('deals_active.create') && canDoAction('deals_active.new.rental.create')"
      :can-view-completed-deals="canDoAction('deals_completed.view')"
      :open-create-sale-modal="ctx.openCreateSaleModal"
      :open-create-sharing-modal="ctx.openCreateSharingModal"
      :deal-show-completed="ctx.dealShowCompleted"
      :set-deal-show-completed="ctx.setDealShowCompleted"
      :load-deals="ctx.loadDeals"
      :deal-list-loading="ctx.dealListLoading"
    />

    <div class="panel__body">
      <p v-if="ctx.dealListError" class="bad">{{ ctx.dealListError }}</p>
      <p v-if="ctx.dealError" class="bad">{{ ctx.dealError }}</p>
      <p v-if="ctx.dealOk" class="ok">{{ ctx.dealOk }}</p>

      <WorkDealFilterChips
        v-if="!ctx.dealListError && ctx.activeDealChips.length"
        :active-deal-chips="ctx.activeDealChips"
        :reset-deal-filter="ctx.resetDealFilter"
      />

      <WorkDealsTableSection
        :sorted-deals="ctx.sortedDeals"
        :deal-filters="ctx.dealFilters"
        :deal-type-options="ctx.dealTypeOptions"
        :deal-flow-status-options="ctx.dealFlowStatusOptions"
        :responsible-options="ctx.responsibleUserOptions"
        :regions="ctx.regions"
        :active-deal-filter="ctx.activeDealFilter"
        :set-active-deal-filter="ctx.setActiveDealFilter"
        :toggle-deal-sort="ctx.toggleDealSort"
        :get-deal-sort-class="ctx.getDealSortClass"
        :load-deals="ctx.loadDeals"
        :reset-deal-filter="ctx.resetDealFilter"
        :validate-deal-range="ctx.validateDealRange"
        :deal-filter-errors="ctx.dealFilterErrors"
        :min-date="ctx.minDate"
        :max-date="ctx.maxDate"
        :edit-deal="ctx.editDeal"
        :start-edit-deal="ctx.startEditDeal"
        :deal-editing-by-deal-id="ctx.dealEditingByDealId"
        :current-username="ctx.currentUsername"
        :responsible-name-by-username="ctx.responsibleNameByUsername"
        :show-deal-warning="ctx.showDealWarning"
        :format-date-time-minutes="ctx.formatDateTimeMinutes"
        :deal-show-completed="ctx.dealShowCompleted"
        :can-do-action="ctx.canDoAction"
        :mark-deal-completed="ctx.markDealCompleted"
        :mark-deal-returned="ctx.markDealReturned"
        :deal-saving="ctx.dealSaving"
        :deal-completing-id="ctx.dealCompletingId"
        :realtime-animation-tick="ctx.dealsRealtimeAnimationTick"
      />

      <div v-if="ctx.dealTotal > 0" class="pager">
        <span class="muted">Всего: {{ ctx.dealTotal }}</span>
        <label class="pager__size">
          <span class="muted">Показывать</span>
          <select v-model.number="ctx.dealPageSize" class="input input--select input--compact">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </label>
        <button class="ghost" @click="ctx.setDealPage(1)" :disabled="ctx.dealPage <= 1 || ctx.dealListLoading">«</button>
        <button class="ghost" @click="ctx.prevDealPage" :disabled="ctx.dealPage <= 1 || ctx.dealListLoading">← Назад</button>
        <label class="pager__jump">
          <span class="muted">Стр.</span>
          <input
            v-model.number="ctx.dealPageInput"
            class="input input--compact input--page"
            type="number"
            min="1"
            :max="ctx.totalPages"
            @keydown.enter.prevent="ctx.jumpDealPage"
            @blur="ctx.jumpDealPage"
          />
        </label>
        <span class="muted">из {{ ctx.totalPages }}</span>
        <button class="ghost" @click="ctx.nextDealPage" :disabled="ctx.dealPage >= ctx.totalPages || ctx.dealListLoading">Вперёд →</button>
        <button class="ghost" @click="ctx.setDealPage(ctx.totalPages)" :disabled="ctx.dealPage >= ctx.totalPages || ctx.dealListLoading">»</button>
      </div>

      <slot />
    </div>
  </section>
</template>

<script setup>
import WorkDealsHeader from './WorkDealsHeader.vue'
import WorkDealFilterChips from './WorkDealFilterChips.vue'
import WorkDealsTableSection from './WorkDealsTableSection.vue'

// Передаем один контекст, чтобы не плодить длинный список пропсов на уровне WorkView.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const { ctx } = props
function canDoAction(actionCode) {
  // Если action-RBAC не передан, закрываем действие, чтобы UI не обходил матрицу.
  if (typeof ctx.canDoAction !== 'function') return false
  return ctx.canDoAction(actionCode)
}
</script>
