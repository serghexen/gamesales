<template>
  <WorkAirpayDialog :title="selectedTransaction || selectedBatch ? 'Детали операции Airpay' : 'История покупок Airpay'" history :busy="busy" @close="emit('close')">
    <div class="airpay-history">
      <p v-if="loading" class="muted" role="status">Загружаем историю…</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="exporting" class="muted" role="status">Готовим Excel…</p>
      <template v-if="selectedTransaction || selectedBatch">
        <button ref="backButton" class="ghost airpay-history-back" type="button" :disabled="busy || loading" @click="closeDetails">← Вернуться к истории</button>
        <template v-if="selectedBatch">
          <WorkAirpayBatch :batch="selectedBatch" :token="token" @busy-change="setBusy('batch', $event)" />
        </template>
        <template v-else>
          <button v-if="selectedTransaction.batch && !archive" class="ghost airpay-history-back" type="button" :disabled="busy || loading" @click="openBatch(selectedTransaction)">Открыть покупку {{ selectedTransaction.batch.quantity }} ключей</button>
          <WorkAirpayTransaction :transaction="selectedTransaction" :token="token" :archive="archive" @busy-change="setBusy('transaction', $event)" @updated="updateTransaction" />
        </template>
      </template>
      <template v-else>
        <template v-if="!busy">
          <div v-if="legacyAvailable" class="airpay-history-sources" role="group" aria-label="Источник истории">
            <button class="ghost" :class="{ 'is-active': !archive }" :aria-pressed="!archive" type="button" :disabled="loading" @click="changeSource(false)">Поставщик<small>Новые операции Airpay</small></button>
            <button class="ghost" :class="{ 'is-active': archive }" :aria-pressed="archive" type="button" :disabled="loading" @click="changeSource(true)">Архив CRM<small>Локальные операции · только чтение</small></button>
          </div>
          <form class="airpay-history-filters" @submit.prevent="applyFilters">
            <label class="field"><span class="label">Дата с (МСК)</span><input v-model="draft.date_from" class="input" type="date" :disabled="loading" /></label>
            <label class="field"><span class="label">Дата по (МСК)</span><input v-model="draft.date_to" class="input" type="date" :min="draft.date_from || undefined" :disabled="loading" /></label>
            <label class="field"><span class="label">Статус</span><select v-model="draft.status" class="input" :disabled="loading"><option value="">Все статусы</option><option v-for="option in statuses" :key="option[0]" :value="option[0]">{{ option[1] }}</option></select></label>
            <label class="field"><span class="label">Вид покупки</span><select v-model="draft.kind" class="input" :disabled="loading"><option value="">Все виды</option><option value="voucher">Ваучер</option><option value="topup">Пополнение</option></select></label>
            <label class="field airpay-history-search"><span class="label">Поиск</span><input v-model="draft.q" class="input" type="search" maxlength="200" :disabled="loading" placeholder="Услуга, аккаунт или ID операции" /></label>
            <button class="btn" type="submit" :disabled="loading">Показать</button>
            <button class="btn" type="button" :disabled="loading || !items.length" @click="downloadHistory">Выгрузить Excel</button>
            <button class="ghost" type="button" :disabled="loading" @click="resetFilters">Сбросить</button>
          </form>
        </template>
        <div class="airpay-history-cards" aria-label="Итоги текущей страницы">
          <div class="mini"><div class="mini__label">Операций на странице</div><div class="mini__value">{{ items.length }}</div></div>
          <div class="mini"><div class="mini__label">Оплачено на странице</div><div class="mini__value">{{ paidOnPage }}</div></div>
        </div>
        <div ref="tableArea" class="table-wrap airpay-history-table">
          <table class="table table--compact">
            <thead><tr><th>Название сервиса</th><th>Вид покупки</th><th>Цена</th><th>Статус</th><th>Результат</th><th>Дата (МСК) ↓</th></tr></thead>
            <tbody>
              <tr v-if="!loading && !items.length"><td colspan="6" class="muted">По выбранным условиям операций нет.</td></tr>
              <tr v-for="item in items" :key="item.agent_transaction_id" class="airpay-history-row" @click="openTransaction(item)">
                <td><button class="airpay-history-service" :data-operation-id="item.agent_transaction_id" type="button" :disabled="busy || loading" aria-label="Открыть детали операции" @click.stop="openTransaction(item)">{{ item.service_title || item.service_id || 'Без названия' }}</button></td>
                <td>{{ item.purchase_kind === 'voucher' ? 'Ваучер' : 'Пополнение' }}</td>
                <td class="airpay-history-price">{{ money(item.amount, item.currency) }}</td>
                <td><span class="airpay-history-state" :class="stateTone(item)">{{ stateLabel(item) }}</span></td>
                <td>{{ item.result_available ? 'Код сохранён' : item.state === 'paid' && item.purchase_kind === 'topup' ? 'Пополнено' : '—' }}</td>
                <td class="airpay-history-date">{{ dateLabel(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <nav aria-label="Страницы истории Airpay"><span>{{ items.length ? `Показаны ${page * 20 + 1}–${page * 20 + items.length}` : 'Нет операций' }} · Страница {{ page + 1 }}</span><div class="airpay-history-actions"><button class="ghost" type="button" :disabled="busy || loading || page === 0" @click="changePage(-1)">Назад</button><button class="ghost" type="button" :disabled="busy || loading || !hasNext" @click="changePage(1)">Далее</button></div></nav>
        <p class="airpay-history-note">Нажмите на строку, чтобы открыть ID транзакций, ответ Airpay и действия по операции. Сохранённый код открывается отдельной кнопкой в деталях.</p>
        <WorkAirpayQueue v-if="!archive" :token="token" :blocked="busy || loading" @open="openBatch({ agent_transaction_id: $event })" />
        <p class="airpay-history-note">Excel: все операции по применённым фильтрам, до 10 000 строк. Коды ваучеров не выгружаются.</p>
      </template>
    </div>
  </WorkAirpayDialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { apiGet, apiGetFile } from '../../../api/http'
import WorkAirpayQueue from './WorkAirpayQueue.vue'
import WorkAirpayDialog from './WorkAirpayDialog.vue'
import WorkAirpayBatch from './WorkAirpayBatch.vue'
import WorkAirpayTransaction from './WorkAirpayTransaction.vue'
const props = defineProps({ token: { type: String, default: '' } })
const emit = defineEmits(['close', 'busy-change'])
const statuses = [['requires_attention', 'Требует разбора'], ['processing', 'Исход оплаты неизвестен'],
  ['awaiting_voucher', 'Оплачен · ожидает кода'], ['completed', 'Завершена'], ['paid', 'Все оплаченные'],
  ['prepared', 'Подготовка'], ['checking', 'Проверяется'], ['check_pending', 'Ожидает проверки'],
  ['check_failed', 'Проверка не пройдена'], ['checked', 'Проверен'], ['failed', 'Отказ в оплате']]
const emptyFilters = { q: '', status: '', kind: '', date_from: '', date_to: '' }
const draft = reactive({ ...emptyFilters })
const applied = ref({ ...emptyFilters })
const exporting = ref(false)
const items = ref([])
const archive = ref(false)
const legacyAvailable = ref(false)
const selectedBatch = ref(null)
const selectedTransaction = ref(null)
const backButton = ref(null)
const tableArea = ref(null)
let detailId = ''
const page = ref(0)
const hasNext = ref(false)
const loading = ref(false)
const error = ref('')
const active = reactive(new Set())
const busy = computed(() => active.size > 0)
let version = 0
function money(value, currency) {
  // Отсутствующую цену не выдаём за ноль, валюту берём из сохранённой операции.
  if (value === '' || value == null || !Number.isFinite(Number(value))) return '—'
  return `${Number(value).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency || ''}`.trim()
}
function dateLabel(value) {
  // Даты совпадают с московским часовым поясом фильтров журнала.
  return value ? new Date(value).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow', dateStyle: 'short', timeStyle: 'short' }) : '—'
}
function stateLabel(item) {
  // Проверенные, но неоплаченные операции нельзя обозначать как успешную покупку.
  if (item.requires_attention) return 'Требует разбора'
  if (item.state === 'paid') return item.purchase_kind === 'voucher' && !item.result_available ? 'Оплачено · ожидается код' : 'Выполнено'
  return { prepared: 'Подготовка', checking: 'Проверяется', check_pending: 'Ожидает проверки', check_failed: 'Проверка отклонена', checked: 'Проверена, не оплачена', processing: 'Исход оплаты неизвестен', failed: 'Оплата отклонена' }[item.state] || 'Статус неизвестен'
}
function stateTone(item) {
  // Цвет дополняет точный статус, не скрывая незавершённые и спорные операции.
  if (item.requires_attention || ['failed', 'check_failed'].includes(item.state)) return 'is-failed'
  return item.state === 'paid' && (item.purchase_kind === 'topup' || item.result_available) ? 'is-succeeded' : 'is-pending'
}
const paidOnPage = computed(() => {
  // API пока не возвращает общие итоги; складываем только оплаченные строки текущей страницы по валютам.
  const totals = new Map()
  for (const item of items.value) {
    if (item.state !== 'paid' || !item.currency || item.amount === '' || item.amount == null || !Number.isFinite(Number(item.amount))) continue
    totals.set(item.currency, (totals.get(item.currency) || 0) + Number(item.amount))
  }
  return [...totals].map(([currency, value]) => money(value, currency)).join(' · ') || '—'
})
function changeSource(value) {
  // Сохраняем фильтры при переключении источника, возвращая первую страницу.
  if (busy.value || loading.value || archive.value === value) return
  archive.value = value
  page.value = 0
  void load()
}
async function openTransaction(item) {
  // Клик читает только сохранённую операцию; код и запросы поставщику здесь не вызываются.
  if (busy.value || loading.value) return
  detailId = item.agent_transaction_id
  const revision = ++version
  loading.value = true
  error.value = ''
  try {
    const value = await apiGet(`/integrations/airpay/${archive.value ? 'legacy/' : ''}transactions/${item.agent_transaction_id}`, { token: props.token })
    if (revision !== version) return
    selectedTransaction.value = value
    loading.value = false
    await nextTick()
    backButton.value?.focus()
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось открыть операцию'
  } finally { if (revision === version) loading.value = false }
}
async function closeDetails() {
  // Возвращаем таблицу без потери фильтров и страницы; раскрытый код остаётся только в карточке.
  if (busy.value || loading.value) return
  selectedTransaction.value = null
  selectedBatch.value = null
  await nextTick()
  const buttons = [...(tableArea.value?.querySelectorAll('button') || [])]
  const trigger = buttons.find(button => button.dataset.operationId === detailId) || buttons[0]
  trigger?.focus()
}
function updateTransaction(value) {
  // Синхронизируем статус в таблице, но не сохраняем в ней раскрытый код ваучера.
  const { pin_code: ignoredCode, ...safe } = value
  void ignoredCode
  items.value = items.value.map(item => item.agent_transaction_id === safe.agent_transaction_id ? safe : item)
}
function setBusy(id, value) {
  // Несколько карточек удерживают общую блокировку независимо друг от друга.
  if (value) active.add(id); else active.delete(id)
  emit('busy-change', busy.value)
}
function filterQuery() {
  // Страницы и Excel используют применённый поиск, а не ещё не отправленные поля формы.
  const params = new URLSearchParams(Object.entries(applied.value).filter(([, value]) => value))
  if (archive.value) params.set('archive', 'crm')
  return params.size ? `&${params}` : ''
}
function applyFilters() {
  // Новый поиск начинается с первой страницы и не прерывает текущую операцию.
  if (loading.value || busy.value) return
  applied.value = { ...draft, q: draft.q.trim() }
  page.value = 0
  void load()
}
function resetFilters() {
  // Сброс очищает условия, сохраняя выбранный источник журнала.
  if (loading.value || busy.value) return
  Object.assign(draft, emptyFilters)
  applyFilters()
}
async function downloadHistory() {
  // Выгружаем сохранённые операции; поздний ответ другого сеанса не скачивается.
  if (loading.value || busy.value) return
  const revision = version
  const lock = Symbol('export')
  exporting.value = true
  error.value = ''
  setBusy(lock, true)
  try {
    const query = filterQuery().slice(1)
    const blob = await apiGetFile(`/integrations/airpay/transactions/export${query ? `?${query}` : ''}`, { token: props.token })
    if (revision !== version) return
    const url = URL.createObjectURL(blob)
    try {
      const link = document.createElement('a')
      link.href = url
      link.download = archive.value ? 'airpay-crm-archive.xlsx' : 'airpay-history.xlsx'
      document.body.appendChild(link)
      link.click()
      link.remove()
    } finally { URL.revokeObjectURL(url) }
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось выгрузить историю Airpay'
  } finally {
    if (revision === version) exporting.value = false
    setBusy(lock, false)
  }
}
async function load() {
  // Читаем 21 строку для определения следующей страницы, показывая по 20 операций.
  if (busy.value) return
  const revision = ++version
  loading.value = true
  error.value = ''
  items.value = []
  hasNext.value = false
  selectedBatch.value = null
  selectedTransaction.value = null
  try {
    const response = await apiGet(`/integrations/airpay/transactions?limit=21&offset=${page.value * 20}${filterQuery()}`, { token: props.token })
    if (revision !== version) return
    hasNext.value = response.items.length > 20
    legacyAvailable.value = Boolean(response.legacy_available)
    items.value = response.items.slice(0, 20)
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось загрузить историю Airpay'
  } finally { if (revision === version) loading.value = false }
}
async function openBatch(item) {
  // Любая строка истории открывает сохранённый состав покупки без повторных check и pay.
  if (busy.value || loading.value) return
  const revision = ++version
  loading.value = true
  error.value = ''
  try {
    const value = await apiGet(`/integrations/airpay/batches/${item.agent_transaction_id}`, { token: props.token })
    if (revision === version) {
      selectedBatch.value = value
      loading.value = false
      await nextTick()
      backButton.value?.focus()
    }
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось загрузить покупку'
  } finally { if (revision === version) loading.value = false }
}
function changePage(delta) {
  // Смена страницы не прерывает активный запрос по покупке.
  if (loading.value || busy.value) return
  page.value += delta
  void load()
}
watch(() => props.token, () => {
  // История нового пользователя загружается с первой страницы без данных прежнего сеанса.
  active.clear()
  emit('busy-change', false)
  exporting.value = false
  archive.value = false
  legacyAvailable.value = false
  Object.assign(draft, emptyFilters)
  applied.value = { ...emptyFilters }
  page.value = 0
  void load()
}, { immediate: true })
onBeforeUnmount(() => {
  // Закрытие отменяет применение поздних ответов и снимает блокировку переключателя.
  version += 1
  emit('busy-change', false)
})
</script>

<style scoped>
.airpay-history { display: grid; gap: 16px; min-width: 0; }
.airpay-history-filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; padding: 14px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .07); }
.airpay-history-filters .field { flex: 1 1 150px; min-width: 0; }
.airpay-history-filters .airpay-history-search { flex: 2 1 280px; }
.airpay-history-filters .input { width: 100%; min-width: 0; box-sizing: border-box; color-scheme: dark; }
.airpay-history-actions, .airpay-history-sources { display: flex; flex-wrap: wrap; gap: 8px; }
.airpay-history-sources .ghost { display: grid; gap: 2px; min-width: 190px; justify-items: start; padding: 10px 14px; }
.airpay-history-sources small { color: #9da9bf; font-size: 11px; font-weight: 500; }
.airpay-history-sources .is-active { box-shadow: inset 3px 0 0 #e88613; border-color: rgba(232,134,19,.7); }
.airpay-history-back { justify-self: start; }
.airpay-history-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 240px)); gap: 10px; }
.airpay-history-cards .mini { min-width: 0; background: #1b2435; border-color: rgba(181,194,219,.2); }
.airpay-history-cards .mini__value { color: #f4f7ff; }
.airpay-history-table { max-height: min(460px, 44vh); overflow: auto; min-height: 120px; }
.airpay-history-table .table { min-width: 800px; color: #e5eaf5; }
.airpay-history-table thead { position: sticky; top: 0; z-index: 1; }
.airpay-history-table th { background: #2a3447; color: #f7f9ff; }
.airpay-history-table td { background: #202838; }
.airpay-history-row { cursor: pointer; }
.airpay-history-row:hover td, .airpay-history-row:focus-within td { background: #2a3447; }
.airpay-history-service { border: 0; padding: 0; background: transparent; color: inherit; text-align: left; font: inherit; cursor: pointer; }
.airpay-history-service:focus-visible { outline: 2px solid #62e4c0; outline-offset: 4px; }
.airpay-history-price, .airpay-history-date { white-space: nowrap; }
.airpay-history-state { display: inline-flex; padding: 4px 8px; border: 1px solid; border-radius: 999px; font-size: 11px; font-weight: 750; }
.is-succeeded { color: #62e4c0; border-color: rgba(70,224,185,.46); }
.is-pending { color: #f6c66e; border-color: rgba(246,187,76,.52); }
.is-failed { color: #ff9b9b; border-color: rgba(255,121,121,.5); }
.airpay-history nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; color: #b5bfd3; font-size: 13px; }
.airpay-history-note { margin: 0; padding: 10px 12px; border-left: 3px solid rgba(181,194,219,.3); background: rgba(181,194,219,.06); color: #9da9bf; font-size: 12px; line-height: 1.45; }
@media (max-width: 640px) {
  .airpay-history-filters .field { flex-basis: 100%; }
  .airpay-history-cards { grid-template-columns: 1fr; }
  .airpay-history-table { max-height: 50vh; }
}
</style>
