<template>
  <details class="airpay-queue" @toggle="onToggle">
    <summary>Состояние очереди Airpay</summary>
    <p class="muted">Чтение сохранённых заданий. Обновление не повторяет оплату. Задания без прогресса более 5 минут требуют проверки исполнителя.</p>
    <button class="ghost" type="button" :disabled="loading || blocked" @click="load">Обновить очередь</button>
    <p v-if="loading" role="status">Загружаем очередь…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="data">
      <p>Ожидают: {{ data.summary.queued }} · Выполняются: {{ data.summary.running }} · Без прогресса: {{ data.summary.stale }}</p>
      <p>Остановлены настройкой оплаты: {{ data.summary.blocked_by_config }} · Ошибок за 24 часа: {{ data.summary.failed_24h }}</p>
      <p v-if="!data.items.length" class="muted">Активных заданий и недавних ошибок нет.</p>
      <div v-for="job in data.items" :key="job.job_id" class="airpay-queue-item">
        <p><strong>{{ actions[job.action] || job.action }}</strong> · {{ states[job.state] || job.state }} · Позиций: {{ job.progress }}</p>
        <p>Операция {{ job.transaction_id }} · Задание {{ job.job_id }}</p>
        <p v-if="job.reason" class="muted">{{ reasons[job.reason] }}</p>
        <button class="ghost" type="button" :disabled="blocked || loading" @click="emit('open', job.transaction_id)">Открыть сохранённую покупку</button>
        <button v-if="job.state === 'queued' && confirming !== job.job_id" class="ghost" type="button" :disabled="blocked || loading" @click="confirming = job.job_id">Отменить запуск задания</button>
        <div v-if="confirming === job.job_id">
          <p>Отменить ещё не начатое задание? Сохранённые оплаты и коды останутся без изменений.</p>
          <button class="ghost" type="button" :disabled="blocked || loading" @click="cancel(job.job_id)">Да, отменить запуск</button>
          <button class="ghost" type="button" :disabled="loading" @click="confirming = ''">Оставить в очереди</button>
        </div>
      </div>
      <p v-if="data.has_more" class="muted">Показаны первые 50 заданий. Покупку можно найти по номеру в истории.</p>
    </template>
  </details>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
const props = defineProps({ token: { type: String, default: '' }, blocked: { type: Boolean, default: false } })
const emit = defineEmits(['open'])
const data = ref(null)
const loading = ref(false)
const error = ref('')
const confirming = ref('')
let version = 0
const actions = { check: 'Проверка', pay: 'Оплата', voucher: 'Получение кода', reconcile: 'Сверка оплаты', renew: 'Переоценка' }
const states = { queued: 'Ожидает', running: 'Выполняется', failed: 'Задание остановлено' }
const reasons = {
  interrupted: 'Исполнитель потерян. Начатые платёжные действия автоматически не повторяются. Проверьте сохранённую покупку.',
  payments_disabled: 'Исполнение этого задания остановлено настройкой оплаты. Не включайте оплату только ради очистки очереди.',
  stale: 'Давно нет прогресса. Это не доказывает отказ оплаты; проверьте исполнителя и сохранённую покупку.',
  failed: 'Задание завершилось с ошибкой. Состояние оплаты проверяйте в покупке — ошибка задания не отменяет списание.',
}
async function load() {
  // Диагностика выполняет только GET и не держит окно заблокированным при закрытии.
  if (loading.value || props.blocked) return
  const revision = ++version
  loading.value = true
  error.value = ''
  try {
    const response = await apiGet('/integrations/airpay/queue', { token: props.token })
    if (revision === version) data.value = response
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось прочитать очередь'
  } finally { if (revision === version) loading.value = false }
}
async function cancel(jobId) {
  // Подтверждённая отмена касается только queued; гонку с запуском блокирует сервер.
  if (loading.value || props.blocked) return
  const revision = ++version
  loading.value = true
  error.value = ''
  try {
    await apiPost(`/integrations/airpay/jobs/${jobId}/cancel`, {}, { token: props.token })
    if (revision !== version) return
    confirming.value = ''
    const response = await apiGet('/integrations/airpay/queue', { token: props.token })
    if (revision === version) data.value = response
  } catch (err) {
    if (revision === version) error.value = err?.message || 'Не удалось отменить запуск'
  } finally { if (revision === version) loading.value = false }
}
function onToggle(event) {
  // До раскрытия панели дополнительный запрос не нужен.
  if (event.target.open && !data.value) void load()
}
watch(() => props.token, () => {
  // Смена пользователя удаляет прежнюю диагностику и исключает поздний ответ старого запроса.
  version += 1
  data.value = null
  confirming.value = ''
  error.value = ''
  loading.value = false
})
onBeforeUnmount(() => { version += 1 })
</script>

<style scoped>
.airpay-queue { border: 1px solid var(--ghost-border, #343b4a); border-radius: 12px; padding: 16px; }
.airpay-queue summary { cursor: pointer; font-weight: 600; }
.airpay-queue-item { border-top: 1px solid var(--ghost-border, #343b4a); margin-top: 12px; padding-top: 8px; overflow-wrap: anywhere; }
</style>
