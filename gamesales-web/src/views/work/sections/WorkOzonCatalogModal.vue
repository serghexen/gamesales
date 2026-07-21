<template>
  <teleport to="body">
    <div
      v-if="showOzonCatalog"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeOzonCatalog"
    >
      <div class="modal modal--auto ozon-catalog-modal">
        <div class="panel__head panel__head--tight modal__head">
          <div>
            <h3>Каталог Ozon</h3>
            <p class="muted ozon-catalog-modal__hint">Карточки только читаются из Ozon. Цены, остатки и публикации не изменяются.</p>
          </div>
          <div class="toolbar-actions">
            <button class="ghost" type="button" :disabled="ozonCatalogSyncing" @click="syncOzonCatalog">
              {{ ozonCatalogSyncing ? 'Синхронизация…' : 'Синхронизировать' }}
            </button>
            <button class="btn btn--icon-plain" type="button" aria-label="Закрыть" title="Закрыть" @click="closeOzonCatalog">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body">
          <p v-if="ozonCatalogError" class="bad">{{ ozonCatalogError }}</p>
          <p v-if="ozonCatalogOk" class="ok">{{ ozonCatalogOk }}</p>
          <p v-if="ozonCatalogLoading" class="muted">Загружаем сохраненный каталог…</p>
          <p v-else-if="!ozonCatalogItems.length" class="muted">Снимка каталога пока нет. Нажмите «Синхронизировать».</p>
          <table v-else class="table table--compact table--dense ozon-catalog-modal__table">
            <thead>
              <tr>
                <th>Карточка Ozon</th>
                <th>Артикул продавца</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in ozonCatalogItems" :key="item.external_product_id">
                <td>
                  <strong>{{ item.title || `Карточка #${item.external_product_id}` }}</strong>
                  <div class="muted">ID: {{ item.external_product_id }}</div>
                </td>
                <td>{{ item.offer_id || '—' }}</td>
                <td>{{ item.state || item.visibility || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
// Окно показывает только локальный снимок; привязка карточек к ключам появится следующим этапом.
defineProps({
  showOzonCatalog: { type: Boolean, required: true },
  closeOzonCatalog: { type: Function, required: true },
  syncOzonCatalog: { type: Function, required: true },
  ozonCatalogItems: { type: Array, required: true },
  ozonCatalogLoading: { type: Boolean, required: true },
  ozonCatalogSyncing: { type: Boolean, required: true },
  ozonCatalogError: { type: String, default: '' },
  ozonCatalogOk: { type: String, default: '' },
})
</script>
