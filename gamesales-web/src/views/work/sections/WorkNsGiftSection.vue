<template>
  <section class="panel panel--wide">
    <div class="panel__head work-ns-gift__head">
      <div class="work-ns-gift__title-wrap">
      </div>
      <div class="toolbar-actions">
        <button
          class="deal-refresh-btn"
          type="button"
          title="Обновить данные Магазина"
          aria-label="Обновить данные Магазина"
          :disabled="ctx.loading"
          @click="ctx.reloadNsGiftData"
        >
          <span class="deal-refresh-btn__content">
            <svg class="deal-refresh-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v6h-6" />
            </svg>
          </span>
        </button>
      </div>
    </div>

    <div class="panel__body work-ns-gift__body">
      <p v-if="ctx.error" class="error">{{ ctx.error }}</p>

      <div class="work-ns-gift__grid" :class="{ 'is-loading': ctx.loading }">
        <div class="work-ns-gift__left-stack">
          <article class="work-ns-gift__card work-ns-gift__card--balance">
            <span class="work-ns-gift__label">Баланс</span>
            <strong class="work-ns-gift__value">{{ formatBalance(ctx.balance) }} USD</strong>
            <span class="muted work-ns-gift__hint">Актуальный остаток кошелька Магазина</span>
          </article>

          <button class="work-ns-gift__steam-tile" :class="{ 'is-active': ctx.steamMode }" type="button" @click="onSteamTileClick">
            <span class="work-ns-gift__steam-tile-title">Steam Games | CIS</span>
            <span class="work-ns-gift__steam-tile-subtitle">RUB / UAH / KZT</span>
          </button>

          <article v-if="ctx.steamMode" class="work-ns-gift__card work-ns-gift__card--steam-form">
            <label class="field">
              <span class="label">Steam Login</span>
              <input
                class="input"
                type="text"
                :value="ctx.steamLogin"
                autocomplete="off"
                placeholder=""
                @input="ctx.setSteamLoginFromEvent"
              />
            </label>
            <label class="field work-ns-gift__steam-amount-field">
              <span class="label">Сумма USD</span>
              <input
                class="input"
                type="number"
                step="0.01"
                min="0.01"
                :value="ctx.steamAmount"
                @input="ctx.setSteamAmountFromEvent"
              />
            </label>
            <table class="table table--compact work-ns-gift__steam-table">
              <thead>
                <tr>
                  <th>Валюта</th>
                  <th>Сумма</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in steamCurrencyRows" :key="`steam-row-${row.code}`">
                  <td>{{ row.code }}</td>
                  <td>{{ row.amount }}</td>
                </tr>
              </tbody>
            </table>
            <div class="work-ns-gift__steam-footer">
              <span class="ns-gift-final-price" :class="{ 'ns-gift-final-price--active': true }">{{ steamBuyLabel }}</span>
            </div>
          </article>
        </div>

        <article class="work-ns-gift__card work-ns-gift__card--form">
          <div class="work-ns-gift__quick-grid">
            <button
              v-for="item in quickCategories"
              :key="`ns-gift-quick-${item.code}`"
              class="work-ns-gift__quick-card"
              type="button"
              @click="onQuickSelect(item)"
            >
              <span class="work-ns-gift__quick-logo">{{ item.logo }}</span>
              <span class="work-ns-gift__quick-copy">
                <span class="work-ns-gift__quick-title">{{ item.title }}</span>
                <span class="work-ns-gift__quick-subtitle">{{ item.subtitle }}</span>
              </span>
            </button>
          </div>

          <label class="work-ns-gift__field">
            <span class="work-ns-gift__label">Категория</span>
            <span class="muted work-ns-gift__count">Всего: {{ categoryCount }}</span>
            <input
              class="input work-ns-gift__input"
              type="text"
              :value="ctx.selectedCategory"
              autocomplete="off"
              placeholder="Начните вводить категорию"
              @focus="onCategoryFocus"
              @blur="onCategoryBlur"
              @input="onCategoryInput"
            />
            <div v-if="showCategoryDropdown && filteredCategories.length" class="work-ns-gift__dropdown">
              <button
                v-for="category in filteredCategories"
                :key="`ns-gift-dropdown-${category.category_id ?? 'none'}-${category.name}`"
                type="button"
                class="work-ns-gift__dropdown-item"
                @mousedown.prevent="onSelectCategory(category)"
              >
                {{ category.name }}
              </button>
            </div>
            <span class="muted work-ns-gift__hint">Поиск работает по списку категорий провайдера</span>
          </label>

        </article>
        <article v-if="!ctx.steamMode" class="work-ns-gift__card work-ns-gift__card--services">
          <div class="table-wrap work-ns-gift__table-wrap">
            <table class="table table--compact">
              <colgroup>
                <col class="ns-gift-col-title" />
                <col class="ns-gift-col-price" />
                <col class="ns-gift-col-stock" />
                <col class="ns-gift-col-quantity" />
                <col class="ns-gift-col-final" />
              </colgroup>
              <thead>
                <tr>
                  <th class="ns-gift-col-title">
                    <span class="th-title th-title--filter">
                      Наименование
                      <span class="th-actions">
                        <button
                          class="filter-icon filter-icon--sort"
                          type="button"
                          aria-label="Сортировка по наименованию"
                          title="Сортировка по наименованию"
                          :class="getServicesSortClass('title')"
                          @click.stop="toggleServicesSort('title')"
                        >
                          <svg viewBox="0 0 24 24">
                            <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                            <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                          </svg>
                        </button>
                      </span>
                    </span>
                  </th>
                  <th class="ns-gift-col-price">
                    <span class="th-title th-title--filter">
                      Цена
                      <span class="th-actions">
                        <button
                          class="filter-icon filter-icon--sort"
                          type="button"
                          aria-label="Сортировка по цене"
                          title="Сортировка по цене"
                          :class="getServicesSortClass('price')"
                          @click.stop="toggleServicesSort('price')"
                        >
                          <svg viewBox="0 0 24 24">
                            <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                            <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                          </svg>
                        </button>
                      </span>
                    </span>
                  </th>
                  <th class="ns-gift-col-stock">
                    <span class="th-title th-title--filter">
                      Доступно
                      <span class="th-actions">
                        <button
                          class="filter-icon filter-icon--sort"
                          type="button"
                          aria-label="Сортировка по доступности"
                          title="Сортировка по доступности"
                          :class="getServicesSortClass('stock')"
                          @click.stop="toggleServicesSort('stock')"
                        >
                          <svg viewBox="0 0 24 24">
                            <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                            <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                          </svg>
                        </button>
                      </span>
                    </span>
                  </th>
                  <th class="ns-gift-col-quantity">Количество</th>
                  <th class="ns-gift-col-final">Финальная Цена</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!ctx.selectedCategoryId">
                  <td colspan="5" class="muted">Выберите категорию, чтобы загрузить услуги.</td>
                </tr>
                <tr v-else-if="ctx.servicesLoading">
                  <td colspan="5" class="muted">Загружаем услуги…</td>
                </tr>
                <tr v-else-if="!filteredServices.length">
                  <td colspan="5" class="muted">По вашему фильтру ничего не найдено.</td>
                </tr>
                <tr v-for="service in filteredServices" :key="`ns-gift-service-${service.service_id}`">
                  <td>{{ service.title }}</td>
                  <td>{{ formatPrice(service.price, service.currency) }}</td>
                  <td>{{ formatStock(service.in_stock) }}</td>
                  <td class="ns-gift-cell-quantity">
                    <div class="ns-gift-quantity">
                      <button
                        class="ns-gift-quantity__btn"
                        type="button"
                        aria-label="Уменьшить количество"
                        @click="decreaseQuantity(service)"
                      >
                        -
                      </button>
                      <span class="ns-gift-quantity__value">{{ getQuantity(service) }}</span>
                      <button
                        class="ns-gift-quantity__btn"
                        type="button"
                        aria-label="Увеличить количество"
                        :disabled="isQuantityAtMax(service)"
                        @click="increaseQuantity(service)"
                      >
                        +
                      </button>
                    </div>
                  </td>
                  <td class="ns-gift-cell-final">
                    <span class="ns-gift-final-price" :class="{ 'ns-gift-final-price--active': getQuantity(service) > 0 }">
                      {{ formatFinalPrice(service) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

// Контекст секции NS Gift: баланс и выбор категории для следующих шагов интеграции.
const props = defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})

const categoryCount = computed(() => {
  // Показываем количество доступных категорий рядом с полем выбора.
  const list = Array.isArray(props.ctx?.categories) ? props.ctx.categories : []
  return list.length
})


const showCategoryDropdown = ref(false)
const servicesSort = ref({ key: 'title', dir: 'asc' })
const serviceQuantities = ref({})

const filteredCategories = computed(() => {
  // Фильтруем и ранжируем категории: точные и префиксные совпадения показываем первыми.
  const list = Array.isArray(props.ctx?.categories) ? props.ctx.categories : []
  const query = String(props.ctx?.selectedCategory || '').trim().toLowerCase()
  if (!query) return list
  const filtered = list.filter((item) => String(item?.name || '').toLowerCase().includes(query))
  return [...filtered].sort((left, right) => {
    const a = String(left?.name || '').toLowerCase()
    const b = String(right?.name || '').toLowerCase()

    const aExact = a === query ? 1 : 0
    const bExact = b === query ? 1 : 0
    if (aExact !== bExact) return bExact - aExact

    const aStarts = a.startsWith(query) ? 1 : 0
    const bStarts = b.startsWith(query) ? 1 : 0
    if (aStarts !== bStarts) return bStarts - aStarts

    const aIndex = a.indexOf(query)
    const bIndex = b.indexOf(query)
    if (aIndex !== bIndex) return aIndex - bIndex

    return a.localeCompare(b)
  })
})

const filteredServices = computed(() => {
  // Фильтруем и сортируем услуги по выбранному столбцу.
  const list = Array.isArray(props.ctx?.services) ? props.ctx.services : []
  const query = String(props.ctx?.servicesSearch || '').trim().toLowerCase()
  const filtered = query
    ? list.filter((item) => String(item?.title || '').toLowerCase().includes(query))
    : list
  return [...filtered].sort(compareServices)
})

const steamCurrencyRows = computed(() => {
  // Готовим строки расчета по валютам для специальной Steam-формы.
  const rates = props.ctx?.steamCurrencyRate || {}
  const amount = Number(String(props.ctx?.steamAmount || '0').replace(',', '.'))
  const normalizedAmount = Number.isFinite(amount) && amount > 0 ? amount : 0
  const rows = [
    { code: 'RUB', rate: Number(rates?.rubUsd || 0) },
    { code: 'KZT', rate: Number(rates?.kztUsd || 0) },
    { code: 'UAH', rate: Number(rates?.uahUsd || 0) },
  ]
  return rows.map((row) => ({
    code: row.code,
    amount: formatSteamAmount(row.rate * normalizedAmount),
  }))
})

const steamBuyLabel = computed(() => {
  // Кнопка покупки пока статическая, без заказа.
  return 'купить'
})

const quickCategories = [
  { code: 'steam', title: 'Steam', subtitle: 'Wallet / Top Up', logo: 'ST', query: 'Steam' },
  { code: 'playstation', title: 'PlayStation', subtitle: 'PSN / Wallet', logo: 'PS', query: 'PlayStation' },
  { code: 'ea', title: 'EA', subtitle: 'EA App / FC Points', logo: 'EA', query: 'EA' },
]

function onCategoryInput(event) {
  // На вводе обновляем строку и показываем список совпадений.
  props.ctx.setSelectedCategoryFromEvent(event)
  showCategoryDropdown.value = true
}

function onCategoryFocus() {
  // Открываем выпадающий список при фокусе на поле.
  showCategoryDropdown.value = true
}

function onCategoryBlur() {
  // Закрываем список с небольшой задержкой для клика по элементу.
  setTimeout(() => {
    showCategoryDropdown.value = false
  }, 120)
}

function onQuickSelect(item) {
  // Быстрые плашки заполняют только поиск по категориям.
  const queryText = String(item?.query || '')
  props.ctx.selectCategoryText(queryText)
  showCategoryDropdown.value = true
}

function onSteamTileClick() {
  // Переключаем Steam-форму через контекст; поддерживаем оба названия обработчика.
  showCategoryDropdown.value = false
  if (typeof props.ctx?.toggleSteamMode === 'function') {
    void props.ctx.toggleSteamMode()
    return
  }
  if (typeof props.ctx?.activateSteamMode === 'function') {
    void props.ctx.activateSteamMode()
  }
}

function onSelectCategory(item) {
  // Выбираем конкретный элемент из списка.
  props.ctx.selectCategoryOption(item?.name || '')
  showCategoryDropdown.value = false
}

watch(
  () => props.ctx?.services,
  (list) => {
    // Очищаем количество для услуг, которых уже нет в текущей выборке.
    const ids = new Set((Array.isArray(list) ? list : []).map((item) => Number(item?.service_id || 0)))
    const next = {}
    Object.entries(serviceQuantities.value).forEach(([key, value]) => {
      const id = Number(key)
      if (ids.has(id)) next[id] = value
    })
    serviceQuantities.value = next
  },
  { deep: true }
)

function compareServices(left, right) {
  // Сравниваем две услуги согласно активной сортировке таблицы.
  const { key, dir } = servicesSort.value
  const order = dir === 'asc' ? 1 : -1
  if (key === 'price') {
    const a = Number(left?.price || 0)
    const b = Number(right?.price || 0)
    return (a - b) * order
  }
  if (key === 'stock') {
    const a = Number(left?.in_stock || 0)
    const b = Number(right?.in_stock || 0)
    return (a - b) * order
  }
  const a = String(left?.title || '').toLowerCase()
  const b = String(right?.title || '').toLowerCase()
  return a.localeCompare(b) * order
}

function toggleServicesSort(key) {
  // Переключает сортировку таблицы услуг по выбранному полю.
  const current = servicesSort.value
  if (current.key === key) {
    servicesSort.value = { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
    return
  }
  servicesSort.value = { key, dir: 'asc' }
}

function getSortButtonClass(state) {
  // Возвращает классы состояния иконки сортировки.
  return {
    'is-active': Boolean(state),
    'is-asc': state === 'asc',
    'is-desc': state === 'desc',
  }
}

function getServicesSortClass(key) {
  // Выставляет состояние иконки для конкретной колонки услуг.
  return getSortButtonClass(servicesSort.value.key === key ? servicesSort.value.dir : '')
}

function formatBalance(value) {
  // Форматируем баланс в короткий вид для статуса в блоке NS Gift.
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return '0'
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 4 }).format(parsed)
}

function formatPrice(value, currency) {
  // Показываем цену как десятичное число с точкой, без разделителей тысяч.
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return '—'
  const numeric = new Intl.NumberFormat('en-US', {
    useGrouping: false,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(parsed)
  return `${numeric} ${String(currency || '').trim().toUpperCase()}`
}

function formatStock(value) {
  // Показывает доступный остаток услуги в компактном виде.
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(parsed).replaceAll(',', ' ')
}

function getQuantity(service) {
  // Возвращает текущее количество для строки услуги.
  const serviceId = Number(service?.service_id || 0)
  return Number(serviceQuantities.value[serviceId] || 0)
}

function getQuantityMax(service) {
  // Ограничиваем количество доступным остатком, если он задан.
  const stock = Number(service?.in_stock || 0)
  if (!Number.isFinite(stock) || stock <= 0) return Number.POSITIVE_INFINITY
  return Math.floor(stock)
}

function isQuantityAtMax(service) {
  // Проверяем, достигнут ли максимум для кнопки "+".
  return getQuantity(service) >= getQuantityMax(service)
}

function increaseQuantity(service) {
  // Увеличиваем количество по услуге с учетом верхней границы.
  const serviceId = Number(service?.service_id || 0)
  if (serviceId <= 0) return
  const current = getQuantity(service)
  const max = getQuantityMax(service)
  const next = Math.min(current + 1, max)
  serviceQuantities.value = { ...serviceQuantities.value, [serviceId]: next }
}

function decreaseQuantity(service) {
  // Уменьшаем количество, не опускаясь ниже нуля.
  const serviceId = Number(service?.service_id || 0)
  if (serviceId <= 0) return
  const current = getQuantity(service)
  const next = Math.max(current - 1, 0)
  serviceQuantities.value = { ...serviceQuantities.value, [serviceId]: next }
}

function formatFinalPrice(service) {
  // Считаем итоговую цену как количество * цену.
  const quantity = getQuantity(service)
  if (quantity <= 0) return 'купить'
  const price = Number(service?.price || 0)
  if (!Number.isFinite(price)) return '—'
  const total = price * quantity
  return formatPrice(total, service?.currency || 'USD')
}

function formatSteamAmount(value) {
  // Формат суммы Steam с 2 знаками после точки.
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return '0.00'
  return new Intl.NumberFormat('en-US', {
    useGrouping: false,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(parsed)
}

</script>

<style scoped>
.work-ns-gift__head {
  align-items: flex-start;
  gap: 16px;
}

.work-ns-gift__title-wrap {
  display: grid;
  gap: 6px;
}

.work-ns-gift__title {
  margin: 0;
}

.work-ns-gift__subtitle {
  margin: 0;
  max-width: 560px;
}

.work-ns-gift__body {
  display: grid;
  gap: 14px;
}

.work-ns-gift__grid {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(320px, 1fr);
  gap: 16px;
  align-items: start;
}

.work-ns-gift__left-stack {
  display: grid;
  gap: 12px;
  align-content: start;
}

.work-ns-gift__card {
  border: 1px solid var(--table-border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  padding: 16px;
}

.work-ns-gift__card--balance {
  display: grid;
  gap: 8px;
  align-content: start;
}

.work-ns-gift__steam-tile {
  border: 1px solid var(--table-border);
  border-radius: 14px;
  background: linear-gradient(165deg, rgba(20, 31, 58, 0.95), rgba(9, 16, 34, 0.95));
  color: inherit;
  padding: 14px;
  text-align: left;
  display: grid;
  gap: 4px;
  cursor: pointer;
}

.work-ns-gift__steam-tile.is-active {
  border-color: rgba(45, 212, 191, 0.5);
  background: linear-gradient(165deg, rgba(16, 38, 66, 0.96), rgba(7, 22, 45, 0.96));
}

.work-ns-gift__steam-tile-title {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.1;
}

.work-ns-gift__steam-tile-subtitle {
  font-size: 12px;
  color: var(--muted);
}

.work-ns-gift__card--steam-form {
  display: grid;
  gap: 14px;
}

.work-ns-gift__label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--muted);
}

.work-ns-gift__value {
  font-size: 30px;
  line-height: 1.1;
}

.work-ns-gift__card--form {
  display: grid;
  gap: 16px;
}

.work-ns-gift__field {
  display: grid;
  gap: 8px;
  position: relative;
}

.work-ns-gift__quick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.work-ns-gift__quick-card {
  border: 1px solid var(--table-border);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  color: inherit;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.work-ns-gift__quick-card:hover {
  border-color: rgba(95, 235, 196, 0.45);
  transform: translateY(-1px);
  background: rgba(95, 235, 196, 0.08);
}

.work-ns-gift__quick-logo {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  background: linear-gradient(150deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.06));
}

.work-ns-gift__quick-copy {
  display: grid;
  gap: 2px;
}

.work-ns-gift__quick-title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.1;
}

.work-ns-gift__quick-subtitle {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.1;
}

.work-ns-gift__count {
  font-size: 12px;
  margin-top: -4px;
}

.work-ns-gift__input {
  min-height: 44px;
}

.work-ns-gift__dropdown {
  display: grid;
  gap: 4px;
  position: absolute;
  top: calc(100% - 24px);
  left: 0;
  right: 0;
  z-index: 9;
  max-height: 260px;
  overflow: auto;
  padding: 6px;
  border: 1px solid var(--table-border);
  border-radius: 10px;
  background: rgba(12, 18, 36, 0.95);
}

.work-ns-gift__dropdown-item {
  border: 1px solid transparent;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  color: inherit;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
}

.work-ns-gift__dropdown-item:hover {
  border-color: rgba(95, 235, 196, 0.42);
  background: rgba(95, 235, 196, 0.1);
}

.work-ns-gift__hint {
  font-size: 12px;
}

.work-ns-gift__table-wrap {
  margin-top: 0;
}

.work-ns-gift__card--services {
  grid-column: 2;
  display: grid;
  gap: 10px;
}

.work-ns-gift__steam-amount-field {
  max-width: 220px;
}

.work-ns-gift__steam-table th,
.work-ns-gift__steam-table td {
  text-align: center;
}

.work-ns-gift__steam-footer {
  display: flex;
  justify-content: center;
}

.work-ns-gift__services-toolbar {
  justify-content: flex-start;
  gap: 8px;
}

.work-ns-gift__services-search {
  min-width: min(420px, 100%);
}

.ns-gift-col-title {
  width: 37%;
  min-width: 260px;
}

.ns-gift-col-price {
  width: 14%;
  min-width: 120px;
}

.ns-gift-col-stock {
  width: 12%;
  min-width: 100px;
}

.ns-gift-col-quantity {
  width: 17%;
  min-width: 140px;
}

.ns-gift-col-final {
  width: 20%;
  min-width: 120px;
}

.ns-gift-cell-quantity,
.ns-gift-cell-final {
  text-align: center;
  vertical-align: middle;
}

.ns-gift-col-stock,
.ns-gift-col-quantity,
.ns-gift-col-final {
  text-align: center;
}

.ns-gift-quantity {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 6px;
}

.ns-gift-quantity__btn {
  border: 1px solid color-mix(in srgb, var(--table-border) 70%, #22d3ee 30%);
  background: color-mix(in srgb, var(--table-bg) 70%, #0f766e 30%);
  color: #d8fff6;
  border-radius: 999px;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.ns-gift-quantity__btn:hover:not(:disabled) {
  border-color: rgba(45, 212, 191, 0.55);
  background: color-mix(in srgb, var(--table-bg) 62%, #0f766e 38%);
}

.ns-gift-quantity__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ns-gift-quantity__value {
  min-width: 18px;
  text-align: center;
  font-weight: 700;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.ns-gift-final-price {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  width: auto;
  max-width: 100%;
  min-height: 26px;
  border-radius: 999px;
  padding: 0 12px;
  background: rgba(148, 163, 184, 0.14);
  border: 1px solid rgba(148, 163, 184, 0.3);
  color: #d5dde8;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0;
  white-space: nowrap;
  box-sizing: border-box;
}

.ns-gift-final-price--active {
  background: rgba(52, 211, 153, 0.2);
  border-color: rgba(52, 211, 153, 0.45);
  color: #b9f9dc;
}

.is-loading {
  opacity: 0.7;
}

@media (max-width: 860px) {
  .work-ns-gift__grid {
    grid-template-columns: 1fr;
  }

  .work-ns-gift__card--services {
    grid-column: auto;
  }

  .work-ns-gift__quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
