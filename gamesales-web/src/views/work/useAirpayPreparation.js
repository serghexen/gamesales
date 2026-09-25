import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../api/http'
import { resolveAirpayJob } from './airpayJob'

export function useAirpayPreparation(props) {
  // Форма и подписанный снимок принадлежат только выбранной услуге и текущей сессии.
  const service = ref(null)
  const fields = reactive({})
  const amountTo = ref('')
  const quantity = ref(1)
  const batch = ref(null)
  const purchaseKind = computed(() => {
    // Фиксированная сумма означает ваучер; неизвестный признак не превращаем в пополнение.
    return service.value?.fixed_payment === true ? 'voucher' : service.value?.fixed_payment === false ? 'topup' : ''
  })
  const transaction = ref(null)
  const purchaseLocked = ref(false)
  let preparationKey = crypto.randomUUID()
  const loading = ref(false)
  const busy = ref(false)
  const error = ref('')
  const result = ref(null)
  const draft = ref(null)
  const retrySeconds = ref(0)
  let version = 0
  let retryCount = 0
  let retryTimer
  const inputs = computed(() => {
    // account обязателен в контракте check даже у услуги, не перечислившей его среди inputs.
    const items = service.value?.inputs || []
    return items.some(field => field.name === 'account') ? items
      : [{ name: 'account', title: 'Идентификатор / аккаунт', required: true }, ...items]
  })

  function invalidate() {
    // Изменение реквизитов отменяет прежнюю проверку и её идентификатор до следующей отправки.
    version += 1
    draft.value = null
    preparationKey = crypto.randomUUID()
    result.value = null
    error.value = ''
    retryCount = 0
    retrySeconds.value = 0
    clearTimeout(retryTimer)
  }

  async function loadService() {
    // Читаем service заново, чтобы форма не использовала устаревшие поля общего каталога.
    invalidate()
    const current = version
    service.value = null
    busy.value = false
    loading.value = true
    Object.keys(fields).forEach(key => delete fields[key])
    amountTo.value = ''
    quantity.value = 1
    batch.value = null
    transaction.value = null
    purchaseLocked.value = false
    try {
      const data = await apiGet(`/integrations/airpay/service?service_id=${encodeURIComponent(props.serviceId)}`, { token: props.token })
      if (current !== version) return
      service.value = data
      inputs.value.forEach(field => {
        // Служебная почта подходит для ваучеров; аккаунт получателя пополнения всегда вводится вручную.
        const voucherEmail = data.fixed_payment === true && field.name === 'account' && /e[\s-]?mail|почт/i.test(field.title || '')
        fields[field.name] = voucherEmail ? 'seller@homtech.ru' : ''
      })
    } catch (err) {
      if (current === version) error.value = err?.message || 'Не удалось загрузить параметры Airpay'
    } finally {
      if (current === version) loading.value = false
    }
  }

  function waitBeforeRetry() {
    // Увеличиваем паузу между ручными повторами временного результата; автоматических запросов нет.
    retrySeconds.value = [5, 15, 30, 60, 300][Math.min(retryCount++, 4)]
    const tick = () => {
      retrySeconds.value -= 1
      if (retrySeconds.value > 0) retryTimer = setTimeout(tick, 1000)
    }
    retryTimer = setTimeout(tick, 1000)
  }

  async function check() {
    // Повтор использует прежнюю подпись; новый prepare нужен только после изменения реквизитов.
    if (busy.value || loading.value || retrySeconds.value || !service.value || !props.canPrepare || !purchaseKind.value || purchaseLocked.value || (result.value && !result.value.retryable)) return
    if (purchaseKind.value === 'voucher' && (!Number.isInteger(Number(quantity.value)) || Number(quantity.value) < 1 || Number(quantity.value) > 20)) {
      error.value = 'Количество ключей должно быть целым числом от 1 до 20'
      return
    }
    const current = version
    busy.value = true
    error.value = ''
    result.value = null
    try {
      if (!draft.value) {
        const prepared = await apiPost('/integrations/airpay/prepare', {
          service_id: props.serviceId, fields: { ...fields },
          preparation_key: preparationKey,
          quantity: purchaseKind.value === 'voucher' ? Number(quantity.value) : 1,
          // Числовой input Vue возвращает number; внутренний API принимает суммы строками.
          amount_to: purchaseKind.value === 'topup' && amountTo.value !== '' ? String(amountTo.value) : null,
        }, { token: props.token })
        if (current !== version) return
        draft.value = prepared
      }
      const checked = await resolveAirpayJob(await apiPost('/integrations/airpay/check', { preparation_token: draft.value.preparation_token }, { token: props.token }),
        { token: props.token, active: () => current === version })
      if (current !== version) return
      result.value = checked
      if (checked.retryable) waitBeforeRetry()
    } catch (err) {
      if (current !== version) return
      error.value = err?.message || 'Не удалось проверить услугу Airpay'
      if ([410, 422, 403].includes(err?.status)) {
        draft.value = null
        // Истёкший снимок нельзя восстановить тем же ключом: следующая подготовка должна стать новой.
        if (err?.status === 410) preparationKey = crypto.randomUUID()
      }
      else if (draft.value) waitBeforeRetry()
    } finally {
      if (current === version) busy.value = false
    }
  }

  async function pay() {
    // После нажатия не создаём новую покупку даже при потере ответа: восстанавливаем запись из истории.
    if (busy.value || purchaseLocked.value || !result.value?.purchase_ready || !result.value?.payments_enabled) return
    purchaseLocked.value = true
    busy.value = true
    error.value = ''
    const current = version
    const isBatch = Boolean(result.value.batch)
    if (isBatch) batch.value = { ...result.value.batch, state: 'processing' }
    else transaction.value = { ...result.value.transaction, state: 'processing', provider_message: 'Ожидаем ответ на оплату' }
    try {
      const paid = await resolveAirpayJob(await apiPost(`/integrations/airpay/${isBatch ? 'batches' : 'transactions'}/${draft.value.agent_transaction_id}/pay`, {
        confirmed_amount: result.value.purchase_amount,
      }, { token: props.token }), { token: props.token, active: () => current === version,
        progress: job => { if (isBatch) batch.value = { ...batch.value, job } } })
      if (current === version) {
        if (isBatch) batch.value = paid
        else transaction.value = paid
      }
    } catch (err) {
      if (current === version) error.value = err?.message || 'Ответ на оплату не получен. Обновите сохранённый результат.'
    } finally {
      if (current === version) busy.value = false
    }
  }

  function acceptTransaction(value) {
    // Если сервер подтверждает, что pay не начинался, разрешаем заново подготовить покупку.
    transaction.value = value
    if (['prepared', 'checked', 'check_failed'].includes(value.state)) {
      purchaseLocked.value = false
      transaction.value = null
      invalidate()
    }
  }

  watch(() => [props.serviceId, props.token], loadService, { immediate: true })
  onBeforeUnmount(() => {
    // Уход со страницы делает поздние ответы и таймер повторной проверки неактуальными.
    version += 1
    clearTimeout(retryTimer)
  })
  return { service, fields, inputs, amountTo, quantity, batch, loading, busy, error, result,
    draft, retrySeconds, invalidate, loadService, check, purchaseKind, transaction, purchaseLocked, pay, acceptTransaction }
}
