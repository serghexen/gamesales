<template>
  <section class="panel panel--wide">
    <div v-if="canManageRolePermissions" class="panel__body">
      <div class="tabs profile-admin-links">
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
      <div class="panel__head analytics-head">
        <div>
          <h2>Аналитика</h2>
          <p class="muted">Продажи и шеринг (по завершенным сделкам).</p>
        </div>
        <div class="analytics-head__actions">
          <button class="ghost" type="button" :disabled="ctx.analyticsLoading" @click="ctx.loadAnalytics">
            Применить
          </button>
          <button class="catalog-refresh-btn" type="button" :disabled="ctx.analyticsLoading" aria-label="Обновить" title="Обновить" @click="ctx.loadAnalytics">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v6h-6" />
            </svg>
          </button>
        </div>
      </div>
      <div class="panel__body">
        <div class="analytics-filters">
          <label class="field">
            <span class="label">Период с</span>
            <input v-model="ctx.analyticsFilters.date_from" class="input" type="date" :max="ctx.analyticsFilters.date_to || ctx.maxDate" />
          </label>
          <label class="field">
            <span class="label">Период по</span>
            <input v-model="ctx.analyticsFilters.date_to" class="input" type="date" :min="ctx.analyticsFilters.date_from || ctx.minDate" :max="ctx.maxDate" />
          </label>
          <label class="field">
            <span class="label">Тип сделки</span>
            <select v-model="ctx.analyticsFilters.deal_type_code" class="input input--select">
              <option value="">Все</option>
              <option v-for="t in ctx.dealTypeOptions" :key="t.code" :value="t.code">{{ t.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="label">Регион</span>
            <select v-model="ctx.analyticsFilters.region_code" class="input input--select">
              <option value="">Все</option>
              <option v-for="r in ctx.regions" :key="r.code" :value="r.code">{{ r.name }} ({{ r.code }})</option>
            </select>
          </label>
          <label class="field">
            <span class="label">Источник</span>
            <select v-model.number="ctx.analyticsFilters.source_id" class="input input--select">
              <option value="">Все</option>
              <option v-for="s in ctx.sourcesByCode" :key="s.source_id" :value="s.source_id">{{ s.name }} ({{ s.code }})</option>
            </select>
          </label>
        </div>

      <p v-if="ctx.analyticsError" class="bad">{{ ctx.analyticsError }}</p>
      <p v-if="!ctx.analyticsLoaded && !ctx.analyticsLoading" class="muted">Укажите за какой период вывести отчет.</p>

      <div v-else-if="ctx.analyticsLoading" class="loader-wrap loader-wrap--compact">
        <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster wheel-and-hamster--mini">
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

      <div v-else class="analytics-cards">
        <div class="mini">
          <div class="mini__label">Сделок</div>
          <div class="mini__value">{{ ctx.analyticsTotals.count }}</div>
        </div>
        <div class="mini">
          <div class="mini__label">Закуп</div>
          <div class="mini__value">{{ ctx.formatPrice(ctx.analyticsTotals.purchase_cost) }}</div>
        </div>
        <div class="mini">
          <div class="mini__label">Выручка</div>
          <div class="mini__value">{{ ctx.formatPrice(ctx.analyticsTotals.revenue) }}</div>
        </div>
        <div class="mini">
          <div class="mini__label">Маржа</div>
          <div class="mini__value">{{ ctx.formatPrice(ctx.analyticsTotals.margin) }}</div>
        </div>
        <div class="mini">
          <div class="mini__label">Средний чек</div>
          <div class="mini__value">{{ ctx.formatPrice(ctx.analyticsTotals.avg_check) }}</div>
        </div>
      </div>

      <div class="divider"></div>

      <div class="analytics-grid">
        <div>
          <h3>По дням</h3>
          <table v-if="ctx.analyticsByDay.length" ref="byDayTableEl" class="table table--compact table--dense">
            <colgroup>
              <col :style="getByDayColumnStyle('date')" />
              <col :style="getByDayColumnStyle('purchase')" />
              <col :style="getByDayColumnStyle('revenue')" />
              <col :style="getByDayColumnStyle('margin')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  Дата
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Дата" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByDayResize($event, 'date')" />
                </th>
                <th>
                  Закуп
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Закуп" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByDayResize($event, 'purchase')" />
                </th>
                <th>
                  Выручка
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Выручка" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByDayResize($event, 'revenue')" />
                </th>
                <th>Маржа</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in ctx.analyticsByDay" :key="row.date">
                <td>{{ ctx.formatDateOnly(row.date) }}</td>
                <td>{{ ctx.formatPrice(row.purchase_cost) }}</td>
                <td>{{ ctx.formatPrice(row.revenue) }}</td>
                <td>{{ ctx.formatPrice(row.margin) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Нет данных за выбранный период.</p>
        </div>
        <div>
          <h3>По типам</h3>
          <table v-if="ctx.analyticsByType.length" ref="byTypeTableEl" class="table table--compact table--dense">
            <colgroup>
              <col :style="getByTypeColumnStyle('type')" />
              <col :style="getByTypeColumnStyle('purchase')" />
              <col :style="getByTypeColumnStyle('revenue')" />
              <col :style="getByTypeColumnStyle('margin')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  Тип
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Тип сделки" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByTypeResize($event, 'type')" />
                </th>
                <th>
                  Закуп
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Закуп по типам" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByTypeResize($event, 'purchase')" />
                </th>
                <th>
                  Выручка
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Выручка по типам" title="Потяните для изменения ширины" @mousedown.stop.prevent="startByTypeResize($event, 'revenue')" />
                </th>
                <th>Маржа</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in ctx.analyticsByType" :key="row.deal_type_code">
                <td>{{ ctx.getDealTypeName(row.deal_type_code) }}</td>
                <td>{{ ctx.formatPrice(row.purchase_cost) }}</td>
                <td>{{ ctx.formatPrice(row.revenue) }}</td>
                <td>{{ ctx.formatPrice(row.margin) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Нет данных по типам.</p>
        </div>
      </div>

      <div class="divider"></div>

      <div class="analytics-grid">
        <div>
          <h3>Источники: по количеству</h3>
          <table v-if="ctx.analyticsSourcesTopCount.length" ref="sourcesCountTableEl" class="table table--compact table--dense">
            <colgroup>
              <col :style="getSourcesCountColumnStyle('source')" />
              <col :style="getSourcesCountColumnStyle('count')" />
              <col :style="getSourcesCountColumnStyle('revenue')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  Источник
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Источник по количеству" title="Потяните для изменения ширины" @mousedown.stop.prevent="startSourcesCountResize($event, 'source')" />
                </th>
                <th>
                  Сделок
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Сделок по источникам" title="Потяните для изменения ширины" @mousedown.stop.prevent="startSourcesCountResize($event, 'count')" />
                </th>
                <th>Выручка</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in ctx.analyticsSourcesTopCount" :key="row.source_id || row.source_code || row.source_name">
                <td>{{ row.source_name || row.source_code || '—' }}</td>
                <td>{{ row.deals_count }}</td>
                <td>{{ ctx.formatPrice(row.revenue) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Нет данных по источникам.</p>
        </div>
        <div>
          <h3>Источники: по выручке</h3>
          <table v-if="ctx.analyticsSourcesTopRevenue.length" ref="sourcesRevenueTableEl" class="table table--compact table--dense">
            <colgroup>
              <col :style="getSourcesRevenueColumnStyle('source')" />
              <col :style="getSourcesRevenueColumnStyle('revenue')" />
              <col :style="getSourcesRevenueColumnStyle('count')" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  Источник
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Источник по выручке" title="Потяните для изменения ширины" @mousedown.stop.prevent="startSourcesRevenueResize($event, 'source')" />
                </th>
                <th>
                  Выручка
                  <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Выручка по источникам" title="Потяните для изменения ширины" @mousedown.stop.prevent="startSourcesRevenueResize($event, 'revenue')" />
                </th>
                <th>Сделок</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in ctx.analyticsSourcesTopRevenue" :key="row.source_id || row.source_code || row.source_name">
                <td>{{ row.source_name || row.source_code || '—' }}</td>
                <td>{{ ctx.formatPrice(row.revenue) }}</td>
                <td>{{ row.deals_count }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">Нет данных по источникам.</p>
        </div>
        <div>
          <h3>Повторные клиенты</h3>
          <div class="mini">
            <div class="mini__label">Повторные</div>
            <div class="mini__value">{{ ctx.analyticsRepeatCustomers.repeat_count }}</div>
          </div>
          <div class="mini">
            <div class="mini__label">Всего клиентов</div>
            <div class="mini__value">{{ ctx.analyticsRepeatCustomers.total_customers }}</div>
          </div>
          <div class="mini">
            <div class="mini__label">Доля повторных</div>
            <div class="mini__value">{{ ctx.formatPercent(ctx.analyticsRepeatCustomers.repeat_share) }}</div>
          </div>
        </div>
      </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, ref, unref } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'

const byDayTableEl = ref(null)
const byTypeTableEl = ref(null)
const sourcesCountTableEl = ref(null)
const sourcesRevenueTableEl = ref(null)

const { getColumnStyle: getByDayColumnStyle, startResize: startByDayResize } = useResizableTableColumns({
  tableRef: byDayTableEl,
  storageKey: 'work.analytics.byday.columns.v1',
  columns: [
    { key: 'date', defaultWidth: 25, minWidth: 16 },
    { key: 'purchase', defaultWidth: 25, minWidth: 16 },
    { key: 'revenue', defaultWidth: 25, minWidth: 16 },
    { key: 'margin', defaultWidth: 25, minWidth: 16 },
  ],
})

const { getColumnStyle: getByTypeColumnStyle, startResize: startByTypeResize } = useResizableTableColumns({
  tableRef: byTypeTableEl,
  storageKey: 'work.analytics.bytype.columns.v1',
  columns: [
    { key: 'type', defaultWidth: 28, minWidth: 18 },
    { key: 'purchase', defaultWidth: 24, minWidth: 16 },
    { key: 'revenue', defaultWidth: 24, minWidth: 16 },
    { key: 'margin', defaultWidth: 24, minWidth: 16 },
  ],
})

const { getColumnStyle: getSourcesCountColumnStyle, startResize: startSourcesCountResize } = useResizableTableColumns({
  tableRef: sourcesCountTableEl,
  storageKey: 'work.analytics.sourcescount.columns.v1',
  columns: [
    { key: 'source', defaultWidth: 46, minWidth: 24 },
    { key: 'count', defaultWidth: 22, minWidth: 14 },
    { key: 'revenue', defaultWidth: 32, minWidth: 18 },
  ],
})

const { getColumnStyle: getSourcesRevenueColumnStyle, startResize: startSourcesRevenueResize } = useResizableTableColumns({
  tableRef: sourcesRevenueTableEl,
  storageKey: 'work.analytics.sourcesrevenue.columns.v1',
  columns: [
    { key: 'source', defaultWidth: 46, minWidth: 24 },
    { key: 'revenue', defaultWidth: 32, minWidth: 18 },
    { key: 'count', defaultWidth: 22, minWidth: 14 },
  ],
})

const props = defineProps({
  ctx: { type: Object, required: true },
})

// Держим состояние роутера и вкладок, чтобы стабильно переключаться внутри админ-блока.
const activeTab = computed(() => String(unref(props.ctx.activeTab) || ''))
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
const canManageRolePermissions = computed(() => Boolean(unref(props.ctx.canManageRolePermissions)))
</script>
