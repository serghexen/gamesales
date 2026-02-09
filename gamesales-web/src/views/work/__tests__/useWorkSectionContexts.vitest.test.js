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
    const dealQuickGameBusy = ref(false)

    const ctx = useWorkSectionContexts({
      editDeal,
      showDealForm,
      dealEditMode,
      dealLoading,
      dealQuickAccountBusy,
      dealQuickGameBusy,
      closeDealModal: () => {},
      dealModalTitle: ref('Title'),
      updateDeal: () => {},
      createDeal: () => {},
    })

    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(false)
    showDealForm.value = true
    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(true)

    editDeal.open = true
    dealEditMode.value = 'edit'
    expect(ctx.dealEditorModalShellCtx.showSaveEdit).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreate).toBe(false)
    expect(ctx.dealEditorModalShellCtx.editDisabled).toBe(true)

    dealQuickAccountBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.isLocked).toBe(true)
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем аккаунт…')

    dealQuickAccountBusy.value = false
    dealQuickGameBusy.value = true
    expect(ctx.dealEditorModalBodyCtx.quickBusyLabel).toBe('Создаем игру…')
  })
})
