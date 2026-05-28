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
        <div>
          <h2>Финансы</h2>
          <p class="muted">Операции, журнал ввода и отчет по проектам (управленческий P&amp;L).</p>
        </div>
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
          <h3 class="section-title">Настройка справочников</h3>
          <p class="muted">Список и управление разделами, операциями и проектами.</p>
          <p v-if="ctx.financeCatalogError" class="bad">{{ ctx.financeCatalogError }}</p>
          <p v-if="ctx.financeCatalogOk" class="good">{{ ctx.financeCatalogOk }}</p>

          <template v-if="canManageRolePermissions">
            <div class="analytics-cards">
              <div class="mini">
                <div class="mini__label">Типы</div>
                <div class="mini__value">{{ ctx.financeTypes.length }}</div>
                <button data-test="finance-open-create-type" class="ghost" type="button" @click="openTypeCreateModal">Добавить</button>
              </div>
              <div class="mini">
                <div class="mini__label">Разделы</div>
                <div class="mini__value">{{ ctx.financeSections.length }}</div>
                <button data-test="finance-open-create-section" class="ghost" type="button" @click="openSectionCreateModal">Добавить</button>
              </div>
              <div class="mini">
                <div class="mini__label">Операции</div>
                <div class="mini__value">{{ ctx.financeOperations.length }}</div>
                <button data-test="finance-open-create-operation" class="ghost" type="button" @click="openOperationCreateModal">Добавить</button>
              </div>
              <div class="mini">
                <div class="mini__label">Проекты</div>
                <div class="mini__value">{{ ctx.financeProjects.length }}</div>
                <button data-test="finance-open-create-project" class="ghost" type="button" @click="openProjectCreateModal">Добавить</button>
              </div>
            </div>

            <h4 class="section-title">Типы</h4>
            <table v-if="ctx.financeTypes.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="type in ctx.financeTypes" :key="type.type_id" class="clickable-row" @click="openTypeEditModal(type)">
                  <td>{{ type.code }}</td>
                  <td>{{ type.name }}</td>
                  <td>
                    <button class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click.stop="archiveType(type.type_id)">Архив</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Типы не добавлены.</p>

            <h4 class="section-title">Разделы</h4>
            <table v-if="ctx.financeSections.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Тип</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="section in ctx.financeSections" :key="section.section_id" class="clickable-row" @click="openSectionEditModal(section)">
                  <td>{{ section.code }}</td>
                  <td>{{ section.name }}</td>
                  <td>{{ resolveTypeName(section.type_id, section.type_name) }}</td>
                  <td>
                    <button class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click.stop="archiveSection(section.section_id)">Архив</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Разделы не добавлены.</p>

            <h4 class="section-title">Операции</h4>
            <table v-if="ctx.financeOperations.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Раздел</th>
                  <th>Правила</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="operation in ctx.financeOperations" :key="operation.operation_id" class="clickable-row" @click="openOperationEditModal(operation)">
                  <td>{{ operation.code }}</td>
                  <td>{{ operation.name }}</td>
                  <td>{{ resolveSectionName(operation.section_id) }}</td>
                  <td>{{ getOperationRuleSummary(operation) }}</td>
                  <td>
                    <button class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click.stop="archiveOperation(operation.operation_id)">Архив</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Операции не добавлены.</p>

            <h4 class="section-title">Проекты</h4>
            <table v-if="ctx.financeProjects.length" class="table table--compact table--dense">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="project in ctx.financeProjects" :key="project.project_id" class="clickable-row" @click="openProjectEditModal(project)">
                  <td>{{ project.code }}</td>
                  <td>{{ project.name }}</td>
                  <td>
                    <button class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click.stop="archiveProject(project.project_id)">Архив</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Проекты не добавлены.</p>
          </template>
          <p v-else class="muted">Редактирование finance-справочников доступно только роли с правами управления доступами.</p>
        </template>

        <template v-if="financeMode === 'entry'">
          <h3 class="section-title">Ввод операции</h3>
          <div class="analytics-filters">
            <label class="field">
              <span class="label">Дата</span>
              <input v-model="ctx.financeNewEntry.biz_date" class="input" type="date" :max="ctx.maxDate" />
            </label>
            <label class="field">
              <span class="label">Тип</span>
              <select v-model="entrySectionKind" class="input input--select">
                <option value="">Все типы</option>
                <option v-for="kind in entryKinds" :key="kind" :value="kind">{{ sectionKindLabels[kind] || kind }}</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Операция</span>
              <select v-model="ctx.financeNewEntry.operation_id" class="input input--select">
                <option value="">Выберите</option>
                <option v-for="op in filteredNewEntryOperations" :key="op.operation_id" :value="op.operation_id">{{ op.name }} ({{ op.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Проект</span>
              <select v-model="ctx.financeNewEntry.project_id" class="input input--select">
                <option value="">Не выбран</option>
                <option v-for="p in ctx.financeProjects" :key="p.project_id" :value="p.project_id">{{ p.name }} ({{ p.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Регион</span>
              <select v-model="ctx.financeNewEntry.region_id" class="input input--select">
                <option value="">Не выбран</option>
                <option v-for="r in ctx.financeRegions" :key="r.region_id" :value="r.region_id">{{ r.name }} ({{ r.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Источник</span>
              <select v-model="ctx.financeNewEntry.source_id" class="input input--select">
                <option value="">Не выбран</option>
                <option v-for="s in ctx.financeSources" :key="s.source_id" :value="s.source_id">{{ s.name }} ({{ s.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Количество</span>
              <input v-model="ctx.financeNewEntry.qty" class="input" type="number" min="-999999" step="0.0001" />
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

          <p v-if="selectedOperation" class="muted">Тип: {{ selectedKindLabel }}. Требования операции: {{ operationRequirementsLabel }}</p>
          <div class="analytics-head__actions finance-actions-row">
            <button data-test="finance-save-entry" class="ghost" type="button" :disabled="ctx.financeEntrySaving" @click="submitFinanceEntry">
              {{ ctx.financeEntrySaving ? 'Сохраняем...' : 'Добавить запись' }}
            </button>
          </div>
          <p v-if="ctx.financeEntryError" class="bad">{{ ctx.financeEntryError }}</p>
          <p v-if="ctx.financeEntryOk" class="good">{{ ctx.financeEntryOk }}</p>
        </template>

        <template v-if="financeMode === 'journal'">
          <h3 class="section-title">Журнал ввода</h3>
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
              <span class="label">Операция</span>
              <select v-model="ctx.financeEntryFilters.operation_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="op in ctx.financeOperations" :key="`flt-op-${op.operation_id}`" :value="op.operation_id">{{ op.name }} ({{ op.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Статус</span>
              <select v-model="ctx.financeEntryFilters.status_code" class="input input--select">
                <option value="">Все</option>
                <option v-for="status in ctx.financeStatuses" :key="status.code" :value="status.code">{{ status.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Лимит</span>
              <select v-model.number="ctx.financeEntryFilters.limit" class="input input--select">
                <option :value="25">25</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
                <option :value="200">200</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Применить</span>
              <button data-test="finance-apply-entries-filters" class="ghost" type="button" :disabled="ctx.financeEntriesLoading" @click="reloadFinanceEntries">Обновить</button>
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
                  <th>Проект</th>
                  <th>Регион</th>
                  <th>Источник</th>
                  <th>Кол-во</th>
                  <th>Сумма</th>
                  <th>Статус</th>
                  <th>Кто внес</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in ctx.financeEntries" :key="entry.entry_id">
                  <td>{{ entry.biz_date }}</td>
                  <td>{{ resolveOperationName(entry.operation_id) }}</td>
                  <td>{{ resolveProjectName(entry.project_id) }}</td>
                  <td>{{ resolveRegionName(entry.region_id) }}</td>
                  <td>{{ resolveSourceName(entry.source_id) }}</td>
                  <td>{{ entry.qty }}</td>
                  <td>{{ ctx.formatPrice(entry.amount) }}</td>
                  <td>{{ resolveStatusName(entry.status_code) }}</td>
                  <td>{{ entry.created_by || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Журнал пуст.</p>
          </template>
          <p class="muted">Всего записей по фильтру: {{ ctx.financeEntriesTotal }}</p>
        </template>

        <template v-if="financeMode === 'report'">
          <div class="panel__head analytics-head">
            <div>
              <h3 class="section-title">Отчет по проектам</h3>
            </div>
            <div class="analytics-head__actions">
              <button data-test="finance-apply-report" class="ghost" type="button" :disabled="ctx.financeLoading" @click="applyFinanceReport">Применить</button>
              <button class="catalog-refresh-btn" type="button" :disabled="ctx.financeLoading" aria-label="Обновить" title="Обновить" @click="applyFinanceReport">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>

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
              <span class="label">Проект</span>
              <select v-model.number="ctx.financeFilters.project_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="p in ctx.financeProjects" :key="`rep-pr-${p.project_id}`" :value="p.project_id">{{ p.name }} ({{ p.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Регион</span>
              <select v-model.number="ctx.financeFilters.region_id" class="input input--select">
                <option value="">Все</option>
                <option v-for="r in ctx.financeRegions" :key="`rep-rg-${r.region_id}`" :value="r.region_id">{{ r.name }} ({{ r.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Источник</span>
              <select v-model.number="ctx.financeFilters.source_id" class="input input--select" :disabled="!ctx.financeFilters.split_by_source">
                <option value="">Все</option>
                <option v-for="s in ctx.financeSources" :key="`rep-src-${s.source_id}`" :value="s.source_id">{{ s.name }} ({{ s.code }})</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Разрез</span>
              <label class="check-item">
                <input v-model="ctx.financeFilters.split_by_source" type="checkbox" />
                <span>Каждый источник</span>
              </label>
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
                  <th>Проект</th>
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
                  <td>{{ row.project_name }}</td>
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
        <div class="modal modal--auto">
          <div class="panel__head panel__head--tight">
            <h3>{{ typeModal.mode === 'create' ? 'Новый тип' : 'Редактировать тип' }}</h3>
          </div>
          <div class="modal__body">
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Код</span>
                <input v-model="typeDraft.code" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Название</span>
                <input v-model="typeDraft.name" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Сортировка</span>
                <input v-model.number="typeDraft.sort_order" class="input" type="number" />
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
      <div v-if="sectionModal.open" class="work-page work-modal-root modal-backdrop" @click.self="closeSectionModal">
        <div class="modal modal--auto">
          <div class="panel__head panel__head--tight">
            <h3>{{ sectionModal.mode === 'create' ? 'Новый раздел' : 'Редактировать раздел' }}</h3>
          </div>
          <div class="modal__body">
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Код</span>
                <input v-model="sectionDraft.code" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Название</span>
                <input v-model="sectionDraft.name" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Тип</span>
                <select v-model="sectionDraft.type_id" class="input input--select">
                  <option value="">Выберите</option>
                  <option v-for="type in ctx.financeTypes" :key="`type-${type.type_id}`" :value="type.type_id">{{ type.name }} ({{ type.code }})</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Сортировка</span>
                <input v-model.number="sectionDraft.sort_order" class="input" type="number" />
              </label>
            </div>
            <div class="toolbar-actions">
              <button class="ghost" type="button" @click="closeSectionModal">Отмена</button>
              <button data-test="finance-create-section" class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click="submitSectionModal">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="operationModal.open" class="work-page work-modal-root modal-backdrop" @click.self="closeOperationModal">
        <div class="modal modal--auto">
          <div class="panel__head panel__head--tight">
            <h3>{{ operationModal.mode === 'create' ? 'Новая операция' : 'Редактировать операцию' }}</h3>
          </div>
          <div class="modal__body">
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Раздел</span>
                <select v-model="operationDraft.section_id" class="input input--select">
                  <option value="">Выберите</option>
                  <option v-for="section in ctx.financeSections" :key="`modal-op-section-${section.section_id}`" :value="section.section_id">{{ section.name }} ({{ section.code }})</option>
                </select>
              </label>
              <label class="field">
                <span class="label">Код</span>
                <input v-model="operationDraft.code" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Название</span>
                <input v-model="operationDraft.name" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Сортировка</span>
                <input v-model.number="operationDraft.sort_order" class="input" type="number" />
              </label>
            </div>
            <div class="analytics-filters">
              <label class="check-item"><input v-model="operationDraft.requires_project" type="checkbox" /><span>Требует проект</span></label>
              <label class="check-item"><input v-model="operationDraft.requires_region" type="checkbox" /><span>Требует регион</span></label>
              <label class="check-item"><input v-model="operationDraft.requires_source" type="checkbox" /><span>Требует источник</span></label>
              <label class="check-item"><input v-model="operationDraft.requires_qty" type="checkbox" /><span>Требует количество</span></label>
              <label class="check-item"><input v-model="operationDraft.allows_negative" type="checkbox" /><span>Разрешить минус</span></label>
            </div>
            <div class="toolbar-actions">
              <button class="ghost" type="button" @click="closeOperationModal">Отмена</button>
              <button data-test="finance-create-operation" class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click="submitOperationModal">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="projectModal.open" class="work-page work-modal-root modal-backdrop" @click.self="closeProjectModal">
        <div class="modal modal--auto">
          <div class="panel__head panel__head--tight">
            <h3>{{ projectModal.mode === 'create' ? 'Новый проект' : 'Редактировать проект' }}</h3>
          </div>
          <div class="modal__body">
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Код</span>
                <input v-model="projectDraft.code" class="input" type="text" />
              </label>
              <label class="field">
                <span class="label">Название</span>
                <input v-model="projectDraft.name" class="input" type="text" />
              </label>
            </div>
            <div class="toolbar-actions">
              <button class="ghost" type="button" @click="closeProjectModal">Отмена</button>
              <button data-test="finance-create-project" class="ghost" type="button" :disabled="ctx.financeCatalogSaving" @click="submitProjectModal">Сохранить</button>
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

const sectionKindLabels = Object.freeze({
  revenue: 'Выручка',
  direct_expense: 'Прямые расходы',
  indirect_expense: 'Косвенные расходы',
  other: 'Другое',
})
const financeMode = ref('entry')
const entrySectionKind = ref('')

const typeModal = reactive({ open: false, mode: 'create', type_id: null })
const sectionModal = reactive({ open: false, mode: 'create', section_id: null })
const operationModal = reactive({ open: false, mode: 'create', operation_id: null })
const projectModal = reactive({ open: false, mode: 'create', project_id: null })

const typeDraft = reactive({ code: '', name: '', sort_order: 100 })
const sectionDraft = reactive({ type_id: '', code: '', name: '', sort_order: 100 })
const operationDraft = reactive({ section_id: '', code: '', name: '', input_mode: 'mixed', requires_region: false, requires_source: false, requires_project: true, requires_qty: false, allows_negative: false, sort_order: 100 })
const projectDraft = reactive({ code: '', name: '' })

// Переключаем вид, чтобы на экране был только один смысловой блок.
function setFinanceMode(mode) {
  financeMode.value = String(mode || 'entry')
}

// Собираем быстрые словари по id/code для отображения журнала ввода.
const operationsMap = computed(() => new Map((unref(props.ctx.financeOperations) || []).map((item) => [Number(item.operation_id), item])))
const typesMap = computed(() => new Map((unref(props.ctx.financeTypes) || []).map((item) => [Number(item.type_id), item])))
const sectionsMap = computed(() => new Map((unref(props.ctx.financeSections) || []).map((item) => [Number(item.section_id), item])))
const projectsMap = computed(() => new Map((unref(props.ctx.financeProjects) || []).map((item) => [Number(item.project_id), item])))
const regionsMap = computed(() => new Map((unref(props.ctx.financeRegions) || []).map((item) => [Number(item.region_id), item])))
const sourcesMap = computed(() => new Map((unref(props.ctx.financeSources) || []).map((item) => [Number(item.source_id), item])))
const statusesMap = computed(() => new Map((unref(props.ctx.financeStatuses) || []).map((item) => [String(item.code || '').toLowerCase(), item])))

const selectedOperation = computed(() => {
  const opId = Number(unref(props.ctx.financeNewEntry?.operation_id) || 0)
  if (!opId) return null
  return operationsMap.value.get(opId) || null
})

const entryKinds = computed(() => {
  // Готовим список типов из текущих операций, чтобы пользователь выбирал схему "тип -> статья".
  const kinds = new Set()
  for (const op of (unref(props.ctx.financeOperations) || [])) {
    const section = sectionsMap.value.get(Number(op.section_id))
    const kindCode = String(section?.type_code || section?.kind || '')
    if (kindCode) kinds.add(kindCode)
  }
  return [...kinds]
})

const filteredNewEntryOperations = computed(() => {
  // Фильтруем список статей по выбранному типу расхода/выручки.
  const kind = String(entrySectionKind.value || '')
  const rows = unref(props.ctx.financeOperations) || []
  if (!kind) return rows
  return rows.filter((op) => {
    const section = sectionsMap.value.get(Number(op.section_id))
    return String(section?.type_code || section?.kind || '') === kind
  })
})

watch(
  selectedOperation,
  (nextOp) => {
    // Синхронизируем выбранный тип по операции, чтобы форма не расходилась по смыслу.
    if (!nextOp) return
    const section = sectionsMap.value.get(Number(nextOp.section_id))
    if (section?.type_code || section?.kind) {
      entrySectionKind.value = String(section?.type_code || section?.kind || '')
    }
  },
  { immediate: true },
)

watch(entrySectionKind, (nextKind) => {
  // Если пользователь сменил тип, сбрасываем статью из другого типа.
  if (!nextKind) return
  const opId = Number(unref(props.ctx.financeNewEntry?.operation_id) || 0)
  if (!opId) return
  const current = operationsMap.value.get(opId)
  if (!current) return
  const section = sectionsMap.value.get(Number(current.section_id))
  if (String(section?.type_code || section?.kind || '') !== String(nextKind)) {
    props.ctx.financeNewEntry.operation_id = ''
  }
})

const operationRequirementsLabel = computed(() => {
  const op = selectedOperation.value
  if (!op) return ''
  const flags = []
  if (op.requires_project) flags.push('проект обязателен')
  if (op.requires_region) flags.push('регион обязателен')
  if (op.requires_source) flags.push('источник обязателен')
  if (op.requires_qty) flags.push('количество обязательно')
  if (op.allows_negative) flags.push('отрицательная сумма допустима')
  return flags.length ? flags.join(', ') : 'дополнительных обязательных полей нет'
})

const selectedKindLabel = computed(() => sectionKindLabels[String(entrySectionKind.value || '')] || 'Не выбран')

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

// Преобразуем id проекта в название для журнала.
function resolveProjectName(projectId) {
  return resolveOptionName(projectsMap, projectId)
}

// Преобразуем id региона в название для журнала.
function resolveRegionName(regionId) {
  return resolveOptionName(regionsMap, regionId)
}

// Преобразуем id источника в название для журнала.
function resolveSourceName(sourceId) {
  return resolveOptionName(sourcesMap, sourceId)
}

// Преобразуем id раздела в название для таблиц настроек.
function resolveSectionName(sectionId) {
  return resolveOptionName(sectionsMap, sectionId)
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

// Собираем короткое описание правил операции.
function getOperationRuleSummary(operation) {
  const flags = []
  if (operation?.requires_project) flags.push('проект')
  if (operation?.requires_region) flags.push('регион')
  if (operation?.requires_source) flags.push('источник')
  if (operation?.requires_qty) flags.push('кол-во')
  if (operation?.allows_negative) flags.push('минус')
  return flags.length ? flags.join(', ') : 'без обязательных полей'
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
  typeDraft.sort_order = 100
}

// Открываем редактирование типа из строки таблицы.
function openTypeEditModal(type) {
  typeModal.open = true
  typeModal.mode = 'edit'
  typeModal.type_id = Number(type?.type_id || 0)
  typeDraft.code = String(type?.code || '')
  typeDraft.name = String(type?.name || '')
  typeDraft.sort_order = Number(type?.sort_order || 100)
}

// Закрываем модалку типа без сохранения.
function closeTypeModal() {
  typeModal.open = false
}

// Сохраняем тип: создаем новый или обновляем существующий.
async function submitTypeModal() {
  const payload = {
    code: typeDraft.code,
    name: typeDraft.name,
    sort_order: Number(typeDraft.sort_order || 100),
  }
  const ok = typeModal.mode === 'create'
    ? await props.ctx.createFinanceType?.(payload)
    : await props.ctx.updateFinanceType?.(typeModal.type_id, payload)
  if (ok) closeTypeModal()
}

// Архивируем тип справочника finance.
async function archiveType(typeId) {
  await props.ctx.archiveFinanceType?.(typeId)
}

// Готовим форму раздела для создания.
function openSectionCreateModal() {
  sectionModal.open = true
  sectionModal.mode = 'create'
  sectionModal.section_id = null
  sectionDraft.type_id = Number((unref(props.ctx.financeTypes) || [])[0]?.type_id || '') || ''
  sectionDraft.code = ''
  sectionDraft.name = ''
  sectionDraft.sort_order = 100
}

// Открываем редактирование раздела из строки таблицы.
function openSectionEditModal(section) {
  sectionModal.open = true
  sectionModal.mode = 'edit'
  sectionModal.section_id = Number(section?.section_id || 0)
  sectionDraft.type_id = section?.type_id ? Number(section.type_id) : ''
  sectionDraft.code = String(section?.code || '')
  sectionDraft.name = String(section?.name || '')
  sectionDraft.sort_order = Number(section?.sort_order || 100)
}

// Закрываем модалку раздела без сохранения.
function closeSectionModal() {
  sectionModal.open = false
}

// Сохраняем раздел: создаем новый или обновляем существующий.
async function submitSectionModal() {
  const payload = {
    type_id: sectionDraft.type_id ? Number(sectionDraft.type_id) : null,
    code: sectionDraft.code,
    name: sectionDraft.name,
    sort_order: Number(sectionDraft.sort_order || 100),
  }
  const ok = sectionModal.mode === 'create'
    ? await props.ctx.createFinanceSection?.(payload)
    : await props.ctx.updateFinanceSection?.(sectionModal.section_id, payload)
  if (ok) closeSectionModal()
}

// Архивируем раздел справочника finance.
async function archiveSection(sectionId) {
  await props.ctx.archiveFinanceSection?.(sectionId)
}

// Готовим форму операции для создания.
function openOperationCreateModal() {
  operationModal.open = true
  operationModal.mode = 'create'
  operationModal.operation_id = null
  operationDraft.section_id = ''
  operationDraft.code = ''
  operationDraft.name = ''
  operationDraft.input_mode = 'mixed'
  operationDraft.requires_region = false
  operationDraft.requires_source = false
  operationDraft.requires_project = true
  operationDraft.requires_qty = false
  operationDraft.allows_negative = false
  operationDraft.sort_order = 100
}

// Открываем редактирование операции из строки таблицы.
function openOperationEditModal(operation) {
  operationModal.open = true
  operationModal.mode = 'edit'
  operationModal.operation_id = Number(operation?.operation_id || 0)
  operationDraft.section_id = Number(operation?.section_id || 0)
  operationDraft.code = String(operation?.code || '')
  operationDraft.name = String(operation?.name || '')
  operationDraft.input_mode = String(operation?.input_mode || 'mixed')
  operationDraft.requires_region = Boolean(operation?.requires_region)
  operationDraft.requires_source = Boolean(operation?.requires_source)
  operationDraft.requires_project = Boolean(operation?.requires_project)
  operationDraft.requires_qty = Boolean(operation?.requires_qty)
  operationDraft.allows_negative = Boolean(operation?.allows_negative)
  operationDraft.sort_order = Number(operation?.sort_order || 100)
}

// Закрываем модалку операции без сохранения.
function closeOperationModal() {
  operationModal.open = false
}

// Сохраняем операцию: создаем новую или обновляем существующую.
async function submitOperationModal() {
  const payload = {
    section_id: operationDraft.section_id,
    code: operationDraft.code,
    name: operationDraft.name,
    input_mode: operationDraft.input_mode,
    requires_region: operationDraft.requires_region,
    requires_source: operationDraft.requires_source,
    requires_project: operationDraft.requires_project,
    requires_qty: operationDraft.requires_qty,
    allows_negative: operationDraft.allows_negative,
    sort_order: Number(operationDraft.sort_order || 100),
  }
  const ok = operationModal.mode === 'create'
    ? await props.ctx.createFinanceOperation?.(payload)
    : await props.ctx.updateFinanceOperation?.(operationModal.operation_id, payload)
  if (ok) closeOperationModal()
}

// Архивируем операцию справочника finance.
async function archiveOperation(operationId) {
  await props.ctx.archiveFinanceOperation?.(operationId)
}

// Готовим форму проекта для создания.
function openProjectCreateModal() {
  projectModal.open = true
  projectModal.mode = 'create'
  projectModal.project_id = null
  projectDraft.code = ''
  projectDraft.name = ''
}

// Открываем редактирование проекта из строки таблицы.
function openProjectEditModal(project) {
  projectModal.open = true
  projectModal.mode = 'edit'
  projectModal.project_id = Number(project?.project_id || 0)
  projectDraft.code = String(project?.code || '')
  projectDraft.name = String(project?.name || '')
}

// Закрываем модалку проекта без сохранения.
function closeProjectModal() {
  projectModal.open = false
}

// Сохраняем проект: создаем новый или обновляем существующий.
async function submitProjectModal() {
  const payload = { code: projectDraft.code, name: projectDraft.name }
  const ok = projectModal.mode === 'create'
    ? await props.ctx.createFinanceProject?.(payload)
    : await props.ctx.updateFinanceProject?.(projectModal.project_id, payload)
  if (ok) closeProjectModal()
}

// Архивируем проект справочника finance.
async function archiveProject(projectId) {
  await props.ctx.archiveFinanceProject?.(projectId)
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
</script>
