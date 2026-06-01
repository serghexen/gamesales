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
          <button data-test="finance-mode-report" class="tab" :class="{ active: financeMode === 'report' }" type="button" @click="setFinanceMode('report')">
            Отчет
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
                    <tr v-for="type in ctx.financeTypes" :key="type.type_id" class="clickable-row" @click="openTypeEditModal(type)">
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
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="operation in ctx.financeOperations" :key="operation.operation_id" class="clickable-row" @click="openOperationEditModal(operation)">
                      <td>{{ operation.name }}</td>
                      <td>{{ resolveOperationTypeName(operation) }}</td>
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
                <span class="label">Тип</span>
                <select v-model="entrySectionKind" class="input input--select">
                  <option value="">Все типы</option>
                  <option v-for="type in entryKinds" :key="`entry-type-${type.type_id}`" :value="String(type.type_id)">{{ type.name }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Операция</span>
                <select v-model="ctx.financeNewEntry.operation_id" class="input input--select">
                  <option value="">Выберите</option>
                  <option v-for="op in filteredNewEntryOperations" :key="op.operation_id" :value="op.operation_id">{{ op.name }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Регион</span>
                <select v-model="ctx.financeNewEntry.region_id" class="input input--select">
                  <option value="">Не выбран</option>
                  <option v-for="r in ctx.financeRegions" :key="r.region_id" :value="r.region_id">{{ r.name }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Источник</span>
                <select v-model="ctx.financeNewEntry.source_id" class="input input--select">
                  <option value="">Не выбран</option>
                  <option v-for="s in ctx.financeSources" :key="s.source_id" :value="s.source_id">{{ s.name }}</option>
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

            <p v-if="selectedOperation" class="muted">Тип: {{ selectedKindLabel }}.</p>
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
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Журнал пуст.</p>
          </template>
          <p class="muted">Всего записей по фильтру: {{ ctx.financeEntriesTotal }}</p>
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
            <label class="field">
              <span class="label">Регион</span>
              <select v-model.number="ctx.financeFilters.region_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="r in ctx.financeRegions" :key="`rep-rg-${r.region_id}`" :value="r.region_id">{{ r.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Источник</span>
              <select v-model.number="ctx.financeFilters.source_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="s in ctx.financeSources" :key="`rep-src-${s.source_id}`" :value="s.source_id">{{ s.name }}</option>
              </select>
            </label>
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
                <div class="mini__label">Выручка</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.revenue) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Прямые</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.direct_expense) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Косвенные</div>
                <div class="mini__value">{{ ctx.formatPrice(ctx.financeReportTotals.indirect_expense) }}</div>
              </div>
              <div class="mini">
                <div class="mini__label">Опер. прибыль</div>
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
                  <th v-if="ctx.financeFilters.split_by_source">Источник</th>
                  <th>Выручка</th>
                  <th>Прямые</th>
                  <th>Косвенные</th>
                  <th>Опер. прибыль</th>
                  <th>Маржа</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in ctx.financeReportItems" :key="`${row.project_code}-${row.source_id || 'all'}`">
                  <td v-if="ctx.financeFilters.split_by_source">{{ row.source_name || '—' }}</td>
                  <td>{{ ctx.formatPrice(row.revenue) }}</td>
                  <td>{{ ctx.formatPrice(row.direct_expense) }}</td>
                  <td>{{ ctx.formatPrice(row.indirect_expense) }}</td>
                  <td>{{ ctx.formatPrice(row.operating_profit) }}</td>
                  <td>{{ ctx.formatPercent(row.margin) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Нет данных по выбранным фильтрам.</p>
          </template>
        </template>
      </div>
    </section>

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
            </div>
            <div class="toolbar-actions">
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
import { computed, reactive, ref, unref, watch } from 'vue'

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
const entrySectionKind = ref('')
const journalSectionKind = ref('')

const typeModal = reactive({ open: false, mode: 'create', type_id: null })
const operationModal = reactive({ open: false, mode: 'create', operation_id: null })

const typeDraft = reactive({ code: '', name: '' })
const operationDraft = reactive({ type_id: '', code: '', name: '', input_mode: 'mixed' })

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
  // Фильтруем список статей по выбранному типу расхода/выручки.
  const selectedTypeId = Number(entrySectionKind.value || 0)
  const rows = unref(props.ctx.financeOperations) || []
  if (!selectedTypeId) return rows
  return rows.filter((op) => resolveOperationTypeId(op) === selectedTypeId)
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
    // Синхронизируем выбранный тип по операции, чтобы форма не расходилась по смыслу.
    if (!nextOp) return
    const typeId = resolveOperationTypeId(nextOp)
    if (typeId) entrySectionKind.value = String(typeId)
  },
  { immediate: true },
)

watch(entrySectionKind, (nextKind) => {
  // Если пользователь сменил тип, сбрасываем статью из другого типа.
  const selectedTypeId = Number(nextKind || 0)
  if (!selectedTypeId) return
  const opId = Number(unref(props.ctx.financeNewEntry?.operation_id) || 0)
  if (!opId) return
  const current = operationsMap.value.get(opId)
  if (!current) return
  if (resolveOperationTypeId(current) !== selectedTypeId) {
    props.ctx.financeNewEntry.operation_id = ''
  }
})

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

const selectedKindLabel = computed(() => {
  const typeId = Number(entrySectionKind.value || 0)
  if (!typeId) return 'Не выбран'
  return resolveTypeName(typeId)
})

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
  return resolveOptionName(sourcesMap, sourceId)
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
  operationDraft.code = String(operation?.code || '')
  operationDraft.name = String(operation?.name || '')
  operationDraft.input_mode = String(operation?.input_mode || 'mixed')
}

// Закрываем модалку операции без сохранения.
function closeOperationModal() {
  operationModal.open = false
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
  await props.ctx.createFinanceEntry?.()
}

// Перезагружаем журнал для выбранных фильтров.
async function reloadFinanceEntries() {
  await props.ctx.loadFinanceEntries?.()
}

// Строим отчет по текущим фильтрам.
async function applyFinanceReport() {
  await props.ctx.loadFinanceProjectsReport?.()
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
  .finance-catalog-grid {
    grid-template-columns: 1fr;
  }

  .finance-catalog-panel__head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
