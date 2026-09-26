<template>
  <section class="airpay" aria-labelledby="airpay-title">
    <header class="panel__head supplier-catalog__head">
      <div>
        <p class="supplier-catalog__eyebrow">Поставщик · агентский каталог</p>
        <h3 id="airpay-title" class="supplier-catalog__title">Airpay</h3>
      </div>
      <div class="supplier-catalog__head-actions">
        <button v-if="canPrepare" class="ghost" type="button" :disabled="refreshLoading" @click="diagnosticsOpen = true">Проверить каталог</button>
        <button v-if="canViewHistory" class="ghost" type="button" :disabled="refreshLoading" @click="historyOpen = true">История покупок</button>
        <button class="deal-refresh-btn" type="button" :disabled="refreshLoading" aria-label="Обновить данные Airpay" title="Обновить баланс и каталог Airpay" @click="refreshData"><span class="deal-refresh-btn__content">↻</span></button>
      </div>
    </header>

    <div class="panel__body">
      <div class="airpay__balance" :aria-busy="loading" aria-live="polite">
        <p v-if="loading" class="muted">Получаем баланс Airpay…</p>
        <p v-else-if="error" class="error" role="alert">{{ error }}</p>
        <div v-else-if="balance?.configured === false" class="airpay__setup">
          <strong>Airpay ещё не подключён</strong>
          <p>Для получения баланса нужно настроить доступ к поставщику на сервере.</p>
        </div>
        <div v-else-if="balance?.configured" class="supplier-catalog__balance">
          <span>Депозит поставщика</span>
          <strong data-testid="airpay-balance">{{ formatMoney(balance.balance, balance.currency) }}</strong>
          <small>Разрешённый овердрафт: <span data-testid="airpay-overdraft">{{ formatMoney(balance.overdraft, balance.currency) }}</span></small>
          <small v-if="availableFunds !== null">Доступно для покупок: <span data-testid="airpay-available">{{ formatMoney(availableFunds, balance.currency) }}</span></small>
          <small>Агентский счёт</small>
        </div>
      </div>

      <WorkAirpayCatalog ref="catalog" :token="token" :can-prepare="canPrepare" :currency="balance?.currency || ''" embedded @busy-change="emit('busy-change', $event)" />
    </div>
    <WorkAirpayDiagnostics v-if="diagnosticsOpen" :token="token" @close="diagnosticsOpen = false" />
    <WorkAirpayHistory v-if="historyOpen" :token="token" @close="historyOpen = false" @busy-change="setHistoryBusy" />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet } from '../../../api/http'
import WorkAirpayCatalog from './WorkAirpayCatalog.vue'
import WorkAirpayHistory from './WorkAirpayHistory.vue'
import WorkAirpayDiagnostics from './WorkAirpayDiagnostics.vue'

const props = defineProps({ token: { type: String, default: '' }, canPrepare: { type: Boolean, default: false }, canViewHistory: { type: Boolean, default: false } })
const emit = defineEmits(['busy-change'])
const loading = ref(false)
const error = ref('')
const balance = ref(null)
const availableFunds = computed(() => {
  // Показываем остаток с разрешённым кредитом; решение о покупке всё равно принимает сервер.
  const current = balance.value?.balance
  const credit = balance.value?.overdraft
  if (typeof current !== 'number' || typeof credit !== 'number' || !Number.isFinite(current) || !Number.isFinite(credit) || credit < 0) return null
  return current + credit
})
const catalog = ref(null)
const historyOpen = ref(false)
const diagnosticsOpen = ref(false)
const historyBusy = ref(false)
const refreshLoading = computed(() => historyBusy.value || loading.value || Boolean(catalog.value?.loading) || Boolean(catalog.value?.preparationBusy))
let requestVersion = 0

function setHistoryBusy(value) {
  // История не даёт переключать поставщика, пока уточняется операция или получается код.
  historyBusy.value = value
  emit('busy-change', value)
}

async function refreshData() {
  // Одна кнопка обновляет оба блока, как у Interhub; ошибки остаются возле своих данных.
  if (refreshLoading.value) return
  await Promise.all([loadBalance(), catalog.value?.reload?.()])
}

async function loadBalance() {
  // Ответ относится только к текущему входу в Airpay; после выхода старые суммы не возвращаем.
  const version = ++requestVersion
  balance.value = null
  error.value = ''
  loading.value = true
  try {
    const result = await apiGet('/integrations/airpay/balance', { token: props.token })
    if (version === requestVersion) balance.value = result
  } catch (err) {
    if (version === requestVersion) error.value = err?.message || 'Не удалось загрузить баланс Airpay'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

function formatMoney(amount, currency) {
  // Валюта необязательна в Airpay: её отсутствие обозначаем явно, не подставляя рубли.
  const options = { minimumFractionDigits: 2, maximumFractionDigits: 2 }
  if (currency) return new Intl.NumberFormat('ru-RU', { ...options, style: 'currency', currency }).format(amount)
  return `${new Intl.NumberFormat('ru-RU', options).format(amount)} · валюта не указана`
}

watch(() => props.token, () => {
  // Новый сеанс авторизации получает собственный баланс без использования предыдущего ответа.
  void loadBalance()
  historyOpen.value = false
  diagnosticsOpen.value = false
}, { immediate: true })

onBeforeUnmount(() => {
  // Поздний ответ не должен менять состояние уже закрытого экрана поставщика.
  requestVersion += 1
})
</script>

<style scoped src="../styles/work-supplier-catalog.css"></style>

<style scoped>
.airpay__balance p { margin: 0 0 18px; line-height: 1.5; }
.airpay__setup p { margin-top: 8px; color: var(--muted, #9da9bf); font-size: 13px; }
</style>
