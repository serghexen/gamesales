<template>
  <teleport to="body">
    <div
      v-if="showOzonDigitalSettings"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeOzonDigitalSettings"
    >
      <div class="modal modal--auto ozon-digital-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div>
            <h3>Ключи Ozon</h3>
          </div>
          <div class="toolbar-actions ozon-digital-modal__head-actions">
            <button
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              type="button"
              :disabled="ozonDigitalSettingsSaving"
              aria-label="Сохранить настройки"
              title="Сохранить настройки"
              @click="saveOzonDigitalSettings"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Вернуться к карточке"
              title="К карточке"
              @click="closeOzonDigitalSettings"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></svg>
            </button>
            <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonDigitalSettings">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': isOzonDigitalBusy, 'modal__body--loader': isOzonDigitalBusy }">
          <div v-if="isOzonDigitalBusy" class="modal__body-overlay">
            <WorkHamsterLoader :label="ozonDigitalBusyLabel" />
          </div>
          <template v-if="!ozonDigitalSettingsLoading">
            <p v-if="ozonDigitalSettingsError" class="bad">{{ ozonDigitalSettingsError }}</p>
            <p v-if="ozonDigitalSettingsOk" class="good">{{ ozonDigitalSettingsOk }}</p>

            <section class="ozon-catalog-details-modal__work-block ozon-key-settings__block" :class="{ 'is-open': isSupplierOpen }">
              <div class="ozon-key-settings__block-head">
                <button class="ozon-catalog-details-modal__work-block-toggle" type="button" :aria-expanded="isSupplierOpen" aria-controls="ozon-key-supplier-content" @click="toggleSupplier">
                  <span class="ozon-catalog-details-modal__work-block-number">01</span>
                  <span class="ozon-catalog-details-modal__work-block-copy"><strong>Автовыдача</strong></span>
                  <svg class="ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
                </button>
                <div class="ozon-key-settings__block-actions">
                  <div class="ozon-digital-modal__auto-switch">
                  <label class="switch" title="Автовыдача через Interhub">
                    <input v-model="autoIssueEnabled" type="checkbox" aria-label="Автовыдача через Interhub" :disabled="!ozonDigitalSettings.interhub_service_id" />
                    <span class="slider">
                      <span class="circle">
                        <svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></svg>
                        <svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg>
                      </span>
                    </span>
                  </label>
                  </div>
                </div>
              </div>

              <div v-if="isSupplierOpen" id="ozon-key-supplier-content" class="ozon-catalog-details-modal__work-block-body">
                <div class="ozon-digital-modal__supplier">
                <div class="ozon-digital-modal__supplier-fields">
                  <label class="field">
                    <span>Товар</span>
                    <div class="ozon-digital-modal__service-picker">
                      <div class="ozon-digital-modal__service-search">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></svg>
                        <input
                          v-model="interhubServiceSearch"
                          class="input"
                          type="search"
                          autocomplete="off"
                          placeholder="Найдите товар или регион"
                          role="combobox"
                          :aria-expanded="isInterhubServicePickerOpen"
                          aria-controls="ozon-interhub-service-results"
                          :disabled="interhubServicesLoading"
                          @focus="openInterhubServicePicker"
                          @input="openInterhubServicePicker"
                          @keydown.enter.prevent="selectFirstInterhubService"
                          @keydown.esc.prevent="closeInterhubServicePicker"
                          @blur="closeInterhubServicePicker"
                        />
                        <button
                          v-if="ozonDigitalSettings.interhub_service_id"
                          class="ozon-digital-modal__service-clear"
                          type="button"
                          aria-label="Очистить выбранный товар"
                          title="Очистить выбор"
                          @mousedown.prevent
                          @click="clearInterhubService"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
                        </button>
                        <button
                          class="ozon-digital-modal__service-toggle"
                          type="button"
                          :aria-label="isInterhubServicePickerOpen ? 'Скрыть список товаров' : 'Показать список товаров'"
                          @mousedown.prevent
                          @click="toggleInterhubServicePicker"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
                        </button>
                      </div>
                      <div v-if="isInterhubServicePickerOpen" id="ozon-interhub-service-results" class="ozon-digital-modal__service-options" role="listbox">
                        <button
                          v-for="service in filteredInterhubServices"
                          :key="service.service_id"
                          class="ozon-digital-modal__service-option"
                          :class="{ 'is-selected': Number(service.service_id) === Number(ozonDigitalSettings.interhub_service_id) }"
                          type="button"
                          role="option"
                          :aria-selected="Number(service.service_id) === Number(ozonDigitalSettings.interhub_service_id)"
                          @mousedown.prevent
                          @click="selectInterhubService(service)"
                        >
                          <strong>{{ service.title }}</strong>
                          <small v-if="service.category">{{ service.category }}</small>
                        </button>
                        <p v-if="!filteredInterhubServices.length" class="ozon-digital-modal__service-empty">Ничего не найдено</p>
                      </div>
                    </div>
                    <small class="ozon-digital-modal__service-help">Поиск по названию, региону или ID услуги</small>
                  </label>
                  <label v-if="ozonDigitalSettings.interhub_service_id && interhubNominals.length" class="field">
                    <span>Номинал</span>
                    <select v-model="ozonDigitalSettings.interhub_nominal_id" class="input">
                      <option value="">Выберите номинал</option>
                      <option v-for="nominal in interhubNominals" :key="nominal.value" :value="nominal.value">{{ nominal.label }}</option>
                    </select>
                  </label>
                </div>
                </div>
              </div>
            </section>

            <WorkMarketplaceKeyPoolPanel
              marketplace="ozon"
              store-code="asat"
              :product-key="String(ozonDigitalSettings.external_product_id || '')"
              :product-title="keyPoolProductTitle"
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
                  <label class="switch" title="Использует ручной пул этой карточки: после сбоя Interhub или как основной источник">
                    <input v-model="poolIssueEnabled" type="checkbox" aria-label="Выдача из ручного пула" />
                    <span class="slider">
                      <span class="circle">
                        <svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></svg>
                        <svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg>
                      </span>
                    </span>
                  </label>
                </div>
              </template>
            </WorkMarketplaceKeyPoolPanel>

            <section class="ozon-digital-modal__orders">
              <div class="ozon-digital-modal__orders-head">
                <div>
                  <h4>Ручная выдача</h4>
                  <p class="muted">Заказы, для которых поставщик не выдал ключ.</p>
                </div>
                <span class="ozon-digital-modal__manual-count">{{ manualOzonDigitalOrders.length }}</span>
              </div>

              <p v-if="!manualOzonDigitalOrders.length" class="ozon-digital-modal__empty muted">Заказов, требующих ручного ключа, пока нет.</p>
              <article v-for="order in manualOzonDigitalOrders" :key="order.id" class="ozon-digital-order">
                <div class="ozon-digital-order__head">
                  <div>
                    <strong>{{ order.product_name || 'Цифровой товар' }}</strong>
                    <p>Отправление {{ order.posting_number }} · SKU {{ order.sku }}</p>
                  </div>
                  <span class="ozon-digital-order__status ozon-digital-order__status--manual_required">{{ hasSavedDelivery(order) ? 'Проверить отправку' : 'Нужен ключ' }}</span>
                </div>
                <p v-if="order.waiting_deadline_at" class="muted">Код ожидается до: {{ formatOzonDate(order.waiting_deadline_at) }}</p>
                <p v-if="order.last_error" class="bad">{{ order.last_error }}</p>
                <div class="ozon-digital-order__delivery">
                  <label v-if="!hasSavedDelivery(order)" class="field">
                    <span>{{ manualDeliveryLabel(order) }}</span>
                    <textarea v-model="deliveryDrafts[order.id]" class="input textarea" rows="2" placeholder="Вставьте ключ для покупателя"></textarea>
                  </label>
                  <button class="btn btn--primary" type="button" :disabled="deliveryBusy[order.id]" @click="submitDelivery(order)">
                    {{ deliveryBusy[order.id] ? 'Отправляем…' : (hasSavedDelivery(order) ? 'Повторить закреплённый ключ' : 'Отправить ключ') }}
                  </button>
                </div>
              </article>
            </section>
          </template>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'
import WorkMarketplaceKeyPoolPanel from './WorkMarketplaceKeyPoolPanel.vue'

const props = defineProps({
  showOzonDigitalSettings: { type: Boolean, required: true },
  closeOzonDigitalSettings: { type: Function, required: true },
  ozonDigitalSettings: { type: Object, required: true },
  ozonDigitalProductTitle: { type: String, default: '' },
  ozonDigitalSettingsLoading: { type: Boolean, required: true },
  ozonDigitalSettingsSaving: { type: Boolean, required: true },
  ozonDigitalSettingsError: { type: String, default: '' },
  ozonDigitalSettingsOk: { type: String, default: '' },
  ozonDigitalOrders: { type: Array, default: () => [] },
  interhubServices: { type: Array, default: () => [] },
  interhubServicesLoading: { type: Boolean, default: false },
  saveOzonDigitalSettings: { type: Function, required: true },
  deliverOzonDigitalOrder: { type: Function, required: true },
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
const deliveryDrafts = reactive({})
const deliveryBusy = reactive({})
const isSupplierOpen = ref(false)
const interhubServiceSearch = ref('')
const isInterhubServicePickerOpen = ref(false)

watch(
  () => [props.showOzonDigitalSettings, props.ozonDigitalSettings.external_product_id, props.ozonDigitalProductTitle, props.ozonDigitalSettings.offer_id],
  ([isOpen, productKey, productTitle]) => {
    // Подгружает таблицу на основном экране ключей сразу после открытия настроек карточки.
    if (isOpen && productKey) props.loadMarketplaceKeyPoolFor({ marketplace: 'ozon', productKey: String(productKey), productTitle: String(productTitle || props.ozonDigitalSettings.offer_id || 'Карточка Ozon'), storeCode: 'asat' })
  },
  { immediate: true },
)

const keyPoolProductTitle = computed(() => String(
  props.ozonDigitalProductTitle || props.ozonDigitalSettings.offer_id || 'Карточка Ozon',
))

const isOzonDigitalBusy = computed(() => Boolean(
  props.ozonDigitalSettingsLoading
  || props.ozonDigitalSettingsSaving
  || Object.values(deliveryBusy).some(Boolean),
))

const ozonDigitalBusyLabel = computed(() => {
  // Объясняет текущую операцию, пока хомяк блокирует повторные действия в модалке.
  if (props.ozonDigitalSettingsSaving) return 'Сохраняем настройки выдачи…'
  if (Object.values(deliveryBusy).some(Boolean)) return 'Отправляем ключ покупателю…'
  return 'Загружаем настройки ключей…'
})

const autoIssueEnabled = computed({
  get: () => Boolean(props.ozonDigitalSettings.auto_issue_enabled),
  set: (enabled) => {
    // Один переключатель управляет всей автовыдачей и синхронно включает выбранного поставщика.
    const value = Boolean(enabled)
    props.ozonDigitalSettings.auto_issue_enabled = value
    props.ozonDigitalSettings.interhub_enabled = value
  },
})

const poolIssueEnabled = computed({
  get: () => Boolean(props.ozonDigitalSettings.pool_issue_enabled),
  set: (enabled) => {
    // Включает отдельный резервный источник, который никогда не запускает покупку у поставщика.
    props.ozonDigitalSettings.pool_issue_enabled = Boolean(enabled)
  },
})

function toggleSupplier() {
  // Сворачивает настройки Interhub, чтобы экран ключей оставался компактным.
  isSupplierOpen.value = !isSupplierOpen.value
}

function interhubServiceLabel(service) {
  // Собирает понятное имя услуги для поля поиска и компактного списка.
  if (!service) return ''
  const title = String(service?.title || '').trim()
  const category = String(service?.category || '').trim()
  return category ? `${title} · ${category}` : title
}

const selectedInterhubService = computed(() => props.interhubServices.find((item) => (
  Number(item?.service_id) === Number(props.ozonDigitalSettings.interhub_service_id)
)) || null)

const filteredInterhubServices = computed(() => {
  // Ищет по видимым данным услуги, чтобы не заставлять оператора листать общий список.
  const query = String(interhubServiceSearch.value || '').trim().toLocaleLowerCase('ru-RU')
  const items = Array.isArray(props.interhubServices) ? props.interhubServices : []
  if (!query) return items.slice(0, 80)
  return items.filter((service) => `${service?.service_id || ''} ${interhubServiceLabel(service)}`.toLocaleLowerCase('ru-RU').includes(query)).slice(0, 80)
})

watch(selectedInterhubService, (service) => {
  // Возвращает в поле выбранное значение после загрузки настроек или явной смены услуги.
  if (!isInterhubServicePickerOpen.value) interhubServiceSearch.value = interhubServiceLabel(service)
}, { immediate: true })

function openInterhubServicePicker() {
  // Открывает подсказки при вводе, не меняя привязку до явного выбора строки.
  isInterhubServicePickerOpen.value = true
}

function closeInterhubServicePicker() {
  // Закрывает список после ухода из поля и восстанавливает выбранную услугу вместо черновика поиска.
  window.setTimeout(() => {
    isInterhubServicePickerOpen.value = false
    interhubServiceSearch.value = interhubServiceLabel(selectedInterhubService.value)
  }, 120)
}

function toggleInterhubServicePicker() {
  // По стрелке показывает весь список, чтобы услугу можно было выбрать и без ввода запроса.
  if (isInterhubServicePickerOpen.value) {
    closeInterhubServicePicker()
    return
  }
  interhubServiceSearch.value = ''
  isInterhubServicePickerOpen.value = true
}

function selectInterhubService(service) {
  // Меняет услугу одним действием и очищает прежний номинал, который мог относиться к другой услуге.
  props.ozonDigitalSettings.interhub_service_id = Number(service?.service_id || 0) || null
  props.ozonDigitalSettings.interhub_nominal_id = ''
  interhubServiceSearch.value = interhubServiceLabel(service)
  isInterhubServicePickerOpen.value = false
}

function selectFirstInterhubService() {
  // Enter подтверждает первую найденную подсказку, чтобы поиск работал без мыши.
  if (filteredInterhubServices.value[0]) selectInterhubService(filteredInterhubServices.value[0])
}

function clearInterhubService() {
  // Сбрасывает связку целиком, не оставляя в настройках номинал от прежнего товара.
  props.ozonDigitalSettings.interhub_service_id = null
  props.ozonDigitalSettings.interhub_nominal_id = ''
  interhubServiceSearch.value = ''
  isInterhubServicePickerOpen.value = true
}

const manualOzonDigitalOrders = computed(() => {
  // Оставляет здесь только заказы с ручной выдачей: история выданных заказов находится в карточке товара.
  return props.ozonDigitalOrders.filter((order) => String(order?.status || '').trim().toLowerCase() === 'manual_required')
})

const interhubNominals = computed(() => {
  // Берёт номиналы выбранной услуги из каталога поставщика, не требуя ручного ввода технического ID.
  const service = props.interhubServices.find((item) => Number(item?.service_id) === Number(props.ozonDigitalSettings.interhub_service_id))
  const field = Array.isArray(service?.fields) ? service.fields.find((item) => String(item?.name || '').toLowerCase() === 'nominal') : null
  const values = Array.isArray(field?.value_list) ? field.value_list : []
  return values.map((item) => ({
    value: String(item?.id ?? item?.value ?? ''),
    label: String(item?.name ?? item?.title ?? item?.value ?? item?.id ?? ''),
  })).filter((item) => item.value && item.label)
})

function formatOzonDate(value) {
  // Показывает срок выдачи в локальном формате, чтобы оператор сразу видел срочные заказы.
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function manualDeliveryLabel(order) {
  // Подсказывает только недостающее число кодов, если часть заказа уже получила автовыдача.
  const requiredQty = Math.max(1, Number(order?.required_qty || 1))
  const remainingQty = Math.max(0, Number(order?.remaining_qty ?? requiredQty))
  if (requiredQty === 1) return 'Ключ'
  return remainingQty === requiredQty
    ? `Ключи — по одному в строке (${requiredQty})`
    : `Добавьте ключи — по одному в строке (осталось ${remainingQty} из ${requiredQty})`
}

function hasSavedDelivery(order) {
  // Показывает безопасный повтор без раскрытия ключа, когда полный комплект уже закреплен до прошлого сбоя.
  return Number(order?.remaining_qty ?? order?.required_qty ?? 1) === 0
}

async function submitDelivery(order) {
  // Блокирует повторный клик, пока Ozon подтверждает передачу введенного ключа.
  const orderId = Number(order?.id || 0)
  if (!orderId || deliveryBusy[orderId]) return
  deliveryBusy[orderId] = true
  try {
    const result = await props.deliverOzonDigitalOrder(order, deliveryDrafts[orderId])
    if (result?.ok) deliveryDrafts[orderId] = ''
  } finally {
    deliveryBusy[orderId] = false
  }
}
</script>
