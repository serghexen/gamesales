<template>
  <section class="panel panel--wide interhub-catalog">
    <div class="panel__head interhub-catalog__head">
      <div>
        <p class="interhub-catalog__eyebrow">InterHub · агентский каталог</p>
        <h2 class="interhub-catalog__title">Платежи</h2>
      </div>
      <button class="deal-refresh-btn" type="button" :disabled="ctx.loading" aria-label="Обновить каталог InterHub" @click="ctx.reload">
        <span class="deal-refresh-btn__content">↻</span>
      </button>
    </div>

    <div class="panel__body">
      <p class="interhub-catalog__lead">Выберите услугу, проверьте реквизиты и сумму. Подтверждение оплаты доступно только владельцу.</p>
      <div class="interhub-catalog__balance"><span>Баланс InterHub</span><strong>{{ formatBalance(ctx.balance, ctx.currency) }}</strong><small>Агентский счёт</small></div>
      <p v-if="ctx.error" class="error">{{ ctx.error }}</p>

      <div class="interhub-catalog__toolbar">
        <label class="interhub-catalog__search">
          <span class="label">Поиск услуги</span>
          <input class="input" type="search" :value="ctx.search" placeholder="Название или категория" @input="ctx.setSearchFromEvent" />
        </label>
        <div class="interhub-catalog__stats" aria-label="Статистика каталога">
          <strong>{{ filteredServices.length }}</strong>
          <span>из {{ ctx.services.length }} услуг</span>
        </div>
      </div>

      <div class="table-wrap interhub-catalog__table-wrap">
        <table class="table table--compact">
          <thead>
            <tr>
              <th>Услуга</th>
              <th>Категория</th>
              <th>Тип</th>
              <th>Лимит</th>
              <th>Реквизиты</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="ctx.loading">
              <td colspan="5" class="muted">Загружаем каталог InterHub…</td>
            </tr>
            <tr v-else-if="!filteredServices.length">
              <td colspan="5" class="muted">Услуги по этому запросу не найдены.</td>
            </tr>
            <tr v-for="service in filteredServices" :key="service.service_id" class="interhub-catalog__row" :class="{ 'is-selected': selectedService?.service_id === service.service_id }" @click="selectService(service)">
              <td>
                <strong>{{ service.title }}</strong>
                <span class="interhub-catalog__id">#{{ service.service_id }}</span>
              </td>
              <td>{{ service.category || '—' }}</td>
              <td><span class="interhub-catalog__type">{{ formatType(service.type) }}</span></td>
              <td>{{ formatLimit(service) }}</td>
              <td>{{ formatFields(service.fields) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <form v-if="selectedService" class="interhub-catalog__form" @submit.prevent="checkPayment">
        <div><p class="interhub-catalog__eyebrow">Шаги оплаты</p><h3>{{ selectedService.title }}</h3></div>
        <label class="field"><span class="label">{{ accountLabel }}</span><input v-model.trim="account" class="input" :required="accountRequired" /><small v-if="!accountRequired" class="muted">Необязательно для этого типа услуги</small></label>
        <div v-if="amountFromNominal" class="interhub-catalog__auto-amount"><span>Сумма пополнения</span><strong>{{ selectedNominalTitle || 'Выберите номинал' }}</strong><small>Подставляется автоматически из номинала</small></div>
        <label v-else-if="needsAmount" class="field"><span class="label">Сумма пополнения</span><input v-model="amount" class="input" type="number" :min="selectedService.min_amount || 0.01" step="0.01" required /><small class="muted">Минимум: {{ selectedService.min_amount || '—' }}</small></label>
        <label v-for="field in selectedService.fields" :key="field.name" class="field"><span class="label">{{ field.name }}<i v-if="field.required"> *</i></span><select v-if="field.type === 'LIST'" v-model="params[field.name]" class="input" :required="field.required"><option value="">Выберите значение</option><option v-for="option in field.value_list" :key="option.id" :value="option.id">{{ option.title }}</option></select><input v-else v-model.trim="params[field.name]" class="input" :required="field.required" /></label>
        <div class="interhub-catalog__actions">
          <button v-if="supportsCalculate" class="btn" type="button" :disabled="ctx.calculationLoading" @click="calculate">{{ ctx.calculationLoading ? 'Узнаём…' : 'Узнать цену (calculate)' }}</button>
          <button class="btn" :disabled="ctx.checkLoading">{{ ctx.checkLoading ? 'Проверяем…' : 'Узнать остаток (check)' }}</button>
        </div>
        <div v-if="ctx.calculation" class="interhub-catalog__payment-result">
          <p class="interhub-catalog__result">{{ ctx.calculation.success ? 'Цена получена' : 'Цену получить не удалось' }} · {{ ctx.calculation.message || 'Ответ получен' }}</p>
          <p v-if="ctx.calculation.success && ctx.calculation.fixed_amount" class="muted">К списанию: {{ formatMoney(ctx.calculation.fixed_amount) }} ₽</p>
        </div>
        <div v-if="ctx.check" class="interhub-catalog__payment-result" :class="{ 'is-error': !ctx.check.success }">
          <p class="interhub-catalog__result">{{ ctx.check.success ? 'Проверка доступности пройдена' : 'Проверка доступности не пройдена' }} · {{ ctx.check.message || 'Ответ получен' }}</p>
          <small class="muted">Check не возвращает числовой остаток, а подтверждает возможность провести операцию.</small>
          <button v-if="ctx.check.success && ctx.canPay && !ctx.payment" class="btn" type="button" :disabled="ctx.paymentLoading" @click="ctx.pay">Оплатить</button>
          <p v-else-if="ctx.check.success && !ctx.canPay" class="muted">Оплатить может только владелец.</p>
        </div>
        <div v-if="ctx.payment" class="interhub-catalog__payment-result" :class="{ 'is-error': !ctx.payment.success }">
          <p class="interhub-catalog__result">{{ paymentMessage }}</p>
          <code v-if="giftCode" class="interhub-catalog__gift-code">{{ giftCode }}</code>
          <button v-if="isProcessing && ctx.canPay" class="btn" type="button" :disabled="ctx.paymentLoading" @click="ctx.refreshPaymentStatus">Обновить статус</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

// Контекст содержит каталог и действия загрузки, чтобы экран не знал деталей API.
const props = defineProps({
  ctx: { type: Object, required: true },
})

const filteredServices = computed(() => {
  // Фильтруем по названию и категории без повторного запроса к провайдеру.
  const query = String(props.ctx.search || '').trim().toLowerCase()
  const services = Array.isArray(props.ctx.services) ? props.ctx.services : []
  if (!query) return services
  return services.filter((service) => `${service?.title || ''} ${service?.category || ''}`.toLowerCase().includes(query))
})
const selectedService = ref(null)
const account = ref('')
const amount = ref('')
const params = reactive({})
const needsAmount = computed(() => ['TOP_UP'].includes(String(selectedService.value?.type || '').toUpperCase()))
const hasNominal = computed(() => Boolean(selectedService.value?.fields?.some((field) => field?.name === 'nominal')))
const amountFromNominal = computed(() => needsAmount.value && hasNominal.value)
const paymentType = computed(() => String(selectedService.value?.type || '').toUpperCase())
const supportsCalculate = computed(() => ['VOUCHER', 'PIN', 'TOP_UP_FIXED'].includes(paymentType.value))
const accountRequired = computed(() => false)
const accountLabel = computed(() => 'Аккаунт (временно необязательно)')
const selectedNominalTitle = computed(() => {
  // Находим подпись выбранного номинала, чтобы не заставлять оператора переносить сумму вручную.
  const nominal = selectedService.value?.fields?.find((field) => field?.name === 'nominal')
  return nominal?.value_list?.find((item) => String(item?.id) === String(params.nominal))?.title || ''
})
const giftCode = computed(() => String(props.ctx.payment?.params?.gift_code || ''))
const isProcessing = computed(() => Number(props.ctx.payment?.status) === 1)
const paymentMessage = computed(() => {
  // Переводим статусы провайдера в понятный оператору итог оплаты.
  if (isProcessing.value) return 'Платёж обрабатывается. Первая проверка статуса — через 1 минуту, затем по графику InterHub.'
  if (props.ctx.payment?.success) return giftCode.value ? 'Оплата успешна. Код ваучера:' : 'Оплата успешно подтверждена.'
  return `Оплата не прошла · ${props.ctx.payment?.message || 'Ответ InterHub не получен'}`
})

function selectService(service) {
  // Открываем форму выбранной услуги и очищаем реквизиты от предыдущей операции.
  selectedService.value = service
  account.value = ''
  amount.value = ''
  Object.keys(params).forEach((key) => delete params[key])
}

function buildPayload() {
  // Собираем одинаковые реквизиты для раздельных calculate и check без скрытых подстановок.
  const payload = { service_id: selectedService.value.service_id, account: account.value, params: { ...params }, flow_type: selectedService.value.type }
  if (amountFromNominal.value) {
    // Извлекаем числовое значение из подписи вида "TRY 250" для обязательного поля amount.
    const numeric = String(selectedNominalTitle.value).match(/[0-9]+(?:[.,][0-9]+)?/)
    payload.amount = Number(String(numeric?.[0] || '').replace(',', '.'))
  } else if (needsAmount.value) {
    // Передаем введенную сумму только для TOP_UP без фиксированного списка номиналов.
    payload.amount = Number(amount.value)
  }
  return payload
}

function calculate() {
  // Узнаём цену отдельно, чтобы владелец видел расчёт до проверки доступности.
  props.ctx.calculate(buildPayload())
}

function checkPayment() {
  // Проверяем доступность отдельным вызовом check и не запускаем оплату.
  props.ctx.checkPayment(buildPayload())
}

function formatType(type) {
  // Делаем технический тип платежа понятнее оператору, сохраняя исходный смысл.
  const labels = {
    TOP_UP: 'Пополнение',
    TOP_UP_FIXED: 'Фикс. номинал',
    VOUCHER: 'Ваучер',
    PIN: 'PIN-код',
  }
  return labels[String(type || '').toUpperCase()] || String(type || '—')
}

function formatLimit(service) {
  // Показываем диапазон только когда провайдер передал хотя бы один лимит.
  const min = Number(service?.min_amount || 0)
  const max = Number(service?.max_amount || 0)
  if (!min && !max) return '—'
  if (!max) return `от ${min}`
  if (!min) return `до ${max}`
  return `${min}–${max}`
}

function formatFields(fields) {
  // Кратко показываем обязательные реквизиты до открытия будущей формы оплаты.
  const items = Array.isArray(fields) ? fields : []
  if (!items.length) return 'Только аккаунт'
  return items.filter((field) => field?.required).map((field) => field.name).join(', ') || 'Дополнительные'
}

function formatBalance(value, currency) {
  // Разделяем тысячи и переводим валютный код в привычное для оператора обозначение.
  const amount = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value || 0)).replace(/\u00A0/g, ' ')
  const symbols = { RUB: '₽', TRY: '₺', USD: '$', EUR: '€' }
  return `${amount} ${symbols[currency] || currency || ''}`.trim()
}

function formatMoney(value) {
  // Показываем стоимость без потери копеек перед необратимым подтверждением оплаты.
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value || 0)).replace(/\u00A0/g, ' ')
}
</script>

<style scoped>
.interhub-catalog__head { align-items: end; border-bottom: 1px solid rgba(245, 158, 11, .32); }
.interhub-catalog__eyebrow { margin: 0 0 4px; color: #b86b12; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.interhub-catalog__title { margin: 0; letter-spacing: -.03em; }
.interhub-catalog__lead { max-width: 680px; margin: 0 0 20px; color: var(--muted, #7a766f); }
.interhub-catalog__balance { display: inline-grid; gap: 3px; margin: 0 0 18px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }.interhub-catalog__balance span, .interhub-catalog__balance small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__balance strong { font-size: 20px; }
.interhub-catalog__toolbar { display: flex; gap: 16px; align-items: end; justify-content: space-between; margin-bottom: 18px; }
.interhub-catalog__search { width: min(460px, 100%); }
.interhub-catalog__stats { display: grid; min-width: 120px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }
.interhub-catalog__stats strong { font-size: 20px; line-height: 1; }
.interhub-catalog__stats span, .interhub-catalog__id { color: var(--muted, #7a766f); font-size: 12px; }
.interhub-catalog__id { display: block; margin-top: 3px; font-family: ui-monospace, monospace; }
.interhub-catalog__type { display: inline-flex; padding: 3px 7px; border: 1px solid rgba(232, 134, 19, .35); color: #9b570d; font-size: 12px; font-weight: 700; }
.interhub-catalog__row { cursor: pointer; }.interhub-catalog__row.is-selected td { background: rgba(232, 134, 19, .08); }.interhub-catalog__form { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; align-items: end; margin-top: 22px; padding: 18px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); }.interhub-catalog__form h3 { margin: 0; }.interhub-catalog__actions { display: flex; flex-wrap: wrap; gap: 8px; }.interhub-catalog__result { margin: 0; font-weight: 700; }.interhub-catalog__payment-result { display: grid; gap: 8px; align-content: center; }.interhub-catalog__payment-result.is-error { color: #d45f5f; }.interhub-catalog__gift-code { width: fit-content; padding: 8px 10px; border: 1px dashed rgba(232, 134, 19, .7); background: rgba(232, 134, 19, .08); color: inherit; font-weight: 700; letter-spacing: .04em; }
.interhub-catalog__auto-amount { display: grid; gap: 3px; min-height: 42px; padding: 8px 10px; border: 1px solid rgba(232, 134, 19, .35); }.interhub-catalog__auto-amount span, .interhub-catalog__auto-amount small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__auto-amount strong { font-size: 18px; }
@media (max-width: 680px) { .interhub-catalog__toolbar { align-items: stretch; flex-direction: column; } .interhub-catalog__search { width: 100%; } .interhub-catalog__stats { width: fit-content; } }
</style>
