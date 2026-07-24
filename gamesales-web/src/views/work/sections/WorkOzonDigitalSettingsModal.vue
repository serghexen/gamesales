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
            <p class="muted ozon-catalog-modal__hint">Сначала ручная выдача: ключ отправляется только после вашего подтверждения.</p>
          </div>
          <div class="toolbar-actions">
            <button class="ghost" type="button" @click="closeOzonDigitalSettings">К карточке</button>
            <button class="btn btn--icon-plain" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonDigitalSettings">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg>
            </button>
          </div>
        </div>
        <div class="modal__body">
          <p v-if="ozonDigitalSettingsLoading" class="muted">Загружаем настройки ручной выдачи…</p>
          <template v-else>
            <p v-if="ozonDigitalSettingsError" class="bad">{{ ozonDigitalSettingsError }}</p>
            <p v-if="ozonDigitalSettingsOk" class="good">{{ ozonDigitalSettingsOk }}</p>

            <section class="ozon-digital-modal__card">
              <div class="ozon-digital-modal__card-head">
                <div>
                  <span class="ozon-digital-modal__eyebrow">Настройка выдачи</span>
                  <strong>{{ automaticSupplierEnabled ? 'Interhub выдаёт ключ автоматически' : 'Ручная выдача — резервный режим' }}</strong>
                </div>
                <span class="ozon-digital-modal__mode">{{ automaticSupplierEnabled ? 'Поставщик №1' : 'Без автоотправки' }}</span>
              </div>

              <div class="ozon-digital-modal__setup">
                <div class="ozon-digital-modal__limit">
                  <label class="field">
                    <span>Остаток для Ozon</span>
                    <input v-model.number="ozonDigitalSettings.manual_stock_limit" class="input" type="number" min="0" max="100000" step="1" />
                  </label>
                  <p class="muted">Сколько укажете, столько отправим в Ozon. Меняется только после нового сохранения.</p>
                  <p class="ozon-digital-modal__offer">Артикул: <strong>{{ ozonDigitalSettings.offer_id || '—' }}</strong></p>
                </div>
                <div class="ozon-digital-modal__supplier">
                  <div class="ozon-digital-modal__supplier-title">
                    <span>Поставщик ключей</span>
                    <small>Приоритет №1</small>
                  </div>
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
                  <label class="ozon-digital-modal__check">
                    <input v-model="ozonDigitalSettings.interhub_enabled" type="checkbox" :disabled="!ozonDigitalSettings.interhub_service_id" />
                    <span>Пробовать Interhub первым</span>
                  </label>
                  <label class="ozon-digital-modal__check">
                    <input v-model="ozonDigitalSettings.auto_issue_enabled" type="checkbox" :disabled="!ozonDigitalSettings.interhub_enabled" />
                    <span>Выдавать автоматически</span>
                  </label>
                  <p class="muted">Если ключа нет или нет баланса, заказ останется для ручной выдачи.</p>
                </div>
                <div class="ozon-digital-modal__messages">
                  <label class="field">
                    <span>Инструкция покупателю</span>
                    <textarea v-model="ozonDigitalSettings.activation_instruction" class="input textarea" rows="2" placeholder="Например: активируйте ключ в PlayStation Store."></textarea>
                  </label>
                  <label class="field">
                    <span>Сообщение при проблеме</span>
                    <textarea v-model="ozonDigitalSettings.support_error_message" class="input textarea" rows="2" placeholder="Произошла ошибка, обратитесь в поддержку."></textarea>
                  </label>
                </div>
              </div>
              <div class="ozon-digital-modal__footer">
                <span class="muted">Сохраняйте, когда хотите вручную изменить остаток в Ozon.</span>
                <button class="btn btn--primary" type="button" :disabled="ozonDigitalSettingsSaving" @click="saveOzonDigitalSettings">
                  {{ ozonDigitalSettingsSaving ? 'Публикуем…' : 'Сохранить и отправить остаток' }}
                </button>
              </div>

              <section class="ozon-digital-modal__stats" aria-label="Статистика ключей Ozon">
                <div><span>Отправлено в Ozon</span><strong>{{ ozonDigitalSettings.published_stock }}</strong></div>
                <div><span>Текущий остаток</span><strong>{{ ozonDigitalSettings.available_stock }}</strong></div>
                <div><span>Требуют выдачи</span><strong>{{ ozonDigitalSettings.pending_orders }}</strong></div>
                <div><span>Выдано</span><strong>{{ ozonDigitalSettings.delivered_orders }}</strong></div>
              </section>
            </section>

            <section class="ozon-digital-modal__orders">
              <div class="ozon-digital-modal__orders-head">
                <div>
                  <h4>Заказы на выдачу</h4>
                  <p class="muted">Заказы Ozon резервирует сам; остаток меняется только вручную выше.</p>
                </div>
                <button class="ghost" type="button" :disabled="ozonDigitalOrdersSyncing" @click="syncOzonDigitalOrders">
                  {{ ozonDigitalOrdersSyncing ? 'Проверяем…' : 'Проверить Ozon' }}
                </button>
              </div>

              <p v-if="!ozonDigitalOrders.length" class="ozon-digital-modal__empty muted">Заказов на ручную выдачу пока нет.</p>
              <article v-for="order in ozonDigitalOrders" :key="order.id" class="ozon-digital-order">
                <div class="ozon-digital-order__head">
                  <div>
                    <strong>{{ order.product_name || 'Цифровой товар' }}</strong>
                    <p>Отправление {{ order.posting_number }} · SKU {{ order.sku }}</p>
                  </div>
                  <span :class="['ozon-digital-order__status', `ozon-digital-order__status--${order.status}`]">{{ orderStatusLabel(order.status) }}</span>
                </div>
                <p v-if="order.waiting_deadline_at" class="muted">Код ожидается до: {{ formatOzonDate(order.waiting_deadline_at) }}</p>
                <p v-if="order.last_error" class="bad">{{ order.last_error }}</p>
                <div v-if="order.status === 'manual_required'" class="ozon-digital-order__delivery">
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

const props = defineProps({
  showOzonDigitalSettings: { type: Boolean, required: true },
  closeOzonDigitalSettings: { type: Function, required: true },
  ozonDigitalSettings: { type: Object, required: true },
  ozonDigitalSettingsLoading: { type: Boolean, required: true },
  ozonDigitalSettingsSaving: { type: Boolean, required: true },
  ozonDigitalOrdersSyncing: { type: Boolean, required: true },
  ozonDigitalSettingsError: { type: String, default: '' },
  ozonDigitalSettingsOk: { type: String, default: '' },
  ozonDigitalOrders: { type: Array, default: () => [] },
  interhubServices: { type: Array, default: () => [] },
  interhubServicesLoading: { type: Boolean, default: false },
  saveOzonDigitalSettings: { type: Function, required: true },
  syncOzonDigitalOrders: { type: Function, required: true },
  deliverOzonDigitalOrder: { type: Function, required: true },
})
const deliveryDrafts = reactive({})
const deliveryBusy = reactive({})

const automaticSupplierEnabled = computed(() => Boolean(
  props.ozonDigitalSettings.interhub_enabled && props.ozonDigitalSettings.auto_issue_enabled && props.ozonDigitalSettings.interhub_service_id,
))

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

function orderStatusLabel(status) {
  // Переводит технический статус в короткую подсказку для ручной обработки заказа.
  return {
    manual_required: 'Нужен ключ',
    delivering: 'Отправляем',
    delivered: 'Выдан',
    supplier_processing: 'Interhub обрабатывает',
    cancelled: 'Отменён',
  }[status] || status
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
