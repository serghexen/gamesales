export function useWorkUiHelpers({
  productsPageSize,
  productsPageInput,
  accountSort,
  productsSort,
  dealSort,
  domainsSortAsc,
}) {
  // Берем размер страницы из select и сохраняем только валидное число.
  function setProductsPageSizeFromEvent(event) {
    const value = Number(event?.target?.value)
    if (!Number.isFinite(value) || value <= 0) return
    productsPageSize.value = value
  }

  // Обновляем поле "номер страницы" из input.
  function setProductsPageInputFromEvent(event) {
    const value = Number(event?.target?.value)
    if (!Number.isFinite(value)) return
    productsPageInput.value = value
  }

  // Общие css-классы для индикаторов сортировки.
  const getSortButtonClass = (state) => ({
    'sort-icon--active': Boolean(state),
    'sort-icon--asc': state === 'asc',
    'sort-icon--desc': state === 'desc',
  })

  const getAccountSortState = (key) => {
    const map = {
      login: ['login_asc', 'login_desc'],
      products: ['products_asc', 'products_desc'],
    }
    const pair = map[key]
    if (!pair) return ''
    const [asc, desc] = pair
    if (accountSort.value === asc) return 'asc'
    if (accountSort.value === desc) return 'desc'
    return ''
  }

  const getAccountSortClass = (key) => getSortButtonClass(getAccountSortState(key))
  const getProductsSortClass = (key) => getSortButtonClass(productsSort.value.key === key ? productsSort.value.dir : '')
  const getDealSortClass = (key) => getSortButtonClass(dealSort.value.key === key ? dealSort.value.dir : '')
  const getDomainsSortClass = () => getSortButtonClass(domainsSortAsc.value ? 'asc' : 'desc')

  // Универсальный помощник для сортировок справочников.
  const getKeyedSortClass = (sortRef, key) => {
    const sort = sortRef?.value ?? sortRef
    const state = sort?.key === key ? sort?.dir : ''
    return getSortButtonClass(state)
  }

  const getSlotAssignmentStatus = (item) => (item?.released_at ? 'Снят' : 'Занят')

  // Высота большого поля комментария по длине текста.
  const getNotesRows = (value) => {
    if (!value) return 2
    const len = String(value).length
    return Math.min(8, Math.max(3, Math.ceil(len / 60)))
  }

  // Высота компактного поля комментария по длине текста.
  const getCompactNotesRows = (value) => {
    if (!value) return 2
    const len = String(value).length
    return Math.min(6, Math.max(2, Math.ceil(len / 120)))
  }

  return {
    setProductsPageSizeFromEvent,
    setProductsPageInputFromEvent,
    getProductsSortClass,
    getAccountSortClass,
    getDealSortClass,
    getDomainsSortClass,
    getKeyedSortClass,
    getSlotAssignmentStatus,
    getNotesRows,
    getCompactNotesRows,
  }
}
