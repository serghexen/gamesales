<template>
  <section class="ozon-catalog-details-modal__work-block marketplace-key-pool-panel" :class="{ 'is-open': isOpen }">
    <div class="ozon-key-settings__block-head">
      <button class="ozon-catalog-details-modal__work-block-toggle" type="button" :aria-expanded="isOpen" aria-controls="marketplace-key-pool-content" @click="toggleOpen">
        <span class="ozon-catalog-details-modal__work-block-number">02</span>
        <span class="ozon-catalog-details-modal__work-block-copy"><strong>Список ключей</strong></span>
        <svg class="ozon-catalog-details-modal__work-block-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5" /></svg>
      </button>
      <div class="marketplace-key-pool-panel__head-actions">
        <slot name="header-actions" />
      </div>
    </div>
    <div v-if="isOpen" id="marketplace-key-pool-content" class="ozon-catalog-details-modal__work-block-body marketplace-key-pool-panel__body">
      <div v-if="marketplaceKeyPoolSaving" class="marketplace-key-pool-panel__saving-overlay"><WorkHamsterLoader label="Обновляем список ключей…" /></div>
      <p v-if="marketplaceKeyPoolError" class="bad">{{ marketplaceKeyPoolError }}</p>
      <div class="marketplace-key-pool-modal__stats marketplace-key-pool-panel__stats" aria-label="Статистика ручного пула ключей">
        <div><small>Свободно</small><strong>{{ marketplaceKeyPool.free_count }}</strong></div>
        <div><small>Выдано</small><strong>{{ marketplaceKeyPool.delivered_count }}</strong></div>
        <div><small>Всего</small><strong>{{ marketplaceKeyPool.total }}</strong></div>
      </div>
      <div class="marketplace-key-pool-modal__list-head marketplace-key-pool-panel__list-head">
        <div><h4>Ключи товара</h4><p class="muted">Удаляются только свободные ключи.</p></div>
        <div class="marketplace-key-pool-panel__list-actions">
          <button class="ghost marketplace-key-pool-entry__open" type="button" :disabled="!productKey || !storeCode" @click="openAddDialog">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>Добавить ключи
          </button>
          <button class="ghost marketplace-key-pool-modal__delete-free" type="button" :disabled="!marketplaceKeyPool.free_count || marketplaceKeyPoolSaving" @click="deleteAllFreeMarketplaceKeyPoolKeys">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" /></svg>Удалить свободные
          </button>
        </div>
      </div>
      <div v-if="marketplaceKeyPoolLoading" class="muted marketplace-key-pool-panel__loading">Загружаем пул…</div>
      <p v-else-if="!marketplaceKeyPool.items.length" class="marketplace-key-pool-modal__empty muted">В этом пуле пока нет ключей.</p>
      <div v-else class="table-wrap marketplace-key-pool-panel__table-wrap">
        <table class="table table--compact marketplace-key-pool-modal__table">
          <thead><tr><th>Ключ</th><th>Статус</th><th>Активировать до</th><th>Заказ</th><th>Действия</th></tr></thead>
          <tbody>
            <tr v-for="key in marketplaceKeyPool.items" :key="key.id">
              <td><code v-if="marketplaceKeyPoolRevealedCode(key)" class="marketplace-key-pool-modal__code">{{ marketplaceKeyPoolRevealedCode(key) }}</code><span v-else>{{ key.masked_code }}</span></td>
              <td><span class="marketplace-key-pool-modal__status" :class="`marketplace-key-pool-modal__status--${key.status}`">{{ statusLabel(key.status) }}</span></td>
              <td>{{ formatDate(key.expires_at) }}</td>
              <td>{{ key.issued_order_ref || '—' }}</td>
              <td class="marketplace-key-pool-modal__actions">
                <button class="btn btn--icon-plain btn--edit marketplace-key-pool-modal__reveal" type="button" :disabled="marketplaceKeyPoolSaving || marketplaceKeyPoolRevealingId === key.id" :aria-label="`Показать ключ ${key.masked_code}`" :title="marketplaceKeyPoolRevealedCode(key) ? 'Ключ показан для проверки' : 'Показать ключ для проверки'" @click="revealMarketplaceKeyPoolKey(key)">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></svg>
                </button>
                <button v-if="key.status === 'free'" class="btn btn--icon-plain btn--danger marketplace-key-pool-modal__remove" type="button" :disabled="marketplaceKeyPoolSaving" :aria-label="`Удалить ${key.masked_code}`" title="Удалить свободный ключ" @click="deleteMarketplaceKeyPoolKey(key)">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="marketplaceKeyPool.total > marketplaceKeyPool.page_size" class="marketplace-key-pool-modal__pager">
        <span>Показаны {{ pageRange }}</span>
        <button class="ghost marketplace-key-pool-modal__page-button" type="button" :disabled="marketplaceKeyPool.page <= 1 || marketplaceKeyPoolLoading" @click="loadMarketplaceKeyPool(marketplaceKeyPool.page - 1)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>Назад</button>
        <button class="ghost marketplace-key-pool-modal__page-button" type="button" :disabled="marketplaceKeyPool.page >= marketplaceKeyPoolTotalPages || marketplaceKeyPoolLoading" @click="loadMarketplaceKeyPool(marketplaceKeyPool.page + 1)">Вперёд<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg></button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

const props = defineProps({
  marketplace: { type: String, required: true }, storeCode: { type: String, default: '' }, productKey: { type: String, default: '' }, productTitle: { type: String, default: '' }, marketplaceKeyPool: { type: Object, default: () => ({ free_count: 0, reserved_count: 0, delivered_count: 0, expired_count: 0, total: 0, page: 1, page_size: 20, items: [] }) }, marketplaceKeyPoolLoading: { type: Boolean, default: false }, marketplaceKeyPoolSaving: { type: Boolean, default: false }, marketplaceKeyPoolError: { type: String, default: '' }, marketplaceKeyPoolTotalPages: { type: Number, default: 1 }, marketplaceKeyPoolRevealingId: { type: Number, default: 0 }, marketplaceKeyPoolRevealedCode: { type: Function, default: () => '' }, openMarketplaceKeyPool: { type: Function, default: () => {} }, loadMarketplaceKeyPool: { type: Function, default: () => {} }, revealMarketplaceKeyPoolKey: { type: Function, default: () => {} }, deleteMarketplaceKeyPoolKey: { type: Function, default: () => {} }, deleteAllFreeMarketplaceKeyPoolKeys: { type: Function, default: () => {} },
})

const isOpen = ref(false)

const pageRange = computed(() => { const from = (Number(props.marketplaceKeyPool.page || 1) - 1) * Number(props.marketplaceKeyPool.page_size || 20) + 1; const to = Math.min(Number(props.marketplaceKeyPool.total || 0), from + Number(props.marketplaceKeyPool.items?.length || 0) - 1); return `${from}–${to} из ${props.marketplaceKeyPool.total}` })

function statusLabel(status) {
  // Переводит технический статус ключа в короткую подпись для таблицы.
  const labels = { free: 'Свободен', reserved: 'Зарезервирован', sending: 'Передаётся', delivered: 'Выдан', expired: 'Истёк', disabled: 'Отключён' }
  return labels[String(status || '')] || 'Неизвестно'
}

function formatDate(value) {
  // Показывает дату действия ключа в привычном оператору формате.
  if (!value) return '—'
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium' }).format(date)
}

function openAddDialog() {
  // Передает кабинет вместе с карточкой, чтобы добавленный ключ не попал в пул другого магазина.
  props.openMarketplaceKeyPool({ marketplace: props.marketplace, storeCode: props.storeCode, productKey: props.productKey, productTitle: props.productTitle })
}

function toggleOpen() {
  // Сворачивает большую таблицу пула, сохраняя настройки карточки компактными.
  isOpen.value = !isOpen.value
}
</script>
