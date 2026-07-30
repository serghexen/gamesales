<template>
  <teleport to="body">
    <div v-if="showYandexMarketDigitalSettings" class="work-page work-modal-root modal-backdrop" @click.self="closeYandexMarketDigitalSettings">
      <div class="modal modal--auto ozon-digital-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div><h3>Ключи Яндекс Маркета</h3></div>
          <div class="toolbar-actions ozon-digital-modal__head-actions">
            <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save" type="button" :disabled="yandexMarketSandboxMode || yandexMarketStockSettingsSaving" :title="yandexMarketSandboxMode ? 'Настройка выдачи ключей пока не подключена' : 'Сохранить настройки'" aria-label="Сохранить настройки" @click="saveProductionSettings">
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
                  <label class="switch" :title="yandexMarketSandboxMode ? 'Автовыдача будет доступна после подключения обработки заказов Маркета' : 'Автовыдача через Interhub'">
                    <input v-model="autoIssueEnabled" type="checkbox" :disabled="yandexMarketSandboxMode || !yandexMarketStockSettings.interhub_service_id" :aria-label="yandexMarketSandboxMode ? 'Автовыдача пока не подключена' : 'Автовыдача через Interhub Яндекс Маркета'" />
                    <span class="slider"><span class="circle"><svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="m243.188 182.86 113.132-113.134c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.503 32.766 12.503 45.247 0l113.132-113.132 113.131 113.132c12.503 12.503 32.769 12.503 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25z" /></svg><svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg></span></span>
                  </label>
                </div>
              </div>
            </div>
            <div v-if="isSupplierOpen" id="yandex-key-supplier-content" class="ozon-catalog-details-modal__work-block-body">
              <div class="ozon-digital-modal__supplier"><div class="ozon-digital-modal__supplier-fields"><template v-if="yandexMarketSandboxMode"><label class="field"><span>Товар</span><select class="input" disabled aria-label="Товар"><option>Будет выбран при подключении</option></select></label></template><template v-else><label class="field"><span>ID услуги Interhub</span><input v-model.number="yandexMarketStockSettings.interhub_service_id" class="input" type="number" min="1" aria-label="ID услуги Interhub Яндекс Маркета" /></label><label class="field"><span>Номинал Interhub</span><input v-model="yandexMarketStockSettings.interhub_nominal_id" class="input" aria-label="Номинал Interhub Яндекс Маркета" /></label></template></div></div>
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
                <label class="switch" :title="yandexMarketSandboxMode ? 'Автовыдача из пула остается выключенной: ключи выдаются только по нажатию в fake-заказе.' : 'Использует ручной пул этой карточки как источник выдачи'">
                  <input v-model="poolIssueEnabled" type="checkbox" :disabled="yandexMarketSandboxMode" :aria-label="yandexMarketSandboxMode ? 'Автоматическая выдача из ручного пула выключена' : 'Выдача из ручного пула Яндекс Маркета'" />
                  <span class="slider"><span class="circle"><svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="m243.188 182.86 113.132-113.134c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.503 32.766 12.503 45.247 0l113.132-113.132 113.131 113.132c12.503 12.503 32.769 12.503 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25z" /></svg><svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg></span></span>
                </label>
              </div>
            </template>
          </WorkMarketplaceKeyPoolPanel>
          <section v-if="yandexMarketSandboxMode" class="ozon-digital-modal__orders">
            <div class="ozon-digital-modal__orders-head"><div><h4>Локальная выдача fake-заказов</h4><p class="muted">Ключи сохраняются в локальном test-пуле. Яндекс Маркет и Interhub не вызываются.</p></div><span class="ozon-digital-modal__manual-count">{{ pendingSandboxOrders.length }}</span></div>
            <p v-if="!pendingSandboxOrders.length" class="ozon-digital-modal__empty muted">Не найдено fake-заказов, ожидающих локальной выдачи.</p>
            <article v-for="order in pendingSandboxOrders" :key="`${order.order_id}:${order.item_id}`" class="ozon-digital-order">
              <div class="ozon-digital-order__head">
                <div><strong>Заказ {{ order.order_id }}</strong><p>{{ order.offer_id }} · требуется ключей: {{ order.quantity }}</p></div>
                <span class="ozon-digital-order__status ozon-digital-order__status--manual_required">Fake · локально</span>
              </div>
              <div class="ozon-digital-order__delivery">
                <label class="field"><span>Ручные ключи — по одному в строке</span><textarea v-model="manualCodes[orderKey(order)]" class="input" rows="3" :disabled="isSaving(order)" :aria-label="`Ручные ключи для fake-заказа ${order.order_id}`" /></label>
                <div class="toolbar-actions">
                  <button class="btn btn--secondary" type="button" :disabled="isSaving(order)" @click="issueFromPool(order)">Взять из пула</button>
                  <button class="btn btn--primary" type="button" :disabled="isSaving(order)" @click="deliverManually(order)">Зафиксировать локально</button>
                </div>
              </div>
            </article>
          </section>
          <section v-if="yandexMarketSandboxMode && readyForMarketOrders.length" class="ozon-digital-modal__orders">
            <div class="ozon-digital-modal__orders-head"><div><h4>Отправка в test Маркет</h4><p class="muted">Ключ уже закреплен локально. Отправка изменит только fake-заказ в test-кабинете.</p></div><span class="ozon-digital-modal__manual-count">{{ readyForMarketOrders.length }}</span></div>
            <article v-for="order in readyForMarketOrders" :key="`market:${order.order_id}:${order.item_id}`" class="ozon-digital-order">
              <div class="ozon-digital-order__head"><div><strong>Заказ {{ order.order_id }}</strong><p>{{ order.offer_id }} · ключи закреплены локально</p></div><span class="ozon-digital-order__status ozon-digital-order__status--supplier_processing">Готов к отправке</span></div>
              <div class="ozon-digital-order__delivery"><button class="btn btn--primary" type="button" :disabled="isSaving(order)" @click="sendToMarket(order)">Отправить в test Маркет</button></div>
            </article>
          </section>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import WorkMarketplaceKeyPoolPanel from './WorkMarketplaceKeyPoolPanel.vue'

const props = defineProps({
  showYandexMarketDigitalSettings: { type: Boolean, required: true },
  closeYandexMarketDigitalSettings: { type: Function, required: true },
  yandexMarketSandboxMode: { type: Boolean, default: false },
  yandexMarketOfferId: { type: String, default: '' },
  yandexMarketTitle: { type: String, default: '' },
  yandexMarketStockSettings: { type: Object, default: () => ({}) },
  yandexMarketStockSettingsSaving: { type: Boolean, default: false },
  saveYandexMarketStockSettings: { type: Function, default: async () => ({ ok: false }) },
  yandexMarketOrders: { type: Array, default: () => [] },
  yandexMarketSandboxDeliverySaving: { type: String, default: '' },
  deliverYandexMarketSandboxOrder: { type: Function, default: async () => ({ ok: false }) },
  issueYandexMarketSandboxOrderFromPool: { type: Function, default: async () => ({ ok: false }) },
  sendYandexMarketSandboxOrderToMarket: { type: Function, default: async () => ({ ok: false }) },
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
const manualCodes = reactive({})

const autoIssueEnabled = computed({
  get: () => Boolean(props.yandexMarketStockSettings.auto_issue_enabled),
  set: (enabled) => {
    // Включает Interhub вместе с автовыдачей, чтобы не сохранить противоречивую конфигурацию.
    props.yandexMarketStockSettings.auto_issue_enabled = Boolean(enabled)
    props.yandexMarketStockSettings.interhub_enabled = Boolean(enabled)
  },
})

const poolIssueEnabled = computed({
  get: () => Boolean(props.yandexMarketStockSettings.pool_issue_enabled),
  set: (enabled) => {
    // Сохраняет выбор ручного пула отдельно от поставщика Interhub.
    props.yandexMarketStockSettings.pool_issue_enabled = Boolean(enabled)
  },
})

const pendingSandboxOrders = computed(() => {
  // Оставляет в очереди только незавершенные позиции: итог выдачи хранится локально рядом с fake-заказом.
  return props.yandexMarketOrders.filter((order) => (
    !String(order?.sandbox_delivery_status || '').trim()
    && !['CANCELLED', 'DELIVERED'].includes(String(order?.status || '').toUpperCase())
  ))
})

const readyForMarketOrders = computed(() => {
  // Показывает только уже закрепленные коды, которые оператор еще не отправлял во внешний test-Маркет.
  return props.yandexMarketOrders.filter((order) => String(order?.sandbox_delivery_status || '') === 'locally_issued')
})

function orderKey(order) {
  // Собирает стабильный ключ формы, чтобы несколько позиций одного заказа не смешивали введенные коды.
  return `${Number(order?.order_id || 0)}:${Number(order?.item_id || 0)}`
}

function isSaving(order) {
  // Блокирует только выдаваемую позицию, пока локальная транзакция закрепляет ключи.
  return props.yandexMarketSandboxDeliverySaving === orderKey(order)
}

async function deliverManually(order) {
  // Передает введенные коды только локальному sandbox-обработчику и очищает форму после успешной фиксации.
  const key = orderKey(order)
  const result = await props.deliverYandexMarketSandboxOrder(order, String(manualCodes[key] || '').split(/\r?\n/))
  if (result?.ok) {
    delete manualCodes[key]
    await props.loadMarketplaceKeyPool()
  }
}

async function issueFromPool(order) {
  // Выдает точное количество из локального test-пула по явному клику оператора.
  const result = await props.issueYandexMarketSandboxOrderFromPool(order)
  if (result?.ok) await props.loadMarketplaceKeyPool()
}

async function sendToMarket(order) {
  // Передает ключ во внешний API только после диалога подтверждения из общего обработчика.
  await props.sendYandexMarketSandboxOrderToMarket(order)
}

function toggleSupplier() {
  // Сворачивает настройки источника, не меняя сохраненные параметры карточки.
  isSupplierOpen.value = !isSupplierOpen.value
}

async function saveProductionSettings() {
  // Отправляет настройки выдачи только из боевой формы; sandbox остаётся локальным сценарием.
  if (props.yandexMarketSandboxMode) return
  await props.saveYandexMarketStockSettings()
}

watch(
  () => [props.showYandexMarketDigitalSettings, props.yandexMarketOfferId, props.yandexMarketTitle],
  ([isOpen, productKey, productTitle]) => {
    // Подгружает отдельный пул нужного контура до показа таблицы ключей.
    if (isOpen && productKey) props.loadMarketplaceKeyPoolFor({ marketplace: 'yandex_market', productKey: String(productKey), productTitle: String(productTitle || productKey), storeCode: props.yandexMarketSandboxMode ? 'test' : 'asat' })
  },
  { immediate: true },
)
</script>
