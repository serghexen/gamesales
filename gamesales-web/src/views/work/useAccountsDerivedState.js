import { computed } from 'vue'

export function useAccountsDerivedState({
  accounts,
  gamesAll,
  accountGameSearch,
  editAccountGameSearch,
}) {
  // Здесь можно добавить локальную сортировку аккаунтов при необходимости.
  const sortedAccounts = computed(() => [...accounts.value])

  // Фильтр игр для формы создания аккаунта.
  const filteredAccountGames = computed(() => {
    const q = accountGameSearch.value.trim().toLowerCase()
    if (!q) return gamesAll.value
    return gamesAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
  })

  // Фильтр игр для формы редактирования аккаунта.
  const filteredEditAccountGames = computed(() => {
    const q = editAccountGameSearch.value.trim().toLowerCase()
    if (!q) return gamesAll.value
    return gamesAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
  })

  return {
    sortedAccounts,
    filteredAccountGames,
    filteredEditAccountGames,
  }
}
