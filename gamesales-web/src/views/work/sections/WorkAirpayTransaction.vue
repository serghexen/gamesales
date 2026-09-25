<template>
  <article class="airpay-transaction" :aria-busy="busy">
    <header><strong>{{ current.service_title }}</strong><span>{{ stateLabel }}</span></header>
    <p v-if="current.batch" class="muted">Ключ {{ current.batch.index + 1 }} из {{ current.batch.quantity }}</p>
    <dl>
      <div><dt>Операция</dt><dd>{{ current.agent_transaction_id }}</dd></div>
      <div><dt>Аккаунт</dt><dd>{{ current.account }}</dd></div>
      <div><dt>Закупочная сумма</dt><dd>{{ current.amount || '—' }} {{ current.currency }}</dd></div>
      <div><dt>Создана</dt><dd>{{ dateLabel(current.created_at) }}</dd></div>
      <div v-if="current.provider_transaction_id"><dt>Номер Airpay</dt><dd>{{ current.provider_transaction_id }}</dd></div>
    </dl>
    <p role="status">{{ current.provider_message }}</p>
    <div v-if="current.pin_code" class="airpay-transaction__code"><span>Код ваучера</span><code>{{ current.pin_code }}</code><button class="ghost" type="button" @click="copyCode">{{ copied ? 'Скопировано' : 'Копировать' }}</button></div>
    <p v-if="current.state === 'processing'" class="muted">«Обновить результат» читает сохранённое состояние. «Уточнить результат оплаты» повторно отправляет в Airpay сохранённый запрос оплаты с тем же номером и реквизитами. Не создавайте новую покупку взамен этой.</p>
    <p v-if="current.state === 'paid' && current.purchase_kind === 'voucher' && !(current.pin_code || current.result_available)" class="muted">Оплата завершена. Осталось получить код; повторная оплата не нужна.</p>
    <p v-if="current.next_attempt_at" class="muted">Следующий запрос поставщику — после {{ dateLabel(current.next_attempt_at) }}.</p>
    <p v-if="!current.payments_enabled" class="muted">Оплата и получение кода отключены в этом окружении. Сохранённые результаты доступны.</p>
    <p v-if="current.requires_attention" class="error" role="status">Требуется ручной разбор: лимит запросов исчерпан. Сверьте результат с Airpay.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="airpay-transaction__actions">
      <button class="ghost" type="button" :disabled="busy || reviewBusy || blocked" @click="request('')">Обновить результат</button>
      <button v-if="current.state === 'processing'" class="btn" type="button" :disabled="busy || reviewBusy || blocked || !current.payments_enabled || current.requires_attention" @click="request('reconcile')">Уточнить результат оплаты</button>
      <button v-if="current.state === 'paid' && current.purchase_kind === 'voucher' && !(current.pin_code || current.result_available)" class="btn" type="button" :disabled="busy || reviewBusy || blocked || !current.payments_enabled || current.requires_attention" @click="request('voucher')">Получить ваучер</button>
      <button v-if="current.result_available && !current.pin_code" class="ghost" type="button" :disabled="busy || reviewBusy || blocked" @click="request('result')">Показать сохранённый код</button>
    </div>
    <WorkAirpayReview :transaction="current" :token="token" :blocked="busy || blocked" :archive="archive" @busy-change="reviewChanged" @resolved="resolved" @refresh="request('')" />
  </article>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
import WorkAirpayReview from './WorkAirpayReview.vue'
const props = defineProps({ transaction: { type: Object, required: true }, token: { type: String, default: '' }, blocked: { type: Boolean, default: false }, archive: { type: Boolean, default: false } })
const emit = defineEmits(['busy-change', 'updated'])
const current = ref(props.transaction)
const busy = ref(false)
const reviewBusy = ref(false)
const error = ref('')
const copied = ref(false)
let version = 0
const stateLabel = computed(() => ({ prepared: 'Подготовлена', checking: 'Проверяется', check_pending: 'Ожидает проверки',
  check_failed: 'Проверка отклонена', checked: 'Проверена, не оплачена', processing: 'Оплата в обработке',
  paid: current.value.purchase_kind === 'voucher' && !(current.value.pin_code || current.value.result_available) ? 'Оплачено · ожидается код' : 'Выполнено', failed: 'Оплата отклонена' }[current.value.state] || 'Статус неизвестен'))
function dateLabel(value) {
  // Даты журнала показываем в часовом поясе пользователя, сохраняя исходное значение на сервере.
  return value ? new Date(value).toLocaleString('ru-RU') : '—'
}
async function request(action) {
  // Обновление читает только БД; сетевые шаги выполняются отдельно и только по явной кнопке.
  if (busy.value || reviewBusy.value || props.blocked || (action && action !== 'result' && (!current.value.payments_enabled || current.value.requires_attention))) return
  const revision = version
  busy.value = true
  emit('busy-change', true)
  error.value = ''
  try {
    const path = `/integrations/airpay/${props.archive ? 'legacy/' : ''}transactions/${current.value.agent_transaction_id}`
    const response = action ? await apiPost(`${path}/${action}`, {}, { token: props.token }) : await apiGet(path, { token: props.token })
    if (revision !== version) return
    current.value = action === 'result' ? { ...current.value, pin_code: response.value } : response
    emit('updated', current.value)
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось обновить операцию Airpay'
  } finally {
    if (revision === version) { busy.value = false; emit('busy-change', false) }
  }
}
function reviewChanged(value) {
  // Разбор блокирует соседние действия карточки и родительскую пачку.
  reviewBusy.value = value
  emit('busy-change', busy.value || value)
}
function resolved(value) {
  // Подтверждённое решение обновляет карточку без отдельного запроса поставщику.
  current.value = value
  emit('updated', value)
}
async function copyCode() {
  // Код копируется только по нажатию пользователя, без фонового обращения к буферу обмена.
  try { await navigator.clipboard.writeText(current.value.pin_code); copied.value = true }
  catch { error.value = 'Не удалось скопировать код. Выделите его вручную.' }
}
watch(() => props.transaction, value => {
  // Новый снимок родителя заменяет прежний статус и сбрасывает уведомление о копировании.
  version += 1
  current.value = value
  copied.value = false
})
onBeforeUnmount(() => {
  // Поздний ответ закрытой истории не обновляет другую операцию.
  version += 1
  emit('busy-change', false)
})
</script>

<style scoped>
.airpay-transaction { padding: 18px; border: 1px solid var(--stroke); border-left: 3px solid #e88613; border-radius: 12px; }
.airpay-transaction header, .airpay-transaction dl > div { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.airpay-transaction header span { color: #f6c66e; }
.airpay-transaction dl { display: grid; gap: 10px; font-size: 13px; }
.airpay-transaction dt { color: var(--muted); }
.airpay-transaction dd { margin: 0; overflow-wrap: anywhere; }
.airpay-transaction__actions { display: flex; flex-wrap: wrap; gap: 10px; }
.airpay-transaction__code { display: grid; gap: 10px; padding: 16px; background: rgba(232,134,19,.08); }
.airpay-transaction__code code { user-select: all; overflow-wrap: anywhere; font-size: 16px; }
.airpay-transaction__code button { justify-self: start; }
</style>
