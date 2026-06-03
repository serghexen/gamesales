<template>
  <section class="panel panel--wide">
    <div v-if="showAdminTabs" class="panel__body">
      <div class="tabs profile-admin-links">
        <router-link
          v-if="canViewUsersSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'profile', admin_panel: undefined } }"
        >
          Пользователи
        </router-link>
        <router-link
          v-if="canManageRolePermissions"
          class="tab"
          :class="{ active: activeTab === 'profile' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'profile', admin_panel: 'access' } }"
        >
          Доступы
        </router-link>
        <router-link
          v-if="canViewAnalyticsSection"
          class="tab"
          :class="{ active: activeTab === 'analytics' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics', admin_panel: undefined } }"
        >
          Аналитика
        </router-link>
        <router-link
          v-if="canViewCatalogsSection"
          class="tab"
          :class="{ active: activeTab === 'catalogs' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs', admin_panel: undefined } }"
        >
          Справочники
        </router-link>
        <router-link
          v-if="canViewFinanceSection"
          class="tab"
          :class="{ active: activeTab === 'finance' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'finance', admin_panel: undefined } }"
        >
          Финансы
        </router-link>
      </div>
    </div>

    <section class="panel admin-content-shell">
      <div class="panel__head analytics-head">
      </div>

      <div class="panel__body">
        <div class="tabs profile-admin-links">
          <button data-test="finance-mode-catalogs" class="tab" :class="{ active: financeMode === 'catalogs' }" type="button" @click="setFinanceMode('catalogs')">
            Справочники
          </button>
          <button data-test="finance-mode-entry" class="tab" :class="{ active: financeMode === 'entry' }" type="button" @click="setFinanceMode('entry')">
            Ввод
          </button>
          <button data-test="finance-mode-journal" class="tab" :class="{ active: financeMode === 'journal' }" type="button" @click="setFinanceMode('journal')">
            Журнал
          </button>
          <button data-test="finance-mode-integrations" class="tab" :class="{ active: financeMode === 'integrations' }" type="button" @click="setFinanceMode('integrations')">
            Интеграции
          </button>
          <button data-test="finance-mode-report" class="tab" :class="{ active: financeMode === 'report' }" type="button" @click="setFinanceMode('report')">
            Отчет по источникам
          </button>
          <button data-test="finance-mode-cash-flow" class="tab" :class="{ active: financeMode === 'cash-flow' }" type="button" @click="setFinanceMode('cash-flow')">
            Cash Flow
          </button>
        </div>

        <template v-if="financeMode === 'catalogs'">
          <p v-if="ctx.financeCatalogError" class="bad">{{ ctx.financeCatalogError }}</p>
          <p v-if="ctx.financeCatalogOk" class="good">{{ ctx.financeCatalogOk }}</p>

          <template v-if="canManageRolePermissions">
            <div class="finance-catalog-grid">
              <section class="finance-catalog-panel">
                <div class="finance-catalog-panel__head">
                  <h4 class="section-title">Типы операций</h4>
                  <div class="finance-catalog-panel__actions">
                    <button data-test="finance-open-create-type" class="deal-create-btn finance-action-btn" type="button" @click="openTypeCreateModal" aria-label="Добавить тип" title="Добавить тип">
                      <span class="deal-create-btn__text">Добавить</span>
                      <span class="deal-create-btn__icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                          <line y2="19" y1="5" x2="12" x1="12"></line>
                          <line y2="12" y1="12" x2="19" x1="5"></line>
                        </svg>
                      </span>
                    </button>
                    <button data-test="finance-refresh-types" class="deal-create-btn deal-create-btn--sharing finance-action-btn finance-action-btn--refresh" type="button" :disabled="ctx.financeCatalogSaving" @click="reloadFinanceCatalogs" aria-label="Обновить типы" title="Обновить типы">
                      <span class="deal-create-btn__text">Обновить</span>
                      <span class="deal-create-btn__icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="deal-create-btn__svg" aria-hidden="true">
                          <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                          <path d="M20 4v6h-6" />
                        </svg>
                      </span>
                    </button>
                  </div>
                </div>
                <table v-if="ctx.financeTypes.length" class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Название</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="type in ctx.financeTypes" :key="type.type_id" :data-test="`finance-type-row-${type.type_id}`" class="clickable-row" @click="openTypeEditModal(type)">
                      <td>{{ type.name }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Типы не добавлены.</p>
              </section>

              <section class="finance-catalog-panel">
                <div class="finance-catalog-panel__head">
                  <h4 class="section-title">Виды операций</h4>
                  <div class="finance-catalog-panel__actions">
                    <button data-test="finance-open-create-operation" class="deal-create-btn finance-action-btn" type="button" @click="openOperationCreateModal" aria-label="Добавить вид операции" title="Добавить вид операции">
                      <span class="deal-create-btn__text">Добавить</span>
                      <span class="deal-create-btn__icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
                          <line y2="19" y1="5" x2="12" x1="12"></line>
                          <line y2="12" y1="12" x2="19" x1="5"></line>
                        </svg>
                      </span>
                    </button>
                    <button data-test="finance-refresh-operations" class="deal-create-btn deal-create-btn--sharing finance-action-btn finance-action-btn--refresh" type="button" :disabled="ctx.financeCatalogSaving" @click="reloadFinanceCatalogs" aria-label="Обновить виды операций" title="Обновить виды операций">
                      <span class="deal-create-btn__text">Обновить</span>
                      <span class="deal-create-btn__icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="deal-create-btn__svg" aria-hidden="true">
                          <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                          <path d="M20 4v6h-6" />
                        </svg>
                      </span>
                    </button>
                  </div>
                </div>
                <table v-if="ctx.financeOperations.length" class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Тип</th>
                      <th>Источник</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="operation in ctx.financeOperations" :key="operation.operation_id" :data-test="`finance-operation-row-${operation.operation_id}`" class="clickable-row" @click="openOperationEditModal(operation)">
                      <td>{{ operation.name }}</td>
                      <td>{{ resolveOperationTypeName(operation) }}</td>
                      <td>{{ resolveSourceName(operation.source_id) }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Виды операций не добавлены.</p>
              </section>
            </div>

          </template>
          <p v-else class="muted">Редактирование finance-справочников доступно только роли с правами управления доступами.</p>
        </template>

        <template v-if="financeMode === 'entry'">
          <div class="finance-entry-wrap" :class="{ 'finance-entry-wrap--locked': ctx.financeEntrySaving }">
            <div v-if="ctx.financeEntrySaving" class="finance-entry-wrap__overlay">
              <div class="loader-wrap loader-wrap--compact">
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
                <p class="muted">Сохраняем…</p>
              </div>
            </div>

            <div class="analytics-filters">
              <label class="field">
                <span class="label">Дата</span>
                <input v-model="ctx.financeNewEntry.biz_date" class="input" type="date" :max="ctx.maxDate" />
              </label>
              <label class="field">
                <span class="label">Операция</span>
                <select v-model="ctx.financeNewEntry.operation_id" class="input input--select">
                  <option value="">Выберите</option>
                  <option v-for="op in filteredNewEntryOperations" :key="op.operation_id" :value="op.operation_id">{{ op.name }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Сумма</span>
                <input v-model="ctx.financeNewEntry.amount" class="input" type="number" step="0.01" />
              </label>
              <label class="field field--wide">
                <span class="label">Комментарий</span>
                <input v-model="ctx.financeNewEntry.comment" class="input" type="text" maxlength="255" placeholder="Опционально" />
              </label>
            </div>

            <div class="analytics-head__actions finance-actions-row">
              <button data-test="finance-save-entry" class="ghost" type="button" :disabled="ctx.financeEntrySaving" @click="submitFinanceEntry">
                {{ ctx.financeEntrySaving ? 'Сохраняем...' : 'Добавить запись' }}
              </button>
            </div>
            <p v-if="ctx.financeEntryError" class="bad">{{ ctx.financeEntryError }}</p>
            <p v-if="ctx.financeEntryOk" class="good">{{ ctx.financeEntryOk }}</p>
          </div>
        </template>

        <template v-if="financeMode === 'journal'">
          <div class="analytics-filters">
            <label class="field">
              <span class="label">Период с</span>
              <input v-model="ctx.financeEntryFilters.date_from" class="input" type="date" :max="ctx.financeEntryFilters.date_to || ctx.maxDate" />
            </label>
            <label class="field">
              <span class="label">Период по</span>
              <input v-model="ctx.financeEntryFilters.date_to" class="input" type="date" :min="ctx.financeEntryFilters.date_from || ctx.minDate" :max="ctx.maxDate" />
            </label>
            <label class="field">
              <span class="label">Тип</span>
              <select v-model="journalSectionKind" class="input input--select">
                <option value="">Все типы</option>
                <option v-for="type in entryKinds" :key="`flt-kind-${type.type_id}`" :value="String(type.type_id)">{{ type.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Операция</span>
              <select v-model="ctx.financeEntryFilters.operation_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="op in filteredJournalOperations" :key="`flt-op-${op.operation_id}`" :value="op.operation_id">{{ op.name }}</option>
              </select>
            </label>
            <label class="field">
              <button data-test="finance-apply-entries-filters" class="ghost" type="button" :disabled="ctx.financeEntriesLoading" @click="reloadFinanceEntries">Применить</button>
            </label>
          </div>

          <p v-if="ctx.financeEntriesError" class="bad">{{ ctx.financeEntriesError }}</p>
          <p v-if="ctx.financeEntriesLoading" class="muted">Загружаем журнал...</p>
          <template v-else>
            <table v-if="ctx.financeEntries.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Операция</th>
                  <th>Регион</th>
                  <th>Источник</th>
                  <th>Сумма</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in ctx.financeEntries" :key="entry.entry_id">
                  <td>{{ entry.biz_date }}</td>
                  <td>{{ resolveOperationName(entry.operation_id) }}</td>
                  <td>{{ resolveRegionName(entry.region_id) }}</td>
                  <td>{{ resolveSourceName(entry.source_id) }}</td>
                  <td>{{ ctx.formatPrice(entry.amount) }}</td>
                  <td>{{ resolveStatusName(entry.status_code) }}</td>
                  <td>
                    <button
                      :data-test="`finance-delete-entry-${entry.entry_id}`"
                      class="ghost"
                      type="button"
                      :disabled="ctx.financeEntriesLoading"
                      @click="deleteFinanceEntryRow(entry)"
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Журнал пуст.</p>
          </template>
          <p class="muted">Всего записей по фильтру: {{ ctx.financeEntriesTotal }}</p>
        </template>

        <template v-if="financeMode === 'integrations'">
          <section class="finance-integration-panel">
            <div class="finance-integration-panel__head">
              <div>
                <h4 class="section-title">Yandex Market</h4>
              </div>
              <span class="finance-integration-badge">API</span>
            </div>

            <div class="analytics-filters">
              <label class="field">
                <span class="label">Магазин</span>
                <select v-model="ctx.financeYandexSync.store_code" class="input input--select">
                  <option value="asat">ASAT - ym</option>
                  <option value="sps">SPS - ym</option>
                  <option value="mds">MDS - ym</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Период с</span>
                <input v-model="ctx.financeYandexSync.date_from" class="input" type="date" :max="ctx.financeYandexSync.date_to || ctx.maxDate" />
              </label>
              <label class="field">
                <span class="label">Период по</span>
                <input v-model="ctx.financeYandexSync.date_to" class="input" type="date" :min="ctx.financeYandexSync.date_from || ctx.minDate" :max="ctx.maxDate" />
              </label>
              <label class="field">
                <button
                  data-test="finance-sync-yandex"
                  class="ghost"
                  type="button"
                  :disabled="ctx.financeYandexSyncLoading"
                  @click="syncYandexMarket"
                >
                  {{ ctx.financeYandexSyncLoading ? 'Синхронизируем...' : 'Синхронизировать Yandex' }}
                </button>
              </label>
            </div>

            <p v-if="ctx.financeYandexSyncStatus" class="muted">{{ ctx.financeYandexSyncStatus }}</p>
            <p v-if="ctx.financeYandexSyncError" class="bad">{{ ctx.financeYandexSyncError }}</p>
            <p v-if="ctx.financeYandexSyncOk" class="good">{{ ctx.financeYandexSyncOk }}</p>

            <div v-if="ctx.financeYandexSyncResult" class="analytics-cards finance-sync-cards">
              <div class="mini">
                <div class="mini__label">Строк Яндекса</div>
                <div class="mini__value">{{ Number(ctx.financeYandexSyncResult.total_rows || 0) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Дней добавлено</div>
                <div class="mini__value">{{ Number(ctx.financeYandexSyncResult.created_rows || 0) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Дней обновлено</div>
                <div class="mini__value">{{ Number(ctx.financeYandexSyncResult.updated_rows || 0) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Дней пропущено</div>
                <div class="mini__value">{{ Number(ctx.financeYandexSyncResult.skipped_rows || 0) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Ошибки</div>
                <div class="mini__value">{{ Number(ctx.financeYandexSyncResult.failed_rows || 0) }}</div>
              </div>
            </div>
          </section>
        </template>

        <template v-if="financeMode === 'report'">
          <div class="analytics-filters">
            <label class="field">
              <span class="label">Период с</span>
              <input v-model="ctx.financeFilters.date_from" class="input" type="date" :max="ctx.financeFilters.date_to || ctx.maxDate" />
            </label>
            <label class="field">
              <span class="label">Период по</span>
              <input v-model="ctx.financeFilters.date_to" class="input" type="date" :min="ctx.financeFilters.date_from || ctx.minDate" :max="ctx.maxDate" />
            </label>
            <div class="field">
              <span class="label">Регион</span>
              <div
                class="finance-multi-filter"
                data-test="finance-report-regions"
              >
                <button
                  class="input finance-multi-filter__summary"
                  type="button"
                  :aria-expanded="openFinanceReportFilter === 'region_id'"
                  @click="toggleFinanceReportFilter('region_id')"
                >
                  {{ formatFinanceFilterSummary('region_id', ctx.financeRegions, 'name') }}
                </button>
                <div v-if="openFinanceReportFilter === 'region_id'" class="check-list check-list--finance-report">
                  <label class="check-item">
                    <input
                      type="checkbox"
                      :checked="isFinanceFilterAll('region_id')"
                      @change="setFinanceFilterAll('region_id')"
                    />
                    <span>Все</span>
                  </label>
                  <label v-for="r in ctx.financeRegions" :key="`rep-rg-${r.region_id}`" class="check-item">
                    <input
                      type="checkbox"
                      :checked="isFinanceFilterSelected('region_id', r.region_id)"
                      @change="toggleFinanceFilterId('region_id', r.region_id, $event.target.checked)"
                    />
                    <span>{{ r.name }}</span>
                  </label>
                </div>
              </div>
            </div>
            <div class="field">
              <span class="label">Источник</span>
              <div
                class="finance-multi-filter"
                data-test="finance-report-sources"
              >
                <button
                  class="input finance-multi-filter__summary"
                  type="button"
                  :aria-expanded="openFinanceReportFilter === 'source_id'"
                  @click="toggleFinanceReportFilter('source_id')"
                >
                  {{ formatFinanceFilterSummary('source_id', ctx.financeSources, 'source') }}
                </button>
                <div v-if="openFinanceReportFilter === 'source_id'" class="check-list check-list--finance-report">
                  <label class="check-item">
                    <input
                      type="checkbox"
                      :checked="isFinanceFilterAll('source_id')"
                      @change="setFinanceFilterAll('source_id')"
                    />
                    <span>Все</span>
                  </label>
                  <label v-for="s in ctx.financeSources" :key="`rep-src-${s.source_id}`" class="check-item">
                    <input
                      type="checkbox"
                      :checked="isFinanceFilterSelected('source_id', s.source_id)"
                      @change="toggleFinanceFilterId('source_id', s.source_id, $event.target.checked)"
                    />
                    <span>{{ formatSourceLabel(s) }}</span>
                  </label>
                </div>
              </div>
            </div>
            <label class="field">
              <button data-test="finance-apply-report" class="ghost" type="button" :disabled="ctx.financeLoading" @click="applyFinanceReport">Применить</button>
            </label>
          </div>

          <p v-if="ctx.financeError" class="bad">{{ ctx.financeError }}</p>
          <p v-if="!ctx.financeLoaded && !ctx.financeLoading" class="muted">Нажмите «Применить», чтобы построить отчет.</p>

          <div v-else-if="ctx.financeLoading" class="loader-wrap loader-wrap--compact">
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

          <template v-else>
            <div class="analytics-cards">
              <div class="mini">
                <div class="mini__label">Поступления</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.revenue) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Расходы</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.direct_expense) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Итог</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.operating_profit) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Маржа</div>
                <div class="mini__value">{{ ctx.formatPercent(ctx.financeReportTotals.margin) }}</div>
              </div>
            </div>

            <table v-if="ctx.financeReportItems.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Регион</th>
                  <th>Поступления</th>
                  <th>Расходы</th>
                  <th>Итог</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in ctx.financeReportItems" :key="`${row.source_id || 'no-source'}-${row.region_id || 'no-region'}-${row.source_name || 'no-name'}-${index}`">
                  <td>{{ formatSourceReportLabel(row) }}</td>
                  <td>{{ formatRegionReportLabel(row) }}</td>
                  <td>{{ ctx.formatPrice(row.revenue) }}</td>
                  <td>{{ ctx.formatPrice(row.direct_expense) }}</td>
                  <td>{{ ctx.formatPrice(resolveReportCashFlow(row)) }}</td>
                  <td class="table__actions">
                    <button
                      class="ghost ghost--compact"
                      type="button"
                      :data-test="`finance-source-details-${index}`"
                      :disabled="ctx.financeSourceDetailsLoading"
                      @click="openSourceDetails(row)"
                    >
                      Расшифровать
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Нет данных по выбранным фильтрам.</p>
          </template>
        </template>

        <template v-if="financeMode === 'cash-flow'">
          <div class="analytics-filters">
            <label class="field">
              <span class="label">Месяц</span>
              <input v-model="ctx.financeCashFlowMonth" class="input" type="month" />
            </label>
            <label class="field">
              <span class="label">Начальный остаток</span>
              <input v-model="ctx.financeCashFlowOpeningDraft" class="input" type="number" step="0.01" />
            </label>
            <label class="field">
              <button data-test="finance-save-cash-flow-opening" class="ghost" type="button" :disabled="ctx.financeCashFlowOpeningSaving" @click="saveFinanceCashFlowOpening">
                {{ ctx.financeCashFlowOpeningSaving ? 'Сохраняем...' : 'Сохранить остаток' }}
              </button>
            </label>
            <label class="field">
              <button data-test="finance-apply-cash-flow" class="ghost" type="button" :disabled="ctx.financeCashFlowLoading" @click="applyFinanceCashFlowReport">Применить</button>
            </label>
          </div>

          <p v-if="ctx.financeError" class="bad">{{ ctx.financeError }}</p>
          <p v-if="ctx.financeCashFlowOpeningOk" class="good">{{ ctx.financeCashFlowOpeningOk }}</p>
          <p v-if="!ctx.financeCashFlowLoaded && !ctx.financeCashFlowLoading" class="muted">Нажмите «Применить», чтобы построить Cash Flow.</p>

          <div v-else-if="ctx.financeCashFlowLoading" class="loader-wrap loader-wrap--compact">
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

          <template v-else>
            <div class="analytics-cards">
              <div class="mini">
                <div class="mini__label">Поступления</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeCashFlowTotals.revenue) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Расходы</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeCashFlowTotals.expense) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Cash Flow</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeCashFlowTotals.cash_flow) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Остаток прошлый</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeCashFlowTotals.opening_balance) }}</div>
                <div class="muted">{{ formatOpeningBalanceHint() }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Остаток текущий</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeCashFlowTotals.current_balance) }}</div>
              </div>
            </div>

            <div class="finance-cash-flow-grid">
              <section class="finance-cash-flow-panel">
                <h4 class="section-title">Поступления</h4>
                <table v-if="ctx.financeCashFlowRevenues.length" class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="line in ctx.financeCashFlowRevenues" :key="`cf-rev-${line.name}`">
                      <td>{{ line.name }}</td>
                      <td>{{ ctx.formatPrice(line.amount) }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Поступлений нет.</p>
              </section>

              <section class="finance-cash-flow-panel">
                <h4 class="section-title">Расходы</h4>
                <table v-if="ctx.financeCashFlowExpenses.length" class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="line in ctx.financeCashFlowExpenses" :key="`cf-exp-${line.name}`">
                      <td>{{ line.name }}</td>
                      <td>{{ ctx.formatPrice(line.amount) }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Расходов нет.</p>
              </section>
            </div>
          </template>
        </template>
      </div>
    </section>

    <teleport to="body">
      <div v-if="ctx.financeSourceDetailsOpen" class="work-page work-modal-root modal-backdrop" @click.self="closeSourceDetails">
        <div class="modal modal--auto finance-details-modal">
          <div class="panel__head panel__head--tight">
            <div>
              <h3>{{ ctx.financeSourceDetailsTitle || 'Расшифровка строки' }}</h3>
              <p class="muted">Период {{ ctx.financeFilters.date_from || '—' }} — {{ ctx.financeFilters.date_to || '—' }}</p>
            </div>
            <button class="ghost ghost--compact" type="button" @click="closeSourceDetails">Закрыть</button>
          </div>
          <div class="modal__body finance-details-modal__body">
            <div v-if="ctx.financeSourceDetailsLoading" class="loader-wrap loader-wrap--compact">
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
            <template v-else>
              <div class="analytics-cards finance-details-cards">
                <div class="mini">
                  <div class="mini__label">Поступления</div>
                  <div class="mini__value">{{ ctx.formatPrice(ctx.financeSourceDetailsTotals.revenue) }}</div>
                </div>
                <div class="mini">
                  <div class="mini__label">Расходы</div>
                  <div class="mini__value">{{ ctx.formatPrice(ctx.financeSourceDetailsTotals.direct_expense) }}</div>
                </div>
                <div class="mini">
                  <div class="mini__label">Итог</div>
                  <div class="mini__value">{{ ctx.formatPrice(ctx.financeSourceDetailsTotals.operating_profit) }}</div>
                </div>
                <div class="mini">
                  <div class="mini__label">Строк</div>
                  <div class="mini__value">{{ Number((ctx.financeSourceDetails || []).length) }}</div>
                </div>
              </div>

              <table v-if="ctx.financeSourceDetails.length" class="table table--compact table--dense finance-details-table">
                <thead>
                  <tr>
                    <th>Основание</th>
                    <th>Клиент / операция</th>
                    <th>Поступления</th>
                    <th>Себестоимость</th>
                    <th>Коэф.</th>
                    <th>Расходы</th>
                    <th>Итог</th>
                    <th>Заказы</th>
                    <th>Почему</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in ctx.financeSourceDetails" :key="`${item.row_type}-${item.deal_id || item.entry_id}`">
                    <td>
                      <div class="finance-detail-main">{{ formatDetailRef(item) }}</div>
                      <div class="muted">{{ item.activity_date }}</div>
                    </td>
                    <td>
                      <div class="finance-detail-main">{{ formatDetailActor(item) }}</div>
                      <div class="muted">{{ item.item_title || '—' }}</div>
                    </td>
                    <td>{{ ctx.formatPrice(item.revenue) }}</td>
                    <td>{{ ctx.formatPrice(item.purchase_cost) }}</td>
                    <td>{{ formatDetailRate(item) }}</td>
                    <td>{{ ctx.formatPrice(item.direct_expense) }}</td>
                    <td>{{ ctx.formatPrice(item.cash_flow) }}</td>
                    <td class="finance-detail-orders">{{ formatDetailOrders(item) }}</td>
                    <td class="finance-detail-reason">{{ item.reason || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Нет строк для расшифровки.</p>
            </template>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="typeModal.open" class="work-page work-modal-root modal-backdrop" @click.self="closeTypeModal">
        <div class="modal modal--auto finance-catalog-modal">
          <div class="panel__head panel__head--tight">
            <h3>{{ typeModal.mode === 'create' ? 'Новый тип операции' : 'Редактировать тип операции' }}</h3>
          </div>
          <div class="modal__body" :class="{ 'modal__body--locked': ctx.financeCatalogSaving }">
            <div v-if="ctx.financeCatalogSaving" class="modal__body-overlay">
              <div class="loader-wrap loader-wrap--compact">
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
                <p class="muted">Сохраняем…</p>
              </div>
            </div>
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Название</span>
                <input v-model="typeDraft.name" class="input" type="text" />
              </label>
            </div>
            <div class="toolbar-actions">
              <button
                v-if="typeModal.mode === 'edit'"
                data-test="finance-delete-type"
                class="ghost"
                type="button"
                :disabled="ctx.financeCatalogSaving"
                @click="deleteTypeFromModal"
              >
                Удалить
              </button>
              <button class="ghost" type="button" @click="closeTypeModal">Отмена</button>
              <button data-test="finance-create-type" class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click="submitTypeModal">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="operationModal.open" class="work-page work-modal-root modal-backdrop" @click.self="closeOperationModal">
        <div class="modal modal--auto finance-catalog-modal">
          <div class="panel__head panel__head--tight">
            <h3>{{ operationModal.mode === 'create' ? 'Новый вид операции' : 'Редактировать вид операции' }}</h3>
          </div>
          <div class="modal__body" :class="{ 'modal__body--locked': ctx.financeCatalogSaving }">
            <div v-if="ctx.financeCatalogSaving" class="modal__body-overlay">
              <div class="loader-wrap loader-wrap--compact">
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
                <p class="muted">Сохраняем…</p>
              </div>
            </div>
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Название</span>
                <input v-model="operationDraft.name" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Тип</span>
                <select v-model="operationDraft.type_id" class="input input--select">
                  <option value="">Выберите</option>
                  <option v-for="type in ctx.financeTypes" :key="`modal-op-type-${type.type_id}`" :value="type.type_id">{{ type.name }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Источник</span>
                <select v-model="operationDraft.source_id" class="input input--select">
                  <option value="">Не выбран</option>
                  <option v-for="source in ctx.financeSources" :key="`modal-op-source-${source.source_id}`" :value="source.source_id">{{ formatSourceLabel(source) }}</option>
                </select>
              </label>
            </div>
            <div class="toolbar-actions">
              <button
                v-if="operationModal.mode === 'edit'"
                data-test="finance-delete-operation"
                class="ghost"
                type="button"
                :disabled="ctx.financeCatalogSaving"
                @click="deleteOperationFromModal"
              >
                Удалить
              </button>
              <button class="ghost" type="button" @click="closeOperationModal">Отмена</button>
              <button data-test="finance-create-operation" class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click="submitOperationModal">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>

  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, unref, watch } from 'vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})

// Держим состояние роутера и вкладок, чтобы стабильно переключаться внутри админ-блока.
const activeTab = computed(() => String(unref(props.ctx.activeTab) || ''))
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
const canViewUsersSection = computed(() => Boolean(unref(props.ctx.canViewUsersSection)))
const canManageRolePermissions = computed(() => Boolean(unref(props.ctx.canManageRolePermissions)))
const canViewAnalyticsSection = computed(() => Boolean(unref(props.ctx.canViewAnalyticsSection)))
const canViewCatalogsSection = computed(() => Boolean(unref(props.ctx.canViewCatalogsSection)))
const canViewFinanceSection = computed(() => Boolean(unref(props.ctx.canViewFinanceSection)))
const showAdminTabs = computed(() => (
  canViewUsersSection.value
  || canManageRolePermissions.value
  || canViewAnalyticsSection.value
  || canViewCatalogsSection.value
  || canViewFinanceSection.value
))

const financeMode = ref('entry')
const journalSectionKind = ref('')
const openFinanceReportFilter = ref('')

const typeModal = reactive({ open: false, mode: 'create', type_id: null })
const operationModal = reactive({ open: false, mode: 'create', operation_id: null })

const typeDraft = reactive({ code: '', name: '' })
const operationDraft = reactive({ type_id: '', source_id: '', code: '', name: '', input_mode: 'mixed' })

// Переключаем вид, чтобы на экране был только один смысловой блок.
function setFinanceMode(mode) {
  financeMode.value = String(mode || 'entry')
}

// Собираем быстрые словари по id/code для отображения журнала ввода.
const operationsMap = computed(() => new Map((unref(props.ctx.financeOperations) || []).map((item) => [Number(item.operation_id), item])))
const typesMap = computed(() => new Map((unref(props.ctx.financeTypes) || []).map((item) => [Number(item.type_id), item])))
const sectionsMap = computed(() => new Map((unref(props.ctx.financeSections) || []).map((item) => [Number(item.section_id), item])))
const regionsMap = computed(() => new Map((unref(props.ctx.financeRegions) || []).map((item) => [Number(item.region_id), item])))
const sourcesMap = computed(() => new Map((unref(props.ctx.financeSources) || []).map((item) => [Number(item.source_id), item])))
const statusesMap = computed(() => new Map((unref(props.ctx.financeStatuses) || []).map((item) => [String(item.code || '').toLowerCase(), item])))

const selectedOperation = computed(() => {
  const opId = Number(unref(props.ctx.financeNewEntry?.operation_id) || 0)
  if (!opId) return null
  return operationsMap.value.get(opId) || null
})

const entryKinds = computed(() => {
  // Показываем в фильтре только те типы, для которых есть хотя бы одна операция.
  const usedTypeIds = new Set()
  for (const op of (unref(props.ctx.financeOperations) || [])) {
    const typeId = resolveOperationTypeId(op)
    if (typeId) usedTypeIds.add(typeId)
  }
  return (unref(props.ctx.financeTypes) || []).filter((type) => usedTypeIds.has(Number(type?.type_id || 0)))
})

const filteredNewEntryOperations = computed(() => {
  // В форме ввода показываем полный список операций.
  return unref(props.ctx.financeOperations) || []
})

const filteredJournalOperations = computed(() => {
  // Для журнала показываем только операции выбранного типа.
  const selectedTypeId = Number(journalSectionKind.value || 0)
  const rows = unref(props.ctx.financeOperations) || []
  if (!selectedTypeId) return rows
  return rows.filter((op) => resolveOperationTypeId(op) === selectedTypeId)
})

watch(
  selectedOperation,
  (nextOp) => {
    // Если операция привязана к источнику, подставляем его в форму ввода.
    if (!nextOp) return
    const sourceId = Number(nextOp?.source_id || 0)
    if (sourceId) props.ctx.financeNewEntry.source_id = sourceId
  },
  { immediate: true },
)

watch(journalSectionKind, (nextKind) => {
  // Если тип журнала сменился, очищаем операцию из другого типа.
  const selectedTypeId = Number(nextKind || 0)
  if (!selectedTypeId) return
  const opId = Number(unref(props.ctx.financeEntryFilters?.operation_id) || 0)
  if (!opId) return
  const current = operationsMap.value.get(opId)
  if (!current) return
  if (resolveOperationTypeId(current) !== selectedTypeId) {
    props.ctx.financeEntryFilters.operation_id = ''
  }
})

watch(
  () => props.ctx.financeEntryFilters?.operation_id,
  (nextOpId) => {
    // Подхватываем тип по выбранной операции, чтобы фильтр "Тип" не расходился с "Операция".
    const opId = Number(nextOpId || 0)
    if (!opId) return
    const operation = operationsMap.value.get(opId)
    if (!operation) return
    const typeId = resolveOperationTypeId(operation)
    if (typeId) {
      journalSectionKind.value = String(typeId)
    }
  },
  { immediate: true },
)

// Определяем type_id операции: в новом контракте берем напрямую, в старом fallback через section.
function resolveOperationTypeId(operation) {
  if (!operation) return ''
  const typeId = Number(operation?.type_id || 0)
  if (typeId) return typeId
  const section = sectionsMap.value.get(Number(operation?.section_id || 0))
  return Number(section?.type_id || 0)
}

// Возвращаем читаемое имя по id, чтобы в таблице не показывать только числа.
function resolveOptionName(collection, id, valueField = 'name') {
  if (id === null || id === undefined || id === '') return '—'
  const normalizedId = Number(id)
  const row = collection.value.get(normalizedId)
  if (!row) return `#${id}`
  return String(row[valueField] || row.code || id)
}

// Преобразуем id операции в название для журнала.
function resolveOperationName(operationId) {
  return resolveOptionName(operationsMap, operationId)
}

// Преобразуем id региона в название для журнала.
function resolveRegionName(regionId) {
  return resolveOptionName(regionsMap, regionId)
}

// Преобразуем id источника в название для журнала.
function resolveSourceName(sourceId) {
  if (sourceId === null || sourceId === undefined || sourceId === '') return '—'
  const normalizedId = Number(sourceId)
  const source = sourcesMap.value.get(normalizedId)
  if (!source) return `#${sourceId}`
  return formatSourceLabel(source)
}

// Формируем подпись источника в едином формате "Название - Код".
function formatSourceLabel(source) {
  const sourceName = String(source?.name || '').trim()
  const sourceCode = String(source?.code || '').trim()
  if (sourceName && sourceCode) return `${sourceName} - ${sourceCode}`
  if (sourceName) return sourceName
  if (sourceCode) return sourceCode
  return '—'
}

// Получаем выбранные id фильтра отчета в виде числового списка.
function getFinanceFilterIds(key) {
  const value = props.ctx.financeFilters?.[key]
  return (Array.isArray(value) ? value : (value ? [value] : []))
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item > 0)
}

// Пустой список означает режим "Все", чтобы запрос не ограничивался фильтром.
function isFinanceFilterAll(key) {
  return getFinanceFilterIds(key).length === 0
}

// Проверяем отдельный чекбокс в мультифильтре отчета.
function isFinanceFilterSelected(key, id) {
  return getFinanceFilterIds(key).includes(Number(id))
}

// Включает "Все" через очистку выбранных значений.
function setFinanceFilterAll(key) {
  if (!props.ctx.financeFilters) return
  props.ctx.financeFilters[key] = []
}

// Добавляет или убирает отдельный id из фильтра отчета.
function toggleFinanceFilterId(key, id, checked) {
  if (!props.ctx.financeFilters) return
  const numericId = Number(id)
  if (!Number.isFinite(numericId) || numericId <= 0) return
  const current = new Set(getFinanceFilterIds(key))
  if (checked) {
    current.add(numericId)
  } else {
    current.delete(numericId)
  }
  props.ctx.financeFilters[key] = Array.from(current)
}

// Формирует короткую подпись закрытого dropdown-фильтра.
function formatFinanceFilterSummary(key, options, labelMode = 'name') {
  const ids = getFinanceFilterIds(key)
  if (!ids.length) return 'Все'
  if (ids.length === 1) {
    const selected = (options || []).find((item) => Number(item?.region_id || item?.source_id || 0) === ids[0])
    if (selected && labelMode === 'source') return formatSourceLabel(selected)
    if (selected) return String(selected?.name || selected?.code || `#${ids[0]}`)
  }
  return `${ids.length} выбрано`
}

// Открывает один dropdown фильтра и закрывает второй, чтобы панели не накладывались.
function toggleFinanceReportFilter(key) {
  openFinanceReportFilter.value = openFinanceReportFilter.value === key ? '' : key
}

// Закрывает dropdown только при клике снаружи, чтобы checkbox внутри не сбрасывал фокус в Windows-браузерах.
function closeFinanceFilterOnOutsidePointer(event) {
  const target = event.target
  const element = target instanceof Element ? target : target?.parentElement
  if (element?.closest?.('.finance-multi-filter')) return
  openFinanceReportFilter.value = ''
}

onMounted(() => {
  document.addEventListener('pointerdown', closeFinanceFilterOnOutsidePointer, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeFinanceFilterOnOutsidePointer, true)
})

// Показываем бизнес-название строки: источник для маркетов, тип сделки для строк без источника.
function formatSourceReportLabel(row) {
  const sourceName = String(row?.source_name || '').trim()
  const sourceCode = String(row?.source_code || '').trim()
  const hasRealSource = Boolean(row?.source_id || sourceCode || (sourceName && sourceName !== 'Без источника'))
  if (!hasRealSource) {
    return row?.region_code ? 'Услуга' : 'Шеринг'
  }
  return formatSourceLabel({ name: row?.source_name, code: row?.source_code })
}

// Показываем в отчете только код региона, чтобы строка была компактной.
function formatRegionReportLabel(row) {
  const regionCode = String(row?.region_code || '').trim()
  if (regionCode) return regionCode
  return '—'
}

// Cash Flow в новом отчете равен поступлениям минус расходы.
function resolveReportCashFlow(row) {
  const explicit = Number(row?.cash_flow)
  if (Number.isFinite(explicit)) return explicit
  return Number(row?.operating_profit || 0)
}

// Открываем расшифровку строки отчета с теми же датами и точными измерениями.
async function openSourceDetails(row) {
  const title = `${formatSourceReportLabel(row)} / ${formatRegionReportLabel(row)}`
  await props.ctx.loadFinanceSourceDetails?.(row, title)
}

// Закрываем модалку деталей и очищаем выбранную строку отчета.
function closeSourceDetails() {
  props.ctx.clearFinanceSourceDetails?.()
}

// Формируем короткую ссылку-основание для строки расшифровки.
function formatDetailRef(item) {
  const dealId = Number(item?.deal_id || 0)
  if (dealId) return `Сделка #${dealId}`
  const entryId = Number(item?.entry_id || 0)
  if (entryId) return `Проводка #${entryId}`
  return '—'
}

// Показываем клиента для сделки или операцию для finance-проводки.
function formatDetailActor(item) {
  const customer = String(item?.customer_name || '').trim()
  if (customer) return customer
  const operation = String(item?.operation_name || '').trim()
  if (operation) return operation
  return '—'
}

// Коэффициент есть только у продаж по региону; для остальных строк оставляем прочерк.
function formatDetailRate(item) {
  const rate = Number(item?.purchase_cost_rate)
  if (!Number.isFinite(rate) || rate <= 0) return '—'
  return String(rate).replace('.', ',')
}

// Для Yandex API-проводок показываем, из каких заказов собран дневной итог.
function formatDetailOrders(item) {
  const ids = Array.isArray(item?.order_ids) ? item.order_ids.filter(Boolean).map((value) => String(value)) : []
  if (!ids.length) return '—'
  const visible = ids.slice(0, 6).join(', ')
  const rest = ids.length - 6
  const count = Number(item?.orders_count || ids.length)
  const suffix = rest > 0 ? `, еще ${rest}` : ''
  return `${visible}${suffix} · заказов ${count}`
}

// Объясняем, откуда взялся начальный остаток месяца.
function formatOpeningBalanceHint() {
  const totals = props.ctx.financeCashFlowTotals || {}
  if (totals.opening_balance_manual) return 'ручной остаток месяца'
  if (totals.opening_balance_month) return `расчет от ${String(totals.opening_balance_month).slice(0, 7)}`
  return 'ручной остаток не задан'
}

// Возвращаем название типа для раздела по type_id или fallback из строки.
function resolveTypeName(typeId, fallbackName = '') {
  const normalizedId = Number(typeId || 0)
  if (normalizedId) {
    const row = typesMap.value.get(normalizedId)
    if (row?.name) return String(row.name)
  }
  return String(fallbackName || '—')
}

// Проставляем ошибку каталога как в ref, так и в обычное поле (для тестовых моков).
function setFinanceCatalogError(message) {
  const holder = props.ctx.financeCatalogError
  if (holder && typeof holder === 'object' && 'value' in holder) {
    holder.value = String(message || '')
  }
}

// Показываем тип операции по прямой связи с type_id; для старых данных есть fallback через section.
function resolveOperationTypeName(operation) {
  const typeId = Number(operation?.type_id || 0)
  if (typeId) return resolveTypeName(typeId)
  const section = sectionsMap.value.get(Number(operation?.section_id || 0))
  if (!section) return '—'
  return resolveTypeName(section.type_id, section.type_name || section.type_code || section.kind || '—')
}

// Транслитерируем кириллицу в латиницу для автоматической генерации code.
function transliterateToLatin(value) {
  const map = {
    а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z', и: 'i', й: 'y',
    к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f',
    х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'sch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
  }
  return String(value || '')
    .toLowerCase()
    .split('')
    .map((char) => map[char] ?? char)
    .join('')
}

// Нормализуем название в snake_case код для API.
function normalizeToCode(value, fallbackPrefix = 'item') {
  const latin = transliterateToLatin(value)
  const normalized = latin
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .replace(/_+/g, '_')
  return normalized || fallbackPrefix
}

// Подбираем уникальный код, чтобы не конфликтовать с уже существующими записями.
function buildUniqueCode(baseCode, usedCodes) {
  const used = new Set((usedCodes || []).map((code) => String(code || '').toLowerCase()).filter(Boolean))
  let nextCode = String(baseCode || '').toLowerCase()
  let counter = 2
  while (used.has(nextCode)) {
    nextCode = `${baseCode}_${counter}`
    counter += 1
  }
  return nextCode
}

// Преобразуем код статуса в человекочитаемый текст для журнала.
function resolveStatusName(statusCode) {
  const code = String(statusCode || '').toLowerCase()
  if (!code) return '—'
  const row = statusesMap.value.get(code)
  return row?.name || code
}

// Готовим форму типа для создания.
function openTypeCreateModal() {
  typeModal.open = true
  typeModal.mode = 'create'
  typeModal.type_id = null
  typeDraft.code = ''
  typeDraft.name = ''
}

// Открываем редактирование типа из строки таблицы.
function openTypeEditModal(type) {
  typeModal.open = true
  typeModal.mode = 'edit'
  typeModal.type_id = Number(type?.type_id || 0)
  typeDraft.code = String(type?.code || '')
  typeDraft.name = String(type?.name || '')
}

// Закрываем модалку типа без сохранения.
function closeTypeModal() {
  typeModal.open = false
}

// Удаляем тип из модалки редактирования после подтверждения пользователя.
async function deleteTypeFromModal() {
  const typeId = Number(typeModal.type_id || 0)
  if (!typeId) return
  if (!window.confirm('Удалить тип операции?')) return
  let ok = await props.ctx.archiveFinanceType?.(typeId)
  const typeDeleteError = String(unref(props.ctx.financeCatalogError) || '')
  if (!ok && (
    typeDeleteError.includes('Нельзя удалить тип: к нему привязаны виды операций')
    || typeDeleteError.includes('Нельзя удалить тип: к нему привязаны разделы')
    || typeDeleteError.includes('Type has operations and cannot be deleted')
    || typeDeleteError.includes('Type has active sections')
  )) {
    if (!window.confirm('У типа есть связанные виды/разделы и, возможно, проводки. Удалить тип вместе с ними?')) return
    ok = await props.ctx.archiveFinanceType?.(typeId, { cascadeEntries: true })
  }
  if (ok) closeTypeModal()
}

// Сохраняем тип: создаем новый или обновляем существующий.
async function submitTypeModal() {
  // Для нового типа автоматически генерируем code из названия и делаем его уникальным.
  const typeName = String(typeDraft.name || '').trim()
  const generatedCode = normalizeToCode(typeName, 'type')
  const nextCode = typeModal.mode === 'create'
    ? buildUniqueCode(generatedCode, (unref(props.ctx.financeTypes) || []).map((item) => item.code))
    : String(typeDraft.code || '').trim().toLowerCase()
  const payload = {
    code: nextCode,
    name: typeName,
  }
  const ok = typeModal.mode === 'create'
    ? await props.ctx.createFinanceType?.(payload)
    : await props.ctx.updateFinanceType?.(typeModal.type_id, payload)
  if (ok) closeTypeModal()
}

// Готовим форму операции для создания.
function openOperationCreateModal() {
  operationModal.open = true
  operationModal.mode = 'create'
  operationModal.operation_id = null
  operationDraft.type_id = Number((unref(props.ctx.financeTypes) || [])[0]?.type_id || '') || ''
  operationDraft.source_id = ''
  operationDraft.code = ''
  operationDraft.name = ''
  operationDraft.input_mode = 'mixed'
}

// Открываем редактирование операции из строки таблицы.
function openOperationEditModal(operation) {
  operationModal.open = true
  operationModal.mode = 'edit'
  operationModal.operation_id = Number(operation?.operation_id || 0)
  operationDraft.type_id = Number(operation?.type_id || '') || ''
  if (!operationDraft.type_id) {
    const section = sectionsMap.value.get(Number(operation?.section_id || 0))
    operationDraft.type_id = Number(section?.type_id || '') || ''
  }
  operationDraft.source_id = Number(operation?.source_id || '') || ''
  operationDraft.code = String(operation?.code || '')
  operationDraft.name = String(operation?.name || '')
  operationDraft.input_mode = String(operation?.input_mode || 'mixed')
}

// Закрываем модалку операции без сохранения.
function closeOperationModal() {
  operationModal.open = false
}

// Удаляем вид операции из модалки редактирования после подтверждения пользователя.
async function deleteOperationFromModal() {
  const operationId = Number(operationModal.operation_id || 0)
  if (!operationId) return
  if (!window.confirm('Удалить вид операции?')) return
  let ok = await props.ctx.archiveFinanceOperation?.(operationId)
  if (!ok && String(unref(props.ctx.financeCatalogError) || '').includes('Нельзя удалить вид операции: по нему уже есть записи')) {
    if (!window.confirm('По операции есть проводки. Удалить вид операции вместе с проводками?')) return
    ok = await props.ctx.archiveFinanceOperation?.(operationId, { cascadeEntries: true })
  }
  if (ok) closeOperationModal()
}

// Сохраняем операцию: создаем новую или обновляем существующую.
async function submitOperationModal() {
  const resolvedTypeId = Number(operationDraft.type_id || 0)
  if (!resolvedTypeId) {
    setFinanceCatalogError('Выберите тип для операции.')
    return
  }
  // Для нового вида операции автоматически генерируем code из названия и делаем его уникальным.
  const operationName = String(operationDraft.name || '').trim()
  const generatedCode = normalizeToCode(operationName, 'operation')
  const nextCode = operationModal.mode === 'create'
    ? buildUniqueCode(generatedCode, (unref(props.ctx.financeOperations) || []).map((item) => item.code))
    : String(operationDraft.code || '').trim().toLowerCase()
  const payload = {
    type_id: resolvedTypeId,
    source_id: operationDraft.source_id ? Number(operationDraft.source_id) : null,
    code: nextCode,
    name: operationName,
    input_mode: operationDraft.input_mode,
    requires_region: false,
    requires_source: false,
    requires_project: false,
    requires_qty: false,
    allows_negative: false,
  }
  const ok = operationModal.mode === 'create'
    ? await props.ctx.createFinanceOperation?.(payload)
    : await props.ctx.updateFinanceOperation?.(operationModal.operation_id, payload)
  if (ok) closeOperationModal()
}

// Запускаем сохранение новой записи через composable.
async function submitFinanceEntry() {
  // Регион в упрощенной форме не используется; источник берем из операции, если он задан.
  props.ctx.financeNewEntry.region_id = ''
  const currentOperation = operationsMap.value.get(Number(props.ctx.financeNewEntry.operation_id || 0))
  props.ctx.financeNewEntry.source_id = Number(currentOperation?.source_id || 0) || ''
  await props.ctx.createFinanceEntry?.()
}

// Перезагружаем журнал для выбранных фильтров.
async function reloadFinanceEntries() {
  await props.ctx.loadFinanceEntries?.()
}

// Удаляем проводку из журнала после подтверждения пользователя.
async function deleteFinanceEntryRow(entry) {
  const entryId = Number(entry?.entry_id || 0)
  if (!entryId) return
  if (!window.confirm(`Удалить проводку #${entryId}?`)) return
  await props.ctx.deleteFinanceEntry?.(entryId)
}

// Строим отчет по текущим фильтрам.
async function applyFinanceReport() {
  await props.ctx.loadFinanceProjectsReport?.()
}

// Строим общий Cash Flow по текущим фильтрам.
async function applyFinanceCashFlowReport() {
  await props.ctx.loadFinanceCashFlowReport?.()
}

// Сохраняем начальный остаток выбранного месяца.
async function saveFinanceCashFlowOpening() {
  await props.ctx.saveFinanceCashFlowOpeningBalance?.()
}

// Запускаем ручной импорт Яндекс Маркета через backend endpoint.
async function syncYandexMarket() {
  await props.ctx.syncFinanceYandexMarket?.()
}

// Перечитываем каталоги типов и видов операций по кнопке "Обновить".
async function reloadFinanceCatalogs() {
  await props.ctx.loadFinanceBootstrap?.()
}
</script>

<style scoped>
.finance-catalog-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
}

.finance-catalog-panel {
  min-width: 0;
}

.finance-cash-flow-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
  margin-top: 18px;
}

.finance-cash-flow-panel {
  min-width: 0;
}

.finance-multi-filter {
  position: relative;
}

.finance-multi-filter__summary {
  display: flex;
  align-items: center;
  cursor: pointer;
  list-style: none;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.finance-multi-filter__summary::-webkit-details-marker {
  display: none;
}

.finance-multi-filter__summary::after {
  content: '';
  width: 8px;
  height: 8px;
  margin-left: auto;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  opacity: 0.75;
}

.finance-multi-filter__summary[aria-expanded='true']::after {
  transform: rotate(225deg);
}

.check-list--finance-report {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  z-index: 30;
  max-height: 220px;
  border-color: var(--input-border);
  background: #101827 !important;
  background-color: #101827 !important;
  opacity: 1;
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.35);
}

.finance-integration-panel {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.finance-integration-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.finance-integration-badge {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.2;
}

.finance-sync-cards {
  margin-top: 2px;
}

.ghost--compact {
  min-height: 34px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.table__actions {
  width: 1%;
  white-space: nowrap;
}

.finance-details-modal.modal {
  width: min(1180px, calc(100vw - 32px)) !important;
  max-width: min(1180px, calc(100vw - 32px)) !important;
}

.finance-details-modal .panel__head {
  align-items: flex-start;
}

.finance-details-modal__body {
  display: grid;
  gap: 14px;
  align-items: stretch;
  overflow-x: auto;
}

.finance-details-cards {
  min-width: 760px;
}

.finance-details-table {
  min-width: 1040px;
}

.finance-detail-main {
  font-weight: 800;
  color: var(--text);
}

.finance-detail-reason {
  max-width: 220px;
  color: var(--muted);
}

.finance-detail-orders {
  max-width: 260px;
  color: var(--text);
}

.finance-catalog-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.finance-catalog-panel__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.finance-catalog-modal.modal {
  width: min(520px, calc(100vw - 32px)) !important;
  max-width: min(520px, calc(100vw - 32px)) !important;
}

.finance-catalog-modal .modal__body {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding-top: 14px;
  padding-bottom: 16px;
}

.finance-catalog-modal .analytics-filters {
  align-self: stretch;
  max-width: none;
  width: 100%;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.finance-catalog-modal .field,
.finance-catalog-modal .input,
.finance-catalog-modal .input--select {
  align-self: stretch;
  max-width: none;
  width: 100%;
}

.finance-action-btn {
  min-width: 138px;
}

.finance-action-btn--refresh .deal-create-btn__icon {
  background: linear-gradient(135deg, #4b8ec6, #6cb6e6);
}

.finance-entry-wrap {
  position: relative;
}

.finance-entry-wrap--locked {
  pointer-events: none;
}

.finance-entry-wrap__overlay {
  position: absolute;
  inset: 0;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(5, 10, 26, 0.5);
}

@media (max-width: 1100px) {
  .finance-catalog-grid,
  .finance-cash-flow-grid {
    grid-template-columns: 1fr;
  }

  .finance-catalog-panel__head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
