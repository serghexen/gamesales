export function useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  isSlotTypeSupportedForGame,
  slotTypes,
  accountsAll,
  editDeal,
  newDeal,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsLoadingEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
  dealGameAssignmentsLoadingNew,
  dealGameAssignmentsLoadingEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  dealSlotAvailabilityLoadingNew,
  dealSlotAvailabilityLoadingEdit,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealAccountsForGameLoading,
  accountSlotReleaseLoading,
  dealSlotAutoAssign,
  dealError,
  quickNewGame,
  quickEditGame,
  quickNewGameLoading,
  quickEditGameLoading,
  quickNewGameError,
  quickEditGameError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountLoading,
  quickEditAccountLoading,
  quickNewAccountError,
  quickEditAccountError,
  newDealGameSearch,
  editDealGameSearch,
  loadGamesAll,
  loadAccountsAll,
}) {
  // Быстрое создание игры прямо из формы сделки.
  async function createQuickGame(target) {
    const isEdit = target === 'edit'
    const state = isEdit ? quickEditGame : quickNewGame
    const loading = isEdit ? quickEditGameLoading : quickNewGameLoading
    const error = isEdit ? quickEditGameError : quickNewGameError
    error.value = ''
    if (!state.title) {
      error.value = 'Укажите название игры'
      return
    }
    if (!state.platform_codes.length) {
      error.value = 'Выберите платформу'
      return
    }
    loading.value = true
    try {
      const created = await apiPost(
        '/games',
        {
          title: state.title,
          platform_codes: state.platform_codes,
          short_title: null,
          link: null,
          logo_url: null,
          text_lang: null,
          audio_lang: null,
          vr_support: null,
          region_code: null,
        },
        { token: auth.state.token }
      )
      await loadGamesAll()
      if (created?.game_id) {
        if (isEdit) {
          editDeal.game_id = created.game_id
          editDealGameSearch.value = ''
        } else {
          newDeal.game_id = created.game_id
          newDealGameSearch.value = ''
        }
      }
      state.title = ''
      state.platform_codes = []
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  // Загружает подходящие аккаунты для выбранной игры и типа слота.
  async function loadDealAccountsForGame(target) {
    const isEdit = target === 'edit'
    const gameId = isEdit ? editDeal.game_id : newDeal.game_id
    const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
    if (!gameId || !slotTypeCode || !isSlotTypeSupportedForGame(slotTypeCode, gameId)) {
      if (isEdit) dealAccountsForGameEdit.value = []
      else dealAccountsForGameNew.value = []
      return
    }
    dealAccountsForGameLoading.value = true
    try {
      const params = new URLSearchParams()
      params.set('game_id', String(gameId))
      if (slotTypeCode) params.set('slot_type_code', slotTypeCode)
      const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
      if (isEdit) {
        let list = data || []
        const currentId = editDeal.account_id
        if (currentId && !list.find((a) => a.account_id === currentId)) {
          const fallback = (accountsAll.value || []).find((a) => a.account_id === currentId)
          if (fallback) list = [fallback, ...list]
        }
        dealAccountsForGameEdit.value = list
      } else {
        dealAccountsForGameNew.value = data || []
      }
    } catch {
      if (isEdit) dealAccountsForGameEdit.value = []
      else dealAccountsForGameNew.value = []
    } finally {
      dealAccountsForGameLoading.value = false
    }
  }

  // Загружает состояние слотов выбранного аккаунта.
  async function loadAccountSlotStatus(target) {
    const isEdit = target === 'edit'
    const accountId = isEdit ? editDeal.account_id : newDeal.account_id
    if (!accountId) {
      if (isEdit) accountSlotStatusEdit.value = []
      else accountSlotStatusNew.value = []
      return
    }
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-status`, { token: auth.state.token })
      if (isEdit) accountSlotStatusEdit.value = data || []
      else accountSlotStatusNew.value = data || []
    } catch {
      if (isEdit) accountSlotStatusEdit.value = []
      else accountSlotStatusNew.value = []
    }
  }

  // Загружает назначения слотов по выбранному аккаунту.
  async function loadDealAccountAssignments(target) {
    const isEdit = target === 'edit'
    const accountId = isEdit ? editDeal.account_id : newDeal.account_id
    if (!accountId) {
      if (isEdit) dealAccountAssignmentsEdit.value = []
      else dealAccountAssignmentsNew.value = []
      return
    }
    const loading = isEdit ? dealAccountAssignmentsLoadingEdit : dealAccountAssignmentsLoadingNew
    loading.value = true
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      if (isEdit) dealAccountAssignmentsEdit.value = data || []
      else dealAccountAssignmentsNew.value = data || []
    } catch {
      if (isEdit) dealAccountAssignmentsEdit.value = []
      else dealAccountAssignmentsNew.value = []
    } finally {
      loading.value = false
    }
  }

  // Загружает назначения слотов по выбранной игре.
  async function loadDealGameAssignments(target) {
    const isEdit = target === 'edit'
    const gameId = isEdit ? editDeal.game_id : newDeal.game_id
    if (!gameId) {
      if (isEdit) dealGameAssignmentsEdit.value = []
      else dealGameAssignmentsNew.value = []
      return
    }
    const loading = isEdit ? dealGameAssignmentsLoadingEdit : dealGameAssignmentsLoadingNew
    loading.value = true
    try {
      const data = await apiGet(`/games/${gameId}/slot-assignments`, { token: auth.state.token })
      if (isEdit) dealGameAssignmentsEdit.value = data || []
      else dealGameAssignmentsNew.value = data || []
    } catch {
      if (isEdit) dealGameAssignmentsEdit.value = []
      else dealGameAssignmentsNew.value = []
    } finally {
      loading.value = false
    }
  }

  // Загружает доступность слотов для выбранной игры.
  async function loadDealSlotAvailability(target) {
    const isEdit = target === 'edit'
    const gameId = isEdit ? editDeal.game_id : newDeal.game_id
    if (!gameId) {
      if (isEdit) dealSlotAvailabilityEdit.value = {}
      else dealSlotAvailabilityNew.value = {}
      return
    }
    const loading = isEdit ? dealSlotAvailabilityLoadingEdit : dealSlotAvailabilityLoadingNew
    loading.value = true
    try {
      const list = slotTypes.value || []
      let availabilityMap = {}
      let availabilityLoaded = false
      try {
        const data = await apiGet(`/accounts/for-deal/availability?game_id=${encodeURIComponent(gameId)}`, { token: auth.state.token })
        availabilityMap = Object.fromEntries((data || []).map((i) => [i.slot_type_code, { hasFree: Boolean(i.has_free) }]))
        availabilityLoaded = true
      } catch {
        availabilityMap = {}
      }
      if (!availabilityLoaded) {
        const results = await Promise.all(
          list.map(async (t) => {
            const supported = isSlotTypeSupportedForGame(t.code, gameId)
            if (!supported) {
              return [t.code, { hasFree: false }]
            }
            try {
              const params = new URLSearchParams()
              params.set('game_id', String(gameId))
              params.set('slot_type_code', t.code)
              const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
              return [t.code, { hasFree: Array.isArray(data) && data.length > 0 }]
            } catch {
              return [t.code, { hasFree: false }]
            }
          })
        )
        availabilityMap = Object.fromEntries(results)
      }
      if (availabilityLoaded) {
        const normalized = {}
        for (const t of list) {
          const supported = isSlotTypeSupportedForGame(t.code, gameId)
          normalized[t.code] = supported ? (availabilityMap[t.code] || { hasFree: false }) : { hasFree: false }
        }
        availabilityMap = normalized
      }
      if (isEdit) dealSlotAvailabilityEdit.value = availabilityMap
      else dealSlotAvailabilityNew.value = availabilityMap
    } finally {
      loading.value = false
    }
  }

  async function releaseSlotFromDeal(item, target) {
    if (!item?.assignment_id) return
    if (!window.confirm('Снять слот у покупателя?')) return
    accountSlotReleaseLoading.value = true
    try {
      await apiPost(`/slot-assignments/${item.assignment_id}/release`, {}, { token: auth.state.token })
      const accountId = item.account_id
      const slotTypeCode = item.slot_type_code
      dealSlotAutoAssign.value = true
      if (target === 'edit') {
        editDeal.account_id = accountId || ''
        editDeal.slot_type_code = slotTypeCode || ''
        await loadAccountSlotStatus('edit')
        await loadDealAccountAssignments('edit')
        await loadDealAccountsForGame('edit')
        await loadDealGameAssignments('edit')
        await loadDealSlotAvailability('edit')
      } else {
        newDeal.account_id = accountId || ''
        newDeal.slot_type_code = slotTypeCode || ''
        await loadAccountSlotStatus('new')
        await loadDealAccountAssignments('new')
        await loadDealAccountsForGame('new')
        await loadDealGameAssignments('new')
        await loadDealSlotAvailability('new')
      }
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      dealSlotAutoAssign.value = false
      accountSlotReleaseLoading.value = false
    }
  }

  async function createQuickAccount(target) {
    const isEdit = target === 'edit'
    const state = isEdit ? quickEditAccount : quickNewAccount
    const loading = isEdit ? quickEditAccountLoading : quickNewAccountLoading
    const error = isEdit ? quickEditAccountError : quickNewAccountError
    error.value = ''
    if (!state.login_name) {
      error.value = 'Укажите логин'
      return
    }
    if (!state.domain_code) {
      error.value = 'Выберите домен'
      return
    }
    if (!state.platform_codes.length) {
      error.value = 'Выберите платформу'
      return
    }
    loading.value = true
    try {
      const created = await apiPost(
        '/accounts',
        {
          login_name: state.login_name,
          domain_code: state.domain_code,
          region_code: isEdit ? editDeal.region_code || null : newDeal.region_code || null,
          account_date: null,
          notes: null,
        },
        { token: auth.state.token }
      )
      await loadAccountsAll()
      const selectedGameId = isEdit ? editDeal.game_id : newDeal.game_id
      if (created?.account_id && selectedGameId) {
        try {
          const existing = await apiGet(`/accounts/${created.account_id}/games`, { token: auth.state.token })
          const ids = new Set((existing || []).map((g) => g.game_id))
          ids.add(selectedGameId)
          await apiPut(
            `/accounts/${created.account_id}/games`,
            { game_ids: Array.from(ids) },
            { token: auth.state.token }
          )
        } catch {
          // ignore game attachment errors
        }
      }
      if (created?.account_id) {
        if (isEdit) {
          editDeal.account_id = created.account_id
        } else {
          newDeal.account_id = created.account_id
        }
      }
      if (created?.account_id) {
        const targetList = isEdit ? dealAccountsForGameEdit : dealAccountsForGameNew
        const exists = (targetList.value || []).some((a) => a.account_id === created.account_id)
        if (!exists) {
          const fallback = (accountsAll.value || []).find((a) => a.account_id === created.account_id) || created
          targetList.value = [fallback, ...(targetList.value || [])]
        }
        if (isEdit) {
          dealGameAssignmentsEdit.value = []
        } else {
          dealGameAssignmentsNew.value = []
        }
      }
      if (isEdit) {
        await loadDealSlotAvailability('edit')
        await loadDealAccountsForGame('edit')
      } else {
        await loadDealSlotAvailability('new')
        await loadDealAccountsForGame('new')
      }
      state.login_name = ''
      state.domain_code = ''
      state.platform_codes = []
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  function clearNewDealGame() {
    newDeal.game_id = ''
    newDealGameSearch.value = ''
    dealAccountsForGameNew.value = []
  }

  function clearEditDealGame() {
    editDeal.game_id = ''
    editDealGameSearch.value = ''
    dealAccountsForGameEdit.value = []
  }

  return {
    createQuickGame,
    createQuickAccount,
    clearNewDealGame,
    clearEditDealGame,
    loadDealAccountsForGame,
    loadAccountSlotStatus,
    loadDealAccountAssignments,
    loadDealGameAssignments,
    loadDealSlotAvailability,
    releaseSlotFromDeal,
  }
}
