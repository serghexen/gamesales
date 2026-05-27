import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'

export function useUserProfileFlow({
  auth,
  router,
  isAdmin,
  canViewUsersSection,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  closeAllModals,
  resetModalPos,
  apiOk,
  loading,
  error,
  users,
  roles,
  userError,
  userOk,
  userLoading,
  showUserForm,
  userFormMode,
  newUser,
  editUser,
  editUserInitial,
  pwdError,
  pwdOk,
  pwdLoading,
  showPwdForm,
  pwdForm,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
}) {
  const userCreateDefaults = { username: '', password: '', name: '', role_code: 'manager' }
  const userEditDefaults = { username: '', name: '', role_code: 'manager', created_at: '' }

  // Очищает форму создания и возвращает дефолтные значения.
  function resetCreateUser() {
    newUser.username = userCreateDefaults.username
    newUser.password = userCreateDefaults.password
    newUser.name = userCreateDefaults.name
    newUser.role_code = userCreateDefaults.role_code
  }

  // Очищает форму просмотра/редактирования пользователя.
  function resetEditUser() {
    editUser.username = userEditDefaults.username
    editUser.name = userEditDefaults.name
    editUser.role_code = userEditDefaults.role_code
    editUser.created_at = userEditDefaults.created_at
    editUserInitial.value = { ...userEditDefaults }
  }

  // Закрывает модалку программно, чтобы confirm не срабатывал после успешного сохранения.
  async function closeModalSilently(closeFn) {
    if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
    try {
      return await closeFn()
    } finally {
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
    }
  }

  // Простая проверка, что API доступен.
  async function checkApi() {
    loading.value = true
    error.value = null
    try {
      await apiGet('/health', { token: auth.state.token })
      apiOk.value = true
    } catch (e) {
      apiOk.value = false
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  // Загружает роли и список пользователей для ролей с правом users.
  async function loadUsers() {
    const canViewUsers = canViewUsersSection?.value ?? isAdmin?.value
    if (!canViewUsers) return
    userLoading.value = true
    userError.value = null
    try {
      const rolesData = await apiGet('/user-roles', { token: auth.state.token })
      roles.value = rolesData || []
      const data = await apiGet('/users', { token: auth.state.token })
      users.value = data || []
    } catch (e) {
      userError.value = mapApiError(e?.message)
    } finally {
      userLoading.value = false
    }
  }

  // Создает нового пользователя.
  async function createUser() {
    userError.value = null
    userOk.value = null
    if (!newUser.username || !newUser.password) {
      userError.value = 'Заполните логин и пароль'
      return
    }
    userLoading.value = true
    try {
      const payload = {
        username: String(newUser.username || '').trim(),
        password: String(newUser.password || ''),
        name: String(newUser.name || '').trim(),
        role_code: String(newUser.role_code || 'manager').trim() || 'manager',
      }
      await apiPost('/users', payload, { token: auth.state.token })
      userOk.value = `Пользователь ${newUser.username} создан`
      resetCreateUser()
      await loadUsers()
      await closeModalSilently(closeUserModal)
    } catch (e) {
      userError.value = mapApiError(e?.message)
    } finally {
      userLoading.value = false
    }
  }

  // Обновляет имя и роль выбранного пользователя из режима редактирования.
  async function updateUser() {
    userError.value = null
    userOk.value = null
    if (!editUser.username || !editUser.role_code) {
      userError.value = 'Выберите роль пользователя'
      return
    }
    userLoading.value = true
    try {
      const payload = {
        name: String(editUser.name || '').trim(),
        role_code: String(editUser.role_code || '').trim(),
      }
      await apiPut(
        `/users/${encodeURIComponent(editUser.username)}`,
        payload,
        { token: auth.state.token }
      )
      userOk.value = `Пользователь ${editUser.username} обновлен`
      await loadUsers()
      await closeModalSilently(closeUserModal)
    } catch (e) {
      userError.value = mapApiError(e?.message)
    } finally {
      userLoading.value = false
    }
  }

  // Сохраняет форму пользователя в зависимости от режима (создание/редактирование).
  async function submitUserForm() {
    if (userFormMode?.value === 'edit') {
      await updateUser()
      return
    }
    if (userFormMode?.value === 'view') {
      userError.value = 'Сначала включите режим редактирования'
      return
    }
    await createUser()
  }

  // Открывает модалку создания пользователя.
  function openUserModal() {
    closeAllModals()
    resetModalPos()
    // В режиме создания форма должна быть чистой и с дефолтной ролью manager.
    userFormMode.value = 'create'
    resetCreateUser()
    resetEditUser()
    showUserForm.value = true
    userError.value = null
    userOk.value = null
  }

  // Открывает карточку пользователя в режиме просмотра.
  function openUserViewModal(item) {
    closeAllModals()
    resetModalPos()
    const username = String(item?.username || '').trim()
    const name = String(item?.name || '').trim()
    const roleCode = String(item?.role || '').trim() || 'manager'
    const createdAt = String(item?.created_at || '').trim()
    userFormMode.value = 'view'
    editUser.username = username
    editUser.name = name
    editUser.role_code = roleCode
    editUser.created_at = createdAt
    editUserInitial.value = { username, name, role_code: roleCode, created_at: createdAt }
    showUserForm.value = true
    userError.value = null
    userOk.value = null
  }

  // Переводит карточку пользователя из просмотра в редактирование.
  function startUserEdit() {
    if (userFormMode.value !== 'view') return
    userFormMode.value = 'edit'
    editUserInitial.value = {
      username: String(editUser.username || '').trim(),
      name: String(editUser.name || '').trim(),
      role_code: String(editUser.role_code || 'manager').trim() || 'manager',
      created_at: String(editUser.created_at || '').trim(),
    }
    userError.value = null
    userOk.value = null
  }

  // Для совместимости старый метод открытия редактирования ведем в просмотр.
  function openUserRoleModal(item) {
    openUserViewModal(item)
  }

  // Закрывает модалку создания пользователя и чистит форму.
  async function closeUserModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const currentMode = String(userFormMode?.value || 'create')
    const isDirty = currentMode === 'edit'
      ? !isSameNormalized(editUser, editUserInitial.value || userEditDefaults)
      : (currentMode === 'create'
          ? !isSameNormalized(newUser, userCreateDefaults)
          : false)
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showUserForm.value = false
    userError.value = null
    userOk.value = null
    userFormMode.value = 'create'
    resetCreateUser()
    resetEditUser()
    return true
  }

  // Меняет пароль текущего пользователя.
  async function changePassword() {
    pwdError.value = null
    pwdOk.value = false
    if (!pwdForm.current || !pwdForm.next || !pwdForm.next2) {
      pwdError.value = 'Заполните все поля'
      return
    }
    if (pwdForm.next !== pwdForm.next2) {
      pwdError.value = 'Пароли не совпадают'
      return
    }
    pwdLoading.value = true
    try {
      await apiPost(
        '/auth/change-password',
        { current_password: pwdForm.current, new_password: pwdForm.next },
        { token: auth.state.token }
      )
      pwdOk.value = true
      pwdForm.current = ''
      pwdForm.next = ''
      pwdForm.next2 = ''
    } catch (e) {
      pwdError.value = mapApiError(e?.message)
    } finally {
      pwdLoading.value = false
    }
  }

  // Открывает модалку смены пароля.
  function openPwdModal() {
    closeAllModals()
    resetModalPos()
    showPwdForm.value = true
    pwdError.value = null
    pwdOk.value = false
  }

  // Закрывает модалку смены пароля и чистит поля.
  async function closePwdModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const isDirty = !isSameNormalized(pwdForm, { current: '', next: '', next2: '' })
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showPwdForm.value = false
    pwdError.value = null
    pwdOk.value = false
    pwdForm.current = ''
    pwdForm.next = ''
    pwdForm.next2 = ''
    return true
  }

  // Выход из аккаунта и переход на страницу логина.
  function onLogout() {
    auth.logout()
    router.replace('/login')
  }

  return {
    checkApi,
    loadUsers,
    createUser,
    updateUser,
    updateUserRole: updateUser,
    submitUserForm,
    openUserModal,
    openUserViewModal,
    openUserRoleModal,
    startUserEdit,
    closeUserModal,
    changePassword,
    openPwdModal,
    closePwdModal,
    onLogout,
  }
}
