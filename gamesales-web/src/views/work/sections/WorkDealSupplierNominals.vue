<template>
  <section v-if="isSupportedRegion" class="deal-supplier" aria-labelledby="deal-supplier-title">
    <div class="deal-supplier__head">
      <div class="deal-supplier__identity">
          <span class="deal-supplier__mark" aria-hidden="true">П</span>
        <div>
          <p class="deal-supplier__eyebrow">Поставщик · {{ regionLabel }}</p>
          <h4 id="deal-supplier-title">Номиналы поставщика</h4>
        </div>
      </div>
    </div>

    <div v-if="!dealId" class="deal-supplier__save-note">
      <strong>Сначала сохраните сделку</strong>
      <span>Покупка привязывается к номеру сделки, поэтому код нельзя получить до первого сохранения.</span>
    </div>

    <template v-else>
      <p v-if="loading" class="deal-supplier__muted">Загружаем номиналы поставщика…</p>
      <p v-else-if="error" class="deal-supplier__error">{{ error }}</p>
      <div v-if="blockedReason" class="deal-supplier__save-note" role="status">
        <strong>{{ blockedReason }}</strong>
        <span>Уже полученные ваучеры остаются в истории сделки.</span>
      </div>
      <button v-if="syncPending" class="ghost" type="button" :disabled="loading || paying" @click="retrySynchronization">Обновить данные сделки</button>

      <div v-if="!loading && supplier && !isCompleted" class="deal-supplier__body">
        <div class="deal-supplier__service">
          <span>Сервис поставщика</span>
          <strong>{{ cleanServiceTitle(supplier.service_title) }}</strong>
        </div>
        <label class="field deal-supplier__field">
          <span class="label">Номинал</span>
          <select
            v-model="nominalId"
            class="input input--select"
            :disabled="purchaseBlocked || purchaseLocked || preparing || paying"
            @change="resetPreparedPurchase"
          >
            <option value="">— выберите номинал —</option>
            <option v-for="nominal in supplier.nominals" :key="nominal.id" :value="String(nominal.id)">
              {{ nominal.title }}
            </option>
          </select>
        </label>
        <button
          class="btn deal-supplier__obtain"
          type="button"
          :disabled="purchaseBlocked || !nominalId || purchaseLocked || preparing || paying"
          @click="preparePurchase"
        >
          <span v-if="preparing" class="deal-supplier__spinner" aria-hidden="true"></span>
          {{ preparing ? 'Проверяем…' : 'Получить' }}
        </button>
      </div>

      <div v-if="purchase && purchase.state !== 'paid'" class="deal-supplier__result" :class="`is-${purchase.state || 'unknown'}`">
        <div>
          <span>{{ purchaseStateLabel }}</span>
          <strong>{{ purchase.nominal_title || selectedNominalTitle }}</strong>
          <small v-if="purchase.created_by">Оператор: {{ purchase.created_by }}</small>
        </div>
        <p v-if="purchase.state === 'processing'">Код будет показан здесь после подтверждения поставщиком. Повторная оплата не отправляется.</p>
        <p v-else-if="purchase.message && purchase.state !== 'checked'">{{ anonymizeSupplierText(purchase.message) }}</p>
      </div>

      <section v-if="paidPurchases.length" class="deal-supplier__vouchers" aria-labelledby="deal-supplier-vouchers-title">
        <div class="deal-supplier__vouchers-head">
          <div>
            <span>Ваучеры в сделке</span>
            <h5 id="deal-supplier-vouchers-title">Получено: {{ paidPurchases.length }}</h5>
          </div>
        </div>
        <ol class="deal-supplier__voucher-list">
          <li v-for="(item, index) in paidPurchases" :key="item.agent_transaction_id" class="deal-supplier__voucher">
            <span class="deal-supplier__voucher-index">{{ paidPurchases.length - index }}</span>
            <div class="deal-supplier__voucher-info">
              <strong>{{ item.nominal_title || item.nominal_id }}</strong>
              <small>{{ item.created_by || 'оператор не указан' }} · {{ formatDate(item.updated_at || item.created_at) }}</small>
            </div>
            <code>{{ item.gift_code }}</code>
            <button class="ghost ghost--small" type="button" @click="copyGiftCode(item)">
              {{ copiedTransactionId === item.agent_transaction_id ? 'Скопировано' : 'Копировать' }}
            </button>
          </li>
        </ol>
        <button v-if="!isCompleted" class="ghost deal-supplier__buy-more" type="button" :disabled="purchaseBlocked || purchaseLocked || preparing || paying" @click="startAnotherPurchase">
          + Купить ещё
        </button>
      </section>
    </template>
  </section>

  <teleport to="body">
    <div v-if="confirmationOpen" class="work-page work-modal-root modal-backdrop deal-supplier-modal-backdrop" @click.self="closeConfirmation">
      <section class="modal modal--auto deal-supplier-confirm" role="dialog" aria-modal="true" aria-labelledby="deal-supplier-confirm-title">
        <div class="modal__head panel__head panel__head--tight deal-supplier-confirm__head">
          <div>
            <p class="deal-supplier__eyebrow">Поставщик · подтверждение покупки</p>
            <h3 id="deal-supplier-confirm-title">Проверьте покупку</h3>
          </div>
          <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" @click="closeConfirmation">×</button>
        </div>
        <div class="modal__body deal-supplier-confirm__body">
          <p class="deal-supplier-confirm__service">
            <span>{{ cleanServiceTitle(prepared?.service_title || supplier?.service_title) }}</span>
            <span class="deal-supplier-confirm__nominal">{{ prepared?.nominal_title || selectedNominalTitle }}</span>
          </p>
          <!-- Закупочная цена остаётся в учёте, но не выводится в блоке ваучеров и подтверждении. -->
          <dl class="deal-supplier-confirm__details">
            <div><dt>Сделка</dt><dd>#{{ dealId }}</dd></div>
            <div><dt>К покупке, шт.</dt><dd>1</dd></div>
            <div :class="{ 'is-error': !prepared?.success }"><dt>Доступность</dt><dd>{{ preparedAvailability }}</dd></div>
          </dl>
          <div class="deal-supplier-confirm__actions">
            <button class="ghost" type="button" :disabled="paying" @click="closeConfirmation">Отмена</button>
            <button class="btn" type="button" :disabled="purchaseBlocked || !prepared?.success || paying" @click="payPurchase">
              {{ paying ? 'Покупаем…' : 'Купить' }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
import { useAuth } from '../../../stores/auth'

const props = defineProps({
  deal: { type: Object, required: true },
  editing: { type: Boolean, default: false },
  syncDeal: { type: Function, default: null },
})
const emit = defineEmits(['busy-change'])

const auth = useAuth()
const loading = ref(false)
const error = ref('')
const supplier = ref(null)
const nominalId = ref('')
const prepared = ref(null)
const purchase = ref(null)
const purchases = ref([])
const preparing = ref(false)
const paying = ref(false)
const copiedTransactionId = ref('')
const confirmationOpen = ref(false)
let statusTimer = null
let generation = 0
let disposed = false
const syncPending = ref(false)
const synchronizing = ref(false)

const dealId = computed(() => Number(props.deal?.deal_id || 0))
const regionCode = computed(() => String(props.deal?.region_code || '').trim().toUpperCase())
const isSupportedRegion = computed(() => ['TR', 'PL'].includes(regionCode.value))
const regionLabel = computed(() => regionCode.value === 'TR' ? 'Турция' : 'Польша')
const selectedNominalTitle = computed(() => supplier.value?.nominals?.find((item) => String(item.id) === nominalId.value)?.title || '')
const purchaseLocked = computed(() => String(purchase.value?.state || '') === 'processing')
// Сохранённое завершение на сервере блокирует покупку даже при устаревшей локальной карточке.
const isCompleted = computed(() => props.deal?.flow_status_code === 'completed' || supplier.value?.flow_status_code === 'completed')
const blockedReason = computed(() => {
  // Покупаем только по сохранённой карточке, а не по локально изменённым региону и статусу.
  if (isCompleted.value) return 'Покупка в завершённой сделке недоступна'
  if (props.editing) return 'Сначала сохраните изменения сделки'
  if (String(props.deal?.flow_status_code || supplier.value?.flow_status_code || '') === 'draft') return 'Покупка в черновике недоступна'
  if (supplier.value?.purchase_allowed === false) return 'Покупка для этой сделки недоступна'
  if (syncPending.value) return 'Покупка сохранена. Обновите данные сделки перед продолжением'
  return ''
})
const purchaseBlocked = computed(() => !dealId.value || loading.value || synchronizing.value || Boolean(blockedReason.value))
const paidPurchases = computed(() => purchases.value.filter((item) => item?.state === 'paid' && item?.gift_code))
const preparedAvailability = computed(() => prepared.value?.success ? 'Готов к покупке' : (anonymizeSupplierText(prepared.value?.message) || 'Поставщик не подтвердил доступность'))
const purchaseStateLabel = computed(() => stateLabel(purchase.value?.state))

function mapError(value, fallback) {
  // Показываем безопасный обезличенный ответ API рядом с блоком поставщика.
  return anonymizeSupplierText(value?.message || fallback)
}

function anonymizeSupplierText(value) {
  // Скрываем техническое название интеграции во всех полученных от поставщика текстах.
  return String(value || '')
    .replace(/supplier\s+hub/gi, 'поставщик')
    .replace(/interhub/gi, 'поставщик')
}

function cleanServiceTitle(value) {
  // Убираем технический префикс po_, сохраняя название и регион поставщика.
  return anonymizeSupplierText(String(value || 'PlayStation').replace(/^po_/i, '').trim())
}

function stateLabel(state) {
  // Переводим внутреннее состояние покупки в короткую подпись оператора.
  return ({ checked: 'Готово к покупке', processing: 'В обработке', paid: 'Код получен', failed: 'Ошибка' })[String(state || '')] || 'Подготовлено'
}

function formatDate(value) {
  // Выводим время истории в локальном формате рабочего интерфейса.
  if (!value) return '—'
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function stopStatusPolling() {
  // Останавливаем опрос при смене сделки или закрытии компонента.
  if (statusTimer) window.clearTimeout(statusTimer)
  statusTimer = null
}

function scheduleStatusPolling() {
  // Перечитываем только связанную сделку, пока сервер безопасно сверяет уже отправленную оплату.
  stopStatusPolling()
  if (disposed || props.editing || purchase.value?.state !== 'processing' || !dealId.value) return
  statusTimer = window.setTimeout(async () => {
    await loadSupplier({ silent: true })
    scheduleStatusPolling()
  }, 3000)
}

async function synchronizeDeal(targetId) {
  // Обновляем всю карточку и её baseline, не подмешивая новую версию к старым полям.
  if (!props.syncDeal) return
  const requestGeneration = generation
  synchronizing.value = true
  try {
    await props.syncDeal(targetId)
    if (!disposed && requestGeneration === generation) syncPending.value = false
  } catch {
    if (!disposed && requestGeneration === generation) syncPending.value = true
    throw new Error('Ваучеры сохранены. Не удалось обновить данные сделки; нажмите «Обновить данные сделки».')
  } finally {
    if (!disposed && requestGeneration === generation) synchronizing.value = false
  }
}

async function loadSupplier({ silent = false } = {}) {
  // Запоздалый ответ другой сделки или региона не меняет текущий блок.
  if (!dealId.value || !isSupportedRegion.value || props.editing) return
  const targetId = dealId.value
  const requestGeneration = generation
  if (!silent) loading.value = true
  error.value = ''
  try {
    const data = await apiGet(`/deals/${targetId}/interhub`, { token: auth.state.token })
    if (disposed || requestGeneration !== generation) return
    supplier.value = data
    purchases.value = Array.isArray(data?.purchases) ? data.purchases : (data?.purchase ? [data.purchase] : [])
    purchase.value = purchases.value.find((item) => ['checked', 'processing', 'failed'].includes(String(item?.state || ''))) || null
    if (purchase.value?.nominal_id) nominalId.value = String(purchase.value.nominal_id)
    if (Number(data?.lock_version) > Number(props.deal?.lock_version || 0)) await synchronizeDeal(targetId)
    if (disposed || requestGeneration !== generation) return
    if (purchase.value?.state === 'processing') scheduleStatusPolling()
  } catch (requestError) {
    if (disposed || requestGeneration !== generation) return
    error.value = mapError(requestError, 'Не удалось загрузить номиналы поставщика')
  } finally {
    if (!disposed && requestGeneration === generation && !silent) loading.value = false
  }
}

async function retrySynchronization() {
  // Повторяем только чтение карточки, никогда не повторяя оплату после ошибки обновления.
  if (loading.value || paying.value) return
  const targetId = dealId.value
  loading.value = true
  try {
    await synchronizeDeal(targetId)
    if (!disposed && dealId.value === targetId) await loadSupplier({ silent: true })
  } catch (requestError) {
    if (!disposed && dealId.value === targetId) error.value = mapError(requestError, 'Не удалось обновить сделку')
  } finally {
    if (!disposed && dealId.value === targetId) loading.value = false
  }
}

function resetPreparedPurchase() {
  // Сбрасываем прежний check после смены номинала, чтобы оплатить можно было только актуальный выбор.
  prepared.value = null
  confirmationOpen.value = false
  copiedTransactionId.value = ''
}

async function preparePurchase() {
  // Проверяем сохранённую версию; смена режима или региона отменяет старое подтверждение.
  if (purchaseBlocked.value || !nominalId.value || preparing.value || paying.value || purchaseLocked.value) return
  const targetId = dealId.value
  const requestGeneration = generation
  preparing.value = true
  error.value = ''
  try {
    const result = await apiPost(`/deals/${targetId}/interhub/prepare`, {
      nominal_id: nominalId.value, lock_version: Number(props.deal.lock_version),
    }, { token: auth.state.token })
    if (disposed || requestGeneration !== generation) return
    prepared.value = result
    if (result?.state === 'paid' || result?.state === 'processing') {
      purchase.value = result
      await loadSupplier({ silent: true })
      return
    }
    confirmationOpen.value = true
  } catch (requestError) {
    if (!disposed && requestGeneration === generation) error.value = mapError(requestError, 'Не удалось подготовить покупку')
  } finally {
    if (!disposed && requestGeneration === generation) preparing.value = false
  }
}

function closeConfirmation() {
  // Закрываем только подтверждение, сохраняя выбранный номинал в форме сделки.
  if (paying.value) return
  confirmationOpen.value = false
}

async function payPurchase() {
  // Отправляем конкретный check с его версией сделки; код сохраняем до обновления формы.
  if (purchaseBlocked.value || !prepared.value?.success || paying.value) return
  const targetId = dealId.value
  const requestGeneration = generation
  paying.value = true
  error.value = ''
  try {
    const result = await apiPost(
      `/deals/${targetId}/interhub/pay`,
      { agent_transaction_id: prepared.value.agent_transaction_id, lock_version: prepared.value.lock_version },
      { token: auth.state.token },
    )
    if (disposed || requestGeneration !== generation) return
    purchase.value = result
    const purchaseIndex = purchases.value.findIndex((item) => item.agent_transaction_id === result?.agent_transaction_id)
    if (purchaseIndex >= 0) purchases.value.splice(purchaseIndex, 1, result)
    else if (result) purchases.value.unshift(result)
    confirmationOpen.value = false
    if (result?.state === 'paid') await synchronizeDeal(targetId)
    if (!disposed && requestGeneration === generation) scheduleStatusPolling()
  } catch (requestError) {
    if (!disposed && requestGeneration === generation) error.value = mapError(requestError, 'Не удалось подтвердить покупку')
  } finally {
    if (!disposed && requestGeneration === generation) paying.value = false
  }
}

function startAnotherPurchase() {
  // Очищаем только форму новой покупки, сохраняя все ранее выданные ваучеры в сделке.
  if (purchaseBlocked.value || purchaseLocked.value || preparing.value || paying.value) return
  nominalId.value = ''
  prepared.value = null
  purchase.value = null
  confirmationOpen.value = false
  error.value = ''
}

async function copyGiftCode(item) {
  // Копируем код выбранного ваучера, поэтому одинаковые номиналы не смешиваются между собой.
  const value = String(item?.gift_code || '')
  if (!value) return
  if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value)
  else {
    // Старый fallback нужен для рабочих браузеров без Clipboard API.
    const area = document.createElement('textarea')
    area.value = value
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  copiedTransactionId.value = String(item?.agent_transaction_id || '')
  window.setTimeout(() => { copiedTransactionId.value = '' }, 1600)
}

watch([dealId, regionCode, () => props.editing, () => props.deal?.flow_status_code], () => {
  // Смена карточки, статуса или режима отменяет локальный check, но не оплату на сервере.
  generation += 1
  stopStatusPolling()
  supplier.value = null
  nominalId.value = ''
  prepared.value = null
  purchase.value = null
  purchases.value = []
  confirmationOpen.value = false
  preparing.value = false
  paying.value = false
  loading.value = false
  syncPending.value = false
  synchronizing.value = false
  error.value = ''
  if (dealId.value && isSupportedRegion.value && !props.editing) void loadSupplier()
}, { immediate: true })

watch(() => [dealId.value, loading.value || preparing.value || paying.value || purchaseLocked.value || syncPending.value || synchronizing.value], ([targetId, busy]) => {
  // Не даём шапке формы редактировать или удалять сделку до синхронизации покупки.
  emit('busy-change', { dealId: targetId, busy })
}, { immediate: true, flush: 'sync' })

onBeforeUnmount(() => {
  // Закрытие карточки не отменяет оплату; её результат восстановится при следующем открытии.
  disposed = true
  generation += 1
  stopStatusPolling()
  emit('busy-change', { dealId: dealId.value, busy: false })
})

</script>

<style scoped>
.deal-supplier { grid-column: 1 / -1; position: relative; display: grid; gap: 14px; margin-top: 4px; padding: 16px; overflow: hidden; border: 1px solid rgba(232, 134, 19, .28); border-radius: 14px; background: linear-gradient(135deg, rgba(232, 134, 19, .1), rgba(16, 22, 38, .94) 48%), repeating-linear-gradient(135deg, transparent 0 11px, rgba(255, 255, 255, .015) 11px 12px); box-shadow: inset 3px 0 0 #e88613; }
.deal-supplier__head, .deal-supplier__identity, .deal-supplier__body { display: flex; align-items: center; }
.deal-supplier__head { justify-content: space-between; gap: 16px; }
.deal-supplier__identity { gap: 11px; }.deal-supplier__mark { display: grid; place-items: center; width: 38px; height: 38px; border: 1px solid rgba(232, 134, 19, .52); border-radius: 10px; background: #e88613; color: #111827; font-weight: 900; letter-spacing: -.06em; transform: rotate(-3deg); }
.deal-supplier__eyebrow { margin: 0 0 3px; color: #e9a64d; font-size: 10px; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }.deal-supplier h4 { margin: 0; color: var(--ink, #f4f7ff); font-size: 17px; }.deal-supplier__body { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(190px, .85fr) auto; gap: 12px; align-items: end; }.deal-supplier__service { display: grid; gap: 5px; min-height: 42px; padding: 9px 12px; border-left: 3px solid #e88613; background: rgba(255, 255, 255, .045); }.deal-supplier__service span { color: var(--muted, #9ca3af); font-size: 11px; }.deal-supplier__service strong { color: var(--ink, #f4f7ff); font-size: 13px; }.deal-supplier__field { margin: 0; }.deal-supplier__obtain { min-width: 132px; min-height: 42px; }.deal-supplier__spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: deal-supplier-spin .7s linear infinite; }.deal-supplier__save-note { display: grid; gap: 4px; padding: 12px 14px; border: 1px dashed rgba(232, 134, 19, .36); border-radius: 10px; color: var(--muted, #b5bfd3); }.deal-supplier__save-note strong { color: var(--ink, #f4f7ff); }.deal-supplier__muted, .deal-supplier__error { margin: 0; }.deal-supplier__error { color: #ffabab; }.deal-supplier__result { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px 14px; border-left: 3px solid #d69a4a; background: rgba(214, 154, 74, .09); }.deal-supplier__result.is-paid { border-left-color: #59e3b1; background: rgba(89, 227, 177, .09); }.deal-supplier__result.is-processing { border-left-color: #7aa7ff; background: rgba(122, 167, 255, .08); }.deal-supplier__result > div:first-child { display: grid; gap: 3px; }.deal-supplier__result span, .deal-supplier__result small { color: var(--muted, #b5bfd3); }.deal-supplier__result strong { color: var(--ink, #f4f7ff); }.deal-supplier__result p { grid-column: 1 / -1; margin: 0; color: var(--muted, #b5bfd3); }
.deal-supplier__vouchers { display: grid; gap: 10px; padding-top: 2px; }.deal-supplier__vouchers-head { display: flex; justify-content: space-between; gap: 16px; align-items: end; }.deal-supplier__vouchers-head span { color: var(--muted, #9ca3af); font-size: 11px; }.deal-supplier__vouchers-head h5 { margin: 3px 0 0; color: var(--ink, #f4f7ff); font-size: 15px; }.deal-supplier__voucher-list { display: grid; gap: 7px; margin: 0; padding: 0; list-style: none; }.deal-supplier__voucher { display: grid; grid-template-columns: 28px minmax(150px, 1fr) minmax(160px, auto) auto; gap: 10px; align-items: center; padding: 10px 11px; border: 1px solid rgba(89, 227, 177, .16); border-left: 3px solid #59e3b1; border-radius: 8px; background: rgba(89, 227, 177, .055); }.deal-supplier__voucher-index { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: rgba(89, 227, 177, .14); color: #8cf0ca; font-size: 11px; font-weight: 800; }.deal-supplier__voucher-info { display: grid; gap: 2px; }.deal-supplier__voucher-info strong { color: var(--ink, #f4f7ff); }.deal-supplier__voucher-info small { color: var(--muted, #9ca3af); }.deal-supplier__voucher code { overflow-wrap: anywhere; color: #8cf0ca; font-size: 13px; font-weight: 800; letter-spacing: .04em; }.deal-supplier__buy-more { justify-self: start; border-color: rgba(232, 134, 19, .42); color: #f0b86e; }
.deal-supplier-modal-backdrop { --modal-bg: #101626; --modal-text: #f4f7ff; --ink: #f4f7ff; --muted: #b5bfd3; --ghost-bg: rgba(255,255,255,.08); --ghost-text: #f4f7ff; --ghost-border: rgba(255,255,255,.18); z-index: 90; align-items: center; padding: 16px; }.deal-supplier-confirm { width: min(540px, calc(100vw - 32px)); min-height: 0; max-height: 90vh; padding: 16px; overflow: auto; }.deal-supplier-confirm__head { margin: 0; padding: 0 0 13px; border-bottom: 1px solid rgba(181,194,219,.16); background: transparent; }.deal-supplier-confirm__head h3 { margin: 0; color: #f4f7ff; font-size: 23px; }.deal-supplier-confirm__body { display: grid; gap: 14px; padding: 18px 0 0; }.deal-supplier-confirm__service { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0; color: #f4f7ff; font-weight: 800; }.deal-supplier-confirm__nominal { padding: 4px 9px; border: 1px solid rgba(232,134,19,.55); background: rgba(232,134,19,.1); color: #f4c57f; font-size: 12px; }.deal-supplier-confirm__details { display: grid; gap: 8px; margin: 0; }.deal-supplier-confirm__details > div { display: grid; grid-template-columns: minmax(145px,.8fr) minmax(0,1.2fr); gap: 14px; padding: 12px 14px; border-left: 3px solid #e88613; background: rgba(232,134,19,.08); }.deal-supplier-confirm__details > div.is-error { border-left-color: #d45f5f; background: rgba(212,95,95,.1); }.deal-supplier-confirm__details dt { color: #b5bfd3; }.deal-supplier-confirm__details dd { margin: 0; color: #f4f7ff; font-weight: 800; text-align: right; }.deal-supplier-confirm__actions { display: flex; justify-content: flex-end; gap: 10px; }
@keyframes deal-supplier-spin { to { transform: rotate(360deg); } }
@media (max-width: 760px) { .deal-supplier__body { grid-template-columns: 1fr; }.deal-supplier__obtain { width: 100%; }.deal-supplier__result { grid-template-columns: 1fr; }.deal-supplier__vouchers-head { align-items: start; flex-direction: column; }.deal-supplier__voucher { grid-template-columns: 28px minmax(0, 1fr); }.deal-supplier__voucher code, .deal-supplier__voucher .ghost { grid-column: 2; }.deal-supplier-confirm__details > div { grid-template-columns: 1fr; gap: 4px; }.deal-supplier-confirm__details dd { text-align: left; } }
</style>
