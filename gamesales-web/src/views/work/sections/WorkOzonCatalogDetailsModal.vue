<template>
  <teleport to="body">
    <div
      v-if="showOzonCatalogDetails"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeOzonCatalogDetails"
    >
      <div class="modal modal--auto ozon-catalog-details-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div>
            <h3>Параметры карточки Ozon</h3>
            <p class="muted ozon-catalog-modal__hint">Данные сохранены при последней синхронизации.</p>
          </div>
          <div class="toolbar-actions">
            <button v-if="ozonCatalogDetails" class="btn btn--primary" type="button" @click="openOzonDigitalSettings">Ключи</button>
            <button class="ghost" type="button" @click="closeOzonCatalogDetails">К каталогу</button>
            <button class="btn btn--icon-plain" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonCatalogDetails">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body">
          <p v-if="ozonCatalogDetailsLoading" class="muted">Загружаем данные карточки…</p>
          <p v-else-if="ozonCatalogDetailsError" class="bad">{{ ozonCatalogDetailsError }}</p>
          <template v-else-if="ozonCatalogDetails">
            <h4 v-if="ozonCatalogDetails.title" class="ozon-catalog-details-modal__title">{{ ozonCatalogDetails.title }}</h4>
            <div v-if="ozonCatalogDetails.primary_image" class="ozon-catalog-details-modal__image-wrap">
              <img class="ozon-catalog-details-modal__image" :src="ozonCatalogDetails.primary_image" alt="Главное изображение товара Ozon" />
            </div>
            <dl v-if="detailFields.length" class="ozon-catalog-details-modal__grid">
              <template v-for="field in detailFields" :key="field.label">
                <dt>{{ field.label }}</dt>
                <dd>{{ field.value }}</dd>
              </template>
            </dl>
            <p v-else-if="!ozonCatalogDetails.primary_image" class="muted">Ozon не передал дополнительных параметров для этой карточки.</p>
          </template>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  showOzonCatalogDetails: { type: Boolean, required: true },
  closeOzonCatalogDetails: { type: Function, required: true },
  openOzonDigitalSettings: { type: Function, required: true },
  ozonCatalogDetails: { type: [Object, null], default: null },
  ozonCatalogDetailsLoading: { type: Boolean, required: true },
  ozonCatalogDetailsError: { type: String, default: '' },
})

function formatOzonDate(value) {
  // Показывает дату в привычном виде, а при нестандартном ответе оставляет исходное значение Ozon.
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

const detailFields = computed(() => {
  // Формирует только заполненные и неповторяющиеся реквизиты, полезные для работы с карточкой.
  const details = props.ozonCatalogDetails || {}
  const barcodes = Array.isArray(details.barcodes) ? details.barcodes.filter(Boolean).join(', ') : ''
  return [
    { label: 'Артикул продавца', value: details.offer_id || '' },
    { label: 'Штрихкоды', value: barcodes },
    { label: 'Категория Ozon', value: details.category_id ? String(details.category_id) : '' },
    { label: 'FBO SKU', value: details.fbo_sku || '' },
    { label: 'FBS SKU', value: details.fbs_sku || '' },
    { label: 'Цена', value: [details.price, details.price_currency_code].filter(Boolean).join(' ') },
    { label: 'Остаток Ozon', value: Number.isInteger(details.available_stock) ? String(details.available_stock) : '' },
    { label: 'Последняя синхронизация', value: formatOzonDate(details.synced_at) },
  ].filter((field) => field.value)
})
</script>
