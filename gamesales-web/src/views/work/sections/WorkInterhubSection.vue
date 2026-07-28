<template>
  <section class="panel panel--wide interhub-catalog">
    <div class="panel__head interhub-catalog__head">
      <div>
        <p class="interhub-catalog__eyebrow">InterHub · агентский каталог</p>
        <h2 class="interhub-catalog__title">Платежи</h2>
      </div>
      <div class="interhub-catalog__head-actions">
        <button class="ghost interhub-catalog__history-action" type="button" @click="openSalesHistory">История продаж</button>
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
      <div class="interhub-catalog__balance"><span>Депозит InterHub</span><strong>{{ formatBalance(ctx.balance, ctx.currency) }}</strong><small v-if="hasOverdraft">Овердрафт: {{ formatBalance(overdraftBalance, ctx.currency) }} из {{ formatBalance(overdraftLimit, ctx.currency) }}</small><small v-if="hasOverdraft">Доступно для оплат: {{ formatBalance(availableForPayments, ctx.currency) }}</small><small v-else>Агентский счёт</small></div>
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
      <form v-if="selectedService" ref="paymentForm" class="interhub-catalog__form" :class="{ 'has-optional-account': paymentType === 'TOP_UP_FIXED' }" @submit.prevent="obtainPayment">
        <div v-if="obtainLoading" class="interhub-catalog__obtain-overlay"><WorkHamsterLoader :label="obtainLoadingLabel" /></div>
        <div class="interhub-catalog__service-summary"><p class="interhub-catalog__eyebrow">Получение</p><h3>{{ selectedService.title }}</h3></div>
        <label v-if="showAccount" class="field"><span class="label">{{ accountLabel }}<i v-if="accountRequired"> *</i></span><input v-model.trim="account" class="input" :required="accountRequired" @input="resetPaymentAfterInputChange" /><small v-if="!accountRequired" class="muted">Необязательно для этого типа услуги</small></label>
        <div v-if="amountFromNominal" class="interhub-catalog__auto-amount"><span>Сумма пополнения</span><strong>{{ selectedNominalTitle || 'Выберите номинал' }}</strong><small>Подставляется автоматически из номинала</small></div>
        <label v-else-if="needsAmount" class="field"><span class="label">Сумма пополнения</span><input v-model="amount" class="input" type="number" :min="selectedService.min_amount || 0.01" step="0.01" required @input="resetPaymentAfterInputChange" /><small class="muted">{{ formatAmountLimit(selectedService) }}</small></label>
        <label v-if="paymentType === 'VOUCHER'" class="field"><span class="label">Количество ключей</span><input v-model.number="voucherQuantity" class="input" type="number" min="1" max="20" step="1" required @input="resetPaymentAfterInputChange" /><small class="muted">Не более 20 за один запуск. Каждый ключ покупается и сохраняется отдельно.</small></label>
        <label v-for="field in selectedService.fields" :key="field.name" class="field"><span class="label">{{ field.name }}<i v-if="field.required"> *</i></span><select v-if="field.type === 'LIST'" v-model="params[field.name]" class="input" :required="field.required" @change="resetPaymentAfterInputChange"><option value="">Выберите значение</option><option v-for="option in sortedNominals(field.value_list)" :key="option.id" :value="option.id">{{ option.title }}</option></select><input v-else v-model.trim="params[field.name]" class="input" :required="field.required" @input="resetPaymentAfterInputChange" /><small v-if="field.name === 'nominal' && selectedCachedPrice" class="muted">Закупочная цена из кэша: {{ formatMoney(selectedCachedPrice.fixed_amount) }} ₽ · {{ formatCachedDate(selectedCachedPrice.calculated_at) }}</small><details v-if="field.name === 'nominal' && selectedCachedPrice" class="interhub-catalog__calculate-response"><summary>Полный ответ calculate</summary><pre>{{ formatProviderResponse(selectedCachedPrice.provider_response) }}</pre></details></label>
        <div class="interhub-catalog__actions is-single">
          <button class="btn interhub-catalog__action-btn" type="submit" :disabled="obtainLoading || !ctx.canPay"><span><strong>Получить</strong><small>Цена, проверка и получение ключа</small></span></button>
        </div>
        <p v-if="!ctx.canPay" class="interhub-catalog__owner-note muted">Получать ключи может только владелец.</p>
        <div v-if="obtainError" class="interhub-catalog__payment-result is-error"><p class="interhub-catalog__result">{{ obtainError }}</p></div>
        <div v-if="ctx.payment" class="interhub-catalog__payment-result" :class="{ 'is-error': !ctx.payment.success }">
          <p class="interhub-catalog__result">{{ paymentMessage }}</p>
          <div v-if="voucherGiftCodes.length" class="interhub-catalog__gift-codes"><code v-for="code in voucherGiftCodes" :key="code" class="interhub-catalog__gift-code">{{ code }}</code></div>
          <code v-else-if="giftCode" class="interhub-catalog__gift-code">{{ giftCode }}</code>
        </div>
      </form>
    </div>
  </section>

  <teleport to="body">
    <div v-if="salesHistoryOpen" class="work-page work-modal-root modal-backdrop interhub-history-backdrop" @click.self="closeSalesHistory">
      <section class="modal interhub-history" role="dialog" aria-modal="true" aria-labelledby="interhub-history-title">
        <div class="modal__head panel__head panel__head--tight interhub-history__head">
          <div>
            <p class="interhub-catalog__eyebrow">InterHub · оплаченные операции</p>
            <h3 id="interhub-history-title">История продаж</h3>
          </div>
          <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeSalesHistory">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>
        <div class="modal__body interhub-history__body">
          <form class="interhub-history__filters" @submit.prevent="applySalesHistoryFilter">
            <label class="field"><span class="label">Дата с</span><input v-model="salesHistoryDateFrom" class="input" type="date" /></label>
            <label class="field"><span class="label">Дата по</span><input v-model="salesHistoryDateTo" class="input" type="date" /></label>
            <label class="field interhub-history__search"><span class="label">Поиск</span><input v-model.trim="salesHistorySearch" class="input" type="search" placeholder="Название сервиса или номинал" /></label>
            <button class="btn" type="submit" :disabled="ctx.salesHistoryLoading">{{ ctx.salesHistoryLoading ? 'Загружаем…' : 'Показать' }}</button>
          </form>
          <p v-if="ctx.salesHistoryError" class="error">{{ ctx.salesHistoryError }}</p>
          <div class="interhub-history__cards" aria-label="Итоги выборки">
            <div class="mini"><div class="mini__label">Операций</div><div class="mini__value">{{ sortedSalesHistory.length }}</div></div>
            <div class="mini"><div class="mini__label">Сумма платежей</div><div class="mini__value">{{ formatMoney(salesHistoryTotalAmount) }} ₽</div></div>
          </div>
          <div class="table-wrap interhub-history__table-wrap">
            <table class="table table--compact">
              <thead>
                <tr>
                  <th><button class="interhub-history__sort" type="button" @click="sortSalesHistory('service')">Название сервиса <span>{{ sortMark('service') }}</span></button></th>
                  <th><button class="interhub-history__sort" type="button" @click="sortSalesHistory('nominal')">Номинал <span>{{ sortMark('nominal') }}</span></button></th>
                  <th><button class="interhub-history__sort" type="button" @click="sortSalesHistory('price')">Цена <span>{{ sortMark('price') }}</span></button></th>
                  <th><button class="interhub-history__sort" type="button" @click="sortSalesHistory('giftCode')">Гифт-код <span>{{ sortMark('giftCode') }}</span></button></th>
                  <th><button class="interhub-history__sort" type="button" @click="sortSalesHistory('createdAt')">Дата <span>{{ sortMark('createdAt') }}</span></button></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="ctx.salesHistoryLoading"><td colspan="5" class="muted">Загружаем историю продаж…</td></tr>
                <tr v-else-if="!sortedSalesHistory.length"><td colspan="5" class="muted">За выбранный период оплаченных операций нет.</td></tr>
                <tr v-for="item in pagedSalesHistory" :key="`${item.serviceId}-${item.createdAt}-${item.giftCode}`">
                  <td>{{ item.service }}</td>
                  <td>{{ item.nominal || '—' }}</td>
                  <td>{{ formatMoney(item.price) }} ₽</td>
                  <td><code v-if="item.giftCode" class="interhub-history__gift-code">{{ item.giftCode }}</code><span v-else>—</span></td>
                  <td>{{ formatHistoryDate(item.createdAt) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="sortedSalesHistory.length" class="interhub-history__pagination">
            <span>{{ salesHistoryRange }}</span>
            <div>
              <button class="ghost" type="button" aria-label="Предыдущая страница истории продаж" :disabled="activeSalesHistoryPage <= 1" @click="changeSalesHistoryPage(-1)">Назад</button>
              <button class="ghost" type="button" aria-label="Следующая страница истории продаж" :disabled="activeSalesHistoryPage >= salesHistoryPageCount" @click="changeSalesHistoryPage(1)">Вперёд</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

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
const voucherQuantity = ref(1)
const params = reactive({})
const salesHistoryOpen = ref(false)
const salesHistoryDateFrom = ref('')
const salesHistoryDateTo = ref('')
const salesHistorySearch = ref('')
const salesHistorySort = reactive({ field: 'createdAt', direction: 'desc' })
const salesHistoryPage = ref(1)
const overdraftBalance = computed(() => Number(props.ctx.overBalance || 0))
const overdraftLimit = computed(() => Math.max(0, Number(props.ctx.overLimit || 0)))
const hasOverdraft = computed(() => overdraftLimit.value > 0)
const availableForPayments = computed(() => {
  // Учитываем знак over_balance из InterHub: отрицательное значение уменьшает доступный лимит.
  return Math.max(0, Number(props.ctx.balance || 0)) + Math.max(0, overdraftLimit.value + overdraftBalance.value)
})
const needsAmount = computed(() => ['TOP_UP'].includes(String(selectedService.value?.type || '').toUpperCase()))
const hasNominal = computed(() => Boolean(selectedService.value?.fields?.some((field) => field?.name === 'nominal')))
const amountFromNominal = computed(() => needsAmount.value && hasNominal.value)
const paymentType = computed(() => String(selectedService.value?.type || '').toUpperCase())
const supportsCalculate = computed(() => ['VOUCHER', 'PIN', 'TOP_UP_FIXED'].includes(paymentType.value))
const showAccount = computed(() => paymentType.value !== 'VOUCHER')
const accountRequired = computed(() => paymentType.value === 'TOP_UP')
const accountLabel = computed(() => accountRequired.value ? 'Аккаунт или номер' : 'Аккаунт (необязательно)')
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
const isVoucherBatch = computed(() => Boolean(props.ctx.payment?.batch_id))
const voucherGiftCodes = computed(() => Array.isArray(props.ctx.payment?.gift_codes) ? props.ctx.payment.gift_codes.map((code) => String(code || '')).filter(Boolean) : [])
const isProcessing = computed(() => Number(props.ctx.payment?.status) === 1)
const obtainLoading = ref(false)
const obtainStage = ref('')
const obtainError = ref('')
const obtainLoadingLabel = computed(() => ({
  calculate: 'Узнаём цену…',
  check: 'Проверяем возможность выдачи…',
  pay: 'Получаем ключи…',
  status: 'Проверяем выдачу ключей…',
}[obtainStage.value] || 'Получаем ключи…'))
const paymentMessage = computed(() => {
  // Переводим статусы провайдера в понятный оператору итог оплаты.
  if (isVoucherBatch.value) {
    const received = Number(props.ctx.payment?.received_quantity || 0)
    const requested = Number(props.ctx.payment?.requested_quantity || 0)
    if (props.ctx.payment?.state === 'completed') return `Получено ключей: ${received} из ${requested}.`
    if (props.ctx.payment?.state === 'awaiting_status') return `Получено ключей: ${received} из ${requested}. Оплата следующего ключа уже отправлена и проверяется без повторного списания.`
    return `Получено ключей: ${received} из ${requested}. ${props.ctx.payment?.message || 'Покупка остановлена.'}`
  }
  if (isProcessing.value) return 'Платёж обрабатывается. Первая проверка статуса — через 1 минуту, затем по графику InterHub.'
  if (props.ctx.payment?.success) return giftCode.value ? 'Оплата успешна. Код ваучера:' : 'Оплата успешно подтверждена.'
  return `Оплата не прошла · ${props.ctx.payment?.message || 'Ответ InterHub не получен'}`
})
const salesHistoryRows = computed(() => {
  // Берём названия из сохранённого calculate, а каталог используем только для старых записей без расчёта.
  const serviceNames = new Map((Array.isArray(props.ctx.services) ? props.ctx.services : []).map((service) => [Number(service?.service_id), String(service?.title || '')]))
  return (Array.isArray(props.ctx.salesHistory) ? props.ctx.salesHistory : []).map((item) => {
    const serviceId = Number(item?.service_id || 0)
    return {
      serviceId,
      service: String(item?.service_title || '').trim() || serviceNames.get(serviceId) || `Услуга #${serviceId || '—'}`,
      nominal: String(item?.nominal_title || '').trim() || String(item?.nominal || ''),
      price: Number(item?.price || 0),
      giftCode: String(item?.gift_code || ''),
      createdAt: String(item?.created_at || ''),
    }
  })
})
const filteredSalesHistory = computed(() => {
  // Ищем по двум понятным оператору полям без нового запроса к истории.
  const query = salesHistorySearch.value.toLocaleLowerCase('ru-RU')
  if (!query) return salesHistoryRows.value
  return salesHistoryRows.value.filter((item) => `${item.service} ${item.nominal}`.toLocaleLowerCase('ru-RU').includes(query))
})
const sortedSalesHistory = computed(() => {
  // Сортируем уже загруженную выборку по любому видимому столбцу без повторного запроса.
  const { field, direction } = salesHistorySort
  const multiplier = direction === 'asc' ? 1 : -1
  return [...filteredSalesHistory.value].sort((left, right) => {
    if (field === 'price') return multiplier * (left.price - right.price)
    if (field === 'createdAt') return multiplier * (new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime())
    return multiplier * titleCollator.compare(String(left[field] || ''), String(right[field] || ''))
  })
})
const salesHistoryTotalAmount = computed(() => {
  // Складываем только строки текущей выборки, уже ограниченной датами и поиском.
  return filteredSalesHistory.value.reduce((total, item) => total + item.price, 0)
})
const salesHistoryPageSize = 25
const salesHistoryPageCount = computed(() => Math.max(1, Math.ceil(sortedSalesHistory.value.length / salesHistoryPageSize)))
const activeSalesHistoryPage = computed(() => Math.min(Math.max(salesHistoryPage.value, 1), salesHistoryPageCount.value))
const pagedSalesHistory = computed(() => {
  // Показываем короткую страницу, чтобы длинная история не растягивала модальное окно.
  const offset = (activeSalesHistoryPage.value - 1) * salesHistoryPageSize
  return sortedSalesHistory.value.slice(offset, offset + salesHistoryPageSize)
})
const salesHistoryRange = computed(() => {
  // Подсказываем границы страницы и общее число найденных оплаченных операций.
  const total = sortedSalesHistory.value.length
  if (!total) return ''
  const start = (activeSalesHistoryPage.value - 1) * salesHistoryPageSize + 1
  const end = Math.min(start + salesHistoryPageSize - 1, total)
  return `Показаны ${start}–${end} из ${total}`
})

watch(() => props.ctx.search, () => {
  // Возвращаемся на первую страницу после поиска, иначе выдача может выглядеть пустой.
  currentPage.value = 1
})

watch(() => props.ctx.salesHistory, () => {
  // Возвращаемся к началу при новой выборке по датам, чтобы не показать пустую страницу.
  salesHistoryPage.value = 1
})

watch(salesHistorySearch, () => {
  // Возвращаемся к началу, чтобы фильтр не оставил пользователя на пустой странице.
  salesHistoryPage.value = 1
})

async function selectService(service) {
  // Открываем новую услугу и очищаем её форму вместе с результатами предыдущей операции.
  selectedService.value = service
  account.value = ''
  amount.value = ''
  voucherQuantity.value = 1
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

function openSalesHistory() {
  // Открываем историю и сразу запрашиваем оплаченные операции с текущими границами дат.
  salesHistoryOpen.value = true
  applySalesHistoryFilter()
}

function closeSalesHistory() {
  // Закрываем окно без сброса фильтра, чтобы оператор мог быстро вернуться к тому же периоду.
  salesHistoryOpen.value = false
}

function applySalesHistoryFilter() {
  // Передаём пустые границы как отсутствие фильтра, а заполненные — как включительный период.
  salesHistoryPage.value = 1
  props.ctx.loadSalesHistory({ dateFrom: salesHistoryDateFrom.value, dateTo: salesHistoryDateTo.value })
}

function sortSalesHistory(field) {
  // Повторный клик по столбцу меняет направление, другой столбец начинает с прямого порядка.
  if (salesHistorySort.field === field) salesHistorySort.direction = salesHistorySort.direction === 'asc' ? 'desc' : 'asc'
  else {
    salesHistorySort.field = field
    salesHistorySort.direction = field === 'createdAt' ? 'desc' : 'asc'
  }
  salesHistoryPage.value = 1
}

function changeSalesHistoryPage(direction) {
  // Переключаем страницу в допустимых границах без повторной загрузки истории.
  salesHistoryPage.value = Math.min(salesHistoryPageCount.value, Math.max(1, activeSalesHistoryPage.value + direction))
}

function sortMark(field) {
  // Показываем направление только у активного столбца, чтобы заголовки не перегружали таблицу.
  if (salesHistorySort.field !== field) return ''
  return salesHistorySort.direction === 'asc' ? '↑' : '↓'
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
  if (paymentType.value === 'VOUCHER') {
    // Передаём количество только как инструкцию для нашей пачки, InterHub получает отдельный pay на каждый ключ.
    payload.quantity = Math.min(20, Math.max(1, Math.trunc(Number(voucherQuantity.value) || 1)))
  }
  return payload
}

function resetPaymentAfterInputChange() {
  // Сбрасываем прежний расчёт, чтобы его цена не ушла в check с новыми реквизитами или номиналом.
  obtainError.value = ''
  if (props.ctx.calculation || props.ctx.check || props.ctx.payment || props.ctx.calculationLoading || props.ctx.checkLoading) props.ctx.resetPaymentFlow()
}

async function obtainPayment() {
  // Выполняет обязательные шаги подряд, оставляя один понятный вход для получения ключа.
  if (obtainLoading.value || !props.ctx.canPay) return
  obtainLoading.value = true
  obtainError.value = ''
  try {
    if (isProcessing.value) {
      obtainStage.value = 'status'
      if (isVoucherBatch.value) await props.ctx.pay()
      else await props.ctx.refreshPaymentStatus()
      return
    }

    const payload = buildPayload()
    props.ctx.resetPaymentFlow()
    if (supportsCalculate.value) {
      obtainStage.value = 'calculate'
      await props.ctx.calculate(payload)
      if (!props.ctx.calculation?.success) {
        obtainError.value = `Не удалось узнать цену: ${props.ctx.calculation?.message || 'Interhub не вернул расчёт'}`
        return
      }
    }

    obtainStage.value = 'check'
    await props.ctx.checkPayment(payload)
    if (!props.ctx.check?.success) {
      obtainError.value = `Не удалось проверить выдачу: ${props.ctx.check?.message || 'Interhub не подтвердил операцию'}`
      return
    }

    obtainStage.value = 'pay'
    await props.ctx.pay()
    if (!props.ctx.payment?.success && !isProcessing.value) {
      obtainError.value = `Не удалось получить ключ: ${props.ctx.payment?.message || 'Interhub не подтвердил оплату'}`
    }
  } catch (error) {
    // Показываем ошибку единого сценария рядом с кнопкой, не скрывая, на каком шаге он остановился.
    obtainError.value = String(error?.message || 'Не удалось получить ключ')
  } finally {
    obtainStage.value = ''
    obtainLoading.value = false
  }
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

function formatHistoryDate(value) {
  // Выводим время оплаты в локальном формате оператора вместо технической ISO-строки.
  if (!value) return '—'
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
.interhub-catalog__row { cursor: pointer; }.interhub-catalog__row.is-selected td { background: rgba(232, 134, 19, .08); }.interhub-catalog__form { display: grid; grid-template-columns: minmax(220px, .8fr) minmax(250px, 1fr) minmax(250px, 1fr) minmax(280px, 1fr); gap: 16px 18px; align-items: start; margin-top: 22px; padding: 22px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); scroll-margin-block: 24px; }.interhub-catalog__service-summary { align-self: center; padding-right: 12px; }.interhub-catalog__form h3 { margin: 0; }.interhub-catalog__actions { display: grid; width: 100%; max-width: 520px; min-width: 0; grid-column: 3 / span 2; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; justify-self: start; }.interhub-catalog__actions.is-single, .interhub-catalog__form.has-optional-account .interhub-catalog__actions { max-width: 300px; grid-column: 4; align-self: center; }.interhub-catalog__form.has-optional-account .interhub-catalog__actions { grid-template-columns: 1fr; }.interhub-catalog__action-btn { display: flex; min-width: 0; min-height: 58px; gap: 9px; align-items: center; justify-content: flex-start; padding: 8px 11px; text-align: left; transition: transform .16s ease, box-shadow .16s ease, filter .16s ease; }.interhub-catalog__action-btn:not(:disabled):hover { box-shadow: 0 8px 20px rgba(70, 224, 185, .16); filter: brightness(1.04); transform: translateY(-1px); }.interhub-catalog__action-btn > span:last-child { display: grid; gap: 1px; min-width: 0; }.interhub-catalog__action-btn strong { font-size: 14px; line-height: 1.08; }.interhub-catalog__action-btn small { color: rgba(9, 18, 27, .68); font-size: 10px; font-weight: 700; letter-spacing: .05em; }.interhub-catalog__action-index { display: grid; width: 24px; height: 24px; flex: 0 0 24px; place-items: center; border: 1px solid rgba(9, 18, 27, .28); border-radius: 50%; font-size: 11px; font-weight: 800; }.interhub-catalog__result { margin: 0; font-weight: 700; }.interhub-catalog__payment-result { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(250px, .8fr) minmax(0, 1fr) auto; gap: 10px 18px; align-items: center; padding-top: 14px; border-top: 1px solid rgba(232, 134, 19, .18); }.interhub-catalog__payment-result.is-error { color: #d45f5f; }.interhub-catalog__payment-result .muted { grid-column: 1 / -1; }.interhub-catalog__gift-code { width: fit-content; padding: 8px 10px; border: 1px dashed rgba(232, 134, 19, .7); background: rgba(232, 134, 19, .08); color: inherit; font-weight: 700; letter-spacing: .04em; }
.interhub-catalog__form { position: relative; }
.interhub-catalog__obtain-overlay { position: absolute; z-index: 3; inset: 0; display: grid; place-items: center; padding: 24px; background: rgba(9, 18, 27, .78); backdrop-filter: blur(2px); }
.interhub-catalog__owner-note { grid-column: 1 / -1; margin: 0; }
.interhub-catalog__gift-codes { display: grid; justify-items: start; gap: 8px; }
.interhub-catalog__gift-code { max-width: 100%; overflow-wrap: anywhere; }
.interhub-catalog__pagination { display: flex; gap: 12px; align-items: center; justify-content: end; margin-top: 12px; color: var(--muted, #7a766f); font-size: 13px; }
.interhub-catalog__auto-amount { display: grid; gap: 3px; min-height: 42px; padding: 8px 10px; border: 1px solid rgba(232, 134, 19, .35); }.interhub-catalog__auto-amount span, .interhub-catalog__auto-amount small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__auto-amount strong { font-size: 18px; }
.interhub-catalog__calculate-response { margin-top: 7px; color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__calculate-response summary { cursor: pointer; color: inherit; }.interhub-catalog__calculate-response pre { max-width: 420px; max-height: 180px; margin: 8px 0 0; padding: 8px; overflow: auto; border: 1px solid rgba(232, 134, 19, .2); background: rgba(9, 12, 25, .38); color: var(--text, #eee); font: 11px/1.45 ui-monospace, monospace; white-space: pre-wrap; }
.interhub-history-backdrop { --modal-bg: #101626; --modal-text: #f4f7ff; --ink: #f4f7ff; --muted: #b5bfd3; --table-bg: #202838; --table-border: rgba(181, 194, 219, .22); --input-bg: #0d1320; --input-border: rgba(181, 194, 219, .28); --ghost-bg: rgba(255, 255, 255, .08); --ghost-text: #f4f7ff; --ghost-border: rgba(255, 255, 255, .18); z-index: 80; }
.interhub-history { width: min(1180px, calc(100vw - 32px)); max-height: min(780px, calc(100vh - 32px)); overflow: auto; }
.interhub-history__head { position: sticky; top: 0; z-index: 1; padding-bottom: 12px; border-bottom: 1px solid rgba(181, 194, 219, .16); background: #101626; }.interhub-history__head h3 { margin: 0; color: #f4f7ff; font-size: 22px; letter-spacing: -.02em; }
.interhub-history__body { display: grid; align-content: start; gap: 16px; }.interhub-history__filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; padding: 14px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); }.interhub-history__filters .field { min-width: 170px; }.interhub-history__filters .interhub-history__search { min-width: 260px; flex: 1 1 260px; }.interhub-history__filters .btn { min-height: 40px; }.interhub-history__cards { display: grid; grid-template-columns: repeat(2, minmax(180px, 240px)); gap: 10px; }.interhub-history__cards .mini { min-width: 0; background: #1b2435; border-color: rgba(181, 194, 219, .2); }.interhub-history__cards .mini__value { color: #f4f7ff; }.interhub-history__table-wrap { max-height: min(460px, 44vh); min-height: 0; overflow: auto; overscroll-behavior: contain; }.interhub-history__table-wrap thead { position: sticky; top: 0; z-index: 1; background: #202838; }.interhub-history__table-wrap .table { color: #eef2ff; }.interhub-history__table-wrap .table th { background: #2a3447; color: #f7f9ff; }.interhub-history__table-wrap .table td { color: #e5eaf5; }.interhub-history__pagination { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 4px; color: #b5bfd3; font-size: 13px; }.interhub-history__pagination > div { display: flex; gap: 8px; }.interhub-history__sort { display: inline-flex; width: 100%; gap: 5px; padding: 0; border: 0; background: transparent; color: inherit; font: inherit; font-weight: 700; text-align: left; cursor: pointer; }.interhub-history__sort span { color: #e88613; }.interhub-history__gift-code { color: #f4f7ff; font: 12px/1.35 ui-monospace, monospace; white-space: nowrap; }
@media (max-width: 1120px) { .interhub-catalog__form { grid-template-columns: repeat(2, minmax(240px, 1fr)); }.interhub-catalog__actions, .interhub-catalog__actions.is-single, .interhub-catalog__form.has-optional-account .interhub-catalog__actions { grid-column: 1 / -1; }.interhub-catalog__payment-result { grid-template-columns: 1fr auto; } }
@media (max-width: 680px) { .interhub-catalog__head { align-items: start; flex-direction: column; } .interhub-catalog__head-actions { justify-content: start; } .interhub-catalog__toolbar { align-items: stretch; flex-direction: column; } .interhub-catalog__search { width: 100%; } .interhub-catalog__stats { width: fit-content; } .interhub-catalog__form { grid-template-columns: 1fr; padding: 16px; } .interhub-catalog__actions, .interhub-catalog__form.has-optional-account .interhub-catalog__actions, .interhub-catalog__payment-result { grid-column: auto; grid-template-columns: 1fr; } .interhub-history { width: calc(100vw - 16px); } .interhub-history__filters { align-items: stretch; }.interhub-history__filters .field, .interhub-history__filters .btn { width: 100%; } .interhub-history__cards { grid-template-columns: 1fr; }.interhub-history__pagination { align-items: stretch; flex-direction: column; }.interhub-history__pagination > div { justify-content: stretch; }.interhub-history__pagination .ghost { flex: 1; } }
</style>
