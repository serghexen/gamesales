import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'

export function useUserProfileFlow({
  auth,
  router,
  isAdmin,
  apiGet,
  apiPost,
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
  newUser,
  pwdError,
  pwdOk,
  pwdLoading,
  showPwdForm,
  pwdForm,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
}) {
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

  // Загружает роли и список пользователей (только для админа).
  async function loadUsers() {
    if (!isAdmin.value) return
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
      await apiPost('/users', newUser, { token: auth.state.token })
      userOk.value = `Пользователь ${newUser.username} создан`
      newUser.username = ''
      newUser.password = ''
      newUser.role_code = 'manager'
      await loadUsers()
      await closeModalSilently(closeUserModal)
    } catch (e) {
      userError.value = mapApiError(e?.message)
    } finally {
      userLoading.value = false
    }
  }

  // Открывает модалку создания пользователя.
  function openUserModal() {
    closeAllModals()
    resetModalPos()
    showUserForm.value = true
    userError.value = null
    userOk.value = null
  }

  // Закрывает модалку создания пользователя и чистит форму.
  async function closeUserModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const isDirty = !isSameNormalized(newUser, { username: '', password: '', role_code: 'manager' })
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showUserForm.value = false
    userError.value = null
    userOk.value = null
    newUser.username = ''
    newUser.password = ''
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
    openUserModal,
    closeUserModal,
    changePassword,
    openPwdModal,
    closePwdModal,
    onLogout,
  }
}
