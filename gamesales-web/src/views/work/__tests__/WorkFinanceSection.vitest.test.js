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
    financeMode: 'entry',
    financeLoading: false,
    financeCashFlowLoading: false,
    financeTrCardBalanceLoading: false,
    financeTrCardBalanceSaving: false,
    financeEntriesLoading: false,
    financeEntrySaving: false,
    financeCatalogSaving: false,
    financeYandexSyncLoading: false,
    financeWildberriesSyncLoading: false,
    financeOzonSyncLoading: false,
    financeWildberriesWaitSeconds: 0,
    financeWildberriesCooldownSeconds: 0,
    financeWildberriesCooldownStoreCode: '',
    financeOzonCooldownSeconds: 0,
    financeOzonCooldownStoreCode: '',
    financeError: '',
    financeEntriesError: '',
    financeEntryError: '',
    financeCatalogError: '',
    financeCatalogOk: '',
    financeEntryOk: '',
    financeTrCardBalanceError: '',
    financeYandexSyncError: '',
    financeYandexSyncOk: '',
    financeYandexSyncStatus: '',
    financeWildberriesSyncError: '',
    financeWildberriesSyncOk: '',
    financeWildberriesSyncStatus: '',
    financeOzonSyncError: '',
    financeOzonSyncOk: '',
    financeOzonSyncStatus: '',
    financeLoaded: true,
    financeEntriesTotal: 1,
    financeFilters: {
      date_from: '2026-05-01',
      date_to: '2026-05-31',
      project_id: '',
      region_id: [],
      source_id: [],
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
    financeYandexSync: {
      store_code: 'asat',
      date_from: '2026-05-30',
      date_to: '2026-05-31',
    },
    financeWildberriesSync: {
      store_code: 'asat',
      date_from: '2026-05-30',
      date_to: '2026-05-31',
    },
    financeOzonSync: {
      store_code: 'asat',
      date_from: '2026-05-30',
      date_to: '2026-05-31',
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
    financeEntries: [{ entry_id: 1, biz_date: '2026-05-30', operation_id: 7, project_id: 1, region_id: 10, source_id: 99, qty: '1.00', amount: '100.00', comment: 'Ручная корректировка', status_code: 'confirmed', created_by: 'qa' }],
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
      {
        source_id: null,
        source_code: null,
        source_name: 'Без источника',
        region_id: 10,
        region_code: 'TR',
        region_name: 'Turkey',
        revenue: 300,
        direct_expense: 100,
        cash_flow: 200,
        deals_count: 1,
      },
      {
        source_id: null,
        source_code: null,
        source_name: 'Без источника',
        region_id: null,
        region_code: null,
        region_name: null,
        revenue: 150,
        direct_expense: 0,
        cash_flow: 150,
        deals_count: 1,
      },
    ],
    financeSourceDetails: [
      {
        row_type: 'deal',
        deal_id: 16308,
        activity_date: '2026-06-02',
        customer_name: 'LifeGuard58',
        operation_name: 'Услуга',
        item_title: 'item-16308',
        revenue: 5810,
        purchase_cost: 1660,
        purchase_cost_rate: 2.5,
        direct_expense: 4150,
        cash_flow: 1660,
        order_ids: ['577', '578'],
        orders_count: 2,
        reason: 'Источник клиента не привязан к finance source',
      },
      {
        row_type: 'entry',
        entry_id: 55,
        activity_date: '2026-06-02',
        operation_name: 'Комиссия',
        item_title: 'нулевая проверка',
        revenue: 0,
        purchase_cost: 0,
        purchase_cost_rate: null,
        direct_expense: 0,
        cash_flow: 0,
        order_ids: [],
        orders_count: 0,
        reason: '',
      },
    ],
    financeSourceDetailsTotals: {
      revenue: 5810,
      purchase_cost: 1660,
      direct_expense: 4150,
      indirect_expense: 0,
      operating_profit: 1660,
      margin: 0.2857,
    },
    financeSourceDetailsTitle: 'Услуга / TR',
    financeSourceDetailsOpen: false,
    financeSourceDetailsLoading: false,
    financeCashFlowLoaded: true,
    financeTrCardBalanceLoaded: true,
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
    financeTrCardBalance: {
      card_code: 'TR',
      region_code: 'TR',
      currency: 'TRY',
      snapshot_balance: 25000,
      spent_after_snapshot: 6000,
      current_balance: 19000,
      snapshot_at: '2026-05-10T11:20:00+03:00',
      snapshot_manual: true,
      comment: '',
    },
    financeTrCardBalanceDraft: '19000',
    financeCashFlowOpeningSaving: false,
    financeCashFlowDetailsLoading: false,
    financeCashFlowOpeningOk: '',
    financeCashFlowRevenues: [
      { name: 'Продажа TR', amount: 15000 },
      { name: 'Шеринг TR', amount: 5000 },
    ],
    financeCashFlowExpenses: [
      { name: 'Закуп TR', amount: 6000 },
      { name: 'Маркетинг', amount: 1000 },
    ],
    financeCashFlowDetailsFilters: {
      date_from: '2026-05-01',
      date_to: '2026-05-31',
    },
    financeCashFlowDetails: [
      {
        row_type: 'deal',
        line_type: 'revenue',
        line_name: 'Продажа TR',
        activity_date: '2026-05-10',
        deal_id: 16308,
        customer_name: 'LifeGuard58',
        operation_name: 'Услуга',
        item_title: 'item-16308',
        region_code: 'TR',
        source_name: 'ASAT',
        source_code: 'ym',
        qty: '1',
        amount: 5810,
        created_by: 'Анатолий',
        order_ids: ['577', '578'],
        orders_count: 2,
        reason: 'Поступление по завершенной продаже',
      },
    ],
    financeCashFlowDetailsTotals: {
      revenue: 5810,
      expense: 0,
      cash_flow: 5810,
    },
    financeCashFlowDetailsTitle: 'Поступление: Продажа TR',
    financeCashFlowDetailsOpen: false,
    financeYandexSyncResult: null,
    financeWildberriesSyncResult: null,
    financeOzonSyncResult: null,
    loadFinanceProjectsReport: vi.fn(),
    loadFinanceSourceDetails: vi.fn(),
    clearFinanceSourceDetails: vi.fn(),
    openFinanceDetailDeal: vi.fn(),
    loadFinanceCashFlowReport: vi.fn(),
    loadFinanceCashFlowDetails: vi.fn(),
    clearFinanceCashFlowDetails: vi.fn(),
    resetFinanceCashFlowDetailsPeriod: vi.fn(),
    saveFinanceCashFlowOpeningBalance: vi.fn(),
    loadFinanceTrCardBalance: vi.fn(),
    saveFinanceTrCardBalance: vi.fn(),
    syncFinanceYandexMarket: vi.fn(),
    syncFinanceWildberries: vi.fn(),
    syncFinanceOzon: vi.fn(),
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
    expect(wrapper.text()).toContain('Интеграции')
    expect(wrapper.text()).toContain('Отчет по источникам')
    expect(wrapper.text()).toContain('Cash Flow')
    expect(wrapper.text()).not.toContain('Магазин')
    expect(wrapper.text()).not.toContain('ASAT - wb')
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
    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')
    await wrapper.find('[data-test="finance-sync-yandex"]').trigger('click')
    await wrapper.find('[data-test="finance-sync-wildberries"]').trigger('click')
    await wrapper.find('[data-test="finance-sync-ozon"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-report"]').trigger('click')
    await wrapper.find('[data-test="finance-apply-report"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-cash-flow"]').trigger('click')
    await wrapper.find('[data-test="finance-apply-cash-flow"]').trigger('click')
    await wrapper.find('[data-test="finance-save-cash-flow-opening"]').trigger('click')
    await wrapper.find('[data-test="finance-refresh-tr-card-balance"]').trigger('click')
    await wrapper.find('[data-test="finance-edit-tr-card-balance"]').trigger('click')
    await wrapper.find('[data-test="finance-save-tr-card-balance"]').trigger('click')
    await wrapper.find('[data-test="finance-mode-catalogs"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-create-type"]').trigger('click')
    await wrapper.find('[data-test="finance-open-create-operation"]').trigger('click')
    await wrapper.find('[data-test="finance-create-operation"]').trigger('click')

    expect(ctx.createFinanceEntry).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceEntries).toHaveBeenCalledTimes(1)
    expect(ctx.syncFinanceYandexMarket).toHaveBeenCalledTimes(1)
    expect(ctx.syncFinanceWildberries).toHaveBeenCalledTimes(1)
    expect(ctx.syncFinanceOzon).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceProjectsReport).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceCashFlowReport).toHaveBeenCalledTimes(1)
    expect(ctx.saveFinanceCashFlowOpeningBalance).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceTrCardBalance).toHaveBeenCalledTimes(1)
    expect(ctx.saveFinanceTrCardBalance).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceType).toHaveBeenCalledTimes(1)
    expect(ctx.createFinanceOperation).toHaveBeenCalledTimes(1)
  })

  it('shows Yandex sync result as daily aggregates', async () => {
    const ctx = buildCtx({
      financeYandexSyncResult: {
        total_rows: 30,
        created_rows: 1,
        updated_rows: 2,
        skipped_rows: 0,
        failed_rows: 0,
      },
      financeYandexSyncOk: 'Yandex: дней добавлено 1, дней обновлено 2, дней пропущено 0, ошибок 0',
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

    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')

    expect(wrapper.text()).toContain('Магазин')
    expect(wrapper.text()).toContain('SPS - ym')
    expect(wrapper.text()).toContain('MDS - ym')
    expect(wrapper.text()).toContain('Строк Яндекса')
    expect(wrapper.text()).toContain('Дней добавлено')
    expect(wrapper.text()).toContain('Дней обновлено')
    expect(wrapper.text()).toContain('Дней пропущено')
    expect(wrapper.text()).toContain('Yandex: дней добавлено 1, дней обновлено 2, дней пропущено 0, ошибок 0')
  })

  it('shows Wildberries sync result as daily aggregates', async () => {
    const ctx = buildCtx({
      financeWildberriesSyncResult: {
        total_rows: 45,
        created_rows: 2,
        updated_rows: 1,
        skipped_rows: 0,
        failed_rows: 0,
      },
      financeWildberriesSyncOk: 'Wildberries: дней добавлено 2, дней обновлено 1, дней пропущено 0, ошибок 0',
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

    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')

    expect(wrapper.text()).toContain('Wildberries')
    expect(wrapper.text()).toContain('ASAT - wb')
    expect(wrapper.text()).toContain('SPS - wb')
    expect(wrapper.text()).toContain('Строк WB')
    expect(wrapper.text()).toContain('Wildberries: дней добавлено 2, дней обновлено 1, дней пропущено 0, ошибок 0')
  })

  it('shows Ozon sync result as daily aggregates', async () => {
    const ctx = buildCtx({
      financeOzonSyncResult: {
        total_rows: 60,
        created_rows: 2,
        updated_rows: 1,
        skipped_rows: 0,
        failed_rows: 0,
      },
      financeOzonSyncOk: 'Ozon: дней добавлено 2, дней обновлено 1, дней пропущено 0, ошибок 0',
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

    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')

    expect(wrapper.text()).toContain('Ozon')
    expect(wrapper.text()).toContain('ASAT - ozon')
    expect(wrapper.text()).not.toContain('SPS - ozon')
    expect(wrapper.text()).toContain('Операций Ozon')
    expect(wrapper.text()).toContain('Ozon: дней добавлено 2, дней обновлено 1, дней пропущено 0, ошибок 0')
  })

  it('shows Wildberries retry countdown and disables sync button', async () => {
    const ctx = buildCtx({
      financeWildberriesCooldownSeconds: 47,
      financeWildberriesCooldownStoreCode: 'asat',
      financeWildberriesSyncStatus: 'Повторный запуск будет доступен через 47 сек.',
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

    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')
    const button = wrapper.find('[data-test="finance-sync-wildberries"]')

    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toContain('Повторить через 47 сек.')
    expect(wrapper.text()).toContain('Повторный запуск будет доступен через 47 сек.')
  })

  it('shows Wildberries wait countdown during active sync', async () => {
    const ctx = buildCtx({
      financeWildberriesSyncLoading: true,
      financeWildberriesWaitSeconds: 54,
      financeWildberriesSyncStatus: 'Ждем лимит Wildberries: 54 сек.',
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

    await wrapper.find('[data-test="finance-mode-integrations"]').trigger('click')

    expect(wrapper.find('[data-test="finance-sync-wildberries"]').text()).toContain('Ждем 54 сек.')
    expect(wrapper.text()).toContain('Ждем лимит Wildberries: 54 сек.')
  })

  it('shows source report rows', async () => {
    const ctx = buildCtx({
      financeFilters: {
        date_from: '2026-05-01',
        date_to: '2026-05-31',
        project_id: '',
        region_id: [10],
        source_id: [99],
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
    expect(ctx.financeMode).toBe('report')
    expect(wrapper.find('[data-test="finance-report-regions"]').text()).toContain('Turkey')
    expect(wrapper.find('[data-test="finance-report-sources"]').text()).toContain('ASAT - ym')
    await wrapper.find('[data-test="finance-report-regions"] button').trigger('click')
    expect(wrapper.find('[data-test="finance-report-regions"]').text()).toContain('Все')
    const regionCheckboxes = wrapper.findAll('[data-test="finance-report-regions"] input[type="checkbox"]')
    expect(regionCheckboxes).toHaveLength(2)
    regionCheckboxes[1].element.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('[data-test="finance-report-regions"] input[type="checkbox"]')).toHaveLength(2)
    await regionCheckboxes[1].setValue(false)
    expect(ctx.financeFilters.region_id).toEqual([])
    document.body.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('[data-test="finance-report-regions"] input[type="checkbox"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Название')
    expect(wrapper.text()).toContain('Поступления')
    expect(wrapper.text()).toContain('Расходы')
    expect(wrapper.text()).toContain('Итог')
    expect(wrapper.find('table thead').text()).toContain('Итог')
    expect(wrapper.find('table thead').text()).not.toContain('Маржа')
    expect(wrapper.text()).toContain('ASAT - ym')
    expect(wrapper.text()).toContain('Услуга')
    expect(wrapper.text()).toContain('Шеринг')
    expect(wrapper.text()).toContain('TR')
    expect(wrapper.text()).not.toContain('Без источника')
    expect(wrapper.text()).not.toContain('Turkey - TR')
  })

  it('opens source report detail modal for selected row', async () => {
    const ctx = buildCtx({ financeSourceDetailsOpen: true })
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
    const buttons = wrapper.findAll('[data-test^="finance-source-details-"]')
    await buttons[1].trigger('click')

    expect(ctx.loadFinanceSourceDetails).toHaveBeenCalledWith(
      expect.objectContaining({ source_id: null, region_id: 10 }),
      'Услуга / TR',
    )
    expect(wrapper.text()).toContain('Услуга / TR')
    expect(wrapper.text()).toContain('Себестоимость')
    expect(wrapper.text()).toContain('1660')
    expect(wrapper.text()).toContain('Сделка #16308')
    await wrapper.find('[data-test="finance-detail-open-deal-16308"]').trigger('click')
    expect(ctx.openFinanceDetailDeal).toHaveBeenCalledWith(16308, 'report')
    expect(wrapper.text()).toContain('LifeGuard58')
    expect(wrapper.text()).toContain('577, 578')
    expect(wrapper.text()).toContain('заказов 2')
    expect(wrapper.text()).toContain('Источник клиента не привязан к finance source')
    const zeroRowCells = wrapper.findAll('.finance-details-table tbody tr')[1].findAll('td').map((cell) => cell.text())
    expect(zeroRowCells[2]).toBe('0')
    expect(zeroRowCells[3]).toBe('0')
    expect(zeroRowCells[4]).toBe('—')
    expect(zeroRowCells[5]).toBe('0')
    expect(zeroRowCells[6]).toBe('0')
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

  it('shows TR card balance with sign color', async () => {
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

    expect(wrapper.find('[data-test="finance-tr-card-balance"]').text()).toContain('19000 TRY')
    expect(wrapper.find('.finance-tr-card__value').classes()).toContain('finance-tr-card__value--positive')
    expect(wrapper.text()).not.toContain('Списано: 6000 TRY')
    expect(wrapper.text()).not.toContain('снимок 2026-05-10 11:20')
    expect(wrapper.find('[aria-label="Фактический баланс TR-карты"]').exists()).toBe(false)
    await wrapper.find('[data-test="finance-edit-tr-card-balance"]').trigger('click')
    expect(wrapper.text()).toContain('Баланс TR-карты')
    expect(wrapper.find('[aria-label="Фактический баланс TR-карты"]').exists()).toBe(true)
    await wrapper.find('[data-test="finance-cancel-tr-card-balance"]').trigger('click')
    expect(wrapper.find('[aria-label="Фактический баланс TR-карты"]').exists()).toBe(false)

    const negativeWrapper = mount(WorkFinanceSection, {
      props: {
        ctx: buildCtx({
          financeTrCardBalance: {
            ...ctx.financeTrCardBalance,
            current_balance: -500,
          },
        }),
      },
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

    expect(negativeWrapper.find('.finance-tr-card__value').text()).toContain('-500 TRY')
    expect(negativeWrapper.find('.finance-tr-card__value').classes()).toContain('finance-tr-card__value--negative')

    const loadingWrapper = mount(WorkFinanceSection, {
      props: { ctx: buildCtx({ financeTrCardBalanceLoading: true }) },
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

    expect(loadingWrapper.find('[data-test="finance-refresh-tr-card-balance"] .wheel-and-hamster').exists()).toBe(true)
  })

  it('opens cash flow detail modal and applies date interval', async () => {
    const ctx = buildCtx({ financeCashFlowDetailsOpen: true })
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
    await wrapper.find('[data-test="finance-cash-flow-details-revenue-0"]').trigger('click')

    expect(ctx.resetFinanceCashFlowDetailsPeriod).toHaveBeenCalledTimes(1)
    expect(ctx.loadFinanceCashFlowDetails).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Продажа TR', line_type: 'revenue' }),
      'Поступление: Продажа TR',
    )
    expect(wrapper.text()).toContain('Дата проводки 2026-05-01 — 2026-05-31')
    expect(wrapper.text()).toContain('Сделка #16308')
    expect(wrapper.text()).toContain('LifeGuard58')
    expect(wrapper.text()).toContain('ASAT - ym')
    expect(wrapper.text()).toContain('Кто внес')
    expect(wrapper.text()).toContain('Анатолий')
    expect(wrapper.text()).not.toContain('Строка Cash Flow')
    expect(wrapper.text()).not.toContain('Товар / комментарий')
    expect(wrapper.text()).not.toContain('Кол-во')
    expect(wrapper.text()).not.toContain('Заказы')

    await wrapper.find('[data-test="finance-cash-flow-open-deal-16308"]').trigger('click')
    expect(ctx.openFinanceDetailDeal).toHaveBeenCalledWith(16308, 'cash-flow')

    await wrapper.find('[data-test="finance-apply-cash-flow-details"]').trigger('click')
    expect(ctx.loadFinanceCashFlowDetails).toHaveBeenCalledTimes(2)
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

  it('shows entry comments in journal', async () => {
    const ctx = buildCtx({
      financeEntries: [
        { entry_id: 1, biz_date: '2026-05-30', operation_id: 7, project_id: 1, region_id: 10, source_id: 99, qty: '1.00', amount: '100.00', comment: 'Ручная корректировка', status_code: 'confirmed' },
        { entry_id: 2, biz_date: '2026-05-31', operation_id: 7, project_id: 1, region_id: 10, source_id: 99, qty: '1.00', amount: '200.00', comment: '', status_code: 'confirmed' },
      ],
      financeEntriesTotal: 2,
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

    await wrapper.find('[data-test="finance-mode-journal"]').trigger('click')
    const rows = wrapper.findAll('tbody tr')

    expect(wrapper.find('table thead').text()).toContain('Комментарий')
    expect(rows[0].text()).toContain('Ручная корректировка')
    expect(rows[1].text()).toContain('—')
  })
})
