import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, reactive } from 'vue'

import { useImportFlow } from '../useImportFlow.js'

function createHarness() {
  const auth = { state: reactive({ token: 'token-1' }) }
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const apiPostForm = vi.fn()
  const apiGetFile = vi.fn()

  const deps = {
    auth,
    API_BASE: 'http://localhost:8000',
    apiGet,
    apiPost,
    apiPostForm,
    apiGetFile,
    mapApiError: (v) => String(v || ''),
    PRODUCT_IMPORT_JOB_KEY: 'PRODUCT_IMPORT_JOB_KEY',
    LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY: 'LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY',
    ACCOUNT_IMPORT_JOB_KEY: 'ACCOUNT_IMPORT_JOB_KEY',
    SLOT_VALIDATE_JOB_KEY: 'SLOT_VALIDATE_JOB_KEY',
    SLOT_IMPORT_JOB_KEY: 'SLOT_IMPORT_JOB_KEY',
    closeAllModals: vi.fn(),
    resetModalPos: vi.fn(),
    showProductImport: ref(false),
    showAccountImport: ref(false),
    showSlotImport: ref(false),
    productImportFile: ref(null),
    accountImportFile: ref(null),
    slotImportFile: ref(null),
    slotImportLimit: ref(10),
    productImportValidated: ref(false),
    accountImportValidated: ref(false),
    slotImportValidated: ref(false),
    productImportErrors: ref([]),
    accountImportErrors: ref([]),
    slotImportErrors: ref([]),
    productImportWarnings: ref([]),
    accountImportWarnings: ref([]),
    slotImportWarnings: ref([]),
    productImportTotal: ref(0),
    accountImportTotal: ref(0),
    slotImportTotal: ref(0),
    productImportLoading: ref(false),
    accountImportLoading: ref(false),
    slotImportLoading: ref(false),
    productImportMessage: ref(''),
    accountImportMessage: ref(''),
    slotImportMessage: ref(''),
    slotImportError: ref(''),
    slotImportAction: ref(''),
    slotImportProgress: reactive({ current: 0, total: 0, phase: '' }),
    slotImportJobId: ref(''),
    slotImportStats: ref(null),
    productImportAction: ref(''),
    accountImportAction: ref(''),
    productImportStats: ref(null),
    accountImportStats: ref(null),
    productImportProgress: reactive({ current: 0, total: 0, phase: '' }),
    accountImportProgress: reactive({ current: 0, total: 0, phase: '' }),
    productImportJobId: ref(''),
    accountImportJobId: ref(''),
    importDetailsRef: ref(null),
    accountImportDetailsRef: ref(null),
    loadProducts: vi.fn(),
    loadProductsAll: vi.fn(),
    accounts: ref([]),
    ensureAccountSecretsLoaded: vi.fn().mockResolvedValue(undefined),
    loadAccounts: vi.fn(),
    loadAccountsAll: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn(async () => true),
  }

  return {
    apiGet,
    apiPost,
    apiPostForm,
    apiGetFile,
    deps,
    flow: useImportFlow(deps),
  }
}

describe('useImportFlow', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('downloadProductTemplate calls products import template endpoint', async () => {
    const h = createHarness()
    h.apiGetFile.mockResolvedValueOnce(new Blob(['ok']))
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const click = vi.fn()
    const createEl = vi.spyOn(document, 'createElement').mockReturnValue({ click })

    await h.flow.downloadProductTemplate()

    expect(h.apiGetFile).toHaveBeenCalledWith('/products/import/template', { token: 'token-1' })
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock')
    expect(createEl).toHaveBeenCalledWith('a')
    expect(click).toHaveBeenCalled()
  })

  it('validateProductImport posts to products import validate endpoint', async () => {
    const h = createHarness()
    h.deps.productImportFile.value = { name: 'products.xlsx' }
    h.apiPostForm.mockResolvedValueOnce({ ok: true, total: 3, errors: [], warnings: [] })

    await h.flow.validateProductImport()

    expect(h.apiPostForm).toHaveBeenCalledWith(
      '/products/import/validate',
      expect.any(FormData),
      { token: 'token-1' },
    )
    expect(h.deps.productImportValidated.value).toBe(true)
    expect(h.deps.productImportTotal.value).toBe(3)
  })

  it('validateAccountDealsCheck posts to accounts deals check endpoint', async () => {
    const h = createHarness()
    h.deps.accountImportFile.value = { name: 'deals_check.xlsx' }
    h.apiPostForm.mockResolvedValueOnce({ ok: false, total: 2, errors: [], warnings: [{ row: 3, field: 'Сделка', message: 'not found' }] })

    await h.flow.validateAccountDealsCheck()

    expect(h.apiPostForm).toHaveBeenCalledWith(
      '/accounts/import/deals-check',
      expect.any(FormData),
      { token: 'token-1' },
    )
    expect(h.deps.accountImportWarnings.value.length).toBe(1)
    expect(String(h.deps.accountImportMessage.value || '')).toContain('Проверка сделок завершена')
  })

  it('fillAccountDealsOrderNumbers posts to accounts deals fill endpoint', async () => {
    const h = createHarness()
    h.deps.accountImportFile.value = { name: 'deals_fill.xlsx' }
    h.apiPostForm.mockResolvedValueOnce({ ok: true, total: 2, updated: 1, skipped: 1, warnings: [] })

    await h.flow.fillAccountDealsOrderNumbers()

    expect(h.apiPostForm).toHaveBeenCalledWith(
      '/accounts/import/deals-fill',
      expect.any(FormData),
      { token: 'token-1' },
    )
    expect(String(h.deps.accountImportMessage.value || '')).toContain('Обновлено сделок: 1')
  })

  it('refreshes visible account secrets after account import is applied', async () => {
    const h = createHarness()
    h.deps.accountImportFile.value = { name: 'accounts.xlsx' }
    h.deps.accountImportValidated.value = true
    h.deps.accounts.value = [{ account_id: 5 }, { account_id: 9 }, { account_id: 9 }]
    h.apiPostForm.mockResolvedValueOnce({ job_id: 'job-1' })
    h.apiGet.mockResolvedValueOnce({
      done: true,
      result: { ok: true, created: 0, updated: 1, skipped: 0, failed: 0, total: 1, errors: [], warnings: [] },
    })

    await h.flow.uploadAccountImport()
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()

    expect(h.deps.loadAccounts).toHaveBeenCalledTimes(1)
    expect(h.deps.loadAccountsAll).toHaveBeenCalledTimes(1)
    expect(h.deps.ensureAccountSecretsLoaded).toHaveBeenCalledWith(5, true)
    expect(h.deps.ensureAccountSecretsLoaded).toHaveBeenCalledWith(9, true)
  })
})
