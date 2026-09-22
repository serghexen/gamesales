<template>
  <section class="panel panel--wide voucher-warehouse">
    <div class="panel__body">
      <div class="tabs profile-admin-links">
        <router-link v-for="tab in adminTabs" :key="tab.key" class="tab" :class="{ active: tab.key === 'voucher-warehouse' }"
          :to="{ name: 'work', query: { ...ctx.routeQuery, tab: tab.key === 'access' ? 'profile' : tab.key, admin_panel: tab.key === 'access' ? 'access' : undefined } }">{{ tab.label }}</router-link>
      </div>
    </div>
    <section class="panel admin-content-shell voucher-warehouse__shell">
      <div class="panel__body">
        <div class="voucher-warehouse__heading">
          <div><h2>Склад ключей</h2><p class="muted">Собственные запасы по номиналам каталога</p></div>
          <button class="account-refresh-btn" type="button" title="Обновить склад" aria-label="Обновить склад" :disabled="w.loading || w.saving" @click="w.load">
            <span class="account-refresh-btn__content"><svg class="account-refresh-btn__icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M16 8a6.2 6.2 0 1 0-.6 5M16 3v5h-5" /></svg></span>
          </button>
        </div>
        <div class="voucher-warehouse__toolbar">
          <input v-model="w.search" class="input" type="search" placeholder="Услуга, номинал или SKU" aria-label="Поиск по складу">
          <span class="muted">Услуг: {{ groups.length }} · Номиналов: {{ w.filtered.length }}</span>
        </div>
        <p v-if="w.error" class="bad" role="alert">{{ w.error }}</p>
        <p v-if="w.loading && !w.items.length" class="muted">Загружаем склад…</p>
        <p v-else-if="!w.items.length && !w.error" class="voucher-warehouse__empty muted">Добавьте номиналы в каталоге — здесь появятся позиции для хранения ключей.</p>
        <p v-else-if="w.items.length && !w.filtered.length" class="muted">По вашему запросу ничего не найдено.</p>
        <section v-for="group in groups" :key="group.id" class="voucher-warehouse__group" :class="{ 'is-expanded': isExpanded(group.id) }">
          <button class="voucher-warehouse__group-title" type="button" :aria-expanded="isExpanded(group.id)" :aria-controls="`warehouse-service-${group.id}`" :disabled="w.saving" @click="toggleGroup(group)">
            <svg class="voucher-warehouse__chevron" viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg>
            <strong>{{ group.name }}</strong><span class="voucher-warehouse__nominal-count muted">Номиналов: {{ group.rows.length }}</span>
          </button>
          <div v-if="isExpanded(group.id)" :id="`warehouse-service-${group.id}`" class="table-wrap">
            <table class="voucher-warehouse__table">
              <colgroup><col style="width: 36%"><col style="width: 28%"><col style="width: 12%"><col style="width: 10%"><col style="width: 14%"></colgroup>
              <thead><tr><th>Номинал / SKU</th><th>Цена пула, ₽</th><th class="voucher-warehouse__number">Свободно</th><th class="voucher-warehouse__number">Всего</th><th>Действия</th></tr></thead>
              <tbody>
                <template v-for="row in group.rows" :key="row.catalog_nominal_id">
                  <tr :class="{ 'is-selected': w.selectedId === row.catalog_nominal_id }">
                    <td><strong>{{ row.name }}</strong><code class="voucher-warehouse__sku">{{ row.sku }}</code></td>
                    <td>
                      <form v-if="w.canManage" class="voucher-warehouse__price" @submit.prevent="w.savePrice(row)">
                        <input v-model="w.prices[row.catalog_nominal_id]" class="input" inputmode="decimal" :aria-label="`Цена пула ${row.sku}`" placeholder="Не задана" :disabled="w.saving" maxlength="21">
                        <button type="submit" class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save" :aria-label="`Сохранить цену ${row.sku}`" title="Сохранить цену пула" :disabled="w.saving || w.prices[row.catalog_nominal_id] === String(row.price ?? '')">
                          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h12l4 4v12H4zM7 4v6h8V4M7 20v-6h10v6" /></svg>
                        </button>
                      </form>
                      <span v-else>{{ money(row.price) }}</span>
                    </td>
                    <td class="voucher-warehouse__number"><strong :class="{ 'voucher-warehouse__available': row.free_count > 0 }">{{ row.free_count }}</strong></td>
                    <td class="voucher-warehouse__number muted">{{ row.total }}</td>
                    <td class="voucher-warehouse__actions"><button v-if="w.canManage" class="ghost" type="button" :disabled="w.saving" :aria-expanded="w.selectedId === row.catalog_nominal_id" :aria-label="`Ключи ${row.sku}`" @click="w.openKeys(row)">{{ w.selectedId === row.catalog_nominal_id ? 'Свернуть' : 'Ключи' }}<svg viewBox="0 0 20 20" aria-hidden="true" :class="{ 'is-open': w.selectedId === row.catalog_nominal_id }"><path d="m6 8 4 4 4-4" /></svg></button></td>
                  </tr>
                  <tr v-if="w.selectedId === row.catalog_nominal_id" class="voucher-warehouse__details">
                    <td colspan="5">
                      <WorkMarketplaceKeyPoolPanel :key="row.catalog_nominal_id" marketplace="warehouse" store-code="warehouse" :product-key="String(row.catalog_nominal_id)" :product-title="w.pool.product_title"
                        compact initially-open allow-expired-deletion :marketplace-key-pool="w.pool" :marketplace-key-pool-loading="w.keysLoading" :marketplace-key-pool-saving="w.saving"
                        :marketplace-key-pool-error="w.keysError" :marketplace-key-pool-total-pages="w.totalPages" :marketplace-key-pool-revealing-id="w.revealingId"
                        :marketplace-key-pool-revealed-code="revealedCode" :open-marketplace-key-pool="w.openAdd" :load-marketplace-key-pool="w.loadKeys"
                        :reveal-marketplace-key-pool-key="w.reveal" :delete-marketplace-key-pool-key="w.remove" :delete-all-free-marketplace-key-pool-keys="removeFree" />
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
    <WorkMarketplaceKeyPoolModal v-if="w.showAdd" label="Склад" :show-marketplace-key-pool="w.showAdd" :close-marketplace-key-pool="w.closeAdd"
      :marketplace-key-pool="w.pool" :marketplace-key-pool-loading="w.keysLoading" :marketplace-key-pool-saving="w.saving"
      :marketplace-key-pool-error="w.keysError" :marketplace-key-pool-ok="w.keysOk" :add-marketplace-key-pool-keys="w.addKeys" />
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, proxyRefs, ref, watch } from 'vue'
import { useVoucherWarehouse } from '../useVoucherWarehouse'
import WorkMarketplaceKeyPoolPanel from './WorkMarketplaceKeyPoolPanel.vue'
import WorkMarketplaceKeyPoolModal from './WorkMarketplaceKeyPoolModal.vue'

const props = defineProps({ ctx: { type: Object, required: true } })
const w = proxyRefs(useVoucherWarehouse(() => props.ctx.token, (options) => props.ctx.requestDealConfirm?.(options)))
const expandedServices = ref(new Set())
const groups = computed(() => {
  // Объединяем по ID услуги: одинаковые названия разных услуг не смешивают их запасы.
  const result = new Map()
  for (const row of w.filtered) {
    if (!result.has(row.item_id)) result.set(row.item_id, { id: row.item_id, name: row.service_name, rows: [] })
    result.get(row.item_id).rows.push(row)
  }
  return [...result.values()].sort((a, b) => a.name.localeCompare(b.name, 'ru', { numeric: true }) || a.id - b.id)
    .map((group) => ({ ...group, rows: group.rows.sort((a, b) => a.name.localeCompare(b.name, 'ru', { numeric: true }) || a.catalog_nominal_id - b.catalog_nominal_id) }))
})

function isExpanded(id) {
  // При входе услуги свёрнуты; поиск раскрывает найденные номиналы, как в каталоге.
  return Boolean(w.search.trim()) || expandedServices.value.has(id)
}

function toggleGroup(group) {
  // Сворачивание услуги закрывает её пул и убирает раскрытые коды, сохраняя черновики цен.
  if (w.saving) return
  const next = new Set(expandedServices.value)
  if (next.has(group.id)) {
    next.delete(group.id)
    if (w.selected?.item_id === group.id) w.closeKeys()
  } else next.add(group.id)
  expandedServices.value = next
}

const adminTabs = computed(() => {
  // Права и порядок вкладок совпадают с соседним каталогом.
  return [
    ['profile', 'Пользователи', 'canViewUsersSection'], ['access', 'Доступы', 'canManageRolePermissions'],
    ['analytics', 'Аналитика', 'canViewAnalyticsSection'], ['catalogs', 'Справочники', 'canViewCatalogsSection'],
    ['finance', 'Финансы', 'canViewFinanceSection'], ['voucher-catalog', 'Каталог', 'canViewVoucherCatalogSection'],
    ['voucher-warehouse', 'Склад', 'canViewVoucherWarehouseSection'],
  ].filter(([, , permission]) => props.ctx[permission]).map(([key, label]) => ({ key, label }))
})

function money(value) {
  // Отсутствующая цена не отображается как бесплатный ключ.
  return value == null ? '—' : new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 6 }).format(Number(value))
}

function revealedCode(key) {
  // Общая таблица получает только явно раскрытые коды текущего пула.
  return w.revealed[key.id] || ''
}

function removeFree() {
  // Не передаём DOM-событие как объект ключа при массовом удалении.
  return w.remove()
}

let previousFocus = null
let previousOverflow = null
function restoreFocus() {
  // Освобождаем блокировку страницы даже при уходе на другую вкладку.
  if (previousOverflow !== null) document.body.style.overflow = previousOverflow
  previousOverflow = null
  if (previousFocus?.isConnected) previousFocus.focus()
  previousFocus = null
}

function modalKeydown(event) {
  // Удерживаем клавиатурный фокус в форме, Escape закрывает её как крестик.
  if (!w.showAdd) return
  if (event.key === 'Escape') { event.preventDefault(); w.closeAdd(); return }
  if (event.key !== 'Tab') return
  const elements = [...document.querySelectorAll('.marketplace-key-pool-backdrop button:not(:disabled), .marketplace-key-pool-backdrop textarea, .marketplace-key-pool-backdrop input')]
  if (!elements.length) return
  const index = elements.indexOf(document.activeElement)
  if (index < 0 || (!event.shiftKey && index === elements.length - 1) || (event.shiftKey && index === 0)) {
    event.preventDefault()
    elements[event.shiftKey ? elements.length - 1 : 0].focus()
  }
}

watch(() => w.showAdd, async (open) => {
  // Загруженная форма использует те же поля селлера, с локальным управлением фокусом склада.
  if (!open) { restoreFocus(); return }
  previousFocus = document.activeElement
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  await nextTick()
  document.querySelector('.marketplace-key-pool-backdrop textarea')?.focus()
})
onMounted(() => {
  // Один запрос при входе; фоновых опросов и автоматического раскрытия строк нет.
  w.load()
  document.addEventListener('keydown', modalKeydown)
})
onBeforeUnmount(() => {
  // Удаляем обработчик формы при закрытии раздела.
  document.removeEventListener('keydown', modalKeydown)
  restoreFocus()
})
</script>

<style scoped>
.voucher-warehouse__shell { padding: 20px; border-radius: 16px; }
.voucher-warehouse__heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.voucher-warehouse__heading h2 { margin: 0; font-size: 17px; font-weight: 650; text-transform: none; letter-spacing: 0; }
.voucher-warehouse__heading p { margin: 6px 0 0; font-size: 12px; }
.voucher-warehouse__toolbar { display: flex; align-items: center; gap: 16px; margin: 18px 0 14px; padding-top: 16px; border-top: 1px solid var(--stroke); font-size: 12px; }
.voucher-warehouse__toolbar .input { width: min(440px, 75%); height: 36px; border-radius: 9px; font-size: 13px; }
.voucher-warehouse__group { border: 1px solid var(--stroke); border-radius: 12px; margin-top: 10px; overflow: hidden; }
.voucher-warehouse__group-title { display: flex; align-items: center; gap: 10px; width: 100%; padding: 14px 12px; border: 0; border-radius: 0; background: rgba(128,148,180,.045); color: var(--ink); text-align: left; font: inherit; font-size: 14px; cursor: pointer; box-shadow: none; }
.voucher-warehouse__group-title:hover { background: rgba(128,148,180,.08); }
.voucher-warehouse__group-title:disabled { cursor: default; opacity: .6; }
.voucher-warehouse__group-title strong { font-weight: 650; overflow-wrap: anywhere; }
.voucher-warehouse__chevron { flex: 0 0 auto; width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; color: var(--muted); transition: transform .15s; }
.is-expanded > .voucher-warehouse__group-title .voucher-warehouse__chevron { transform: rotate(90deg); }
.voucher-warehouse__nominal-count { flex: 0 0 auto; padding: 3px 7px; background: rgba(128,148,180,.075); border-radius: 5px; font-size: 11px; font-variant-numeric: tabular-nums; }
.voucher-warehouse__table { width: 100%; font-size: 13px; table-layout: fixed; margin: 0; border-collapse: collapse; background: transparent; }
.voucher-warehouse__table > tbody > tr > td:first-child { overflow-wrap: anywhere; }
.voucher-warehouse__table > thead > tr > th { padding: 9px 12px; border-block: 1px solid var(--stroke); background: rgba(128,148,180,.025); text-align: left; font-weight: 500; color: var(--muted); font-size: 11px; }
.voucher-warehouse__table > thead > tr > .voucher-warehouse__number { text-align: right; }
.voucher-warehouse__table > thead > tr > th:last-child { text-align: right; }
.voucher-warehouse__table > tbody > tr > td { padding: 10px 12px; vertical-align: middle; border-bottom: 1px solid var(--stroke); }
.voucher-warehouse__sku { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; user-select: all; }
.voucher-warehouse__price { display: flex; align-items: center; gap: 8px; max-width: 220px; }
.voucher-warehouse__price .input { width: 140px; min-width: 0; flex: 1 1 140px; height: 34px; font-size: 13px; border-radius: 8px; font-variant-numeric: tabular-nums; }
.voucher-warehouse .voucher-warehouse__price .deal-create-action-btn { width: 32px; min-width: 32px; flex: 0 0 32px; height: 32px; padding: 7px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; border: 2px solid rgba(255,255,255,.2); color: #fff; background: linear-gradient(135deg,#10b981,#059669); box-shadow: 0 3px 10px rgba(16,185,129,.2); transition: transform .15s, box-shadow .15s; }
.voucher-warehouse .voucher-warehouse__price .deal-create-action-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(16,185,129,.35); }
.voucher-warehouse .voucher-warehouse__price .deal-create-action-btn:disabled { opacity: .35; box-shadow: none; }
.voucher-warehouse__price svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; }
.voucher-warehouse__number { text-align: right; font-variant-numeric: tabular-nums; }
.voucher-warehouse__available { color: #54d5ad; }
.voucher-warehouse__actions { text-align: right; white-space: nowrap; }
.voucher-warehouse .voucher-warehouse__actions button { display: inline-flex; align-items: center; justify-content: flex-end; gap: 7px; min-height: 32px; padding: 6px 8px; border: 0; border-radius: 7px; background: transparent; box-shadow: none; color: var(--muted); font-size: 12px; font-weight: 600; }
.voucher-warehouse .voucher-warehouse__actions button:hover:not(:disabled), .is-selected .voucher-warehouse__actions button { color: #54d5ad; background: rgba(84,213,173,.06); }
.voucher-warehouse__actions svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 1.6; }
.voucher-warehouse__actions svg.is-open { transform: rotate(180deg); }
.voucher-warehouse__table > tbody > .is-selected { background: rgba(128,148,180,.035); }
.voucher-warehouse__table > tbody > .voucher-warehouse__details > td { padding: 12px 18px 16px 26px; background: transparent; }
.voucher-warehouse__details :deep(.marketplace-key-pool-panel--compact) { padding-left: 14px; border-left: 2px solid rgba(84,213,173,.2); }
.voucher-warehouse__empty { text-align: center; padding: 28px 16px; font-size: 13px; }
.voucher-warehouse button:focus-visible, .voucher-warehouse input:focus-visible { outline: 2px solid #54d5ad; outline-offset: 3px; }
@media (max-width: 760px) {
  .voucher-warehouse__shell { padding: 14px; }
  .voucher-warehouse__table { min-width: 650px; }
  .voucher-warehouse__toolbar { gap: 10px; flex-wrap: wrap; }
  .voucher-warehouse__group-title { flex-wrap: wrap; }
}
</style>
