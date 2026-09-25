<template>
  <div class="airpay-check">
    <template v-if="result.scheme === 'contracts'">
      <label class="field"><span class="label">Договор, счёт или заказ</span><select v-model="contractIndex" class="input"><option value="">Выберите из ответа Airpay</option><option v-for="(contract, index) in result.contracts" :key="index" :value="String(index)">{{ contract.contractNumber || contract.contractId }} · {{ contract.name || 'Без названия' }}{{ contract.contractSum ? ` · ${contract.contractSum} ${currency}` : '' }}</option></select></label>
      <p v-if="!result.contracts.length" class="muted">Airpay не вернул доступных договоров.</p>
      <label v-if="selectedContract && !selectedContract.contractSum" class="field"><span class="label">Сумма по выбранному договору</span><input v-model="contractAmount" class="input" type="number" min="0.01" step="0.01" /></label>
    </template>

    <template v-if="result.scheme === 'invoice'">
      <label class="field"><span class="label">Квитанция</span><select v-model="invoiceIndex" class="input"><option value="">Выберите квитанцию</option><option v-for="(invoice, index) in invoices" :key="index" :value="String(index)">{{ invoice.invoiceId || 'Без номера' }} · {{ invoice.clientName || 'Без имени' }}</option></select></label>
      <p v-if="!invoices.length" class="muted">Airpay не вернул доступных квитанций.</p>
      <template v-if="selectedInvoice">
        <p v-if="selectedInvoice.clientAddress" class="muted">{{ selectedInvoice.clientAddress }}</p>
        <div v-for="(item, index) in selectedInvoice.services" :key="index" class="airpay-check__invoice-row">
          <label><input v-model="selectedRows" type="checkbox" :value="index" /> {{ item.subServiceName || item.subServiceId }}</label>
          <template v-if="selectedRows.includes(index)">
            <label class="field"><span class="label">Сумма</span><input v-model="amounts[index]" class="input" type="number" min="0.01" step="0.01" /></label>
            <label v-if="item.data?.isMeter" class="field"><span class="label">Показания · {{ item.data.si || 'ед.' }}</span><input v-model="readings[index]" class="input" type="number" :min="item.data.prevCount || 0" step="any" /><small class="muted">Предыдущие: {{ item.data.prevCount || '—' }}</small></label>
            <p v-if="item.data?.comment" class="muted">{{ item.data.comment }}</p>
          </template>
        </div>
      </template>
    </template>

    <p v-if="summaryError" class="muted">{{ summaryError }}</p>
    <button v-if="!confirmed" class="ghost" type="button" :disabled="Boolean(summaryError) || busy" @click="confirmed = true">Проверьте покупку</button>
    <WorkAirpayDialog v-if="confirmed" title="Проверьте покупку" :busy="busy" purchase @close="confirmed = false">
      <section class="airpay-check__confirmation" aria-label="Подтверждение покупки Airpay">
        <p class="airpay-check__service">{{ service.title }}</p>
        <dl class="airpay-check__details">
          <div v-if="(result.quantity || 1) > 1"><dt>Цена за ключ</dt><dd>{{ result.unit_amount ? money(airpayCents(result.unit_amount)) : 'Различается по ключам' }}</dd></div>
          <div><dt>{{ (result.quantity || 1) > 1 ? 'Итого к оплате' : 'Актуальная цена' }}</dt><dd>{{ totalCents ? money(totalCents) : 'Не получена' }}</dd></div>
          <div><dt>Аккаунт</dt><dd>{{ account }}</dd></div>
          <div v-if="selectedContract"><dt>Договор / счёт</dt><dd>{{ selectedContract.contractNumber || selectedContract.contractId }}</dd></div>
          <div v-if="selectedInvoice"><dt>Квитанция</dt><dd>{{ selectedInvoice.invoiceId }}</dd></div>
          <div v-for="(row, index) in invoiceSummary.rows || []" :key="index"><dt>{{ row.title }}</dt><dd>{{ money(row.cents) }}<small v-if="row.reading != null"> · показания {{ row.reading }}</small></dd></div>
          <div v-if="isVoucher"><dt>К покупке, шт.</dt><dd>{{ result.quantity || 1 }}</dd></div>
          <div v-if="isVoucher"><dt>Актуальный остаток, шт.</dt><dd>Поставщик не сообщает</dd></div>
          <div :class="{ 'is-error': !result.purchase_ready || summaryError }"><dt>Доступность</dt><dd>{{ summaryError || (result.purchase_ready ? 'Проверка пройдена, цена получена' : result.purchase_block_reason || 'Требуется подтверждение цены') }}</dd></div>
        </dl>
        <p v-if="isVoucher" class="airpay-check__hint">Выдача ваучера подтверждается при оплате.</p>
        <details class="airpay-check__extra">
          <summary>Данные проверки</summary>
          <dl class="airpay-check__details">
            <div><dt>Номер проверки</dt><dd>{{ result.agent_transaction_id }}</dd></div>
            <div v-if="result.transaction?.expires_at"><dt>Подготовка действует до</dt><dd>{{ new Date(result.transaction.expires_at).toLocaleString('ru-RU') }}</dd></div>
            <div v-if="result.currency_rate"><dt>Курс конвертации</dt><dd>{{ result.currency_rate }}</dd></div>
            <div v-if="result.final_amount"><dt>Зачисление в валюте поставщика</dt><dd>{{ result.final_amount }} {{ result.currency }}</dd></div>
            <div v-for="field in result.displays" :key="field.name"><dt>{{ field.title || field.name }}</dt><dd>{{ field.value }}</dd></div>
          </dl>
        </details>
        <p v-if="!result.payments_enabled" class="airpay-check__hint">Оплата и получение ваучера отключены в этом окружении.</p>
        <p v-else-if="result.purchase_ready" class="airpay-check__hint">Покупка спишет указанную сумму с депозита Airpay.</p>
        <div class="airpay-check__actions">
          <button class="ghost" type="button" :disabled="busy" @click="confirmed = false">Отмена</button>
          <button class="btn" type="button" :disabled="busy || Boolean(summaryError) || !result.payments_enabled || !result.purchase_ready" @click="confirmPurchase">{{ busy ? 'Покупаем…' : result.payments_enabled ? 'Купить' : 'Оплата отключена' }}</button>
        </div>
      </section>
    </WorkAirpayDialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import WorkAirpayDialog from './WorkAirpayDialog.vue'
import { airpayCents, invoiceSelection } from '../airpayCheckSummary'

const props = defineProps({ result: { type: Object, required: true }, service: { type: Object, required: true },
  account: { type: String, default: '' }, currency: { type: String, default: '' }, busy: { type: Boolean, default: false } })
const emit = defineEmits(['pay'])
const contractIndex = ref('')
const contractAmount = ref('')
const invoiceIndex = ref('')
const selectedRows = ref([])
const amounts = reactive({})
const readings = reactive({})
const confirmed = ref(false)
const isVoucher = computed(() => props.result.transaction?.purchase_kind === 'voucher' || props.service.fixed_payment === true)
const selectedContract = computed(() => contractIndex.value === '' ? null : props.result.contracts?.[Number(contractIndex.value)])
const invoices = computed(() => props.result.invoice?.invoices || [])
const selectedInvoice = computed(() => invoiceIndex.value === '' ? null : invoices.value[Number(invoiceIndex.value)])
const invoiceSummary = computed(() => invoiceSelection(selectedInvoice.value, selectedRows.value, amounts, readings))
const totalCents = computed(() => {
  // Разные схемы берут сумму из своих полей, без смешивания договора, номинала и квитанции.
  if (props.result.scheme === 'invoice') return invoiceSummary.value.cents
  if (props.result.scheme === 'contracts') return airpayCents(selectedContract.value?.contractSum || contractAmount.value)
  return airpayCents(props.result.purchase_amount || props.result.fixed_price || props.result.fixed_amount || props.result.amount_to)
})
const summaryError = computed(() => {
  // Не разрешаем оплату без выбранного объекта и известной положительной суммы.
  if (props.result.scheme === 'invoice') return invoiceSummary.value.error || ''
  if (props.result.scheme === 'contracts' && !selectedContract.value?.contractId) return 'Выберите договор или счёт.'
  if (!totalCents.value) return isVoucher.value ? 'Поставщик не вернул цену. Выполните новую проверку.' : 'Сумма не определена. Укажите её и выполните новую проверку.'
  return ''
})

function confirmPurchase() {
  // Открытие окна не запускает оплату: нужен отдельный клик и разрешение сервера.
  if (!props.busy && !summaryError.value && props.result.payments_enabled && props.result.purchase_ready) emit('pay')
}

watch(() => props.result, value => {
  // Обычная успешная проверка сразу открывает итог, как в Interhub; сложные схемы ждут выбора.
  confirmed.value = value.success && value.scheme === 'simple'
}, { immediate: true })

function money(cents) {
  // Закупочную цену подписываем валютой сохранённой проверки, даже если виджет баланса устарел.
  const currency = props.result.purchase_currency || props.currency
  return `${new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cents / 100)} ${currency || '(валюта не указана)'}`
}

watch(invoiceIndex, () => {
  // У каждой квитанции свой набор услуг, сумм и показаний; переносить их между квитанциями нельзя.
  selectedRows.value = []
  Object.keys(amounts).forEach(key => delete amounts[key])
  Object.keys(readings).forEach(key => delete readings[key])
  ;(selectedInvoice.value?.services || []).forEach((item, index) => { amounts[index] = String(item.data?.paySum ?? '') })
})
watch(contractIndex, () => {
  // Вручную введённая сумма предыдущего договора не должна применяться к новому договору.
  contractAmount.value = ''
})
watch([contractIndex, contractAmount, invoiceIndex, selectedRows, amounts, readings], () => {
  // Любая правка выбора закрывает прежнее подтверждение до повторного просмотра итогов.
  confirmed.value = false
}, { deep: true })
</script>

<style scoped src="../styles/work-supplier-catalog.css"></style>
<style scoped>
.airpay-check { display: grid; gap: 12px; margin-top: 16px; }
.airpay-check > button { justify-self: start; }
.airpay-check__confirmation { display: grid; gap: 14px; }
.airpay-check__service { margin: 0; color: #f4f7ff; font-weight: 700; }
.airpay-check__details { display: grid; gap: 8px; margin: 0; }
.airpay-check__details > div { display: grid; grid-template-columns: minmax(145px, .8fr) minmax(0, 1.2fr); gap: 14px; padding: 12px 14px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }
.airpay-check__details > div.is-error { border-left-color: #d45f5f; background: rgba(212, 95, 95, .1); }
.airpay-check__details dt { color: #b5bfd3; font-size: 12px; }
.airpay-check__details dd { margin: 0; color: #f4f7ff; font-weight: 700; text-align: right; overflow-wrap: anywhere; }
.airpay-check__details .is-error dd { color: #ffabab; }
.airpay-check__hint { margin: 0; color: #b5bfd3; font-size: 13px; line-height: 1.45; }
.airpay-check__extra summary { color: #b5bfd3; font-size: 13px; cursor: pointer; }
.airpay-check__extra[open] summary { margin-bottom: 10px; }
.airpay-check__actions { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding-top: 4px; }
.airpay-check__actions .btn, .airpay-check__actions .ghost { min-height: 42px; padding: 9px 16px; }
.airpay-check__invoice-row { display: grid; gap: 12px; padding: 12px; border: 1px solid var(--stroke); }
@media (max-width: 680px) {
  .airpay-check__details > div { grid-template-columns: 1fr; gap: 5px; }
  .airpay-check__details dd { text-align: left; }
  .airpay-check__actions { flex-wrap: wrap; }
}
</style>
