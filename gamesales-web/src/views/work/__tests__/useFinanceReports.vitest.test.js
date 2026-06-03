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

  it('builds cash flow report query and fills line totals', async () => {
    const h = createHarness()
    h.finance.financeCashFlowMonth.value = '2026-06'
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
      '/finance/reports/cash-flow?month=2026-06',
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

  it('saves cash flow opening balance and reloads report', async () => {
    const h = createHarness()
    h.finance.financeCashFlowMonth.value = '2026-07'
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
    expect(h.apiGet).toHaveBeenCalledWith('/finance/reports/cash-flow?month=2026-07', { token: 'token-1' })
    expect(h.finance.financeCashFlowOpeningOk.value).toBe('Начальный остаток сохранен')
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
