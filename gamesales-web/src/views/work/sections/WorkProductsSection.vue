<template>
  <section class="panel panel--wide">
    <WorkProductsHeader
      :product-filters="ctx.productFilters"
      :apply-product-search="ctx.applyProductSearch"
      :can-create-products="canDoAction('products.create_games')"
      :open-create-game-product-modal="ctx.openCreateGameProductModal"
      :open-create-subscription-product-modal="ctx.openCreateSubscriptionProductModal"
      :open-product-import="ctx.openProductImport"
      :load-products="ctx.loadProducts"
      :products-loading="ctx.productsLoading"
    />
    <div class="panel__body">
      <div v-if="ctx.productsLoading" class="loader-wrap loader-overlay">
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
      <WorkGameFilterChips
        v-else-if="ctx.activeProductChips.length"
        :active-product-chips="ctx.activeProductChips"
        :reset-product-filter="ctx.resetProductFilter"
      />
      <WorkGameImportModal
        :show-product-import="ctx.showProductImport"
        :close-product-import="ctx.closeProductImport"
        :modal-ref="ctx.modalRef"
        :modal-style="ctx.modalStyle"
        :start-modal-drag="ctx.startModalDrag"
        :product-import-loading="ctx.productImportLoading"
        :download-product-template="ctx.downloadProductTemplate"
        :validate-product-import="ctx.validateProductImport"
        :product-import-file="ctx.productImportFile"
        :product-import-action="ctx.productImportAction"
        :upload-product-import="ctx.uploadProductImport"
        :product-import-validated="ctx.productImportValidated"
        :product-import-job-id="ctx.productImportJobId"
        :cancel-product-import="ctx.cancelProductImport"
        :scroll-to-import-details="ctx.scrollToImportDetails"
        :product-import-progress="ctx.productImportProgress"
        :on-product-import-file="ctx.onProductImportFile"
        :import-details-ref="ctx.importDetailsRef"
        :product-import-message="ctx.productImportMessage"
        :product-import-errors="ctx.productImportErrors"
        :product-import-warnings="ctx.productImportWarnings"
        :download-product-import-report="ctx.downloadProductImportReport"
        :product-import-stats="ctx.productImportStats"
      />

      <WorkProductsTableSection
        :sorted-products="ctx.sortedProducts"
        :paged-products="ctx.pagedProducts"
        :product-filters="ctx.productFilters"
        :active-product-filter="ctx.activeProductFilter"
        :product-filter-draft="ctx.productFilterDraft"
        :open-product-filter="ctx.openProductFilter"
        :toggle-products-sort="ctx.toggleProductsSort"
        :get-products-sort-class="ctx.getProductsSortClass"
        :apply-product-filter="ctx.applyProductFilter"
        :reset-product-filter="ctx.resetProductFilter"
        :format-product-platforms="ctx.formatProductPlatforms"
        :open-product-accounts="ctx.openProductAccounts"
        :can-view-games="canDoAction('products.view_games')"
        :can-view-type-column="canDoAction('products.list.type')"
        :can-view-title-column="canDoAction('products.list.title')"
        :can-view-platform-column="canDoAction('products.list.platform')"
        :can-open-product-accounts="canDoAction('products.reflect_accounts')"
      />

      <WorkProductsPager
        :products-total="ctx.productsTotal"
        :products-page-size="ctx.productsPageSize"
        :set-products-page-size="ctx.setProductsPageSizeFromEvent"
        :products-page="ctx.productsPage"
        :set-products-page="ctx.setProductsPage"
        :prev-products-page="ctx.prevProductsPage"
        :products-page-input="ctx.productsPageInput"
        :set-products-page-input="ctx.setProductsPageInputFromEvent"
        :products-total-pages="ctx.productsTotalPages"
        :jump-products-page="ctx.jumpProductsPage"
        :next-products-page="ctx.nextProductsPage"
      />

      <div class="divider"></div>

      <WorkProductEditorModal :ctx="ctx.productEditorModalCtx" />
    </div>
  </section>
</template>

<script setup>
import WorkProductsHeader from './WorkProductsHeader.vue'
import WorkGameFilterChips from './WorkGameFilterChips.vue'
import WorkGameImportModal from './WorkGameImportModal.vue'
import WorkProductsTableSection from './WorkProductsTableSection.vue'
import WorkProductsPager from './WorkProductsPager.vue'
import WorkProductEditorModal from './WorkProductEditorModal.vue'

// Контекст секции товаров: фильтры, таблица, пагинация, импорт и модалка.
const props = defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})
function canDoAction(actionCode) {
  // Если action-RBAC не передан, закрываем действие, чтобы UI не обходил матрицу.
  if (typeof props.ctx.canDoAction !== 'function') return false
  return props.ctx.canDoAction(actionCode)
}
</script>
