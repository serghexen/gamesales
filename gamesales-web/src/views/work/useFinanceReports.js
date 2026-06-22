import { reactive, ref } from 'vue'

export function useFinanceReports({ auth, apiGet, apiPost, apiPut, apiDelete, mapApiError }) {
  const today = new Date().toISOString().slice(0, 10)
  const currentMonth = today.slice(0, 7)
  const financeFilters = reactive({
    date_from: today,
    date_to: today,
    region_id: [],
    source_id: [],
    project_id: '',
    split_by_source: false,
  })
  const financeNewEntry = reactive({
    biz_date: today,
    operation_id: '',
    project_id: '',
    region_id: '',
    source_id: '',
    qty: 1,
    amount: '',
    currency: 'RUB',
    comment: '',
  })
  const financeEntryFilters = reactive({
    date_from: '',
    date_to: '',
    project_id: '',
    region_id: '',
    source_id: '',
    operation_id: '',
  })
  const financeCashFlowDetailsFilters = reactive({
    date_from: '',
    date_to: '',
  })
  const financeYandexSync = reactive({
    store_code: 'asat',
    date_from: today,
    date_to: today,
  })
  const financeWildberriesSync = reactive({
    store_code: 'asat',
    date_from: today,
    date_to: today,
  })
  const financeOzonSync = reactive({
    store_code: 'asat',
    date_from: today,
    date_to: today,
  })
  const financeOperations = ref([])
  const financeTypes = ref([])
  const financeSections = ref([])
  const financeProjects = ref([])
  const financeRegions = ref([])
  const financeSources = ref([])
  const financeStatuses = ref([])
  const financeEntries = ref([])
  const financeEntriesTotal = ref(0)
  const financeReportTotals = reactive({
    revenue: 0,
    direct_expense: 0,
    indirect_expense: 0,
    gross_profit: 0,
    operating_profit: 0,
    margin: 0,
  })
  const financeReportItems = ref([])
  const financeSourceDetails = ref([])
  const financeSourceDetailsTotals = reactive({
    revenue: 0,
    purchase_cost: 0,
    direct_expense: 0,
    indirect_expense: 0,
    gross_profit: 0,
    operating_profit: 0,
    margin: 0,
  })
  const financeSourceDetailsTitle = ref('')
  const financeSourceDetailsOpen = ref(false)
  const financeCashFlowTotals = reactive({
    revenue: 0,
    expense: 0,
    cash_flow: 0,
    opening_balance: 0,
    current_balance: 0,
  })
  const financeTrCardBalance = reactive({
    card_code: 'TR',
    region_code: 'TR',
    currency: 'TRY',
    snapshot_balance: 0,
    spent_after_snapshot: 0,
    current_balance: 0,
    snapshot_at: '',
    snapshot_manual: false,
    comment: '',
  })
  const financeCashFlowMonth = ref(currentMonth)
  const financeCashFlowOpeningDraft = ref('')
  const financeTrCardBalanceDraft = ref('')
  const financeCashFlowRevenues = ref([])
  const financeCashFlowExpenses = ref([])
  const financeCashFlowDetails = ref([])
  const financeCashFlowDetailsTotals = reactive({
    revenue: 0,
    expense: 0,
    cash_flow: 0,
  })
  const financeCashFlowDetailsTitle = ref('')
  const financeCashFlowDetailsOpen = ref(false)
  const financeYandexSyncResult = ref(null)
  const financeYandexSyncStatus = ref('')
  const financeWildberriesSyncResult = ref(null)
  const financeWildberriesSyncStatus = ref('')
  const financeOzonSyncResult = ref(null)
  const financeOzonSyncStatus = ref('')
  const financeNewSection = reactive({
    type_id: '',
    code: '',
    name: '',
    sort_order: 100,
  })
  const financeNewType = reactive({
    code: '',
    name: '',
  })
  const financeNewOperation = reactive({
    type_id: '',
    source_id: '',
    code: '',
    name: '',
    input_mode: 'mixed',
    allows_negative: false,
  })
  const financeNewProject = reactive({
    code: '',
    name: '',
  })
  const financeCatalogsLoaded = ref(false)
  const financeLoaded = ref(false)
  const financeCashFlowLoaded = ref(false)
  const financeTrCardBalanceLoaded = ref(false)
  const financeEntriesLoaded = ref(false)
  const financeLoading = ref(false)
  const financeCashFlowLoading = ref(false)
  const financeCashFlowOpeningSaving = ref(false)
  const financeTrCardBalanceLoading = ref(false)
  const financeTrCardBalanceSaving = ref(false)
  const financeCashFlowDetailsLoading = ref(false)
  const financeEntriesLoading = ref(false)
  const financeEntrySaving = ref(false)
  const financeCatalogSaving = ref(false)
  const financeYandexSyncLoading = ref(false)
  const financeWildberriesSyncLoading = ref(false)
  const financeOzonSyncLoading = ref(false)
  const financeWildberriesWaitSeconds = ref(0)
  const financeWildberriesCooldownSeconds = ref(0)
  const financeWildberriesCooldownStoreCode = ref('')
  const financeOzonCooldownSeconds = ref(0)
  const financeOzonCooldownStoreCode = ref('')
  const financeSourceDetailsLoading = ref(false)
  const financeError = ref(null)
  const financeEntriesError = ref(null)
  const financeEntryError = ref(null)
  const financeCatalogError = ref(null)
  const financeCatalogOk = ref('')
  const financeEntryOk = ref('')
  const financeCashFlowOpeningOk = ref('')
  const financeTrCardBalanceError = ref(null)
  const financeYandexSyncError = ref(null)
  const financeYandexSyncOk = ref('')
  const financeWildberriesSyncError = ref(null)
  const financeWildberriesSyncOk = ref('')
  const financeOzonSyncError = ref(null)
  const financeOzonSyncOk = ref('')
  let financeWildberriesCooldownTimer = null
  let financeOzonCooldownTimer = null

  const getFinanceCashFlowMonthRange = (monthValue = financeCashFlowMonth.value) => {
    // Строим границы месяца для фильтра расшифровки, чтобы дата проводки совпадала с отчетным месяцем.
    const raw = String(monthValue || currentMonth).trim()
    const match = raw.match(/^(\d{4})-(\d{2})$/)
    const normalized = match ? raw : currentMonth
    const [year, month] = normalized.split('-').map((part) => Number(part))
    const lastDay = new Date(year, month, 0).getDate()
    return {
      date_from: `${normalized}-01`,
      date_to: `${normalized}-${String(lastDay).padStart(2, '0')}`,
    }
  }

  const startFinanceWildberriesCooldown = (seconds, storeCode = 'asat') => {
    // Показываем обратный отсчет лимита WB и автоматически разрешаем повторный запуск.
    const initialSeconds = Math.max(0, Math.ceil(Number(seconds) || 0))
    if (financeWildberriesCooldownTimer) clearInterval(financeWildberriesCooldownTimer)
    financeWildberriesCooldownSeconds.value = initialSeconds
    financeWildberriesCooldownStoreCode.value = initialSeconds ? String(storeCode || 'asat') : ''
    if (!initialSeconds) return
    financeWildberriesSyncStatus.value = `Повторный запуск будет доступен через ${initialSeconds} сек.`
    financeWildberriesCooldownTimer = setInterval(() => {
      financeWildberriesCooldownSeconds.value = Math.max(0, financeWildberriesCooldownSeconds.value - 1)
      if (financeWildberriesCooldownSeconds.value > 0) {
        financeWildberriesSyncStatus.value = `Повторный запуск будет доступен через ${financeWildberriesCooldownSeconds.value} сек.`
        return
      }
      clearInterval(financeWildberriesCooldownTimer)
      financeWildberriesCooldownTimer = null
      financeWildberriesCooldownStoreCode.value = ''
      financeWildberriesSyncStatus.value = 'Можно повторить синхронизацию'
    }, 1000)
  }

  const updateFinanceWildberriesProgress = (message) => {
    // Извлекаем секунды из статуса backend, чтобы кнопка показывала ожидание текущей задачи.
    financeWildberriesSyncStatus.value = String(message || '')
    const waitMatch = financeWildberriesSyncStatus.value.match(/(\d+)\s+сек/i)
    financeWildberriesWaitSeconds.value = waitMatch ? Number(waitMatch[1]) : 0
  }

  const startFinanceOzonCooldown = (seconds, storeCode = 'asat') => {
    // Показываем время до повторного запроса Ozon и разблокируем кнопку после лимита.
    const initialSeconds = Math.max(0, Math.ceil(Number(seconds) || 0))
    if (financeOzonCooldownTimer) clearInterval(financeOzonCooldownTimer)
    financeOzonCooldownSeconds.value = initialSeconds
    financeOzonCooldownStoreCode.value = initialSeconds ? String(storeCode || 'asat') : ''
    if (!initialSeconds) return
    financeOzonSyncStatus.value = `Повторный запуск будет доступен через ${initialSeconds} сек.`
    financeOzonCooldownTimer = setInterval(() => {
      financeOzonCooldownSeconds.value = Math.max(0, financeOzonCooldownSeconds.value - 1)
      if (financeOzonCooldownSeconds.value > 0) {
        financeOzonSyncStatus.value = `Повторный запуск будет доступен через ${financeOzonCooldownSeconds.value} сек.`
        return
      }
      clearInterval(financeOzonCooldownTimer)
      financeOzonCooldownTimer = null
      financeOzonCooldownStoreCode.value = ''
      financeOzonSyncStatus.value = 'Можно повторить синхронизацию'
    }, 1000)
  }

  const clearFinanceSourceDetails = () => {
    // Закрываем расшифровку и сбрасываем суммы, чтобы не показывать старую строку отчета.
    financeSourceDetails.value = []
    financeSourceDetailsTotals.revenue = 0
    financeSourceDetailsTotals.purchase_cost = 0
    financeSourceDetailsTotals.direct_expense = 0
    financeSourceDetailsTotals.indirect_expense = 0
    financeSourceDetailsTotals.gross_profit = 0
    financeSourceDetailsTotals.operating_profit = 0
    financeSourceDetailsTotals.margin = 0
    financeSourceDetailsTitle.value = ''
    financeSourceDetailsOpen.value = false
  }

  const clearFinanceReport = () => {
    // Сбрасываем отчет, чтобы не показывать устаревшие агрегаты при ошибке запроса.
    financeReportTotals.revenue = 0
    financeReportTotals.direct_expense = 0
    financeReportTotals.indirect_expense = 0
    financeReportTotals.gross_profit = 0
    financeReportTotals.operating_profit = 0
    financeReportTotals.margin = 0
    financeReportItems.value = []
  }

  const clearFinanceCashFlowDetails = () => {
    // Закрываем расшифровку Cash Flow и очищаем старые строки выбранной статьи.
    financeCashFlowDetails.value = []
    financeCashFlowDetailsTotals.revenue = 0
    financeCashFlowDetailsTotals.expense = 0
    financeCashFlowDetailsTotals.cash_flow = 0
    financeCashFlowDetailsTitle.value = ''
    financeCashFlowDetailsOpen.value = false
  }

  const clearFinanceCashFlowReport = () => {
    // Сбрасываем Cash Flow отдельно, чтобы вкладки отчетов не перетирали друг друга.
    financeCashFlowTotals.revenue = 0
    financeCashFlowTotals.expense = 0
    financeCashFlowTotals.cash_flow = 0
    financeCashFlowTotals.opening_balance = 0
    financeCashFlowTotals.current_balance = 0
    financeCashFlowRevenues.value = []
    financeCashFlowExpenses.value = []
    clearFinanceCashFlowDetails()
  }

  const applyFinanceTrCardBalance = (data) => {
    // Перекладываем ответ API в реактивный объект и готовим поле ручной установки.
    financeTrCardBalance.card_code = String(data?.card_code || 'TR')
    financeTrCardBalance.region_code = String(data?.region_code || 'TR')
    financeTrCardBalance.currency = String(data?.currency || 'TRY')
    financeTrCardBalance.snapshot_balance = Number(data?.snapshot_balance || 0)
    financeTrCardBalance.spent_after_snapshot = Number(data?.spent_after_snapshot || 0)
    financeTrCardBalance.current_balance = Number(data?.current_balance || 0)
    financeTrCardBalance.snapshot_at = String(data?.snapshot_at || '')
    financeTrCardBalance.snapshot_manual = Boolean(data?.snapshot_manual)
    financeTrCardBalance.comment = String(data?.comment || '')
    financeTrCardBalanceDraft.value = String(data?.current_balance ?? '')
  }

  const clearFinanceTrCardBalance = () => {
    // Сбрасываем виджет карты TR, чтобы после ошибки не оставался старый расчет.
    applyFinanceTrCardBalance({})
    financeTrCardBalanceLoaded.value = false
  }

  const loadFinanceBootstrap = async () => {
    // Подгружаем справочники finance для фильтров и селекторов отчета.
    financeError.value = null
    try {
      const data = await apiGet('/finance/catalogs/bootstrap', { token: auth.state.token })
      financeTypes.value = Array.isArray(data?.types) ? data.types : []
      financeOperations.value = Array.isArray(data?.operations) ? data.operations : []
      financeSections.value = Array.isArray(data?.sections) ? data.sections : []
      financeProjects.value = Array.isArray(data?.projects) ? data.projects : []
      financeRegions.value = Array.isArray(data?.regions) ? data.regions : []
      financeSources.value = Array.isArray(data?.sources) ? data.sources : []
      financeStatuses.value = Array.isArray(data?.statuses) ? data.statuses : []
      financeCatalogsLoaded.value = true
    } catch (e) {
      financeCatalogsLoaded.value = false
      financeError.value = mapApiError(e?.message)
    }
  }

  const loadFinanceEntries = async () => {
    // Загружаем только ручной журнал, чтобы интеграции не смешивались с вводом оператора.
    financeEntriesError.value = null
    financeEntriesLoading.value = true
    try {
      const params = new URLSearchParams()
      params.set('input_channel', 'manual')
      if (financeEntryFilters.date_from) params.set('date_from', financeEntryFilters.date_from)
      if (financeEntryFilters.date_to) params.set('date_to', financeEntryFilters.date_to)
      if (financeEntryFilters.region_id) params.set('region_id', String(financeEntryFilters.region_id))
      if (financeEntryFilters.source_id) params.set('source_id', String(financeEntryFilters.source_id))
      if (financeEntryFilters.operation_id) params.set('operation_id', String(financeEntryFilters.operation_id))

      const query = params.toString()
      const data = await apiGet(`/finance/entries${query ? `?${query}` : ''}`, { token: auth.state.token })
      financeEntries.value = Array.isArray(data?.items) ? data.items : []
      financeEntriesTotal.value = Number(data?.total || 0)
      financeEntriesLoaded.value = true
    } catch (e) {
      financeEntries.value = []
      financeEntriesTotal.value = 0
      financeEntriesLoaded.value = false
      financeEntriesError.value = mapApiError(e?.message)
    } finally {
      financeEntriesLoading.value = false
    }
  }

  const createFinanceEntry = async () => {
    // Создаем новую запись finance и после успеха обновляем журнал и отчет.
    financeEntryError.value = null
    financeEntryOk.value = ''
    if (typeof apiPost !== 'function') {
      financeEntryError.value = 'Функция apiPost не настроена'
      return false
    }
    if (!financeNewEntry.operation_id) {
      financeEntryError.value = 'Выберите операцию'
      return false
    }
    // Количество фиксируем как 1, потому что в форме сейчас вводится только сумма операции.
    const qty = 1
    const amount = Number(financeNewEntry.amount)
    if (!Number.isFinite(amount)) {
      financeEntryError.value = 'Укажите сумму'
      return false
    }
    financeEntrySaving.value = true
    try {
      const payload = {
        biz_date: financeNewEntry.biz_date || today,
        operation_id: Number(financeNewEntry.operation_id),
        project_id: null,
        region_id: financeNewEntry.region_id ? Number(financeNewEntry.region_id) : null,
        source_id: financeNewEntry.source_id ? Number(financeNewEntry.source_id) : null,
        qty,
        amount,
        currency: String(financeNewEntry.currency || 'RUB').toUpperCase(),
        input_channel: 'manual',
        external_key: `ui-${Date.now()}-${Math.floor(Math.random() * 100000)}`,
        comment: String(financeNewEntry.comment || '').trim() || null,
      }
      await apiPost('/finance/entries', payload, { token: auth.state.token })
      financeEntryOk.value = 'Запись добавлена'
      financeNewEntry.amount = ''
      financeNewEntry.comment = ''
      const refreshTasks = [loadFinanceEntries(), loadFinanceProjectsReport()]
      if (financeCashFlowLoaded.value) refreshTasks.push(loadFinanceCashFlowReport())
      await Promise.all(refreshTasks)
      return true
    } catch (e) {
      financeEntryError.value = mapApiError(e?.message)
      return false
    } finally {
      financeEntrySaving.value = false
    }
  }

  const deleteFinanceEntry = async (entryId) => {
    // Удаляем проводку и перечитываем журнал/отчет, чтобы экран сразу показал актуальные суммы.
    financeEntriesError.value = null
    if (!entryId) return false
    financeEntriesLoading.value = true
    try {
      await apiDelete(`/finance/entries/${Number(entryId)}`, { token: auth.state.token })
      const refreshTasks = [loadFinanceEntries(), loadFinanceProjectsReport()]
      if (financeCashFlowLoaded.value) refreshTasks.push(loadFinanceCashFlowReport())
      await Promise.all(refreshTasks)
      return true
    } catch (e) {
      financeEntriesError.value = mapApiError(e?.message)
      return false
    } finally {
      financeEntriesLoading.value = false
    }
  }

  const loadFinanceProjectsReport = async () => {
    // Загружаем отчет по источникам из завершенных сделок основной схемы app.
    financeError.value = null
    financeLoading.value = true
    try {
      const params = new URLSearchParams()
      const appendFilterIds = (key, value) => {
        // Передаем мультивыбор повторяющимися query-параметрами, чтобы backend получил список id.
        const values = Array.isArray(value) ? value : (value ? [value] : [])
        values
          .map((item) => Number(item))
          .filter((item) => Number.isFinite(item) && item > 0)
          .forEach((item) => params.append(key, String(item)))
      }
      if (financeFilters.date_from) params.set('date_from', financeFilters.date_from)
      if (financeFilters.date_to) params.set('date_to', financeFilters.date_to)
      appendFilterIds('region_id', financeFilters.region_id)
      appendFilterIds('source_id', financeFilters.source_id)

      const query = params.toString()
      const data = await apiGet(`/finance/reports/sources${query ? `?${query}` : ''}`, { token: auth.state.token })
      clearFinanceSourceDetails()
      financeReportTotals.revenue = Number(data?.totals?.revenue || 0)
      financeReportTotals.direct_expense = Number(data?.totals?.direct_expense || 0)
      financeReportTotals.indirect_expense = Number(data?.totals?.indirect_expense || 0)
      financeReportTotals.gross_profit = Number(data?.totals?.gross_profit || 0)
      financeReportTotals.operating_profit = Number(data?.totals?.operating_profit || 0)
      financeReportTotals.margin = Number(data?.totals?.margin || 0)
      financeReportItems.value = Array.isArray(data?.items) ? data.items : []
      financeLoaded.value = true
    } catch (e) {
      clearFinanceReport()
      financeLoaded.value = false
      financeError.value = mapApiError(e?.message)
    } finally {
      financeLoading.value = false
    }
  }

  const loadFinanceSourceDetails = async (row, title = '') => {
    // Загружаем расшифровку конкретной строки отчета: сделки и finance-проводки с теми же фильтрами.
    financeError.value = null
    financeSourceDetailsLoading.value = true
    financeSourceDetailsOpen.value = true
    financeSourceDetailsTitle.value = String(title || '').trim() || 'Расшифровка строки'
    try {
      const params = new URLSearchParams()
      if (financeFilters.date_from) params.set('date_from', financeFilters.date_from)
      if (financeFilters.date_to) params.set('date_to', financeFilters.date_to)
      const sourceId = Number(row?.source_id || 0)
      const regionId = Number(row?.region_id || 0)
      if (sourceId > 0) {
        params.set('source_id', String(sourceId))
      } else {
        params.set('source_empty', '1')
      }
      if (regionId > 0) {
        params.set('region_id', String(regionId))
      } else {
        params.set('region_empty', '1')
      }
      const query = params.toString()
      const data = await apiGet(`/finance/reports/sources/details${query ? `?${query}` : ''}`, { token: auth.state.token })
      financeSourceDetails.value = Array.isArray(data?.items) ? data.items : []
      financeSourceDetailsTotals.revenue = Number(data?.totals?.revenue || 0)
      financeSourceDetailsTotals.purchase_cost = Number(data?.totals?.purchase_cost || 0)
      financeSourceDetailsTotals.direct_expense = Number(data?.totals?.direct_expense || 0)
      financeSourceDetailsTotals.indirect_expense = Number(data?.totals?.indirect_expense || 0)
      financeSourceDetailsTotals.gross_profit = Number(data?.totals?.gross_profit || 0)
      financeSourceDetailsTotals.operating_profit = Number(data?.totals?.operating_profit || 0)
      financeSourceDetailsTotals.margin = Number(data?.totals?.margin || 0)
      return true
    } catch (e) {
      financeSourceDetails.value = []
      financeError.value = mapApiError(e?.message)
      return false
    } finally {
      financeSourceDetailsLoading.value = false
    }
  }

  const loadFinanceCashFlowReport = async () => {
    // Загружаем общий Cash Flow: поступления, расходы и остатки по выбранному периоду.
    financeError.value = null
    financeCashFlowLoading.value = true
    try {
      const params = new URLSearchParams()
      if (financeCashFlowMonth.value) params.set('month', String(financeCashFlowMonth.value))

      const query = params.toString()
      const data = await apiGet(`/finance/reports/cash-flow${query ? `?${query}` : ''}`, { token: auth.state.token })
      clearFinanceCashFlowDetails()
      financeCashFlowTotals.revenue = Number(data?.totals?.revenue || 0)
      financeCashFlowTotals.expense = Number(data?.totals?.expense || 0)
      financeCashFlowTotals.cash_flow = Number(data?.totals?.cash_flow || 0)
      financeCashFlowTotals.opening_balance = Number(data?.totals?.opening_balance || 0)
      financeCashFlowTotals.current_balance = Number(data?.totals?.current_balance || 0)
      financeCashFlowOpeningDraft.value = String(data?.totals?.opening_balance || '')
      financeCashFlowRevenues.value = Array.isArray(data?.revenues) ? data.revenues : []
      financeCashFlowExpenses.value = Array.isArray(data?.expenses) ? data.expenses : []
      financeCashFlowLoaded.value = true
    } catch (e) {
      clearFinanceCashFlowReport()
      financeCashFlowLoaded.value = false
      financeError.value = mapApiError(e?.message)
    } finally {
      financeCashFlowLoading.value = false
    }
  }

  const resetFinanceCashFlowDetailsPeriod = () => {
    // Возвращаем фильтр расшифровки к полному выбранному месяцу Cash Flow.
    const range = getFinanceCashFlowMonthRange()
    financeCashFlowDetailsFilters.date_from = range.date_from
    financeCashFlowDetailsFilters.date_to = range.date_to
  }

  const loadFinanceCashFlowDetails = async (line, title = '') => {
    // Загружаем строки выбранной статьи Cash Flow с фильтром по дате проводки.
    financeError.value = null
    financeCashFlowDetailsLoading.value = true
    financeCashFlowDetailsOpen.value = true
    financeCashFlowDetailsTitle.value = String(title || '').trim() || 'Расшифровка Cash Flow'
    try {
      const params = new URLSearchParams()
      if (!financeCashFlowDetailsFilters.date_from || !financeCashFlowDetailsFilters.date_to) {
        resetFinanceCashFlowDetailsPeriod()
      }
      if (financeCashFlowDetailsFilters.date_from) params.set('date_from', financeCashFlowDetailsFilters.date_from)
      if (financeCashFlowDetailsFilters.date_to) params.set('date_to', financeCashFlowDetailsFilters.date_to)
      if (line?.line_type) params.set('line_type', String(line.line_type))
      if (line?.name) params.set('line_name', String(line.name))
      const query = params.toString()
      const data = await apiGet(`/finance/reports/cash-flow/details${query ? `?${query}` : ''}`, { token: auth.state.token })
      financeCashFlowDetails.value = Array.isArray(data?.items) ? data.items : []
      financeCashFlowDetailsTotals.revenue = Number(data?.totals?.revenue || 0)
      financeCashFlowDetailsTotals.expense = Number(data?.totals?.expense || 0)
      financeCashFlowDetailsTotals.cash_flow = Number(data?.totals?.cash_flow || 0)
      return true
    } catch (e) {
      financeCashFlowDetails.value = []
      financeError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCashFlowDetailsLoading.value = false
    }
  }

  const saveFinanceCashFlowOpeningBalance = async () => {
    // Сохраняем ручной начальный остаток для выбранного месяца и сразу перестраиваем отчет.
    financeError.value = null
    financeCashFlowOpeningOk.value = ''
    const month = String(financeCashFlowMonth.value || '').trim()
    const amount = Number(financeCashFlowOpeningDraft.value)
    if (!month) {
      financeError.value = 'Выберите месяц'
      return false
    }
    if (!Number.isFinite(amount)) {
      financeError.value = 'Укажите начальный остаток'
      return false
    }
    financeCashFlowOpeningSaving.value = true
    try {
      await apiPut('/finance/cash-flow/opening-balance', {
        month,
        amount,
      }, { token: auth.state.token })
      financeCashFlowOpeningOk.value = 'Начальный остаток сохранен'
      await loadFinanceCashFlowReport()
      return true
    } catch (e) {
      financeError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCashFlowOpeningSaving.value = false
    }
  }

  const loadFinanceTrCardBalance = async () => {
    // Загружаем расчетный остаток TR-карты от последнего ручного снимка.
    financeTrCardBalanceError.value = null
    financeTrCardBalanceLoading.value = true
    try {
      const data = await apiGet('/finance/card-balances/tr', { token: auth.state.token })
      applyFinanceTrCardBalance(data)
      financeTrCardBalanceLoaded.value = true
      return true
    } catch (e) {
      clearFinanceTrCardBalance()
      financeTrCardBalanceError.value = mapApiError(e?.message)
      return false
    } finally {
      financeTrCardBalanceLoading.value = false
    }
  }

  const saveFinanceTrCardBalance = async () => {
    // Сохраняем фактический остаток карты сейчас и сразу перечитываем расчет списаний.
    financeTrCardBalanceError.value = null
    const amount = Number(financeTrCardBalanceDraft.value)
    if (!Number.isFinite(amount)) {
      financeTrCardBalanceError.value = 'Укажите баланс TR-карты'
      return false
    }
    financeTrCardBalanceSaving.value = true
    try {
      const data = await apiPut('/finance/card-balances/tr', {
        amount,
        comment: 'Ручная установка фактического баланса',
      }, { token: auth.state.token })
      applyFinanceTrCardBalance(data)
      financeTrCardBalanceLoaded.value = true
      return true
    } catch (e) {
      financeTrCardBalanceError.value = mapApiError(e?.message)
      return false
    } finally {
      financeTrCardBalanceSaving.value = false
    }
  }

  const syncFinanceYandexMarket = async () => {
    // Запускаем ручную загрузку экономики заказов Яндекса за выбранный период.
    financeYandexSyncError.value = null
    financeYandexSyncOk.value = ''
    financeYandexSyncResult.value = null
    financeYandexSyncStatus.value = ''
    const dateFrom = String(financeYandexSync.date_from || '').trim()
    const dateTo = String(financeYandexSync.date_to || '').trim()
    const storeCode = String(financeYandexSync.store_code || 'asat').trim().toLowerCase()
    if (!dateFrom || !dateTo) {
      financeYandexSyncError.value = 'Выберите период синхронизации'
      return false
    }
    if (dateTo < dateFrom) {
      financeYandexSyncError.value = 'Дата окончания должна быть не раньше даты начала'
      return false
    }
    financeYandexSyncLoading.value = true
    try {
      const started = await apiPost('/finance/integrations/yandex/sync', {
        store_code: storeCode,
        date_from: dateFrom,
        date_to: dateTo,
      }, { token: auth.state.token })
      const jobId = String(started?.job_id || '')
      if (!jobId) throw new Error('Yandex sync job_id is missing')
      financeYandexSyncStatus.value = started?.message || 'Синхронизация запущена'
      let job = started
      for (let attempt = 0; attempt < 180; attempt += 1) {
        if (job?.status === 'done' || job?.status === 'failed') break
        job = await apiGet(`/finance/integrations/yandex/sync/${encodeURIComponent(jobId)}`, { token: auth.state.token })
        financeYandexSyncStatus.value = job?.message || String(job?.status || '')
        if (job?.status === 'done' || job?.status === 'failed') break
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      if (job?.status !== 'done') {
        throw new Error(job?.error || 'Yandex sync job was not completed')
      }
      const result = job?.result || {}
      financeYandexSyncResult.value = result || null
      const created = Number(result?.created_rows || 0)
      const updated = Number(result?.updated_rows || 0)
      const skipped = Number(result?.skipped_rows || 0)
      const failed = Number(result?.failed_rows || 0)
      financeYandexSyncOk.value = `Yandex: дней добавлено ${created}, дней обновлено ${updated}, дней пропущено ${skipped}, ошибок ${failed}`
      const refreshTasks = [loadFinanceEntries(), loadFinanceProjectsReport()]
      if (financeCashFlowLoaded.value) refreshTasks.push(loadFinanceCashFlowReport())
      await Promise.all(refreshTasks)
      return failed === 0
    } catch (e) {
      financeYandexSyncError.value = mapApiError(e?.message)
      return false
    } finally {
      financeYandexSyncLoading.value = false
    }
  }

  const syncFinanceWildberries = async () => {
    // Запускаем ручную загрузку финансового отчета WB и обновляем отчеты после завершения.
    const storeCode = String(financeWildberriesSync.store_code || 'asat').trim().toLowerCase()
    if (financeWildberriesCooldownSeconds.value > 0 && financeWildberriesCooldownStoreCode.value === storeCode) return false
    financeWildberriesSyncError.value = null
    financeWildberriesSyncOk.value = ''
    financeWildberriesSyncResult.value = null
    financeWildberriesSyncStatus.value = ''
    financeWildberriesWaitSeconds.value = 0
    const dateFrom = String(financeWildberriesSync.date_from || '').trim()
    const dateTo = String(financeWildberriesSync.date_to || '').trim()
    if (!dateFrom || !dateTo) {
      financeWildberriesSyncError.value = 'Выберите период синхронизации'
      return false
    }
    if (dateTo < dateFrom) {
      financeWildberriesSyncError.value = 'Дата окончания должна быть не раньше даты начала'
      return false
    }
    financeWildberriesSyncLoading.value = true
    try {
      const started = await apiPost('/finance/integrations/wildberries/sync', {
        store_code: storeCode,
        date_from: dateFrom,
        date_to: dateTo,
      }, { token: auth.state.token })
      const jobId = String(started?.job_id || '')
      if (!jobId) throw new Error('Wildberries sync job_id is missing')
      updateFinanceWildberriesProgress(started?.message || 'Синхронизация запущена')
      let job = started
      for (let attempt = 0; attempt < 180; attempt += 1) {
        if (job?.status === 'done' || job?.status === 'failed') break
        job = await apiGet(`/finance/integrations/wildberries/sync/${encodeURIComponent(jobId)}`, { token: auth.state.token })
        updateFinanceWildberriesProgress(job?.message || String(job?.status || ''))
        if (job?.status === 'done' || job?.status === 'failed') break
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      if (job?.status !== 'done') {
        startFinanceWildberriesCooldown(job?.retry_after_seconds, storeCode)
        throw new Error(job?.error || 'Wildberries sync job was not completed')
      }
      const result = job?.result || {}
      financeWildberriesWaitSeconds.value = 0
      financeWildberriesSyncResult.value = result || null
      const created = Number(result?.created_rows || 0)
      const updated = Number(result?.updated_rows || 0)
      const skipped = Number(result?.skipped_rows || 0)
      const failed = Number(result?.failed_rows || 0)
      financeWildberriesSyncOk.value = `Wildberries: дней добавлено ${created}, дней обновлено ${updated}, дней пропущено ${skipped}, ошибок ${failed}`
      const refreshTasks = [loadFinanceEntries(), loadFinanceProjectsReport()]
      if (financeCashFlowLoaded.value) refreshTasks.push(loadFinanceCashFlowReport())
      await Promise.all(refreshTasks)
      return failed === 0
    } catch (e) {
      const errorMessage = mapApiError(e?.message)
      financeWildberriesSyncError.value = errorMessage
      const retryMatch = String(errorMessage).match(/через\s+(\d+)\s+сек/i)
      if (retryMatch && financeWildberriesCooldownSeconds.value <= 0) {
        startFinanceWildberriesCooldown(Number(retryMatch[1]), storeCode)
      }
      return false
    } finally {
      financeWildberriesSyncLoading.value = false
      financeWildberriesWaitSeconds.value = 0
    }
  }

  const syncFinanceOzon = async () => {
    // Запускаем ручную загрузку финансовых операций Ozon и обновляем отчеты после завершения.
    const storeCode = String(financeOzonSync.store_code || 'asat').trim().toLowerCase()
    if (financeOzonCooldownSeconds.value > 0 && financeOzonCooldownStoreCode.value === storeCode) return false
    financeOzonSyncError.value = null
    financeOzonSyncOk.value = ''
    financeOzonSyncResult.value = null
    financeOzonSyncStatus.value = ''
    const dateFrom = String(financeOzonSync.date_from || '').trim()
    const dateTo = String(financeOzonSync.date_to || '').trim()
    if (!dateFrom || !dateTo) {
      financeOzonSyncError.value = 'Выберите период синхронизации'
      return false
    }
    if (dateTo < dateFrom) {
      financeOzonSyncError.value = 'Дата окончания должна быть не раньше даты начала'
      return false
    }
    financeOzonSyncLoading.value = true
    try {
      const started = await apiPost('/finance/integrations/ozon/sync', {
        store_code: storeCode,
        date_from: dateFrom,
        date_to: dateTo,
      }, { token: auth.state.token })
      const jobId = String(started?.job_id || '')
      if (!jobId) throw new Error('Ozon sync job_id is missing')
      financeOzonSyncStatus.value = started?.message || 'Синхронизация запущена'
      let job = started
      for (let attempt = 0; attempt < 180; attempt += 1) {
        if (job?.status === 'done' || job?.status === 'failed') break
        job = await apiGet(`/finance/integrations/ozon/sync/${encodeURIComponent(jobId)}`, { token: auth.state.token })
        financeOzonSyncStatus.value = job?.message || String(job?.status || '')
        if (job?.status === 'done' || job?.status === 'failed') break
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      if (job?.status !== 'done') {
        startFinanceOzonCooldown(job?.retry_after_seconds, storeCode)
        throw new Error(job?.error || 'Ozon sync job was not completed')
      }
      const result = job?.result || {}
      financeOzonSyncResult.value = result || null
      const created = Number(result?.created_rows || 0)
      const updated = Number(result?.updated_rows || 0)
      const skipped = Number(result?.skipped_rows || 0)
      const failed = Number(result?.failed_rows || 0)
      financeOzonSyncOk.value = `Ozon: дней добавлено ${created}, дней обновлено ${updated}, дней пропущено ${skipped}, ошибок ${failed}`
      const refreshTasks = [loadFinanceEntries(), loadFinanceProjectsReport()]
      if (financeCashFlowLoaded.value) refreshTasks.push(loadFinanceCashFlowReport())
      await Promise.all(refreshTasks)
      return failed === 0
    } catch (e) {
      const errorMessage = mapApiError(e?.message)
      financeOzonSyncError.value = errorMessage
      const retryMatch = String(errorMessage).match(/через\s+(\d+)\s+сек/i)
      if (retryMatch && financeOzonCooldownSeconds.value <= 0) {
        startFinanceOzonCooldown(Number(retryMatch[1]), storeCode)
      }
      return false
    } finally {
      financeOzonSyncLoading.value = false
    }
  }

  const createFinanceSection = async (draft = null) => {
    // Добавляем новый раздел в справочник finance и обновляем bootstrap.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const source = draft || financeNewSection
    const typeId = Number(source.type_id || 0)
    const code = String(source.code || '').trim().toLowerCase()
    const name = String(source.name || '').trim()
    if (!typeId || !code || !name) {
      financeCatalogError.value = 'Для раздела нужны тип, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPost('/finance/catalogs/sections', {
        type_id: typeId,
        code,
        name,
        sort_order: Number(source.sort_order || 100),
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Раздел добавлен'
      if (!draft) {
        financeNewSection.code = ''
        financeNewSection.name = ''
        financeNewSection.type_id = ''
      }
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const createFinanceType = async (draft = null) => {
    // Добавляем новый тип P&L для разделов и операций.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const source = draft || financeNewType
    const code = String(source.code || '').trim().toLowerCase()
    const name = String(source.name || '').trim()
    if (!code || !name) {
      financeCatalogError.value = 'Для типа нужны код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPost('/finance/catalogs/types', {
        code,
        name,
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Тип добавлен'
      if (!draft) {
        financeNewType.code = ''
        financeNewType.name = ''
      }
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const updateFinanceType = async (typeId, draft) => {
    // Обновляем тип P&L и перечитываем справочники.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const code = String(draft?.code || '').trim().toLowerCase()
    const name = String(draft?.name || '').trim()
    if (!typeId || !code || !name) {
      financeCatalogError.value = 'Для типа нужны id, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPut(`/finance/catalogs/types/${Number(typeId)}`, {
        code,
        name,
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Тип обновлен'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const archiveFinanceType = async (typeId, options = null) => {
    // Архивируем тип; по флагу можно каскадно удалить проводки по операциям типа.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!typeId) return false
    const cascadeEntries = Boolean(options?.cascadeEntries)
    const suffix = cascadeEntries ? '?cascade_entries=1' : ''
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/types/${Number(typeId)}${suffix}`, { token: auth.state.token })
      financeCatalogOk.value = cascadeEntries ? 'Тип удален вместе с проводками' : 'Тип архивирован'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const archiveFinanceSection = async (sectionId) => {
    // Архивируем раздел, если нет активных дочерних сущностей.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!sectionId) return false
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/sections/${Number(sectionId)}`, { token: auth.state.token })
      financeCatalogOk.value = 'Раздел архивирован'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const updateFinanceSection = async (sectionId, draft) => {
    // Обновляем раздел справочника finance и перечитываем справочники.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const code = String(draft?.code || '').trim().toLowerCase()
    const name = String(draft?.name || '').trim()
    const typeId = Number(draft?.type_id || 0)
    if (!sectionId || !typeId || !code || !name) {
      financeCatalogError.value = 'Для раздела нужны id, тип, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPut(`/finance/catalogs/sections/${Number(sectionId)}`, {
        type_id: typeId,
        code,
        name,
        sort_order: Number(draft?.sort_order || 100),
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Раздел обновлен'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const createFinanceOperation = async (draft = null) => {
    // Добавляем операцию (статью) в выбранный тип.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const source = draft || financeNewOperation
    const typeId = Number(source.type_id || 0)
    const code = String(source.code || '').trim().toLowerCase()
    const name = String(source.name || '').trim()
    if (!typeId || !code || !name) {
      financeCatalogError.value = 'Для операции нужны тип, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPost('/finance/catalogs/operations', {
        type_id: typeId,
        source_id: source.source_id ? Number(source.source_id) : null,
        code,
        name,
        input_mode: String(source.input_mode || 'mixed'),
        requires_region: false,
        requires_source: false,
        requires_project: false,
        requires_qty: false,
        allows_negative: Boolean(source.allows_negative),
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Операция добавлена'
      if (!draft) {
        financeNewOperation.code = ''
        financeNewOperation.name = ''
      }
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const archiveFinanceOperation = async (operationId, options = null) => {
    // Архивируем операцию; по флагу можно каскадно удалить ее проводки.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!operationId) return false
    const cascadeEntries = Boolean(options?.cascadeEntries)
    const suffix = cascadeEntries ? '?cascade_entries=1' : ''
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/operations/${Number(operationId)}${suffix}`, { token: auth.state.token })
      financeCatalogOk.value = cascadeEntries ? 'Операция удалена вместе с проводками' : 'Операция архивирована'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const updateFinanceOperation = async (operationId, draft) => {
    // Обновляем операцию справочника finance с правилами обязательных полей.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const typeId = Number(draft?.type_id || 0)
    const code = String(draft?.code || '').trim().toLowerCase()
    const name = String(draft?.name || '').trim()
    if (!operationId || !typeId || !code || !name) {
      financeCatalogError.value = 'Для операции нужны id, тип, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPut(`/finance/catalogs/operations/${Number(operationId)}`, {
        type_id: typeId,
        source_id: draft?.source_id ? Number(draft.source_id) : null,
        code,
        name,
        input_mode: String(draft?.input_mode || 'mixed'),
        requires_region: false,
        requires_source: false,
        requires_project: false,
        requires_qty: false,
        allows_negative: Boolean(draft?.allows_negative),
      }, { token: auth.state.token })
      financeCatalogOk.value = 'Операция обновлена'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const createFinanceProject = async (draft = null) => {
    // Добавляем проект в справочник для разрезов отчета.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const source = draft || financeNewProject
    const code = String(source.code || '').trim().toLowerCase()
    const name = String(source.name || '').trim()
    if (!code || !name) {
      financeCatalogError.value = 'Заполните код и название проекта'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPost('/finance/catalogs/projects', { code, name }, { token: auth.state.token })
      financeCatalogOk.value = 'Проект добавлен'
      if (!draft) {
        financeNewProject.code = ''
        financeNewProject.name = ''
      }
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const archiveFinanceProject = async (projectId) => {
    // Архивируем проект, если на него нет финансовых проводок.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!projectId) return false
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/projects/${Number(projectId)}`, { token: auth.state.token })
      financeCatalogOk.value = 'Проект архивирован'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  const updateFinanceProject = async (projectId, draft) => {
    // Обновляем проект finance для последующего использования в отчетах.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const code = String(draft?.code || '').trim().toLowerCase()
    const name = String(draft?.name || '').trim()
    if (!projectId || !code || !name) {
      financeCatalogError.value = 'Для проекта нужны id, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPut(`/finance/catalogs/projects/${Number(projectId)}`, { code, name }, { token: auth.state.token })
      financeCatalogOk.value = 'Проект обновлен'
      await loadFinanceBootstrap()
      return true
    } catch (e) {
      financeCatalogError.value = mapApiError(e?.message)
      return false
    } finally {
      financeCatalogSaving.value = false
    }
  }

  return {
    financeFilters,
    financeNewEntry,
    financeEntryFilters,
    financeCashFlowDetailsFilters,
    financeYandexSync,
    financeWildberriesSync,
    financeOzonSync,
    financeNewSection,
    financeNewType,
    financeNewOperation,
    financeNewProject,
    financeOperations,
    financeTypes,
    financeSections,
    financeProjects,
    financeRegions,
    financeSources,
    financeStatuses,
    financeEntries,
    financeEntriesTotal,
    financeReportTotals,
    financeReportItems,
    financeSourceDetails,
    financeSourceDetailsTotals,
    financeSourceDetailsTitle,
    financeSourceDetailsOpen,
    financeCashFlowTotals,
    financeTrCardBalance,
    financeCashFlowMonth,
    financeCashFlowOpeningDraft,
    financeTrCardBalanceDraft,
    financeCashFlowRevenues,
    financeCashFlowExpenses,
    financeCashFlowDetails,
    financeCashFlowDetailsTotals,
    financeCashFlowDetailsTitle,
    financeCashFlowDetailsOpen,
    financeYandexSyncResult,
    financeYandexSyncStatus,
    financeWildberriesSyncResult,
    financeWildberriesSyncStatus,
    financeOzonSyncResult,
    financeOzonSyncStatus,
    financeCatalogsLoaded,
    financeLoaded,
    financeCashFlowLoaded,
    financeTrCardBalanceLoaded,
    financeEntriesLoaded,
    financeLoading,
    financeCashFlowLoading,
    financeCashFlowOpeningSaving,
    financeTrCardBalanceLoading,
    financeTrCardBalanceSaving,
    financeCashFlowDetailsLoading,
    financeEntriesLoading,
    financeEntrySaving,
    financeCatalogSaving,
    financeYandexSyncLoading,
    financeWildberriesSyncLoading,
    financeOzonSyncLoading,
    financeWildberriesWaitSeconds,
    financeWildberriesCooldownSeconds,
    financeWildberriesCooldownStoreCode,
    financeOzonCooldownSeconds,
    financeOzonCooldownStoreCode,
    financeSourceDetailsLoading,
    financeError,
    financeEntriesError,
    financeEntryError,
    financeCatalogError,
    financeCatalogOk,
    financeEntryOk,
    financeCashFlowOpeningOk,
    financeTrCardBalanceError,
    financeYandexSyncError,
    financeYandexSyncOk,
    financeWildberriesSyncError,
    financeWildberriesSyncOk,
    financeOzonSyncError,
    financeOzonSyncOk,
    loadFinanceBootstrap,
    loadFinanceEntries,
    createFinanceEntry,
    deleteFinanceEntry,
    createFinanceSection,
    createFinanceType,
    updateFinanceType,
    archiveFinanceType,
    archiveFinanceSection,
    updateFinanceSection,
    createFinanceOperation,
    archiveFinanceOperation,
    updateFinanceOperation,
    createFinanceProject,
    archiveFinanceProject,
    updateFinanceProject,
    loadFinanceProjectsReport,
    loadFinanceSourceDetails,
    clearFinanceSourceDetails,
    loadFinanceCashFlowReport,
    loadFinanceCashFlowDetails,
    clearFinanceCashFlowDetails,
    resetFinanceCashFlowDetailsPeriod,
    saveFinanceCashFlowOpeningBalance,
    loadFinanceTrCardBalance,
    saveFinanceTrCardBalance,
    syncFinanceYandexMarket,
    syncFinanceWildberries,
    syncFinanceOzon,
  }
}
