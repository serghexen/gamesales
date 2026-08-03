<template>
  <teleport to="body">
    <div v-if="showYandexMarketCatalogDetails" class="work-page work-modal-root modal-backdrop" @click.self="closeYandexMarketCatalogDetails">
      <div class="modal modal--auto yandex-catalog-details-modal ozon-catalog-details-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div><h3>Параметры карточки Яндекс Маркета</h3></div>
          <div class="toolbar-actions yandex-catalog-details-modal__head-actions ozon-catalog-details-modal__head-actions"><button v-if="yandexMarketCatalogDetails" class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save" type="button" aria-label="Открыть ключи" title="Ключи" @click="openYandexMarketDigitalSettings"><svg class="ozon-catalog-details-modal__keys-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14a1 1 0 0 1 1 1v4a2 2 0 0 0 0 4v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4a2 2 0 0 0 0-4V5a1 1 0 0 1 1-1Z" /><path d="M13 7v2M13 11v2M13 15v2" /></svg></button><button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--edit" type="button" aria-label="Вернуться к каталогу" title="К каталогу" @click="closeYandexMarketCatalogDetails"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></svg></button><button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeYandexMarketCatalogDetails"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg></button></div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': yandexMarketCatalogDetailsLoading, 'modal__body--loader': yandexMarketCatalogDetailsLoading }">
          <div v-if="yandexMarketCatalogDetailsLoading" class="modal__body-overlay"><WorkHamsterLoader label="Загружаем параметры и остаток Маркета…" /></div>
          <p v-if="!yandexMarketCatalogDetailsLoading && yandexMarketCatalogDetailsError" class="bad">{{ yandexMarketCatalogDetailsError }}</p>
          <template v-if="!yandexMarketCatalogDetailsLoading && yandexMarketCatalogDetails">
            <section class="yandex-catalog-details-modal__overview ozon-catalog-details-modal__overview" :class="{ 'has-image': yandexMarketCatalogDetails.primary_image }">
              <div v-if="yandexMarketCatalogDetails.primary_image" class="yandex-catalog-details-modal__image-wrap ozon-catalog-details-modal__image-wrap"><img class="yandex-catalog-details-modal__image ozon-catalog-details-modal__image" :src="yandexMarketCatalogDetails.primary_image" alt="Главное изображение товара Яндекс Маркета" /></div>
              <div class="yandex-catalog-details-modal__overview-info ozon-catalog-details-modal__overview-info"><h4 class="yandex-catalog-details-modal__title ozon-catalog-details-modal__title">{{ yandexMarketCatalogDetails.title || yandexMarketCatalogDetails.offer_id }}</h4><dl class="yandex-catalog-details-modal__grid ozon-catalog-details-modal__grid"><template v-for="field in detailFields" :key="field.label"><dt>{{ field.label }}</dt><dd>{{ field.value }}</dd></template></dl></div>
            </section>
            <div class="yandex-catalog-details-modal__work-blocks ozon-catalog-details-modal__work-blocks">
              <section class="yandex-catalog-details-modal__work-block ozon-catalog-details-modal__work-block" :class="{ 'is-open': isStockOpen }">
                <button class="yandex-catalog-details-modal__work-block-toggle ozon-catalog-details-modal__work-block-toggle" type="button" :aria-expanded="isStockOpen" @click="toggleStock">
                  <span class="yandex-catalog-details-modal__work-block-number ozon-catalog-details-modal__work-block-number">01</span>
                  <span class="yandex-catalog-details-modal__work-block-copy ozon-catalog-details-modal__work-block-copy">
                    <strong>Остаток</strong>
                    <small>Актуальное количество, доступное для продажи на Маркете</small>
                  </span>
                  <svg class="yandex-catalog-details-modal__work-block-chevron ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
                </button>
                <div v-if="isStockOpen" class="yandex-catalog-details-modal__work-block-body ozon-catalog-details-modal__work-block-body">
                  <div class="ozon-catalog-details-modal__sale-settings-form">
                    <label class="field ozon-catalog-details-modal__stock-field">
                      <span>Остаток на Маркете</span>
                      <input v-model.number="yandexMarketStockSettings.manual_stock_limit" class="input" type="number" min="0" aria-label="Остаток для публикации на Маркете" />
                      <div class="ozon-catalog-details-modal__stock-actions">
                        <button class="btn btn--primary ozon-catalog-details-modal__stock-submit" type="button" :disabled="yandexMarketStockSettingsSaving" title="Опубликовать указанный остаток в Яндекс Маркете" @click="saveYandexMarketStockSettings({ publishStock: true })">Отправить</button>
                        <button class="btn btn--icon-plain ozon-catalog-details-modal__stock-settings-save" type="button" :disabled="yandexMarketStockSettingsSaving" title="Сохранить инструкцию и настройки выдачи" aria-label="Сохранить настройки карточки" @click="saveYandexMarketStockSettings()">
                          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h12l4 4v12H4z" /><path d="M7 4v6h8V4" /><path d="M7 20v-6h10v6" /></svg>
                        </button>
                      </div>
                    </label>
                    <label class="field">
                      <span>Инструкция покупателю</span>
                      <textarea v-model="yandexMarketStockSettings.activation_instruction" class="input textarea" rows="3" placeholder="Например: активируйте ключ в PlayStation Store." aria-label="Инструкция покупателю"></textarea>
                    </label>
                    <label class="field">
                      <span>Сообщение при проблеме</span>
                      <textarea v-model="yandexMarketStockSettings.support_error_message" class="input textarea" rows="2" placeholder="Например: обратитесь в поддержку." aria-label="Сообщение при проблеме Яндекс Маркета"></textarea>
                    </label>
                  </div>
                </div>
              </section>
              <section class="yandex-catalog-details-modal__work-block ozon-catalog-details-modal__work-block" :class="{ 'is-open': isOrdersOpen }">
                <button class="yandex-catalog-details-modal__work-block-toggle ozon-catalog-details-modal__work-block-toggle" type="button" :aria-expanded="isOrdersOpen" @click="toggleOrders">
                  <span class="yandex-catalog-details-modal__work-block-number ozon-catalog-details-modal__work-block-number">02</span>
                  <span class="yandex-catalog-details-modal__work-block-copy ozon-catalog-details-modal__work-block-copy">
                    <strong>Заказы</strong>
                    <small>История продаж этой карточки на Яндекс Маркете</small>
                  </span>
                  <svg class="yandex-catalog-details-modal__work-block-chevron ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
                </button>
                <div v-if="isOrdersOpen" class="ozon-catalog-details-modal__order-history yandex-catalog-details-modal__work-block-body ozon-catalog-details-modal__work-block-body">
                  <div class="ozon-catalog-details-modal__order-history-toolbar">
                    <label class="ozon-catalog-details-modal__order-history-search">
                      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></svg>
                      <input v-model.trim="orderQuery" class="input" type="search" placeholder="Поиск: заказ, SKU или дата" aria-label="Поиск заказов Яндекс Маркета" @input="resetOrdersPage" />
                    </label>
                    <div class="ozon-catalog-details-modal__order-history-actions">
                      <span v-if="yandexMarketOrdersSyncing">Получаем последние заказы из Маркета…</span>
                      <span v-if="yandexMarketOrdersLastSyncedAt">Обновлено: {{ formatOrderDate(yandexMarketOrdersLastSyncedAt) }}</span>
                      <button class="btn btn--icon-plain deal-create-action-btn ozon-catalog-details-modal__sync-orders-btn" type="button" :disabled="yandexMarketOrdersSyncing" :title="yandexMarketOrdersSyncing ? 'Синхронизация заказов' : 'Синхронизировать заказы'" aria-label="Синхронизировать заказы Яндекс Маркета" @click="syncYandexMarketOrders">
                        <svg :class="{ 'is-loading': yandexMarketOrdersSyncing }" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v6h-6" /></svg>
                      </button>
                    </div>
                  </div>
                  <div v-if="visibleOrders.length" class="ozon-catalog-details-modal__order-history-table-wrap">
                    <table class="table table--compact table--dense ozon-catalog-details-modal__order-history-table">
                      <thead><tr><th>Заказ</th><th>Статус Маркета</th><th>Источник</th><th>Дата</th><th v-if="!yandexMarketSandboxMode">Действие</th></tr></thead>
                      <tbody><tr v-for="order in visibleOrders" :key="`${order.order_id}-${order.item_id}`">
                        <td><strong>Заказ {{ order.order_id }}</strong><span>SKU {{ order.offer_id || '—' }} · {{ order.quantity || 0 }} шт.</span></td>
                        <td><strong>{{ marketStatusLabel(order.status) }}</strong><span v-if="order.substatus">{{ order.substatus }}</span></td>
                        <td>Яндекс Маркет</td>
                        <td><strong>{{ formatOrderDate(order.created_at) || '—' }}</strong><span v-if="order.updated_at">Обновлён: {{ formatOrderDate(order.updated_at) }}</span></td>
                        <td v-if="!yandexMarketSandboxMode">
                          <button v-if="canStartProductionDelivery(order)" class="ghost" type="button" :disabled="isStartingProductionDelivery(order)" :aria-label="`Запустить выдачу заказа Яндекс Маркета ${order.order_id}`" @click="startProductionDelivery(order)">{{ isStartingProductionDelivery(order) ? 'Запускаем…' : 'Запустить выдачу' }}</button>
                          <button v-else-if="canRevealYandexMarketDigitalCodesForOrder(order)" class="ozon-catalog-details-modal__supplier-operation-action" type="button" :aria-label="`Открыть выдачу для заказа Яндекс Маркета ${order.order_id}`" title="Открыть выдачу" @click="openYandexMarketDigitalCodes(order)">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l3 3v15H6z" /><path d="M15 3v4h4M9 11h6M9 15h6" /></svg>
                          </button>
                          <span v-else>—</span>
                        </td>
                      </tr></tbody>
                    </table>
                  </div>
                  <div v-if="filteredOrders.length" class="ozon-catalog-details-modal__order-history-pagination"><span>{{ ordersRange }}</span><div><button class="ghost" type="button" :disabled="ordersPage <= 1" @click="changeOrdersPage(-1)">Назад</button><button class="ghost" type="button" :disabled="ordersPage >= ordersPageCount" @click="changeOrdersPage(1)">Вперёд</button></div></div>
                  <p v-else-if="yandexMarketOrdersLoading" class="muted ozon-catalog-details-modal__order-history-empty">Загружаем сохраненную историю заказов…</p>
                  <p v-else class="muted ozon-catalog-details-modal__order-history-empty">Заказов по этой карточке пока нет. Нажмите обновление, чтобы получить их из Маркета.</p>
                </div>
              </section>
            </div>
          </template>
        </div>
        <div v-if="showYandexMarketDigitalCodes" class="ozon-catalog-details-modal__supplier-operation-backdrop" @click.self="closeYandexMarketDigitalCodes">
          <section class="ozon-catalog-details-modal__supplier-operation" role="dialog" aria-modal="true" aria-label="Выданный ключ Яндекс Маркета">
            <div class="panel__head panel__head--tight modal__head ozon-catalog-details-modal__supplier-operation-head">
              <div><span>Выдача ключа</span><strong>Яндекс Маркет · Заказ {{ yandexMarketDigitalCodesOrder?.order_id }}</strong></div>
              <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close ozon-catalog-details-modal__supplier-operation-close" type="button" aria-label="Закрыть выдачу ключа" title="Закрыть" @click="closeYandexMarketDigitalCodes"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
            </div>
            <div v-if="yandexMarketDigitalCodesLoading" class="ozon-catalog-details-modal__supplier-operation-loading"><WorkHamsterLoader label="Загружаем отправленный ключ…" /></div>
            <p v-else-if="yandexMarketDigitalCodesError" class="bad">{{ yandexMarketDigitalCodesError }}</p>
            <dl v-else-if="yandexMarketDigitalCodes.length" class="ozon-catalog-details-modal__supplier-operation-grid">
              <dt>Ключ</dt>
              <dd class="ozon-catalog-details-modal__supplier-operation-identifier">
                <code>{{ yandexMarketDigitalCodes.join('\n') }}</code>
                <button class="btn btn--icon-plain ozon-catalog-details-modal__supplier-operation-copy" type="button" aria-label="Копировать ключ выдачи Яндекс Маркета" title="Копировать" @click="copyYandexMarketDigitalCodes"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></svg></button>
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
  showYandexMarketCatalogDetails: { type: Boolean, required: true }, closeYandexMarketCatalogDetails: { type: Function, required: true }, openYandexMarketDigitalSettings: { type: Function, required: true }, yandexMarketSandboxMode: { type: Boolean, default: true }, yandexMarketCatalogDetails: { type: Object, default: null }, yandexMarketCatalogDetailsLoading: { type: Boolean, required: true }, yandexMarketCatalogDetailsError: { type: String, default: '' }, yandexMarketStockSettings: { type: Object, required: true }, yandexMarketStockSettingsSaving: { type: Boolean, required: true }, saveYandexMarketStockSettings: { type: Function, required: true }, yandexMarketOrders: { type: Array, default: () => [] }, yandexMarketOrdersLoading: { type: Boolean, required: true }, yandexMarketOrdersSyncing: { type: Boolean, required: true }, yandexMarketOrdersLastSyncedAt: { type: String, default: null }, yandexMarketProductionStartDeliverySaving: { type: Number, default: 0 }, canRevealYandexMarketDigitalCodes: { type: Boolean, default: false }, loadYandexMarketOrders: { type: Function, required: true }, syncYandexMarketOrders: { type: Function, required: true }, startYandexMarketProductionOrder: { type: Function, default: async () => ({ ok: false }) }, revealYandexMarketProductionOrderCodes: { type: Function, default: null },
})

const isStockOpen = ref(false)
const isOrdersOpen = ref(false)
const orderQuery = ref('')
const ordersPage = ref(1)
const showYandexMarketDigitalCodes = ref(false)
const yandexMarketDigitalCodesLoading = ref(false)
const yandexMarketDigitalCodesError = ref('')
const yandexMarketDigitalCodesOrder = ref(null)
const yandexMarketDigitalCodes = ref([])
const ORDERS_PAGE_SIZE = 10

watch(() => props.showYandexMarketCatalogDetails, (isOpen) => {
  // Закрывает секции при новом открытии карточки, как в эталонной форме Ozon.
  if (!isOpen) {
    closeYandexMarketDigitalCodes()
    return
  }
  isStockOpen.value = false
  isOrdersOpen.value = false
  orderQuery.value = ''
  ordersPage.value = 1
})

function toggleStock() {
  // Раскрывает только справочное значение остатка без записи в кабинет Маркета.
  isStockOpen.value = !isStockOpen.value
}

async function toggleOrders() {
  // Открывает историю из локального снимка и не запускает синхронизацию до явной команды оператора.
  isOrdersOpen.value = !isOrdersOpen.value
  if (isOrdersOpen.value) await props.loadYandexMarketOrders()
}

function resetOrdersPage() {
  // Возвращает на первую страницу после изменения поисковой строки.
  ordersPage.value = 1
}

function changeOrdersPage(delta) {
  // Переключает страницу уже отфильтрованной локальной истории.
  ordersPage.value = Math.min(ordersPageCount.value, Math.max(1, ordersPage.value + delta))
}

function formatOrderDate(value) {
  // Показывает дату единообразно с историей Ozon и не ломает таблицу пустым значением.
  const date = new Date(value || '')
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function marketStatusLabel(status) {
  // Переводит основные статусы Маркета в короткие подписи для оператора.
  return ({ PROCESSING: 'В обработке', DELIVERED: 'Доставлен', CANCELLED: 'Отменён', DELIVERY: 'В доставке', PICKUP: 'В пункте выдачи', UNPAID: 'Не оплачен', PENDING: 'Ожидает обработки' })[String(status || '').toUpperCase()] || status || '—'
}

function canStartProductionDelivery(order) {
  // Показывает явный запуск только для еще обрабатываемой позиции боевого заказа.
  return String(order?.status || '').toUpperCase() === 'PROCESSING' && Number(order?.order_id || 0) > 0 && Number(order?.item_id || 0) > 0
}

function isStartingProductionDelivery(order) {
  // Блокирует повторный клик по тому же заказу, пока сервер проводит выдачу.
  return Number(props.yandexMarketProductionStartDeliverySaving || 0) === Number(order?.order_id || 0)
}

function canRevealYandexMarketDigitalCodesForOrder(order) {
  // Показывает просмотр только владельцу и только после подтвержденной доставки позиции Маркета.
  return !props.yandexMarketSandboxMode
    && props.canRevealYandexMarketDigitalCodes
    && typeof props.revealYandexMarketProductionOrderCodes === 'function'
    && String(order?.status || '').toUpperCase() === 'DELIVERED'
    && Number(order?.order_id || 0) > 0
    && Number(order?.item_id || 0) > 0
}

async function openYandexMarketDigitalCodes(order) {
  // Запрашивает ключ только после клика, поэтому он не попадает в обычный список заказов.
  if (!canRevealYandexMarketDigitalCodesForOrder(order)) return
  showYandexMarketDigitalCodes.value = true
  yandexMarketDigitalCodesLoading.value = true
  yandexMarketDigitalCodesError.value = ''
  yandexMarketDigitalCodesOrder.value = order
  yandexMarketDigitalCodes.value = []
  const result = await props.revealYandexMarketProductionOrderCodes(order)
  if (result?.ok && Array.isArray(result.codes) && result.codes.length) yandexMarketDigitalCodes.value = result.codes
  else yandexMarketDigitalCodesError.value = result?.message || 'Ключ для этого заказа не найден'
  yandexMarketDigitalCodesLoading.value = false
}

function closeYandexMarketDigitalCodes() {
  // Очищает показанный ключ при закрытии, чтобы он не оставался в состоянии следующей карточки.
  showYandexMarketDigitalCodes.value = false
  yandexMarketDigitalCodesLoading.value = false
  yandexMarketDigitalCodesError.value = ''
  yandexMarketDigitalCodesOrder.value = null
  yandexMarketDigitalCodes.value = []
}

async function copyYandexMarketDigitalCodes() {
  // Копирует полный комплект ключей одной позиции для быстрой сверки с покупателем.
  const value = yandexMarketDigitalCodes.value.join('\n')
  if (!value) return
  try {
    await globalThis.navigator?.clipboard?.writeText(value)
  } catch {
    yandexMarketDigitalCodesError.value = 'Не удалось скопировать ключ'
  }
}

async function startProductionDelivery(order) {
  // Передает операторскую команду в родительскую логику, где есть подтверждение и обработка ошибки.
  await props.startYandexMarketProductionOrder(order)
}

const filteredOrders = computed(() => {
  // Ищет по номеру, SKU, статусу и дате без дополнительных запросов к Маркету.
  const query = orderQuery.value.toLocaleLowerCase('ru-RU')
  return props.yandexMarketOrders.filter((order) => !query || [order.order_id, order.offer_id, order.status, order.substatus, formatOrderDate(order.created_at)].join(' ').toLocaleLowerCase('ru-RU').includes(query))
})

const ordersPageCount = computed(() => Math.max(1, Math.ceil(filteredOrders.value.length / ORDERS_PAGE_SIZE)))
const visibleOrders = computed(() => filteredOrders.value.slice((ordersPage.value - 1) * ORDERS_PAGE_SIZE, ordersPage.value * ORDERS_PAGE_SIZE))
const ordersRange = computed(() => {
  // Сообщает границы текущей страницы, как в истории заказов Ozon.
  const total = filteredOrders.value.length
  if (!total) return 'Нет заказов'
  const from = (ordersPage.value - 1) * ORDERS_PAGE_SIZE + 1
  return `Показаны ${from}–${Math.min(total, from + ORDERS_PAGE_SIZE - 1)} из ${total}`
})

const detailFields = computed(() => {
  // Собирает только полезные поля из сохраненной карточки без показа технического ответа API.
  const item = props.yandexMarketCatalogDetails || {}
  return [
    ['Артикул продавца', item.market_sku],
    ['SKU', item.offer_id],
    ['Цена', item.price ? `${item.price} ${item.currency_code || '₽'}` : ''],
    ['Остаток', props.yandexMarketStockSettings.market_available_stock ?? ''],
  ].filter(([, value]) => String(value || '').trim())
    .map(([label, value]) => ({ label, value }))
})
</script>
