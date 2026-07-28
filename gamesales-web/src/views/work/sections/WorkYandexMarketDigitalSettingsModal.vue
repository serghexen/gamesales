<template>
  <teleport to="body">
    <div v-if="showYandexMarketDigitalSettings" class="work-page work-modal-root modal-backdrop" @click.self="closeYandexMarketDigitalSettings">
      <div class="modal modal--auto ozon-digital-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div><h3>Ключи Яндекс Маркета</h3></div>
          <div class="toolbar-actions ozon-digital-modal__head-actions">
            <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save" type="button" disabled title="Настройка выдачи ключей пока не подключена" aria-label="Сохранить настройки">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h12l4 4v12H4z" /><path d="M7 4v6h8V4" /><path d="M7 20v-6h10v6" /></svg>
            </button>
            <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--edit" type="button" aria-label="Вернуться к карточке" title="К карточке" @click="closeYandexMarketDigitalSettings"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></svg></button>
            <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeYandexMarketDigitalSettings"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg></button>
          </div>
        </div>
        <div class="modal__body">
          <section class="ozon-catalog-details-modal__work-block ozon-key-settings__block" :class="{ 'is-open': isSupplierOpen }">
            <div class="ozon-key-settings__block-head">
              <button class="ozon-catalog-details-modal__work-block-toggle" type="button" :aria-expanded="isSupplierOpen" aria-controls="yandex-key-supplier-content" @click="toggleSupplier">
                <span class="ozon-catalog-details-modal__work-block-number">01</span>
                <span class="ozon-catalog-details-modal__work-block-copy"><strong>Автовыдача</strong></span>
                <svg class="ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
              </button>
              <div class="ozon-key-settings__block-actions">
                <div class="ozon-digital-modal__auto-switch">
                  <label class="switch" title="Автовыдача будет доступна после подключения обработки заказов Маркета">
                    <input type="checkbox" disabled aria-label="Автовыдача пока не подключена" />
                    <span class="slider"><span class="circle"><svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="m243.188 182.86 113.132-113.134c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.503 32.766 12.503 45.247 0l113.132-113.132 113.131 113.132c12.503 12.503 32.769 12.503 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25z" /></svg><svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg></span></span>
                  </label>
                </div>
              </div>
            </div>
            <div v-if="isSupplierOpen" id="yandex-key-supplier-content" class="ozon-catalog-details-modal__work-block-body">
              <div class="ozon-digital-modal__supplier"><div class="ozon-digital-modal__supplier-fields"><label class="field"><span>Товар</span><select class="input" disabled aria-label="Товар"><option>Будет выбран при подключении</option></select></label></div></div>
            </div>
          </section>
          <WorkMarketplaceKeyPoolPanel
            marketplace="yandex_market"
            :product-key="yandexMarketOfferId"
            :product-title="yandexMarketTitle || yandexMarketOfferId"
            :marketplace-key-pool="marketplaceKeyPool"
            :marketplace-key-pool-loading="marketplaceKeyPoolLoading"
            :marketplace-key-pool-saving="marketplaceKeyPoolSaving"
            :marketplace-key-pool-error="marketplaceKeyPoolError"
            :marketplace-key-pool-total-pages="marketplaceKeyPoolTotalPages"
            :marketplace-key-pool-revealing-id="marketplaceKeyPoolRevealingId"
            :marketplace-key-pool-revealed-code="marketplaceKeyPoolRevealedCode"
            :open-marketplace-key-pool="openMarketplaceKeyPool"
            :load-marketplace-key-pool="loadMarketplaceKeyPool"
            :reveal-marketplace-key-pool-key="revealMarketplaceKeyPoolKey"
            :delete-marketplace-key-pool-key="deleteMarketplaceKeyPoolKey"
            :delete-all-free-marketplace-key-pool-keys="deleteAllFreeMarketplaceKeyPoolKeys"
          >
            <template #header-actions>
              <div class="ozon-digital-modal__auto-switch marketplace-key-pool-panel__issue-switch">
                <label class="switch" title="Выдача из пула будет доступна после подключения обработки заказов Маркета">
                  <input type="checkbox" disabled aria-label="Выдача из ручного пула пока не подключена" />
                  <span class="slider"><span class="circle"><svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="m243.188 182.86 113.132-113.134c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.503 32.766 12.503 45.247 0l113.132-113.132 113.131 113.132c12.503 12.503 32.769 12.503 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25z" /></svg><svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg></span></span>
                </label>
              </div>
            </template>
          </WorkMarketplaceKeyPoolPanel>
          <section class="ozon-digital-modal__orders">
            <div class="ozon-digital-modal__orders-head"><div><h4>Ручная выдача</h4><p class="muted">Заказы, для которых поставщик не выдал ключ.</p></div><span class="ozon-digital-modal__manual-count">0</span></div>
            <p class="ozon-digital-modal__empty muted">Заказов, требующих ручного ключа, пока нет.</p>
          </section>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import WorkMarketplaceKeyPoolPanel from './WorkMarketplaceKeyPoolPanel.vue'

const props = defineProps({
  showYandexMarketDigitalSettings: { type: Boolean, required: true },
  closeYandexMarketDigitalSettings: { type: Function, required: true },
  yandexMarketOfferId: { type: String, default: '' },
  yandexMarketTitle: { type: String, default: '' },
  openMarketplaceKeyPool: { type: Function, default: () => {} },
  loadMarketplaceKeyPoolFor: { type: Function, default: () => {} },
  marketplaceKeyPool: { type: Object, default: () => ({ free_count: 0, reserved_count: 0, delivered_count: 0, expired_count: 0, total: 0, page: 1, page_size: 20, items: [] }) },
  marketplaceKeyPoolLoading: { type: Boolean, default: false },
  marketplaceKeyPoolSaving: { type: Boolean, default: false },
  marketplaceKeyPoolError: { type: String, default: '' },
  marketplaceKeyPoolTotalPages: { type: Number, default: 1 },
  marketplaceKeyPoolRevealingId: { type: Number, default: 0 },
  marketplaceKeyPoolRevealedCode: { type: Function, default: () => '' },
  loadMarketplaceKeyPool: { type: Function, default: () => {} },
  revealMarketplaceKeyPoolKey: { type: Function, default: () => {} },
  deleteMarketplaceKeyPoolKey: { type: Function, default: () => {} },
  deleteAllFreeMarketplaceKeyPoolKeys: { type: Function, default: () => {} },
})

const isSupplierOpen = ref(false)

function toggleSupplier() {
  // Сворачивает подготовительный блок автовыдачи, пока Маркет подключён только на чтение.
  isSupplierOpen.value = !isSupplierOpen.value
}

watch(
  () => [props.showYandexMarketDigitalSettings, props.yandexMarketOfferId, props.yandexMarketTitle],
  ([isOpen, productKey, productTitle]) => {
    // Подгружает отдельный пул текущего SKU Маркета до показа таблицы на основном экране.
    if (isOpen && productKey) props.loadMarketplaceKeyPoolFor({ marketplace: 'yandex_market', productKey: String(productKey), productTitle: String(productTitle || productKey) })
  },
  { immediate: true },
)
</script>
