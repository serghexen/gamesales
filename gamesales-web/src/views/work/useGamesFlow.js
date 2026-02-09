import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'

export function useGamesFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiPostFormWithProgress,
  mapApiError,
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showGameForm,
  gameEditMode,
  editGame,
  newGame,
  gameError,
  gameOk,
  gamesLoading,
  gameLoading,
  gameSaving,
  games,
  gamesAll,
  gamesTotal,
  gamesSort,
  gamesPage,
  gamesPageSize,
  gameFilters,
  gameFilterDraft,
  accountFilters,
  gameAccounts,
  gameAccountsLoading,
  gameAccountsError,
  gameAccountsPage,
  gameSlotAssignments,
  gameSlotAssignmentsError,
  gameSlotAssignmentsLoading,
  gameLogoLoading,
  gameLogoUploading,
  gameLogoProgress,
  gameLogoCache,
  readLogoCache,
  writeLogoCache,
  clearLogoCache,
  loadGameSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
}) {
  let initialEditGameSnapshot = null
  // Открывает игру в режиме просмотра и подгружает логотип.
  function startEditGame(game) {
    closeAllModals()
    resetModalPos()
    showGameForm.value = false
    editGame.open = true
    gameEditMode.value = 'view'
    editGame.game_id = game.game_id
    editGame.title = game.title || ''
    editGame.short_title = game.short_title || ''
    editGame.link = game.link || ''
    editGame.logo_url = game.logo_url || ''
    editGame.logo_b64 = ''
    editGame.logo_mime = ''
    editGame.text_lang = game.text_lang || ''
    editGame.audio_lang = game.audio_lang || ''
    editGame.vr_support = game.vr_support || ''
    editGame.platform_codes = Array.isArray(game.platform_codes) ? [...game.platform_codes] : []
    editGame.region_code = game.region_code || ''
    // Сохраняем исходные данные для проверки несохраненных правок.
    initialEditGameSnapshot = {
      title: editGame.title,
      short_title: editGame.short_title,
      link: editGame.link,
      logo_url: editGame.logo_url,
      text_lang: editGame.text_lang,
      audio_lang: editGame.audio_lang,
      vr_support: editGame.vr_support,
      platform_codes: [...(editGame.platform_codes || [])],
      region_code: editGame.region_code,
      logo_b64: '',
      logo_mime: '',
    }
    loadGameLogo(game.game_id)
  }

  // Очищает состояние редактирования игры.
  function cancelEditGame() {
    editGame.open = false
    editGame.game_id = null
    gameEditMode.value = 'view'
    editGame.title = ''
    editGame.short_title = ''
    editGame.link = ''
    editGame.logo_url = ''
    editGame.logo_b64 = ''
    editGame.logo_mime = ''
    editGame.text_lang = ''
    editGame.audio_lang = ''
    editGame.vr_support = ''
    editGame.platform_codes = []
    editGame.region_code = ''
    gameLogoLoading.value = false
    gameLogoUploading.value = false
    gameLogoProgress.value = 0
    gameSlotAssignments.value = []
    gameSlotAssignmentsError.value = null
    gameSlotAssignmentsLoading.value = false
    initialEditGameSnapshot = null
  }

  // Открывает форму создания новой игры.
  function openCreateGameModal() {
    closeAllModals()
    resetModalPos()
    showGameForm.value = true
    gameEditMode.value = 'edit'
    cancelEditGame()
    gameError.value = null
    gameOk.value = null
  }

  // Закрывает модалку игры и очищает все временные поля.
  async function closeGameModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const createDirty = showGameForm.value && !isSameNormalized(newGame, {
      title: '',
      short_title: '',
      link: '',
      logo_url: '',
      text_lang: '',
      audio_lang: '',
      vr_support: '',
      platform_codes: [],
      region_code: '',
    })
    const editCurrent = {
      title: editGame.title,
      short_title: editGame.short_title,
      link: editGame.link,
      logo_url: editGame.logo_url,
      text_lang: editGame.text_lang,
      audio_lang: editGame.audio_lang,
      vr_support: editGame.vr_support,
      platform_codes: [...(editGame.platform_codes || [])],
      region_code: editGame.region_code,
      logo_b64: editGame.logo_b64 || '',
      logo_mime: editGame.logo_mime || '',
    }
    const editDirty = editGame.open && gameEditMode.value === 'edit' && !isSameNormalized(editCurrent, initialEditGameSnapshot || {})
    if (guardEnabled && !(await confirmDiscardIfNeeded(createDirty || editDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showGameForm.value = false
    cancelEditGame()
    gameError.value = null
    gameOk.value = null
    gameAccounts.value = []
    gameAccountsError.value = null
    gameAccountsLoading.value = false
    gameSlotAssignments.value = []
    gameSlotAssignmentsError.value = null
    gameSlotAssignmentsLoading.value = false
    newGame.title = ''
    newGame.short_title = ''
    newGame.link = ''
    newGame.logo_url = ''
    newGame.text_lang = ''
    newGame.audio_lang = ''
    newGame.vr_support = ''
    newGame.platform_codes = []
    newGame.region_code = ''
    return true
  }

  // Открывает модалку игры и грузит связанные аккаунты/слоты.
  function openGameAccounts(game) {
    resetModalPos()
    startEditGame(game)
    gameAccounts.value = []
    gameAccountsPage.value = 1
    loadGameAccounts(game.game_id)
    loadGameSlotAssignments(game.game_id)
  }

  function refreshGameAccounts() {
    if (editGame.game_id) {
      gameAccountsPage.value = 1
      loadGameAccounts(editGame.game_id)
    }
  }

  // Загружает логотип игры (сначала из кэша, потом из API).
  async function loadGameLogo(gameId) {
    editGame.logo_b64 = ''
    editGame.logo_mime = ''
    gameLogoLoading.value = true
    if (gameLogoCache.has(gameId)) {
      const cached = gameLogoCache.get(gameId)
      editGame.logo_b64 = cached?.data_b64 || ''
      editGame.logo_mime = cached?.mime || ''
      gameLogoLoading.value = false
      return
    }
    const stored = readLogoCache(gameId)
    if (stored) {
      editGame.logo_b64 = stored?.data_b64 || ''
      editGame.logo_mime = stored?.mime || ''
      gameLogoCache.set(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
      gameLogoLoading.value = false
      return
    }
    try {
      const res = await apiGet(`/games/${gameId}/logo`, { token: auth.state.token })
      editGame.logo_b64 = res?.data_b64 || ''
      editGame.logo_mime = res?.mime || ''
      gameLogoCache.set(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
      writeLogoCache(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
    } catch {
      // no logo or error, ignore
    } finally {
      gameLogoLoading.value = false
      if (editGame.open && gameEditMode.value === 'view' && initialEditGameSnapshot) {
        initialEditGameSnapshot.logo_b64 = editGame.logo_b64 || ''
        initialEditGameSnapshot.logo_mime = editGame.logo_mime || ''
      }
    }
  }

  // Загружает новый логотип игры с прогрессом.
  async function onGameLogoSelected(event) {
    const file = event?.target?.files?.[0]
    if (!file || !editGame.game_id) return
    const form = new FormData()
    form.append('file', file)
    gameLogoLoading.value = true
    gameLogoUploading.value = true
    gameLogoProgress.value = 0
    try {
      await apiPostFormWithProgress(`/games/${editGame.game_id}/logo`, form, {
        token: auth.state.token,
        onProgress: (p) => { gameLogoProgress.value = p },
      })
      gameLogoCache.delete(editGame.game_id)
      clearLogoCache(editGame.game_id)
      await loadGameLogo(editGame.game_id)
    } catch (e) {
      gameError.value = mapApiError(e?.message)
      gameLogoLoading.value = false
    } finally {
      gameLogoUploading.value = false
      event.target.value = ''
    }
  }

  // Удаляет логотип игры.
  async function removeGameLogo() {
    if (!editGame.game_id) return
    gameLogoLoading.value = true
    gameLogoUploading.value = false
    try {
      await apiDelete(`/games/${editGame.game_id}/logo`, { token: auth.state.token })
      editGame.logo_b64 = ''
      editGame.logo_mime = ''
      gameLogoCache.delete(editGame.game_id)
      clearLogoCache(editGame.game_id)
    } catch (e) {
      gameError.value = mapApiError(e?.message)
    } finally {
      gameLogoLoading.value = false
    }
  }

  // Загружает список игр для таблицы.
  async function loadGames() {
    gamesLoading.value = true
    try {
      const params = new URLSearchParams()
      if (gameFilters.q) params.set('q', gameFilters.q)
      if (gameFilters.platform_code) params.set('platform_code', gameFilters.platform_code)
      if (gameFilters.region_code) params.set('region_code', gameFilters.region_code)
      params.set('sort_key', gamesSort.value.key)
      params.set('sort_dir', gamesSort.value.dir)
      params.set('page', String(gamesPage.value))
      params.set('page_size', String(gamesPageSize.value))
      const res = await apiGet(`/games?${params.toString()}`, { token: auth.state.token })
      games.value = res?.items || []
      gamesTotal.value = Number(res?.total || 0)
    } catch {
      games.value = []
      gamesTotal.value = 0
    } finally {
      gamesLoading.value = false
    }
  }

  async function loadGamesAll() {
    try {
      const params = new URLSearchParams()
      params.set('all', 'true')
      params.set('sort_key', 'title')
      params.set('sort_dir', 'asc')
      const res = await apiGet(`/games?${params.toString()}`, { token: auth.state.token })
      gamesAll.value = res?.items || []
    } catch {
      gamesAll.value = []
    }
  }

  async function loadGameAccounts(gameId) {
    gameAccountsLoading.value = true
    gameAccountsError.value = null
    try {
      const data = await apiGet(`/games/${gameId}/accounts`, { token: auth.state.token })
      gameAccounts.value = data || []
    } catch (e) {
      gameAccountsError.value = mapApiError(e?.message)
      gameAccounts.value = []
    } finally {
      gameAccountsLoading.value = false
    }
  }

  async function createGame() {
    gameError.value = null
    gameOk.value = null
    if (!newGame.title) {
      gameError.value = 'Укажите название игры'
      return
    }
    gameLoading.value = true
    gameSaving.value = true
    try {
      await apiPost(
        '/games',
        {
          title: newGame.title,
          short_title: newGame.short_title || null,
          link: newGame.link || null,
          logo_url: newGame.logo_url || null,
          text_lang: newGame.text_lang || null,
          audio_lang: newGame.audio_lang || null,
          vr_support: newGame.vr_support || null,
          platform_codes: newGame.platform_codes || [],
          region_code: newGame.region_code || null,
        },
        { token: auth.state.token }
      )
      gameOk.value = `Игра “${newGame.title}” добавлена`
      newGame.title = ''
      newGame.short_title = ''
      newGame.link = ''
      newGame.logo_url = ''
      newGame.text_lang = ''
      newGame.audio_lang = ''
      newGame.vr_support = ''
      newGame.platform_codes = []
      newGame.region_code = ''
      await loadGames()
      await loadGamesAll()
      closeGameModal()
    } catch (e) {
      gameError.value = mapApiError(e?.message)
    } finally {
      gameLoading.value = false
      gameSaving.value = false
    }
  }

  async function updateGame() {
    gameError.value = null
    gameOk.value = null
    if (!editGame.game_id) return
    if (!editGame.title) {
      gameError.value = 'Укажите название игры'
      return
    }
    gameLoading.value = true
    gameSaving.value = true
    try {
      await apiPut(
        `/games/${editGame.game_id}`,
        {
          title: editGame.title,
          short_title: editGame.short_title || null,
          link: editGame.link || null,
          logo_url: editGame.logo_url || null,
          text_lang: editGame.text_lang || null,
          audio_lang: editGame.audio_lang || null,
          vr_support: editGame.vr_support || null,
          platform_codes: editGame.platform_codes || [],
          region_code: editGame.region_code || null,
        },
        { token: auth.state.token }
      )
      gameOk.value = 'Игра обновлена'
      await loadGames()
      await loadGamesAll()
      cancelEditGame()
    } catch (e) {
      gameError.value = mapApiError(e?.message)
    } finally {
      gameLoading.value = false
      gameSaving.value = false
    }
  }

  async function deleteGame() {
    gameError.value = null
    gameOk.value = null
    if (!editGame.game_id) return
    if (!window.confirm('Архивировать игру?')) return
    gameLoading.value = true
    gameSaving.value = true
    try {
      await apiDelete(`/games/${editGame.game_id}`, { token: auth.state.token })
      gameOk.value = 'Игра архивирована'
      await loadGames()
      await loadGamesAll()
      closeGameModal()
    } catch (e) {
      gameError.value = mapApiError(e?.message)
    } finally {
      gameLoading.value = false
      gameSaving.value = false
    }
  }

  function goToAccount(login) {
    setActiveTab('accounts')
    accountFilters.login_q = login || ''
  }

  async function openDealGame(deal) {
    if (!deal || !deal.game_id) return
    setActiveTab('games')
    gameFilters.q = deal.game_title || ''
    gameFilters.platform_code = ''
    gameFilters.region_code = ''
    gameFilterDraft.title = gameFilters.q
    gameFilterDraft.platform = ''
    gameFilterDraft.region = ''
    gamesPage.value = 1
    await loadGames()
    if (!gamesAll.value.length) {
      await loadGamesAll()
    }
    const game = gamesAll.value.find((g) => g.game_id === deal.game_id) || games.value.find((g) => g.game_id === deal.game_id)
    if (game) {
      openGameAccounts(game)
    }
  }

  return {
    openGameAccounts,
    startEditGame,
    cancelEditGame,
    openCreateGameModal,
    closeGameModal,
    refreshGameAccounts,
    loadGameLogo,
    onGameLogoSelected,
    removeGameLogo,
    goToAccount,
    openDealGame,
    loadGames,
    loadGamesAll,
    loadGameAccounts,
    createGame,
    updateGame,
    deleteGame,
  }
}
