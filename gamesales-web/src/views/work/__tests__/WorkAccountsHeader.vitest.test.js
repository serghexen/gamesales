import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkAccountsHeader from '../sections/WorkAccountsHeader.vue'

function buildProps(overrides = {}) {
  return {
    accountFilters: { search_q: '' },
    applyAccountSearch: vi.fn(),
    openCreateAccountModal: vi.fn(),
    openAccountImport: vi.fn(),
    openSlotImport: vi.fn(),
    loadAccounts: vi.fn(),
    accountsLoading: false,
    ...overrides,
  }
}

describe('WorkAccountsHeader', () => {
  it('shows order number in common search placeholder and submits by enter', async () => {
    const applyAccountSearch = vi.fn()
    const wrapper = mount(WorkAccountsHeader, {
      props: buildProps({ applyAccountSearch }),
    })

    const input = wrapper.find('.input--account-search')

    expect(input.attributes('placeholder')).toContain('номер заказа')

    await input.trigger('keydown.enter')

    expect(applyAccountSearch).toHaveBeenCalledTimes(1)
  })
})
