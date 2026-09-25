<template>
  <WorkAirpayDialog title="История покупок Airpay" :busy="busy" @close="emit('close')">
    <div class="airpay-history">
      <p v-if="loading" class="muted" role="status">Загружаем историю…</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="!loading && !error && !items.length" class="muted">По выбранным условиям операций нет.</p>
      <p v-if="exporting" class="muted" role="status">Готовим Excel…</p>
      <template v-if="!busy">
        <label v-if="legacyAvailable" class="field"><span>Источник истории</span><select v-model="archive" :disabled="loading" @change="page = 0; load()"><option :value="false">Supplier Hub · Airpay</option><option :value="true">Архив CRM · только чтение</option></select></label>
        <form class="airpay-history-filters" @submit.prevent="applyFilters">
          <label class="field airpay-history-search"><span>Поиск</span><input v-model="draft.q" type="search" maxlength="200" :disabled="loading" placeholder="Услуга, аккаунт или номер операции" /></label>
          <label class="field"><span>Состояние</span><select v-model="draft.status" :disabled="loading"><option value="">Все состояния</option><option v-for="option in statuses" :key="option[0]" :value="option[0]">{{ option[1] }}</option></select></label>
          <label class="field"><span>Вид покупки</span><select v-model="draft.kind" :disabled="loading"><option value="">Все виды</option><option value="voucher">Ваучер</option><option value="topup">Пополнение</option></select></label>
          <label class="field"><span>Создана с (МСК)</span><input v-model="draft.date_from" type="date" :disabled="loading" /></label>
          <label class="field"><span>По дату включительно (МСК)</span><input v-model="draft.date_to" type="date" :min="draft.date_from || undefined" :disabled="loading" /></label>
          <div class="airpay-history-actions"><button class="btn" type="submit" :disabled="loading">Найти</button><button class="ghost" type="button" :disabled="loading" @click="resetFilters">Сбросить</button></div>
        </form>
        <div class="airpay-history-actions"><button class="ghost" type="button" :disabled="loading" @click="load">Обновить историю</button><button class="ghost" type="button" :disabled="loading || !items.length" @click="downloadHistory">Выгрузить Excel</button></div>
        <p class="muted">Excel: все операции по применённым фильтрам, до 10 000 строк. Коды ваучеров не выгружаются.</p>
        <nav aria-label="Страницы истории Airpay"><button class="ghost" type="button" :disabled="loading || page === 0" @click="changePage(-1)">Назад</button><span>Страница {{ page + 1 }}</span><button class="ghost" type="button" :disabled="loading || !hasNext" @click="changePage(1)">Далее</button></nav>
      </template>
      <WorkAirpayQueue v-if="!archive" :token="token" :blocked="busy || loading" @open="openBatch({ agent_transaction_id: $event })" />
      <template v-if="selectedBatch">
        <button class="ghost" type="button" :disabled="busy" @click="selectedBatch = null">Вернуться к истории</button>
        <WorkAirpayBatch :batch="selectedBatch" :token="token" @busy-change="setBusy('batch', $event)" />
      </template>
      <template v-else>
      <div v-for="item in items" :key="item.agent_transaction_id">
        <button v-if="item.batch && !archive" class="ghost" type="button" :disabled="busy || loading" @click="openBatch(item)">Открыть покупку {{ item.batch.quantity }} ключей</button>
        <WorkAirpayTransaction :transaction="item" :token="token" :blocked="busy" :archive="archive" @busy-change="setBusy(item.agent_transaction_id, $event)" />
      </div>
      </template>
    </div>
  </WorkAirpayDialog>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
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
const page = ref(0)
const hasNext = ref(false)
const loading = ref(false)
const error = ref('')
const active = reactive(new Set())
const busy = computed(() => active.size > 0)
let version = 0
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
  selectedBatch.value = null
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
    if (revision === version) selectedBatch.value = value
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
.airpay-history { display: grid; gap: 18px; }
.airpay-history-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; align-items: end; }
.airpay-history-actions { display: flex; flex-wrap: wrap; gap: 12px; }
.airpay-history > button { justify-self: start; }
.airpay-history nav { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
</style>
