<template>
  <section class="panel panel--wide">
    <WorkProductsHeader
      :product-filters="ctx.productFilters"
      :apply-product-search="ctx.applyProductSearch"
      :open-create-game-product-modal="ctx.openCreateGameProductModal"
      :open-create-subscription-product-modal="ctx.openCreateSubscriptionProductModal"
      :open-product-import="ctx.openProductImport"
      :open-ozon-catalog="ctx.openOzonCatalog"
      :can-manage-ozon="ctx.canManageOzon"
      :open-yandex-market-catalog="ctx.openYandexMarketCatalog"
      :can-manage-yandex-market="ctx.canManageYandexMarket"
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

      <WorkOzonCatalogModal
        v-if="ctx.canManageOzon"
        :show-ozon-catalog="ctx.showOzonCatalog"
        :close-ozon-catalog="ctx.closeOzonCatalog"
        :sync-ozon-catalog="ctx.syncOzonCatalog"
        :update-ozon-catalog-archive="ctx.updateOzonCatalogArchive"
        :open-ozon-catalog-details="ctx.openOzonCatalogDetails"
        :ozon-catalog-items="ctx.ozonCatalogItems"
        :ozon-catalog-loading="ctx.ozonCatalogLoading"
        :ozon-catalog-syncing="ctx.ozonCatalogSyncing"
        :ozon-catalog-item-action-id="ctx.ozonCatalogItemActionId"
        :ozon-catalog-error="ctx.ozonCatalogError"
        :ozon-catalog-ok="ctx.ozonCatalogOk"
      />

      <WorkYandexMarketCatalogModal
        v-if="ctx.canManageYandexMarket"
        :show-yandex-market-catalog="ctx.showYandexMarketCatalog"
        :close-yandex-market-catalog="ctx.closeYandexMarketCatalog"
        :sync-yandex-market-catalog="ctx.syncYandexMarketCatalog"
        :update-yandex-market-catalog-archive="ctx.updateYandexMarketCatalogArchive"
        :open-yandex-market-catalog-details="ctx.openYandexMarketCatalogDetails"
        :yandex-market-catalog-items="ctx.yandexMarketCatalogItems"
        :yandex-market-catalog-loading="ctx.yandexMarketCatalogLoading"
        :yandex-market-catalog-syncing="ctx.yandexMarketCatalogSyncing"
        :yandex-market-catalog-item-action-id="ctx.yandexMarketCatalogItemActionId"
        :yandex-market-catalog-error="ctx.yandexMarketCatalogError"
        :yandex-market-catalog-ok="ctx.yandexMarketCatalogOk"
      />

      <WorkYandexMarketCatalogDetailsModal
        v-if="ctx.canManageYandexMarket"
        :show-yandex-market-catalog-details="ctx.showYandexMarketCatalogDetails"
        :close-yandex-market-catalog-details="ctx.closeYandexMarketCatalogDetails"
        :open-yandex-market-digital-settings="ctx.openYandexMarketDigitalSettings"
        :yandex-market-sandbox-mode="ctx.yandexMarketSandboxMode"
        :yandex-market-catalog-details="ctx.yandexMarketCatalogDetails"
        :yandex-market-catalog-details-loading="ctx.yandexMarketCatalogDetailsLoading"
        :yandex-market-catalog-details-error="ctx.yandexMarketCatalogDetailsError"
        :yandex-market-stock-settings="ctx.yandexMarketStockSettings"
        :yandex-market-stock-settings-saving="ctx.yandexMarketStockSettingsSaving"
        :save-yandex-market-stock-settings="ctx.saveYandexMarketStockSettings"
        :yandex-market-orders="ctx.yandexMarketOrders"
        :yandex-market-orders-loading="ctx.yandexMarketOrdersLoading"
        :yandex-market-orders-syncing="ctx.yandexMarketOrdersSyncing"
        :yandex-market-orders-last-synced-at="ctx.yandexMarketOrdersLastSyncedAt"
        :load-yandex-market-orders="ctx.loadYandexMarketOrders"
        :sync-yandex-market-orders="ctx.syncYandexMarketOrders"
      />

      <WorkYandexMarketDigitalSettingsModal
        v-if="ctx.canManageYandexMarket"
        :show-yandex-market-digital-settings="ctx.showYandexMarketDigitalSettings"
        :close-yandex-market-digital-settings="ctx.closeYandexMarketDigitalSettings"
        :yandex-market-sandbox-mode="ctx.yandexMarketSandboxMode"
        :yandex-market-offer-id="ctx.yandexMarketCatalogDetails?.offer_id || ''"
        :yandex-market-title="ctx.yandexMarketCatalogDetails?.title || ''"
        :yandex-market-stock-settings="ctx.yandexMarketStockSettings"
        :yandex-market-stock-settings-saving="ctx.yandexMarketStockSettingsSaving"
        :save-yandex-market-stock-settings="ctx.saveYandexMarketStockSettings"
        :yandex-market-interhub-services="ctx.yandexMarketInterhubServices"
        :yandex-market-interhub-services-loading="ctx.yandexMarketInterhubServicesLoading"
        :yandex-market-production-manual-orders="ctx.yandexMarketProductionManualOrders"
        :yandex-market-production-manual-orders-loading="ctx.yandexMarketProductionManualOrdersLoading"
        :yandex-market-production-manual-delivery-saving="ctx.yandexMarketProductionManualDeliverySaving"
        :yandex-market-orders="ctx.yandexMarketOrders"
        :yandex-market-sandbox-delivery-saving="ctx.yandexMarketSandboxDeliverySaving"
        :deliver-yandex-market-sandbox-order="ctx.deliverYandexMarketSandboxOrder"
        :issue-yandex-market-sandbox-order-from-pool="ctx.issueYandexMarketSandboxOrderFromPool"
        :send-yandex-market-sandbox-order-to-market="ctx.sendYandexMarketSandboxOrderToMarket"
        :deliver-yandex-market-production-order="ctx.deliverYandexMarketProductionOrder"
        :issue-yandex-market-production-order-from-pool="ctx.issueYandexMarketProductionOrderFromPool"
        :open-marketplace-key-pool="ctx.openMarketplaceKeyPool"
        :load-marketplace-key-pool-for="ctx.loadMarketplaceKeyPoolFor"
        :marketplace-key-pool="ctx.marketplaceKeyPool"
        :marketplace-key-pool-loading="ctx.marketplaceKeyPoolLoading"
        :marketplace-key-pool-saving="ctx.marketplaceKeyPoolSaving"
        :marketplace-key-pool-error="ctx.marketplaceKeyPoolError"
        :marketplace-key-pool-total-pages="ctx.marketplaceKeyPoolTotalPages"
        :marketplace-key-pool-revealing-id="ctx.marketplaceKeyPoolRevealingId"
        :marketplace-key-pool-revealed-code="ctx.marketplaceKeyPoolRevealedCode"
        :load-marketplace-key-pool="ctx.loadMarketplaceKeyPool"
        :reveal-marketplace-key-pool-key="ctx.revealMarketplaceKeyPoolKey"
        :delete-marketplace-key-pool-key="ctx.deleteMarketplaceKeyPoolKey"
        :delete-all-free-marketplace-key-pool-keys="ctx.deleteAllFreeMarketplaceKeyPoolKeys"
      />

      <WorkOzonCatalogDetailsModal
        v-if="ctx.canManageOzon"
        :show-ozon-catalog-details="ctx.showOzonCatalogDetails"
        :close-ozon-catalog-details="ctx.closeOzonCatalogDetails"
        :open-ozon-digital-settings="ctx.openOzonDigitalSettings"
        :ozon-catalog-details="ctx.ozonCatalogDetails"
        :ozon-catalog-details-loading="ctx.ozonCatalogDetailsLoading"
        :ozon-catalog-details-error="ctx.ozonCatalogDetailsError"
        :ozon-digital-settings="ctx.ozonDigitalSettings"
        :ozon-digital-settings-loading="ctx.ozonDigitalSettingsLoading"
        :ozon-digital-settings-saving="ctx.ozonDigitalSettingsSaving"
        :ozon-digital-settings-error="ctx.ozonDigitalSettingsError"
        :ozon-digital-settings-ok="ctx.ozonDigitalSettingsOk"
        :ozon-digital-orders="ctx.ozonDigitalOrders"
        :ozon-digital-orders-syncing="ctx.ozonDigitalOrdersSyncing"
        :load-ozon-digital-settings="ctx.loadOzonDigitalSettings"
        :save-ozon-digital-settings="ctx.saveOzonDigitalSettings"
        :sync-ozon-digital-orders="ctx.syncOzonDigitalOrders"
        :can-reveal-ozon-digital-codes="ctx.isAdmin"
        :reveal-ozon-digital-order-codes="ctx.revealOzonDigitalOrderCodes"
        :load-ozon-digital-supplier-operation="ctx.loadOzonDigitalSupplierOperation"
      />

      <WorkOzonDigitalSettingsModal
        v-if="ctx.canManageOzon"
        :show-ozon-digital-settings="ctx.showOzonDigitalSettings"
        :close-ozon-digital-settings="ctx.closeOzonDigitalSettings"
        :ozon-digital-settings="ctx.ozonDigitalSettings"
        :ozon-digital-product-title="ctx.ozonCatalogDetails?.title || ''"
        :ozon-digital-settings-loading="ctx.ozonDigitalSettingsLoading"
        :ozon-digital-settings-saving="ctx.ozonDigitalSettingsSaving"
        :ozon-digital-settings-error="ctx.ozonDigitalSettingsError"
        :ozon-digital-settings-ok="ctx.ozonDigitalSettingsOk"
        :ozon-digital-orders="ctx.ozonDigitalOrders"
        :interhub-services="ctx.ozonInterhubServices"
        :interhub-services-loading="ctx.ozonInterhubServicesLoading"
        :save-ozon-digital-settings="ctx.saveOzonDigitalSettings"
        :deliver-ozon-digital-order="ctx.deliverOzonDigitalOrder"
        :open-marketplace-key-pool="ctx.openMarketplaceKeyPool"
        :load-marketplace-key-pool-for="ctx.loadMarketplaceKeyPoolFor"
        :marketplace-key-pool="ctx.marketplaceKeyPool"
        :marketplace-key-pool-loading="ctx.marketplaceKeyPoolLoading"
        :marketplace-key-pool-saving="ctx.marketplaceKeyPoolSaving"
        :marketplace-key-pool-error="ctx.marketplaceKeyPoolError"
        :marketplace-key-pool-total-pages="ctx.marketplaceKeyPoolTotalPages"
        :marketplace-key-pool-revealing-id="ctx.marketplaceKeyPoolRevealingId"
        :marketplace-key-pool-revealed-code="ctx.marketplaceKeyPoolRevealedCode"
        :load-marketplace-key-pool="ctx.loadMarketplaceKeyPool"
        :reveal-marketplace-key-pool-key="ctx.revealMarketplaceKeyPoolKey"
        :delete-marketplace-key-pool-key="ctx.deleteMarketplaceKeyPoolKey"
        :delete-all-free-marketplace-key-pool-keys="ctx.deleteAllFreeMarketplaceKeyPoolKeys"
      />

      <WorkMarketplaceKeyPoolModal
        :show-marketplace-key-pool="ctx.showMarketplaceKeyPool"
        :close-marketplace-key-pool="ctx.closeMarketplaceKeyPool"
        :marketplace-key-pool="ctx.marketplaceKeyPool"
        :marketplace-key-pool-loading="ctx.marketplaceKeyPoolLoading"
        :marketplace-key-pool-saving="ctx.marketplaceKeyPoolSaving"
        :marketplace-key-pool-error="ctx.marketplaceKeyPoolError"
        :marketplace-key-pool-ok="ctx.marketplaceKeyPoolOk"
        :add-marketplace-key-pool-keys="ctx.addMarketplaceKeyPoolKeys"
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
import WorkOzonCatalogModal from './WorkOzonCatalogModal.vue'
import WorkYandexMarketCatalogModal from './WorkYandexMarketCatalogModal.vue'
import WorkYandexMarketCatalogDetailsModal from './WorkYandexMarketCatalogDetailsModal.vue'
import WorkYandexMarketDigitalSettingsModal from './WorkYandexMarketDigitalSettingsModal.vue'
import WorkOzonCatalogDetailsModal from './WorkOzonCatalogDetailsModal.vue'
import WorkOzonDigitalSettingsModal from './WorkOzonDigitalSettingsModal.vue'
import WorkMarketplaceKeyPoolModal from './WorkMarketplaceKeyPoolModal.vue'
import WorkProductsTableSection from './WorkProductsTableSection.vue'
import WorkProductsPager from './WorkProductsPager.vue'
import WorkProductEditorModal from './WorkProductEditorModal.vue'

// Контекст секции товаров: фильтры, таблица, пагинация, импорт и модалка.
defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})
</script>
