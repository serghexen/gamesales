import { computed } from 'vue'

export function useAccountsDerivedState({
  accounts,
  productsAll,
  accountProductSearch,
  editAccountProductSearch,
}) {
  // Здесь можно добавить локальную сортировку аккаунтов при необходимости.
  const sortedAccounts = computed(() => [...accounts.value])

  // Фильтр товаров для формы создания аккаунта.
  const filteredAccountProducts = computed(() => {
    const q = accountProductSearch.value.trim().toLowerCase()
    if (!q) return productsAll.value
    return productsAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
  })

  // Фильтр товаров для формы редактирования аккаунта.
  const filteredEditAccountProducts = computed(() => {
    const q = editAccountProductSearch.value.trim().toLowerCase()
    if (!q) return productsAll.value
    return productsAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
  })

  return {
    sortedAccounts,
    filteredAccountProducts,
    filteredEditAccountProducts,
  }
}
