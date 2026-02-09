import { computed, watch } from 'vue'

export function useGamesViewState({
  games,
  gamesTotal,
  gamesPage,
  gamesPageInput,
  gamesPageSize,
  loadGames,
  gameAccounts,
  gameAccountsSort,
  gameAccountsPage,
  gameAccountsPageSize,
}) {
  // Количество страниц в списке игр.
  const gamesTotalPages = computed(() => {
    const pages = Math.ceil(gamesTotal.value / gamesPageSize.value)
    return pages > 0 ? pages : 1
  })

  // Локально можно расширить сортировку игр, сейчас отдаем как есть.
  const sortedGames = computed(() => [...games.value])
  const pagedGames = computed(() => sortedGames.value)

  // Если страниц стало меньше, держим текущую страницу в рамках.
  watch(gamesTotalPages, (total) => {
    if (gamesPage.value > total) gamesPage.value = total
  })

  // Синхронизируем поле ввода страницы и реальную страницу.
  watch(gamesPage, (val) => {
    gamesPageInput.value = val
  })

  // При смене размера страницы перезагружаем список с первой страницы.
  watch(gamesPageSize, () => {
    gamesPage.value = 1
    loadGames()
  })

  // Сортировка аккаунтов внутри модалки игры.
  const sortedGameAccounts = computed(() => {
    const list = [...gameAccounts.value]
    const { key, dir } = gameAccountsSort.value
    list.sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' && typeof bv === 'number') {
        return dir === 'asc' ? av - bv : bv - av
      }
      return dir === 'asc'
        ? String(av || '').localeCompare(String(bv || ''))
        : String(bv || '').localeCompare(String(av || ''))
    })
    return list
  })

  // Количество страниц в таблице аккаунтов игры.
  const gameAccountsTotalPages = computed(() => {
    const pages = Math.ceil(sortedGameAccounts.value.length / gameAccountsPageSize)
    return pages > 0 ? pages : 1
  })

  // Текущая страница аккаунтов игры.
  const pagedGameAccounts = computed(() => {
    const start = (gameAccountsPage.value - 1) * gameAccountsPageSize
    return sortedGameAccounts.value.slice(start, start + gameAccountsPageSize)
  })

  return {
    gamesTotalPages,
    sortedGames,
    pagedGames,
    gameAccountsTotalPages,
    pagedGameAccounts,
  }
}
