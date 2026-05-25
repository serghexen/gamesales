import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkAccountsTableSection from '../sections/WorkAccountsTableSection.vue'

function buildProps(overrides = {}) {
  return {
    sortedAccounts: [],
    accountFilters: { login_q: '', product_q: '' },
    activeAccountFilter: '',
    accountFilterDraft: { login: '', product: '' },
    openAccountFilter: vi.fn(),
    toggleAccountSort: vi.fn(),
    getAccountSortClass: vi.fn(() => ''),
    applyAccountFilter: vi.fn(),
    resetAccountFilter: vi.fn(),
    startEditAccount: vi.fn(),
    formatAccountProductsLine: vi.fn(() => ''),
    getAccountSlotStatusList: vi.fn(() => []),
    formatAccountSlotStatusLine: vi.fn(() => ''),
    formatSecret: vi.fn((value) => value),
    getReserveSecrets: vi.fn(() => ''),
    ensureAccountSecretsLoaded: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

describe('WorkAccountsTableSection', () => {
  it('renders accounts table inside horizontal scroll wrapper', async () => {
    const wrapper = mount(WorkAccountsTableSection, {
      props: buildProps({
        sortedAccounts: [{ account_id: 5, login_full: 'a@mail.com' }],
      }),
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.accounts-table-wrap').exists()).toBe(true)
    expect(wrapper.find('table.accounts-table').exists()).toBe(true)
  })

  it('preloads secrets for visible accounts on mount', async () => {
    const ensureAccountSecretsLoaded = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(WorkAccountsTableSection, {
      props: buildProps({
        sortedAccounts: [
          { account_id: 5, login_full: 'a@mail.com' },
          { account_id: 9, login_full: 'b@mail.com' },
          { account_id: 5, login_full: 'a@mail.com' },
          { account_id: null, login_full: 'none' },
        ],
        ensureAccountSecretsLoaded,
      }),
    })

    await wrapper.vm.$nextTick()

    expect(ensureAccountSecretsLoaded).toHaveBeenCalledTimes(2)
    expect(ensureAccountSecretsLoaded).toHaveBeenNthCalledWith(1, 5)
    expect(ensureAccountSecretsLoaded).toHaveBeenNthCalledWith(2, 9)
  })

  it('preloads secrets when visible accounts list changes', async () => {
    const ensureAccountSecretsLoaded = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(WorkAccountsTableSection, {
      props: buildProps({
        sortedAccounts: [{ account_id: 5, login_full: 'a@mail.com' }],
        ensureAccountSecretsLoaded,
      }),
    })

    await wrapper.vm.$nextTick()
    ensureAccountSecretsLoaded.mockClear()

    await wrapper.setProps({
      sortedAccounts: [
        { account_id: 11, login_full: 'c@mail.com' },
        { account_id: 12, login_full: 'd@mail.com' },
      ],
    })
    await wrapper.vm.$nextTick()

    expect(ensureAccountSecretsLoaded).toHaveBeenCalledTimes(2)
    expect(ensureAccountSecretsLoaded).toHaveBeenNthCalledWith(1, 11)
    expect(ensureAccountSecretsLoaded).toHaveBeenNthCalledWith(2, 12)
  })
})
