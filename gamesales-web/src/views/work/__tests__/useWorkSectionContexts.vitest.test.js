import { describe, it, expect } from 'vitest'
import { ref, reactive } from 'vue'

import { useWorkSectionContexts } from '../useWorkSectionContexts.js'

describe('useWorkSectionContexts', () => {
  it('builds deal modal shell/body reactive state', () => {
    const editDeal = reactive({ open: false })
    const showDealForm = ref(false)
    const dealEditMode = ref('view')
    const dealLoading = ref(false)
    const dealQuickAccountBusy = ref(false)
    const dealQuickProductBusy = ref(false)
    const responsibleUserOptions = ref(['manager1'])
    const canEditCompletedDeal = ref(true)

    const ctx = useWorkSectionContexts({
      editDeal,
      showDealForm,
      dealEditMode,
      dealLoading,
      dealQuickAccountBusy,
      dealQuickProductBusy,
      canEditCompletedDeal,
      responsibleUserOptions,
      closeDealModal: () => {},
      dealModalTitle: ref('Title'),
      updateDeal: () => {},
      updateDealDraft: () => {},
      createDeal: () => {},
      createDealDraft: () => {},
      toggleDealEditMode: () => {},
    })

    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(false)
    showDealForm.value = true
    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(true)

    editDeal.open = true
    dealEditMode.value = 'edit'
    expect(ctx.dealEditorModalShellCtx.showSaveEdit).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreate).toBe(false)
    expect(ctx.dealEditorModalShellCtx.editDisabled).toBe(false)

    dealQuickAccountBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.isLocked).toBe(true)
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем аккаунт…')

    dealQuickAccountBusy.value = false
    dealQuickProductBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем товар…')
    expect(ctx.dealEditorFormCtx.responsibleUserOptions).toEqual(['manager1'])
    expect(ctx.dealEditorFormCtx.allowCompletedDealEdit).toBe(true)
  })
})
