<template>
  <section class="panel panel--wide voucher-catalog">
    <div class="panel__body">
      <div class="tabs profile-admin-links">
        <router-link v-for="tab in adminTabs" :key="tab.key" class="tab" :class="{ active: tab.key === 'voucher-catalog' }"
          :to="{ name: 'work', query: { ...ctx.routeQuery, tab: tab.key === 'access' ? 'profile' : tab.key, admin_panel: tab.key === 'access' ? 'access' : undefined } }">
          {{ tab.label }}
        </router-link>
      </div>
    </div>
    <section class="panel admin-content-shell voucher-catalog__shell">
      <div class="panel__body">
        <div class="voucher-catalog__heading">
          <div>
            <h2 class="section-title">Каталог ваучеров</h2>
            <p class="muted voucher-catalog__schedule"><span>Цены · ежедневно в 09:00 МСК</span><span>Остатки · каждый час</span></p>
          </div>
          <div v-if="canEdit" class="voucher-catalog__heading-actions">
            <button type="button" class="voucher-catalog__button voucher-catalog__button--primary" data-test="catalog-create-service" :disabled="saving" @click="openForm()">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12" /></svg><span>Добавить сервис</span>
            </button>
          </div>
        </div>

        <div class="voucher-catalog__toolbar">
          <div class="voucher-catalog__search">
            <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>
            <input v-model="search" class="input" type="search" placeholder="Найти услугу, номинал или SKU" aria-label="Поиск по каталогу">
          </div>
          <span class="muted voucher-catalog__total" aria-live="polite">{{ search.trim() ? `Найдено: ${filteredItems.length} из ${items.length}` : `Услуг: ${items.length}` }}</span>
          <button class="account-refresh-btn voucher-catalog__refresh" aria-label="Обновить список" title="Обновить список" type="button" :disabled="loading || saving" :aria-busy="refreshing" @click="refreshList">
            <span class="account-refresh-btn__content"><svg class="account-refresh-btn__icon" viewBox="0 0 20 20" aria-hidden="true" :class="{ 'is-loading': refreshing }"><path d="M16 8a6.2 6.2 0 1 0-.6 5M16 3v5h-5" /></svg></span>
          </button>
        </div>
        <p v-if="error" class="bad" role="alert">{{ error }}</p>
        <p v-if="!loading && !items.length && !error" class="voucher-catalog__empty muted">Добавьте услугу, например PlayStation — Turkey, и выберите её номиналы.</p>
        <p v-else-if="items.length && !filteredItems.length" class="muted">По вашему запросу ничего не найдено.</p>
        <section v-for="item in filteredItems" :key="item.item_id" class="voucher-catalog__group" :class="{ 'is-expanded': isExpanded(item.item_id) }">
          <div class="voucher-catalog__group-head">
            <button class="voucher-catalog__group-title" type="button" :aria-expanded="isExpanded(item.item_id)" @click="toggleGroup(item.item_id)">
              <svg class="voucher-catalog__chevron" viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg><strong>{{ item.name }}</strong><span class="muted voucher-catalog__nominal-count">Номиналов: {{ item.nominals.length }}</span>
            </button>
            <div v-if="canEdit" class="toolbar-actions">
              <button type="button" class="voucher-catalog__button voucher-catalog__button--quiet" :disabled="saving" @click="openForm(item)">Изменить услугу</button>
              <button type="button" class="voucher-catalog__button voucher-catalog__button--accent" :disabled="saving" @click="openForm(item, 'nominals')">+ Номиналы</button>
              <button type="button" class="voucher-catalog__button voucher-catalog__delete-service" :disabled="saving" :aria-label="`Удалить услугу ${item.name}`" title="Удалить услугу" @click="askDeleteService(item)"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M7 5V3h6v2M5 5l1 12h8l1-12M8 8v6M12 8v6" /></svg></button>
            </div>
          </div>
          <template v-if="isExpanded(item.item_id)">
            <p v-if="!item.nominals.length" class="muted voucher-catalog__empty">В услуге пока нет номиналов. Добавьте их из каталога поставщика или вручную.</p>
            <div v-else class="voucher-catalog__nominals">
              <WorkVoucherCatalogNominal v-for="nominal in sortedNominals(item)" :key="nominal.catalog_nominal_id"
                :nominal="nominal" :can-edit="canEdit" :saving="saving" :now="clock" :search="search"
                @edit="openForm(item, 'nominal', nominal)" @delete="askDelete(item, nominal)" @unlink="unlink(item.item_id, $event)" />
            </div>
          </template>
        </section>
      </div>
    </section>
    <WorkVoucherCatalogModal :ctx="modalCtx" />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, proxyRefs, ref } from 'vue'
import { useVoucherCatalog } from '../useVoucherCatalog'
import WorkVoucherCatalogModal from './WorkVoucherCatalogModal.vue'
import WorkVoucherCatalogNominal from './WorkVoucherCatalogNominal.vue'

const props = defineProps({ ctx: { type: Object, required: true } })
const catalog = useVoucherCatalog(() => props.ctx.token)
const modalCtx = proxyRefs(catalog)
const { items, canEdit, loading, saving, error, search, filteredItems, load, openForm, unlink, askDelete, askDeleteService } = catalog
const expandedServices = ref(new Set())

function isExpanded(id) {
  // При каждом входе услуги свёрнуты; поиск раскрывает найденные номиналы.
  return Boolean(search.value.trim()) || expandedServices.value.has(id)
}

function toggleGroup(id) {
  // Сворачиваем только выбранную услугу, сохраняя состояние остальных групп.
  const next = new Set(expandedServices.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedServices.value = next
}

function sortedNominals(item) {
  // Числовая сортировка ставит 500 перед 1000 независимо от порядка добавления.
  return [...item.nominals].sort((a, b) => a.name.localeCompare(b.name, 'ru', { numeric: true }))
}

const clock = ref(Date.now())
const refreshing = ref(false)
let clockTimer

async function refreshList() {
  // Кнопка показывает загрузку только при ручном обновлении списка.
  if (loading.value || saving.value) return
  refreshing.value = true
  try {
    await load()
    clock.value = Date.now()
  } finally {
    refreshing.value = false
  }
}
const adminTabs = computed(() => {
  // Навигация использует те же права, что и соседние административные разделы.
  return [
    ['profile', 'Пользователи', 'canViewUsersSection'], ['access', 'Доступы', 'canManageRolePermissions'],
    ['analytics', 'Аналитика', 'canViewAnalyticsSection'], ['catalogs', 'Справочники', 'canViewCatalogsSection'],
    ['finance', 'Финансы', 'canViewFinanceSection'], ['voucher-catalog', 'Каталог', 'canViewVoucherCatalogSection'],
    ['voucher-warehouse', 'Склад', 'canViewVoucherWarehouseSection'],
  ].filter(([, , permission]) => props.ctx[permission]).map(([key, label]) => ({ key, label }))
})

onMounted(() => {
  // Загружаем список при входе; таймер обновляет только отметки давности данных.
  load()
  clockTimer = setInterval(() => {
    clock.value = Date.now()
  }, 60000)
})
onBeforeUnmount(() => {
  // Освобождаем таймер отметок давности при выходе из раздела.
  clearInterval(clockTimer)
})
</script>

<style scoped>
/* Одна палитра и сетка только внутри каталога; соседние разделы сохраняют свои стили. */
.voucher-catalog { --catalog-accent: #54d5ad; --catalog-accent-ink: #082e23; --catalog-line: var(--stroke, rgba(160,174,198,.18)); }
.voucher-catalog .voucher-catalog__shell { padding: 20px; border-radius: 16px; }
.voucher-catalog__shell > .panel__body { margin-top: 0; }
.voucher-catalog__heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.voucher-catalog__heading-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.voucher-catalog .voucher-catalog__heading h2 { margin: 0; font-size: 17px; line-height: 1.4; font-weight: 650; letter-spacing: 0; text-transform: none; color: var(--ink); }
.voucher-catalog__schedule { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 6px 0 0; font-size: 12px; line-height: 1.5; }
.voucher-catalog__schedule span + span { border-left: 1px solid var(--catalog-line); padding-left: 16px; }
.voucher-catalog .voucher-catalog__button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 34px; padding: 7px 11px; border: 1px solid var(--catalog-line); border-radius: 8px; background: transparent; color: var(--ink); box-shadow: none; font: inherit; font-size: 12px; line-height: 1.4; font-weight: 600; white-space: nowrap; cursor: pointer; transition: background .15s, border-color .15s; }
.voucher-catalog .voucher-catalog__button:hover { background: rgba(128,148,180,.08); border-color: var(--muted); }
.voucher-catalog .voucher-catalog__button--primary { background: var(--catalog-accent); border-color: var(--catalog-accent); color: var(--catalog-accent-ink); }
.voucher-catalog .voucher-catalog__button--primary:hover { background: #6fe0bd; border-color: #6fe0bd; }
.voucher-catalog .voucher-catalog__button--accent { color: var(--catalog-accent); background: rgba(84,213,173,.08); border-color: rgba(84,213,173,.25); }
.voucher-catalog .voucher-catalog__button--accent:hover { background: rgba(84,213,173,.16); border-color: var(--catalog-accent); }
.voucher-catalog .voucher-catalog__button--quiet { border-color: transparent; color: var(--muted); }
.voucher-catalog .voucher-catalog__delete-service { border-color: transparent; color: var(--muted); padding: 7px; }
.voucher-catalog .voucher-catalog__delete-service:hover { color: #f29aa5; background: rgba(242,154,165,.08); }
.voucher-catalog .voucher-catalog__button:disabled { opacity: .5; cursor: default; }
.voucher-catalog button:focus-visible, .voucher-catalog .input:focus-visible { outline: 2px solid var(--catalog-accent); outline-offset: 3px; }
.voucher-catalog svg { flex: 0 0 auto; width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.voucher-catalog__toolbar { display: flex; align-items: center; gap: 14px; margin: 18px 0 14px; padding-top: 16px; border-top: 1px solid var(--catalog-line); }
.voucher-catalog__search { position: relative; flex: 0 1 440px; min-width: 180px; }
.voucher-catalog__search > svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.voucher-catalog .voucher-catalog__search .input { height: 36px; width: 100%; padding: 0 12px 0 36px; border-radius: 9px; font-size: 13px; }
.voucher-catalog__total { flex: 0 0 auto; font-size: 12px; font-variant-numeric: tabular-nums; }
.voucher-catalog__refresh { margin-left: auto; }
.voucher-catalog__refresh .is-loading { animation: voucher-catalog-spin 1s linear infinite; }
.voucher-catalog__group { border: 1px solid var(--catalog-line); border-radius: 12px; margin-top: 10px; overflow: hidden; }
.voucher-catalog__group-head { padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: rgba(128,148,180,.045); }
.voucher-catalog__group-title { display: flex; flex: 1; min-width: 0; align-items: center; gap: 10px; border: 0; padding: 6px 0; background: transparent; color: var(--ink); text-align: left; cursor: pointer; font: inherit; font-size: 14px; }
.voucher-catalog__group-title strong { overflow-wrap: anywhere; font-weight: 650; }
.voucher-catalog__chevron { color: var(--muted); transition: transform .15s; }
.is-expanded > .voucher-catalog__group-head .voucher-catalog__chevron { transform: rotate(90deg); }
.voucher-catalog__nominal-count { flex: 0 0 auto; padding: 3px 7px; background: rgba(128,148,180,.075); border-radius: 5px; font-size: 11px; font-variant-numeric: tabular-nums; }
.voucher-catalog__group-head .toolbar-actions { display: flex; flex: 0 0 auto; align-items: center; gap: 6px; }
.voucher-catalog__empty { padding: 28px 16px; margin: 0; text-align: center; font-size: 13px; }
@keyframes voucher-catalog-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .voucher-catalog__refresh .is-loading { animation: none; } }
@media (max-width: 760px) {
  .voucher-catalog .voucher-catalog__shell { padding: 14px; }
  .voucher-catalog__toolbar { flex-wrap: wrap; gap: 10px; }
  .voucher-catalog__search { flex: 1 1 100%; }
  .voucher-catalog__group-head { flex-wrap: wrap; gap: 6px; }
  .voucher-catalog__group-title { flex-basis: 100%; flex-wrap: wrap; }
  .voucher-catalog__group-head .toolbar-actions { margin-left: 26px; }
  .voucher-catalog__schedule { display: grid; gap: 2px; }
  .voucher-catalog__schedule span + span { border: 0; padding: 0; }
}
</style>
