import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createReserveClaimToken } from '../reserveClaimToken'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function harness() {
  // Исполняем настоящую функцию копирования формы с управляемыми ответами API и буфером обмена.
  vi.useFakeTimers()
  const source = readFileSync(resolve(process.cwd(), 'src/views/work/sections/WorkDealEditorForm.vue'), 'utf8')
  const names = ['copySharingField', 'getSharingReserveOptions', 'pickFirstFreeReserveKey']
  const functions = names.map((name) => source.match(new RegExp(`(?:async )?function ${name}\\([\\s\\S]*?^\\}`, 'm'))[0]).join('\n')
  const deal = { account_id: 4087, reserve_key: 'reserve9', reserve_claim_token: '', deal_id: 27401 }
  const deps = {
    editDeal: { value: deal }, newDeal: { value: deal },
    reserveCopyInFlight: { new: false, edit: false }, accountDetailsRequestSeq: { new: 1, edit: 1 },
    createReserveClaimToken, normalizeReserveKey: (key) => key,
    getSharingFieldCopyValue: () => 'FAKE-CODE', canCopySharingReserve: () => true,
    isCompletedDeal: () => false, getSharingFieldCopyKey: () => 'edit:reserve',
    claimAccountReserve: { value: vi.fn(async (_a, _k, _d, token) => ({ claim_token: token })) },
    releaseAccountReserveClaim: { value: vi.fn().mockResolvedValue({ released: true }) },
    copyTextToClipboard: vi.fn().mockResolvedValue(undefined),
    ensureAccountReserveUsageLoaded: vi.fn().mockResolvedValue(undefined),
    showDealWarning: { value: vi.fn() }, copiedSharingFieldKey: { value: '' },
    getAccountReserveEntriesForDeal: vi.fn(() => Array.from({ length: 10 }, (_, i) => ({
      key: `reserve${i + 1}`, listed: true, used: i < 7,
    }))),
  }
  const factory = new Function('deps', `const {${Object.keys(deps).join(',')}} = deps; let copiedSharingFieldTimerId = 0; ${functions}; return {${names.join(',')}}`)
  return { ...deps, ...factory(deps), deal }
}

describe('reserve claim operation', () => {
  it('does not offer the old copied codes from the Mango case', () => {
    // API исключает текущую сделку, но старые копирования 4/5 остаются занятыми и для своего сотрудника.
    const h = harness()
    h.deal.reserve_key = 'reserve8'
    expect(h.getSharingReserveOptions('edit').map((r) => r.key)).toEqual(['reserve8','reserve9','reserve10'])
    h.getAccountReserveEntriesForDeal.mockReturnValue(Array.from({ length: 10 }, (_, i) => ({
      key: `reserve${i + 1}`, listed: true, used: i < 8,
    })))
    expect(h.pickFirstFreeReserveKey(4087)).toBe('reserve9')
  })

  it('retries a lost response with the token generated before the first request', async () => {
    // Потерянный ответ не очищает операцию и не заставляет сервер выдавать код заново.
    const h = harness()
    h.claimAccountReserve.value.mockRejectedValueOnce(new Error('network'))
    await h.copySharingField('new','reserve')
    const token = h.deal.reserve_claim_token
    expect(token).toMatch(/^[0-9a-f-]{36}$/)
    expect(h.copyTextToClipboard).not.toHaveBeenCalled()
    expect(h.releaseAccountReserveClaim.value).not.toHaveBeenCalled()
    await h.copySharingField('new','reserve')
    expect(h.claimAccountReserve.value.mock.calls.map((call) => call[3])).toEqual([token,token])
    expect(h.deal.reserve_claim_token).toBe(token)
    expect(h.copyTextToClipboard).toHaveBeenCalledOnce()
  })

  it('blocks a second click while copying and keeps the token for saving', async () => {
    // Одновременные клики одной формы не создают несколько запросов и сохраняют доказательство выдачи.
    const h = harness()
    let finish
    h.claimAccountReserve.value.mockImplementation((_a,_k,_d,token) => new Promise((resolve) => {
      finish = () => resolve({ claim_token: token })
    }))
    const first = h.copySharingField('edit','reserve')
    await h.copySharingField('edit','reserve')
    expect(h.claimAccountReserve.value).toHaveBeenCalledOnce()
    finish()
    await first
    expect(h.deal.reserve_claim_token).toBe(h.claimAccountReserve.value.mock.calls[0][3])
    expect(h.copyTextToClipboard).toHaveBeenCalledOnce()
  })

  it('keeps access to the saved deal reserve without retaining a stale claim', async () => {
    // Сохранённая связь проверяется сервером; для повторного копирования своего кода токен назначения не нужен.
    const h = harness()
    h.claimAccountReserve.value.mockResolvedValue({ assigned: true, claim_token: '' })
    await h.copySharingField('edit','reserve')
    expect(h.copyTextToClipboard).toHaveBeenCalledOnce()
    expect(h.deal.reserve_claim_token).toBe('')
  })

  it('does not copy a late response into a changed form or clear its newer token', async () => {
    // Ответ старой формы нельзя перенести в новую выдачу после смены аккаунта или закрытия.
    const h = harness()
    h.claimAccountReserve.value.mockImplementation(async (_a,_k,_d,token) => {
      h.accountDetailsRequestSeq.edit += 1
      h.deal.reserve_claim_token = 'another-operation'
      return { claim_token: token }
    })
    await h.copySharingField('edit','reserve')
    expect(h.copyTextToClipboard).not.toHaveBeenCalled()
    expect(h.deal.reserve_claim_token).toBe('another-operation')
    expect(h.releaseAccountReserveClaim.value).toHaveBeenCalledOnce()
  })

  it('never releases a repeated successful claim after a clipboard failure', async () => {
    // При повторе код уже мог быть скопирован раньше, поэтому ошибка буфера не возвращает его в свободные.
    const h = harness()
    h.claimAccountReserve.value.mockImplementation(async (_a,_k,_d,token) => ({ claim_token: token, reused: true }))
    h.copyTextToClipboard.mockRejectedValue(new Error('denied'))
    await h.copySharingField('edit','reserve')
    expect(h.releaseAccountReserveClaim.value).not.toHaveBeenCalled()
    expect(h.deal.reserve_claim_token).not.toBe('')
  })

  it('creates distinct UUIDs without randomUUID support', () => {
    // Старые браузеры используют криптографические байты с тем же форматом UUID, без Math.random.
    const getRandomValues = crypto.getRandomValues.bind(crypto)
    vi.stubGlobal('crypto', { getRandomValues })
    const first = createReserveClaimToken()
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
    expect(createReserveClaimToken()).not.toBe(first)
  })
})
