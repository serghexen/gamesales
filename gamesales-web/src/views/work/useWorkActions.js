export function useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
  loadDeals,
  loadAccounts,
  loadGames,
  accountsPage,
  accountsPageInput,
  gamesPage,
  gamesPageInput,
  newDeal,
  editDeal,
  newDealGameSearch,
  editDealGameSearch,
  quickNewGame,
  quickEditGame,
  quickNewGameError,
  quickEditGameError,
  accountSlotAssignments,
  accountSlotAssignmentsLoading,
  accountSlotAssignmentsError,
  gameSlotAssignments,
  gameSlotAssignmentsLoading,
  gameSlotAssignmentsError,
  accountSlotReleaseLoading,
  editAccount,
  showDealForm,
  dealError,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealAccountsForGame,
  loadDealGameAssignments,
  gameAccountsSort,
  gameAccountsPage,
  gameAccountsTotalPages,
  closeGameModal,
  goToAccount,
}) {
  // Переход из карточки игры прямо к аккаунту.
  function openAccountFromGame(login) {
    if (!login) return
    closeGameModal()
    goToAccount(login)
  }

  // Применяет поиск по сделкам.
  function applyDealSearch() {
    loadDeals(1)
  }

  // Применяет поиск по аккаунтам.
  function applyAccountSearch() {
    accountsPage.value = 1
    accountsPageInput.value = 1
    loadAccounts()
  }

  // Применяет поиск по играм.
  function applyGameSearch() {
    gamesPage.value = 1
    gamesPageInput.value = 1
    loadGames()
  }

  function syncNewDealGameSearch() {
    newDealGameSearch.value = ''
  }

  function syncEditDealGameSearch() {
    editDealGameSearch.value = ''
  }

  function onNewDealGameSearch() {
    if (newDeal.game_id) newDeal.game_id = ''
    quickNewGameError.value = ''
    if (newDealGameSearch.value) quickNewGame.title = newDealGameSearch.value
  }

  function onEditDealGameSearch() {
    if (editDeal.game_id) editDeal.game_id = ''
    quickEditGameError.value = ''
    if (editDealGameSearch.value) quickEditGame.title = editDealGameSearch.value
  }

  // Подгружает назначения слотов у аккаунта для модалки аккаунта.
  async function loadAccountSlotAssignments(accountId) {
    if (!accountId) {
      accountSlotAssignments.value = []
      return
    }
    accountSlotAssignmentsLoading.value = true
    accountSlotAssignmentsError.value = null
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      accountSlotAssignments.value = data || []
    } catch (e) {
      accountSlotAssignmentsError.value = mapApiError(e?.message)
      accountSlotAssignments.value = []
    } finally {
      accountSlotAssignmentsLoading.value = false
    }
  }

  // Подгружает назначения слотов у игры для модалки игры.
  async function loadGameSlotAssignments(gameId) {
    if (!gameId) {
      gameSlotAssignments.value = []
      return
    }
    gameSlotAssignmentsLoading.value = true
    gameSlotAssignmentsError.value = null
    try {
      const data = await apiGet(`/games/${gameId}/slot-assignments`, { token: auth.state.token })
      gameSlotAssignments.value = data || []
    } catch (e) {
      gameSlotAssignmentsError.value = mapApiError(e?.message)
      gameSlotAssignments.value = []
    } finally {
      gameSlotAssignmentsLoading.value = false
    }
  }

  // Снимает слот у покупателя и обновляет связанные данные на форме.
  async function releaseSlotAssignment(assignmentId) {
    if (!assignmentId) return
    if (!window.confirm('Снять слот у покупателя?')) return
    accountSlotReleaseLoading.value = true
    try {
      await apiPost(`/slot-assignments/${assignmentId}/release`, {}, { token: auth.state.token })
      if (editAccount.open && editAccount.account_id) {
        await loadAccountSlotAssignments(editAccount.account_id)
      }
      if (editDeal.open && editDeal.account_id) {
        await loadAccountSlotStatus('edit')
        await loadDealAccountAssignments('edit')
        await loadDealAccountsForGame('edit')
      }
      if (showDealForm.value && newDeal.account_id) {
        await loadAccountSlotStatus('new')
        await loadDealAccountAssignments('new')
        await loadDealAccountsForGame('new')
      }
      if (editDeal.open) {
        await loadDealGameAssignments('edit')
      }
      if (showDealForm.value) {
        await loadDealGameAssignments('new')
      }
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      accountSlotReleaseLoading.value = false
    }
  }

  // Переключает сортировку таблицы аккаунтов внутри модалки игры.
  function sortGameAccounts(key) {
    const current = gameAccountsSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      gameAccountsSort.value = { key, dir: 'asc' }
    }
    gameAccountsPage.value = 1
  }

  function nextGameAccountsPage() {
    if (gameAccountsPage.value < gameAccountsTotalPages.value) {
      gameAccountsPage.value += 1
    }
  }

  function prevGameAccountsPage() {
    if (gameAccountsPage.value > 1) {
      gameAccountsPage.value -= 1
    }
  }

  return {
    openAccountFromGame,
    applyDealSearch,
    applyAccountSearch,
    applyGameSearch,
    syncNewDealGameSearch,
    syncEditDealGameSearch,
    onNewDealGameSearch,
    onEditDealGameSearch,
    loadAccountSlotAssignments,
    loadGameSlotAssignments,
    releaseSlotAssignment,
    sortGameAccounts,
    nextGameAccountsPage,
    prevGameAccountsPage,
  }
}
