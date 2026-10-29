import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref, watch, nextTick } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { isCompletedDeal } from '../dealsUtils'

const cleanups = []
afterEach(() => cleanups.splice(0).forEach((stop) => stop()))

function harness(initial = {}) {
  // Исполняем функции и регистрацию watcher из настоящей формы на реактивном состоянии Vue.
  const source = readFileSync(resolve(process.cwd(), 'src/views/work/sections/WorkDealEditorForm.vue'), 'utf8')
  const names = ['ensureDealAccountDetailsLoaded', 'handleEditDealAccountChange']
  const functions = names.map((name) => source.match(new RegExp(`(?:async )?function ${name}\\([\\s\\S]*?^\\}`, 'm'))[0]).join('\n')
  const registration = source.split('\n').find((line) => line.startsWith('watch(') && line.includes('handleEditDealAccountChange'))
  const editDeal = ref({ open: true, deal_id: 42, account_id: null, deal_type_code: 'rental', flow_status_code: 'draft', reserve_key: '', reserve_claim_token: '', ...initial })
  const newDeal = ref({ account_id: 7, deal_type_code: 'rental', reserve_key: '' })
  const deps = {
    watch, editDeal, newDeal, isCompletedDeal,
    dealEditMode: ref('view'), editDealOpenedAsDraft: ref(false),
    dealReserveSelectionLoading: ref(false), accountDetailsRequestSeq: { new: 0, edit: 0 },
    editDealAccountDetailsLoading: ref(false), newDealAccountDetailsLoading: ref(false),
    getDealAccountIdByTarget: (target) => Number((target === 'edit' ? editDeal : newDeal).value.account_id || 0),
    hasAccountLabelForDetails: () => true,
    loadAccountsAll: ref(vi.fn()), ensureAccountSecretsLoaded: ref(vi.fn().mockResolvedValue(undefined)),
    ensureAccountReserveUsageLoaded: vi.fn().mockResolvedValue(undefined),
    hasAccountReserveUsage: vi.fn().mockReturnValue(true), normalizeReserveKey: (key) => key || '',
    getUsedReserveKeysByAccount: () => new Set(['reserve1', 'reserve2', 'reserve3']),
    pickFirstFreeReserveKey: vi.fn().mockReturnValue('reserve4'),
    getAccountReserveEntriesForDeal: vi.fn().mockReturnValue([{ key: 'reserve4' }]),
    showDealWarning: ref(vi.fn()),
  }
  const factory = new Function('deps', `const {${Object.keys(deps).join(',')}} = deps; ${functions}; const stop = ${registration}; return {stop, ${names.join(',')}}`)
  const flow = factory(deps)
  cleanups.push(flow.stop)
  return { ...deps, ...flow }
}

async function settle() {
  // Дожидаемся watcher и его асинхронной загрузки без браузера и обращения к API.
  await nextTick()
  await flushPromises()
}

describe('draft reserve selection', () => {
  it.each([false, true])('selects a free reserve after choosing an account in draft editing, duplicate=%s', async (duplicate) => {
    // Обычный выбор и выбор дубля проходят одинаковую проверку свободного кода.
    const h = harness()
    h.dealEditMode.value = 'edit'
    Object.assign(h.editDeal.value, { account_id: 7, is_duplicate_flow: duplicate })
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('reserve4')
    expect(h.pickFirstFreeReserveKey).toHaveBeenCalledExactlyOnceWith(7, 42)
    expect(h.dealReserveSelectionLoading.value).toBe(false)
  })

  it.each(['draft', 'pending', 'completed'])('does not assign on opening or enabling edit for a %s deal', async (flow_status_code) => {
    // Сам просмотр и кнопка редактирования не являются выбором аккаунта.
    const h = harness({ flow_status_code, account_id: 7 })
    await settle()
    h.dealEditMode.value = 'edit'
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.pickFirstFreeReserveKey).not.toHaveBeenCalled()
  })

  it('remembers a draft when the employee selects pending before the account', async () => {
    // Порядок заполнения статуса и аккаунта не должен повторять ошибку сделки №26788.
    const h = harness()
    h.dealEditMode.value = 'edit'
    h.editDeal.value.flow_status_code = 'pending'
    h.editDeal.value.account_id = 7
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('reserve4')
  })

  it('does not auto-assign when an originally pending deal changes account', async () => {
    // Исправление ограничено заполнением черновика, рабочие сделки не получают новую выдачу автоматически.
    const h = harness({ flow_status_code: 'pending' })
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
  })

  it.each(['selected', 'claimed'])('preserves a reserve chosen while loading: %s', async (kind) => {
    // Запоздалая подстановка не заменяет выбор сотрудника или уже скопированный код.
    const h = harness()
    let finish
    h.ensureAccountReserveUsageLoaded.mockReturnValue(new Promise((resolve) => { finish = resolve }))
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await nextTick()
    expect(h.dealReserveSelectionLoading.value).toBe(true)
    h.editDeal.value.reserve_key = 'reserve6'
    if (kind === 'claimed') h.editDeal.value.reserve_claim_token = 'owned-claim'
    finish()
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('reserve6')
    expect(h.pickFirstFreeReserveKey).not.toHaveBeenCalled()
  })

  it.each(['close', 'view', 'another-deal'])('ignores late loading after %s', async (action) => {
    // Ответ прежней формы не должен назначить резерв после закрытия или переключения сделки.
    const h = harness()
    let finish
    h.ensureAccountReserveUsageLoaded.mockReturnValue(new Promise((resolve) => { finish = resolve }))
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await nextTick()
    if (action === 'close') h.editDeal.value.open = false
    if (action === 'view') h.dealEditMode.value = 'view'
    if (action === 'another-deal') h.editDeal.value.deal_id = 43
    await nextTick()
    finish()
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.dealReserveSelectionLoading.value).toBe(false)
  })

  it('warns when the selected account has no available reserve', async () => {
    // Пустой набор не превращается в фиктивное назначение.
    const h = harness()
    h.pickFirstFreeReserveKey.mockReturnValue('')
    h.getAccountReserveEntriesForDeal.mockReturnValue([])
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.showDealWarning.value).toHaveBeenCalledWith('У выбранного аккаунта нет доступных резервов')
  })

  it('keeps the latest request in charge when the account changes A to B to A', async () => {
    // Совпадения account_id недостаточно: первый ответ A уже относится к устаревшему выбору.
    const h = harness()
    const finish = []
    h.ensureAccountReserveUsageLoaded.mockImplementation(() => new Promise((resolve) => { finish.push(resolve) }))
    h.dealEditMode.value = 'edit'
    for (const accountId of [7, 8, 7]) {
      h.editDeal.value.account_id = accountId
      await nextTick()
    }
    finish[0]()
    finish[1]()
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.dealReserveSelectionLoading.value).toBe(true)
    finish[2]()
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('reserve4')
    expect(h.dealReserveSelectionLoading.value).toBe(false)
    expect(h.pickFirstFreeReserveKey).toHaveBeenCalledTimes(1)
  })

  it('never selects from cached secrets when reserve usage failed to load', async () => {
    // При неизвестной занятости нельзя считать первый код свободным.
    const h = harness()
    h.hasAccountReserveUsage.mockReturnValue(false)
    h.ensureAccountReserveUsageLoaded.mockRejectedValue(new Error('offline'))
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await settle()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.pickFirstFreeReserveKey).not.toHaveBeenCalled()
    expect(h.dealReserveSelectionLoading.value).toBe(false)
  })

  it('keeps automatic selection in the new-deal form', async () => {
    // Прежний сценарий создания продолжает подставлять свободный код.
    const h = harness()
    await h.ensureDealAccountDetailsLoaded('new')
    expect(h.newDeal.value.reserve_key).toBe('reserve4')
  })
  it('does not pick a reserve from stale cache when fresh secrets failed to load', async () => {
    // Сохранённый кеш не подтверждает наличие кода после ошибки обновления.
    const h = harness()
    h.ensureAccountSecretsLoaded.value.mockResolvedValue(false)
    h.dealEditMode.value = 'edit'
    h.editDeal.value.account_id = 7
    await settle()
    expect(h.pickFirstFreeReserveKey).not.toHaveBeenCalled()
    expect(h.editDeal.value.reserve_key).toBe('')
    expect(h.dealReserveSelectionLoading.value).toBe(false)
  })

})
