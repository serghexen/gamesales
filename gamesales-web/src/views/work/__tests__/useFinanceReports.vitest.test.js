import { describe, it, expect, vi } from 'vitest'
import { reactive } from 'vue'

import { useFinanceReports } from '../useFinanceReports.js'

function createHarness() {
  const auth = { state: reactive({ token: 'token-1' }) }
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const apiPut = vi.fn()
  const apiDelete = vi.fn()
  const mapApiError = (v) => String(v || '')
  const finance = useFinanceReports({ auth, apiGet, apiPost, apiPut, apiDelete, mapApiError })
  return { auth, apiGet, apiPost, apiPut, apiDelete, finance }
}

describe('useFinanceReports', () => {
  it('sets current day as default sources report period', () => {
    const h = createHarness()
    const today = new Date().toISOString().slice(0, 10)

    expect(h.finance.financeFilters.date_from).toBe(today)
    expect(h.finance.financeFilters.date_to).toBe(today)
    expect(h.finance.financePlFilters.date_from).toBe(today)
    expect(h.finance.financePlFilters.date_to).toBe(today)
  })

  it('loads bootstrap catalogs for filters', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce({
      types: [{ type_id: 2, code: 'direct_expense', name: 'Прямые расходы' }],
      sections: [{ section_id: 1, code: 'revenue', name: 'Выручка', kind: 'revenue' }],
      projects: [{ project_id: 1, code: 'core', name: 'Core' }],
      regions: [{ region_id: 10, code: 'TR', name: 'Turkey' }],
      sources: [{ source_id: 99, code: 'ym', name: 'ASAT' }],
    })

    await h.finance.loadFinanceBootstrap()

    expect(h.apiGet).toHaveBeenCalledWith('/finance/catalogs/bootstrap', { token: 'token-1' })
    expect(h.finance.financeCatalogsLoaded.value).toBe(true)
    expect(h.finance.financeTypes.value).toHaveLength(1)
    expect(h.finance.financeSections.value).toHaveLength(1)
    expect(h.finance.financeProjects.value).toHaveLength(1)
    expect(h.finance.financeRegions.value).toHaveLength(1)
    expect(h.finance.financeSources.value).toHaveLength(1)
  })

  it('builds sources report query and fills totals', async () => {
    const h = createHarness()
    h.finance.financeFilters.date_from = '2026-05-01'
    h.finance.financeFilters.date_to = '2026-05-31'
    h.finance.financeFilters.region_id = [10, 11]
    h.finance.financeFilters.source_id = [99, 100]
    h.apiGet.mockResolvedValueOnce({
      totals: {
        revenue: '100.00',
        direct_expense: '50.00',
        indirect_expense: '10.00',
        gross_profit: '50.00',
        operating_profit: '40.00',
        margin: '0.4000',
      },
      items: [{ source_id: 99, source_name: 'ASAT', region_code: 'TR', cash_flow: '40.00' }],
    })

    await h.finance.loadFinanceProjectsReport()

    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/sources?date_from=2026-05-01&date_to=2026-05-31&region_id=10&region_id=11&source_id=99&source_id=100',
      { token: 'token-1' },
    )
    expect(h.finance.financeLoaded.value).toBe(true)
    expect(h.finance.financeReportTotals.revenue).toBe(100)
    expect(h.finance.financeReportTotals.operating_profit).toBe(40)
    expect(h.finance.financeReportItems.value).toHaveLength(1)
  })

  it('passes selected source report row types to query', async () => {
    const h = createHarness()
    h.finance.financeFilters.date_from = '2026-05-01'
    h.finance.financeFilters.date_to = '2026-05-31'
    h.finance.financeFilters.operation_code = ['sale', 'rental']
    h.apiGet.mockResolvedValueOnce({
      totals: { revenue: '150.00', direct_expense: '0.00', operating_profit: '150.00', margin: '1.0000' },
      items: [{ source_id: null, source_name: 'Без источника', operation_code: 'rental', operation_name: 'Шеринг', cash_flow: '150.00' }],
    })

    await h.finance.loadFinanceProjectsReport()

    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/sources?date_from=2026-05-01&date_to=2026-05-31&operation_code=sale&operation_code=rental',
      { token: 'token-1' },
    )
    expect(h.finance.financeReportItems.value[0]?.operation_code).toBe('rental')
  })

  it('loads source report detail rows for selected table line', async () => {
    const h = createHarness()
    h.finance.financeFilters.date_from = '2026-06-02'
    h.finance.financeFilters.date_to = '2026-06-02'
    h.apiGet.mockResolvedValueOnce({
      totals: {
        revenue: '35821.00',
        purchase_cost: '1660.00',
        direct_expense: '25840.00',
        operating_profit: '9981.00',
        margin: '0.2786',
      },
      items: [{ row_type: 'deal', deal_id: 16308, revenue: '5810.00', direct_expense: '4150.00' }],
    })

    const ok = await h.finance.loadFinanceSourceDetails({ source_id: null, region_id: 10 }, 'Услуга / TR')

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/sources/details?date_from=2026-06-02&date_to=2026-06-02&source_empty=1&region_id=10',
      { token: 'token-1' },
    )
    expect(h.finance.financeSourceDetailsOpen.value).toBe(true)
    expect(h.finance.financeSourceDetailsTitle.value).toBe('Услуга / TR')
    expect(h.finance.financeSourceDetailsTotals.purchase_cost).toBe(1660)
    expect(h.finance.financeSourceDetailsTotals.operating_profit).toBe(9981)
    expect(h.finance.financeSourceDetails.value[0]?.deal_id).toBe(16308)
  })

  it('passes operation and region code to source report details', async () => {
    const h = createHarness()
    h.finance.financeFilters.date_from = '2026-06-21'
    h.finance.financeFilters.date_to = '2026-06-21'
    h.apiGet.mockResolvedValueOnce({
      totals: { revenue: '0.00', purchase_cost: '0.00', direct_expense: '0.00', operating_profit: '0.00', margin: '0.0000' },
      items: [],
    })

    const ok = await h.finance.loadFinanceSourceDetails(
      { source_id: null, region_id: null, region_code: 'USA', operation_code: 'sale' },
      'Услуга / USA',
    )

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/sources/details?date_from=2026-06-21&date_to=2026-06-21&source_empty=1&region_code=USA&operation_code=sale',
      { token: 'token-1' },
    )
  })

  it('passes source code to source report details when finance source id is missing', async () => {
    const h = createHarness()
    h.finance.financeFilters.date_from = '2026-06-21'
    h.finance.financeFilters.date_to = '2026-06-21'
    h.apiGet.mockResolvedValueOnce({
      totals: { revenue: '0.00', purchase_cost: '0.00', direct_expense: '0.00', operating_profit: '0.00', margin: '0.0000' },
      items: [],
    })

    const ok = await h.finance.loadFinanceSourceDetails(
      { source_id: null, source_code: 'manual', region_id: null, region_code: 'USA', operation_code: 'sale' },
      'Manual / USA',
    )

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/sources/details?date_from=2026-06-21&date_to=2026-06-21&source_code=manual&region_code=USA&operation_code=sale',
      { token: 'token-1' },
    )
  })

  it('builds cash flow report query and fills line totals', async () => {
    const h = createHarness()
    h.finance.financeCashFlowFilters.date_from = '2026-06-10'
    h.finance.financeCashFlowFilters.date_to = '2026-06-20'
    h.apiGet.mockResolvedValueOnce({
      totals: {
        revenue: '20000.00',
        expense: '7000.00',
        cash_flow: '13000.00',
        opening_balance: '3000.00',
        current_balance: '16000.00',
        opening_balance_month: '2026-06-01',
        opening_balance_manual: true,
      },
      revenues: [{ name: 'Продажа TR', amount: '15000.00' }],
      expenses: [{ name: 'Закуп TR', amount: '7000.00' }],
    })

    await h.finance.loadFinanceCashFlowReport()

    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/cash-flow?date_from=2026-06-10&date_to=2026-06-20',
      { token: 'token-1' },
    )
    expect(h.finance.financeCashFlowLoaded.value).toBe(true)
    expect(h.finance.financeCashFlowLoading.value).toBe(false)
    expect(h.finance.financeLoading.value).toBe(false)
    expect(h.finance.financeCashFlowTotals.cash_flow).toBe(13000)
    expect(h.finance.financeCashFlowTotals.current_balance).toBe(16000)
    expect(h.finance.financeCashFlowOpeningDraft.value).toBe('3000.00')
    expect(h.finance.financeCashFlowRevenues.value[0]?.name).toBe('Продажа TR')
    expect(h.finance.financeCashFlowExpenses.value[0]?.name).toBe('Закуп TR')
  })

  it('loads cash flow details with date interval and selected line', async () => {
    const h = createHarness()
    h.finance.financeCashFlowDetailsFilters.date_from = '2026-06-10'
    h.finance.financeCashFlowDetailsFilters.date_to = '2026-06-20'
    h.apiGet.mockResolvedValueOnce({
      totals: {
        revenue: '5810.00',
        expense: '0.00',
        cash_flow: '5810.00',
      },
      items: [{ row_type: 'deal', line_type: 'revenue', line_name: 'Продажа TR', deal_id: 16308, amount: '5810.00' }],
    })

    const ok = await h.finance.loadFinanceCashFlowDetails({ line_type: 'revenue', name: 'Продажа TR' }, 'Поступление: Продажа TR')

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/cash-flow/details?date_from=2026-06-10&date_to=2026-06-20&line_type=revenue&line_name=%D0%9F%D1%80%D0%BE%D0%B4%D0%B0%D0%B6%D0%B0+TR',
      { token: 'token-1' },
    )
    expect(h.finance.financeCashFlowDetailsOpen.value).toBe(true)
    expect(h.finance.financeCashFlowDetailsTitle.value).toBe('Поступление: Продажа TR')
    expect(h.finance.financeCashFlowDetailsTotals.revenue).toBe(5810)
    expect(h.finance.financeCashFlowDetails.value[0]?.deal_id).toBe(16308)
  })

  it('passes selected source ids to marketplace cash flow details', async () => {
    const h = createHarness()
    h.finance.financeCashFlowDetailsFilters.date_from = '2026-06-10'
    h.finance.financeCashFlowDetailsFilters.date_to = '2026-06-20'
    h.finance.financeCashFlowDetailsFilters.source_id = [99, 100]
    h.apiGet.mockResolvedValueOnce({
      totals: { revenue: '100.00', expense: '0.00', cash_flow: '100.00' },
      items: [],
    })

    const ok = await h.finance.loadFinanceCashFlowDetails(
      { line_type: 'revenue', name: 'Продажи маркетплейсов (API)' },
      'Поступление: Продажи маркетплейсов (API)',
    )

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/cash-flow/details?date_from=2026-06-10&date_to=2026-06-20&line_type=revenue&line_name=%D0%9F%D1%80%D0%BE%D0%B4%D0%B0%D0%B6%D0%B8+%D0%BC%D0%B0%D1%80%D0%BA%D0%B5%D1%82%D0%BF%D0%BB%D0%B5%D0%B9%D1%81%D0%BE%D0%B2+%28API%29&source_id=99&source_id=100',
      { token: 'token-1' },
    )
  })

  it('allows cash flow report to be loaded repeatedly', async () => {
    const h = createHarness()
    h.apiGet
      .mockResolvedValueOnce({ totals: { cash_flow: '100.00' }, revenues: [], expenses: [] })
      .mockResolvedValueOnce({ totals: { cash_flow: '200.00' }, revenues: [], expenses: [] })

    await h.finance.loadFinanceCashFlowReport()
    await h.finance.loadFinanceCashFlowReport()

    expect(h.apiGet).toHaveBeenCalledTimes(2)
    expect(h.finance.financeCashFlowLoading.value).toBe(false)
    expect(h.finance.financeCashFlowTotals.cash_flow).toBe(200)
  })

  it('builds PL report from cash flow lines and grouped totals', async () => {
    const h = createHarness()
    h.finance.financePlFilters.date_from = '2026-06-10'
    h.finance.financePlFilters.date_to = '2026-06-20'
    h.apiGet.mockResolvedValueOnce({
      totals: {
        revenue: '20000.00',
        direct_expense: '6000.00',
        indirect_expense: '800.00',
        tax_expense: '200.00',
        gross_profit: '14000.00',
        operating_profit: '13200.00',
        net_profit: '13000.00',
      },
      revenues: [{ name: 'Продажа TR', amount: '20000.00' }],
      expenses: [
        { name: 'Закуп TR', amount: '6000.00', expense_kind: 'direct' },
        { name: 'Маркетинг', amount: '800.00', expense_kind: 'indirect' },
        { name: 'Налог УСН', amount: '200.00', expense_kind: 'tax' },
      ],
    })

    const ok = await h.finance.loadFinancePlReport()

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/reports/cash-flow?date_from=2026-06-10&date_to=2026-06-20',
      { token: 'token-1' },
    )
    expect(h.finance.financePlLoaded.value).toBe(true)
    expect(h.finance.financePlTotals.gross_profit).toBe(14000)
    expect(h.finance.financePlTotals.operating_profit).toBe(13200)
    expect(h.finance.financePlTotals.net_profit).toBe(13000)
    expect(h.finance.financePlDirectExpenses.value[0]?.name).toBe('Закуп TR')
    expect(h.finance.financePlIndirectExpenses.value[0]?.name).toBe('Маркетинг')
    expect(h.finance.financePlTaxExpenses.value[0]?.name).toBe('Налог УСН')
  })

  it('saves cash flow opening balance and reloads report', async () => {
    const h = createHarness()
    h.finance.financeCashFlowMonth.value = '2026-07'
    h.finance.financeCashFlowFilters.date_from = '2026-07-01'
    h.finance.financeCashFlowFilters.date_to = '2026-07-31'
    h.finance.financeCashFlowOpeningDraft.value = '12345.67'
    h.apiPut.mockResolvedValueOnce({ month: '2026-07-01', amount: '12345.67' })
    h.apiGet.mockResolvedValueOnce({ totals: { opening_balance: '12345.67' }, revenues: [], expenses: [] })

    const ok = await h.finance.saveFinanceCashFlowOpeningBalance()

    expect(ok).toBe(true)
    expect(h.apiPut).toHaveBeenCalledWith(
      '/finance/cash-flow/opening-balance',
      { month: '2026-07', amount: 12345.67 },
      { token: 'token-1' },
    )
    expect(h.apiGet).toHaveBeenCalledWith('/finance/reports/cash-flow?date_from=2026-07-01&date_to=2026-07-31', { token: 'token-1' })
    expect(h.finance.financeCashFlowOpeningOk.value).toBe('Начальный остаток сохранен')
  })

  it('loads TR card balance and prepares current balance draft', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce({
      card_code: 'TR',
      region_code: 'TR',
      currency: 'TRY',
      snapshot_balance: '25000.00',
      spent_after_snapshot: '6000.00',
      current_balance: '19000.00',
      snapshot_at: '2026-06-22T10:00:00+03:00',
      snapshot_manual: true,
      comment: 'manual',
    })

    const ok = await h.finance.loadFinanceTrCardBalance()

    expect(ok).toBe(true)
    expect(h.apiGet).toHaveBeenCalledWith('/finance/card-balances/tr', { token: 'token-1' })
    expect(h.finance.financeTrCardBalanceLoaded.value).toBe(true)
    expect(h.finance.financeTrCardBalance.current_balance).toBe(19000)
    expect(h.finance.financeTrCardBalance.spent_after_snapshot).toBe(6000)
    expect(h.finance.financeTrCardBalanceDraft.value).toBe('19000.00')
  })

  it('saves TR card balance as current factual snapshot', async () => {
    const h = createHarness()
    h.finance.financeTrCardBalanceDraft.value = '3456.78'
    h.apiPut.mockResolvedValueOnce({
      card_code: 'TR',
      region_code: 'TR',
      currency: 'TRY',
      snapshot_balance: '3456.78',
      spent_after_snapshot: '0.00',
      current_balance: '3456.78',
      snapshot_at: '2026-06-22T12:00:00+03:00',
      snapshot_manual: true,
    })

    const ok = await h.finance.saveFinanceTrCardBalance()

    expect(ok).toBe(true)
    expect(h.apiPut).toHaveBeenCalledWith(
      '/finance/card-balances/tr',
      { amount: 3456.78, comment: 'Ручная установка фактического баланса' },
      { token: 'token-1' },
    )
    expect(h.finance.financeTrCardBalance.current_balance).toBe(3456.78)
  })

  it('loads entries journal with filters', async () => {
    const h = createHarness()
    h.finance.financeEntryFilters.date_from = '2026-05-01'
    h.finance.financeEntryFilters.date_to = '2026-05-10'
    h.finance.financeEntryFilters.operation_id = 7
    h.apiGet.mockResolvedValueOnce({
      total: 1,
      items: [{ entry_id: 77, biz_date: '2026-05-10', operation_id: 7, amount: '100.00', qty: '1.00' }],
    })

    await h.finance.loadFinanceEntries()

    expect(h.apiGet).toHaveBeenCalledWith(
      '/finance/entries?input_channel=manual&date_from=2026-05-01&date_to=2026-05-10&operation_id=7',
      { token: 'token-1' },
    )
    expect(h.finance.financeEntriesLoaded.value).toBe(true)
    expect(h.finance.financeEntriesTotal.value).toBe(1)
    expect(h.finance.financeEntries.value[0]?.entry_id).toBe(77)
  })

  it('creates entry and refreshes journal and report', async () => {
    const h = createHarness()
    h.finance.financeNewEntry.biz_date = '2026-05-11'
    h.finance.financeNewEntry.operation_id = 9
    h.finance.financeNewEntry.region_id = 10
    h.finance.financeNewEntry.source_id = 99
    h.finance.financeNewEntry.amount = '555.70'
    h.finance.financeNewEntry.comment = 'manual add'
    h.apiPost.mockResolvedValueOnce({ entry_id: 700 })
    h.apiGet
      .mockResolvedValueOnce({ total: 1, items: [{ entry_id: 700, amount: '555.70', qty: '1.00' }] })
      .mockResolvedValueOnce({ totals: { revenue: '555.70' }, items: [] })

    const ok = await h.finance.createFinanceEntry()

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/entries',
      expect.objectContaining({
        biz_date: '2026-05-11',
        operation_id: 9,
        project_id: null,
        region_id: 10,
        source_id: 99,
        qty: 1,
        amount: 555.7,
        currency: 'RUB',
        comment: 'manual add',
      }),
      { token: 'token-1' },
    )
    expect(h.finance.financeEntryOk.value).toBe('Запись добавлена')
    expect(h.finance.financeNewEntry.amount).toBe('')
  })

  it('syncs Yandex Market entries and refreshes finance data', async () => {
    const h = createHarness()
    h.finance.financeYandexSync.date_from = '2026-06-01'
    h.finance.financeYandexSync.date_to = '2026-06-02'
    h.apiPost.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'queued',
      message: 'Синхронизация поставлена в очередь',
    })
    h.apiGet
      .mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'done',
        message: 'Синхронизация завершена',
        result: {
          total_rows: 3,
          created_rows: 2,
          updated_rows: 1,
          skipped_rows: 1,
          failed_rows: 0,
          errors: [],
        },
      })
      .mockResolvedValueOnce({ total: 2, items: [{ entry_id: 701, amount: '100.00', qty: '1.00' }] })
      .mockResolvedValueOnce({ totals: { revenue: '100.00' }, items: [] })

    const ok = await h.finance.syncFinanceYandexMarket()

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/integrations/yandex/sync',
      { store_code: 'asat', date_from: '2026-06-01', date_to: '2026-06-02' },
      { token: 'token-1' },
    )
    expect(h.finance.financeYandexSyncOk.value).toBe('Yandex: дней добавлено 2, дней обновлено 1, дней пропущено 1, ошибок 0')
    expect(h.finance.financeYandexSyncResult.value.created_rows).toBe(2)
    expect(h.finance.financeYandexSyncStatus.value).toBe('Синхронизация завершена')
    expect(h.apiGet).toHaveBeenCalledTimes(3)
  })

  it('syncs Wildberries entries and refreshes finance data', async () => {
    const h = createHarness()
    h.finance.financeWildberriesSync.store_code = 'sps'
    h.finance.financeWildberriesSync.date_from = '2026-06-01'
    h.finance.financeWildberriesSync.date_to = '2026-06-02'
    h.apiPost.mockResolvedValueOnce({
      job_id: 'wb-job-1',
      status: 'queued',
      message: 'Синхронизация поставлена в очередь',
    })
    h.apiGet
      .mockResolvedValueOnce({
        job_id: 'wb-job-1',
        status: 'done',
        message: 'Синхронизация завершена',
        result: {
          total_rows: 20,
          created_rows: 2,
          updated_rows: 0,
          skipped_rows: 1,
          failed_rows: 0,
          errors: [],
        },
      })
      .mockResolvedValueOnce({ total: 2, items: [{ entry_id: 801, amount: '100.00', qty: '1.00' }] })
      .mockResolvedValueOnce({ totals: { revenue: '100.00' }, items: [] })

    const ok = await h.finance.syncFinanceWildberries()

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/integrations/wildberries/sync',
      { store_code: 'sps', date_from: '2026-06-01', date_to: '2026-06-02' },
      { token: 'token-1' },
    )
    expect(h.finance.financeWildberriesSyncOk.value).toBe('Wildberries: дней добавлено 2, дней обновлено 0, дней пропущено 1, ошибок 0')
    expect(h.finance.financeWildberriesSyncResult.value.total_rows).toBe(20)
    expect(h.finance.financeWildberriesSyncStatus.value).toBe('Синхронизация завершена')
    expect(h.apiGet).toHaveBeenCalledTimes(3)
  })

  it('syncs Ozon entries and refreshes finance data', async () => {
    const h = createHarness()
    h.finance.financeOzonSync.store_code = 'asat'
    h.finance.financeOzonSync.date_from = '2026-06-01'
    h.finance.financeOzonSync.date_to = '2026-06-02'
    h.apiPost.mockResolvedValueOnce({
      job_id: 'ozon-job-1',
      status: 'queued',
      message: 'Синхронизация поставлена в очередь',
    })
    h.apiGet
      .mockResolvedValueOnce({
        job_id: 'ozon-job-1',
        status: 'done',
        message: 'Синхронизация завершена',
        result: {
          total_rows: 35,
          created_rows: 2,
          updated_rows: 1,
          skipped_rows: 0,
          failed_rows: 0,
          errors: [],
        },
      })
      .mockResolvedValueOnce({ total: 2, items: [{ entry_id: 901, amount: '100.00', qty: '1.00' }] })
      .mockResolvedValueOnce({ totals: { revenue: '100.00' }, items: [] })

    const ok = await h.finance.syncFinanceOzon()

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/integrations/ozon/sync',
      { store_code: 'asat', date_from: '2026-06-01', date_to: '2026-06-02' },
      { token: 'token-1' },
    )
    expect(h.finance.financeOzonSyncOk.value).toBe('Ozon: дней добавлено 2, дней обновлено 1, дней пропущено 0, ошибок 0')
    expect(h.finance.financeOzonSyncResult.value.total_rows).toBe(35)
    expect(h.finance.financeOzonSyncStatus.value).toBe('Синхронизация завершена')
    expect(h.apiGet).toHaveBeenCalledTimes(3)
  })

  it('counts down Wildberries retry delay after rate limit', async () => {
    vi.useFakeTimers()
    try {
      const h = createHarness()
      h.apiPost.mockResolvedValueOnce({
        job_id: 'wb-job-rate-limit',
        status: 'queued',
        message: 'Синхронизация поставлена в очередь',
      })
      h.apiGet.mockResolvedValueOnce({
        job_id: 'wb-job-rate-limit',
        status: 'failed',
        message: 'Синхронизация завершилась ошибкой',
        error: 'Лимит Wildberries Finance API. Повторите примерно через 3 сек.',
        retry_after_seconds: 3,
      })

      const resultPromise = h.finance.syncFinanceWildberries()
      await vi.runAllTicks()
      const result = await resultPromise

      expect(result).toBe(false)
      expect(h.finance.financeWildberriesCooldownSeconds.value).toBe(3)
      expect(h.finance.financeWildberriesSyncStatus.value).toBe('Повторный запуск будет доступен через 3 сек.')

      await vi.advanceTimersByTimeAsync(3000)

      expect(h.finance.financeWildberriesCooldownSeconds.value).toBe(0)
      expect(h.finance.financeWildberriesSyncStatus.value).toBe('Можно повторить синхронизацию')
    } finally {
      vi.useRealTimers()
    }
  })

  it('creates finance operation catalog record and reloads bootstrap', async () => {
    const h = createHarness()
    h.finance.financeNewOperation.type_id = 3
    h.finance.financeNewOperation.code = 'indirect_adv'
    h.finance.financeNewOperation.name = 'Продвижение'
    h.apiPost.mockResolvedValueOnce({ operation_id: 44 })
    h.apiGet.mockResolvedValueOnce({ operations: [{ operation_id: 44 }] })

    const ok = await h.finance.createFinanceOperation()

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/catalogs/operations',
      expect.objectContaining({ type_id: 3, code: 'indirect_adv', name: 'Продвижение' }),
      { token: 'token-1' },
    )
    expect(h.finance.financeCatalogOk.value).toBe('Операция добавлена')
  })

  it('creates finance type catalog record and reloads bootstrap', async () => {
    const h = createHarness()
    h.apiPost.mockResolvedValueOnce({ type_id: 12 })
    h.apiGet.mockResolvedValueOnce({ types: [{ type_id: 12, code: 'new_type' }] })

    const ok = await h.finance.createFinanceType({ code: 'new_type', name: 'Новый тип' })

    expect(ok).toBe(true)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/finance/catalogs/types',
      expect.objectContaining({ code: 'new_type', name: 'Новый тип' }),
      { token: 'token-1' },
    )
    expect(h.finance.financeCatalogOk.value).toBe('Тип добавлен')
  })

  it('deletes finance entry and refreshes journal/report', async () => {
    const h = createHarness()
    h.apiDelete.mockResolvedValueOnce({ ok: true })
    h.apiGet
      .mockResolvedValueOnce({ total: 0, items: [] })
      .mockResolvedValueOnce({ totals: { revenue: '0.00' }, items: [] })

    const ok = await h.finance.deleteFinanceEntry(77)

    expect(ok).toBe(true)
    expect(h.apiDelete).toHaveBeenCalledWith('/finance/entries/77', { token: 'token-1' })
  })

  it('archives operation and type with cascade_entries query when requested', async () => {
    const h = createHarness()
    h.apiDelete.mockResolvedValue({ ok: true })
    h.apiGet.mockResolvedValue({ operations: [], types: [] })

    const opOk = await h.finance.archiveFinanceOperation(44, { cascadeEntries: true })
    const typeOk = await h.finance.archiveFinanceType(12, { cascadeEntries: true })

    expect(opOk).toBe(true)
    expect(typeOk).toBe(true)
    expect(h.apiDelete).toHaveBeenNthCalledWith(
      1,
      '/finance/catalogs/operations/44?cascade_entries=1',
      { token: 'token-1' },
    )
    expect(h.apiDelete).toHaveBeenNthCalledWith(
      2,
      '/finance/catalogs/types/12?cascade_entries=1',
      { token: 'token-1' },
    )
  })
})
