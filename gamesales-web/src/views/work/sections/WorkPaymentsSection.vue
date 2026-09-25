<template>
  <section class="panel panel--wide work-payments" aria-labelledby="work-payments-title">
    <header class="work-payments__header">
      <div>
        <h2 id="work-payments-title">Платежи</h2>
        <p>Выберите поставщика для работы с каталогом и покупками.</p>
      </div>
      <span class="work-payments__count">Поставщиков: {{ providers.length }}</span>
    </header>

    <div class="work-payments__providers" role="group" aria-label="Поставщик платежей" :aria-describedby="switchLocked ? 'work-payments-busy' : undefined">
      <button
        v-for="provider in providers"
        :key="provider.id"
        type="button"
        class="work-payments__provider"
        :class="{ 'is-active': activeProviderId === provider.id }"
        :aria-pressed="activeProviderId === provider.id"
        :disabled="switchLocked && activeProviderId !== provider.id"
        @click="selectProvider(provider.id)"
      >
        <span class="work-payments__provider-mark" aria-hidden="true">{{ provider.mark }}</span>
        <span class="work-payments__provider-copy">
          <strong>{{ provider.name }}</strong>
          <small>{{ provider.caption }}</small>
        </span>
        <span class="work-payments__selected" aria-hidden="true">{{ activeProviderId === provider.id ? '✓' : '' }}</span>
      </button>
    </div>
    <p v-if="switchLocked" id="work-payments-busy" class="work-payments__busy" role="status">Дождитесь результата операции {{ activeProvider.name }}, чтобы сменить поставщика.</p>

    <div class="work-payments__content">
      <WorkInterhubSection v-if="activeProviderId === 'interhub'" :ctx="ctx" embedded />
      <WorkAirpaySection v-else-if="activeProviderId === 'airpay'" :token="ctx.token" :can-prepare="Boolean(ctx.canPrepareAirpay)" :can-view-history="Boolean(ctx.canManagePrices || ctx.canPay)" @busy-change="airpayBusy = $event" />
      <section v-else class="work-payments__pending" aria-labelledby="work-payments-pending-title">
        <span class="work-payments__pending-mark" aria-hidden="true">{{ activeProvider.mark }}</span>
        <span class="work-payments__status">Ожидает подключения</span>
        <h3 id="work-payments-pending-title">{{ activeProvider.name }}</h3>
        <p>Каталог, баланс и покупки появятся после подключения поставщика.</p>
        <button class="ghost" type="button" @click="selectProvider('interhub')">Перейти к Interhub</button>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, h, ref } from 'vue'
import WorkInterhubSection from './WorkInterhubSection.vue'
// Отдельный модуль Airpay загружается только по выбору, не мешая начальному экрану Interhub.
const WorkAirpaySection = defineAsyncComponent({
  loader: () => import('./WorkAirpaySection.vue'),
  timeout: 10000,
  errorComponent: { render() {
    // Ошибка загрузки оставляет переключатель доступным для возврата к рабочему поставщику.
    return h('p', { class: 'error', role: 'alert' }, 'Не удалось открыть Airpay. Обновите страницу или вернитесь к Interhub.')
  } },
})

const props = defineProps({
  ctx: { type: Object, required: true },
})

// Список задаёт порядок и подписи выбора; новых поставщиков добавляем здесь.
const providers = [
  { id: 'interhub', name: 'Interhub', mark: 'IH', caption: 'Каталог и покупки' },
  { id: 'airpay', name: 'Airpay', mark: 'AP', caption: 'Каталог и покупки' },
]
const activeProviderId = ref('interhub')
const airpayBusy = ref(false)
const activeProvider = computed(() => providers.find(provider => provider.id === activeProviderId.value))
const switchLocked = computed(() => {
  // Не даём закрыть форму, пока запрос или уже отправленный платёж ещё не завершён.
  const ctx = props.ctx
  return Boolean(airpayBusy.value || ctx.calculationLoading || ctx.checkLoading || ctx.paymentLoading || Number(ctx.payment?.status) === 1)
})

function selectProvider(providerId) {
  // Убираем прежнее подтверждение покупки: расчёт одного поставщика не должен перейти к другому.
  if (switchLocked.value || providerId === activeProviderId.value || !providers.some(provider => provider.id === providerId)) return
  props.ctx.resetPaymentFlow()
  activeProviderId.value = providerId
}
</script>

<style scoped>
.work-payments { min-width: 0; }
.work-payments__header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.work-payments__header h2 { margin: 0; font-size: 24px; }
.work-payments__header p { margin: 6px 0 0; color: var(--muted, #9da9bf); font-size: 13px; line-height: 1.5; }
.work-payments__count { color: var(--muted, #9da9bf); font-size: 12px; white-space: nowrap; }
.work-payments__providers { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.work-payments__provider { display: flex; flex: 0 1 260px; align-items: center; gap: 12px; min-width: 0; padding: 14px; border: 1px solid var(--stroke, #364055); border-radius: 12px; background: transparent; color: var(--ink, #e5eaf5); text-align: left; font: inherit; cursor: pointer; }
.work-payments__provider:hover:not(:disabled) { border-color: #e88613; }
.work-payments__provider.is-active { border-color: #e88613; background: rgba(232, 134, 19, .09); box-shadow: inset 0 -2px 0 #e88613; }
.work-payments__provider:focus-visible { outline: 2px solid #e88613; outline-offset: 3px; }
.work-payments__provider:disabled { opacity: .45; cursor: wait; }
.work-payments__provider-mark, .work-payments__pending-mark { display: grid; flex-shrink: 0; place-items: center; width: 38px; height: 38px; border: 1px solid var(--stroke, #364055); border-radius: 10px; font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.is-active .work-payments__provider-mark { border-color: rgba(232, 134, 19, .35); color: #f6c66e; }
.work-payments__provider-copy { display: grid; gap: 4px; }
.work-payments__provider-copy strong { font-size: 15px; }
.work-payments__provider-copy small { color: var(--muted, #9da9bf); font-size: 12px; }
.work-payments__selected { width: 16px; margin-left: auto; color: #f6c66e; font-weight: 800; }
.work-payments__busy { margin: 12px 0 0; color: #f6c66e; font-size: 13px; }
.work-payments__content { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--stroke, #364055); }
.work-payments__pending { display: flex; flex-direction: column; align-items: center; padding: 48px 16px; text-align: center; }
.work-payments__pending-mark { width: 64px; height: 64px; margin-bottom: 20px; border-radius: 18px; font-size: 20px; color: var(--muted, #9da9bf); }
.work-payments__status { padding: 5px 10px; border: 1px solid var(--stroke, #364055); border-radius: 20px; color: var(--muted, #9da9bf); font-size: 11px; }
.work-payments__pending h3 { margin: 16px 0 0; font-size: 24px; }
.work-payments__pending p { max-width: 360px; margin: 10px 0 24px; color: var(--muted, #9da9bf); font-size: 14px; line-height: 1.6; }
@media (max-width: 600px) {
  .work-payments__header { align-items: flex-start; }
  .work-payments__count { display: none; }
  .work-payments__providers { gap: 8px; }
  .work-payments__provider { flex: 1 1 180px; padding: 12px; }
  .work-payments__pending { padding: 32px 8px; }
}
</style>
