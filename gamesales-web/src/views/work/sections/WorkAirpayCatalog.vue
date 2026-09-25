<template>
  <section class="airpay-catalog" aria-label="Каталог услуг Airpay">
    <header v-if="!embedded" class="airpay-catalog__header">
      <div><h4 id="airpay-catalog-title">Каталог услуг</h4><p>Выберите услугу, чтобы посмотреть её параметры.</p></div>
      <button class="ghost" type="button" :disabled="loading" @click="loadCatalog">{{ loading ? 'Загружаем…' : 'Обновить каталог' }}</button>
    </header>
    <p v-if="loading" class="muted" role="status">Загружаем услуги Airpay…</p>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="configured === false" class="muted">Каталог будет доступен после настройки подключения Airpay.</p>
    <template v-else-if="configured">
      <div class="supplier-catalog__toolbar airpay-catalog__filters">
        <label class="supplier-catalog__search"><span class="label">Поиск услуги</span><input v-model="search" class="input" type="search" :disabled="preparationBusy" placeholder="Название, код или страна" /></label>
        <button class="ghost supplier-catalog__sort" type="button" :disabled="preparationBusy" @click="toggleSort">По названию: {{ sortDirection === 'asc' ? 'А–Я' : 'Я–А' }}</button>
        <label class="airpay-catalog__group"><span class="label">Группа</span><select v-model="group" class="input" :disabled="preparationBusy" aria-label="Группа услуг"><option value="">Все группы</option><option v-for="name in groups" :key="name" :value="name">{{ name }}</option></select></label>
        <div class="supplier-catalog__stats" role="status" aria-label="Статистика каталога"><strong>{{ filteredServices.length }}</strong><span>из {{ services.length }} услуг</span></div>
      </div>
      <p v-if="!services.length" class="muted">Airpay пока не вернул доступных услуг для этого агента.</p>
      <div v-else-if="!filteredServices.length" class="airpay-catalog__empty"><p>Услуги по этим условиям не найдены.</p><button class="ghost" type="button" @click="resetFilters">Сбросить фильтры</button></div>
      <div v-else class="table-wrap supplier-table-wrap airpay-catalog__table">
        <table class="table table--compact table--supplier">
          <thead><tr><th>Услуга</th><th>Группа</th><th>Страна</th><th>Сумма платежа</th></tr></thead>
          <tbody><tr v-for="service in pagedServices" :key="service.service_id" :class="{ 'is-selected': selectedService?.service_id === service.service_id }">
            <td><button class="airpay-catalog__service" type="button" :disabled="preparationBusy" :aria-expanded="selectedService?.service_id === service.service_id" :aria-controls="selectedService?.service_id === service.service_id ? 'airpay-service-details' : undefined" @click="selectService(service)"><strong>{{ service.title }}</strong><span class="supplier-catalog__id">#{{ service.service_id }}</span></button></td>
            <td>{{ service.group || '—' }}</td><td>{{ service.country || '—' }}</td><td><span class="supplier-catalog__type">{{ paymentAmountLabel(service.fixed_payment) }}</span></td>
          </tr></tbody>
        </table>
      </div>
      <nav v-if="totalPages > 1" class="airpay-catalog__pagination supplier-catalog__pagination" aria-label="Страницы каталога Airpay">
        <button class="ghost" type="button" :disabled="page === 1" @click="page -= 1">Назад</button><span>Страница {{ page }} из {{ totalPages }}</span><button class="ghost" type="button" :disabled="page === totalPages" @click="page += 1">Далее</button>
      </nav>
      <section v-if="selectedService" id="airpay-service-details" ref="paymentForm" class="airpay-catalog__details" :aria-label="`Подготовка покупки: ${selectedService.title}`">
        <WorkAirpayPreparation :key="selectedService.service_id" :service-id="selectedService.service_id" :token="token" :can-prepare="canPrepare" :currency="currency" @busy-change="setPreparationBusy" />
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { apiGet } from '../../../api/http'
import WorkAirpayPreparation from './WorkAirpayPreparation.vue'

const props = defineProps({ token: { type: String, default: '' }, embedded: { type: Boolean, default: false },
  canPrepare: { type: Boolean, default: false }, currency: { type: String, default: '' } })
const emit = defineEmits(['busy-change'])
const preparationBusy = ref(false)
const services = ref([])
const configured = ref(null)
const loading = ref(false)
const error = ref('')
const search = ref('')
const group = ref('')
const page = ref(1)
const sortDirection = ref('asc')
const selectedService = ref(null)
const paymentForm = ref(null)
const pageSize = 20
const collator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' })
let requestVersion = 0

const groups = computed(() => [...new Set(services.value.map(service => service.group).filter(Boolean))].sort(collator.compare))
const filteredServices = computed(() => {
  // Поиск и группа уточняют список, а выбранное направление сортирует весь каталог до пагинации.
  const query = search.value.trim().toLocaleLowerCase('ru')
  return services.value.filter(service => (!group.value || service.group === group.value)
    && `${service.title} ${service.service_id} ${service.group} ${service.country}`.toLocaleLowerCase('ru').includes(query))
    .sort((left, right) => (sortDirection.value === 'asc' ? 1 : -1) * collator.compare(left.title, right.title))
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredServices.value.length / pageSize)))
const pagedServices = computed(() => filteredServices.value.slice((page.value - 1) * pageSize, page.value * pageSize))

async function loadCatalog() {
  // Запрос каталога независим от баланса; сбой одного метода не скрывает другой.
  if (preparationBusy.value) return
  const version = ++requestVersion
  loading.value = true
  error.value = ''
  configured.value = null
  services.value = []
  selectedService.value = null
  page.value = 1
  try {
    const result = await apiGet('/integrations/airpay/services', { token: props.token })
    if (version !== requestVersion) return
    configured.value = result.configured
    services.value = result.items
    if (!groups.value.includes(group.value)) group.value = ''
  } catch (err) {
    if (version === requestVersion) error.value = err?.message || 'Не удалось загрузить каталог Airpay'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function selectService(service) {
  // Раскрываем подготовку под каталогом и прокручиваем к ней, как в Interhub; повторное нажатие сворачивает её.
  if (preparationBusy.value) return
  selectedService.value = selectedService.value?.service_id === service.service_id ? null : service
  await nextTick()
  paymentForm.value?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
}

function setPreparationBusy(value) {
  // Передаём занятость формы в общую шапку, чтобы её обновление не прервало check.
  preparationBusy.value = value
  emit('busy-change', value)
}

function toggleSort() {
  // Переключаем порядок названий и возвращаем первую страницу, как в каталоге Interhub.
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  page.value = 1
}

function paymentAmountLabel(fixed) {
  // Отсутствующий признак не считаем разрешением вводить произвольную сумму.
  return fixed === true ? 'Фиксированная' : fixed === false ? 'Произвольная' : 'Не указана'
}

function resetFilters() {
  // Возвращаем полный список, если условия поиска не дали результатов.
  search.value = ''
  group.value = ''
}

watch([search, group], () => {
  // После изменения условий показываем первую страницу и убираем детали прежней услуги.
  page.value = 1
  selectedService.value = null
})
watch(() => props.token, () => {
  // Смена пользователя заново загружает разрешённые ему услуги.
  resetFilters()
  void loadCatalog()
}, { immediate: true })
onBeforeUnmount(() => {
  // Ответ закрытого экрана не должен восстановить его каталог или выбранную услугу.
  requestVersion += 1
})

// Общая шапка поставщика обновляет каталог и учитывает его загрузку без второй кнопки.
defineExpose({ reload: loadCatalog, loading, preparationBusy })
</script>

<style scoped src="../styles/work-supplier-catalog.css"></style>

<style scoped>
.airpay-catalog { min-width: 0; }
.airpay-catalog__header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.airpay-catalog h4 { margin: 0; font-size: 17px; }
.airpay-catalog__header p { margin: 6px 0 0; color: var(--muted, #9da9bf); font-size: 13px; }
.airpay-catalog__filters { flex-wrap: wrap; }
.airpay-catalog__group { width: min(220px, 100%); }
.airpay-catalog__table { overflow-x: auto; }
.airpay-catalog__table table { width: 100%; min-width: 540px; }
.airpay-catalog__service { display: block; width: 100%; padding: 0; border: 0; background: transparent; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.airpay-catalog__service:hover strong { color: #f6c66e; }
.airpay-catalog__service:focus-visible { outline: 2px solid #e88613; outline-offset: 2px; border-radius: 4px; }
.airpay-catalog__table .is-selected td { background: rgba(232, 134, 19, .08); }
.airpay-catalog__details { margin-top: 22px; padding: 22px; border-left: 3px solid #e88613; background: rgba(232, 134, 19, .06); scroll-margin-block: 24px; }
@media (max-width: 680px) {
  .airpay-catalog__group { width: 100%; }
  .airpay-catalog__details { padding: 16px; }
}
</style>
