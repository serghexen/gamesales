<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div
        v-if="canManageRolePermissions"
        class="tabs profile-admin-links"
      >
        <router-link class="tab" :to="{ name: 'work', query: { ...routeQuery, tab: 'profile', admin_panel: undefined } }">
          Пользователи
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'profile' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'profile', admin_panel: 'access' } }">
          Доступы
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'analytics' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics', admin_panel: undefined } }">
          Аналитика
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'catalogs' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs', admin_panel: undefined } }">
          Справочники
        </router-link>
      </div>
    </div>

    <section class="panel admin-content-shell">
      <div class="panel__body">
        <p v-if="catalogsError" class="bad">{{ catalogsError }}</p>
        <p v-if="catalogsOk" class="ok">{{ catalogsOk }}</p>

        <div v-if="catalogsLoading" class="loader-wrap loader-overlay">
          <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster">
            <div class="wheel"></div>
            <div class="hamster">
              <div class="hamster__body">
                <div class="hamster__head">
                  <div class="hamster__ear"></div>
                  <div class="hamster__eye"></div>
                  <div class="hamster__nose"></div>
                </div>
                <div class="hamster__limb hamster__limb--fr"></div>
                <div class="hamster__limb hamster__limb--fl"></div>
                <div class="hamster__limb hamster__limb--br"></div>
                <div class="hamster__limb hamster__limb--bl"></div>
                <div class="hamster__tail"></div>
              </div>
            </div>
            <div class="spoke"></div>
          </div>
        </div>

        <div v-else>
          <!-- Модалки справочников живут отдельно, чтобы не раздувать шаблон -->
          <WorkCatalogModals :ctx="catalogModalsCtx" />

          <div class="catalog-grid">
        <div class="catalog catalog--domain">
          <div class="panel__head">
            <div class="toolbar-actions">
              <button class="deal-create-btn" type="button" @click="openDomainModal" aria-label="Добавить домен" title="Добавить домен">
                <span class="deal-create-btn__text">Домен</span>
                <span class="deal-create-btn__icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                    <line y2="19" y1="5" x2="12" x1="12"></line>
                    <line y2="12" y1="12" x2="19" x1="5"></line>
                  </svg>
                </span>
              </button>
            </div>
            <div class="toolbar-actions">
              <button
                class="catalog-refresh-btn"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadDomains"
                :disabled="catalogsLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <table v-if="sortedDomains.length" ref="domainsTableEl" class="table table--compact">
            <colgroup>
              <col :style="getDomainsColumnStyle('name')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  <span class="th-title">
                    Домен
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по домену"
                      title="Сортировка по домену"
                      @click.stop="toggleDomainsSort"
                      :class="getDomainsSortClass()"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Домен"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startDomainsResize($event, 'name')"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in sortedDomains" :key="d.name" class="clickable-row" @click="openEditDomain(d)">
                <td>{{ d.name }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Пока нет доменов.</p>
        </div>

        <div class="catalog catalog--source">
          <div class="panel__head">
            <div class="toolbar-actions">
              <button class="deal-create-btn" type="button" @click="openSourceModal" aria-label="Добавить источник" title="Добавить источник">
                <span class="deal-create-btn__text">Источник</span>
                <span class="deal-create-btn__icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                    <line y2="19" y1="5" x2="12" x1="12"></line>
                    <line y2="12" y1="12" x2="19" x1="5"></line>
                  </svg>
                </span>
              </button>
            </div>
            <div class="toolbar-actions">
              <button
                class="catalog-refresh-btn"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadSources"
                :disabled="catalogsLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <table v-if="sortedSources.length" ref="sourcesTableEl" class="table table--compact">
            <colgroup>
              <col :style="getSourcesColumnStyle('code')" />
              <col :style="getSourcesColumnStyle('name')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  <span class="th-title">
                    Код
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по коду"
                      title="Сортировка по коду"
                      @click.stop="toggleSourcesSort('code')"
                      :class="getKeyedSortClass(sourcesSort, 'code')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Код источника"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startSourcesResize($event, 'code')"
                  />
                </th>
                <th>
                  <span class="th-title">
                    Название
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по названию"
                      title="Сортировка по названию"
                      @click.stop="toggleSourcesSort('name')"
                      :class="getKeyedSortClass(sourcesSort, 'name')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Название источника"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startSourcesResize($event, 'name')"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in sortedSources" :key="s.source_id" class="clickable-row" @click="openEditSource(s)">
                <td>{{ s.code }}</td>
                <td>{{ s.name }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Пока нет источников.</p>
        </div>

        <div class="catalog catalog--platform">
          <div class="panel__head">
            <div class="toolbar-actions">
              <button class="deal-create-btn" type="button" @click="openPlatformModal" aria-label="Добавить платформу" title="Добавить платформу">
                <span class="deal-create-btn__text">Платформа</span>
                <span class="deal-create-btn__icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                    <line y2="19" y1="5" x2="12" x1="12"></line>
                    <line y2="12" y1="12" x2="19" x1="5"></line>
                  </svg>
                </span>
              </button>
            </div>
            <div class="toolbar-actions">
              <button
                class="catalog-refresh-btn"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadCatalogs"
                :disabled="catalogsLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <table v-if="sortedPlatforms.length" ref="platformsTableEl" class="table table--compact">
            <colgroup>
              <col :style="getPlatformsColumnStyle('code')" />
              <col :style="getPlatformsColumnStyle('name')" />
              <col :style="getPlatformsColumnStyle('slots')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  <span class="th-title">
                    Код
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по коду"
                      title="Сортировка по коду"
                      @click.stop="togglePlatformsSort('code')"
                      :class="getKeyedSortClass(platformsSort, 'code')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Код платформы"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startPlatformsResize($event, 'code')"
                  />
                </th>
                <th>
                  <span class="th-title">
                    Название
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по названию"
                      title="Сортировка по названию"
                      @click.stop="togglePlatformsSort('name')"
                      :class="getKeyedSortClass(platformsSort, 'name')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Название платформы"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startPlatformsResize($event, 'name')"
                  />
                </th>
                <th>
                  <span class="th-title">
                    Слоты
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по слотам"
                      title="Сортировка по слотам"
                      @click.stop="togglePlatformsSort('slot_capacity')"
                      :class="getKeyedSortClass(platformsSort, 'slot_capacity')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Слоты платформы"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startPlatformsResize($event, 'slots')"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in sortedPlatforms" :key="p.code" class="clickable-row" @click="openEditPlatform(p)">
                <td>{{ p.code }}</td>
                <td>{{ p.name }}</td>
                <td>{{ p.slot_capacity }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Пока нет платформ.</p>
        </div>

        <div class="catalog catalog--region">
          <div class="panel__head">
            <div class="toolbar-actions">
              <button class="deal-create-btn" type="button" @click="openRegionModal" aria-label="Добавить регион" title="Добавить регион">
                <span class="deal-create-btn__text">Регион</span>
                <span class="deal-create-btn__icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                    <line y2="19" y1="5" x2="12" x1="12"></line>
                    <line y2="12" y1="12" x2="19" x1="5"></line>
                  </svg>
                </span>
              </button>
            </div>
            <div class="toolbar-actions">
              <button
                class="catalog-refresh-btn"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadCatalogs"
                :disabled="catalogsLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <table v-if="sortedRegions.length" ref="regionsTableEl" class="table table--compact">
            <colgroup>
              <col :style="getRegionsColumnStyleByRole('code')" />
              <col :style="getRegionsColumnStyleByRole('name')" />
              <col v-if="isAdmin" :style="getRegionsColumnStyleByRole('rate')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  <span class="th-title">
                    Код
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по коду"
                      title="Сортировка по коду"
                      @click.stop="toggleRegionsSort('code')"
                      :class="getKeyedSortClass(regionsSort, 'code')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Код региона"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startRegionsResizeByRole($event, 'code')"
                  />
                </th>
                <th>
                  <span class="th-title">
                    Название
                    <button
                      class="filter-icon filter-icon--sort"
                      type="button"
                      aria-label="Сортировка по названию"
                      title="Сортировка по названию"
                      @click.stop="toggleRegionsSort('name')"
                      :class="getKeyedSortClass(regionsSort, 'name')"
                    >
                      <svg viewBox="0 0 24 24">
                        <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                        <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                      </svg>
                    </button>
                  </span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Название региона"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startRegionsResizeByRole($event, 'name')"
                  />
                </th>
                <th v-if="isAdmin">
                  <span class="th-title">Коэф.</span>
                  <button
                    class="table-col-resizer"
                    type="button"
                    aria-label="Изменить ширину колонки Коэффициент региона"
                    title="Потяните для изменения ширины"
                    @mousedown.stop.prevent="startRegionsResizeByRole($event, 'rate')"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in sortedRegions" :key="r.code" class="clickable-row" @click="openEditRegion(r)">
                <td>{{ r.code }}</td>
                <td>{{ r.name }}</td>
                <td v-if="isAdmin">{{ r.purchase_cost_rate }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Пока нет регионов.</p>
        </div>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { reactive, ref, toRefs } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'
import WorkCatalogModals from './WorkCatalogModals.vue'

// Один объект контекста, чтобы компонент был проще подключать.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const domainsTableEl = ref(null)
const sourcesTableEl = ref(null)
const platformsTableEl = ref(null)
const regionsTableEl = ref(null)

const { getColumnStyle: getDomainsColumnStyle, startResize: startDomainsResize } = useResizableTableColumns({
  tableRef: domainsTableEl,
  storageKey: 'work.catalogs.domains.columns.v1',
  columns: [
    { key: 'name', defaultWidth: 100, minWidth: 36 },
  ],
})

const { getColumnStyle: getSourcesColumnStyle, startResize: startSourcesResize } = useResizableTableColumns({
  tableRef: sourcesTableEl,
  storageKey: 'work.catalogs.sources.columns.v1',
  columns: [
    { key: 'code', defaultWidth: 34, minWidth: 18 },
    { key: 'name', defaultWidth: 66, minWidth: 32 },
  ],
})

const { getColumnStyle: getPlatformsColumnStyle, startResize: startPlatformsResize } = useResizableTableColumns({
  tableRef: platformsTableEl,
  storageKey: 'work.catalogs.platforms.columns.v1',
  columns: [
    { key: 'code', defaultWidth: 24, minWidth: 14 },
    { key: 'name', defaultWidth: 56, minWidth: 30 },
    { key: 'slots', defaultWidth: 20, minWidth: 12 },
  ],
})

const { getColumnStyle: getRegionsColumnStyle, startResize: startRegionsResize } = useResizableTableColumns({
  tableRef: regionsTableEl,
  storageKey: 'work.catalogs.regions.admin.columns.v1',
  columns: [
    { key: 'code', defaultWidth: 24, minWidth: 14 },
    { key: 'name', defaultWidth: 56, minWidth: 30 },
    { key: 'rate', defaultWidth: 20, minWidth: 12 },
  ],
})

const { getColumnStyle: getRegionsUserColumnStyle, startResize: startRegionsUserResize } = useResizableTableColumns({
  tableRef: regionsTableEl,
  storageKey: 'work.catalogs.regions.user.columns.v1',
  columns: [
    { key: 'code', defaultWidth: 30, minWidth: 16 },
    { key: 'name', defaultWidth: 70, minWidth: 34 },
  ],
})

// Возвращает стиль ширины колонки в зависимости от роли, чтобы не оставлять "пустые" проценты.
function getRegionsColumnStyleByRole(key) {
  return isAdmin.value ? getRegionsColumnStyle(key) : getRegionsUserColumnStyle(key)
}

// Запускает ресайз для текущего набора колонок таблицы регионов.
function startRegionsResizeByRole(event, key) {
  if (isAdmin.value) {
    startRegionsResize(event, key)
    return
  }
  startRegionsUserResize(event, key)
}

const {
  activeTab,
  routeQuery,
  canManageRolePermissions,
  catalogsError,
  catalogsOk,
  catalogsLoading,
  catalogModalsCtx,
  openDomainModal,
  loadDomains,
  sortedDomains,
  toggleDomainsSort,
  getDomainsSortClass,
  openEditDomain,
  openSourceModal,
  loadSources,
  sortedSources,
  toggleSourcesSort,
  getKeyedSortClass,
  sourcesSort,
  openEditSource,
  openPlatformModal,
  loadCatalogs,
  sortedPlatforms,
  togglePlatformsSort,
  platformsSort,
  openEditPlatform,
  openRegionModal,
  sortedRegions,
  toggleRegionsSort,
  regionsSort,
  openEditRegion,
  isAdmin,
} = toRefs(ctx)
</script>
