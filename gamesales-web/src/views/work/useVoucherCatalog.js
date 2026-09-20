import { computed, reactive, ref } from 'vue'
import { apiDelete, apiGet, apiPost, apiPut } from '../../api/http'

export function useVoucherCatalog(getToken) {
  // Услуги, собственные номиналы и форма живут отдельно от WorkView для свободного переноса раздела.
  const items = ref([])
  const suppliers = ref([])
  const canEdit = ref(false)
  const loading = ref(false)
  const saving = ref(false)
  const optionsLoading = ref(false)
  const error = ref('')
  const formError = ref('')
  const formOpen = ref(false)
  const closeConfirm = ref(false)
  const deleteConfirm = ref(false)
  const bindingOpen = ref(false)
  const mode = ref('service')
  const options = ref([])
  const search = ref('')
  const sourceItem = ref(null)
  const deleteServiceName = computed(() => sourceItem.value?.name || '')
  const deleteServiceNominalCount = computed(() => sourceItem.value?.nominals?.length || 0)
  const baseline = ref('')
  const draft = reactive({ item_id: null, name: '', catalog_nominal_id: null, nominal_name: '',
    supplier_code: 'interhub', service_id: '', selected: [], link_nominal_id: '', source: 'supplier',
    routing_offers: [], fulfillment_revision: 0 })
  let optionsRequest = 0
  let loadingPromise = null
  const dirty = computed(() => draftChanges() !== baseline.value)
  const title = computed(() => mode.value === 'nominals' ? 'Добавить номиналы'
    : mode.value === 'nominal' ? 'Карточка номинала' : draft.item_id ? 'Изменить услугу' : 'Новая услуга')
  const filteredItems = computed(() => {
    // Поиск находит всю услугу по её имени, собственному номиналу или подписи поставщика.
    const query = search.value.trim().toLocaleLowerCase('ru')
    return items.value.filter((item) => [item.name, ...(item.nominals || []).flatMap((nominal) => [nominal.name,
      ...nominal.offers.flatMap((offer) => [offer.service_title, offer.nominal_title, offer.supplier_name])])]
      .some((value) => String(value).toLocaleLowerCase('ru').includes(query)))
  })
  const services = computed(() => [...new Map(options.value.map((item) => [String(item.service_id), item.service_title])).entries()]
    .map(([id, title]) => ({ id, title })).sort((a, b) => a.title.localeCompare(b.title, 'ru')))
  const nominals = computed(() => options.value.filter((item) => String(item.service_id) === draft.service_id).map((item) => ({
    ...item, linked: (sourceItem.value?.nominals || []).some((nominal) => nominal.offers.some((offer) =>
      offer.supplier_code === draft.supplier_code && String(offer.service_id) === draft.service_id
      && String(offer.nominal_id) === String(item.nominal_id))),
  })).sort((a, b) => a.nominal_title.localeCompare(b.nominal_title, 'ru', { numeric: true })))

  function draftChanges() {
    // Просмотр услуг и переключение вкладок не требуют подтверждения; введённые данные защищаем.
    return JSON.stringify({ name: draft.name, nominal_name: draft.nominal_name, selected: draft.selected,
      routing: draft.routing_offers.map((offer) => [offer.offer_id, offer.fulfillment_enabled]),
      binding: draft.selected.length || draft.link_nominal_id
        ? [draft.supplier_code, draft.service_id, draft.link_nominal_id] : null })
  }

  async function load() {
    // Если чтение уже идёт, сохранение дождётся его перед повторным запросом свежего снимка.
    if (loadingPromise) return loadingPromise
    loading.value = true
    error.value = ''
    loadingPromise = (async () => {
      try {
        const result = await apiGet('/voucher-catalog', { token: getToken() })
        items.value = result.items
        suppliers.value = result.suppliers
        canEdit.value = result.can_edit
      } catch (err) {
        error.value = err.message || 'Не удалось загрузить каталог'
      } finally {
        loading.value = false
        loadingPromise = null
      }
    })()
    return loadingPromise
  }

  function selectService() {
    // Выбор другой услуги сбрасывает чужие номиналы, а название новой услуги заполняется один раз.
    draft.selected = []
    draft.link_nominal_id = ''
    if (!draft.item_id && !draft.name.trim()) draft.name = services.value.find((item) => item.id === draft.service_id)?.title || ''
  }

  function toggleNominal(option, checked) {
    // Собственное название хранится отдельно от подписи поставщика и доступно для правки.
    const id = String(option.nominal_id)
    draft.selected = draft.selected.filter((item) => item.id !== id)
    if (checked && !option.linked) draft.selected.push({ id, name: option.nominal_title })
  }

  function selectAll(checked) {
    // Массовый выбор пропускает уже связанные номиналы и сохраняет введённые собственные названия.
    const names = new Map(draft.selected.map((item) => [item.id, item.name]))
    draft.selected = checked ? nominals.value.filter((item) => !item.linked).map((item) => ({
      id: String(item.nominal_id), name: names.get(String(item.nominal_id)) || item.nominal_title,
    })) : []
  }

  async function loadOptions() {
    // Поздний ответ старой формы или другого поставщика не должен менять текущий выбор.
    const request = ++optionsRequest
    optionsLoading.value = true
    options.value = []
    draft.service_id = ''
    draft.selected = []
    draft.link_nominal_id = ''
    formError.value = ''
    try {
      const result = await apiGet(`/voucher-catalog/suppliers/${encodeURIComponent(draft.supplier_code)}/nominals`, { token: getToken() })
      if (request === optionsRequest && formOpen.value) options.value = result
    } catch (err) {
      if (request === optionsRequest) formError.value = err.message || 'Не удалось загрузить номиналы'
    } finally {
      if (request === optionsRequest) optionsLoading.value = false
    }
  }

  async function openForm(item = null, nextMode = 'service', nominal = null) {
    // Все действия открывают одну знакомую модалку: услугу, пакет номиналов или отдельный номинал.
    if (saving.value) return
    sourceItem.value = item
    mode.value = nextMode
    Object.assign(draft, { item_id: item?.item_id ?? null, name: item?.name || '',
      catalog_nominal_id: nominal?.catalog_nominal_id ?? null, nominal_name: nominal?.name || '',
      supplier_code: suppliers.value[0]?.code || 'interhub', service_id: '', selected: [], link_nominal_id: '', source: 'supplier',
      routing_offers: (nominal?.offers || []).map((offer) => ({ ...offer, fulfillment_enabled: offer.fulfillment_enabled !== false }))
        .sort((a, b) => (a.fulfillment_priority ?? a.offer_id) - (b.fulfillment_priority ?? b.offer_id) || a.offer_id - b.offer_id),
      fulfillment_revision: nominal?.fulfillment_revision ?? 0 })
    bindingOpen.value = false
    optionsRequest += 1
    options.value = []
    optionsLoading.value = false
    baseline.value = draftChanges()
    closeConfirm.value = false
    deleteConfirm.value = false
    formError.value = ''
    formOpen.value = true
    if (nextMode === 'nominals' || !item) await loadOptions()
  }

  function moveOffer(from, to) {
    // Порядок меняется только в черновике и сохраняется общей кнопкой карточки.
    if (saving.value || from === to || from < 0 || to < 0 || from >= draft.routing_offers.length || to >= draft.routing_offers.length) return
    const [offer] = draft.routing_offers.splice(from, 1)
    draft.routing_offers.splice(to, 0, offer)
  }

  function toggleOffer(id, enabled) {
    // Отключение выдачи сохраняет позицию поставщика, его связку и снимки.
    if (saving.value) return
    const offer = draft.routing_offers.find((row) => row.offer_id === id)
    if (offer) offer.fulfillment_enabled = enabled
  }

  async function showBinding() {
    // Порядок редактируется без обращения к поставщику; каталог загружаем только для новой связки.
    bindingOpen.value = true
    await loadOptions()
  }

  function hideBinding() {
    // Отмена новой связки не сбрасывает уже отредактированный порядок поставщиков.
    bindingOpen.value = false
    optionsRequest += 1
    optionsLoading.value = false
    draft.service_id = ''
    draft.link_nominal_id = ''
    formError.value = ''
  }

  function discard() {
    // Закрытие отменяет только несохранённую форму и делает её сетевые ответы неактуальными.
    if (saving.value) return
    optionsRequest += 1
    optionsLoading.value = false
    formOpen.value = false
    closeConfirm.value = false
    deleteConfirm.value = false
  }

  async function askDelete(item = null, nominal = null) {
    // Из таблицы открываем ту же карточку, чтобы подтверждение не пряталось в длинном списке.
    if (saving.value) return
    if (item && nominal) await openForm(item, 'nominal', nominal)
    if (mode.value !== 'nominal' || !draft.catalog_nominal_id) return
    closeConfirm.value = false
    formError.value = ''
    deleteConfirm.value = true
  }

  async function deleteNominal() {
    // Удаление требует явного подтверждения и обновляет список только после успешного ответа API.
    if (saving.value || !deleteConfirm.value || !draft.catalog_nominal_id) return
    saving.value = true
    formError.value = ''
    try {
      await apiDelete(`/voucher-catalog/items/${draft.item_id}/nominals/${draft.catalog_nominal_id}`, { token: getToken() })
      formOpen.value = false
      deleteConfirm.value = false
      if (loadingPromise) await loadingPromise
      await load()
    } catch (err) {
      formError.value = err.message || 'Не удалось удалить номинал'
    } finally {
      saving.value = false
    }
  }

  async function askDeleteService(item = null) {
    // Подтверждение из списка и из карточки использует сохранённое имя и состав услуги.
    if (saving.value) return
    if (item) await openForm(item)
    if (mode.value !== 'service' || !draft.item_id) return
    closeConfirm.value = false
    formError.value = ''
    deleteConfirm.value = true
  }

  async function deleteService() {
    // Услуга исчезает из списка только после успешного удаления всего содержимого на сервере.
    if (saving.value || !deleteConfirm.value || mode.value !== 'service' || !draft.item_id) return
    saving.value = true
    formError.value = ''
    try {
      await apiDelete(`/voucher-catalog/items/${draft.item_id}`, { token: getToken() })
      formOpen.value = false
      deleteConfirm.value = false
      if (loadingPromise) await loadingPromise
      await load()
    } catch (err) {
      formError.value = err.message || 'Не удалось удалить услугу'
    } finally {
      saving.value = false
    }
  }

  function requestClose() {
    // Крестику, Escape и клику по фону даём одинаковую защиту введённых данных.
    if (saving.value) return
    if (dirty.value) closeConfirm.value = true
    else discard()
  }

  async function save() {
    // Формируем либо услугу, либо атомарный пакет собственных номиналов с выбранными соответствиями.
    if (saving.value || optionsLoading.value || deleteConfirm.value) return
    formError.value = ''
    if (!draft.name.trim()) { formError.value = 'Укажите название услуги'; return }
    let chosen = []
    const binding = (nominalId) => ({ supplier_code: draft.supplier_code, service_id: draft.service_id, nominal_id: nominalId })
    if (mode.value === 'nominal') {
      chosen = [{ catalog_nominal_id: draft.catalog_nominal_id, name: draft.nominal_name.trim(),
        routing: { revision: draft.fulfillment_revision, offers: draft.routing_offers.map((offer) => ({
          offer_id: offer.offer_id, enabled: offer.fulfillment_enabled,
        })) },
        ...(draft.link_nominal_id ? { binding: binding(draft.link_nominal_id) } : {}) }]
      if (draft.service_id && !draft.link_nominal_id) { formError.value = 'Выберите номинал поставщика'; return }
    } else if (mode.value === 'nominals' && draft.source === 'manual') {
      chosen = [{ name: draft.nominal_name.trim() }]
    } else {
      chosen = draft.selected.map((item) => ({ name: item.name.trim(), binding: binding(item.id) }))
      if ((mode.value === 'nominals' || draft.service_id) && !chosen.length) { formError.value = 'Отметьте хотя бы один номинал'; return }
    }
    if (chosen.some((item) => !item.name)) { formError.value = 'Укажите название каждого номинала'; return }
    if (new Set(chosen.map((item) => item.name)).size !== chosen.length) { formError.value = 'Названия номиналов должны различаться'; return }
    if (chosen.length > 100) { formError.value = 'За один раз можно добавить до 100 номиналов'; return }
    saving.value = true
    try {
      const auth = { token: getToken() }
      if (mode.value !== 'service') await apiPost(`/voucher-catalog/items/${draft.item_id}/nominals`, { nominals: chosen }, auth)
      else if (draft.item_id) await apiPut(`/voucher-catalog/items/${draft.item_id}`, { name: draft.name.trim() }, auth)
      else await apiPost('/voucher-catalog/items', { name: draft.name.trim(), nominals: chosen }, auth)
      formOpen.value = false
      closeConfirm.value = false
      if (loadingPromise) await loadingPromise
      await load()
    } catch (err) {
      formError.value = err.message || 'Не удалось сохранить каталог'
    } finally {
      saving.value = false
    }
  }

  async function unlink(itemId, offerId) {
    // Убираем только связь с поставщиком, сохраняя услугу и собственный номинал.
    if (saving.value) return
    saving.value = true
    try {
      await apiDelete(`/voucher-catalog/items/${itemId}/offers/${offerId}`, { token: getToken() })
      if (loadingPromise) await loadingPromise
      await load()
    } catch (err) {
      error.value = err.message || 'Не удалось удалить связку'
    } finally {
      saving.value = false
    }
  }

  return { items, suppliers, canEdit, loading, saving, optionsLoading, error, formError, formOpen,
    closeConfirm, deleteConfirm, bindingOpen, mode, title, draft, search, filteredItems, services, nominals, load, loadOptions,
    openForm, selectService, toggleNominal, selectAll, save, unlink, requestClose, discard,
    moveOffer, toggleOffer, showBinding, hideBinding, askDelete, deleteNominal,
    askDeleteService, deleteService, deleteServiceName, deleteServiceNominalCount }
}
