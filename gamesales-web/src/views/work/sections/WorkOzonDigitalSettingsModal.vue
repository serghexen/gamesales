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

            <section class="ozon-digital-modal__card">
              <div class="ozon-digital-modal__card-head">
                <div>
                  <span class="ozon-digital-modal__eyebrow">Поставщик ключей</span>
                  <strong>Interhub</strong>
                </div>
                <div class="ozon-digital-modal__auto-switch">
                  <span>Автовыдача</span>
                  <label class="switch">
                    <input v-model="autoIssueEnabled" type="checkbox" :disabled="!ozonDigitalSettings.interhub_service_id" />
                    <span class="slider">
                      <span class="circle">
                        <svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true"><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></svg>
                        <svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></svg>
                      </span>
                    </span>
                  </label>
                </div>
              </div>

              <div class="ozon-digital-modal__supplier">
                <div class="ozon-digital-modal__supplier-fields">
                  <label class="field">
                    <span>Услуга Interhub</span>
                    <select v-model="ozonDigitalSettings.interhub_service_id" class="input" :disabled="interhubServicesLoading">
                      <option :value="null">{{ interhubServicesLoading ? 'Загружаем услуги…' : 'Не выбрана' }}</option>
                      <option v-for="service in interhubServices" :key="service.service_id" :value="Number(service.service_id)">
                        {{ service.title }}{{ service.category ? ` · ${service.category}` : '' }}
                      </option>
                    </select>
                  </label>
                  <label v-if="interhubNominals.length" class="field">
                    <span>Номинал</span>
                    <select v-model="ozonDigitalSettings.interhub_nominal_id" class="input">
                      <option value="">Выберите номинал</option>
                      <option v-for="nominal in interhubNominals" :key="nominal.value" :value="nominal.value">{{ nominal.label }}</option>
                    </select>
                  </label>
                </div>
              </div>
            </section>

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
                  <span class="ozon-digital-order__status ozon-digital-order__status--manual_required">Нужен ключ</span>
                </div>
                <p v-if="order.waiting_deadline_at" class="muted">Код ожидается до: {{ formatOzonDate(order.waiting_deadline_at) }}</p>
                <p v-if="order.last_error" class="bad">{{ order.last_error }}</p>
                <div class="ozon-digital-order__delivery">
                  <label class="field">
                    <span>Ключ{{ order.required_qty > 1 ? `и — по одному в строке (${order.required_qty})` : '' }}</span>
                    <textarea v-model="deliveryDrafts[order.id]" class="input textarea" rows="2" placeholder="Вставьте ключ для покупателя"></textarea>
                  </label>
                  <button class="btn btn--primary" type="button" :disabled="deliveryBusy[order.id]" @click="submitDelivery(order)">
                    {{ deliveryBusy[order.id] ? 'Отправляем…' : 'Отправить ключ' }}
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
import { computed, reactive } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

const props = defineProps({
  showOzonDigitalSettings: { type: Boolean, required: true },
  closeOzonDigitalSettings: { type: Function, required: true },
  ozonDigitalSettings: { type: Object, required: true },
  ozonDigitalSettingsLoading: { type: Boolean, required: true },
  ozonDigitalSettingsSaving: { type: Boolean, required: true },
  ozonDigitalSettingsError: { type: String, default: '' },
  ozonDigitalSettingsOk: { type: String, default: '' },
  ozonDigitalOrders: { type: Array, default: () => [] },
  interhubServices: { type: Array, default: () => [] },
  interhubServicesLoading: { type: Boolean, default: false },
  saveOzonDigitalSettings: { type: Function, required: true },
  deliverOzonDigitalOrder: { type: Function, required: true },
})
const deliveryDrafts = reactive({})
const deliveryBusy = reactive({})

const isOzonDigitalBusy = computed(() => Boolean(
  props.ozonDigitalSettingsLoading
  || props.ozonDigitalSettingsSaving
  || Object.values(deliveryBusy).some(Boolean),
))

const ozonDigitalBusyLabel = computed(() => {
  // Объясняет текущую операцию, пока хомяк блокирует повторные действия в модалке.
  if (props.ozonDigitalSettingsSaving) return 'Сохраняем настройки и отправляем остаток…'
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
