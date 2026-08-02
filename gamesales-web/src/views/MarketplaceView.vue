<template>
  <main class="work-page page marketplace-page">
    <div class="shell">
      <header class="top marketplace-page__header">
        <div class="brand">
          <div class="logo marketplace-page__brand-logo"><img :src="marketplaceLogoSrc" alt="Homtech" /></div>
          <div>
            <div class="title">HomTech API Seller</div>
          </div>
        </div>
        <nav class="tabs marketplace-workspace-nav" aria-label="Разделы модуля">
          <button class="tab" type="button" :class="{ active: activeSection === 'stores' }" @click="activeSection = 'stores'">Магазины</button>
          <button class="tab" type="button" :class="{ active: activeSection === 'catalog' }" @click="activeSection = 'catalog'">Каталог</button>
          <button class="tab" type="button" :class="{ active: activeSection === 'orders' }" @click="activeSection = 'orders'">Заказы</button>
        </nav>
        <router-link class="top-profile-btn marketplace-page__profile" :to="{ name: 'work', query: { tab: 'profile' } }" aria-label="Профиль" title="Профиль"><span class="top-profile-btn__content"><svg class="top-profile-btn__icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span></router-link>
      </header>

      <section class="marketplace-page__content" aria-label="Рабочая область маркетплейсов">
        <p v-if="loadError" class="marketplace-page__notice marketplace-page__notice--error">{{ loadError }}</p>

        <section v-if="activeSection === 'catalog'" class="marketplace-catalog" aria-label="Каталог всех магазинов">
          <div class="marketplace-catalog__tools">
            <label class="marketplace-catalog__search"><span>Поиск</span><input v-model.trim="catalogSearch" type="search" placeholder="Название, артикул или SKU" @input="scheduleCatalogLoad" /></label>
            <div v-if="connections.length" class="marketplace-catalog__filters" aria-label="Фильтр по магазинам">
              <button type="button" :class="{ 'is-active': !catalogConnectionId }" @click="selectCatalogConnection(null)">Все магазины</button>
              <button v-for="connection in connections" :key="connection.id" type="button" :class="{ 'is-active': catalogConnectionId === connection.id }" @click="selectCatalogConnection(connection.id)"><img v-if="providerLogo(connection.provider_code)" class="marketplace-catalog__filter-logo" :src="providerLogo(connection.provider_code)" alt="" /><i v-else :class="`is-${connection.provider_code}`">{{ providerMark(connection.provider_code) }}</i><span>{{ connection.display_name }}</span></button>
            </div>
            <button class="marketplace-catalog__refresh" type="button" :disabled="catalogSyncing || !connections.length" :title="catalogSyncing ? 'Обновляем каталог' : catalogConnectionId ? 'Обновить выбранный магазин' : 'Обновить каталог'" :aria-label="catalogSyncing ? 'Обновляем каталог' : catalogConnectionId ? 'Обновить выбранный магазин' : 'Обновить каталог'" @click="syncCatalog"><svg :class="{ 'is-spinning': catalogSyncing }" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v6h-6"/></svg></button>
          </div>
          <p v-if="catalogError" class="marketplace-page__notice marketplace-page__notice--error">{{ catalogError }}</p>
          <div v-if="loading || catalogLoading" class="marketplace-page__loading">Загружаем каталог…</div>
          <div v-else-if="!connections.length" class="marketplace-page__empty">
            <div class="marketplace-page__empty-mark">01</div>
            <h3>Сначала подключите магазин</h3>
            <p>После подключения Ozon или Яндекс Маркета его товары появятся здесь единым списком.</p>
            <button class="marketplace-page__secondary" type="button" @click="openConnectionForm('ozon')">Подключить магазин</button>
          </div>
          <div v-else-if="!catalogItems.length" class="marketplace-page__empty">
            <div class="marketplace-page__empty-mark">КАТАЛОГ</div>
            <h3>{{ catalogSearch ? 'Ничего не найдено' : 'Каталог ещё не загружен' }}</h3>
            <p>{{ catalogSearch ? 'Попробуйте изменить запрос или выбрать другой магазин.' : 'Нажмите «Обновить каталог»: система прочитает товары и сохранит локальный снимок.' }}</p>
          </div>
        <div v-else class="marketplace-catalog__cards-wrap">
          <div class="marketplace-catalog__meta"><span>Найдено: {{ catalogItems.length }}</span></div>
          <div class="marketplace-catalog__cards" aria-label="Товары каталога">
            <article v-for="item in catalogItems" :key="`${item.connection_id}-${item.external_product_id}`" class="marketplace-catalog-card">
              <header>
                <img v-if="providerLogo(item.provider_code)" class="marketplace-provider-logo" :src="providerLogo(item.provider_code)" alt="" />
                <i v-else :class="`is-${item.provider_code}`">{{ providerMark(item.provider_code) }}</i>
                <div><b>{{ item.title || 'Без названия' }}</b><span>{{ item.connection_name }} · {{ providerName(item.provider_code) }}</span></div>
                <div class="marketplace-catalog-card__signals" aria-label="Статус товара">
                  <span class="marketplace-catalog-card__stock" data-tooltip="Будущий остаток: 1" role="img" aria-label="Будущий остаток: 1">1</span>
                </div>
              </header>
              <div class="marketplace-catalog-card__article"><span>SKU:</span><code>{{ item.sku || item.offer_id || item.external_product_id }}</code><div class="marketplace-catalog-card__signals marketplace-catalog-card__actions" aria-label="Настройки товара"><span :class="{ 'is-on': item.auto_issue_enabled }" :data-tooltip="item.auto_issue_enabled ? 'Автоотправка активна' : 'Автоотправка пока не настроена'" role="img" aria-label="Автоотправка"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3.5 11.2 16.8-7.1-5.9 15.8-3.3-6.1-7.6-2.6Z"/><path d="m11 13.7 3.9-4.3"/></svg></span><span :class="{ 'is-on': item.activation_instruction }" :data-tooltip="item.activation_instruction ? 'Инструкция заполнена' : 'Инструкция пока не добавлена'" role="img" aria-label="Инструкция"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.5h9.2A3.8 3.8 0 0 1 18 8.3v11.2H8.3A3.3 3.3 0 0 1 5 16.2V4.5Z"/><path d="M8.5 9h6M8.5 12h6M8.5 15h3.6"/></svg></span></div></div>
            </article>
          </div>
        </div>
        </section>

        <section v-else-if="activeSection === 'orders'" class="marketplace-catalog marketplace-orders" aria-label="Заказы всех магазинов">
          <div class="marketplace-catalog__tools">
            <label class="marketplace-catalog__search"><span>Поиск</span><input v-model.trim="orderSearch" type="search" placeholder="Номер заказа, товар или SKU" @input="scheduleOrdersLoad" /></label>
            <div v-if="connections.length" class="marketplace-catalog__filters" aria-label="Фильтр заказов по магазинам">
              <button type="button" :class="{ 'is-active': !orderConnectionId }" @click="selectOrdersConnection(null)">Все магазины</button>
              <button v-for="connection in connections" :key="connection.id" type="button" :class="{ 'is-active': orderConnectionId === connection.id }" @click="selectOrdersConnection(connection.id)"><img v-if="providerLogo(connection.provider_code)" class="marketplace-catalog__filter-logo" :src="providerLogo(connection.provider_code)" alt="" /><i v-else :class="`is-${connection.provider_code}`">{{ providerMark(connection.provider_code) }}</i><span>{{ connection.display_name }}</span></button>
            </div>
            <button class="marketplace-catalog__refresh" type="button" :disabled="ordersSyncing || !connections.length" :title="ordersSyncing ? 'Обновляем заказы' : orderConnectionId ? 'Обновить выбранный магазин' : 'Обновить заказы'" :aria-label="ordersSyncing ? 'Обновляем заказы' : orderConnectionId ? 'Обновить выбранный магазин' : 'Обновить заказы'" @click="syncOrders"><svg :class="{ 'is-spinning': ordersSyncing }" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v6h-6"/></svg></button>
            <div class="marketplace-orders__filters" aria-label="Дополнительные фильтры заказов">
              <label class="marketplace-orders__period"><span>Период</span><div><input v-model="orderDateFrom" type="date" aria-label="Заказы с даты" /><b>—</b><input v-model="orderDateTo" type="date" aria-label="Заказы по дату" /></div></label>
              <div class="marketplace-orders__status"><span>Статус</span><div><button v-for="option in orderStatusOptions" :key="option.value" type="button" :class="{ 'is-active': orderStatus === option.value }" @click="selectOrdersStatus(option.value)">{{ option.label }}</button></div></div>
              <button class="marketplace-orders__apply" type="button" @click="applyOrderFilters">Применить</button>
              <button v-if="hasOrderFilters" class="marketplace-orders__reset" type="button" @click="resetOrderFilters">Сбросить фильтры</button>
            </div>
          </div>
          <p v-if="ordersError" class="marketplace-page__notice marketplace-page__notice--error">{{ ordersError }}</p>
          <div v-if="loading || ordersLoading" class="marketplace-page__loading">Загружаем заказы…</div>
          <div v-else-if="!connections.length" class="marketplace-page__empty">
            <div class="marketplace-page__empty-mark">ЗАКАЗЫ</div>
            <h3>Сначала подключите магазин</h3>
            <p>После подключения Ozon или Яндекс Маркета здесь появится безопасный read-only снимок заказов.</p>
            <button class="marketplace-page__secondary" type="button" @click="openConnectionForm('ozon')">Подключить магазин</button>
          </div>
          <div v-else-if="!orderItems.length" class="marketplace-page__empty">
            <div class="marketplace-page__empty-mark">ЗАКАЗЫ</div>
            <h3>{{ hasOrderFilters ? 'Ничего не найдено' : 'Заказов пока нет в снимке' }}</h3>
            <p>{{ hasOrderFilters ? 'Измените условия поиска или сбросьте фильтры.' : 'Нажмите «Обновить»: система только прочитает заказы и сохранит локальный снимок.' }}</p>
          </div>
          <div v-else class="marketplace-catalog__cards-wrap">
            <div class="marketplace-catalog__meta"><span>Найдено: {{ ordersTotal }}</span></div>
            <div class="marketplace-catalog__cards" aria-label="Заказы">
              <article v-for="item in orderItems" :key="`${item.connection_id}-${item.external_order_id}-${item.external_item_id}`" class="marketplace-catalog-card marketplace-order-card">
                <header>
                  <img v-if="providerLogo(item.provider_code)" class="marketplace-provider-logo" :src="providerLogo(item.provider_code)" alt="" />
                  <i v-else :class="`is-${item.provider_code}`">{{ providerMark(item.provider_code) }}</i>
                  <div><b>Заказ №{{ item.external_order_id }}</b><span>{{ item.connection_name }} · {{ providerName(item.provider_code) }}</span></div>
                </header>
                <div class="marketplace-order-card__details"><b>{{ item.title || item.offer_id || 'Позиция без названия' }}</b><span :class="`is-${item.normalized_status || 'problem'}`">{{ orderStatusText(item.normalized_status) }}</span></div>
                <div class="marketplace-catalog-card__article"><span>SKU:</span><code>{{ item.sku || item.offer_id || '—' }}</code><time v-if="item.created_at" class="marketplace-order-card__date" :datetime="item.created_at">{{ formatOrderDateTime(item.created_at) }}</time></div>
              </article>
            </div>
            <nav v-if="ordersTotalPages > 1" class="marketplace-orders__pagination" aria-label="Страницы заказов"><button type="button" :disabled="ordersPage === 1" @click="goToOrdersPage(ordersPage - 1)">← Назад</button><span>Страница {{ ordersPage }} из {{ ordersTotalPages }} · {{ ordersTotal }} заказов</span><button type="button" :disabled="ordersPage === ordersTotalPages" @click="goToOrdersPage(ordersPage + 1)">Вперёд →</button></nav>
          </div>
        </section>

        <section v-else aria-label="Подключенные магазины">
          <div v-if="loading" class="marketplace-page__loading">Загружаем подключения…</div>
          <div v-else-if="!connections.length" class="marketplace-page__empty">
            <div class="marketplace-page__empty-mark">02</div>
            <h3>Пока нет подключённых магазинов</h3>
            <p>Добавьте Ozon или Яндекс Маркет — затем можно будет загрузить их товары в единый каталог.</p>
            <button class="marketplace-page__secondary" type="button" @click="openConnectionForm('ozon')">Подключить первый магазин</button>
          </div>
          <div v-else class="marketplace-page__grid">
            <article v-for="connection in connections" :key="connection.id" class="marketplace-connection-card">
              <div class="marketplace-connection-card__top">
                <img v-if="providerLogo(connection.provider_code)" class="marketplace-connection-card__provider marketplace-provider-logo" :src="providerLogo(connection.provider_code)" alt="" />
                <div v-else class="marketplace-connection-card__provider" :class="`is-${connection.provider_code}`">{{ providerMark(connection.provider_code) }}</div>
                <div class="marketplace-connection-card__status" :class="`is-${connection.status}`"><i></i>{{ statusText(connection.status) }}</div>
              </div>
              <h3>{{ connection.display_name }}</h3>
              <p class="marketplace-connection-card__provider-name">{{ providerName(connection.provider_code) }}</p>
              <dl>
                <div><dt>Токен</dt><dd>{{ connection.token_masked }}</dd></div>
                <div v-if="connection.provider_code === 'ozon'"><dt>Client ID</dt><dd>{{ connection.client_id }}</dd></div>
                <div v-else><dt>Кабинет / магазин</dt><dd>{{ connection.business_id }} / {{ connection.campaign_id }}</dd></div>
              </dl>
              <footer><span>Добавлен {{ formatDate(connection.created_at) }}</span><button type="button" :disabled="removingId === connection.id" @click="removeConnection(connection)">Отключить</button></footer>
            </article>
            <button class="marketplace-connection-card marketplace-connection-card--add" type="button" @click="openConnectionForm('ozon')"><span>+</span><strong>Подключить магазин</strong></button>
          </div>
        </section>
      </section>
    </div>
  </main>

  <div v-if="isSyncing" class="marketplace-catalog__loader" role="status" aria-live="polite">
    <div aria-label="Хомяк бежит в колесе" role="img" class="wheel-and-hamster">
      <div class="wheel"></div>
      <div class="hamster"><div class="hamster__body"><div class="hamster__head"><div class="hamster__ear"></div><div class="hamster__eye"></div><div class="hamster__nose"></div></div><div class="hamster__limb hamster__limb--fr"></div><div class="hamster__limb hamster__limb--fl"></div><div class="hamster__limb hamster__limb--br"></div><div class="hamster__limb hamster__limb--bl"></div><div class="hamster__tail"></div></div></div>
      <div class="spoke"></div>
    </div>
    <p>{{ syncLoaderText }}</p>
  </div>

  <div v-if="formOpen" class="marketplace-dialog" role="dialog" aria-modal="true" aria-labelledby="marketplace-dialog-title" @click.self="closeConnectionForm">
    <form class="marketplace-dialog__card" @submit.prevent="saveConnection">
      <button class="marketplace-dialog__close" type="button" aria-label="Закрыть" @click="closeConnectionForm">×</button>
      <p class="marketplace-page__eyebrow">НОВОЕ ПОДКЛЮЧЕНИЕ</p>
      <h2 id="marketplace-dialog-title">Подключить магазин</h2>
      <div class="marketplace-dialog__providers" role="radiogroup" aria-label="Маркетплейс">
        <button v-for="provider in providers" :key="provider.code" type="button" :class="{ 'is-selected': form.provider_code === provider.code }" @click="selectProvider(provider.code)"><b :class="{ 'is-provider-logo': Boolean(providerLogo(provider.code)) }"><img v-if="providerLogo(provider.code)" :src="providerLogo(provider.code)" alt="" /><template v-else>{{ provider.mark }}</template></b>{{ provider.name }}</button>
      </div>
      <label v-if="form.provider_code === 'ozon'"><span>Название магазина</span><input v-model.trim="form.display_name" required maxlength="120" placeholder="Например, ASAT Games" /></label>
      <label v-if="form.provider_code === 'ozon'"><span>Client ID кабинета</span><input v-model.trim="form.client_id" required maxlength="128" placeholder="Например, 48186803" /></label>
      <label><span>{{ form.provider_code === 'ozon' ? 'API Key' : 'API-Key Яндекс Маркета' }}</span><textarea v-model.trim="form.token" required minlength="8" maxlength="4096" placeholder="Вставьте ключ из кабинета маркетплейса" /></label>
      <div v-if="form.provider_code === 'yandex_market' && discoveredStores.length" class="marketplace-dialog__stores">
        <span>Выберите магазин</span>
        <button v-for="store in discoveredStores" :key="store.campaign_id" type="button" :class="{ 'is-selected': form.campaign_id === store.campaign_id }" @click="selectYandexStore(store)"><b>{{ store.display_name }}</b><small>Кабинет {{ store.business_id }} · магазин {{ store.campaign_id }}</small></button>
      </div>
      <p v-if="formError" class="marketplace-page__notice marketplace-page__notice--error">{{ formError }}</p>
      <div class="marketplace-dialog__actions"><button class="marketplace-page__secondary" type="button" @click="closeConnectionForm">Отмена</button><button class="marketplace-page__primary" type="submit" :disabled="saving">{{ saving ? 'Проверяем…' : submitLabel }}</button></div>
    </form>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { apiDelete, apiGet, apiPost } from '../api/http'
import { useAuth } from '../stores/auth'
import marketplaceLogoSrc from '../assets/homtech-marketplace-logo.png'
import ozonLogo from '../assets/ozon-mark.svg'
import yandexMarketLogo from '../assets/yandex-market-mark.svg'
import './work/styles/work-core.css'

const { state } = useAuth()
const activeSection = ref('catalog')
const connections = ref([])
const loading = ref(true)
const loadError = ref('')
const formOpen = ref(false)
const saving = ref(false)
const removingId = ref(0)
const formError = ref('')
const discoveredStores = ref([])
const catalogItems = ref([])
const catalogSearch = ref('')
const catalogConnectionId = ref(null)
const catalogLoading = ref(false)
const catalogSyncing = ref(false)
const catalogError = ref('')
const orderItems = ref([])
const orderSearch = ref('')
const orderConnectionId = ref(null)
const orderDateFrom = ref('')
const orderDateTo = ref('')
const orderStatus = ref('')
const ordersTotal = ref(0)
const ordersPage = ref(1)
const ordersPageSize = 20
const ordersTotalPages = ref(1)
const ordersLoading = ref(false)
const ordersSyncing = ref(false)
const ordersError = ref('')
let catalogSearchTimer = null
let ordersSearchTimer = null
const providers = [
  { code: 'ozon', name: 'Ozon', mark: 'O' },
  { code: 'yandex_market', name: 'Яндекс Маркет', mark: 'Я' },
]
const orderStatusOptions = [
  { value: '', label: 'Все статусы' },
  { value: 'processing', label: 'В процессе' },
  { value: 'in_delivery', label: 'Доставляется' },
  { value: 'delivered', label: 'Доставлен' },
  { value: 'cancelled', label: 'Отменён' },
  { value: 'problem', label: 'Проблема' },
]
const form = reactive({ provider_code: 'ozon', display_name: '', client_id: '', token: '', business_id: null, campaign_id: null })
const submitLabel = computed(() => form.provider_code === 'yandex_market' && !discoveredStores.value.length ? 'Найти магазины' : 'Подключить магазин')
const isSyncing = computed(() => catalogSyncing.value || ordersSyncing.value)
const syncLoaderText = computed(() => ordersSyncing.value ? 'Обновляем заказы…' : 'Обновляем каталог…')
const hasOrderFilters = computed(() => Boolean(orderSearch.value || orderConnectionId.value || orderDateFrom.value || orderDateTo.value || orderStatus.value))

function providerName(providerCode) {
  // Подставляет понятное имя витрины вместо технического кода API.
  return providers.find((provider) => provider.code === providerCode)?.name || 'Маркетплейс'
}

function providerMark(providerCode) {
  // Оставляет короткую марку, чтобы источник товара быстро различался в общем списке.
  return providers.find((provider) => provider.code === providerCode)?.mark || 'M'
}

function providerLogo(providerCode) {
  // Возвращает локальный знак маркетплейса, чтобы карточки и форма подключения выглядели одинаково.
  return { ozon: ozonLogo, yandex_market: yandexMarketLogo }[providerCode] || ''
}

function statusText(status) {
  // Объясняет состояние подключения, не раскрывая технические детали проверки токена.
  return { saved: 'Сохранён', active: 'Активен', error: 'Требует внимания', disabled: 'Отключён' }[status] || 'Неизвестно'
}

function orderStatusText(status) {
  // Показывает единый русский статус вместо отличающихся технических значений маркетплейсов.
  return { processing: 'В процессе', in_delivery: 'Доставляется', delivered: 'Доставлен', cancelled: 'Отменён', problem: 'Проблема' }[status] || 'Проблема'
}

function formatOrderDateTime(value) {
  // Форматирует время создания заказа компактно, чтобы оно помещалось в нижнюю строку карточки.
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(date)
}

function formatDate(value) {
  // Показывает дату без технического формата времени, который не нужен в карточке магазина.
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'недавно' : new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}

async function loadConnections() {
  // Получает только безопасные маски токенов и карточки текущего рабочего пространства.
  loading.value = true
  loadError.value = ''
  try {
    const result = await apiGet('/marketplace/connections', { token: state.token })
    connections.value = Array.isArray(result?.items) ? result.items : []
  } catch (error) {
    loadError.value = error?.message || 'Не удалось загрузить подключенные магазины'
  } finally {
    loading.value = false
  }
}

async function loadCatalog() {
  // Ищет в едином локальном снимке, поэтому ввод не делает запросов к внешним маркетплейсам.
  catalogLoading.value = true
  catalogError.value = ''
  const params = new URLSearchParams()
  if (catalogSearch.value) params.set('query', catalogSearch.value)
  if (catalogConnectionId.value) params.set('connection_id', String(catalogConnectionId.value))
  const suffix = params.size ? `?${params.toString()}` : ''
  try {
    const result = await apiGet(`/marketplace/catalog${suffix}`, { token: state.token })
    catalogItems.value = Array.isArray(result?.items) ? result.items : []
  } catch (error) {
    catalogError.value = error?.message || 'Не удалось загрузить каталог'
  } finally {
    catalogLoading.value = false
  }
}

function scheduleCatalogLoad() {
  // Небольшая пауза не отправляет отдельный запрос на каждую введенную букву поиска.
  if (catalogSearchTimer) window.clearTimeout(catalogSearchTimer)
  catalogSearchTimer = window.setTimeout(loadCatalog, 220)
}

function selectCatalogConnection(connectionId) {
  // Переключает магазин в общем каталоге и сразу перезагружает только нужный срез.
  catalogConnectionId.value = connectionId
  loadCatalog()
}

async function loadOrders() {
  // Читает отфильтрованный снимок заказов, не обращаясь к кабинетам маркетплейсов.
  ordersLoading.value = true
  ordersError.value = ''
  const params = new URLSearchParams()
  if (orderSearch.value) params.set('query', orderSearch.value)
  if (orderConnectionId.value) params.set('connection_id', String(orderConnectionId.value))
  if (orderDateFrom.value) params.set('date_from', orderDateFrom.value)
  if (orderDateTo.value) params.set('date_to', orderDateTo.value)
  if (orderStatus.value) params.set('status', orderStatus.value)
  params.set('page', String(ordersPage.value))
  params.set('page_size', String(ordersPageSize))
  const suffix = params.size ? `?${params.toString()}` : ''
  try {
    const result = await apiGet(`/marketplace/orders${suffix}`, { token: state.token })
    orderItems.value = Array.isArray(result?.items) ? result.items : []
    ordersTotal.value = Math.max(0, Number(result?.total) || 0)
    ordersPage.value = Math.max(1, Number(result?.page) || 1)
    ordersTotalPages.value = Math.max(1, Number(result?.total_pages) || 1)
  } catch (error) {
    ordersError.value = error?.message || 'Не удалось загрузить заказы'
  } finally {
    ordersLoading.value = false
  }
}

function scheduleOrdersLoad() {
  // Дает пользователю закончить ввод, прежде чем перечитать локальный снимок заказов.
  if (ordersSearchTimer) window.clearTimeout(ordersSearchTimer)
  ordersSearchTimer = window.setTimeout(() => {
    ordersPage.value = 1
    loadOrders()
  }, 220)
}

function selectOrdersConnection(connectionId) {
  // Переключает срез заказов по магазину и сразу обновляет карточки.
  orderConnectionId.value = connectionId
  ordersPage.value = 1
  loadOrders()
}

function selectOrdersStatus(status) {
  // Выбирает единый внутренний статус, но оставляет его черновиком до нажатия «Применить».
  orderStatus.value = status
}

function applyOrderFilters() {
  // Применяет дату и статус одним действием, возвращаясь на первую страницу списка.
  ordersPage.value = 1
  loadOrders()
}

function resetOrderFilters() {
  // Возвращает общий список заказов и очищает все условия, включая поиск по магазину.
  orderSearch.value = ''
  orderConnectionId.value = null
  orderDateFrom.value = ''
  orderDateTo.value = ''
  orderStatus.value = ''
  ordersPage.value = 1
  loadOrders()
}

function goToOrdersPage(page) {
  // Перелистывает только локальный снимок и не вызывает обновление заказов в маркетплейсе.
  if (page < 1 || page > ordersTotalPages.value || page === ordersPage.value) return
  ordersPage.value = page
  loadOrders()
}

function openConnectionForm(providerCode) {
  // Открывает чистую форму, позволяя выбрать нужную витрину до ввода чувствительного токена.
  selectProvider(providerCode)
  form.display_name = ''
  form.client_id = ''
  form.token = ''
  formError.value = ''
  formOpen.value = true
}

function selectProvider(providerCode) {
  // Сбрасывает найденные кабинеты при смене витрины, чтобы не сохранить ID другого маркетплейса.
  form.provider_code = providerCode
  form.display_name = ''
  form.client_id = ''
  form.business_id = null
  form.campaign_id = null
  discoveredStores.value = []
  formError.value = ''
}

function selectYandexStore(store) {
  // Запоминает только выбранный магазин из результата API и использует его название на карточке подключения.
  form.business_id = store.business_id
  form.campaign_id = store.campaign_id
  form.display_name = store.display_name
}

function closeConnectionForm() {
  // Закрывает форму и очищает токен из реактивного состояния после завершения работы с ним.
  form.token = ''
  discoveredStores.value = []
  formError.value = ''
  formOpen.value = false
}

async function saveConnection() {
  // Передает токен единственный раз для шифрования сервером и сразу обновляет список магазинов.
  saving.value = true
  formError.value = ''
  try {
    if (form.provider_code === 'yandex_market' && !discoveredStores.value.length) {
      const result = await apiPost('/marketplace/connections/discover', { provider_code: form.provider_code, token: form.token }, { token: state.token })
      discoveredStores.value = Array.isArray(result?.items) ? result.items : []
      return
    }
    if (form.provider_code === 'yandex_market' && !form.campaign_id) {
      formError.value = 'Выберите магазин из найденного списка'
      return
    }
    const created = await apiPost('/marketplace/connections', { ...form }, { token: state.token })
    connections.value.unshift(created)
    closeConnectionForm()
  } catch (error) {
    formError.value = error?.message || 'Не удалось сохранить магазин'
  } finally {
    saving.value = false
  }
}

async function removeConnection(connection) {
  // Просит явное подтверждение перед отключением кабинета и удаляет только выбранную карточку.
  if (!window.confirm(`Отключить «${connection.display_name}»? Токен будет удалён.`)) return
  removingId.value = connection.id
  loadError.value = ''
  try {
    await apiDelete(`/marketplace/connections/${connection.id}`, { token: state.token })
    connections.value = connections.value.filter((item) => item.id !== connection.id)
    if (catalogConnectionId.value === connection.id) catalogConnectionId.value = null
    if (orderConnectionId.value === connection.id) orderConnectionId.value = null
    await loadCatalog()
    await loadOrders()
  } catch (error) {
    loadError.value = error?.message || 'Не удалось отключить магазин'
  } finally {
    removingId.value = 0
  }
}

async function syncCatalog() {
  // Запускает только read-only чтение каждого выбранного магазина и затем обновляет общий снимок.
  const targetConnections = catalogConnectionId.value
    ? connections.value.filter((connection) => connection.id === catalogConnectionId.value)
    : connections.value.filter((connection) => connection.status === 'active')
  if (!targetConnections.length) return
  catalogSyncing.value = true
  catalogError.value = ''
  try {
    for (const connection of targetConnections) {
      await apiPost(`/marketplace/connections/${connection.id}/catalog/sync`, {}, { token: state.token })
    }
    await loadCatalog()
  } catch (error) {
    catalogError.value = error?.message || 'Не удалось обновить каталог'
  } finally {
    catalogSyncing.value = false
  }
}

async function syncOrders() {
  // Запускает только read-only чтение заказов выбранного магазина либо всех активных подключений.
  const targetConnections = orderConnectionId.value
    ? connections.value.filter((connection) => connection.id === orderConnectionId.value)
    : connections.value.filter((connection) => connection.status === 'active')
  if (!targetConnections.length) return
  ordersSyncing.value = true
  ordersError.value = ''
  try {
    for (const connection of targetConnections) {
      await apiPost(`/marketplace/connections/${connection.id}/orders/sync`, {}, { token: state.token })
    }
    await loadOrders()
  } catch (error) {
    ordersError.value = error?.message || 'Не удалось обновить заказы'
  } finally {
    ordersSyncing.value = false
  }
}

onMounted(async () => {
  // Сначала получает список магазинов, затем выводит общий каталог как стартовый экран модуля.
  await loadConnections()
  await loadCatalog()
  await loadOrders()
})

onBeforeUnmount(() => {
  // Отменяет отложенный поиск, если пользователь ушел со страницы до завершения паузы.
  if (catalogSearchTimer) window.clearTimeout(catalogSearchTimer)
  if (ordersSearchTimer) window.clearTimeout(ordersSearchTimer)
})
</script>

<style scoped>
.marketplace-page__header { justify-content: flex-start; gap: 20px; margin-bottom: 2px; }.marketplace-page__header .brand { min-width: 0; }.marketplace-page__brand-logo { background: #050914; border-color: rgba(73, 181, 255, .42); }.marketplace-page__brand-logo img { transform: scale(3); transform-origin: 50% 41%; }.marketplace-page__profile { margin-left: auto; }
.marketplace-page__eyebrow { margin: 0 0 7px; color: var(--accent); font-size: 10px; font-weight: 700; letter-spacing: .12em; }
.marketplace-page h2, .marketplace-page h3, .marketplace-page p { margin-top: 0; }
.marketplace-page__content { padding: 8px 2px 4px; }
.marketplace-workspace-nav { margin-left: 4px; }
.marketplace-page__section-head, .marketplace-connection-card__top, .marketplace-connection-card footer, .marketplace-dialog__actions { display: flex; align-items: center; }
.marketplace-page__section-head { justify-content: space-between; gap: 20px; margin: 26px 0 8px; }
.marketplace-page__section-head h2 { margin-bottom: 0; font-size: 24px; letter-spacing: -.035em; }
.marketplace-page__primary, .marketplace-page__secondary { border-radius: 11px; padding: 10px 14px; font: 700 12px 'Space Grotesk', sans-serif; cursor: pointer; transition: transform .2s ease, box-shadow .2s ease, background .2s ease; }
.marketplace-page__primary { color: var(--btn-text); border: 1px solid rgba(255, 255, 255, .24); background: var(--btn-bg); box-shadow: 0 8px 22px rgba(62, 232, 181, .19); }
.marketplace-page__primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(62, 232, 181, .27); }
.marketplace-page__primary:disabled { opacity: .64; cursor: wait; }.marketplace-page__primary span { font-size: 17px; vertical-align: -1px; }
.marketplace-page__secondary { color: var(--ghost-text); border: 1px solid var(--ghost-border); background: var(--ghost-bg); }.marketplace-page__secondary:hover { background: rgba(255, 255, 255, .12); }
.marketplace-catalog__hint { max-width: 650px; margin-bottom: 18px; color: var(--muted); font-size: 12px; line-height: 1.55; }
.marketplace-catalog__tools { display: grid; grid-template-columns: minmax(220px, 400px) 1fr; gap: 11px 18px; align-items: end; margin-bottom: 18px; }
.marketplace-catalog__search { display: grid; gap: 6px; }.marketplace-catalog__search span { color: var(--muted); font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.marketplace-catalog__search input { width: 100%; padding: 12px 13px; color: var(--ink); outline: 0; border: 1px solid var(--input-border); border-radius: 11px; background: var(--input-bg); font: 12px 'Space Grotesk', sans-serif; }.marketplace-catalog__search input:focus { border-color: rgba(62, 232, 181, .72); box-shadow: 0 0 0 3px rgba(62, 232, 181, .11); }
.marketplace-catalog__filters { display: flex; flex-wrap: wrap; gap: 6px; }.marketplace-catalog__filters button { max-width: 175px; overflow: hidden; padding: 8px 10px; color: var(--muted); text-overflow: ellipsis; white-space: nowrap; border: 1px solid var(--tab-border); border-radius: 9px; background: var(--tab-bg); font: 700 10px 'Space Grotesk', sans-serif; cursor: pointer; }.marketplace-catalog__filters button.is-active { color: var(--tab-active-text); border-color: rgba(62, 232, 181, .45); background: var(--tab-active-bg); }
.marketplace-catalog__cards-wrap { padding: 0 1px; }.marketplace-catalog__meta { display: flex; justify-content: space-between; gap: 16px; padding: 0 2px 10px; color: var(--muted); font-size: 11px; }.marketplace-catalog__cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }.marketplace-catalog-card { min-width: 0; padding: 14px; border: 1px solid var(--stroke); border-radius: 14px; background: var(--card); box-shadow: 0 9px 22px rgba(0, 0, 0, .1); transition: transform .18s ease, border-color .18s ease, background .18s ease; }.marketplace-catalog-card:hover { transform: translateY(-2px); border-color: rgba(62, 232, 181, .42); background: rgba(18, 29, 52, .92); }.marketplace-catalog-card header { display: grid; grid-template-columns: 31px minmax(0, 1fr) auto; gap: 10px; align-items: start; }.marketplace-catalog-card header > i { display: grid; width: 31px; height: 31px; place-items: center; color: #0b0f19; border-radius: 10px; background: linear-gradient(135deg, #3ee8b5, #7df0c6); font: 800 12px 'Space Grotesk', sans-serif; font-style: normal; }.marketplace-catalog-card header b { display: block; overflow: hidden; color: var(--ink); text-overflow: ellipsis; white-space: nowrap; font-size: 12px; line-height: 1.3; }.marketplace-catalog-card header > div:nth-child(2) span { display: block; overflow: hidden; margin-top: 4px; color: var(--muted); text-overflow: ellipsis; white-space: nowrap; font-size: 10px; }.marketplace-catalog-card__signals { display: flex; gap: 4px; }.marketplace-catalog-card__signals > span, .marketplace-catalog-card__instruction { position: relative; display: grid; width: 22px; height: 22px; place-items: center; color: rgba(202, 211, 231, .46); border: 1px solid rgba(202, 211, 231, .15); border-radius: 7px; background: rgba(255, 255, 255, .025); cursor: help; transition: color .18s ease, border-color .18s ease, background .18s ease; }.marketplace-catalog-card__signals > span:hover, .marketplace-catalog-card__instruction:hover { color: var(--ink); border-color: rgba(202, 211, 231, .35); }.marketplace-catalog-card__signals > span.is-on, .marketplace-catalog-card__instruction.is-on { color: var(--accent); border-color: rgba(62, 232, 181, .5); background: rgba(62, 232, 181, .12); box-shadow: 0 0 14px rgba(62, 232, 181, .12); }.marketplace-catalog-card__stock { color: #ffc760 !important; border-color: rgba(255, 190, 70, .25) !important; background: rgba(255, 190, 70, .08) !important; font: 700 11px monospace; }.marketplace-catalog-card__signals svg, .marketplace-catalog-card__instruction svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }.marketplace-catalog-card__signals > span::after, .marketplace-catalog-card__instruction::after { position: absolute; z-index: 4; right: 0; bottom: calc(100% + 7px); width: max-content; max-width: 175px; padding: 6px 7px; color: #eef2ff; content: attr(data-tooltip); opacity: 0; pointer-events: none; border: 1px solid rgba(255, 255, 255, .18); border-radius: 7px; background: #111a2e; box-shadow: 0 8px 20px rgba(0, 0, 0, .32); font: 600 9px 'Space Grotesk', sans-serif; transition: opacity .14s ease, transform .14s ease; transform: translateY(3px); }.marketplace-catalog-card__signals > span:hover::after, .marketplace-catalog-card__instruction:hover::after { opacity: 1; transform: translateY(0); }.marketplace-catalog-card__article { display: flex; align-items: center; justify-content: flex-start; gap: 6px; margin-top: 13px; padding-top: 10px; border-top: 1px dashed rgba(255, 255, 255, .16); }.marketplace-catalog-card__article > span:first-child { color: var(--muted); font-size: 10px; }.marketplace-catalog-card__article code { overflow: hidden; color: #d7def2; text-overflow: ellipsis; white-space: nowrap; font: 700 10px monospace; }.marketplace-catalog-card__instruction { flex: 0 0 22px; margin-left: auto; }
.marketplace-page__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(275px, 1fr)); gap: 14px; }.marketplace-connection-card { padding: 19px; background: var(--card); border: 1px solid var(--stroke); border-radius: 16px; box-shadow: 0 10px 26px rgba(0, 0, 0, .11); transition: transform .2s ease, border-color .2s ease; }.marketplace-connection-card:hover { transform: translateY(-3px); border-color: rgba(62, 232, 181, .4); }.marketplace-connection-card__top { justify-content: space-between; margin-bottom: 22px; }.marketplace-connection-card__provider { display: grid; width: 36px; height: 36px; place-items: center; color: #0b0f19; border-radius: 12px; background: linear-gradient(135deg, #3ee8b5, #7df0c6); font-size: 15px; font-weight: 800; }.marketplace-connection-card__provider.is-yandex_market { background: linear-gradient(135deg, #f7b955, #ffdd91); }.marketplace-connection-card__status { display: flex; align-items: center; gap: 6px; color: var(--accent); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .055em; }.marketplace-connection-card__status i { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px rgba(62, 232, 181, .12); }.marketplace-connection-card__status.is-error { color: #ff8c8c; }.marketplace-connection-card__status.is-error i { background: #ff6b6b; box-shadow: 0 0 0 3px rgba(255, 107, 107, .12); }.marketplace-connection-card h3 { margin-bottom: 3px; font-size: 17px; letter-spacing: -.025em; }.marketplace-connection-card__provider-name { margin-bottom: 20px; color: var(--muted); font-size: 12px; }.marketplace-connection-card dl { margin: 0; border-top: 1px solid var(--stroke); }.marketplace-connection-card dl div { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--stroke); font-size: 11px; }.marketplace-connection-card dt { color: var(--muted); }.marketplace-connection-card dd { margin: 0; color: #eef2ff; font-family: monospace; font-size: 11px; }.marketplace-connection-card footer { justify-content: space-between; margin-top: 15px; color: var(--muted); font-size: 10px; }.marketplace-connection-card footer button { padding: 0; color: #ff8c8c; border: 0; background: none; font: 700 10px 'Space Grotesk', sans-serif; cursor: pointer; }.marketplace-connection-card footer button:disabled { opacity: .45; }
.marketplace-connection-card--add { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; min-height: 258px; color: var(--muted); border-style: dashed; border-color: rgba(202, 211, 231, .28); background: rgba(10, 16, 32, .32); box-shadow: none; font-family: 'Space Grotesk', sans-serif; cursor: pointer; }.marketplace-connection-card--add span { color: var(--accent); font-size: 40px; font-weight: 300; line-height: .8; }.marketplace-connection-card--add strong { font-size: 13px; }.marketplace-connection-card--add:hover { color: var(--ink); border-color: rgba(62, 232, 181, .72); background: rgba(62, 232, 181, .07); box-shadow: inset 0 0 0 1px rgba(62, 232, 181, .12); }
.marketplace-page__empty, .marketplace-page__loading, .marketplace-page__notice { border-radius: 16px; }.marketplace-page__empty { padding: 44px 28px; text-align: center; background: var(--card); border: 1px dashed rgba(255, 255, 255, .26); }.marketplace-page__empty-mark { margin-bottom: 10px; color: var(--accent-2); font: 500 12px monospace; }.marketplace-page__empty h3 { margin-bottom: 7px; font-size: 17px; }.marketplace-page__empty p { max-width: 460px; margin: 0 auto 18px; color: var(--muted); font-size: 12px; line-height: 1.65; }.marketplace-page__loading { padding: 33px; color: var(--muted); border: 1px dashed rgba(255, 255, 255, .24); font-size: 12px; }.marketplace-page__notice { margin: 0 0 14px; padding: 12px 14px; font-size: 12px; }.marketplace-page__notice--error { color: #ffc7c7; border: 1px solid rgba(255, 107, 107, .35); background: rgba(255, 107, 107, .11); }
.marketplace-dialog { position: fixed; z-index: 20; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(3, 7, 18, .72); backdrop-filter: blur(9px); }.marketplace-dialog__card { position: relative; width: min(100%, 525px); padding: 30px; color: var(--ink); border: 1px solid var(--stroke); border-radius: 18px; background: var(--modal-bg); box-shadow: 0 25px 75px rgba(0, 0, 0, .45); font-family: 'Space Grotesk', sans-serif; }.marketplace-dialog__card h2 { margin-bottom: 23px; font-family: 'Space Grotesk', sans-serif; font-size: 25px; font-weight: 700; letter-spacing: -.03em; }.marketplace-dialog__close { position: absolute; top: 15px; right: 17px; width: 30px; height: 30px; color: var(--muted); border: 0; background: none; font-size: 25px; cursor: pointer; }.marketplace-dialog__providers { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 18px; }.marketplace-dialog__providers button { display: flex; gap: 8px; align-items: center; padding: 10px; color: var(--tab-text); border: 1px solid var(--tab-border); background: var(--tab-bg); border-radius: 10px; font: 600 12px 'Space Grotesk', sans-serif; cursor: pointer; }.marketplace-dialog__providers button.is-selected { color: var(--tab-active-text); border-color: rgba(62, 232, 181, .45); background: var(--tab-active-bg); }.marketplace-dialog__providers b { display: grid; width: 21px; height: 21px; place-items: center; color: #0b0f19; border-radius: 7px; background: var(--accent); }.marketplace-dialog__providers button:nth-child(2) b { background: var(--accent-2); }.marketplace-dialog__card label { display: block; margin: 14px 0; }.marketplace-dialog__card label span, .marketplace-dialog__stores > span { display: block; margin-bottom: 6px; color: var(--muted); font-size: 11px; font-weight: 700; }.marketplace-dialog__card input, .marketplace-dialog__card textarea { display: block; width: 100%; padding: 10px 11px; color: var(--ink); outline: 0; border: 1px solid var(--input-border); background: var(--input-bg); border-radius: 10px; font: 12px monospace; }.marketplace-dialog__card textarea { min-height: 86px; resize: vertical; }.marketplace-dialog__card input:focus, .marketplace-dialog__card textarea:focus { border-color: rgba(62, 232, 181, .72); box-shadow: 0 0 0 3px rgba(62, 232, 181, .11); }.marketplace-dialog__stores { display: grid; gap: 7px; margin-top: 15px; }.marketplace-dialog__stores button { display: grid; gap: 3px; padding: 11px 12px; color: var(--ink); text-align: left; border: 1px solid var(--tab-border); border-radius: 10px; background: var(--tab-bg); cursor: pointer; }.marketplace-dialog__stores button.is-selected { border-color: rgba(62, 232, 181, .68); background: rgba(62, 232, 181, .12); }.marketplace-dialog__stores b { font-size: 12px; }.marketplace-dialog__stores small { color: var(--muted); font: 10px monospace; }.marketplace-dialog__actions { justify-content: flex-end; gap: 8px; margin-top: 20px; }
.marketplace-catalog-card__actions { flex: 0 0 auto; margin-left: auto; }.marketplace-provider-logo { display: block; object-fit: contain; }.marketplace-catalog-card header > .marketplace-provider-logo { width: 31px; height: 31px; }.marketplace-connection-card__provider.marketplace-provider-logo { border-radius: 12px; background: transparent; }.marketplace-dialog__providers b { overflow: hidden; }.marketplace-dialog__providers b.is-provider-logo, .marketplace-dialog__providers button:nth-child(2) b.is-provider-logo { background: transparent; }.marketplace-dialog__providers b img { width: 100%; height: 100%; }
.marketplace-catalog__cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.marketplace-catalog__filter-actions { display: flex; gap: 10px; align-items: end; min-width: 0; }.marketplace-catalog__tools { grid-template-columns: minmax(220px, 400px) minmax(0, 1fr); }
.marketplace-catalog__tools { margin-top: 8px; }.marketplace-catalog__refresh { position: relative; box-sizing: border-box; display: inline-flex; width: 28px; height: 28px; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; flex: 0 0 28px; align-items: center; justify-content: center; padding: 0; overflow: hidden; color: #fff; line-height: 1; border: 2px solid rgba(255, 255, 255, .1); border-radius: 999px; background: linear-gradient(135deg, #ec4899 0%, #db2777 100%); box-shadow: 0 6px 18px rgba(236, 72, 153, .34); cursor: pointer; transition: transform .3s cubic-bezier(.23, 1, .32, 1), box-shadow .3s ease, border-color .3s ease, opacity .2s ease; }.marketplace-catalog__refresh:hover:not(:disabled) { transform: translateY(-1px); border-color: rgba(236, 72, 153, .38); box-shadow: 0 8px 22px rgba(236, 72, 153, .48); }.marketplace-catalog__refresh:disabled { opacity: .55; cursor: not-allowed; box-shadow: 0 3px 9px rgba(236, 72, 153, .24); }.marketplace-catalog__refresh svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 2; transition: transform .3s ease; }.marketplace-catalog__refresh:hover:not(:disabled) svg { transform: rotate(-20deg) scale(1.08); }.marketplace-catalog__refresh svg.is-spinning { animation: marketplace-catalog-spin .8s linear infinite; }
@keyframes marketplace-catalog-spin { to { transform: rotate(360deg); } }
.marketplace-catalog__tools { grid-template-columns: minmax(220px, 400px) minmax(0, 1fr) 42px; }.marketplace-catalog__refresh { width: 42px; height: 42px; min-width: 42px; max-width: 42px; min-height: 42px; max-height: 42px; flex-basis: 42px; }.marketplace-catalog__refresh svg { width: 20px; height: 20px; }
.marketplace-catalog__loader { position: fixed; z-index: 60; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; isolation: isolate; }.marketplace-catalog__loader::before { position: absolute; inset: 0; z-index: 0; content: ''; background: rgba(6, 10, 18, .6); backdrop-filter: blur(8px); }.marketplace-catalog__loader .wheel-and-hamster, .marketplace-catalog__loader p { position: relative; z-index: 1; }.marketplace-catalog__loader p { margin: 0; color: var(--ink); font-size: 12px; font-weight: 700; }.marketplace-catalog__loader .wheel-and-hamster { --dur: 1s; position: relative; width: 11.5em; height: 11.5em; overflow: visible; font-size: 10px; }.marketplace-catalog__loader .wheel, .marketplace-catalog__loader .hamster, .marketplace-catalog__loader .hamster div, .marketplace-catalog__loader .spoke { position: absolute; }.marketplace-catalog__loader .wheel, .marketplace-catalog__loader .spoke { top: 0; left: 0; width: 100%; height: 100%; border-radius: 50%; }.marketplace-catalog__loader .wheel { z-index: 2; background: radial-gradient(100% 100% at center, hsla(0, 0%, 60%, 0) 47.8%, hsl(0, 0%, 60%) 48%); }.marketplace-catalog__loader .hamster { top: 50%; left: calc(50% - 3.5em); z-index: 1; width: 7em; height: 3.75em; transform: rotate(4deg) translate(-.8em, 1.4em); transform-origin: 50% 0; animation: marketplace-hamster-run var(--dur) ease-in-out infinite; }.marketplace-catalog__loader .hamster__head { top: 0; left: -2em; width: 2.75em; height: 2.5em; border-radius: 70% 30% 0 100% / 40% 25% 25% 60%; background: hsl(30, 90%, 55%); box-shadow: 0 -.25em 0 hsl(30, 90%, 80%) inset, .75em -1.55em 0 hsl(30, 90%, 90%) inset; transform-origin: 100% 50%; animation: marketplace-hamster-head var(--dur) ease-in-out infinite; }.marketplace-catalog__loader .hamster__ear { top: -.25em; right: -.25em; width: .75em; height: .75em; border-radius: 50%; background: hsl(0, 90%, 85%); box-shadow: -.25em 0 hsl(30, 90%, 55%) inset; transform-origin: 50% 75%; animation: marketplace-hamster-ear var(--dur) ease-in-out infinite; }.marketplace-catalog__loader .hamster__eye { top: .375em; left: 1.25em; width: .5em; height: .5em; border-radius: 50%; background: #000; animation: marketplace-hamster-eye var(--dur) linear infinite; }.marketplace-catalog__loader .hamster__nose { top: .75em; left: 0; width: .2em; height: .25em; border-radius: 35% 65% 85% 15% / 70% 50% 50% 30%; background: hsl(0, 90%, 75%); }.marketplace-catalog__loader .hamster__body { top: .25em; left: 2em; width: 4.5em; height: 3em; border-radius: 50% 30% 50% 30% / 15% 60% 40% 40%; background: hsl(30, 90%, 90%); box-shadow: .1em .75em 0 hsl(30, 90%, 55%) inset, .15em -.5em 0 hsl(30, 90%, 80%) inset; transform-origin: 17% 50%; transform-style: preserve-3d; animation: marketplace-hamster-body var(--dur) ease-in-out infinite; }.marketplace-catalog__loader .hamster__limb--fr, .marketplace-catalog__loader .hamster__limb--fl { top: 2em; left: .5em; width: 1em; height: 1.5em; clip-path: polygon(0 0, 100% 0, 70% 80%, 60% 100%, 0 100%, 40% 80%); transform-origin: 50% 0; }.marketplace-catalog__loader .hamster__limb--fr { background: linear-gradient(hsl(30, 90%, 80%) 80%, hsl(0, 90%, 75%) 80%); animation: marketplace-hamster-fr var(--dur) linear infinite; }.marketplace-catalog__loader .hamster__limb--fl { background: linear-gradient(hsl(30, 90%, 90%) 80%, hsl(0, 90%, 85%) 80%); animation: marketplace-hamster-fl var(--dur) linear infinite; }.marketplace-catalog__loader .hamster__limb--br, .marketplace-catalog__loader .hamster__limb--bl { top: 1em; left: 2.8em; width: 1.5em; height: 2.5em; border-radius: .75em .75em 0 0; clip-path: polygon(0 0, 100% 0, 100% 30%, 70% 90%, 70% 100%, 30% 100%, 40% 90%, 0 30%); transform-origin: 50% 30%; }.marketplace-catalog__loader .hamster__limb--br { background: linear-gradient(hsl(30, 90%, 80%) 90%, hsl(0, 90%, 75%) 90%); animation: marketplace-hamster-br var(--dur) linear infinite; }.marketplace-catalog__loader .hamster__limb--bl { background: linear-gradient(hsl(30, 90%, 90%) 90%, hsl(0, 90%, 85%) 90%); animation: marketplace-hamster-bl var(--dur) linear infinite; }.marketplace-catalog__loader .hamster__tail { top: 1.5em; right: -.5em; width: 1em; height: .5em; border-radius: .25em 50% 50% .25em; background: hsl(0, 90%, 85%); box-shadow: 0 -.2em 0 hsl(0, 90%, 75%) inset; transform-origin: .25em .25em; animation: marketplace-hamster-tail var(--dur) linear infinite; }.marketplace-catalog__loader .spoke { background: radial-gradient(100% 100% at center, hsl(0, 0%, 60%) 4.8%, hsla(0, 0%, 60%, 0) 5%), linear-gradient(hsla(0, 0%, 55%, 0) 46.9%, hsl(0, 0%, 65%) 47% 52.9%, hsla(0, 0%, 65%, 0) 53%) 50% 50% / 99% 99% no-repeat; animation: marketplace-hamster-spoke var(--dur) linear infinite; }
@keyframes marketplace-hamster-run { from, to { transform: rotate(4deg) translate(-.8em, 1.4em); } 50% { transform: rotate(0) translate(-.8em, 1.4em); } } @keyframes marketplace-hamster-head { from, 25%, 50%, 75%, to { transform: rotate(0); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(8deg); } } @keyframes marketplace-hamster-eye { from, 90%, to { transform: scaleY(1); } 95% { transform: scaleY(0); } } @keyframes marketplace-hamster-ear { from, 25%, 50%, 75%, to { transform: rotate(0); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(12deg); } } @keyframes marketplace-hamster-body { from, 25%, 50%, 75%, to { transform: rotate(0); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-2deg); } } @keyframes marketplace-hamster-fr { from, 25%, 50%, 75%, to { transform: rotate(50deg) translateZ(-1px); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-30deg) translateZ(-1px); } } @keyframes marketplace-hamster-fl { from, 25%, 50%, 75%, to { transform: rotate(-30deg); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(50deg); } } @keyframes marketplace-hamster-br { from, 25%, 50%, 75%, to { transform: rotate(-60deg) translateZ(-1px); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(20deg) translateZ(-1px); } } @keyframes marketplace-hamster-bl { from, 25%, 50%, 75%, to { transform: rotate(20deg); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-60deg); } } @keyframes marketplace-hamster-tail { from, 25%, 50%, 75%, to { transform: rotate(30deg) translateZ(-1px); } 12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(10deg) translateZ(-1px); } } @keyframes marketplace-hamster-spoke { from { transform: rotate(0); } to { transform: rotate(-1turn); } }
.marketplace-catalog__tools { grid-template-columns: minmax(220px, 400px) minmax(0, 1fr) 42px; }.marketplace-catalog__filters { align-items: center; }.marketplace-catalog__filters button { display: inline-flex; height: 42px; max-width: 210px; align-items: center; gap: 8px; padding: 0 12px; }.marketplace-catalog__filters button span { overflow: hidden; text-overflow: ellipsis; }.marketplace-catalog__filter-logo { width: 20px; height: 20px; flex: 0 0 20px; object-fit: contain; }.marketplace-catalog__filters button > i { display: grid; width: 20px; height: 20px; flex: 0 0 20px; place-items: center; color: #0b0f19; border-radius: 6px; background: var(--accent); font: 800 9px 'Space Grotesk', sans-serif; font-style: normal; }.marketplace-catalog__refresh { align-self: end; justify-self: end; }
.marketplace-orders__filters { display: flex; grid-column: 1 / -1; flex-wrap: wrap; align-items: end; gap: 10px 18px; }.marketplace-orders__period, .marketplace-orders__status { display: grid; gap: 6px; }.marketplace-orders__period > span, .marketplace-orders__status > span { color: var(--muted); font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }.marketplace-orders__period > div, .marketplace-orders__status > div { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }.marketplace-orders__period input { box-sizing: border-box; width: 138px; height: 36px; padding: 0 9px; color: #e9eefb; outline: 0; border: 1px solid rgba(178, 195, 226, .28); border-radius: 9px; background: rgba(8, 16, 33, .72); font: 600 11px 'Space Grotesk', sans-serif; }.marketplace-orders__period input:focus { border-color: rgba(62, 232, 181, .72); box-shadow: 0 0 0 3px rgba(62, 232, 181, .1); }.marketplace-orders__period b { color: var(--muted); font-size: 12px; }.marketplace-orders__status button, .marketplace-orders__reset { height: 36px; padding: 0 11px; color: #b7c4dc; border: 1px solid rgba(178, 195, 226, .22); border-radius: 9px; background: rgba(32, 43, 70, .72); font: 700 10px 'Space Grotesk', sans-serif; cursor: pointer; transition: color .18s ease, border-color .18s ease, background .18s ease; }.marketplace-orders__status button:hover, .marketplace-orders__reset:hover { color: #f3f6ff; border-color: rgba(178, 195, 226, .42); }.marketplace-orders__status button.is-active { color: var(--tab-active-text); border-color: rgba(62, 232, 181, .48); background: var(--tab-active-bg); }.marketplace-orders__reset { align-self: end; color: #ffc7c7; border-color: rgba(255, 146, 146, .32); background: rgba(255, 107, 107, .08); }
.marketplace-orders__apply { align-self: end; height: 36px; padding: 0 14px; color: #071423; border: 1px solid rgba(255, 255, 255, .25); border-radius: 9px; background: var(--btn-bg); box-shadow: 0 6px 16px rgba(62, 232, 181, .16); font: 700 10px 'Space Grotesk', sans-serif; cursor: pointer; transition: transform .18s ease, box-shadow .18s ease; }.marketplace-orders__apply:hover { transform: translateY(-1px); box-shadow: 0 9px 20px rgba(62, 232, 181, .24); }.marketplace-orders__pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 18px 0 4px; color: #b7c4dc; font-size: 11px; }.marketplace-orders__pagination button { min-width: 92px; height: 36px; padding: 0 12px; color: #e9eefb; border: 1px solid rgba(178, 195, 226, .28); border-radius: 9px; background: rgba(32, 43, 70, .72); font: 700 10px 'Space Grotesk', sans-serif; cursor: pointer; transition: color .18s ease, border-color .18s ease, background .18s ease; }.marketplace-orders__pagination button:hover:not(:disabled) { border-color: rgba(62, 232, 181, .48); background: rgba(62, 232, 181, .11); }.marketplace-orders__pagination button:disabled { opacity: .42; cursor: default; }
.marketplace-order-card__details { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 13px; }.marketplace-order-card__details b { overflow: hidden; color: #d7def2; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }.marketplace-order-card__details span { flex: 0 0 auto; max-width: 34%; overflow: hidden; color: var(--accent-2); text-overflow: ellipsis; white-space: nowrap; font: 700 9px monospace; text-transform: uppercase; }.marketplace-order-card__details span.is-processing { color: #ffc760; }.marketplace-order-card__details span.is-in_delivery { color: #77baff; }.marketplace-order-card__details span.is-delivered { color: var(--accent); }.marketplace-order-card__details span.is-cancelled { color: #ff9292; }.marketplace-order-card__details span.is-problem { color: #ff9292; }.marketplace-order-card .marketplace-catalog-card__article { margin-top: 9px; }.marketplace-order-card__date { margin-left: auto; color: var(--muted); white-space: nowrap; font: 500 9px 'Space Grotesk', sans-serif; }
.marketplace-catalog-card, .marketplace-connection-card:not(.marketplace-connection-card--add) { border-color: rgba(168, 186, 222, .3); background: linear-gradient(135deg, rgba(31, 46, 78, .98), rgba(18, 29, 53, .98)); box-shadow: 0 10px 25px rgba(0, 0, 0, .16), inset 0 1px 0 rgba(255, 255, 255, .035); }.marketplace-catalog-card:hover { background: linear-gradient(135deg, rgba(38, 58, 94, .98), rgba(22, 37, 67, .98)); }.marketplace-catalog-card header b, .marketplace-connection-card h3 { color: #f3f6ff; }.marketplace-catalog-card header > div:nth-child(2) span, .marketplace-catalog-card__article > span:first-child, .marketplace-order-card__date, .marketplace-connection-card__provider-name, .marketplace-connection-card dt, .marketplace-connection-card footer { color: #b7c4dc; }.marketplace-catalog-card__article code, .marketplace-order-card__details b, .marketplace-connection-card dd { color: #e9eefb; }.marketplace-catalog-card__article, .marketplace-connection-card dl, .marketplace-connection-card dl div { border-color: rgba(178, 195, 226, .2); }
@media (max-width: 760px) { .marketplace-page__header { flex-wrap: wrap; }.marketplace-workspace-nav { order: 3; width: 100%; margin-left: 0; }.marketplace-workspace-nav button { flex: 1; justify-content: center; }.marketplace-page__content { padding-top: 8px; }.marketplace-catalog__tools { grid-template-columns: 1fr; }.marketplace-catalog__cards { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .marketplace-page__header { align-items: flex-start; }.marketplace-page__header .tabs { justify-content: flex-end; }.marketplace-page__section-head { align-items: flex-end; }.marketplace-page__section-head h2 { font-size: 21px; }.marketplace-page__primary { padding: 10px 11px; white-space: nowrap; }.marketplace-dialog__card { padding: 25px 20px; } }
</style>
