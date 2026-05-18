import { computed, watch } from 'vue'

export function useAccountsViewState({
  accountsTotal,
  accountsPage,
  accountsPageInput,
  accountsPageSize,
  loadAccounts,
}) {
  // Количество страниц в списке аккаунтов.
  const accountsTotalPages = computed(() => {
    const pages = Math.ceil(accountsTotal.value / accountsPageSize.value)
    return pages > 0 ? pages : 1
  })

  // Если страниц стало меньше, текущая страница не должна выходить за пределы.
  watch(accountsTotalPages, (total) => {
    if (accountsPage.value <= total) return
    // Если после фильтрации ушли на несуществующую страницу, догружаем последнюю доступную.
    accountsPage.value = total
    if (accountsTotal.value > 0) {
      loadAccounts()
    }
  })

  // Синхронизируем поле ввода страницы и реальную страницу.
  watch(accountsPage, (val) => {
    accountsPageInput.value = val
  })

  // При смене размера страницы грузим первую страницу.
  watch(accountsPageSize, () => {
    accountsPage.value = 1
    loadAccounts()
  })

  return {
    accountsTotalPages,
  }
}
