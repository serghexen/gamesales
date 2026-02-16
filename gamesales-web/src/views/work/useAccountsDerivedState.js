import { computed } from 'vue'

export function useAccountsDerivedState({
  accounts,
  productsAll,
  accountProductSearch,
  editAccountProductSearch,
  accountProductType,
  editAccountProductType,
}) {
  // Здесь можно добавить локальную сортировку аккаунтов при необходимости.
  const sortedAccounts = computed(() => [...accounts.value])

  // Проверяет, подходит ли товар под выбранный тип фильтра (игра/подписка/все).
  const matchesProductType = (item, selectedType) => {
    const type = String(selectedType || '').trim().toLowerCase()
    if (!type) return true
    const itemType = String(item?.type_code || '').trim().toLowerCase()
    return itemType === type
  }

  // Фильтр товаров для формы создания аккаунта.
  const filteredAccountProducts = computed(() => {
    const q = accountProductSearch.value.trim().toLowerCase()
    const selectedType = accountProductType?.value || ''
    return productsAll.value.filter((g) => {
      if (!matchesProductType(g, selectedType)) return false
      if (!q) return true
      return (g.title || '').toLowerCase().includes(q)
    })
  })

  // Фильтр товаров для формы редактирования аккаунта.
  const filteredEditAccountProducts = computed(() => {
    const q = editAccountProductSearch.value.trim().toLowerCase()
    const selectedType = editAccountProductType?.value || ''
    return productsAll.value.filter((g) => {
      if (!matchesProductType(g, selectedType)) return false
      if (!q) return true
      return (g.title || '').toLowerCase().includes(q)
    })
  })

  return {
    sortedAccounts,
    filteredAccountProducts,
    filteredEditAccountProducts,
  }
}
