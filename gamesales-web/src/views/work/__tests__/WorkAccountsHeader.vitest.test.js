import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkAccountsHeader from '../sections/WorkAccountsHeader.vue'

function buildProps(overrides = {}) {
  return {
    accountFilters: { search_q: '', without_products: false },
    toggleEmptyAccounts: vi.fn(),
    applyAccountSearch: vi.fn(),
    openCreateAccountModal: vi.fn(),
    openAccountImport: vi.fn(),
    openSlotImport: vi.fn(),
    downloadSlotsExport: vi.fn(),
    slotsExportLoading: false,
    slotsExportMessage: '',
    slotsExportError: '',
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

  it('downloads slots history from the toolbar', async () => {
    const downloadSlotsExport = vi.fn()
    const wrapper = mount(WorkAccountsHeader, {
      props: buildProps({ downloadSlotsExport }),
    })

    await wrapper.find('[aria-label="Выгрузить историю слотов"]').trigger('click')

    expect(downloadSlotsExport).toHaveBeenCalledTimes(1)
  })

  it('toggles accounts without linked games or subscriptions', async () => {
    const toggleEmptyAccounts = vi.fn()
    const wrapper = mount(WorkAccountsHeader, {
      props: buildProps({
        accountFilters: { search_q: '', without_products: true },
        toggleEmptyAccounts,
      }),
    })

    const button = wrapper.get('.account-empty-toggle')
    expect(button.attributes('aria-pressed')).toBe('true')

    await button.trigger('click')

    expect(toggleEmptyAccounts).toHaveBeenCalledTimes(1)
  })

  it('shows progress and disables slots export button while file is generated', () => {
    const wrapper = mount(WorkAccountsHeader, {
      props: buildProps({
        slotsExportLoading: true,
        slotsExportMessage: 'Формируем XLSX…',
      }),
    })

    const button = wrapper.find('[aria-label="Формируется выгрузка слотов"]')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.find('.spinner').exists()).toBe(true)
    expect(wrapper.get('[role="status"]').text()).toBe('Формируем XLSX…')
  })
})
