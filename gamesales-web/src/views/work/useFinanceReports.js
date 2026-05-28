import { reactive, ref } from 'vue'

export function useFinanceReports({ auth, apiGet, apiPost, apiPut, apiDelete, mapApiError }) {
  const today = new Date().toISOString().slice(0, 10)
  const financeFilters = reactive({
    date_from: '',
    date_to: '',
    region_id: '',
    source_id: '',
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
    status_code: '',
    limit: 50,
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
  const financeNewSection = reactive({
    type_id: '',
    code: '',
    name: '',
    sort_order: 100,
  })
  const financeNewType = reactive({
    code: '',
    name: '',
    sort_order: 100,
  })
  const financeNewOperation = reactive({
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
  })
  const financeNewProject = reactive({
    code: '',
    name: '',
  })
  const financeCatalogsLoaded = ref(false)
  const financeLoaded = ref(false)
  const financeEntriesLoaded = ref(false)
  const financeLoading = ref(false)
  const financeEntriesLoading = ref(false)
  const financeEntrySaving = ref(false)
  const financeCatalogSaving = ref(false)
  const financeError = ref(null)
  const financeEntriesError = ref(null)
  const financeEntryError = ref(null)
  const financeCatalogError = ref(null)
  const financeCatalogOk = ref('')
  const financeEntryOk = ref('')

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
    // Загружаем журнал первичных записей finance для оперативного контроля ввода.
    financeEntriesError.value = null
    financeEntriesLoading.value = true
    try {
      const params = new URLSearchParams()
      if (financeEntryFilters.date_from) params.set('date_from', financeEntryFilters.date_from)
      if (financeEntryFilters.date_to) params.set('date_to', financeEntryFilters.date_to)
      if (financeEntryFilters.project_id) params.set('project_id', String(financeEntryFilters.project_id))
      if (financeEntryFilters.region_id) params.set('region_id', String(financeEntryFilters.region_id))
      if (financeEntryFilters.source_id) params.set('source_id', String(financeEntryFilters.source_id))
      if (financeEntryFilters.operation_id) params.set('operation_id', String(financeEntryFilters.operation_id))
      if (financeEntryFilters.status_code) params.set('status_code', String(financeEntryFilters.status_code))
      params.set('limit', String(financeEntryFilters.limit || 50))

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
    const qty = Number(financeNewEntry.qty || 1)
    if (!Number.isFinite(qty) || qty === 0) {
      financeEntryError.value = 'Укажите корректное количество'
      return false
    }
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
        project_id: financeNewEntry.project_id ? Number(financeNewEntry.project_id) : null,
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
      await Promise.all([loadFinanceEntries(), loadFinanceProjectsReport()])
      return true
    } catch (e) {
      financeEntryError.value = mapApiError(e?.message)
      return false
    } finally {
      financeEntrySaving.value = false
    }
  }

  const loadFinanceProjectsReport = async () => {
    // Загружаем отчет по проектам с фильтрами и режимом разреза по источнику.
    financeError.value = null
    financeLoading.value = true
    try {
      const params = new URLSearchParams()
      if (financeFilters.date_from) params.set('date_from', financeFilters.date_from)
      if (financeFilters.date_to) params.set('date_to', financeFilters.date_to)
      if (financeFilters.region_id) params.set('region_id', String(financeFilters.region_id))
      if (financeFilters.source_id) params.set('source_id', String(financeFilters.source_id))
      if (financeFilters.project_id) params.set('project_id', String(financeFilters.project_id))
      params.set('split_by_source', financeFilters.split_by_source ? 'true' : 'false')

      const query = params.toString()
      const data = await apiGet(`/finance/reports/projects${query ? `?${query}` : ''}`, { token: auth.state.token })
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
        sort_order: Number(source.sort_order || 100),
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
        sort_order: Number(draft?.sort_order || 100),
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

  const archiveFinanceType = async (typeId) => {
    // Архивируем тип, если к нему не привязаны активные разделы.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!typeId) return false
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/types/${Number(typeId)}`, { token: auth.state.token })
      financeCatalogOk.value = 'Тип архивирован'
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
    // Добавляем операцию (статью) в выбранный раздел.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    const source = draft || financeNewOperation
    const sectionId = Number(source.section_id || 0)
    const code = String(source.code || '').trim().toLowerCase()
    const name = String(source.name || '').trim()
    if (!sectionId || !code || !name) {
      financeCatalogError.value = 'Для операции нужны раздел, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPost('/finance/catalogs/operations', {
        section_id: sectionId,
        code,
        name,
        input_mode: String(source.input_mode || 'mixed'),
        requires_region: Boolean(source.requires_region),
        requires_source: Boolean(source.requires_source),
        requires_project: Boolean(source.requires_project),
        requires_qty: Boolean(source.requires_qty),
        allows_negative: Boolean(source.allows_negative),
        sort_order: Number(source.sort_order || 100),
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

  const archiveFinanceOperation = async (operationId) => {
    // Архивируем операцию, если на нее еще не привязаны записи.
    financeCatalogError.value = null
    financeCatalogOk.value = ''
    if (!operationId) return false
    financeCatalogSaving.value = true
    try {
      await apiDelete(`/finance/catalogs/operations/${Number(operationId)}`, { token: auth.state.token })
      financeCatalogOk.value = 'Операция архивирована'
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
    const sectionId = Number(draft?.section_id || 0)
    const code = String(draft?.code || '').trim().toLowerCase()
    const name = String(draft?.name || '').trim()
    if (!operationId || !sectionId || !code || !name) {
      financeCatalogError.value = 'Для операции нужны id, раздел, код и название'
      return false
    }
    financeCatalogSaving.value = true
    try {
      await apiPut(`/finance/catalogs/operations/${Number(operationId)}`, {
        section_id: sectionId,
        code,
        name,
        input_mode: String(draft?.input_mode || 'mixed'),
        requires_region: Boolean(draft?.requires_region),
        requires_source: Boolean(draft?.requires_source),
        requires_project: Boolean(draft?.requires_project),
        requires_qty: Boolean(draft?.requires_qty),
        allows_negative: Boolean(draft?.allows_negative),
        sort_order: Number(draft?.sort_order || 100),
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
    financeCatalogsLoaded,
    financeLoaded,
    financeEntriesLoaded,
    financeLoading,
    financeEntriesLoading,
    financeEntrySaving,
    financeCatalogSaving,
    financeError,
    financeEntriesError,
    financeEntryError,
    financeCatalogError,
    financeCatalogOk,
    financeEntryOk,
    loadFinanceBootstrap,
    loadFinanceEntries,
    createFinanceEntry,
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
  }
}
