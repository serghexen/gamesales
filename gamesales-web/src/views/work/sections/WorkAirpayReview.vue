<template>
  <section class="airpay-review" aria-label="Журнал и разбор Airpay">
    <div class="airpay-review__actions">
      <button class="ghost" type="button" :disabled="busy || blocked" @click="loadEvents()">Журнал событий</button>
      <button v-if="canResolve" class="ghost" type="button" :disabled="busy || blocked" @click="opened = !opened">Ручной разбор</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="events !== null" aria-label="События операции">
      <p v-if="!events.length" class="muted">Событий пока нет. Для старых операций история начинается после обновления журнала.</p>
      <ol class="airpay-review__events"><li v-for="event in events" :key="event.id">
        <strong>{{ eventLabel(event.event_type) }}</strong><span>{{ dateLabel(event.created_at) }} · {{ event.actor }}</span>
        <small>{{ event.state_before || '—' }} → {{ event.state_after }}</small>
        <p v-if="event.evidence">Основание: {{ event.evidence }}</p>
      </li></ol>
      <button v-if="nextCursor" class="ghost" type="button" :disabled="busy || blocked" @click="loadEvents(nextCursor)">Ранее</button>
    </section>
    <form v-if="opened && canResolve" class="airpay-review__form" @submit.prevent="resolve">
      <h4>Результат внешней сверки</h4>
      <p class="muted">Сначала проверьте операцию у Airpay. Здесь сохраняется подтверждённый результат: запросы оплаты и получения кода не выполняются.</p>
      <fieldset :disabled="busy || blocked || Boolean(savedRequest)">
        <label class="field"><span>Решение</span><select v-model="decision"><option value="record_success">Покупка подтверждена</option><option v-if="transaction.state === 'processing'" value="confirm_failed">Airpay подтвердил отсутствие оплаты</option></select></label>
        <template v-if="decision === 'record_success'">
          <label class="field"><span>Номер оплаченной транзакции Airpay</span><input v-model="providerId" required maxlength="128" /></label>
          <label v-if="transaction.purchase_kind === 'voucher'" class="field"><span>Полученный код ваучера</span><input v-model="code" type="password" required maxlength="4096" autocomplete="off" /></label>
        </template>
        <label class="field"><span>Основание решения</span><textarea v-model="evidence" required minlength="10" maxlength="1000" placeholder="Например, номер обращения и подтверждение Airpay. Без кодов и паролей." /></label>
        <label class="airpay-review__verified"><input v-model="verified" type="checkbox" required /> Я проверил эту операцию у Airpay и подтверждаю результат</label>
      </fieldset>
      <p v-if="savedRequest && error" class="muted">Повтор сохранит то же решение. Перед изменением данных обновите операцию.</p>
      <div class="airpay-review__actions">
        <button class="btn" type="submit" :disabled="busy || blocked || !verified">{{ savedRequest ? 'Повторить сохранение решения' : 'Сохранить решение' }}</button>
        <button class="ghost" type="button" :disabled="busy || blocked" @click="emit('refresh')">Обновить операцию</button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
const props = defineProps({ transaction: { type: Object, required: true }, token: { type: String, default: '' }, blocked: Boolean, archive: Boolean })
const emit = defineEmits(['busy-change', 'resolved', 'refresh'])
const busy = ref(false), error = ref(''), opened = ref(false), events = ref(null), nextCursor = ref(null)
const decision = ref('record_success'), providerId = ref(''), code = ref(''), evidence = ref(''), verified = ref(false), savedRequest = ref(null)
let revision = 0
const canResolve = computed(() => !props.archive && props.transaction.resolution_available && Boolean(props.transaction.updated_at))
function eventLabel(value) {
  // Названия объясняют действие без вывода сырых ответов и реквизитов поставщика.
  return ({ prepared: 'Создана подготовка', pay_requested: 'Запрошена оплата', voucher_requested: 'Запрошен код', check_requested: 'Запрошена проверка', voucher_saved: 'Код сохранён', state_changed: 'Изменён статус', operation_updated: 'Обновлена операция', attention_required: 'Требуется разбор', operator_resolved: 'Сохранено решение владельца', replaced: 'Подготовка заменена' })[value] || 'Событие операции'
}
function dateLabel(value) {
  // Журнал показываем в часовом поясе пользователя.
  return new Date(value).toLocaleString('ru-RU')
}
function path() {
  // Архив читается через старый журнал CRM и не допускает новых решений.
  return `/integrations/airpay/${props.archive ? 'legacy/' : ''}transactions/${props.transaction.agent_transaction_id}`
}
async function loadEvents(before = null) {
  // Пагинация читает только журнал БД и никогда не запускает проверку поставщика.
  if (busy.value || props.blocked) return
  const stamp = revision
  busy.value = true; emit('busy-change', true); error.value = ''
  try {
    const response = await apiGet(`${path()}/events${before ? `?before=${encodeURIComponent(before)}` : ''}`, { token: props.token })
    if (stamp !== revision) return
    events.value = before ? [...events.value, ...response.items] : response.items
    nextCursor.value = response.next_cursor
  } catch (err) { if (stamp === revision) error.value = err?.message || 'Не удалось прочитать журнал' }
  finally { if (stamp === revision) { busy.value = false; emit('busy-change', false) } }
}
async function resolve() {
  // После потери ответа повторяем неизменный запрос с тем же ключом, не создавая второго решения.
  if (busy.value || props.blocked || !canResolve.value || !verified.value) return
  const stamp = revision
  savedRequest.value ||= { request_id: crypto.randomUUID(), decision: decision.value, expected_updated_at: props.transaction.updated_at,
    verified: true, evidence: evidence.value.trim(), provider_transaction_id: decision.value === 'record_success' ? providerId.value.trim() : '',
    code: decision.value === 'record_success' && props.transaction.purchase_kind === 'voucher' ? code.value.trim() : '' }
  busy.value = true; emit('busy-change', true); error.value = ''
  try {
    const response = await apiPost(`${path()}/resolve`, savedRequest.value, { token: props.token })
    if (stamp !== revision) return
    code.value = ''; savedRequest.value = null; opened.value = false; events.value = null
    emit('resolved', response)
  } catch (err) { if (stamp === revision) error.value = err?.message || 'Не удалось сохранить решение' }
  finally { if (stamp === revision) { busy.value = false; emit('busy-change', false) } }
}
watch(() => props.transaction, () => {
  // При обновлении или смене операции удаляем секрет формы и прежний снимок решения.
  revision += 1
  const wasBusy = busy.value
  busy.value = false
  if (wasBusy) emit('busy-change', false)
  code.value = ''; savedRequest.value = null; verified.value = false; evidence.value = ''; decision.value = 'record_success'
  providerId.value = props.transaction.provider_transaction_id || ''; events.value = null; nextCursor.value = null; error.value = ''
}, { immediate: true })
onBeforeUnmount(() => {
  // Ответ закрытой карточки не меняет другой журнал; введённый код не сохраняется в браузере.
  revision += 1; code.value = ''; savedRequest.value = null; emit('busy-change', false)
})
</script>

<style scoped>
.airpay-review { border-top: 1px solid var(--stroke); margin-top: 16px; padding-top: 16px; }
.airpay-review__actions { display: flex; gap: 10px; flex-wrap: wrap; }
.airpay-review__form { display: grid; gap: 14px; padding: 18px; margin-top: 16px; border-left: 3px solid #e88613; background: rgba(232,134,19,.06); }
.airpay-review__form h4, .airpay-review__form p { margin: 0; }
.airpay-review__form fieldset { border: 0; padding: 0; margin: 0; display: grid; gap: 14px; min-width: 0; }
.airpay-review__form textarea { min-height: 84px; resize: vertical; }
.airpay-review__verified { display: flex; align-items: flex-start; gap: 10px; }
.airpay-review__verified input { width: auto; flex: 0 0 auto; }
.airpay-review__events { display: grid; gap: 12px; padding-left: 22px; }
.airpay-review__events li { padding-left: 6px; overflow-wrap: anywhere; }
.airpay-review__events span, .airpay-review__events small { display: block; color: var(--muted); margin-top: 4px; }
</style>
