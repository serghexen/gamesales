<template>
  <section class="airpay-preparation" :aria-busy="busy" aria-label="Подготовка покупки Airpay">
    <div v-if="busy && !purchaseLocked" class="airpay-preparation__overlay" role="status"><WorkHamsterLoader label="Узнаём цену и проверяем реквизиты…" /></div>
    <p v-if="loading" class="muted" role="status">Получаем актуальные поля услуги…</p>
    <template v-else-if="service">
      <form v-if="!purchaseLocked" class="airpay-preparation__form" @submit.prevent="check">
        <div class="airpay-preparation__summary"><p class="supplier-catalog__eyebrow">Получение</p><h3>{{ service.title }}</h3></div>
        <div class="airpay-preparation__fields">
          <div class="field"><span class="label">Результат покупки</span><strong>{{ purchaseKind === 'voucher' ? 'Код ваучера' : purchaseKind === 'topup' ? 'Пополнение аккаунта' : 'Тип услуги не определён' }}</strong><small class="muted">{{ purchaseKind === 'voucher' ? 'Фиксированная сумма. Закупочную цену получим при проверке.' : purchaseKind === 'topup' ? 'Произвольная сумма. Укажите сумму к зачислению.' : 'Airpay не указал вид суммы платежа. Проверка пока недоступна.' }}</small></div>
          <label v-for="field in inputs" :key="field.name" class="field"><span class="label">{{ field.title || field.name }}{{ field.required || field.name === 'account' ? ' *' : '' }}</span><input v-model="fields[field.name]" class="input" :required="field.required || field.name === 'account'" :disabled="busy || !canPrepare" maxlength="512" autocomplete="off" @input="invalidate" /></label>
          <label v-if="purchaseKind === 'voucher'" class="field"><span class="label">Количество ключей</span><input v-model="quantity" class="input" aria-label="Количество ключей" type="number" min="1" max="20" step="1" required :disabled="busy || !canPrepare" @input="invalidate" /><small class="muted">Не более 20 за один запуск. Каждый ключ покупается и сохраняется отдельно.</small></label>
          <label v-if="purchaseKind === 'topup'" class="field"><span class="label">Сумма к зачислению *</span><input v-model="amountTo" class="input" type="number" min="0.01" max="999999999.99" step="0.01" required :disabled="busy || !canPrepare" placeholder="Введите сумму" @input="invalidate" /></label>
        </div>
        <div class="airpay-preparation__actions">
          <button class="btn airpay-preparation__action-btn" type="submit" :disabled="busy || !canPrepare || !purchaseKind || retrySeconds > 0 || (result && !result.retryable)"><span><strong>{{ busy ? 'Проверяем…' : retrySeconds ? `Повтор через ${retrySeconds} с` : draft && (!result || result.retryable) ? 'Повторить проверку' : 'Получить' }}</strong><small>Цена и проверка доступности</small></span></button>
          <button v-if="result && !result.retryable" class="ghost" type="button" :disabled="busy" @click="invalidate">Новая проверка</button>
          <small class="muted">Проверка без оплаты. Списание — только после подтверждения покупки.</small>
        </div>
        <p v-if="!canPrepare" class="airpay-preparation__owner-note muted">Проверять реквизиты может только владелец.</p>
      </form>
      <p v-if="result" :class="result.success ? 'airpay-preparation__success' : 'error'" role="status">{{ result.success ? 'Проверка пройдена' : result.retryable ? 'Проверка ожидает повторения' : 'Проверка отклонена' }} · {{ result.message || `Код ${result.result}` }}</p>
      <WorkAirpayCheckResult v-if="result?.success && !purchaseLocked" :result="result" :service="service" :account="fields.account" :currency="result.purchase_currency || currency" :busy="busy" @pay="pay" />
      <WorkAirpayBatch v-if="batch" :batch="batch" :token="token" :blocked="busy" @busy-change="setTransactionBusy" />
      <WorkAirpayTransaction v-if="transaction" :transaction="transaction" :token="token" :blocked="busy" @busy-change="setTransactionBusy" @updated="acceptTransaction" />
    </template>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button v-if="!loading && !service" class="ghost" type="button" @click="loadService">Повторить загрузку параметров</button>
  </section>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { useAirpayPreparation } from '../useAirpayPreparation'
import WorkHamsterLoader from './WorkHamsterLoader.vue'
import WorkAirpayCheckResult from './WorkAirpayCheckResult.vue'
import WorkAirpayBatch from './WorkAirpayBatch.vue'
import WorkAirpayTransaction from './WorkAirpayTransaction.vue'

const props = defineProps({ serviceId: { type: String, required: true }, token: { type: String, default: '' },
  canPrepare: { type: Boolean, default: false }, currency: { type: String, default: '' } })
const emit = defineEmits(['busy-change'])
const { service, fields, inputs, amountTo, quantity, batch, loading, busy, error, result,
  draft, retrySeconds, invalidate, loadService, check, purchaseKind, transaction, purchaseLocked, pay, acceptTransaction } = useAirpayPreparation(props)
function setTransactionBusy(value) {
  // Сверка и получение кода удерживают выбранную услугу, пока запрос покупки не завершён.
  busy.value = value
}
watch(busy, value => {
  // Пока выполняется check, родитель блокирует обновление каталога и смену поставщика.
  emit('busy-change', value)
})
onBeforeUnmount(() => {
  // Закрытая форма больше не удерживает блокировку родительского экрана.
  emit('busy-change', false)
})
</script>

<style scoped src="../styles/work-supplier-catalog.css"></style>
<style scoped>
.airpay-preparation { position: relative; min-width: 0; }
.airpay-preparation__overlay { position: absolute; z-index: 3; inset: 0; display: grid; place-items: center; padding: 24px; background: rgba(9, 18, 27, .78); backdrop-filter: blur(2px); }
.airpay-preparation__form { display: grid; grid-template-columns: minmax(220px, .8fr) minmax(0, 1fr) minmax(220px, .72fr); gap: 16px 18px; align-items: start; }
.airpay-preparation__summary { align-self: center; padding-right: 12px; }
.airpay-preparation__summary h3 { margin: 0; }
.airpay-preparation__fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px 18px; min-width: 0; }
.airpay-preparation__actions { display: grid; width: 100%; max-width: 300px; min-width: 0; gap: 10px; justify-self: start; margin-top: 35px; }
.airpay-preparation__action-btn { display: flex; min-width: 0; min-height: 58px; align-items: center; justify-content: flex-start; padding: 8px 11px; text-align: left; }
.airpay-preparation__action-btn > span { display: grid; gap: 1px; min-width: 0; }
.airpay-preparation__action-btn strong { font-size: 14px; line-height: 1.08; }
.airpay-preparation__action-btn small { color: rgba(9, 18, 27, .68); font-size: 10px; font-weight: 700; letter-spacing: .05em; }
.airpay-preparation__owner-note { grid-column: 1 / -1; margin: 0; }
.airpay-preparation__success { color: #62e4c0; }
@media (max-width: 1120px) {
  .airpay-preparation__form { grid-template-columns: minmax(220px, .8fr) minmax(0, 1fr); }
  .airpay-preparation__fields, .airpay-preparation__actions { grid-column: 2; }
  .airpay-preparation__actions { margin-top: 0; }
}
@media (max-width: 680px) {
  .airpay-preparation__form { grid-template-columns: 1fr; }
  .airpay-preparation__fields, .airpay-preparation__actions { grid-column: auto; grid-template-columns: 1fr; }
}
</style>
