<template>
  <WorkAirpayDialog title="Проверка каталога Airpay" history :busy="loading" @close="emit('close')">
    <div class="airpay-diagnostics">
      <p class="muted">Опрос service и check без оплаты. Для фиксированных услуг с полем Email используем seller@homtech.ru. Аккаунты игроков и суммы не подбираем — такие позиции отметим отдельно.</p>
      <div class="airpay-diagnostics__actions">
        <button v-if="!run || run.state !== 'active'" class="btn" type="button" :disabled="loading" @click="start">Начать опрос</button>
        <button v-else-if="!running" class="btn" type="button" :disabled="loading" @click="resume">Продолжить опрос</button>
        <button v-if="running" class="ghost" type="button" @click="pause">Пауза после текущей позиции</button>
        <button v-if="run?.state === 'active' && !running" class="ghost" type="button" :disabled="loading" @click="cancel">Завершить опрос</button>
        <button class="ghost" type="button" :disabled="loading || running" @click="load">Обновить отчёт</button>
        <button v-if="run" class="ghost" type="button" :disabled="loading" @click="download">Скачать отчёт JSON</button>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="loading" role="status">{{ running ? 'Проверяем позицию…' : 'Загружаем…' }}</p>
      <template v-if="run">
        <p role="status">{{ run.state === 'completed' ? 'Опрос завершён' : run.state === 'cancelled' ? 'Опрос остановлен' : running ? 'Опрос выполняется' : 'Опрос на паузе' }} · Обработано {{ run.processed }} из {{ run.total }}</p>
        <p class="muted">Успешно: {{ count('ok') }} · Отклонено: {{ count('rejected') }} · Нужны реквизиты: {{ count('needs_input') }} · Остальные результаты: {{ otherCount }}</p>
        <div class="table-wrap airpay-diagnostics__table"><table class="table table--compact">
          <thead><tr><th>Услуга</th><th>Результат check</th><th>fixedPrice</th><th>Ответ / причина</th><th>Детали</th></tr></thead>
          <tbody><tr v-for="item in run.items" :key="item.service_id">
            <td>{{ item.title }}<small>{{ item.service_id }}</small></td>
            <td>{{ labels[item.state] || item.state }}<small v-if="item.result !== undefined">Код {{ item.result }}</small></td>
            <td>{{ item.fixed_price || '—' }}<small v-if="item.price_warning">{{ item.price_warning }}</small></td>
            <td>{{ item.message || '—' }}</td>
            <td><details><summary>ID и параметры</summary><dl>
              <dt>ID диагностики</dt><dd>{{ item.agent_transaction_id || '—' }}</dd>
              <dt>ID Airpay</dt><dd>{{ item.provider_transaction_id || '—' }}</dd>
              <dt>Фиксированная сумма</dt><dd>{{ item.fixed_payment === true ? 'Да' : item.fixed_payment === false ? 'Нет' : '—' }}</dd>
              <dt>Поля услуги</dt><dd v-for="field in item.fields || []" :key="field.name">{{ field.title || field.name }} · {{ field.required ? 'Обязательное' : 'Необязательное' }}</dd>
              <dt>Конвертация</dt><dd>{{ item.conversion || '—' }}</dd>
              <dt>Ответ получен</dt><dd>{{ item.finished_at || '—' }}</dd>
            </dl></details></td>
          </tr></tbody>
        </table></div>
      </template>
      <p class="muted">Успешный check не подтверждает наличие товара и не определяет тип выдачи. fixedPrice показываем как вернул поставщик, без подмены суммой конвертации. Диагностика не создаёт покупку.</p>
      <p class="muted">Опрос идёт последовательно, пока окно открыто. После закрытия можно продолжить сохранённый запуск; обработанные позиции повторно не проверяются.</p>
    </div>
  </WorkAirpayDialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
import WorkAirpayDialog from './WorkAirpayDialog.vue'
const props = defineProps({ token: { type: String, default: '' } })
const emit = defineEmits(['close'])
const run = ref(null)
const loading = ref(false)
const running = ref(false)
const error = ref('')
let version = 0
let timer
let requestId = ''
const labels = { pending: 'Не проверена', running: 'Проверяется', ok: 'Успешно', rejected: 'Отклонено', needs_input: 'Нужны реквизиты', pending_response: 'Ответ не окончательный', invalid_response: 'Некорректный ответ', transport_error: 'Ошибка запроса', interrupted: 'Шаг прерван' }
function count(state) {
  // Счётчики относятся к сохранённым ответам, а не к наличию товара или успешной оплате.
  return run.value?.items.filter(item => item.state === state).length || 0
}
const otherCount = computed(() => (run.value?.processed || 0) - count('ok') - count('rejected') - count('needs_input'))
function pause() {
  // Текущий check завершается, но следующий автоматически не запускается.
  running.value = false
  clearTimeout(timer)
}
async function load() {
  // Возвращаем последний отчёт без запуска внешних запросов после открытия окна.
  pause()
  const revision = ++version
  loading.value = true
  error.value = ''
  try {
    const response = await apiGet('/integrations/airpay/diagnostics', { token: props.token })
    if (revision === version) run.value = response.run
  } catch (err) { if (revision === version) error.value = err?.message || 'Не удалось прочитать отчёт' }
  finally { if (revision === version) loading.value = false }
}
async function start() {
  // Повтор после потери ответа использует прежний UUID запуска, не создавая дубликат.
  if (loading.value) return
  const revision = version
  requestId ||= crypto.randomUUID()
  loading.value = true
  error.value = ''
  try {
    const response = await apiPost('/integrations/airpay/diagnostics', { request_id: requestId }, { token: props.token })
    if (revision !== version) return
    run.value = response.run
    requestId = ''
    running.value = run.value.state === 'active'
  } catch (err) { if (revision === version) error.value = err?.message || 'Не удалось начать опрос' }
  finally {
    if (revision === version) {
      loading.value = false
      if (running.value) void step()
    }
  }
}
function resume() {
  // Продолжение обрабатывает только оставшиеся позиции, не повторяя неопределённый check.
  if (loading.value || running.value || run.value?.state !== 'active') return
  running.value = true
  void step()
}
async function step() {
  // Последовательные шаги ограничивают нагрузку; при сетевой ошибке дальнейший опрос ставится на паузу.
  if (!running.value || loading.value) return
  const revision = version
  const previous = run.value.processed
  loading.value = true
  error.value = ''
  try {
    const response = await apiPost(`/integrations/airpay/diagnostics/${run.value.id}/next`, {}, { token: props.token })
    if (revision !== version) return
    run.value = response.run
    if (run.value.state !== 'active') pause()
    if (run.value.processed > previous) {
      // После ошибки последнего шага сначала даём владельцу проверить ответ поставщика.
      const last = run.value.items.filter(item => !['pending', 'running'].includes(item.state)).at(-1)
      if (last?.state === 'transport_error') { pause(); error.value = 'Опрос приостановлен после ошибки запроса. Проверьте отчёт.' }
    }
  } catch (err) {
    if (revision === version) { pause(); error.value = err?.message || 'Ответ потерян. Обновите отчёт перед продолжением.' }
  } finally {
    if (revision === version) {
      loading.value = false
      if (running.value) timer = setTimeout(step, 1200)
    }
  }
}
async function cancel() {
  // Завершаем диагностический запуск, оставляя все полученные результаты для разбора.
  if (loading.value || running.value) return
  const revision = version
  loading.value = true
  error.value = ''
  try {
    const response = await apiPost(`/integrations/airpay/diagnostics/${run.value.id}/cancel`, {}, { token: props.token })
    if (revision === version) run.value = response.run
  } catch (err) { if (revision === version) error.value = err?.message || 'Не удалось завершить опрос' }
  finally { if (revision === version) loading.value = false }
}
function download() {
  // JSON сохраняет ID строками и переносит ответы без формул Excel и скрытых платёжных данных.
  const url = URL.createObjectURL(new Blob([JSON.stringify(run.value, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `airpay-check-${run.value.id}.json`
  link.click()
  URL.revokeObjectURL(url)
}
watch(() => props.token, () => {
  // Смена владельца очищает прежний отчёт и останавливает следующий шаг.
  run.value = null
  requestId = ''
  void load()
}, { immediate: true })
onBeforeUnmount(() => {
  // Закрытие не отменяет уже отправленный check, но исключает фоновые продолжения и поздние ответы.
  version += 1
  pause()
})
</script>

<style scoped>
.airpay-diagnostics { display: grid; gap: 14px; }
.airpay-diagnostics p { margin: 0; }
.airpay-diagnostics__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.airpay-diagnostics__table { max-height: 45vh; overflow: auto; }
.airpay-diagnostics__table table { min-width: 850px; }
.airpay-diagnostics__table th { position: sticky; top: 0; background: #2a3447; }
.airpay-diagnostics__table small { display: block; color: var(--muted); }
.airpay-diagnostics__table td { vertical-align: top; }
.airpay-diagnostics__table dd { margin: 0 0 8px; overflow-wrap: anywhere; }
</style>
