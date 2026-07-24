<template>
  <teleport to="body">
    <div
      v-if="showOzonCatalogDetails"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeOzonCatalogDetails"
    >
      <div class="modal modal--auto ozon-catalog-details-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div>
            <h3>Параметры карточки Ozon</h3>
          </div>
          <div class="toolbar-actions ozon-catalog-details-modal__head-actions">
            <button
              v-if="ozonCatalogDetails"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              type="button"
              aria-label="Открыть ключи"
              title="Ключи"
              @click="openOzonDigitalSettings"
            >
              <svg class="ozon-catalog-details-modal__keys-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 4h14a1 1 0 0 1 1 1v4a2 2 0 0 0 0 4v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4a2 2 0 0 0 0-4V5a1 1 0 0 1 1-1Z" />
                <path d="M13 7v2M13 11v2M13 15v2" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Вернуться к каталогу"
              title="К каталогу"
              @click="closeOzonCatalogDetails"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M19 12H5" />
                <path d="m11 18-6-6 6-6" />
              </svg>
            </button>
            <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonCatalogDetails">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': isDetailsBusy, 'modal__body--loader': isDetailsBusy }">
          <div v-if="isDetailsBusy" class="modal__body-overlay">
            <WorkHamsterLoader :label="detailsBusyLabel" />
          </div>
          <p v-if="!ozonCatalogDetailsLoading && ozonCatalogDetailsError" class="bad">{{ ozonCatalogDetailsError }}</p>
          <template v-if="!ozonCatalogDetailsLoading && ozonCatalogDetails">
            <section class="ozon-catalog-details-modal__overview" :class="{ 'has-image': ozonCatalogDetails.primary_image }">
              <div v-if="ozonCatalogDetails.primary_image" class="ozon-catalog-details-modal__image-wrap">
                <img class="ozon-catalog-details-modal__image" :src="ozonCatalogDetails.primary_image" alt="Главное изображение товара Ozon" />
              </div>
              <div class="ozon-catalog-details-modal__overview-info">
                <h4 v-if="ozonCatalogDetails.title" class="ozon-catalog-details-modal__title">{{ ozonCatalogDetails.title }}</h4>
                <dl v-if="detailFields.length" class="ozon-catalog-details-modal__grid">
                  <template v-for="field in detailFields" :key="field.label">
                    <dt>{{ field.label }}</dt>
                    <dd>{{ field.value }}</dd>
                  </template>
                </dl>
                <p v-else-if="!ozonCatalogDetails.primary_image" class="muted">Ozon не передал дополнительных параметров для этой карточки.</p>
              </div>
            </section>

            <div class="ozon-catalog-details-modal__work-blocks">
              <section class="ozon-catalog-details-modal__work-block" :class="{ 'is-open': isSaleSettingsOpen }">
                <button
                  class="ozon-catalog-details-modal__work-block-toggle"
                  type="button"
                  :aria-expanded="isSaleSettingsOpen"
                  aria-controls="ozon-sale-settings"
                  :disabled="ozonDigitalSettingsLoading || ozonDigitalSettingsSaving"
                  @click="toggleSaleSettings"
                >
                  <span class="ozon-catalog-details-modal__work-block-number">01</span>
                  <span class="ozon-catalog-details-modal__work-block-copy">
                    <strong>Остаток и инструкции</strong>
                    <small>Лимит продаж и сообщения для покупателя</small>
                  </span>
                  <svg class="ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m7 9 5 5 5-5" />
                  </svg>
                </button>
                <div v-if="isSaleSettingsOpen" id="ozon-sale-settings" class="ozon-catalog-details-modal__work-block-body">
                  <p v-if="ozonDigitalSettingsError" class="bad">{{ ozonDigitalSettingsError }}</p>
                  <p v-if="ozonDigitalSettingsOk" class="good">{{ ozonDigitalSettingsOk }}</p>
                  <div class="ozon-catalog-details-modal__sale-settings-form">
                    <label class="field ozon-catalog-details-modal__stock-field">
                      <span>Остаток для Ozon</span>
                      <input v-model.number="ozonDigitalSettings.manual_stock_limit" class="input" type="number" min="0" max="100000" step="1" />
                      <button class="btn btn--primary ozon-catalog-details-modal__stock-submit" type="button" :disabled="ozonDigitalSettingsSaving" @click="saveOzonDigitalSettings">
                        {{ ozonDigitalSettingsSaving ? 'Отправляем…' : 'Отправить' }}
                      </button>
                    </label>
                    <label class="field">
                      <span>Инструкция покупателю</span>
                      <textarea v-model="ozonDigitalSettings.activation_instruction" class="input textarea" rows="3" placeholder="Например: активируйте ключ в PlayStation Store."></textarea>
                    </label>
                    <label class="field">
                      <span>Сообщение при проблеме</span>
                      <textarea v-model="ozonDigitalSettings.support_error_message" class="input textarea" rows="3" placeholder="Произошла ошибка, обратитесь в поддержку."></textarea>
                    </label>
                  </div>
                </div>
              </section>

              <section class="ozon-catalog-details-modal__work-block" :class="{ 'is-open': isOrderHistoryOpen }">
                <button
                  class="ozon-catalog-details-modal__work-block-toggle"
                  type="button"
                  :aria-expanded="isOrderHistoryOpen"
                  aria-controls="ozon-order-history"
                  :disabled="ozonDigitalOrdersSyncing"
                  @click="toggleOrderHistory"
                >
                  <span class="ozon-catalog-details-modal__work-block-number">02</span>
                  <span class="ozon-catalog-details-modal__work-block-copy">
                    <strong>Заказы</strong>
                    <small>История продаж этой карточки в Ozon</small>
                  </span>
                  <svg class="ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m7 9 5 5 5-5" />
                  </svg>
                </button>
              <section v-if="isOrderHistoryOpen" id="ozon-order-history" class="ozon-catalog-details-modal__order-history ozon-catalog-details-modal__work-block-body" aria-label="История заказов Ozon">
                <p v-if="ozonDigitalSettingsError" class="bad">{{ ozonDigitalSettingsError }}</p>
                <div class="ozon-catalog-details-modal__order-history-toolbar">
                  <label v-if="ozonDigitalOrders.length" class="ozon-catalog-details-modal__order-history-search">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <circle cx="11" cy="11" r="6" />
                      <path d="m16 16 4 4" />
                    </svg>
                    <input v-model.trim="orderHistoryQuery" class="input" type="search" placeholder="Поиск: заказ, SKU или дата" @input="resetOrderHistoryPage" />
                  </label>
                  <div class="ozon-catalog-details-modal__order-history-actions">
                    <span v-if="ozonDigitalSettings.last_orders_sync_at">Обновлено: {{ formatOzonDate(ozonDigitalSettings.last_orders_sync_at) }}</span>
                    <button
                      class="btn btn--icon-plain deal-create-action-btn ozon-catalog-details-modal__sync-orders-btn"
                      type="button"
                      :disabled="ozonDigitalOrdersSyncing"
                      :title="ozonDigitalOrdersSyncing ? 'Синхронизация заказов' : 'Синхронизировать заказы'"
                      :aria-label="ozonDigitalOrdersSyncing ? 'Синхронизация заказов' : 'Синхронизировать заказы'"
                      @click="syncOzonDigitalOrders"
                    >
                      <svg :class="{ 'is-loading': ozonDigitalOrdersSyncing }" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                        <path d="M20 4v6h-6" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div v-if="filteredSortedOzonDigitalOrders.length" class="ozon-catalog-details-modal__order-history-table-wrap">
                  <table class="table table--compact table--dense ozon-catalog-details-modal__order-history-table">
                    <colgroup>
                      <col class="ozon-catalog-details-modal__order-column" />
                      <col class="ozon-catalog-details-modal__status-column" />
                      <col class="ozon-catalog-details-modal__source-column" />
                      <col class="ozon-catalog-details-modal__date-column" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>
                          <span class="th-title th-title--filter">Заказ
                            <button class="filter-icon filter-icon--sort" type="button" aria-label="Сортировка по заказу" title="Сортировка по заказу" :class="getOrderHistorySortClass('order')" @click.stop="toggleOrderHistorySort('order')">
                              <svg viewBox="0 0 24 24" aria-hidden="true"><path class="sort-icon__up" d="M7 10l5-5 5 5" /><path class="sort-icon__down" d="M7 14l5 5 5-5" /></svg>
                            </button>
                          </span>
                        </th>
                        <th>
                          <span class="th-title th-title--filter">Статус Ozon
                            <button class="filter-icon filter-icon--sort" type="button" aria-label="Сортировка по статусу Ozon" title="Сортировка по статусу Ozon" :class="getOrderHistorySortClass('status')" @click.stop="toggleOrderHistorySort('status')">
                              <svg viewBox="0 0 24 24" aria-hidden="true"><path class="sort-icon__up" d="M7 10l5-5 5 5" /><path class="sort-icon__down" d="M7 14l5 5 5-5" /></svg>
                            </button>
                          </span>
                        </th>
                        <th>
                          <span class="th-title th-title--filter">Источник
                            <button class="filter-icon filter-icon--sort" type="button" aria-label="Сортировка по источнику" title="Сортировка по источнику" :class="getOrderHistorySortClass('source')" @click.stop="toggleOrderHistorySort('source')">
                              <svg viewBox="0 0 24 24" aria-hidden="true"><path class="sort-icon__up" d="M7 10l5-5 5 5" /><path class="sort-icon__down" d="M7 14l5 5 5-5" /></svg>
                            </button>
                          </span>
                        </th>
                        <th>
                          <span class="th-title th-title--filter">Дата
                            <button class="filter-icon filter-icon--sort" type="button" aria-label="Сортировка по дате" title="Сортировка по дате" :class="getOrderHistorySortClass('date')" @click.stop="toggleOrderHistorySort('date')">
                              <svg viewBox="0 0 24 24" aria-hidden="true"><path class="sort-icon__up" d="M7 10l5-5 5 5" /><path class="sort-icon__down" d="M7 14l5 5 5-5" /></svg>
                            </button>
                          </span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="order in visibleOzonDigitalOrders" :key="order.id || `${order.posting_number}-${order.sku}`">
                        <td>
                          <strong>{{ order.order_number ? `Заказ ${order.order_number}` : 'Номер заказа не получен' }}</strong>
                          <span>Отправление {{ order.posting_number || '—' }} · SKU {{ order.sku || '—' }} · {{ order.required_qty || 1 }} шт.</span>
                        </td>
                        <td>{{ ozonStatusLabel(order.ozon_status, order.status) }}</td>
                        <td class="ozon-catalog-details-modal__order-source">
                          <div class="ozon-catalog-details-modal__order-source-content">
                            <span>{{ deliverySourceLabel(order.delivery_source) }}</span>
                            <button
                              v-if="canOpenSupplierOperation(order)"
                              class="ozon-catalog-details-modal__supplier-operation-action"
                              type="button"
                              :aria-label="`Открыть выдачу для заказа ${order.id}`"
                              title="Открыть выдачу"
                              @click="openSupplierOperation(order)"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M6 3h9l3 3v15H6z" />
                                <path d="M15 3v4h4M9 11h6M9 15h6" />
                              </svg>
                            </button>
                          </div>
                        </td>
                        <td>
                          <strong>{{ formatOzonDate(order.created_at) || '—' }}</strong>
                          <span v-if="order.delivered_at">Выдан: {{ formatOzonDate(order.delivered_at) }}</span>
                          <span v-else-if="order.waiting_deadline_at">Код до: {{ formatOzonDate(order.waiting_deadline_at) }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="filteredSortedOzonDigitalOrders.length" class="ozon-catalog-details-modal__order-history-pagination">
                  <span>{{ orderHistoryRange }}</span>
                  <div>
                    <button class="ghost" type="button" aria-label="Предыдущая страница заказов" :disabled="activeOrderHistoryPage <= 1" @click="changeOrderHistoryPage(-1)">
                      Назад
                    </button>
                    <button class="ghost" type="button" aria-label="Следующая страница заказов" :disabled="activeOrderHistoryPage >= orderHistoryPageCount" @click="changeOrderHistoryPage(1)">
                      Вперёд
                    </button>
                  </div>
                </div>
                <p v-else-if="ozonDigitalOrders.length" class="muted ozon-catalog-details-modal__order-history-empty">По вашему запросу заказы не найдены.</p>
                <p v-else class="muted ozon-catalog-details-modal__order-history-empty">Заказов по этой карточке пока нет.</p>
              </section>
              </section>
            </div>
          </template>
        </div>
        <div v-if="showSupplierOperation" class="ozon-catalog-details-modal__supplier-operation-backdrop" @click.self="closeSupplierOperation">
          <section class="ozon-catalog-details-modal__supplier-operation" role="dialog" aria-modal="true" aria-label="Операция поставщика">
            <div class="panel__head panel__head--tight modal__head ozon-catalog-details-modal__supplier-operation-head">
              <div>
                <span>{{ supplierOperation ? 'Операция поставщика' : 'Выдача ключа' }}</span>
                <strong>{{ supplierOperationProviderName }}</strong>
              </div>
              <button
                class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close ozon-catalog-details-modal__supplier-operation-close"
                type="button"
                aria-label="Закрыть операцию поставщика"
                title="Закрыть"
                @click="closeSupplierOperation"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 6l12 12M18 6l-12 12" />
                </svg>
              </button>
            </div>
            <div v-if="supplierOperationLoading" class="ozon-catalog-details-modal__supplier-operation-loading">
              <WorkHamsterLoader label="Загружаем операцию…" />
            </div>
            <p v-else-if="supplierOperationError && !supplierOperationCodes.length" class="bad">{{ supplierOperationError }}</p>
            <dl v-else-if="supplierOperation || supplierOperationCodes.length" class="ozon-catalog-details-modal__supplier-operation-grid">
              <template v-if="supplierOperation">
              <dt>Agent transaction ID</dt>
              <dd class="ozon-catalog-details-modal__supplier-operation-identifier">
                <code>{{ supplierOperation.agent_transaction_id }}</code>
                <button
                  class="btn btn--icon-plain ozon-catalog-details-modal__supplier-operation-copy"
                  type="button"
                  aria-label="Копировать Agent transaction ID"
                  title="Копировать"
                  @click="copySupplierOperationValue(supplierOperation.agent_transaction_id, 'agent')"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="8" y="8" width="11" height="11" rx="2" />
                    <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
                  </svg>
                </button>
              </dd>
              <dt>Операция поставщика</dt>
              <dd v-if="supplierOperation.provider_transaction_id" class="ozon-catalog-details-modal__supplier-operation-identifier">
                <code>{{ supplierOperation.provider_transaction_id }}</code>
                <button
                  class="btn btn--icon-plain ozon-catalog-details-modal__supplier-operation-copy"
                  type="button"
                  aria-label="Копировать операцию поставщика"
                  title="Копировать"
                  @click="copySupplierOperationValue(supplierOperation.provider_transaction_id, 'provider')"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="8" y="8" width="11" height="11" rx="2" />
                    <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
                  </svg>
                </button>
              </dd>
              <dd v-else>Не передан поставщиком</dd>
              <dt>Услуга</dt>
              <dd>{{ supplierOperationServiceTitle }}</dd>
              <dt>Номинал</dt>
              <dd>{{ supplierOperationNominalTitle }}</dd>
              <dt>Сумма</dt>
              <dd>{{ formatSupplierOperationAmount(supplierOperation.amount) }}</dd>
              <dt>Статус</dt>
              <dd>{{ supplierOperationStateLabel(supplierOperation.state) }}</dd>
              <dt>Ответ поставщика</dt>
              <dd>{{ supplierOperation.provider_message || '—' }}</dd>
              <dt>Обновлено</dt>
              <dd>{{ formatOzonDate(supplierOperation.updated_at || supplierOperation.created_at) || '—' }}</dd>
              </template>
              <dt>Ключ</dt>
              <dd class="ozon-catalog-details-modal__supplier-operation-identifier">
                <code>{{ supplierOperationCodes.join('\n') }}</code>
                <button
                  class="btn btn--icon-plain ozon-catalog-details-modal__supplier-operation-copy"
                  type="button"
                  aria-label="Копировать ключ выдачи"
                  title="Копировать"
                  @click="copySupplierOperationValue(supplierOperationCodes.join('\n'), 'code')"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="8" y="8" width="11" height="11" rx="2" />
                    <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
                  </svg>
                </button>
              </dd>
            </dl>
          </section>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

const props = defineProps({
  showOzonCatalogDetails: { type: Boolean, required: true },
  closeOzonCatalogDetails: { type: Function, required: true },
  openOzonDigitalSettings: { type: Function, required: true },
  ozonCatalogDetails: { type: [Object, null], default: null },
  ozonCatalogDetailsLoading: { type: Boolean, required: true },
  ozonCatalogDetailsError: { type: String, default: '' },
  ozonDigitalSettings: { type: Object, required: true },
  ozonDigitalSettingsLoading: { type: Boolean, required: true },
  ozonDigitalSettingsSaving: { type: Boolean, required: true },
  ozonDigitalOrdersSyncing: { type: Boolean, required: true },
  ozonDigitalSettingsError: { type: String, default: '' },
  ozonDigitalSettingsOk: { type: String, default: '' },
  ozonDigitalOrders: { type: Array, default: () => [] },
  loadOzonDigitalSettings: { type: Function, required: true },
  saveOzonDigitalSettings: { type: Function, required: true },
  syncOzonDigitalOrders: { type: Function, required: true },
  canRevealOzonDigitalCodes: { type: Boolean, default: false },
  revealOzonDigitalOrderCodes: { type: Function, default: null },
  loadOzonDigitalSupplierOperation: { type: Function, default: null },
})

const ORDER_HISTORY_PAGE_SIZE = 10
const orderHistoryPage = ref(1)
const orderHistoryQuery = ref('')
const orderHistorySort = ref({ key: 'date', dir: 'desc' })
const isSaleSettingsOpen = ref(false)
const isOrderHistoryOpen = ref(false)
const showSupplierOperation = ref(false)
const supplierOperationLoading = ref(false)
const supplierOperationError = ref('')
const supplierOperation = ref(null)
const supplierOperationOrder = ref(null)
const supplierOperationCodes = ref([])
const copiedSupplierOperationValue = ref('')

watch(() => props.showOzonCatalogDetails, (isOpen) => {
  // При новом открытии карточки скрывает рабочие разделы, чтобы не запрашивать ключи и настройки заранее.
  if (!isOpen) return
  isSaleSettingsOpen.value = false
  isOrderHistoryOpen.value = false
  orderHistoryQuery.value = ''
  resetOrderHistoryPage()
})

const isDetailsBusy = computed(() => props.ozonCatalogDetailsLoading || props.ozonDigitalSettingsLoading || props.ozonDigitalSettingsSaving || props.ozonDigitalOrdersSyncing)
const detailsBusyLabel = computed(() => {
  // Показывает понятную причину ожидания, пока настройки карточки нельзя менять повторно.
  if (props.ozonDigitalOrdersSyncing) return 'Синхронизируем заказы Ozon…'
  if (props.ozonDigitalSettingsSaving) return 'Сохраняем настройки и отправляем остаток…'
  if (props.ozonDigitalSettingsLoading) return 'Загружаем настройки продажи…'
  return 'Загружаем данные карточки…'
})

function formatOzonDate(value) {
  // Показывает дату в привычном виде, а при нестандартном ответе оставляет исходное значение Ozon.
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function ozonStatusLabel(ozonStatus, localStatus) {
  // Подтвержденная выдача важнее промежуточного ответа Ozon, который может обновляться с задержкой.
  const normalized = String(ozonStatus || '').trim().toLowerCase()
  const normalizedLocal = String(localStatus || '').trim().toLowerCase()
  if (normalizedLocal === 'delivered') return 'Доставлено'
  if (normalizedLocal === 'cancelled') return 'Отменено'
  if (!normalized) {
    if (normalizedLocal === 'supplier_processing') return 'Обрабатывается поставщиком'
    if (normalizedLocal === 'delivering') return 'Ключ отправляется'
    return 'Ожидает ключ'
  }
  if (normalized === 'done') return 'Доставлено'
  if (normalized.includes('cancel')) return 'Отменено'
  return `Ozon: ${ozonStatus}`
}

async function toggleSaleSettings() {
  // Загружает настройки только при раскрытии блока, чтобы карточка товара открывалась без запроса ключей.
  if (isSaleSettingsOpen.value) {
    isSaleSettingsOpen.value = false
    return
  }
  isSaleSettingsOpen.value = true
  const productId = Number(props.ozonCatalogDetails?.external_product_id || 0)
  if (productId) await props.loadOzonDigitalSettings(productId, { includeOrders: false })
}

async function toggleOrderHistory() {
  // Открывает историю только по явному действию и сразу запрашивает свежие заказы выбранной карточки.
  if (isOrderHistoryOpen.value) {
    isOrderHistoryOpen.value = false
    return
  }
  isOrderHistoryOpen.value = true
  await props.syncOzonDigitalOrders()
}

function deliverySourceLabel(source) {
  // Показывает оператору понятный способ выдачи вместо внутреннего кода поставщика.
  const normalized = String(source || '').trim().toLowerCase()
  if (normalized === 'interhub') return 'Interhub'
  if (normalized === 'manual') return 'Ручной ввод'
  return source || '—'
}

function canOpenSupplierOperation(order) {
  // Открывает одну карточку выдачи только для выданного ключа и при явном праве его просмотра.
  const source = String(order?.delivery_source || '').trim().toLowerCase()
  return props.canRevealOzonDigitalCodes
    && typeof props.revealOzonDigitalOrderCodes === 'function'
    && (source === 'manual' || (source === 'interhub' && typeof props.loadOzonDigitalSupplierOperation === 'function'))
}

async function openSupplierOperation(order) {
  // Открывает одну карточку выдачи: с реквизитами Interhub или только вручную введенным ключом.
  if (!canOpenSupplierOperation(order)) return
  showSupplierOperation.value = true
  supplierOperationLoading.value = true
  supplierOperationError.value = ''
  supplierOperation.value = null
  supplierOperationOrder.value = order
  supplierOperationCodes.value = []
  copiedSupplierOperationValue.value = ''
  const codesResult = await props.revealOzonDigitalOrderCodes(order)
  if (codesResult?.ok && Array.isArray(codesResult.codes) && codesResult.codes.length) {
    supplierOperationCodes.value = codesResult.codes
  } else {
    supplierOperationError.value = codesResult?.message || 'Ключ для этого заказа не найден'
  }
  if (String(order?.delivery_source || '').trim().toLowerCase() === 'interhub') {
    const result = await props.loadOzonDigitalSupplierOperation(order)
    if (result?.ok && result.operation) {
      supplierOperation.value = result.operation
    } else if (!supplierOperationError.value) {
      supplierOperationError.value = result?.message || 'Операция поставщика не найдена'
    }
  }
  supplierOperationLoading.value = false
}

function closeSupplierOperation() {
  // Закрывает карточку операции и очищает реквизиты предыдущего заказа из локального состояния.
  showSupplierOperation.value = false
  supplierOperation.value = null
  supplierOperationOrder.value = null
  supplierOperationCodes.value = []
  supplierOperationError.value = ''
  copiedSupplierOperationValue.value = ''
}

function supplierOperationStateLabel(state) {
  // Переводит внутренний статус поставщика в короткий текст для оператора.
  const normalized = String(state || '').trim().toLowerCase()
  if (normalized === 'paid') return 'Оплачено и выдано'
  if (normalized === 'processing') return 'В обработке'
  if (normalized === 'failed') return 'Неуспешно'
  return state || '—'
}

function formatSupplierOperationAmount(value) {
  // Форматирует сумму поставщика, оставляя неизвестное значение явным, а не подменяя его нулём.
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 2 }).format(amount)
}

async function copySupplierOperationValue(value, key) {
  // Копирует выбранный идентификатор операции, чтобы его можно было быстро отправить в поддержку поставщика.
  const transactionId = String(value || '').trim()
  if (!transactionId) return
  try {
    await globalThis.navigator?.clipboard?.writeText(transactionId)
    copiedSupplierOperationValue.value = key
  } catch {
    supplierOperationError.value = 'Не удалось скопировать идентификатор операции'
  }
}

const supplierOperationProviderName = computed(() => deliverySourceLabel(supplierOperation.value?.provider_code || supplierOperationOrder.value?.delivery_source))

const supplierOperationServiceTitle = computed(() => {
  // Показывает название услуги из calculate, сохраняя технический ID для старой истории.
  const operation = supplierOperation.value || {}
  return String(operation.service_title || '').trim() || `Услуга #${operation.service_id || '—'}`
})

const supplierOperationNominalTitle = computed(() => {
  // Показывает название номинала из calculate, сохраняя технический ID для старой истории.
  const operation = supplierOperation.value || {}
  return String(operation.nominal_title || '').trim()
    || (operation.nominal_id ? `Номинал #${operation.nominal_id}` : '')
})

function orderHistorySearchText(order) {
  // Собирает номер заказа, SKU и оба формата даты, чтобы один поиск находил нужную запись.
  const createdAt = order?.created_at || ''
  const deliveredAt = order?.delivered_at || ''
  const dateText = [createdAt, deliveredAt]
    .flatMap((value) => [value, formatOzonDate(value), value ? new Date(value).toLocaleDateString('ru-RU') : ''])
  return [
    order?.order_number,
    order?.posting_number,
    order?.sku,
    ozonStatusLabel(order?.ozon_status, order?.status),
    deliverySourceLabel(order?.delivery_source),
    ...dateText,
  ].join(' ').toLocaleLowerCase('ru-RU')
}

function orderHistorySortValue(order, key) {
  // Возвращает одно значение для сортировки каждой колонки, сохраняя даты числовыми.
  if (key === 'date') return new Date(order?.created_at || 0).getTime() || 0
  if (key === 'status') return ozonStatusLabel(order?.ozon_status, order?.status)
  if (key === 'source') return deliverySourceLabel(order?.delivery_source)
  return `${order?.order_number || ''} ${order?.posting_number || ''}`
}

const filteredSortedOzonDigitalOrders = computed(() => {
  // Фильтрует историю по введенному тексту и сортирует её до разбиения на страницы.
  const query = String(orderHistoryQuery.value || '').trim().toLocaleLowerCase('ru-RU')
  const { key, dir } = orderHistorySort.value
  const multiplier = dir === 'asc' ? 1 : -1
  return [...props.ozonDigitalOrders]
    .filter((order) => !query || orderHistorySearchText(order).includes(query))
    .sort((left, right) => {
      const leftValue = orderHistorySortValue(left, key)
      const rightValue = orderHistorySortValue(right, key)
      if (typeof leftValue === 'number' && typeof rightValue === 'number') return (leftValue - rightValue) * multiplier
      return String(leftValue).localeCompare(String(rightValue), 'ru', { numeric: true, sensitivity: 'base' }) * multiplier
    })
})

const orderHistoryPageCount = computed(() => Math.max(1, Math.ceil(filteredSortedOzonDigitalOrders.value.length / ORDER_HISTORY_PAGE_SIZE)))
const activeOrderHistoryPage = computed(() => Math.min(Math.max(orderHistoryPage.value, 1), orderHistoryPageCount.value))
const visibleOzonDigitalOrders = computed(() => {
  // Отдаёт только текущую страницу истории, чтобы длинный журнал не растягивал модальное окно.
  const offset = (activeOrderHistoryPage.value - 1) * ORDER_HISTORY_PAGE_SIZE
  return filteredSortedOzonDigitalOrders.value.slice(offset, offset + ORDER_HISTORY_PAGE_SIZE)
})
const orderHistoryRange = computed(() => {
  // Показывает оператору границы открытой страницы и общее количество заказов по карточке.
  const total = filteredSortedOzonDigitalOrders.value.length
  if (!total) return ''
  const start = (activeOrderHistoryPage.value - 1) * ORDER_HISTORY_PAGE_SIZE + 1
  const end = Math.min(start + ORDER_HISTORY_PAGE_SIZE - 1, total)
  return `Показаны ${start}–${end} из ${total}`
})

function changeOrderHistoryPage(delta) {
  // Переключает страницу в допустимых границах, не позволяя уйти за начало или конец истории.
  orderHistoryPage.value = Math.min(orderHistoryPageCount.value, Math.max(1, activeOrderHistoryPage.value + delta))
}

function resetOrderHistoryPage() {
  // Возвращает к началу, чтобы новый поисковый запрос не оставил пользователя на пустой странице.
  orderHistoryPage.value = 1
}

function toggleOrderHistorySort(key) {
  // Переключает направление повторным нажатием и начинает показ с первой страницы.
  if (orderHistorySort.value.key === key) {
    orderHistorySort.value = { key, dir: orderHistorySort.value.dir === 'asc' ? 'desc' : 'asc' }
  } else {
    orderHistorySort.value = { key, dir: 'asc' }
  }
  resetOrderHistoryPage()
}

function getOrderHistorySortClass(key) {
  // Подключает общий индикатор сортировки из таблицы сделок к текущей колонке истории.
  const direction = orderHistorySort.value.key === key ? orderHistorySort.value.dir : ''
  return {
    'sort-icon--active': Boolean(direction),
    'sort-icon--asc': direction === 'asc',
    'sort-icon--desc': direction === 'desc',
  }
}

const detailFields = computed(() => {
  // Формирует только заполненные и неповторяющиеся реквизиты, полезные для работы с карточкой.
  const details = props.ozonCatalogDetails || {}
  const barcodes = Array.isArray(details.barcodes) ? details.barcodes.filter(Boolean).join(', ') : ''
  return [
    { label: 'Артикул продавца', value: details.offer_id || '' },
    { label: 'SKU', value: details.sku || '' },
    { label: 'Штрихкоды', value: barcodes },
    { label: 'Категория Ozon', value: details.category_id ? String(details.category_id) : '' },
    { label: 'FBO SKU', value: details.fbo_sku || '' },
    { label: 'FBS SKU', value: details.fbs_sku || '' },
    { label: 'Цена', value: [details.price, details.price_currency_code].filter(Boolean).join(' ') },
    { label: 'Остаток Ozon', value: Number.isInteger(details.available_stock) ? String(details.available_stock) : '' },
  ].filter((field) => field.value)
})
</script>
