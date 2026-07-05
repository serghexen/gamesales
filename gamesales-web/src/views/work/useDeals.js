import { computed, ref, watch } from 'vue'

export function useDeals({ auth, apiGet, mapApiError, resolveDealFlowStatusFilter, dealFilters, dealShowCompleted, canDoAction }) {
  // Данные таблицы сделок + состояние списка.
  const dealItems = ref([])
  const dealListError = ref(null)
  const dealListLoading = ref(false)
  const dealPage = ref(1)
  const dealPageInput = ref(1)
  const dealPageSize = ref(20)
  const dealTotal = ref(0)
  let dealListRequestSeq = 0
  // По умолчанию показываем сделки по дате от старых к новым, чтобы новые оказывались внизу.
  const dealSort = ref({ key: 'date', dir: 'asc' })

  // Общее число страниц по текущему размеру страницы.
  const totalPages = computed(() => {
    const pages = Math.ceil(dealTotal.value / dealPageSize.value)
    return pages > 0 ? pages : 1
  })

  // Если страниц стало меньше, возвращаемся в допустимый диапазон.
  watch(totalPages, (total) => {
    if (dealPage.value <= total) return
    // Если текущая страница стала недоступной, переключаемся на последнюю валидную и догружаем данные.
    dealPage.value = total
    if (dealTotal.value > 0) {
      loadDeals(total)
    }
  })

  // Держим поле "номер страницы" синхронно с реальной страницей.
  watch(dealPage, (val) => {
    dealPageInput.value = val
  })

  // При смене размера страницы начинаем с первой.
  watch(dealPageSize, () => {
    dealPage.value = 1
    loadDeals(1)
  })

  // Таблица использует порядок, который вернул backend (сортировка теперь серверная).
  const sortedDeals = computed(() => [...dealItems.value])

  // Переключает направление сортировки по колонке.
  function toggleDealSort(key) {
    const current = dealSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      dealSort.value = { key, dir: 'asc' }
    }
    dealPage.value = 1
    loadDeals(1)
  }

  // Безопасный переход на страницу.
  function setDealPage(page) {
    const target = Math.min(Math.max(1, Number(page) || 1), totalPages.value)
    if (target === dealPage.value) return
    loadDeals(target)
  }

  function jumpDealPage() {
    setDealPage(dealPageInput.value)
  }

  function prevDealPage() {
    setDealPage(dealPage.value - 1)
  }

  function nextDealPage() {
    setDealPage(dealPage.value + 1)
  }

  // Загружает сделки с учетом фильтров и пагинации.
  async function loadDeals(page = 1) {
    const requestId = ++dealListRequestSeq
    dealListError.value = null
    dealListLoading.value = true
    try {
      const params = new URLSearchParams()
      if (dealFilters.search_q) params.set('q', dealFilters.search_q)
      if (dealFilters.type_q) params.set('type_q', dealFilters.type_q)
      if (dealFilters.customer_q) params.set('customer_q', dealFilters.customer_q)
      if (dealFilters.responsible_q) params.set('responsible_q', dealFilters.responsible_q)
      if (dealFilters.region_q) params.set('region_q', dealFilters.region_q)
      const canViewCompletedDeals = typeof canDoAction === 'function' ? canDoAction('deals_completed.view') : true
      const effectiveShowCompleted = Boolean(dealShowCompleted.value && canViewCompletedDeals)
      const flowStatusFilter = resolveDealFlowStatusFilter(dealFilters.status_q, effectiveShowCompleted)
      const canViewDraftDeals = typeof canDoAction === 'function' ? canDoAction('deals_draft.view') : true
      // Убираем из запроса статусы, которые роль не должна видеть по action-правам.
      const allowedFlowStatusFilter = flowStatusFilter
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
        .filter((item) => item !== 'draft' || canViewDraftDeals)
        .filter((item) => item !== 'completed' || canViewCompletedDeals)
        .join(',')
      params.set('flow_status_q', allowedFlowStatusFilter || '__no_status__')
      if (dealFilters.purchase_from) params.set('purchase_from', dealFilters.purchase_from)
      if (dealFilters.purchase_to) params.set('purchase_to', dealFilters.purchase_to)
      params.set('sort_key', String(dealSort.value?.key || 'date'))
      params.set('sort_dir', String(dealSort.value?.dir || 'asc'))
      params.set('page', String(page))
      params.set('page_size', String(dealPageSize.value))
      const res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
      if (requestId !== dealListRequestSeq) return
      // Нормализуем ответ в product-first поля для единого контракта UI.
      dealItems.value = (res?.items || []).map((item) => ({
        ...item,
        // Поддерживаем старые ответы API, где товар мог приходить как game_id.
        product_id: item?.product_id ?? item?.game_id ?? null,
        product_title: item?.product_title || '',
        product_short_title: item?.product_short_title || '',
        product_link: item?.product_link || '',
      }))
      dealTotal.value = res?.total || 0
      dealPage.value = page
    } catch (e) {
      if (requestId !== dealListRequestSeq) return
      dealListError.value = mapApiError(e?.message)
    } finally {
      if (requestId === dealListRequestSeq) {
        dealListLoading.value = false
      }
    }
  }

  return {
    dealItems,
    dealListError,
    dealListLoading,
    dealPage,
    dealPageInput,
    dealPageSize,
    dealTotal,
    dealSort,
    totalPages,
    sortedDeals,
    toggleDealSort,
    setDealPage,
    jumpDealPage,
    prevDealPage,
    nextDealPage,
    loadDeals,
  }
}
