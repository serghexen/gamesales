import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'

import { useWorkSectionContexts } from '../useWorkSectionContexts.js'

describe('useWorkSectionContexts', () => {
  it('builds deal modal shell/body reactive state', () => {
    const editDeal = reactive({ open: false, flow_status_code: '' })
    const showDealForm = ref(false)
    const dealEditMode = ref('view')
    const dealLoading = ref(false)
    const dealQuickAccountBusy = ref(false)
    const dealQuickProductBusy = ref(false)
    const responsibleUserOptions = ref(['manager1'])
    const canEditCompletedDeal = ref(true)
    const newDeal = reactive({ deal_type_code: 'rental' })

    const updateDeal = vi.fn()
    const updateDealDraft = vi.fn()
    const ctx = useWorkSectionContexts({
      editDeal,
      newDeal,
      showDealForm,
      dealEditMode,
      dealLoading,
      dealQuickAccountBusy,
      dealQuickProductBusy,
      canEditCompletedDeal,
      responsibleUserOptions,
      canDoAction: () => true,
      closeDealModal: () => {},
      dealModalTitle: ref('Title'),
      updateDeal,
      updateDealDraft,
      createDeal: () => {},
      createDealDraft: () => {},
      toggleDealEditMode: () => {},
    })

    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(false)
    showDealForm.value = true
    expect(ctx.dealEditorModalShellCtx.isOpen).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreateDraft).toBe(true)

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

    editDeal.flow_status_code = 'draft'
    expect(ctx.dealEditorModalShellCtx.showSaveDraft).toBe(false)
    ctx.dealEditorModalShellCtx.onSaveEdit()
    expect(updateDeal).toHaveBeenCalledTimes(1)
    expect(updateDealDraft).toHaveBeenCalledTimes(0)
  })

  it('gates deal modal actions by action permissions', () => {
    const editDeal = reactive({ open: true, flow_status_code: 'draft' })
    const showDealForm = ref(false)
    const dealEditMode = ref('edit')
    const blocked = new Set(['deals_draft.edit', 'deals_draft.save', 'deals_draft.delete', 'deals_active.draft'])
    const ctx = useWorkSectionContexts({
      editDeal,
      newDeal: reactive({ deal_type_code: 'sale' }),
      showDealForm,
      dealEditMode,
      dealLoading: ref(false),
      dealQuickAccountBusy: ref(false),
      dealQuickProductBusy: ref(false),
      canEditCompletedDeal: ref(true),
      responsibleUserOptions: ref([]),
      canDoAction: (actionCode) => !blocked.has(actionCode),
      closeDealModal: () => {},
      dealModalTitle: ref('Title'),
      updateDeal: vi.fn(),
      updateDealDraft: vi.fn(),
      createDeal: vi.fn(),
      createDealDraft: vi.fn(),
      deleteDeal: vi.fn(),
      toggleDealEditMode: vi.fn(),
    })

    expect(ctx.dealEditorModalShellCtx.showSaveEdit).toBe(false)
    expect(ctx.dealEditorModalShellCtx.showDelete).toBe(false)
    expect(ctx.dealEditorModalShellCtx.showEdit).toBe(false)

    editDeal.open = false
    showDealForm.value = true
    expect(ctx.dealEditorModalShellCtx.showCreate).toBe(true)
    expect(ctx.dealEditorModalShellCtx.showCreateDraft).toBe(false)
  })
})
