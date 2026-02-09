export function useCatalogs({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  closeAllModals,
  resetModalPos,
  showDomainForm,
  showSourceForm,
  showPlatformForm,
  showRegionForm,
  newDomain,
  editDomain,
  domainEditMode,
  newSource,
  editSource,
  sourceEditMode,
  newPlatform,
  editPlatform,
  platformEditMode,
  newRegion,
  editRegion,
  regionEditMode,
  catalogsError,
  catalogsOk,
  catalogsLoading,
  catalogSaving,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  newDeal,
  editDeal,
  loadDealSlotAvailability,
}) {
  // Загружает базовые справочники для форм: платформы и регионы.
  async function loadCatalogs() {
    catalogsLoading.value = true
    try {
      const [p, r] = await Promise.all([
        apiGet('/platforms', { token: auth.state.token }),
        apiGet('/regions', { token: auth.state.token }),
      ])
      platforms.value = p || []
      regions.value = r || []
    } catch {
      platforms.value = []
      regions.value = []
    } finally {
      catalogsLoading.value = false
    }
  }

  // Загружает типы слотов и обновляет доступность в формах сделок.
  async function loadSlotTypes() {
    try {
      const data = await apiGet('/slot-types', { token: auth.state.token })
      slotTypes.value = data || []
      if (newDeal.game_id) loadDealSlotAvailability('new')
      if (editDeal.open && editDeal.game_id) loadDealSlotAvailability('edit')
    } catch {
      slotTypes.value = []
    }
  }

  // Загружает список доменов.
  async function loadDomains() {
    catalogsLoading.value = true
    try {
      const d = await apiGet('/domains', { token: auth.state.token })
      domains.value = d || []
    } catch {
      domains.value = []
    } finally {
      catalogsLoading.value = false
    }
  }

  // Загружает список источников.
  async function loadSources() {
    catalogsLoading.value = true
    try {
      const s = await apiGet('/sources', { token: auth.state.token })
      sources.value = s || []
    } catch {
      sources.value = []
    } finally {
      catalogsLoading.value = false
    }
  }

  // Открывает домен в режиме просмотра/редактирования.
  function openEditDomain(d) {
    closeAllModals()
    resetModalPos()
    showDomainForm.value = false
    editDomain.open = true
    editDomain.name = d.name
    editDomain.original = d.name
    domainEditMode.value = 'view'
  }

  function cancelEditDomain() {
    editDomain.open = false
    editDomain.name = ''
    editDomain.original = ''
    domainEditMode.value = 'view'
  }

  // Открывает модалку создания домена.
  function openDomainModal() {
    closeAllModals()
    resetModalPos()
    showDomainForm.value = true
    cancelEditDomain()
    catalogsError.value = null
    catalogsOk.value = null
  }

  function closeDomainModal() {
    showDomainForm.value = false
    cancelEditDomain()
    catalogsError.value = null
    catalogsOk.value = null
    newDomain.value = ''
  }

  // Сохраняет изменения домена.
  async function saveEditDomain() {
    if (!editDomain.name) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPut(`/domains/${encodeURIComponent(editDomain.original)}`, { name: editDomain.name }, { token: auth.state.token })
      catalogsOk.value = 'Домен обновлён'
      await loadDomains()
      closeDomainModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  // Открывает источник в режиме просмотра/редактирования.
  function openEditSource(s) {
    closeAllModals()
    resetModalPos()
    showSourceForm.value = false
    editSource.open = true
    editSource.source_id = s.source_id
    editSource.code = s.code
    editSource.name = s.name
    sourceEditMode.value = 'view'
  }

  function cancelEditSource() {
    editSource.open = false
    editSource.source_id = null
    editSource.code = ''
    editSource.name = ''
    sourceEditMode.value = 'view'
  }

  function openSourceModal() {
    closeAllModals()
    resetModalPos()
    showSourceForm.value = true
    cancelEditSource()
    catalogsError.value = null
    catalogsOk.value = null
  }

  function closeSourceModal() {
    showSourceForm.value = false
    cancelEditSource()
    catalogsError.value = null
    catalogsOk.value = null
    newSource.code = ''
    newSource.name = ''
  }

  // Сохраняет изменения источника.
  async function saveEditSource() {
    if (!editSource.source_id || !editSource.code || !editSource.name) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPut(
        `/sources/${encodeURIComponent(editSource.source_id)}`,
        { code: editSource.code, name: editSource.name },
        { token: auth.state.token }
      )
      catalogsOk.value = 'Источник обновлён'
      await loadSources()
      closeSourceModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  // Открывает платформу в режиме просмотра/редактирования.
  function openEditPlatform(p) {
    closeAllModals()
    resetModalPos()
    showPlatformForm.value = false
    editPlatform.open = true
    editPlatform.code = p.code
    editPlatform.name = p.name
    editPlatform.slot_capacity = p.slot_capacity || 0
    platformEditMode.value = 'view'
  }

  function cancelEditPlatform() {
    editPlatform.open = false
    editPlatform.code = ''
    editPlatform.name = ''
    editPlatform.slot_capacity = 0
    platformEditMode.value = 'view'
  }

  function openPlatformModal() {
    closeAllModals()
    resetModalPos()
    showPlatformForm.value = true
    cancelEditPlatform()
    catalogsError.value = null
    catalogsOk.value = null
  }

  function closePlatformModal() {
    showPlatformForm.value = false
    cancelEditPlatform()
    catalogsError.value = null
    catalogsOk.value = null
    newPlatform.code = ''
    newPlatform.name = ''
    newPlatform.slot_capacity = 0
  }

  async function saveEditPlatform() {
    if (!editPlatform.code || !editPlatform.name) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPut(
        `/platforms/${encodeURIComponent(editPlatform.code)}`,
        { name: editPlatform.name, slot_capacity: editPlatform.slot_capacity },
        { token: auth.state.token }
      )
      catalogsOk.value = 'Платформа обновлена'
      await loadCatalogs()
      closePlatformModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  function openEditRegion(r) {
    closeAllModals()
    resetModalPos()
    showRegionForm.value = false
    editRegion.open = true
    editRegion.code = r.code
    editRegion.name = r.name
    editRegion.purchase_cost_rate = Number(r.purchase_cost_rate ?? 1)
    regionEditMode.value = 'view'
  }

  function cancelEditRegion() {
    editRegion.open = false
    editRegion.code = ''
    editRegion.name = ''
    editRegion.purchase_cost_rate = 1
    regionEditMode.value = 'view'
  }

  function openRegionModal() {
    closeAllModals()
    resetModalPos()
    showRegionForm.value = true
    cancelEditRegion()
    catalogsError.value = null
    catalogsOk.value = null
  }

  function closeRegionModal() {
    showRegionForm.value = false
    cancelEditRegion()
    catalogsError.value = null
    catalogsOk.value = null
    newRegion.code = ''
    newRegion.name = ''
    newRegion.purchase_cost_rate = 1
  }

  async function saveEditRegion() {
    if (!editRegion.code || !editRegion.name) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPut(
        `/regions/${encodeURIComponent(editRegion.code)}`,
        { name: editRegion.name, purchase_cost_rate: editRegion.purchase_cost_rate },
        { token: auth.state.token }
      )
      catalogsOk.value = 'Регион обновлён'
      await loadCatalogs()
      closeRegionModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function createDomain() {
    catalogsError.value = null
    catalogsOk.value = null
    if (!newDomain.value) {
      catalogsError.value = 'Введите домен'
      return
    }
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPost('/domains', { name: newDomain.value }, { token: auth.state.token })
      catalogsOk.value = `Домен ${newDomain.value} добавлен`
      newDomain.value = ''
      await loadDomains()
      closeDomainModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function createSource() {
    catalogsError.value = null
    catalogsOk.value = null
    if (!newSource.code || !newSource.name) {
      catalogsError.value = 'Введите код и название источника'
      return
    }
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPost('/sources', newSource, { token: auth.state.token })
      catalogsOk.value = `Источник ${newSource.code} добавлен`
      newSource.code = ''
      newSource.name = ''
      await loadSources()
      closeSourceModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function createPlatform() {
    catalogsError.value = null
    catalogsOk.value = null
    if (!newPlatform.code || !newPlatform.name) {
      catalogsError.value = 'Введите код и название платформы'
      return
    }
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPost('/platforms', newPlatform, { token: auth.state.token })
      catalogsOk.value = `Платформа ${newPlatform.code} добавлена`
      newPlatform.code = ''
      newPlatform.name = ''
      newPlatform.slot_capacity = 0
      await loadCatalogs()
      closePlatformModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function createRegion() {
    catalogsError.value = null
    catalogsOk.value = null
    if (!newRegion.code || !newRegion.name) {
      catalogsError.value = 'Введите код и название региона'
      return
    }
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiPost('/regions', newRegion, { token: auth.state.token })
      catalogsOk.value = `Регион ${newRegion.code} добавлен`
      newRegion.code = ''
      newRegion.name = ''
      newRegion.purchase_cost_rate = 1
      await loadCatalogs()
      closeRegionModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function deleteDomain(name) {
    if (!window.confirm(`Удалить домен ${name}?`)) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiDelete(`/domains/${encodeURIComponent(name)}`, { token: auth.state.token })
      catalogsOk.value = `Домен ${name} удалён`
      await loadDomains()
      if (editDomain.open && editDomain.original === name) closeDomainModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function deleteSource(sourceId) {
    if (!sourceId) return
    if (!window.confirm('Удалить источник?')) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiDelete(`/sources/${encodeURIComponent(sourceId)}`, { token: auth.state.token })
      catalogsOk.value = 'Источник удалён'
      await loadSources()
      if (editSource.open && editSource.source_id === sourceId) closeSourceModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function deletePlatform(code) {
    if (!window.confirm(`Удалить платформу ${code}?`)) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiDelete(`/platforms/${encodeURIComponent(code)}`, { token: auth.state.token })
      catalogsOk.value = `Платформа ${code} удалена`
      await loadCatalogs()
      if (editPlatform.open && editPlatform.code === code) closePlatformModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  async function deleteRegion(code) {
    if (!window.confirm(`Удалить регион ${code}?`)) return
    catalogsError.value = null
    catalogsOk.value = null
    catalogsLoading.value = true
    catalogSaving.value = true
    try {
      await apiDelete(`/regions/${encodeURIComponent(code)}`, { token: auth.state.token })
      catalogsOk.value = `Регион ${code} удалён`
      await loadCatalogs()
      if (editRegion.open && editRegion.code === code) closeRegionModal()
    } catch (e) {
      catalogsError.value = mapApiError(e?.message)
    } finally {
      catalogsLoading.value = false
      catalogSaving.value = false
    }
  }

  return {
    loadCatalogs,
    loadSlotTypes,
    loadDomains,
    loadSources,
    openEditDomain,
    cancelEditDomain,
    openDomainModal,
    closeDomainModal,
    saveEditDomain,
    openEditSource,
    cancelEditSource,
    openSourceModal,
    closeSourceModal,
    saveEditSource,
    openEditPlatform,
    cancelEditPlatform,
    openPlatformModal,
    closePlatformModal,
    saveEditPlatform,
    openEditRegion,
    cancelEditRegion,
    openRegionModal,
    closeRegionModal,
    saveEditRegion,
    createDomain,
    createSource,
    createPlatform,
    createRegion,
    deleteDomain,
    deleteSource,
    deletePlatform,
    deleteRegion,
  }
}
