import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkFinanceSection from '../sections/WorkFinanceSection.vue'

function buildCtx(overrides = {}) {
  return {
    activeTab: 'finance',
    routeQuery: {},
    canViewUsersSection: true,
    canManageRolePermissions: true,
    canViewAnalyticsSection: true,
    canViewCatalogsSection: true,
    canViewFinanceSection: true,
    financeLoading: false,
    financeEntriesLoading: false,
    financeEntrySaving: false,
    financeCatalogSaving: false,
    financeError: '',
    financeEntriesError: '',
    financeEntryError: '',
    financeCatalogError: '',
    financeCatalogOk: '',
    financeEntryOk: '',
    financeLoaded: true,
    financeEntriesTotal: 1,
    financeFilters: {
      date_from: '2026-05-01',
      date_to: '2026-05-31',
      project_id: '',
      region_id: '',
      source_id: '',
      split_by_source: false,
    },
    financeNewEntry: {
      biz_date: '2026-05-31',
      operation_id: '7',
      project_id: '',
      region_id: '',
      source_id: '',
      qty: 1,
      amount: '100',
      currency: 'RUB',
      comment: '',
    },
    financeEntryFilters: {
      date_from: '',
      date_to: '',
      project_id: '',
      region_id: '',
      source_id: '',
      operation_id: '',
      status_code: '',
      limit: 50,
    },
    financeNewSection: {
      type_id: 2,
      code: '',
      name: '',
      sort_order: 100,
    },
    financeNewOperation: {
      section_id: '',
      code: '',
      name: '',
      input_mode: 'mixed',
      requires_region: false,
      requires_source: false,
      requires_project: true,
      requires_qty: false,
      allows_negative: false,
      sort_order: 100,
    },
    financeNewProject: {
      code: '',
      name: '',
    },
    financeOperations: [{ operation_id: 7, section_id: 20, code: 'rev_sale', name: 'Продажа', requires_project: true, requires_region: true, requires_source: true, requires_qty: false, allows_negative: false }],
    financeTypes: [{ type_id: 2, code: 'direct_expense', name: 'Прямые расходы' }],
    financeSections: [{ section_id: 20, type_id: 2, type_code: 'direct_expense', kind: 'direct_expense', code: 'direct', name: 'Прямые расходы' }],
    financeProjects: [{ project_id: 1, code: 'core', name: 'Core' }],
    financeRegions: [{ region_id: 10, code: 'TR', name: 'Turkey' }],
    financeSources: [{ source_id: 99, code: 'ym', name: 'ASAT' }],
    financeStatuses: [{ code: 'confirmed', name: 'Подтверждено' }],
    financeEntries: [{ entry_id: 1, biz_date: '2026-05-30', operation_id: 7, project_id: 1, region_id: 10, source_id: 99, qty: '1.00', amount: '100.00', status_code: 'confirmed', created_by: 'qa' }],
    financeReportTotals: {
      revenue: 1000,
      direct_expense: 500,
      indirect_expense: 100,
      operating_profit: 400,
      margin: 0.4,
    },
    financeReportItems: [
      {
        project_code: 'core',
        project_name: 'Core',
        source_id: 99,
        source_name: 'ASAT',
        revenue: 1000,
        direct_expense: 500,
        indirect_expense: 100,
        operating_profit: 400,
        margin: 0.4,
      },
    ],
    loadFinanceProjectsReport: vi.fn(),
    loadFinanceEntries: vi.fn(),
    createFinanceEntry: vi.fn(),
    createFinanceSection: vi.fn(),
    archiveFinanceSection: vi.fn(),
    updateFinanceSection: vi.fn(),
    createFinanceType: vi.fn(),
    archiveFinanceType: vi.fn(),
    updateFinanceType: vi.fn(),
    createFinanceOperation: vi.fn(),
    archiveFinanceOperation: vi.fn(),
    updateFinanceOperation: vi.fn(),
    createFinanceProject: vi.fn(),
    archiveFinanceProject: vi.fn(),
    updateFinanceProject: vi.fn(),
    maxDate: '2026-05-31',
    minDate: '2020-01-01',
    formatPrice: (v) => String(v),
    formatPercent: (v) => String(v),
    ...overrides,
  }
}

describe('WorkFinanceSection', () => {
  it('renders mode tabs and entry form by default', () => {
    const wrapper = mount(WorkFinanceSection, {
      props: { ctx: buildCtx() },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a class="admin-link"><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.findAll('.admin-link').length).toBeGreaterThanOrEqual(4)
    expect(wrapper.text()).toContain('Финансы')
    expect(wrapper.text()).toContain('Справочники')
    expect(wrapper.text()).toContain('Ввод')
    expect(wrapper.text()).toContain('Журнал')
    expect(wrapper.text()).toContain('Отчет')
    expect(wrapper.text()).toContain('Ввод операции')
    expect(wrapper.text()).toContain('Продажа')
    expect(wrapper.text()).toContain('Тип: Прямые расходы')
  })

  it('calls actions for save, journal refresh and report build', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkFinanceSection, {
      props: { ctx },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a><slot /></a>',
          },
        },
      },
    })

    await wrapper.find('[data-test="finance-save-entry"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-journal"]').trigger('click')
    await wrapper.find('[data-test="finance-apply-entries-filters"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-report"]').trigger('click')
    await wrapper.find('[data-test="finance-apply-report"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-catalogs"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-section"]').trigger('click')
    await wrapper.find('[data-test="finance-create-section"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-operation"]').trigger('click')
    await wrapper.find('[data-test="finance-create-operation"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-project"]').trigger('click')
    await wrapper.find('[data-test="finance-create-project"]').trigger('click')

    expect(ctx.createFinanceEntry).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceEntries).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceProjectsReport).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceType).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceSection).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceOperation).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceProject).toHaveBeenCalledTimes(1)
  })

  it('shows source column when split_by_source is enabled', async () => {
    const ctx = buildCtx({
      financeFilters: {
        date_from: '2026-05-01',
        date_to: '2026-05-31',
        project_id: '',
        region_id: '',
        source_id: '',
        split_by_source: true,
      },
    })
    const wrapper = mount(WorkFinanceSection, {
      props: { ctx },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a><slot /></a>',
          },
        },
      },
    })

    await wrapper.find('[data-test="finance-mode-report"]').trigger('click')
    expect(wrapper.text()).toContain('Источник')
  })
})
