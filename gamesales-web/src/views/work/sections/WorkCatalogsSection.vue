<template>
  <section class="panel panel--wide">
    <div class="panel__head"></div>
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

        <div class="catalog">
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
                class="btn btn--icon btn--glow btn--glow-refresh"
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
          <table v-if="sortedDomains.length" class="table table--compact">
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

        <div class="catalog">
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
                class="btn btn--icon btn--glow btn--glow-refresh"
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
          <table v-if="sortedSources.length" class="table table--compact">
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

        <div class="catalog">
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
                class="btn btn--icon btn--glow btn--glow-refresh"
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
          <table v-if="sortedPlatforms.length" class="table table--compact">
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

        <div class="catalog">
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
                class="btn btn--icon btn--glow btn--glow-refresh"
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
          <table v-if="sortedRegions.length" class="table table--compact">
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
                </th>
                <th v-if="isAdmin">Коэф.</th>
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
  </section>
</template>

<script setup>
import { reactive, toRefs } from 'vue'
import WorkCatalogModals from './WorkCatalogModals.vue'

// Один объект контекста, чтобы компонент был проще подключать.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
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
