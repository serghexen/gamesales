import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'

import { useWorkSectionContexts } from '../useWorkSectionContexts.js'

describe('useWorkSectionContexts', () => {
  it('builds deal modal shell/body reactive state', () => {
    // Контекст формы должен получать актуальную роль после смены пользователя.
    const auth = { state: reactive({ role: 'owner' }) }
    const editDeal = reactive({ open: false, flow_status_code: '' })
    const showDealForm = ref(false)
    const dealEditMode = ref('view')
    const dealLoading = ref(false)
    const dealReserveSelectionLoading = ref(false)
    const dealSupplierBusy = ref(false)
    const dealQuickAccountBusy = ref(false)
    const dealQuickProductBusy = ref(false)
    const responsibleUserOptions = ref(['manager1'])
    const canEditCompletedDeal = ref(true)
    const newDeal = reactive({ deal_type_code: 'rental' })

    const updateDeal = vi.fn()
    const updateDealDraft = vi.fn()
    const openAccountFromDeal = vi.fn()
    const canViewAccountsSection = ref(true)
    const ctx = useWorkSectionContexts({
      auth,
      editDeal,
      newDeal,
      showDealForm,
      dealEditMode,
      dealLoading,
      dealReserveSelectionLoading,
      dealSupplierBusy,
      dealQuickAccountBusy,
      dealQuickProductBusy,
      canEditCompletedDeal,
      responsibleUserOptions,
      closeDealModal: () => {},
      dealModalTitle: ref('Title'),
      updateDeal,
      updateDealDraft,
      openAccountFromDeal,
      canViewAccountsSection,
      createDeal: () => {},
      createDealDraft: () => {},
      toggleDealEditMode: () => {},
    })

    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(false)
    expect(ctx.dealEditorFormCtx.openAccountFromDeal).toBe(openAccountFromDeal)
    expect(ctx.dealEditorFormCtx.canViewAccountsSection).toBe(true)
    canViewAccountsSection.value = false
    expect(ctx.dealEditorFormCtx.canViewAccountsSection).toBe(false)
    showDealForm.value = true
    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreateDraft).toBe(true)

    editDeal.open = true
    dealEditMode.value = 'edit'
    expect(ctx.dealEditorModalShellCtx.showSaveEdit).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreate).toBe(false)
    expect(ctx.dealEditorModalShellCtx.editDisabled).toBe(false)

    // На время покупки и обновления версии шапка не запускает редактирование или сохранение.
    dealSupplierBusy.value = true
    expect(ctx.dealEditorModalShellCtx.editDisabled).toBe(true)
    expect(ctx.dealEditorModalShellCtx.actionsDisabled).toBe(true)
    ctx.dealEditorModalShellCtx.onSaveEdit()
    expect(updateDeal).not.toHaveBeenCalled()
    dealSupplierBusy.value = false
    expect(ctx.dealEditorModalShellCtx.actionsDisabled).toBe(false)

    // Подбор резерва блокирует сохранение до завершения загрузки и разделяет флаг с формой.
    ctx.dealEditorFormCtx.dealReserveSelectionLoading = true
    expect(dealReserveSelectionLoading.value).toBe(true)
    expect(ctx.dealEditorModalShellCtx.actionsDisabled).toBe(true)
    ctx.dealEditorModalShellCtx.onSaveEdit()
    expect(updateDeal).not.toHaveBeenCalled()
    dealReserveSelectionLoading.value = false
    expect(ctx.dealEditorModalShellCtx.actionsDisabled).toBe(false)

    dealQuickAccountBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.isLocked).toBe(true)
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем аккаунт…')

    dealQuickAccountBusy.value = false
    dealQuickProductBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем товар…')
    expect(ctx.dealEditorFormCtx.responsibleUserOptions).toEqual(['manager1'])
    expect(ctx.dealEditorFormCtx.allowCompletedDealEdit).toBe(true)
    expect(ctx.dealEditorFormCtx.currentUserRole).toBe('owner')
    auth.state.role = 'admin'
    expect(ctx.dealEditorFormCtx.currentUserRole).toBe('admin')

    editDeal.flow_status_code = 'draft'
    expect(ctx.dealEditorModalShellCtx.showSaveDraft).toBe(false)
    ctx.dealEditorModalShellCtx.onSaveEdit()
    expect(updateDeal).toHaveBeenCalledTimes(1)
    expect(updateDealDraft).toHaveBeenCalledTimes(0)
  })
})
