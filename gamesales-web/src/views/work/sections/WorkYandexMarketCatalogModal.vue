<template>
  <teleport to="body">
    <div v-if="showYandexMarketCatalog" class="work-page work-modal-root modal-backdrop" @click.self="closeYandexMarketCatalog">
      <div class="modal modal--auto yandex-catalog-modal">
        <div class="panel__head panel__head--tight modal__head yandex-catalog-modal__head">
          <div><h3>Каталог Яндекс Маркета · test</h3><p class="muted yandex-catalog-modal__hint">Sandbox test-магазина: карточки и fake-заказы отделены от ASAT. Остатки доступны только для просмотра.</p></div>
          <div class="yandex-catalog-modal__head-actions"><div class="yandex-catalog-modal__sync-meta" aria-live="polite"><span>{{ yandexMarketCatalogSyncing ? 'Синхронизация…' : 'Последняя синхронизация' }}</span><strong>{{ latestCatalogSyncLabel }}</strong></div><button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--refresh" type="button" :disabled="yandexMarketCatalogSyncing" :title="yandexMarketCatalogSyncing ? 'Синхронизация каталога' : 'Синхронизировать каталог'" :aria-label="yandexMarketCatalogSyncing ? 'Синхронизация каталога' : 'Синхронизировать каталог'" @click="syncYandexMarketCatalog"><svg class="yandex-catalog-modal__sync-icon" :class="{ 'is-loading': yandexMarketCatalogSyncing }" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v6h-6" /></svg></button><button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" aria-label="Закрыть" title="Закрыть" @click="closeYandexMarketCatalog"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg></button></div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': isBusy, 'modal__body--loader': isBusy }">
          <div v-if="isBusy" class="modal__body-overlay"><WorkHamsterLoader :label="yandexMarketCatalogSyncing ? 'Синхронизируем каталог Яндекс Маркета…' : 'Загружаем сохранённый каталог…'" /></div>
          <p v-if="yandexMarketCatalogError" class="bad">{{ yandexMarketCatalogError }}</p><p v-if="yandexMarketCatalogOk" class="ok">{{ yandexMarketCatalogOk }}</p><p v-if="!yandexMarketCatalogLoading && !yandexMarketCatalogItems.length" class="muted">Снимка каталога пока нет. Нажмите «Синхронизировать».</p>
          <template v-if="!yandexMarketCatalogLoading && yandexMarketCatalogItems.length"><div class="yandex-catalog-modal__tabs" role="tablist" aria-label="Статус карточек Яндекс Маркета"><button class="yandex-catalog-modal__tab" :class="{ 'is-active': catalogTab === 'active' }" type="button" role="tab" :aria-selected="catalogTab === 'active'" @click="catalogTab = 'active'">Активные <span>{{ activeCatalogItems.length }}</span></button><button class="yandex-catalog-modal__tab" :class="{ 'is-active': catalogTab === 'archived' }" type="button" role="tab" :aria-selected="catalogTab === 'archived'" @click="catalogTab = 'archived'">Архив <span>{{ archivedCatalogItems.length }}</span></button></div><label class="yandex-catalog-modal__search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></svg><input v-model.trim="catalogSearch" type="search" placeholder="Поиск по названию или SKU" aria-label="Поиск по названию или SKU карточки Яндекс Маркета" /></label><p v-if="!visibleCatalogItems.length" class="muted yandex-catalog-modal__empty">{{ catalogSearch ? 'Карточки по запросу не найдены.' : catalogTab === 'active' ? 'Активных карточек нет.' : 'В архиве пока нет карточек.' }}</p></template>
          <table v-if="!yandexMarketCatalogLoading && visibleCatalogItems.length" class="table table--compact table--dense yandex-catalog-modal__table"><thead><tr><th>Карточка Яндекс Маркета</th><th class="yandex-catalog-modal__action-head">Действие</th></tr></thead><tbody><tr v-for="item in pagedCatalogItems" :key="item.offer_id" class="clickable-row" @click="openYandexMarketCatalogDetails(item)"><td><strong>{{ item.title || item.offer_id }}</strong><div class="muted">SKU: {{ item.offer_id }}</div></td><td class="yandex-catalog-modal__action"><button class="ghost yandex-catalog-modal__open-btn" type="button" @click.stop="openYandexMarketCatalogDetails(item)">Открыть</button></td></tr></tbody></table>
          <nav v-if="visibleCatalogItems.length && catalogTotalPages > 1" class="yandex-catalog-modal__pagination" aria-label="Страницы каталога Яндекс Маркета"><button class="ghost" type="button" :disabled="catalogPage === 1" aria-label="Предыдущая страница каталога Яндекс Маркета" @click="changeCatalogPage(-1)">Назад</button><span>Страница {{ catalogPage }} из {{ catalogTotalPages }}</span><label>Показывать <select v-model.number="catalogPageSize" class="input input--select input--compact" aria-label="Карточек на странице"><option :value="20">20</option><option :value="50">50</option></select></label><button class="ghost" type="button" :disabled="catalogPage === catalogTotalPages" aria-label="Следующая страница каталога Яндекс Маркета" @click="changeCatalogPage(1)">Далее</button></nav>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

const props = defineProps({ showYandexMarketCatalog: { type: Boolean, required: true }, closeYandexMarketCatalog: { type: Function, required: true }, syncYandexMarketCatalog: { type: Function, required: true }, openYandexMarketCatalogDetails: { type: Function, required: true }, yandexMarketCatalogItems: { type: Array, required: true }, yandexMarketCatalogLoading: { type: Boolean, required: true }, yandexMarketCatalogSyncing: { type: Boolean, required: true }, yandexMarketCatalogError: { type: String, default: '' }, yandexMarketCatalogOk: { type: String, default: '' } })

const catalogTab = ref('active')
const catalogSearch = ref('')
const catalogPage = ref(1)
const catalogPageSize = ref(20)
const isBusy = computed(() => props.yandexMarketCatalogLoading || props.yandexMarketCatalogSyncing)
const activeCatalogItems = computed(() => props.yandexMarketCatalogItems.filter((item) => !item.archived))
const archivedCatalogItems = computed(() => props.yandexMarketCatalogItems.filter((item) => item.archived))
const selectedCatalogItems = computed(() => (catalogTab.value === 'archived' ? archivedCatalogItems.value : activeCatalogItems.value))
const visibleCatalogItems = computed(() => {
  // Ищет по названию и SKU, как и каталог Ozon, без обращения к кабинету Маркета.
  const query = catalogSearch.value.toLocaleLowerCase('ru-RU')
  if (!query) return selectedCatalogItems.value
  return selectedCatalogItems.value.filter((item) => [item?.title, item?.offer_id, item?.market_sku].some((value) => String(value || '').toLocaleLowerCase('ru-RU').includes(query)))
})
const catalogTotalPages = computed(() => Math.max(1, Math.ceil(visibleCatalogItems.value.length / catalogPageSize.value)))
const pagedCatalogItems = computed(() => {
  // Ограничивает длинный каталог страницей, сохраняя высоту окна такой же, как у Ozon.
  const start = (catalogPage.value - 1) * catalogPageSize.value
  return visibleCatalogItems.value.slice(start, start + catalogPageSize.value)
})
const latestCatalogSyncLabel = computed(() => formatCatalogSyncDate(props.yandexMarketCatalogItems.reduce((latest, item) => (!latest || new Date(item?.synced_at || 0) > new Date(latest) ? item?.synced_at : latest), '')))

watch([catalogTab, catalogSearch, catalogPageSize], () => { catalogPage.value = 1 })
watch(catalogTotalPages, () => { catalogPage.value = Math.min(catalogPage.value, catalogTotalPages.value) })

function changeCatalogPage(direction) {
  // Переключает страницу локального снимка без нового запроса к Яндекс Маркету.
  catalogPage.value = Math.min(catalogTotalPages.value, Math.max(1, catalogPage.value + direction))
}

function formatCatalogSyncDate(value) {
  // Форматирует дату снимка так же, как в окне каталога Ozon.
  if (!value) return 'Нет данных'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
</script>
