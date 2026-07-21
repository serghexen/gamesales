<template>
  <section class="panel panel--wide interhub-catalog">
    <div class="panel__head interhub-catalog__head">
      <div>
        <p class="interhub-catalog__eyebrow">InterHub · агентский каталог</p>
        <h2 class="interhub-catalog__title">Платежи</h2>
      </div>
      <div class="interhub-catalog__head-actions">
        <button v-if="ctx.canManagePrices" class="ghost interhub-catalog__price-action" type="button" :disabled="ctx.priceRefreshLoading" @click="ctx.refreshPrices">
          {{ ctx.priceRefreshLoading ? 'Обновляем цены…' : 'Обновить закупочные цены' }}
        </button>
        <button v-if="ctx.canManagePrices" class="ghost interhub-catalog__price-action" type="button" :disabled="ctx.priceRefreshLoading" @click="ctx.exportPrices">Выгрузить Excel</button>
        <button class="deal-refresh-btn" type="button" :disabled="ctx.loading" aria-label="Обновить каталог InterHub" @click="ctx.reload">
          <span class="deal-refresh-btn__content">↻</span>
        </button>
      </div>
    </div>

      <div class="panel__body">
      <p class="interhub-catalog__lead">Выберите услугу, проверьте реквизиты и сумму. Подтверждение оплаты доступно только владельцу.</p>
      <div class="interhub-catalog__balance"><span>Баланс InterHub</span><strong>{{ formatBalance(ctx.balance, ctx.currency) }}</strong><small>Агентский счёт</small></div>
      <p v-if="ctx.error" class="error">{{ ctx.error }}</p>
      <p v-if="ctx.priceError" class="error">{{ ctx.priceError }}</p>
      <p v-if="ctx.priceRefresh" class="muted interhub-catalog__price-progress">Обновление цен: {{ ctx.priceRefresh.processed }} из {{ ctx.priceRefresh.total }} · успешно {{ ctx.priceRefresh.successes }} · ошибок {{ ctx.priceRefresh.errors }}<span v-if="ctx.priceRefresh.message"> · {{ ctx.priceRefresh.message }}</span></p>

      <div class="interhub-catalog__toolbar">
        <label class="interhub-catalog__search">
          <span class="label">Поиск услуги</span>
          <input class="input" type="search" :value="ctx.search" placeholder="Название или категория" @input="ctx.setSearchFromEvent" />
        </label>
        <button class="ghost interhub-catalog__sort" type="button" @click="toggleServicesSort">По названию: {{ servicesSortDirection === 'asc' ? 'А–Я' : 'Я–А' }}</button>
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
            </tr>
          </thead>
          <tbody>
            <tr v-if="ctx.loading">
              <td colspan="3" class="muted">Загружаем каталог InterHub…</td>
            </tr>
            <tr v-else-if="!filteredServices.length">
              <td colspan="3" class="muted">Услуги по этому запросу не найдены.</td>
            </tr>
            <tr v-for="service in pagedServices" :key="service.service_id" class="interhub-catalog__row" :class="{ 'is-selected': selectedService?.service_id === service.service_id }" @click="selectService(service)">
              <td>
                <strong>{{ service.title }}</strong>
                <span class="interhub-catalog__id">#{{ service.service_id }}</span>
              </td>
              <td>{{ service.category || '—' }}</td>
              <td><span class="interhub-catalog__type">{{ formatType(service.type) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav v-if="totalPages > 1" class="interhub-catalog__pagination" aria-label="Страницы каталога InterHub">
        <button class="ghost" type="button" :disabled="currentPage === 1" aria-label="Предыдущая страница" @click="changePage(-1)">Назад</button>
        <span>Страница {{ currentPage }} из {{ totalPages }}</span>
        <button class="ghost" type="button" :disabled="currentPage === totalPages" aria-label="Следующая страница" @click="changePage(1)">Далее</button>
      </nav>
      <form v-if="selectedService" ref="paymentForm" class="interhub-catalog__form" @submit.prevent="checkPayment">
        <div class="interhub-catalog__service-summary"><p class="interhub-catalog__eyebrow">Шаги оплаты</p><h3>{{ selectedService.title }}</h3></div>
        <label v-if="showAccount" class="field"><span class="label">{{ accountLabel }}<i v-if="accountRequired"> *</i></span><input v-model.trim="account" class="input" :required="accountRequired" @input="resetPaymentAfterInputChange" /><small v-if="!accountRequired" class="muted">Необязательно для этого типа услуги</small></label>
        <div v-if="amountFromNominal" class="interhub-catalog__auto-amount"><span>Сумма пополнения</span><strong>{{ selectedNominalTitle || 'Выберите номинал' }}</strong><small>Подставляется автоматически из номинала</small></div>
        <label v-else-if="needsAmount" class="field"><span class="label">Сумма пополнения</span><input v-model="amount" class="input" type="number" :min="selectedService.min_amount || 0.01" step="0.01" required @input="resetPaymentAfterInputChange" /><small class="muted">{{ formatAmountLimit(selectedService) }}</small></label>
        <label v-for="field in selectedService.fields" :key="field.name" class="field"><span class="label">{{ field.name }}<i v-if="field.required"> *</i></span><select v-if="field.type === 'LIST'" v-model="params[field.name]" class="input" :required="field.required" @change="resetPaymentAfterInputChange"><option value="">Выберите значение</option><option v-for="option in sortedNominals(field.value_list)" :key="option.id" :value="option.id">{{ option.title }}</option></select><input v-else v-model.trim="params[field.name]" class="input" :required="field.required" @input="resetPaymentAfterInputChange" /><small v-if="field.name === 'nominal' && selectedCachedPrice" class="muted">Закупочная цена из кэша: {{ formatMoney(selectedCachedPrice.fixed_amount) }} ₽ · {{ formatCachedDate(selectedCachedPrice.calculated_at) }}</small><details v-if="field.name === 'nominal' && selectedCachedPrice" class="interhub-catalog__calculate-response"><summary>Полный ответ calculate</summary><pre>{{ formatProviderResponse(selectedCachedPrice.provider_response) }}</pre></details></label>
        <div class="interhub-catalog__actions" :class="{ 'is-single': !supportsCalculate }">
          <button v-if="supportsCalculate" class="btn interhub-catalog__action-btn" type="button" :disabled="ctx.calculationLoading" @click="calculate"><span class="interhub-catalog__action-index">1</span><span><strong>{{ ctx.calculationLoading ? 'Узнаём цену…' : 'Узнать цену' }}</strong><small>calculate</small></span></button>
          <button class="btn interhub-catalog__action-btn" type="submit" :disabled="checkDisabled"><span class="interhub-catalog__action-index">{{ supportsCalculate ? 2 : 1 }}</span><span><strong>{{ checkActionText }}</strong><small>check</small></span></button>
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
import { computed, nextTick, reactive, ref, watch } from 'vue'

// Контекст содержит каталог и действия загрузки, чтобы экран не знал деталей API.
const props = defineProps({
  ctx: { type: Object, required: true },
})

const titleCollator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' })
const servicesSortDirection = ref('asc')
const filteredServices = computed(() => {
  // Фильтруем по названию и категории без повторного запроса к провайдеру.
  const query = String(props.ctx.search || '').trim().toLowerCase()
  const services = Array.isArray(props.ctx.services) ? props.ctx.services : []
  const filtered = query ? services.filter((service) => `${service?.title || ''} ${service?.category || ''}`.toLowerCase().includes(query)) : services
  const direction = servicesSortDirection.value === 'asc' ? 1 : -1
  return [...filtered].sort((left, right) => direction * titleCollator.compare(String(left?.title || ''), String(right?.title || '')))
})
const pageSize = 20
const currentPage = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(filteredServices.value.length / pageSize)))
const pagedServices = computed(() => {
  // Показываем короткую страницу каталога, чтобы форма оплаты оставалась рядом с выбранной услугой.
  const start = (currentPage.value - 1) * pageSize
  return filteredServices.value.slice(start, start + pageSize)
})
const selectedService = ref(null)
const paymentForm = ref(null)
const account = ref('')
const amount = ref('')
const params = reactive({})
const needsAmount = computed(() => ['TOP_UP'].includes(String(selectedService.value?.type || '').toUpperCase()))
const hasNominal = computed(() => Boolean(selectedService.value?.fields?.some((field) => field?.name === 'nominal')))
const amountFromNominal = computed(() => needsAmount.value && hasNominal.value)
const paymentType = computed(() => String(selectedService.value?.type || '').toUpperCase())
const supportsCalculate = computed(() => ['VOUCHER', 'PIN', 'TOP_UP_FIXED'].includes(paymentType.value))
const hasCalculatedPrice = computed(() => Boolean(props.ctx.calculation?.success && Number(props.ctx.calculation?.fixed_amount) > 0))
const checkDisabled = computed(() => Boolean(props.ctx.checkLoading || (supportsCalculate.value && !hasCalculatedPrice.value)))
const checkActionText = computed(() => {
  // Подсказываем обязательный порядок для услуг, где check использует цену из calculate.
  if (props.ctx.checkLoading) return 'Проверяем…'
  return checkDisabled.value && supportsCalculate.value ? 'Сначала узнайте цену' : 'Узнать остаток'
})
const showAccount = computed(() => !['VOUCHER', 'TOP_UP_FIXED'].includes(paymentType.value))
const accountRequired = computed(() => paymentType.value === 'TOP_UP')
const accountLabel = computed(() => accountRequired.value ? 'Аккаунт или номер' : 'Аккаунт (временно необязательно)')
const selectedNominalTitle = computed(() => {
  // Находим подпись выбранного номинала, чтобы не заставлять оператора переносить сумму вручную.
  const nominal = selectedService.value?.fields?.find((field) => field?.name === 'nominal')
  return nominal?.value_list?.find((item) => String(item?.id) === String(params.nominal))?.title || ''
})
const selectedCachedPrice = computed(() => {
  // Находим сохранённую цену именно для выбранных услуги и номинала без нового запроса calculate.
  const serviceId = Number(selectedService.value?.service_id || 0)
  const nominalId = Number(params.nominal || 0)
  return (props.ctx.cachedPrices || []).find((item) => Number(item?.service_id) === serviceId && Number(item?.nominal_id) === nominalId) || null
})
const giftCode = computed(() => String(props.ctx.payment?.params?.gift_code || ''))
const isProcessing = computed(() => Number(props.ctx.payment?.status) === 1)
const paymentMessage = computed(() => {
  // Переводим статусы провайдера в понятный оператору итог оплаты.
  if (isProcessing.value) return 'Платёж обрабатывается. Первая проверка статуса — через 1 минуту, затем по графику InterHub.'
  if (props.ctx.payment?.success) return giftCode.value ? 'Оплата успешна. Код ваучера:' : 'Оплата успешно подтверждена.'
  return `Оплата не прошла · ${props.ctx.payment?.message || 'Ответ InterHub не получен'}`
})

watch(() => props.ctx.search, () => {
  // Возвращаемся на первую страницу после поиска, иначе выдача может выглядеть пустой.
  currentPage.value = 1
})

async function selectService(service) {
  // Открываем новую услугу и очищаем её форму вместе с результатами предыдущей операции.
  selectedService.value = service
  account.value = ''
  amount.value = ''
  Object.keys(params).forEach((key) => delete params[key])
  props.ctx.resetPaymentFlow()
  await nextTick()
  // Переносим фокус экрана к форме, чтобы оператор сразу видел, что выбрать дальше.
  paymentForm.value?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
}

function changePage(direction) {
  // Переключаем страницу в допустимых пределах без повторной загрузки каталога.
  currentPage.value = Math.min(totalPages.value, Math.max(1, currentPage.value + direction))
}

function toggleServicesSort() {
  // Меняем порядок услуг и возвращаемся к началу списка, чтобы не потерять выбранную страницу.
  servicesSortDirection.value = servicesSortDirection.value === 'asc' ? 'desc' : 'asc'
  currentPage.value = 1
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

function resetPaymentAfterInputChange() {
  // Сбрасываем прежний расчёт, чтобы его цена не ушла в check с новыми реквизитами или номиналом.
  if (props.ctx.calculation || props.ctx.check || props.ctx.payment || props.ctx.calculationLoading || props.ctx.checkLoading) props.ctx.resetPaymentFlow()
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

function formatAmountLimit(service) {
  // Показываем лимиты рядом с вводом суммы, чтобы оператор видел их в момент заполнения.
  const min = Number(service?.min_amount || 0)
  const max = Number(service?.max_amount || 0)
  if (!min && !max) return 'Лимит не указан'
  if (!max) return `Минимум: ${min}`
  if (!min) return `Максимум: ${max}`
  return `Лимит: ${min}–${max}`
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

function formatCachedDate(value) {
  // Показываем оператору время кэша, чтобы цена не выглядела как расчёт в реальном времени.
  if (!value) return 'дата неизвестна'
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function formatProviderResponse(value) {
  // Показываем сохранённый JSON как есть, чтобы оператор видел все поля ответа calculate.
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch {
    return String(value || '')
  }
}

function sortedNominals(options) {
  // Сортируем номиналы по сумме, а одинаковые значения — по подписи без случайного порядка от API.
  return [...(Array.isArray(options) ? options : [])].sort((left, right) => {
    const difference = nominalSortValue(left?.title) - nominalSortValue(right?.title)
    if (difference) return difference
    return titleCollator.compare(String(left?.title || ''), String(right?.title || ''))
  })
}

function nominalSortValue(title) {
  // Сохраняем разрядность в подписях вида "INR 2.500", чтобы 2 500 не стало 2,5.
  const match = String(title || '').match(/\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?/)
  if (!match) return Number.POSITIVE_INFINITY
  const value = match[0]
  const groups = value.split(/[.,]/)
  const normalized = groups.length > 1 && groups.slice(1).every((group) => group.length === 3)
    ? groups.join('')
    : value.replace(',', '.')
  return Number(normalized) || Number.POSITIVE_INFINITY
}
</script>

<style scoped>
.interhub-catalog__head { align-items: end; border-bottom: 1px solid rgba(245, 158, 11, .32); }
.interhub-catalog__head-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: end; }.interhub-catalog__price-action { white-space: nowrap; }
.interhub-catalog__eyebrow { margin: 0 0 4px; color: #b86b12; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.interhub-catalog__title { margin: 0; letter-spacing: -.03em; }
.interhub-catalog__lead { max-width: 680px; margin: 0 0 20px; color: var(--muted, #7a766f); }
.interhub-catalog__balance { display: inline-grid; gap: 3px; margin: 0 0 18px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }.interhub-catalog__balance span, .interhub-catalog__balance small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__balance strong { font-size: 20px; }
.interhub-catalog__price-progress { margin: -8px 0 18px; }
.interhub-catalog__toolbar { display: flex; gap: 16px; align-items: end; justify-content: space-between; margin-bottom: 18px; }
.interhub-catalog__search { width: min(460px, 100%); }
.interhub-catalog__sort { margin-right: auto; white-space: nowrap; }
.interhub-catalog__stats { display: grid; min-width: 120px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }
.interhub-catalog__stats strong { font-size: 20px; line-height: 1; }
.interhub-catalog__stats span, .interhub-catalog__id { color: var(--muted, #7a766f); font-size: 12px; }
.interhub-catalog__id { display: block; margin-top: 3px; font-family: ui-monospace, monospace; }
.interhub-catalog__type { display: inline-flex; padding: 3px 7px; border: 1px solid rgba(232, 134, 19, .35); color: #9b570d; font-size: 12px; font-weight: 700; }
.interhub-catalog__row { cursor: pointer; }.interhub-catalog__row.is-selected td { background: rgba(232, 134, 19, .08); }.interhub-catalog__form { display: grid; grid-template-columns: minmax(220px, .8fr) minmax(250px, 1fr) minmax(250px, 1fr) minmax(280px, 1fr); gap: 16px 18px; align-items: start; margin-top: 22px; padding: 22px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); scroll-margin-block: 24px; }.interhub-catalog__service-summary { align-self: center; padding-right: 12px; }.interhub-catalog__form h3 { margin: 0; }.interhub-catalog__actions { display: grid; width: 100%; max-width: 520px; min-width: 0; grid-column: 3 / span 2; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; justify-self: start; }.interhub-catalog__actions.is-single { max-width: 300px; grid-column: 4; align-self: center; }.interhub-catalog__action-btn { display: flex; min-width: 0; min-height: 58px; gap: 9px; align-items: center; justify-content: flex-start; padding: 8px 11px; text-align: left; transition: transform .16s ease, box-shadow .16s ease, filter .16s ease; }.interhub-catalog__action-btn:not(:disabled):hover { box-shadow: 0 8px 20px rgba(70, 224, 185, .16); filter: brightness(1.04); transform: translateY(-1px); }.interhub-catalog__action-btn > span:last-child { display: grid; gap: 1px; min-width: 0; }.interhub-catalog__action-btn strong { font-size: 14px; line-height: 1.08; }.interhub-catalog__action-btn small { color: rgba(9, 18, 27, .68); font-size: 10px; font-weight: 700; letter-spacing: .05em; }.interhub-catalog__action-index { display: grid; width: 24px; height: 24px; flex: 0 0 24px; place-items: center; border: 1px solid rgba(9, 18, 27, .28); border-radius: 50%; font-size: 11px; font-weight: 800; }.interhub-catalog__result { margin: 0; font-weight: 700; }.interhub-catalog__payment-result { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(250px, .8fr) minmax(0, 1fr) auto; gap: 10px 18px; align-items: center; padding-top: 14px; border-top: 1px solid rgba(232, 134, 19, .18); }.interhub-catalog__payment-result.is-error { color: #d45f5f; }.interhub-catalog__payment-result .muted { grid-column: 1 / -1; }.interhub-catalog__gift-code { width: fit-content; padding: 8px 10px; border: 1px dashed rgba(232, 134, 19, .7); background: rgba(232, 134, 19, .08); color: inherit; font-weight: 700; letter-spacing: .04em; }
.interhub-catalog__pagination { display: flex; gap: 12px; align-items: center; justify-content: end; margin-top: 12px; color: var(--muted, #7a766f); font-size: 13px; }
.interhub-catalog__auto-amount { display: grid; gap: 3px; min-height: 42px; padding: 8px 10px; border: 1px solid rgba(232, 134, 19, .35); }.interhub-catalog__auto-amount span, .interhub-catalog__auto-amount small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__auto-amount strong { font-size: 18px; }
.interhub-catalog__calculate-response { margin-top: 7px; color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__calculate-response summary { cursor: pointer; color: inherit; }.interhub-catalog__calculate-response pre { max-width: 420px; max-height: 180px; margin: 8px 0 0; padding: 8px; overflow: auto; border: 1px solid rgba(232, 134, 19, .2); background: rgba(9, 12, 25, .38); color: var(--text, #eee); font: 11px/1.45 ui-monospace, monospace; white-space: pre-wrap; }
@media (max-width: 1120px) { .interhub-catalog__form { grid-template-columns: repeat(2, minmax(240px, 1fr)); }.interhub-catalog__actions, .interhub-catalog__actions.is-single { grid-column: 1 / -1; }.interhub-catalog__payment-result { grid-template-columns: 1fr auto; } }
@media (max-width: 680px) { .interhub-catalog__head { align-items: start; flex-direction: column; } .interhub-catalog__head-actions { justify-content: start; } .interhub-catalog__toolbar { align-items: stretch; flex-direction: column; } .interhub-catalog__search { width: 100%; } .interhub-catalog__stats { width: fit-content; } .interhub-catalog__form { grid-template-columns: 1fr; padding: 16px; } .interhub-catalog__actions, .interhub-catalog__payment-result { grid-column: auto; grid-template-columns: 1fr; } }
</style>
