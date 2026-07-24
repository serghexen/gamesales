<template>
  <teleport to="body">
    <div
      v-if="showOzonCatalog"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeOzonCatalog"
    >
      <div class="modal modal--auto ozon-catalog-modal">
        <div class="panel__head panel__head--tight modal__head ozon-catalog-modal__head">
          <div>
            <h3>Каталог Ozon</h3>
            <p class="muted ozon-catalog-modal__hint">Карточки синхронизируются с Ozon. Архивом можно управлять отсюда; цены и остатки не меняются.</p>
          </div>
          <div class="ozon-catalog-modal__head-actions">
            <div class="ozon-catalog-modal__sync-meta" aria-live="polite">
              <span>{{ ozonCatalogSyncing ? 'Синхронизация…' : 'Последняя синхронизация' }}</span>
              <strong>{{ latestCatalogSyncLabel }}</strong>
            </div>
            <button
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--refresh ozon-catalog-modal__sync-btn"
              type="button"
              :disabled="ozonCatalogSyncing"
              :title="ozonCatalogSyncing ? 'Синхронизация каталога' : 'Синхронизировать каталог'"
              :aria-label="ozonCatalogSyncing ? 'Синхронизация каталога' : 'Синхронизировать каталог'"
              @click="syncOzonCatalog"
            >
              <svg class="ozon-catalog-modal__sync-icon" :class="{ 'is-loading': ozonCatalogSyncing }" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                <path d="M20 4v6h-6" />
              </svg>
            </button>
            <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close ozon-catalog-modal__close-btn" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonCatalog">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': ozonCatalogLoading || ozonCatalogSyncing, 'modal__body--loader': ozonCatalogLoading || ozonCatalogSyncing }">
          <div v-if="ozonCatalogLoading || ozonCatalogSyncing" class="modal__body-overlay">
            <WorkHamsterLoader :label="ozonCatalogSyncing ? 'Синхронизируем каталог Ozon…' : 'Загружаем сохранённый каталог…'" />
          </div>
          <p v-if="ozonCatalogError" class="bad">{{ ozonCatalogError }}</p>
          <p v-if="ozonCatalogOk" class="ok">{{ ozonCatalogOk }}</p>
          <p v-if="!ozonCatalogLoading && !ozonCatalogItems.length" class="muted">Снимка каталога пока нет. Нажмите «Синхронизировать».</p>
          <template v-if="!ozonCatalogLoading && ozonCatalogItems.length">
            <div class="ozon-catalog-modal__tabs" role="tablist" aria-label="Статус карточек Ozon">
              <button
                class="ozon-catalog-modal__tab"
                :class="{ 'is-active': catalogTab === 'active' }"
                type="button"
                role="tab"
                :aria-selected="catalogTab === 'active'"
                @click="catalogTab = 'active'"
              >
                Активные <span>{{ activeCatalogItems.length }}</span>
              </button>
              <button
                class="ozon-catalog-modal__tab"
                :class="{ 'is-active': catalogTab === 'archived' }"
                type="button"
                role="tab"
                :aria-selected="catalogTab === 'archived'"
                @click="catalogTab = 'archived'"
              >
                Архив <span>{{ archivedCatalogItems.length }}</span>
              </button>
            </div>
            <label class="ozon-catalog-modal__search">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="11" cy="11" r="6" />
                <path d="m16 16 4 4" />
              </svg>
              <input v-model.trim="catalogSearch" type="search" placeholder="Поиск по названию или SKU" aria-label="Поиск по названию или SKU карточки Ozon" />
            </label>
            <p v-if="!visibleCatalogItems.length" class="muted ozon-catalog-modal__empty">
              {{ catalogSearch ? 'Карточки по запросу не найдены.' : catalogTab === 'active' ? 'Активных карточек нет.' : 'В архиве пока нет карточек.' }}
            </p>
          </template>
          <table v-if="!ozonCatalogLoading && visibleCatalogItems.length" class="table table--compact table--dense ozon-catalog-modal__table">
            <thead>
              <tr>
                <th>Карточка Ozon</th>
                <th class="ozon-catalog-modal__action-head">Действие</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in visibleCatalogItems" :key="item.external_product_id" class="clickable-row" @click="openOzonCatalogDetails(item)">
                <td>
                  <strong>{{ item.title || `Карточка #${item.external_product_id}` }}</strong>
                  <div class="muted">
                    <span v-if="item.sku">SKU: {{ item.sku }}</span>
                  </div>
                </td>
                <td class="ozon-catalog-modal__action">
                  <button
                    class="ghost ozon-catalog-modal__archive-btn"
                    type="button"
                    :disabled="Boolean(ozonCatalogItemActionId)"
                    @click.stop="updateOzonCatalogArchive(item, !isArchived(item))"
                  >
                    {{ ozonCatalogItemActionId === item.external_product_id ? 'Сохраняем…' : isArchived(item) ? 'Восстановить' : 'В архив' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

// Окно показывает только локальный снимок; привязка карточек к ключам появится следующим этапом.
const props = defineProps({
  showOzonCatalog: { type: Boolean, required: true },
  closeOzonCatalog: { type: Function, required: true },
  syncOzonCatalog: { type: Function, required: true },
  updateOzonCatalogArchive: { type: Function, required: true },
  openOzonCatalogDetails: { type: Function, required: true },
  ozonCatalogItems: { type: Array, required: true },
  ozonCatalogLoading: { type: Boolean, required: true },
  ozonCatalogSyncing: { type: Boolean, required: true },
  ozonCatalogItemActionId: { type: Number, default: 0 },
  ozonCatalogError: { type: String, default: '' },
  ozonCatalogOk: { type: String, default: '' },
})

const catalogTab = ref('active')
const catalogSearch = ref('')

function isArchived(item) {
  // Считает архивными только карточки, которые Ozon вернул с соответствующей видимостью или статусом.
  return [item?.visibility, item?.state].some((value) => String(value || '').toUpperCase().includes('ARCHIV'))
}

function formatCatalogSyncDate(value) {
  // Форматирует дату снимка каталога в короткий вид, понятный оператору без технического ISO-формата.
  if (!value) return 'Нет данных'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function matchesCatalogSearch(item) {
  // Ищет по названию и SKU, не показывая и не используя внутренний ID карточки в интерфейсе.
  const query = catalogSearch.value.trim().toLocaleLowerCase('ru-RU')
  if (!query) return true
  const title = String(item?.title || '').toLocaleLowerCase('ru-RU')
  const sku = String(item?.sku || '').toLocaleLowerCase('ru-RU')
  return title.includes(query) || sku.includes(query)
}

const activeCatalogItems = computed(() => props.ozonCatalogItems.filter((item) => !isArchived(item)))
const archivedCatalogItems = computed(() => props.ozonCatalogItems.filter((item) => isArchived(item)))
const selectedCatalogItems = computed(() => (catalogTab.value === 'archived' ? archivedCatalogItems.value : activeCatalogItems.value))
const visibleCatalogItems = computed(() => selectedCatalogItems.value.filter(matchesCatalogSearch))
const latestCatalogSyncAt = computed(() => {
  // Берет самую свежую дату из снимка, так как все карточки обновляются одной синхронизацией.
  return props.ozonCatalogItems.reduce((latest, item) => {
    const value = item?.synced_at
    if (!value || Number.isNaN(new Date(value).getTime())) return latest
    return !latest || new Date(value).getTime() > new Date(latest).getTime() ? value : latest
  }, '')
})
const latestCatalogSyncLabel = computed(() => formatCatalogSyncDate(latestCatalogSyncAt.value))
</script>
