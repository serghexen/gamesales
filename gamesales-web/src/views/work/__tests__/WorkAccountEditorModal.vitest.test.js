import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkAccountEditorModal from '../sections/WorkAccountEditorModal.vue'

function buildProps(overrides = {}) {
  const editAccount = {
    open: true,
    account_id: 5,
    login_name: 'acc',
    domain_code: 'mail.com',
    region_code: 'RU',
    status_code: 'active',
    is_deactivated: false,
    deactivated_at: '',
    next_activation_at: '',
    account_date: '2026-03-01',
    notes: '',
    email_password: '',
    account_password: '',
    auth_code: '',
    reserve_text: '',
    product_ids: [],
  }
  return {
    editAccount,
    cancelEditAccount: vi.fn(),
    modalRef: null,
    modalStyle: {},
    startModalDrag: vi.fn(),
    accountModalMode: 'edit',
    accountEditMode: 'edit',
    setAccountEditMode: vi.fn(),
    toggleAccountEditMode: vi.fn(),
    updateAccount: vi.fn().mockResolvedValue(undefined),
    accountsLoading: false,
    accountSaving: false,
    createAccount: vi.fn(),
    deleteAccount: vi.fn(),
    accountProductsLoading: false,
    getDomainLabel: (code) => code || '—',
    domains: [],
    getRegionLabel: (code) => code || '—',
    regions: [],
    getAccountStatusLabel: () => 'Активный',
    maxDate: '2026-12-31',
    accountProductTitles: [],
    editAccountProductSearch: '',
    editAccountProductType: '',
    filteredEditAccountProducts: [],
    accountSlotAssignmentsError: '',
    accountSlotAssignmentsLoading: false,
    accountSlotAssignments: [],
    sortedAccountSlotAssignments: [],
    getSlotTypeLabel: (code) => code,
    getSlotAssignmentStatus: () => 'Активен',
    formatDateTimeMinutes: (value) => String(value || ''),
    accountSlotReleaseLoading: false,
    releaseSlotAssignment: vi.fn(),
    accountDealsError: '',
    accountDealsLoading: false,
    accountDeals: [],
    getDealProductTitleTooltip: () => '',
    getDealProductTitleDisplay: () => '',
    formatDate: (value) => String(value || ''),
    accountsError: '',
    accountsOk: '',
    newAccount: {
      login_name: '',
      domain_code: '',
      region_code: '',
      account_date: '',
      notes: '',
      account_password: '',
      email_password: '',
      auth_code: '',
      reserve_text: '',
      product_ids: [],
    },
    accountProductSearch: '',
    accountProductType: '',
    filteredAccountProducts: [],
    setEditAccountProductSearch: vi.fn(),
    setAccountProductSearch: vi.fn(),
    setEditAccountProductType: vi.fn(),
    setAccountProductType: vi.fn(),
    ...overrides,
  }
}

describe('WorkAccountEditorModal', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows deactivation checkbox only in edit mode', () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({ accountEditMode: 'edit' }),
      global: { stubs: { teleport: true } },
    })
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Деактивация:')
    expect(wrapper.text()).not.toContain('Повтораня деактивация')
  })

  it('shows deactivation status near account name in view mode', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-04T12:00:00Z'))
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountEditMode: 'view',
        editAccount: {
          ...buildProps().editAccount,
          is_deactivated: true,
          deactivated_at: '2026-03-04T12:00:00Z',
          next_activation_at: '2026-03-14T12:00:00Z',
        },
      }),
      global: { stubs: { teleport: true } },
    })
    expect(wrapper.text()).toContain('Повтораня деактивация через 10 дней')
  })

  it('keeps deactivation checkbox editable even before timer expiry', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-04T12:00:00Z'))
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountEditMode: 'edit',
        editAccount: {
          ...buildProps().editAccount,
          is_deactivated: true,
          deactivated_at: '2026-03-04T12:00:00Z',
          next_activation_at: '2026-03-14T12:00:00Z',
        },
      }),
      global: { stubs: { teleport: true } },
    })
    expect(wrapper.text()).toContain('Повтораня деактивация через 10 дней')
    expect(wrapper.text()).not.toContain('Деактивирован.')
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
    expect(checkbox.attributes('disabled')).toBeUndefined()
  })

  it('allows uncheck when activation timer expired', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-20T12:00:00Z'))
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountEditMode: 'edit',
        editAccount: {
          ...buildProps().editAccount,
          is_deactivated: true,
          deactivated_at: '2026-03-04T12:00:00Z',
          next_activation_at: '2026-03-14T12:00:00Z',
        },
      }),
      global: { stubs: { teleport: true } },
    })
    expect(wrapper.text()).toContain('Повтораня деактивация через 0 дней')
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
    expect(checkbox.attributes('disabled')).toBeUndefined()
  })

  it('hides deactivation checkbox when role cannot toggle and keeps status visible', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-04T12:00:00Z'))
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountEditMode: 'edit',
        canToggleDeactivation: false,
        editAccount: {
          ...buildProps().editAccount,
          is_deactivated: true,
          deactivated_at: '2026-03-04T12:00:00Z',
          next_activation_at: '2026-03-14T12:00:00Z',
        },
      }),
      global: { stubs: { teleport: true } },
    })
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(false)
    expect(wrapper.text()).toContain('Повтораня деактивация через 10 дней')
  })
})
