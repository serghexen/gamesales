<template>
  <section class="airpay-batch" :aria-busy="busy || blocked" aria-label="Результат покупки ваучеров Airpay">
    <header><h4>Покупка {{ current.quantity }} ключей</h4><p role="status">Оплачено: {{ current.paid_quantity }} из {{ current.quantity }} · Получено кодов: {{ current.received_quantity }}</p></header>
    <p>Общая сумма: {{ current.total_amount || '—' }} {{ current.currency }}</p>
    <p v-if="current.job" role="status">{{ current.job.state === 'queued' ? 'В очереди' : current.job.state === 'failed' ? 'Задание остановлено' : 'Выполняется' }} · Обработано позиций: {{ current.job.progress }}. Результат сохранится в истории.</p>
    <p v-if="current.last_job?.state === 'failed'" class="error" role="alert">{{ current.last_job.error }} Ошибка задания не отменяет сохранённые оплаты.</p>
    <p v-if="current.replaced" class="muted">Неоплаченный остаток перенесён в отдельную подготовку. Оплаченные ключи остаются в этой покупке.</p>
    <p v-if="current.state === 'processing'" class="muted">Есть незавершённая оплата. Следующие ключи не покупаем, пока её результат не подтверждён.</p>
    <p v-if="current.state === 'failed'" class="error">Покупка остановлена после отказа. Уже оплаченные ключи сохранены.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="airpay-batch__actions">
      <button class="ghost" type="button" :disabled="busy || blocked" @click="request('')">Обновить покупку</button>
      <button v-if="['checked', 'partial'].includes(current.state) && !current.replaced && !current.job" class="btn" type="button" :disabled="busy || blocked || !current.payments_enabled" @click="confirming = true">Продолжить покупку</button>
      <button v-if="current.items.some(item => item.state === 'paid' && !(item.pin_code || item.result_available))" class="btn" type="button" :disabled="busy || blocked || !!current.job || !current.payments_enabled" @click="request('vouchers')">Получить оплаченные ваучеры</button>
      <button v-if="current.paid_quantity < current.quantity && current.state !== 'processing' && !current.job" class="ghost" type="button" :disabled="busy || blocked" @click="request('renew')">{{ current.replaced ? 'Открыть подготовку остатка' : 'Проверить неоплаченный остаток' }}</button>
      <button v-if="current.state === 'prepared' && !current.replaced && !current.job" class="ghost" type="button" :disabled="busy || blocked" @click="request('check')">Повторить сохранённую проверку</button>
    </div>
    <p v-if="busy" role="status">Выполняем запрос…</p>
    <WorkAirpayTransaction v-for="item in current.items" :key="item.agent_transaction_id" :transaction="item" :token="token" :blocked="busy || blocked || !!current.job" @busy-change="setChildBusy" @updated="updateItem" />
    <WorkAirpayDialog v-if="confirming" title="Продолжить покупку" purchase :busy="busy" @close="confirming = false">
      <p>К покупке осталось: {{ current.quantity - current.paid_quantity }}. Уже оплаченные позиции повторно не покупаются.</p>
      <p>Общая сумма всех {{ current.quantity }} ключей: {{ current.total_amount }} {{ current.currency }}.</p>
      <p v-if="current.remaining_amount">Сейчас к оплате: {{ current.remaining_amount }} {{ current.currency }}.</p>
      <div class="airpay-batch__actions"><button class="ghost" type="button" :disabled="busy" @click="confirming = false">Отмена</button><button class="btn" type="button" :disabled="busy || blocked || !current.payments_enabled" @click="request('pay')">Купить оставшиеся</button></div>
    </WorkAirpayDialog>
  </section>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
import WorkAirpayTransaction from './WorkAirpayTransaction.vue'
import WorkAirpayDialog from './WorkAirpayDialog.vue'
import { resolveAirpayJob } from '../airpayJob'
const props = defineProps({ batch: { type: Object, required: true }, token: { type: String, default: '' }, blocked: { type: Boolean, default: false } })
const emit = defineEmits(['busy-change'])
const current = ref(props.batch)
const busy = ref(false)
const error = ref('')
const confirming = ref(false)
let version = 0
function setChildBusy(value) {
  // На время сверки отдельной операции запрещаем запуск остальной пачки.
  busy.value = value
  emit('busy-change', value)
}
function updateItem(item) {
  // Сохранённые коды показываем сразу; продолжение разрешается после чтения полного состояния сервера.
  const items = current.value.items.map(row => row.agent_transaction_id === item.agent_transaction_id ? item : row)
  current.value = { ...current.value, items, paid_quantity: items.filter(row => row.state === 'paid').length,
    received_quantity: items.filter(row => row.pin_code || row.result_available).length }
}
async function request(action) {
  // Потерянный ответ восстанавливается чтением БД; продолжение оплаты требует отдельного подтверждения.
  if (busy.value || props.blocked || (action && !['renew', 'check'].includes(action) && !current.value.payments_enabled) || (action && current.value.job)) return
  const revision = version
  busy.value = true
  emit('busy-change', true)
  error.value = ''
  try {
    const path = `/integrations/airpay/batches/${current.value.batch_id}`
    // При потере ответа продолжения сначала читаем журнал, не предлагаем оплатить повторно.
    if (action === 'pay') current.value = { ...current.value, state: 'processing' }
    let value = action ? await apiPost(`${path}/${action}`, action === 'pay' ? { confirmed_amount: current.value.total_amount } : {}, { token: props.token })
      : await apiGet(path, { token: props.token })
    const refreshingJob = !action && Boolean(value.job)
    value = await resolveAirpayJob(value, { token: props.token, active: () => revision === version,
      progress: job => { current.value = { ...current.value, job } } })
    if (refreshingJob) value = await apiGet(path, { token: props.token })
    if (action === 'renew') {
      // Продолжение создаёт проверку только оставшихся ключей и не начинает оплату.
      const renewed = value
      current.value = renewed.batch
      const checked = await resolveAirpayJob(await apiPost(`/integrations/airpay/batches/${renewed.batch.batch_id}/check`, {}, { token: props.token }),
        { token: props.token, active: () => revision === version, progress: job => { current.value = { ...current.value, job } } })
      error.value = checked.purchase_block_reason || (!checked.success ? checked.message || 'Проверка пока не завершена' : '')
      value = await apiGet(`/integrations/airpay/batches/${renewed.batch.batch_id}`, { token: props.token })
    }
    if (action === 'check') {
      error.value = value.purchase_block_reason || (!value.success ? value.message || 'Проверка пока не завершена' : '')
      value = await apiGet(path, { token: props.token })
    }
    if (revision === version) { current.value = value; confirming.value = false }
  } catch (err) {
    if (revision === version) { error.value = err?.message || 'Обновите сохранённый результат покупки'; confirming.value = false }
  } finally {
    if (revision === version) { busy.value = false; emit('busy-change', false) }
  }
}
watch(() => props.batch, value => {
  // Снимок первоначальной покупки заменяет временный статус ожидания.
  version += 1
  current.value = value
})
onBeforeUnmount(() => {
  // Поздний сетевой ответ не меняет закрытую форму.
  version += 1
  emit('busy-change', false)
})
</script>

<style scoped>
.airpay-batch { display: grid; gap: 16px; }
.airpay-batch h4, .airpay-batch p { margin: 0; }
.airpay-batch__actions { display: flex; flex-wrap: wrap; gap: 10px; }
</style>
