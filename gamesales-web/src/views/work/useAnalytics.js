import { reactive, ref } from 'vue'

export function useAnalytics({ auth, apiGet, mapApiError }) {
  const analyticsFilters = reactive({
    date_from: '',
    date_to: '',
    deal_type_code: '',
    region_code: '',
    source_id: '',
  })
  const analyticsTotals = reactive({
    revenue: 0,
    purchase_cost: 0,
    margin: 0,
    count: 0,
    avg_check: 0,
  })
  const analyticsByDay = ref([])
  const analyticsByType = ref([])
  const analyticsSourcesTopCount = ref([])
  const analyticsSourcesTopRevenue = ref([])
  const analyticsRepeatCustomers = reactive({
    repeat_count: 0,
    total_customers: 0,
    repeat_share: 0,
  })
  const analyticsLoaded = ref(false)
  const analyticsLoading = ref(false)
  const analyticsError = ref(null)

  const clearAnalyticsData = () => {
    analyticsByDay.value = []
    analyticsByType.value = []
    analyticsSourcesTopCount.value = []
    analyticsSourcesTopRevenue.value = []
    analyticsRepeatCustomers.repeat_count = 0
    analyticsRepeatCustomers.total_customers = 0
    analyticsRepeatCustomers.repeat_share = 0
  }

  const loadAnalytics = async () => {
    analyticsError.value = null
    analyticsLoaded.value = false

    const hasFilters = Boolean(
      analyticsFilters.date_from ||
        analyticsFilters.date_to ||
        analyticsFilters.deal_type_code ||
        analyticsFilters.region_code ||
        analyticsFilters.source_id
    )

    if (!hasFilters) {
      clearAnalyticsData()
      return
    }

    analyticsLoading.value = true
    try {
      const params = new URLSearchParams()
      if (analyticsFilters.date_from) params.set('date_from', analyticsFilters.date_from)
      if (analyticsFilters.date_to) params.set('date_to', analyticsFilters.date_to)
      if (analyticsFilters.deal_type_code) params.set('deal_type_code', analyticsFilters.deal_type_code)
      if (analyticsFilters.region_code) params.set('region_code', analyticsFilters.region_code)
      if (analyticsFilters.source_id) params.set('source_id', analyticsFilters.source_id)

      const [sales, sources] = await Promise.all([
        apiGet(`/analytics/sales?${params.toString()}`, { token: auth.state.token }),
        apiGet(`/analytics/sources?${params.toString()}`, { token: auth.state.token }),
      ])

      analyticsTotals.revenue = Number(sales?.totals?.revenue || 0)
      analyticsTotals.purchase_cost = Number(sales?.totals?.purchase_cost || 0)
      analyticsTotals.margin = Number(sales?.totals?.margin || 0)
      analyticsTotals.count = Number(sales?.totals?.count || 0)
      analyticsTotals.avg_check = Number(sales?.totals?.avg_check || 0)
      analyticsByDay.value = Array.isArray(sales?.by_day) ? sales.by_day : []
      analyticsByType.value = Array.isArray(sales?.by_type) ? sales.by_type : []

      analyticsSourcesTopCount.value = Array.isArray(sources?.top_by_count) ? sources.top_by_count : []
      analyticsSourcesTopRevenue.value = Array.isArray(sources?.top_by_revenue) ? sources.top_by_revenue : []
      analyticsRepeatCustomers.repeat_count = Number(sources?.repeat_customers?.repeat_count || 0)
      analyticsRepeatCustomers.total_customers = Number(sources?.repeat_customers?.total_customers || 0)
      analyticsRepeatCustomers.repeat_share = Number(sources?.repeat_customers?.repeat_share || 0)
      analyticsLoaded.value = true
    } catch (e) {
      analyticsError.value = mapApiError(e?.message)
      clearAnalyticsData()
    } finally {
      analyticsLoading.value = false
    }
  }

  return {
    analyticsFilters,
    analyticsTotals,
    analyticsByDay,
    analyticsByType,
    analyticsSourcesTopCount,
    analyticsSourcesTopRevenue,
    analyticsRepeatCustomers,
    analyticsLoaded,
    analyticsLoading,
    analyticsError,
    loadAnalytics,
  }
}
