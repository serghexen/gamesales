<template>
  <section class="panel panel--wide">
    <div class="panel__head analytics-head">
      <div>
        <h2>Аналитика</h2>
        <p class="muted">Продажи и шеринг (по завершенным сделкам).</p>
      </div>
      <div class="analytics-head__actions">
        <button class="ghost" type="button" :disabled="ctx.analyticsLoading" @click="ctx.loadAnalytics">
          Применить
        </button>
        <button class="btn btn--icon btn--glow btn--glow-refresh" type="button" :disabled="ctx.analyticsLoading" aria-label="Обновить" title="Обновить" @click="ctx.loadAnalytics">
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
          <table v-if="ctx.analyticsByDay.length" class="table table--compact table--dense">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Закуп</th>
                <th>Выручка</th>
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
          <table v-if="ctx.analyticsByType.length" class="table table--compact table--dense">
            <thead>
              <tr>
                <th>Тип</th>
                <th>Закуп</th>
                <th>Выручка</th>
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
          <table v-if="ctx.analyticsSourcesTopCount.length" class="table table--compact table--dense">
            <thead>
              <tr>
                <th>Источник</th>
                <th>Сделок</th>
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
          <table v-if="ctx.analyticsSourcesTopRevenue.length" class="table table--compact table--dense">
            <thead>
              <tr>
                <th>Источник</th>
                <th>Выручка</th>
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
</template>

<script setup>
defineProps({
  ctx: { type: Object, required: true },
})
</script>
