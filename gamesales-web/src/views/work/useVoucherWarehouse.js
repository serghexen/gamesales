import { computed, onScopeDispose, reactive, ref } from 'vue'
import { apiDelete, apiGet, apiPost, apiPut } from '../../api/http'

export function useVoucherWarehouse(getToken, confirm) {
  // Склад использует собственные маршруты: существующие пулы селлера остаются отдельными.
  const items = ref([])
  const canManage = ref(false)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const search = ref('')
  const prices = reactive({})
  const priceBases = new Map()
  const selectedId = ref(null)
  const keysLoading = ref(false)
  const keysError = ref('')
  const keysOk = ref('')
  const showAdd = ref(false)
  const revealingId = ref(0)
  const revealed = reactive({})
  const pool = ref(emptyPool())
  let active = true
  let keyRequest = 0
  let loadingPromise = null
  const selected = computed(() => items.value.find((row) => row.catalog_nominal_id === selectedId.value))
  const filtered = computed(() => {
    // Поиск одинаково работает по SKU, сервису и названию номинала.
    const query = search.value.trim().toLocaleLowerCase('ru')
    return items.value.filter((row) => [row.sku, row.service_name, row.name].some((value) => String(value).toLocaleLowerCase('ru').includes(query)))
  })
  const totalPages = computed(() => Math.max(1, Math.ceil(pool.value.total / pool.value.page_size)))

  function emptyPool() {
    // При смене позиции старые ключи и статистика не должны мелькать в новом пуле.
    return { items: [], total: 0, free_count: 0, reserved_count: 0, delivered_count: 0, expired_count: 0, page: 1, page_size: 20 }
  }

  function clearRevealed() {
    // Полные коды живут только до закрытия списка или перехода на другую страницу.
    Object.keys(revealed).forEach((key) => delete revealed[key])
    revealingId.value = 0
  }

  function path(id = selectedId.value) {
    // ID всегда берётся из выбранного номинала каталога, а не из данных маркетплейса.
    return `/voucher-warehouse/nominals/${id}`
  }

  async function load() {
    // Ручное обновление сохраняет несохранённые цены других строк.
    if (loadingPromise) return loadingPromise
    loading.value = true
    error.value = ''
    loadingPromise = (async () => {
      try {
        const result = await apiGet('/voucher-warehouse', { token: getToken() })
        if (!active) return
        for (const row of result.items) {
          // Версия остаётся вместе с введённой ценой, даже если остальные данные обновились.
          const previous = priceBases.get(row.catalog_nominal_id)
          if (!(row.catalog_nominal_id in prices) || prices[row.catalog_nominal_id] === String(previous?.price ?? '')) {
            prices[row.catalog_nominal_id] = String(row.price ?? '')
            priceBases.set(row.catalog_nominal_id, { price: row.price, version: row.price_updated_at ?? null })
          }
        }
        items.value = result.items
        canManage.value = result.can_manage
        if (selectedId.value && !selected.value) closeKeys()
      } catch (err) {
        if (active) error.value = err.message || 'Не удалось загрузить склад'
      } finally {
        loading.value = false
        loadingPromise = null
      }
    })()
    return loadingPromise
  }

  async function reloadAfterMutation() {
    // Дожидаемся старого чтения, затем запрашиваем снимок после завершённой записи.
    if (loadingPromise) await loadingPromise
    if (active) await load()
  }

  async function savePrice(row) {
    // Пустая цена снимает значение, а ноль остаётся допустимой ценой всего пула.
    if (saving.value || !canManage.value) return
    const id = row.catalog_nominal_id
    const value = prices[id].trim().replace(',', '.')
    if (value && !/^\d{1,14}(\.\d{1,6})?$/.test(value)) { error.value = 'Укажите неотрицательную цену: до 6 знаков после запятой'; return }
    saving.value = true
    error.value = ''
    try {
      const current = items.value.find((item) => item.catalog_nominal_id === id)
      if (!current) { error.value = 'Позиция больше не найдена на складе'; return }
      let base = priceBases.get(id)
      if (base?.version !== (current.price_updated_at ?? null)) {
        // Замена чужого изменения требует явного выбора; введённую цену не теряем.
        const money = (price) => price == null ? 'не задана' : `${price} ₽`
        const accepted = await confirm?.({ title: 'Цена пула изменилась',
          message: `Актуальная цена: ${money(current.price)}. Заменить её на ${money(value || null)}?`,
          confirmText: 'Заменить', cancelText: 'Оставить текущую' })
        if (!active) return
        if (!accepted) {
          prices[id] = String(current.price ?? '')
          priceBases.set(id, { price: current.price, version: current.price_updated_at ?? null })
          return
        }
        base = { price: current.price, version: current.price_updated_at ?? null }
      }
      const result = await apiPut(`${path(id)}/price`, { price: value || null, expected_updated_at: base?.version ?? null }, { token: getToken() })
      if (!active) return
      row.price = value || null
      row.price_updated_at = result.price_updated_at
      prices[id] = value
      priceBases.set(id, { price: row.price, version: result.price_updated_at })
      await reloadAfterMutation()
    } catch (err) {
      // После конфликта перечитываем серверную цену, сохраняя черновик для сравнения и подтверждения.
      if (active && err.status === 409) await reloadAfterMutation()
      if (active) error.value = err.message || 'Не удалось сохранить цену'
    } finally {
      saving.value = false
    }
  }

  async function loadKeys(page = 1) {
    // Запоздалый ответ другого SKU или страницы не попадает в текущий список.
    const id = selectedId.value
    if (!id || !canManage.value) return
    const request = ++keyRequest
    keysLoading.value = true
    keysError.value = ''
    clearRevealed()
    try {
      const result = await apiGet(`${path(id)}/keys?page=${page}`, { token: getToken() })
      if (active && request === keyRequest) pool.value = { ...result, product_title: `${result.service_name} · ${result.name} · ${result.sku}` }
    } catch (err) {
      if (active && request === keyRequest) keysError.value = err.message || 'Не удалось загрузить ключи'
    } finally {
      if (request === keyRequest) keysLoading.value = false
    }
  }

  async function openKeys(row) {
    // Открываем только одну позицию, чтобы действия с ключами были однозначными.
    if (saving.value || !canManage.value) return
    if (selectedId.value === row.catalog_nominal_id) { closeKeys(); return }
    selectedId.value = row.catalog_nominal_id
    pool.value = { ...emptyPool(), product_title: `${row.service_name} · ${row.name} · ${row.sku}` }
    keysOk.value = ''
    await loadKeys()
  }

  function closeKeys() {
    // Закрытие списка отменяет показ кодов, но не отменяет уже отправленную запись.
    if (saving.value) return
    keyRequest += 1
    selectedId.value = null
    showAdd.value = false
    keysLoading.value = false
    pool.value = emptyPool()
    clearRevealed()
  }

  function openAdd() {
    // Форма наполнения получает текущий пул только после завершения его загрузки.
    if (!selectedId.value || saving.value || keysLoading.value) return
    keysError.value = ''
    keysOk.value = ''
    showAdd.value = true
  }

  function closeAdd() {
    // Повторный клик не закрывает форму во время сохранения ключей.
    if (!saving.value) showAdd.value = false
  }

  async function addKeys(text, expiresAt) {
    // Пустые строки пропускаем; размер пакета проверяем до сетевого запроса.
    if (saving.value || !canManage.value || !selectedId.value) return { ok: false }
    const codes = text.split(/\r?\n/).map((code) => code.trim()).filter(Boolean)
    if (!codes.length || codes.length > 1000) { keysError.value = 'Добавьте от 1 до 1000 ключей, каждый с новой строки'; return { ok: false } }
    saving.value = true
    keysError.value = ''
    keysOk.value = ''
    try {
      const result = await apiPost(`${path()}/keys`, { codes, expires_at: expiresAt || null }, { token: getToken() })
      if (!active) return { ok: true }
      keysOk.value = `Добавлено: ${result.added}. Повторов: ${result.duplicates}.`
      await loadKeys()
      await reloadAfterMutation()
      return { ok: true }
    } catch (err) {
      if (active) keysError.value = err.message || 'Не удалось добавить ключи'
      return { ok: false }
    } finally {
      saving.value = false
    }
  }

  async function reveal(key) {
    // Раскрытие одного ключа не резервирует его; повторный клик скрывает код.
    if (saving.value || keysLoading.value || revealingId.value || !canManage.value) return
    if (revealed[key.id]) { delete revealed[key.id]; return }
    const request = keyRequest
    revealingId.value = key.id
    try {
      const result = await apiPost(`${path()}/keys/${key.id}/reveal`, {}, { token: getToken() })
      if (active && request === keyRequest) revealed[key.id] = result.code
    } catch (err) {
      if (active && request === keyRequest) keysError.value = err.message || 'Не удалось показать ключ'
    } finally {
      if (request === keyRequest) revealingId.value = 0
    }
  }

  async function remove(key = null) {
    // Подтверждение фиксирует выбранный пул до удаления, защищая от переключения SKU.
    if (saving.value || keysLoading.value || !canManage.value || !selectedId.value) return
    const throughKeyId = pool.value.through_key_id
    if (!key && !(throughKeyId > 0)) { keysError.value = 'Обновите список ключей перед удалением'; return }
    saving.value = true
    try {
      const accepted = await confirm?.({ title: key ? 'Удалить ключ?' : 'Удалить свободные ключи?',
        message: key ? `Ключ ${key.masked_code} будет удалён без возможности восстановления.`
          : `Будут удалены свободные ключи из открытого списка, включая просроченные: ${pool.value.free_count + pool.value.expired_count}. Новые поступления сохранятся.`,
        confirmText: 'Удалить', cancelText: 'Отмена' })
      if (!accepted || !active) return
      const result = await apiDelete(`${path()}/keys${key ? `/${key.id}` : `?through_key_id=${throughKeyId}`}`, { token: getToken() })
      if (!active) return
      keysOk.value = `Удалено ключей: ${result.removed}`
      await loadKeys(pool.value.page)
      await reloadAfterMutation()
    } catch (err) {
      if (active) keysError.value = err.message || 'Не удалось удалить ключи'
    } finally {
      saving.value = false
    }
  }

  onScopeDispose(() => {
    // После ухода со склада ответы запросов и раскрытые ключи больше не используются.
    active = false
    keyRequest += 1
    clearRevealed()
  })

  return { items, filtered, prices, selected, selectedId, pool, canManage, loading, saving, search, error,
    keysLoading, keysError, keysOk, showAdd, revealingId, revealed, totalPages,
    load, savePrice, openKeys, closeKeys, loadKeys, openAdd, closeAdd, addKeys, reveal, remove }
}
