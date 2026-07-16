<template>
  <section class="panel panel--wide interhub-catalog">
    <div class="panel__head interhub-catalog__head">
      <div>
        <p class="interhub-catalog__eyebrow">InterHub · агентский каталог</p>
        <h2 class="interhub-catalog__title">Платежи</h2>
      </div>
      <button class="deal-refresh-btn" type="button" :disabled="ctx.loading" aria-label="Обновить каталог InterHub" @click="ctx.reload">
        <span class="deal-refresh-btn__content">↻</span>
      </button>
    </div>

    <div class="panel__body">
      <p class="interhub-catalog__lead">Выберите услугу, чтобы на следующем этапе проверить реквизиты и рассчитать платёж. Оплата пока отключена.</p>
      <div class="interhub-catalog__balance"><span>Баланс InterHub</span><strong>{{ formatBalance(ctx.balance, ctx.currency) }}</strong><small>Агентский счёт</small></div>
      <p v-if="ctx.error" class="error">{{ ctx.error }}</p>

      <div class="interhub-catalog__toolbar">
        <label class="interhub-catalog__search">
          <span class="label">Поиск услуги</span>
          <input class="input" type="search" :value="ctx.search" placeholder="Название или категория" @input="ctx.setSearchFromEvent" />
        </label>
        <div class="interhub-catalog__stats" aria-label="Статистика каталога">
          <strong>{{ filteredServices.length }}</strong>
          <span>из {{ ctx.services.length }} услуг</span>
        </div>
      </div>

      <div class="table-wrap interhub-catalog__table-wrap">
        <table class="table table--compact">
          <thead>
            <tr>
              <th>Услуга</th>
              <th>Категория</th>
              <th>Тип</th>
              <th>Лимит</th>
              <th>Реквизиты</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="ctx.loading">
              <td colspan="5" class="muted">Загружаем каталог InterHub…</td>
            </tr>
            <tr v-else-if="!filteredServices.length">
              <td colspan="5" class="muted">Услуги по этому запросу не найдены.</td>
            </tr>
            <tr v-for="service in filteredServices" :key="service.service_id" class="interhub-catalog__row" :class="{ 'is-selected': selectedService?.service_id === service.service_id }" @click="selectService(service)">
              <td>
                <strong>{{ service.title }}</strong>
                <span class="interhub-catalog__id">#{{ service.service_id }}</span>
              </td>
              <td>{{ service.category || '—' }}</td>
              <td><span class="interhub-catalog__type">{{ formatType(service.type) }}</span></td>
              <td>{{ formatLimit(service) }}</td>
              <td>{{ formatFields(service.fields) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <form v-if="selectedService" class="interhub-catalog__form" @submit.prevent="calculate">
        <div><p class="interhub-catalog__eyebrow">Шаг 1 · проверка</p><h3>{{ selectedService.title }}</h3></div>
        <label class="field"><span class="label">{{ accountLabel }}</span><input v-model.trim="account" class="input" required /></label>
        <label v-if="needsAmount" class="field"><span class="label">Сумма</span><input v-model="amount" class="input" type="number" min="0.01" step="0.01" required /></label>
        <label v-for="field in selectedService.fields" :key="field.name" class="field"><span class="label">{{ field.name }}<i v-if="field.required"> *</i></span><select v-if="field.type === 'LIST'" v-model="params[field.name]" class="input" :required="field.required"><option value="">Выберите значение</option><option v-for="option in field.value_list" :key="option.id" :value="option.id">{{ option.title }}</option></select><input v-else v-model.trim="params[field.name]" class="input" :required="field.required" /></label>
        <button class="btn" :disabled="ctx.calculationLoading">{{ ctx.calculationLoading ? 'Проверяем…' : 'Рассчитать и проверить' }}</button>
        <p v-if="ctx.calculation" class="interhub-catalog__result">{{ ctx.calculation.success ? 'Можно продолжать' : 'Проверка не пройдена' }} · {{ ctx.calculation.message || 'Ответ получен' }}</p>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

// Контекст содержит каталог и действия загрузки, чтобы экран не знал деталей API.
const props = defineProps({
  ctx: { type: Object, required: true },
})

const filteredServices = computed(() => {
  // Фильтруем по названию и категории без повторного запроса к провайдеру.
  const query = String(props.ctx.search || '').trim().toLowerCase()
  const services = Array.isArray(props.ctx.services) ? props.ctx.services : []
  if (!query) return services
  return services.filter((service) => `${service?.title || ''} ${service?.category || ''}`.toLowerCase().includes(query))
})
const selectedService = ref(null)
const account = ref('')
const amount = ref('')
const params = reactive({})
const needsAmount = computed(() => ['TOP_UP'].includes(String(selectedService.value?.type || '').toUpperCase()) && !selectedService.value?.fields?.some((field) => field?.name === 'nominal'))
const accountLabel = computed(() => String(selectedService.value?.title || '').toLowerCase().includes('playstation') ? 'PSN ID / логин' : 'Аккаунт или номер')

function selectService(service) {
  // Открываем форму выбранной услуги и очищаем реквизиты от предыдущей операции.
  selectedService.value = service
  account.value = ''
  amount.value = ''
  Object.keys(params).forEach((key) => delete params[key])
}

function calculate() {
  // Передаем только заполненные параметры для безопасного предварительного расчета.
  const payload = { service_id: selectedService.value.service_id, account: account.value, params: { ...params } }
  if (needsAmount.value) payload.amount = Number(amount.value)
  props.ctx.calculate(payload)
}

function formatType(type) {
  // Делаем технический тип платежа понятнее оператору, сохраняя исходный смысл.
  const labels = {
    TOP_UP: 'Пополнение',
    TOP_UP_FIXED: 'Фикс. номинал',
    VOUCHER: 'Ваучер',
    PIN: 'PIN-код',
  }
  return labels[String(type || '').toUpperCase()] || String(type || '—')
}

function formatLimit(service) {
  // Показываем диапазон только когда провайдер передал хотя бы один лимит.
  const min = Number(service?.min_amount || 0)
  const max = Number(service?.max_amount || 0)
  if (!min && !max) return '—'
  if (!max) return `от ${min}`
  if (!min) return `до ${max}`
  return `${min}–${max}`
}

function formatFields(fields) {
  // Кратко показываем обязательные реквизиты до открытия будущей формы оплаты.
  const items = Array.isArray(fields) ? fields : []
  if (!items.length) return 'Только аккаунт'
  return items.filter((field) => field?.required).map((field) => field.name).join(', ') || 'Дополнительные'
}

function formatBalance(value, currency) {
  // Разделяем тысячи и переводим валютный код в привычное для оператора обозначение.
  const amount = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value || 0)).replace(/\u00A0/g, ' ')
  const symbols = { RUB: '₽', TRY: '₺', USD: '$', EUR: '€' }
  return `${amount} ${symbols[currency] || currency || ''}`.trim()
}
</script>

<style scoped>
.interhub-catalog__head { align-items: end; border-bottom: 1px solid rgba(245, 158, 11, .32); }
.interhub-catalog__eyebrow { margin: 0 0 4px; color: #b86b12; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.interhub-catalog__title { margin: 0; letter-spacing: -.03em; }
.interhub-catalog__lead { max-width: 680px; margin: 0 0 20px; color: var(--muted, #7a766f); }
.interhub-catalog__balance { display: inline-grid; gap: 3px; margin: 0 0 18px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }.interhub-catalog__balance span, .interhub-catalog__balance small { color: var(--muted, #7a766f); font-size: 12px; }.interhub-catalog__balance strong { font-size: 20px; }
.interhub-catalog__toolbar { display: flex; gap: 16px; align-items: end; justify-content: space-between; margin-bottom: 18px; }
.interhub-catalog__search { width: min(460px, 100%); }
.interhub-catalog__stats { display: grid; min-width: 120px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }
.interhub-catalog__stats strong { font-size: 20px; line-height: 1; }
.interhub-catalog__stats span, .interhub-catalog__id { color: var(--muted, #7a766f); font-size: 12px; }
.interhub-catalog__id { display: block; margin-top: 3px; font-family: ui-monospace, monospace; }
.interhub-catalog__type { display: inline-flex; padding: 3px 7px; border: 1px solid rgba(232, 134, 19, .35); color: #9b570d; font-size: 12px; font-weight: 700; }
.interhub-catalog__row { cursor: pointer; }.interhub-catalog__row.is-selected td { background: rgba(232, 134, 19, .08); }.interhub-catalog__form { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; align-items: end; margin-top: 22px; padding: 18px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); }.interhub-catalog__form h3 { margin: 0; }.interhub-catalog__result { margin: 0; font-weight: 700; }
@media (max-width: 680px) { .interhub-catalog__toolbar { align-items: stretch; flex-direction: column; } .interhub-catalog__search { width: 100%; } .interhub-catalog__stats { width: fit-content; } }
</style>
