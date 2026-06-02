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
    financeCashFlowLoading: false,
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
    },
    financeNewSection: {
      type_id: 2,
      code: '',
      name: '',
      sort_order: 100,
    },
    financeNewOperation: {
      type_id: '',
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
    financeOperations: [{ operation_id: 7, type_id: 2, section_id: 20, code: 'rev_sale', name: 'Продажа', requires_project: true, requires_region: true, requires_source: true, requires_qty: false, allows_negative: false }],
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
        source_id: 99,
        source_code: 'ym',
        source_name: 'ASAT',
        region_id: 10,
        region_code: 'TR',
        region_name: 'Turkey',
        revenue: 1000,
        direct_expense: 500,
        cash_flow: 500,
        deals_count: 2,
      },
    ],
    financeCashFlowLoaded: true,
    financeCashFlowTotals: {
      revenue: 20000,
      expense: 7000,
      cash_flow: 13000,
      opening_balance: 3000,
      current_balance: 16000,
      opening_balance_month: '2026-05-01',
      opening_balance_manual: true,
    },
    financeCashFlowMonth: '2026-05',
    financeCashFlowOpeningDraft: '3000',
    financeCashFlowOpeningSaving: false,
    financeCashFlowOpeningOk: '',
    financeCashFlowRevenues: [
      { name: 'Продажа TR', amount: 15000 },
      { name: 'Шеринг TR', amount: 5000 },
    ],
    financeCashFlowExpenses: [
      { name: 'Закуп TR', amount: 6000 },
      { name: 'Маркетинг', amount: 1000 },
    ],
    loadFinanceProjectsReport: vi.fn(),
    loadFinanceCashFlowReport: vi.fn(),
    saveFinanceCashFlowOpeningBalance: vi.fn(),
    loadFinanceEntries: vi.fn(),
    createFinanceEntry: vi.fn(),
    deleteFinanceEntry: vi.fn(),
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
    expect(wrapper.text()).toContain('Отчет по источникам')
    expect(wrapper.text()).toContain('Cash Flow')
    expect(wrapper.text()).toContain('Комментарий')
    expect(wrapper.text()).toContain('Продажа')
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
    await wrapper.find('[data-test="finance-mode-cash-flow"]').trigger('click')
    await wrapper.find('[data-test="finance-apply-cash-flow"]').trigger('click')
    await wrapper.find('[data-test="finance-save-cash-flow-opening"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-catalogs"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-operation"]').trigger('click')
    await wrapper.find('[data-test="finance-create-operation"]').trigger('click')

    expect(ctx.createFinanceEntry).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceEntries).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceProjectsReport).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceCashFlowReport).toHaveBeenCalledTimes(1)
    expect(ctx.saveFinanceCashFlowOpeningBalance).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceType).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceOperation).toHaveBeenCalledTimes(1)
  })

  it('shows source report rows', async () => {
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
    expect(wrapper.text()).toContain('Поступления')
    expect(wrapper.text()).toContain('Расходы')
    expect(wrapper.text()).toContain('Cash Flow')
    expect(wrapper.text()).toContain('ASAT - ym')
    expect(wrapper.text()).toContain('TR')
    expect(wrapper.text()).not.toContain('Turkey - TR')
  })

  it('shows cash flow report rows and balances', async () => {
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

    await wrapper.find('[data-test="finance-mode-cash-flow"]').trigger('click')

    expect(wrapper.text()).toContain('Поступления')
    expect(wrapper.text()).toContain('Расходы')
    expect(wrapper.text()).toContain('Остаток прошлый')
    expect(wrapper.text()).toContain('Остаток текущий')
    expect(wrapper.text()).toContain('ручной остаток месяца')
    expect(wrapper.text()).toContain('Продажа TR')
    expect(wrapper.text()).toContain('Шеринг TR')
    expect(wrapper.text()).toContain('Закуп TR')
    expect(wrapper.text()).toContain('Маркетинг')
  })

  it('keeps cash flow apply button enabled when only source report is loading', async () => {
    const ctx = buildCtx({ financeLoading: true, financeCashFlowLoading: false })
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

    await wrapper.find('[data-test="finance-mode-cash-flow"]').trigger('click')

    expect(wrapper.find('[data-test="finance-apply-cash-flow"]').attributes('disabled')).toBeUndefined()
  })

  it('shows type modal with name-only input', async () => {
    const ctx = buildCtx({
      financeTypes: [{ type_id: 2, code: 'direct_expense', name: 'Прямые расходы' }],
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

    await wrapper.find('[data-test="finance-mode-catalogs"]').trigger('click')
    expect(wrapper.text()).not.toContain('Архив')

    await wrapper.find('[data-test="finance-type-row-2"]').trigger('click')
    expect(wrapper.text()).toContain('Редактировать тип')
    expect(wrapper.text()).toContain('Название')
    expect(wrapper.text()).not.toContain('Код системного типа фиксирован')
  })

  it('archives type and operation from edit modals', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const ctx = buildCtx()
    ctx.archiveFinanceType.mockResolvedValue(true)
    ctx.archiveFinanceOperation.mockResolvedValue(true)

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

    await wrapper.find('[data-test="finance-mode-catalogs"]').trigger('click')
    await wrapper.find('[data-test="finance-type-row-2"]').trigger('click')
    await wrapper.find('[data-test="finance-delete-type"]').trigger('click')

    await wrapper.find('[data-test="finance-operation-row-7"]').trigger('click')
    await wrapper.find('[data-test="finance-delete-operation"]').trigger('click')

    expect(ctx.archiveFinanceType).toHaveBeenCalledWith(2)
    expect(ctx.archiveFinanceOperation).toHaveBeenCalledWith(7)
    expect(confirmSpy).toHaveBeenCalledTimes(2)
    confirmSpy.mockRestore()
  })

  it('deletes entry from journal after confirm', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
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

    await wrapper.find('[data-test="finance-mode-journal"]').trigger('click')
    await wrapper.find('[data-test="finance-delete-entry-1"]').trigger('click')

    expect(ctx.deleteFinanceEntry).toHaveBeenCalledWith(1)
    confirmSpy.mockRestore()
  })
})
