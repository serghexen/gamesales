<template>
  <section class="sbp-center">
    <button
      data-test="sbp-open"
      class="sbp-center__trigger"
      type="button"
      aria-label="Открыть платежи СБП"
      title="Платежи СБП"
      @click="openCenter"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <path d="M14 14h3v3h-3zM18 18h3v3h-3zM18 14h3M14 19v2" />
      </svg>
      <span>СБП</span>
      <span v-if="unseenCount" data-test="sbp-unseen" class="sbp-center__badge">{{ badgeLabel }}</span>
    </button>

    <teleport to="body">
      <transition name="sbp-fade">
        <div v-if="open" class="work-page work-modal-root sbp-backdrop" @click.self="closeCenter">
          <section class="sbp-modal" role="dialog" aria-modal="true" aria-labelledby="sbp-title">
            <header class="sbp-modal__head">
              <div class="sbp-modal__brand" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                  <path d="M14 14h3v3h-3zM18 18h3v3h-3zM18 14h3M14 19v2" />
                </svg>
              </div>
              <div>
                <span class="sbp-modal__eyebrow">Система быстрых платежей</span>
                <h2 id="sbp-title">Платежи</h2>
              </div>
              <button class="sbp-modal__close" type="button" aria-label="Закрыть" @click="closeCenter">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 6l12 12M18 6 6 18" />
                </svg>
              </button>
            </header>

            <nav class="sbp-tabs" aria-label="Разделы платежного центра">
              <button data-test="sbp-tab-new" :class="{ 'is-active': tab === 'new' }" type="button" @click="tab = 'new'">
                Новый QR
              </button>
              <button data-test="sbp-tab-history" :class="{ 'is-active': tab === 'history' }" type="button" @click="openHistory">
                История
                <span v-if="unseenCount">{{ badgeLabel }}</span>
              </button>
            </nav>

            <div v-if="tab === 'new'" class="sbp-modal__content">
              <form v-if="!activePayment" class="sbp-form" @submit.prevent="createPayment">
                <label class="sbp-field">
                  <span class="sbp-field__head">
                    <b>Описание услуги</b>
                    <small>{{ description.trim().length }}/128</small>
                  </span>
                  <input
                    v-model="description"
                    data-test="sbp-description"
                    type="text"
                    maxlength="128"
                    autocomplete="off"
                    placeholder="Например, A Way Out для PS5"
                    @input="error = ''"
                  />
                  <small class="sbp-field__hint">Попадёт в платёж и кассовый чек</small>
                </label>

                <div class="sbp-form__row">
                  <label class="sbp-field">
                    <span class="sbp-field__head"><b>Покупатель</b></span>
                    <input
                      v-model="buyer"
                      data-test="sbp-buyer"
                      type="text"
                      maxlength="200"
                      autocomplete="off"
                      placeholder="Имя, ник или номер заказа"
                      @input="error = ''"
                    />
                    <small class="sbp-field__hint">Только для истории CRM</small>
                  </label>

                  <label class="sbp-field sbp-field--amount">
                    <span class="sbp-field__head"><b>Сумма</b></span>
                    <span class="sbp-amount">
                      <input
                        v-model="amount"
                        data-test="sbp-amount"
                        type="text"
                        inputmode="decimal"
                        autocomplete="off"
                        placeholder="0"
                        @input="error = ''"
                      />
                      <b>₽</b>
                    </span>
                    <small class="sbp-field__hint">{{ limitsLabel }}</small>
                  </label>
                </div>

                <p class="sbp-form__notice">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 10v6M12 7h.01" />
                  </svg>
                  QR действует {{ config.qr_lifetime_minutes || 15 }} минут. Покупатель не передаётся в банк и чек.
                </p>

                <p v-if="configLoaded && !config.enabled" class="sbp-message sbp-message--warning">
                  Интеграция пока выключена или заполнена не полностью. Проверьте переменные окружения API.
                </p>
                <p v-if="error" class="sbp-message sbp-message--error" role="alert">{{ error }}</p>

                <button data-test="sbp-create" class="sbp-primary" type="submit" :disabled="busy || !formValid || !config.enabled">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <path d="M14 14h3v3h-3zM18 18h3v3h-3zM18 14h3M14 19v2" />
                  </svg>
                  {{ busy ? 'Формируем QR…' : 'Сформировать QR' }}
                </button>
              </form>

              <article v-else class="sbp-payment" data-test="sbp-payment-result">
                <div class="sbp-payment__summary">
                  <span class="sbp-status" :class="`sbp-status--${activePayment.state}`">
                    <i></i>{{ statusLabel(activePayment.state) }}
                  </span>
                  <strong>{{ formatRubles(activePayment.amount) }}</strong>
                </div>
                <dl class="sbp-payment__details">
                  <div><dt>Услуга</dt><dd>{{ activePayment.description }}</dd></div>
                  <div><dt>Покупатель</dt><dd>{{ activePayment.buyer }}</dd></div>
                  <div><dt>Создал</dt><dd>{{ activePayment.created_by }}</dd></div>
                </dl>
                <div v-if="activePayment.qr_data_url && activePayment.state === 'pending'" class="sbp-qr">
                  <img :src="activePayment.qr_data_url" alt="QR-код для оплаты через СБП" />
                  <p>Код можно скачать и отправить покупателю. Закрытие окна не отменяет платёж.</p>
                </div>
                <div v-else-if="activePayment.state === 'confirmed'" class="sbp-result sbp-result--success">
                  <span>✓</span><strong>Оплата подтверждена</strong>
                </div>
                <div v-else-if="isFinished(activePayment.state)" class="sbp-result sbp-result--failure">
                  <span>!</span><strong>{{ statusLabel(activePayment.state) }}</strong>
                </div>
                <p v-if="activePayment.last_error" class="sbp-message sbp-message--error">{{ activePayment.last_error }}</p>
                <div class="sbp-payment__actions">
                  <button v-if="activePayment.qr_data_url" data-test="sbp-download" class="sbp-secondary" type="button" @click="downloadQr(activePayment)">Скачать QR</button>
                  <button data-test="sbp-create-another" class="sbp-primary sbp-primary--compact" type="button" @click="startAnother">Создать ещё</button>
                  <button class="sbp-secondary" type="button" @click="closeCenter">Закрыть</button>
                </div>
              </article>
            </div>

            <div v-else class="sbp-modal__content sbp-history">
              <div class="sbp-history__toolbar">
                <div class="sbp-scope">
                  <button :class="{ 'is-active': !mineOnly }" type="button" @click="setScope(false)">Все</button>
                  <button :class="{ 'is-active': mineOnly }" type="button" @click="setScope(true)">Мои</button>
                </div>
                <button
                  data-test="sbp-refresh"
                  class="sbp-secondary sbp-refresh"
                  :class="{ 'is-refreshing': manualRefreshing }"
                  type="button"
                  :disabled="manualRefreshing"
                  @click="refreshHistory"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M20 6v5h-5M4 18v-5h5M6.1 9a7 7 0 0 1 11.6-2.6L20 11M4 13l2.3 4.6A7 7 0 0 0 17.9 15" />
                  </svg>
                  Обновить
                </button>
              </div>
              <div class="sbp-history__filters">
                <form class="sbp-search" role="search" @submit.prevent="applyHistorySearch">
                  <input
                    v-model="historySearch"
                    data-test="sbp-history-search"
                    type="search"
                    maxlength="100"
                    autocomplete="off"
                    placeholder="Услуга, покупатель, сотрудник…"
                  />
                  <button v-if="historySearch" class="sbp-search__clear" type="button" aria-label="Очистить поиск" @click="clearHistorySearch">×</button>
                  <button class="sbp-search__submit" type="submit" aria-label="Найти" title="Найти">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></svg>
                  </button>
                </form>
                <label class="sbp-state-filter">
                  <span>Статус</span>
                  <select v-model="historyState" data-test="sbp-history-state" @change="applyHistoryFilters">
                    <option value="">Все статусы</option>
                    <option value="pending">Ожидает оплату</option>
                    <option value="confirmed">Оплачен</option>
                    <option value="expired">Истёк</option>
                    <option value="rejected">Отклонён</option>
                    <option value="cancelled">Отменён</option>
                    <option value="failed">Ошибка</option>
                  </select>
                </label>
              </div>
              <p v-if="historyError" class="sbp-message sbp-message--error">{{ historyError }}</p>
              <div v-if="!historyLoading && !payments.length" class="sbp-history__empty">
                Здесь появятся созданные QR и результаты оплат.
              </div>
              <div v-else class="sbp-history__list">
                <div class="sbp-history__columns" aria-hidden="true">
                  <span>Статус</span>
                  <span>Платёж</span>
                  <span>Создал</span>
                  <span>Сумма</span>
                  <span></span>
                </div>
                <article v-for="payment in payments" :key="payment.id" data-test="sbp-history-row" class="sbp-history-row">
                  <span class="sbp-status" :class="`sbp-status--${payment.state}`"><i></i>{{ statusLabel(payment.state) }}</span>
                  <div class="sbp-history-row__main">
                    <h3>{{ payment.description }}</h3>
                    <p>{{ payment.buyer }}</p>
                  </div>
                  <div class="sbp-history-row__meta">
                    <b>{{ payment.created_by }}</b>
                    <time :datetime="payment.created_at">{{ formatDate(payment.created_at) }}</time>
                  </div>
                  <strong class="sbp-history-row__amount">{{ formatRubles(payment.amount) }}</strong>
                  <button class="sbp-history-row__open" type="button" @click="showPayment(payment)">
                    {{ payment.state === 'pending' ? 'Открыть QR' : 'Открыть' }}
                  </button>
                </article>
              </div>
              <footer v-if="historyTotal" class="sbp-pagination">
                <span>{{ historyRangeLabel }}</span>
                <div>
                  <button data-test="sbp-page-prev" type="button" :disabled="historyPage <= 1" aria-label="Предыдущая страница" @click="goToHistoryPage(historyPage - 1)">‹</button>
                  <b>{{ historyPage }} / {{ historyPageCount }}</b>
                  <button data-test="sbp-page-next" type="button" :disabled="historyPage >= historyPageCount" aria-label="Следующая страница" @click="goToHistoryPage(historyPage + 1)">›</button>
                </div>
              </footer>
            </div>
          </section>
        </div>
      </transition>

      <transition-group name="sbp-toast" tag="div" class="sbp-toasts" aria-live="polite">
        <button v-for="toast in toasts" :key="toast.id" type="button" @click="showPayment(toast.payment)">
          <span>✓</span>
          <div><strong>Оплата получена</strong><small>{{ toast.payment.buyer }} · {{ formatRubles(toast.payment.amount) }}</small></div>
        </button>
      </transition-group>
    </teleport>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, unref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'

const props = defineProps({
  ctx: { type: Object, required: true },
})

const defaultDescription = 'Услуга по оформлению цифрового контента'
const open = ref(false)
const tab = ref('new')
const description = ref(defaultDescription)
const buyer = ref('')
const amount = ref('')
const busy = ref(false)
const error = ref('')
const configLoaded = ref(false)
const config = ref({ enabled: false, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 })
const activePayment = ref(null)
const payments = ref([])
const mineOnly = ref(false)
const historyLoading = ref(false)
const manualRefreshing = ref(false)
const historyError = ref('')
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 12
const historySearch = ref('')
const appliedHistorySearch = ref('')
const historyState = ref('')
const unseenCount = ref(0)
const toasts = ref([])
const knownConfirmedIds = new Set()
let historyInitialized = false
let historyRequestSequence = 0
let pollTimer = null

const token = computed(() => String(unref(props.ctx.authToken) || ''))
const amountKopecks = computed(() => {
  // Преобразуем рубли в целые копейки без отправки дробного float в API.
  const normalized = String(amount.value || '').trim().replace(',', '.')
  if (!/^\d+(?:\.\d{0,2})?$/.test(normalized)) return 0
  return Math.round(Number(normalized) * 100)
})
const formValid = computed(() => (
  description.value.trim().length >= 1
  && description.value.trim().length <= 128
  && buyer.value.trim().length >= 1
  && buyer.value.trim().length <= 200
  && amountKopecks.value >= Number(config.value.min_amount || 0)
  && amountKopecks.value <= Number(config.value.max_amount || 0)
))
const limitsLabel = computed(() => (
  `От ${formatLimit(config.value.min_amount)} до ${formatLimit(config.value.max_amount)} ₽`
))
const badgeLabel = computed(() => unseenCount.value > 99 ? '99+' : String(unseenCount.value))
const historyPageCount = computed(() => Math.max(1, Math.ceil(historyTotal.value / historyPageSize)))
const historyRangeLabel = computed(() => {
  // Показываем диапазон текущей серверной страницы без перечисления всех операций в браузере.
  if (!historyTotal.value) return 'Нет операций'
  const first = (historyPage.value - 1) * historyPageSize + 1
  const last = Math.min(historyPage.value * historyPageSize, historyTotal.value)
  return `${first}–${last} из ${historyTotal.value}`
})

function formatRubles(kopecks) {
  // Форматируем сумму из копеек одинаково в QR и истории.
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 2 })
    .format(Number(kopecks || 0) / 100)
}

function formatLimit(kopecks) {
  // Для подсказки лимита убираем лишние нули у целых рублей.
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(kopecks || 0) / 100)
}

function formatDate(value) {
  // Показываем локальные дату и время без технического ISO-формата.
  if (!value) return '—'
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function statusLabel(state) {
  // Переводим внутреннее состояние в короткий статус оператора.
  return ({
    created: 'Создаётся',
    init_pending: 'Создаётся',
    init_unknown: 'Уточняется',
    pending: 'Ожидает оплату',
    confirmed: 'Оплачен',
    rejected: 'Отклонён',
    expired: 'Истёк',
    cancelled: 'Отменён',
    failed: 'Ошибка',
  })[state] || 'Уточняется'
}

function isFinished(state) {
  // Отделяем финальные состояния, для которых QR больше не нужен.
  return ['confirmed', 'rejected', 'expired', 'cancelled', 'failed'].includes(String(state || ''))
}

async function loadConfig() {
  // Загружаем серверные лимиты и kill switch, не дублируя их в интерфейсе.
  if (!token.value) return
  try {
    config.value = await apiGet('/payments/tbank/sbp/config', { token: token.value })
  } catch (requestError) {
    config.value.enabled = false
    error.value = requestError?.message || 'Не удалось загрузить настройки СБП'
  } finally {
    configLoaded.value = true
  }
}

function addPaymentToast(payment) {
  // Уведомляем о новой оплате и автоматически убираем toast, не помечая историю просмотренной.
  const id = `${payment.id}-${Date.now()}`
  toasts.value.push({ id, payment })
  window.setTimeout(() => {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }, 8000)
}

async function refreshActivePayment() {
  // Точечно перечитываем открытый QR, чтобы увидеть статус и повторно получить изображение после краткой ошибки.
  if (!activePayment.value?.id || isFinished(activePayment.value.state)) return
  try {
    activePayment.value = await apiGet(`/payments/tbank/sbp/${encodeURIComponent(activePayment.value.id)}`, { token: token.value })
  } catch {
    // Общая история и серверная сверка продолжат работу после временной ошибки сети.
  }
}

async function loadHistory({ notify = true } = {}) {
  // Последний запрос побеждает предыдущий, поэтому ручное обновление не теряется на фоне polling.
  if (!token.value) return
  const requestId = ++historyRequestSequence
  historyLoading.value = true
  historyError.value = ''
  try {
    const query = new URLSearchParams({
      limit: String(historyPageSize),
      offset: String((historyPage.value - 1) * historyPageSize),
      mine: mineOnly.value ? 'true' : 'false',
    })
    if (appliedHistorySearch.value) query.set('q', appliedHistorySearch.value)
    if (historyState.value) query.set('state', historyState.value)
    const response = await apiGet(`/payments/tbank/sbp?${query.toString()}`, { token: token.value })
    if (requestId !== historyRequestSequence) return
    const items = Array.isArray(response?.items) ? response.items : []
    if (historyInitialized && notify) {
      for (const payment of items) {
        if (payment.state === 'confirmed' && !knownConfirmedIds.has(payment.id)) addPaymentToast(payment)
      }
    }
    for (const payment of items) {
      if (payment.state === 'confirmed') knownConfirmedIds.add(payment.id)
    }
    historyInitialized = true
    payments.value = items
    historyTotal.value = Number(response?.total || 0)
    unseenCount.value = Number(response?.unseen_confirmed_count || 0)
    if (activePayment.value) {
      const updated = items.find((item) => item.id === activePayment.value.id)
      if (updated) activePayment.value = updated
    }
  } catch (requestError) {
    if (requestId === historyRequestSequence) {
      historyError.value = requestError?.message || 'Не удалось загрузить историю платежей'
    }
  } finally {
    if (requestId === historyRequestSequence) historyLoading.value = false
  }
}

async function refreshHistory() {
  // Ручная кнопка всегда запускает свежий запрос и показывает только свою короткую анимацию.
  if (manualRefreshing.value) return
  manualRefreshing.value = true
  try {
    await loadHistory({ notify: false })
  } finally {
    manualRefreshing.value = false
  }
}

async function applyHistorySearch() {
  // Применяем поиск по Enter или кнопке и возвращаемся на первую страницу результата.
  appliedHistorySearch.value = historySearch.value.trim()
  historyPage.value = 1
  await loadHistory({ notify: false })
}

async function clearHistorySearch() {
  // Очищаем видимый и применённый запрос одним действием.
  historySearch.value = ''
  appliedHistorySearch.value = ''
  historyPage.value = 1
  await loadHistory({ notify: false })
}

async function applyHistoryFilters() {
  // Любая смена статуса начинает выборку с первой страницы.
  historyPage.value = 1
  await loadHistory({ notify: false })
}

async function goToHistoryPage(page) {
  // Загружаем только допустимую серверную страницу и сохраняем текущие фильтры.
  const nextPage = Math.min(Math.max(1, Number(page) || 1), historyPageCount.value)
  if (nextPage === historyPage.value) return
  historyPage.value = nextPage
  await loadHistory({ notify: false })
}

async function pollPayments() {
  // Один общий polling поддерживает историю всех сотрудников и не зависит от открытой модалки.
  await Promise.all([loadHistory(), refreshActivePayment()])
}

async function createPayment() {
  // Создаём отдельную операцию; закрытие формы после ответа никак её не отменяет.
  if (!formValid.value || !config.value.enabled || busy.value) return
  busy.value = true
  error.value = ''
  try {
    activePayment.value = await apiPost('/payments/tbank/sbp', {
      description: description.value.trim(),
      buyer: buyer.value.trim(),
      amount: amountKopecks.value,
    }, { token: token.value })
    await loadHistory({ notify: false })
  } catch (requestError) {
    error.value = requestError?.message || 'Не удалось сформировать QR-код'
  } finally {
    busy.value = false
  }
}

function startAnother() {
  // Очищаем форму, а предыдущий платёж оставляем в долговечной общей истории.
  activePayment.value = null
  description.value = defaultDescription
  buyer.value = ''
  amount.value = ''
  error.value = ''
  tab.value = 'new'
}

function openCenter() {
  // Открываем новую форму, не меняя статус уже созданных операций.
  open.value = true
  tab.value = 'new'
  error.value = ''
}

function closeCenter() {
  // Закрытие — только действие интерфейса; webhook и reconciliation продолжаются на сервере.
  open.value = false
}

async function openHistory() {
  // При явном просмотре истории снимаем персональный badge подтверждённых оплат.
  tab.value = 'history'
  await loadHistory({ notify: false })
  try {
    await apiPost('/payments/tbank/sbp/mark-seen', {}, { token: token.value })
    unseenCount.value = 0
    payments.value = payments.value.map((payment) => payment.state === 'confirmed' ? { ...payment, is_seen: true } : payment)
  } catch {
    // Не скрываем историю, если отметка просмотра временно не сохранилась.
  }
}

async function setScope(value) {
  // Переключаем общие и собственные операции без смены прав доступа.
  mineOnly.value = Boolean(value)
  historyPage.value = 1
  await loadHistory({ notify: false })
}

function showPayment(payment) {
  // Открываем платёж из toast и оставляем пользователю доступ к его QR или результату.
  activePayment.value = payment
  tab.value = 'new'
  open.value = true
}

function qrDataUrlBlob(dataUrl) {
  // Превращаем банковский data URL в файл, потому что Safari не скачивает такие ссылки напрямую.
  const separator = dataUrl.indexOf(',')
  if (separator < 0) throw new Error('Некорректный формат QR-кода')
  const header = dataUrl.slice(0, separator)
  const payload = dataUrl.slice(separator + 1)
  const mimeType = header.match(/^data:([^;,]+)/i)?.[1] || 'image/svg+xml'
  const bytes = /;base64/i.test(header)
    ? Uint8Array.from(window.atob(payload), (character) => character.charCodeAt(0))
    : new TextEncoder().encode(decodeURIComponent(payload))
  return new Blob([bytes], { type: mimeType })
}

function downloadQr(payment) {
  // Скачиваем QR через blob URL, а после старта загрузки освобождаем память браузера.
  if (!payment?.qr_data_url) return
  try {
    const objectUrl = URL.createObjectURL(qrDataUrlBlob(payment.qr_data_url))
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = `sbp-${payment.order_id || payment.id}.svg`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000)
  } catch {
    error.value = 'Не удалось скачать QR-код. Попробуйте сформировать его повторно.'
  }
}

function onKeydown(event) {
  // Escape закрывает только интерфейс и не прерывает банковскую операцию.
  if (open.value && event.key === 'Escape') closeCenter()
}

watch(token, async (nextToken) => {
  // После смены авторизации начинаем с новой персональной отметки просмотров.
  if (!nextToken) return
  historyInitialized = false
  knownConfirmedIds.clear()
  await Promise.all([loadConfig(), loadHistory({ notify: false })])
})

onMounted(async () => {
  // Компонент живёт в шапке, поэтому polling работает на любой вкладке CRM.
  window.addEventListener('keydown', onKeydown)
  if (token.value) await Promise.all([loadConfig(), loadHistory({ notify: false })])
  pollTimer = window.setInterval(pollPayments, 10_000)
})

onBeforeUnmount(() => {
  // Останавливаем только браузерный polling; серверный worker остаётся активным.
  window.removeEventListener('keydown', onKeydown)
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.sbp-center { display: inline-flex; flex: 0 0 auto; }
.sbp-center__trigger {
  position: relative; display: inline-flex; align-items: center; gap: 7px; min-height: 42px; padding: 0 12px;
  border: 1px solid rgba(62, 232, 181, .42); border-radius: 12px; color: #7df0d0; cursor: pointer;
  background: linear-gradient(180deg, rgba(62, 232, 181, .14), rgba(20, 42, 55, .45));
  box-shadow: inset 0 1px rgba(255,255,255,.1), 0 7px 20px rgba(3,8,20,.24); font: inherit; font-weight: 800;
}
.sbp-center__trigger:hover { border-color: rgba(62,232,181,.8); color: #b8ffe9; transform: translateY(-1px); }
.sbp-center__trigger svg, .sbp-primary svg { width: 21px; height: 21px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.sbp-center__badge { min-width: 19px; height: 19px; padding: 0 5px; display: inline-grid; place-items: center; border-radius: 99px; background: #ff7167; color: #101527; font-size: 10px; }
.sbp-backdrop { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center; padding: 20px; background: rgba(2,6,18,.78); backdrop-filter: blur(12px); }
.sbp-modal { width: min(720px, calc(100vw - 32px)); max-height: min(760px, calc(100vh - 32px)); overflow: hidden; display: flex; flex-direction: column; color: #eef2ff; border: 1px solid rgba(115,143,208,.42); border-radius: 22px; background: radial-gradient(620px 220px at 100% 0, rgba(62,232,181,.13), transparent 65%), linear-gradient(150deg, #111934, #080e20 74%); box-shadow: 0 28px 80px rgba(0,0,0,.52); }
.sbp-modal__head { display: flex; align-items: center; gap: 12px; padding: 18px 22px 14px; }
.sbp-modal__head h2 { margin: 1px 0 0; font-size: 23px; line-height: 1.05; letter-spacing: -.03em; }
.sbp-modal__eyebrow { color: #55e9bd; font-size: 10px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
.sbp-modal__brand { width: 42px; height: 42px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 13px; color: #59ebc1; background: rgba(62,232,181,.1); border: 1px solid rgba(62,232,181,.28); }
.sbp-modal__brand svg { width: 23px; fill: none; stroke: currentColor; stroke-width: 1.7; }
.sbp-modal__close { margin-left: auto; width: 36px; height: 36px; flex: 0 0 auto; display: grid; place-items: center; padding: 0; border-radius: 11px; border: 1px solid rgba(255,255,255,.16); background: rgba(255,255,255,.04); color: #bdc9e7; cursor: pointer; }
.sbp-modal__close:hover { border-color: rgba(255,255,255,.3); background: rgba(255,255,255,.08); color: #eef2ff; }
.sbp-modal__close svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; }
.sbp-tabs { display: flex; gap: 7px; padding: 0 22px 13px; border-bottom: 1px solid rgba(255,255,255,.1); }
.sbp-tabs button, .sbp-scope button { display: inline-flex; align-items: center; gap: 7px; border: 0; border-radius: 9px; padding: 8px 12px; background: rgba(255,255,255,.05); color: #9eaccd; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; }
.sbp-tabs button.is-active, .sbp-scope button.is-active { background: rgba(62,232,181,.14); color: #72efca; }
.sbp-tabs button span { min-width: 18px; height: 18px; display: inline-grid; place-items: center; border-radius: 99px; background: #ff7167; color: #101527; font-size: 10px; }
.sbp-modal__content { min-height: 0; flex: 1 1 auto; overflow-y: auto; padding: 18px 22px 22px; }
.sbp-form { display: grid; gap: 14px; max-width: 620px; margin: 0 auto; }
.sbp-form__row { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(180px, .85fr); gap: 12px; align-items: start; }
.sbp-field { min-width: 0; display: grid; grid-template-rows: auto 44px auto; gap: 6px; }
.sbp-field__head { min-height: 18px; display: flex; align-items: baseline; justify-content: space-between; gap: 12px; color: #dfe7fa; }
.sbp-field__head b { font-size: 12px; font-weight: 800; }
.sbp-field__head small { color: #667596; font-size: 9px; font-variant-numeric: tabular-nums; }
.sbp-field input { width: 100%; height: 44px; box-sizing: border-box; border: 1px solid rgba(140,160,211,.28); border-radius: 12px; padding: 0 14px; outline: none; background: rgba(4,9,24,.62); color: #f4f7ff; font: inherit; font-size: 14px; transition: border-color .16s ease, box-shadow .16s ease, background .16s ease; }
.sbp-field input::placeholder { color: #7884a1; }
.sbp-field input:focus { border-color: #55e9bd; box-shadow: 0 0 0 3px rgba(62,232,181,.1); }
.sbp-field__hint { min-height: 14px; color: #7f8dad; font-size: 10px; line-height: 1.35; }
.sbp-amount { height: 44px; display: flex; align-items: center; border: 1px solid rgba(140,160,211,.28); border-radius: 12px; background: rgba(4,9,24,.62); transition: border-color .16s ease, box-shadow .16s ease, background .16s ease; }
.sbp-amount:focus-within { border-color: #55e9bd; box-shadow: 0 0 0 3px rgba(62,232,181,.1); }
.sbp-amount input { height: 42px; border: 0; background: transparent; box-shadow: none !important; font-size: 19px; font-weight: 800; font-variant-numeric: tabular-nums; }
.sbp-amount b { padding-right: 14px; color: #8f9cbd; font-size: 17px; }
.sbp-form__notice { min-height: 34px; display: flex; align-items: center; gap: 8px; margin: -2px 0 0; padding: 8px 10px; border: 1px solid rgba(108,133,190,.14); border-radius: 10px; background: rgba(92,115,170,.055); color: #8190b1; font-size: 10px; line-height: 1.35; }
.sbp-form__notice svg { width: 15px; height: 15px; flex: 0 0 auto; fill: none; stroke: #58dcb8; stroke-width: 1.7; stroke-linecap: round; }
.sbp-form > .sbp-primary { margin-top: 2px; }
.sbp-primary, .sbp-secondary { border-radius: 12px; font: inherit; font-weight: 800; cursor: pointer; }
.sbp-primary { min-height: 46px; display: flex; align-items: center; justify-content: center; gap: 9px; border: 0; background: linear-gradient(135deg, #47e7ba, #8df3d3); color: #071427; box-shadow: 0 12px 30px rgba(62,232,181,.16); }
.sbp-primary:disabled { cursor: not-allowed; filter: saturate(.2); opacity: .55; }
.sbp-primary--compact { min-height: 42px; padding: 0 18px; }
.sbp-secondary { min-height: 42px; padding: 0 16px; border: 1px solid rgba(151,168,211,.28); background: rgba(255,255,255,.04); color: #cbd5ef; }
.sbp-message { margin: 0; padding: 10px 12px; border-radius: 11px; font-size: 12px; }
.sbp-message--warning { color: #ffd58c; background: rgba(247,185,85,.1); border: 1px solid rgba(247,185,85,.24); }
.sbp-message--error { color: #ffb5bd; background: rgba(255,92,111,.09); border: 1px solid rgba(255,92,111,.24); }
.sbp-payment { max-width: 680px; margin: 0 auto; display: grid; gap: 12px; }
.sbp-payment__summary { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.sbp-payment__summary > strong { font-size: 24px; }
.sbp-status { display: inline-flex; align-items: center; gap: 8px; color: #c4cee7; font-size: 12px; font-weight: 800; }
.sbp-status i { width: 8px; height: 8px; border-radius: 50%; background: #62a9ff; box-shadow: 0 0 0 4px rgba(98,169,255,.1); }
.sbp-status--confirmed { color: #72efca; }.sbp-status--confirmed i { background: #49dfb4; }
.sbp-status--rejected, .sbp-status--expired, .sbp-status--cancelled, .sbp-status--failed { color: #ffb0ba; }
.sbp-status--rejected i, .sbp-status--expired i, .sbp-status--cancelled i, .sbp-status--failed i { background: #ff6d7e; }
.sbp-payment__details { display: grid; grid-template-columns: 1.45fr 1fr .85fr; gap: 8px; margin: 0; }
.sbp-payment__details div { min-width: 0; padding: 9px 10px; border-radius: 10px; background: rgba(255,255,255,.04); }
.sbp-payment__details dt { color: #7583a5; font-size: 10px; text-transform: uppercase; }
.sbp-payment__details dd { margin: 3px 0 0; overflow-wrap: anywhere; font-size: 13px; line-height: 1.25; font-weight: 700; }
.sbp-qr { display: grid; justify-items: center; gap: 8px; padding: 12px 14px; border: 1px solid rgba(62,232,181,.24); border-radius: 16px; background: rgba(62,232,181,.05); }
.sbp-qr img { width: min(220px, 62vw); aspect-ratio: 1; padding: 9px; border-radius: 11px; background: #fff; }
.sbp-qr p { margin: 0; max-width: 100%; text-align: center; color: #9aa8c8; font-size: 11px; line-height: 1.3; }
.sbp-result { min-height: 230px; display: grid; place-items: center; align-content: center; gap: 12px; border-radius: 20px; background: rgba(255,255,255,.035); }
.sbp-result span { width: 64px; height: 64px; display: grid; place-items: center; border-radius: 50%; font-size: 32px; font-weight: 900; }
.sbp-result--success span { background: #53e3ba; color: #071427; }.sbp-result--failure span { background: #f7b955; color: #071427; }
.sbp-payment__actions { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.sbp-payment__actions .sbp-primary, .sbp-payment__actions .sbp-secondary { min-height: 38px; }
.sbp-history { min-height: 360px; }
.sbp-history__toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.sbp-scope { display: flex; gap: 6px; }
.sbp-refresh { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 36px; padding: 0 12px; font-size: 11px; }
.sbp-refresh svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.sbp-refresh.is-refreshing svg { animation: sbp-spin .7s linear infinite; }
.sbp-refresh:disabled { cursor: wait; opacity: .72; }
.sbp-history__filters { display: grid; grid-template-columns: minmax(0,1fr) 176px; gap: 8px; margin-bottom: 10px; }
.sbp-search { min-width: 0; display: flex; align-items: center; min-height: 38px; overflow: hidden; border: 1px solid rgba(140,160,211,.24); border-radius: 10px; background: rgba(4,9,24,.48); }
.sbp-search:focus-within { border-color: rgba(62,232,181,.56); box-shadow: 0 0 0 3px rgba(62,232,181,.07); }
.sbp-search input { min-width: 0; flex: 1 1 auto; padding: 0 11px; border: 0; outline: 0; background: transparent; color: #e8edfc; font: inherit; font-size: 11px; }
.sbp-search input::-webkit-search-cancel-button { display: none; }
.sbp-search__clear, .sbp-search__submit { flex: 0 0 auto; display: grid; place-items: center; border: 0; background: transparent; color: #7887a8; cursor: pointer; }
.sbp-search__clear { width: 28px; height: 28px; font-size: 18px; }
.sbp-search__submit { width: 38px; height: 38px; border-left: 1px solid rgba(140,160,211,.15); color: #62e9c1; }
.sbp-search__submit:hover, .sbp-search__clear:hover { color: #b9ffe9; background: rgba(62,232,181,.06); }
.sbp-search__submit svg { width: 15px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }
.sbp-state-filter { min-width: 0; display: flex; align-items: center; gap: 7px; min-height: 38px; padding: 0 9px; border: 1px solid rgba(140,160,211,.24); border-radius: 10px; background: rgba(4,9,24,.48); }
.sbp-state-filter span { color: #697897; font-size: 8px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.sbp-state-filter select { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: #cbd5ef; font: inherit; font-size: 10px; font-weight: 700; cursor: pointer; }
.sbp-history__empty { padding: 70px 20px; text-align: center; color: #8090b3; border: 1px dashed rgba(151,168,211,.22); border-radius: 16px; }
.sbp-history__list { max-height: 350px; display: grid; gap: 0; border: 1px solid rgba(151,168,211,.17); border-radius: 13px; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; scrollbar-color: rgba(83,232,190,.35) transparent; background: rgba(255,255,255,.02); }
.sbp-history__columns, .sbp-history-row { display: grid; grid-template-columns: 92px minmax(160px,1fr) 106px 78px 72px; align-items: center; gap: 10px; }
.sbp-history__columns { position: sticky; top: 0; z-index: 2; min-height: 28px; padding: 0 12px; color: #657493; background: #10172d; box-shadow: 0 1px rgba(151,168,211,.12); font-size: 8px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.sbp-history-row { min-width: 0; padding: 10px 12px; border-top: 1px solid rgba(151,168,211,.12); }
.sbp-history-row:hover { background: rgba(255,255,255,.035); }
.sbp-history-row__main, .sbp-history-row__meta { min-width: 0; display: grid; gap: 3px; }
.sbp-history-row .sbp-status { gap: 6px; font-size: 10px; }
.sbp-history-row .sbp-status i { width: 7px; height: 7px; }
.sbp-history-row__main h3 { margin: 0; overflow: hidden; color: #dfe6f8; font-size: 10.5px; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap; }
.sbp-history-row__main p { margin: 0; overflow: hidden; color: #8795b5; font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
.sbp-history-row__meta b { overflow: hidden; color: #aeb9d3; font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
.sbp-history-row__meta time { color: #6f7d9c; font-size: 8px; white-space: nowrap; }
.sbp-history-row__amount { color: #e8edfc; font-size: 10.5px; text-align: right; white-space: nowrap; }
.sbp-history-row__open { min-height: 30px; padding: 0 8px; border: 1px solid rgba(62,232,181,.2); border-radius: 8px; background: rgba(62,232,181,.07); color: #65e9c1; font: inherit; font-size: 10px; font-weight: 800; cursor: pointer; }
.sbp-history-row__open:hover { border-color: rgba(62,232,181,.42); background: rgba(62,232,181,.12); }
.sbp-pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 9px; color: #7180a1; font-size: 9px; }
.sbp-pagination div { display: flex; align-items: center; gap: 6px; }
.sbp-pagination b { min-width: 48px; color: #9eaccb; text-align: center; font-size: 9px; }
.sbp-pagination button { width: 28px; height: 28px; display: grid; place-items: center; padding: 0; border: 1px solid rgba(140,160,211,.22); border-radius: 8px; background: rgba(255,255,255,.035); color: #cbd5ef; font: inherit; font-size: 17px; cursor: pointer; }
.sbp-pagination button:hover:not(:disabled) { border-color: rgba(62,232,181,.42); color: #6debc6; }
.sbp-pagination button:disabled { cursor: not-allowed; opacity: .3; }
.sbp-toasts { position: fixed; z-index: 1100; right: 22px; bottom: 22px; display: grid; gap: 10px; }
.sbp-toasts button { width: min(360px, calc(100vw - 32px)); display: flex; align-items: center; gap: 12px; padding: 14px; border: 1px solid rgba(62,232,181,.38); border-radius: 15px; background: #101a32; color: #eff5ff; box-shadow: 0 18px 50px rgba(0,0,0,.42); text-align: left; cursor: pointer; }
.sbp-toasts button > span { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 50%; background: #50e3b9; color: #071427; font-weight: 900; }
.sbp-toasts div { display: grid; gap: 2px; }.sbp-toasts small { color: #9ba9c9; }
.sbp-fade-enter-active, .sbp-fade-leave-active, .sbp-toast-enter-active, .sbp-toast-leave-active { transition: opacity .18s ease, transform .18s ease; }
.sbp-fade-enter-from, .sbp-fade-leave-to, .sbp-toast-enter-from, .sbp-toast-leave-to { opacity: 0; transform: translateY(8px); }
@keyframes sbp-spin { to { transform: rotate(360deg); } }
@media (max-width: 700px) {
  .sbp-backdrop { padding: 0; align-items: end; }
  .sbp-modal { width: 100%; max-height: 94svh; border-radius: 24px 24px 0 0; }
  .sbp-modal__head, .sbp-modal__content { padding-left: 16px; padding-right: 16px; }
  .sbp-tabs { padding-left: 16px; padding-right: 16px; }
  .sbp-form__row { grid-template-columns: 1fr; gap: 14px; }
  .sbp-payment__details { grid-template-columns: 1fr; }
  .sbp-history__filters { grid-template-columns: 1fr; }
  .sbp-history__columns { display: none; }
  .sbp-history-row { grid-template-columns: 1fr auto; gap: 8px 12px; }
  .sbp-history-row .sbp-status, .sbp-history-row__main { grid-column: 1; }
  .sbp-history-row__meta { grid-column: 1; grid-template-columns: auto 1fr; }
  .sbp-history-row__amount { grid-column: 2; grid-row: 1; }
  .sbp-history-row__open { grid-column: 2; grid-row: 2 / span 2; align-self: stretch; }
  .sbp-qr img { width: min(210px, 64vw); }
  .sbp-center__trigger span:not(.sbp-center__badge) { display: none; }
  .sbp-center__trigger { padding: 0 10px; }
}
</style>
