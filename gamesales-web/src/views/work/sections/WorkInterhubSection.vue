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
            <tr v-for="service in filteredServices" :key="service.service_id">
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
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
.interhub-catalog__head { align-items: end; border-bottom: 1px solid rgba(245, 158, 11, .32); }
.interhub-catalog__eyebrow { margin: 0 0 4px; color: #b86b12; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.interhub-catalog__title { margin: 0; letter-spacing: -.03em; }
.interhub-catalog__lead { max-width: 680px; margin: 0 0 20px; color: var(--muted, #7a766f); }
.interhub-catalog__toolbar { display: flex; gap: 16px; align-items: end; justify-content: space-between; margin-bottom: 18px; }
.interhub-catalog__search { width: min(460px, 100%); }
.interhub-catalog__stats { display: grid; min-width: 120px; padding: 8px 12px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .08); }
.interhub-catalog__stats strong { font-size: 20px; line-height: 1; }
.interhub-catalog__stats span, .interhub-catalog__id { color: var(--muted, #7a766f); font-size: 12px; }
.interhub-catalog__id { display: block; margin-top: 3px; font-family: ui-monospace, monospace; }
.interhub-catalog__type { display: inline-flex; padding: 3px 7px; border: 1px solid rgba(232, 134, 19, .35); color: #9b570d; font-size: 12px; font-weight: 700; }
@media (max-width: 680px) { .interhub-catalog__toolbar { align-items: stretch; flex-direction: column; } .interhub-catalog__search { width: 100%; } .interhub-catalog__stats { width: fit-content; } }
</style>
