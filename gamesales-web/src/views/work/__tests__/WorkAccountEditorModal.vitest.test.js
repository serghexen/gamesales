import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

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
    editAccountProductType: 'game',
    filteredEditAccountProducts: [],
    accountSlotAssignmentsError: '',
    accountSlotAssignmentsLoading: false,
    accountSlotAssignments: [],
    sortedAccountSlotAssignments: [],
    getSlotTypeLabel: (code) => code,
    getSlotAssignmentStatus: () => 'Активен',
    formatDateTimeMinutes: (value) => String(value || ''),
    accountSlotReleaseLoading: false,
    canManageAccountSlotAssignments: true,
    releaseSlotAssignment: vi.fn(),
    restoreSlotAssignment: vi.fn(),
    accountDealsError: '',
    accountDealsLoading: false,
    accountDeals: [],
    loadAccountUsedReserveKeys: vi.fn().mockResolvedValue([]),
    claimAccountReserve: vi.fn().mockResolvedValue({ claim_token: 'claim-1', reserve_key: 'reserve1' }),
    releaseAccountReserveClaim: vi.fn().mockResolvedValue(undefined),
    startEditDeal: vi.fn(),
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
      subscription_valid_until: '',
    },
    accountProductSearch: '',
    accountProductType: 'game',
    filteredAccountProducts: [],
    createQuickAccountProduct: vi.fn(),
    quickNewAccountProduct: {
      title: '',
      platform_codes: [],
    },
    quickNewAccountProductLoading: false,
    quickNewAccountProductError: '',
    quickEditAccountProduct: {
      title: '',
      platform_codes: [],
    },
    quickEditAccountProductLoading: false,
    quickEditAccountProductError: '',
    platforms: [],
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
    expect(wrapper.text()).not.toContain('Повторная деактивация')
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
    expect(wrapper.text()).toContain('Повторная деактивация через 10 дней')
  })

  it('keeps deactivation checkbox enabled before timer expiry for manual revert', () => {
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
    expect(wrapper.text()).toContain('Повторная деактивация через 10 дней')
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
    expect(wrapper.text()).toContain('Повторная деактивация через 0 дней')
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
    expect(wrapper.text()).toContain('Повторная деактивация через 10 дней')
  })

  it('create mode keeps only game/subscription types and defaults to game', () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'create',
        accountEditMode: 'edit',
      }),
      global: { stubs: { teleport: true } },
    })
    const typeSelect = wrapper.findAll('select').find((item) => item.text().includes('Игра') && item.text().includes('Подписка'))
    expect(typeSelect).toBeTruthy()
    expect(typeSelect.text()).not.toContain('Все')
    expect(typeSelect.element.value).toBe('game')
  })

  it('shows quick product create when list is empty and calls create handler with selected type', async () => {
    const createQuickAccountProduct = vi.fn()
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'create',
        accountEditMode: 'edit',
        filteredAccountProducts: [],
        accountProductType: 'game',
        createQuickAccountProduct,
        quickNewAccountProduct: { title: 'PS Plus', platform_codes: ['ps5'] },
        platforms: [{ code: 'ps5', name: 'PlayStation 5' }],
      }),
      global: { stubs: { teleport: true } },
    })

    const toggleBtn = wrapper.findAll('button').find((btn) => btn.text().includes('Быстрое создание товара'))
    expect(toggleBtn).toBeTruthy()
    await toggleBtn.trigger('click')
    const createBtn = wrapper.findAll('button').find((btn) => btn.text().trim() === 'Создать')
    expect(createBtn).toBeTruthy()
    await createBtn.trigger('click')
    expect(createQuickAccountProduct).toHaveBeenCalledWith('game')
  })

  it('create subscription mode shows existing list and hides quick create block', () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'create',
        accountEditMode: 'edit',
        accountProductType: 'subscription',
        filteredAccountProducts: [{ product_id: 1, title: 'Old Sub' }],
      }),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Old Sub')
    expect(wrapper.text()).not.toContain('Для подписки используется только новое быстрое создание товара')
    expect(wrapper.text()).not.toContain('Быстрое создание товара')
    expect(wrapper.text()).not.toContain('Добавить срок подписки')
  })

  it('create subscription mode shows add-term block when subscription product is selected', () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'create',
        accountEditMode: 'edit',
        accountProductType: 'subscription',
        newAccount: {
          ...buildProps().newAccount,
          product_ids: [7],
          subscription_valid_until: '2027-03-26',
        },
      }),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Добавить срок подписки')
  })

  it('shows restore button for released slot assignment and calls restore handler', async () => {
    const restoreSlotAssignment = vi.fn()
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        accountSlotAssignments: [{ assignment_id: 55 }],
        sortedAccountSlotAssignments: [
          {
            assignment_id: 55,
            slot_type_code: 'play_ps4',
            released_at: '2026-05-20T10:00:00Z',
            released_by: 'manager',
            product_title: 'Game A',
            customer_nickname: 'buyer',
            assigned_at: '2026-03-20T10:00:00Z',
          },
        ],
        restoreSlotAssignment,
      }),
      global: { stubs: { teleport: true } },
    })

    const restoreBtn = wrapper.findAll('button').find((btn) => btn.text().trim() === 'Вернуть')
    expect(restoreBtn).toBeTruthy()
    await restoreBtn.trigger('click')
    expect(restoreSlotAssignment).toHaveBeenCalledWith(55)
  })

  it('hides manual slot buttons when role cannot manage assignments', () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        canManageAccountSlotAssignments: false,
        accountSlotAssignments: [{ assignment_id: 56 }],
        sortedAccountSlotAssignments: [
          {
            assignment_id: 56,
            slot_type_code: 'play_ps5',
            released_at: null,
            released_by: '',
            product_title: 'Game B',
            customer_nickname: 'buyer',
            assigned_at: '2026-03-20T10:00:00Z',
          },
        ],
      }),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).not.toContain('Снять')
    expect(wrapper.text()).not.toContain('Вернуть')
  })

  it('copies account email from modal header', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        editAccount: {
          ...buildProps().editAccount,
          login_name: 'user',
          domain_code: 'mail.com',
        },
      }),
      global: { stubs: { teleport: true } },
    })

    const copyBtn = wrapper.find('button[aria-label="Копировать почту"]')
    expect(copyBtn.exists()).toBe(true)
    await copyBtn.trigger('click')
    expect(writeText).toHaveBeenCalledWith('user@mail.com')
  })

  it('renders copy button for reserve row in view mode', async () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        editAccount: {
          ...buildProps().editAccount,
          reserve_text: 'AAA111 BBB222',
          existing_reserve_keys: ['reserve1', 'reserve2'],
        },
      }),
      global: { stubs: { teleport: true } },
    })
    await flushPromises()

    expect(wrapper.find('button[aria-label="Копировать Резерв 1"]').exists()).toBe(true)
  })

  it('keeps single reserve textarea in edit mode', async () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'edit',
        editAccount: {
          ...buildProps().editAccount,
          reserve_text: 'AAA111 BBB222',
          existing_reserve_keys: ['reserve1', 'reserve2'],
        },
        loadAccountUsedReserveKeys: vi.fn().mockResolvedValue(['reserve1']),
      }),
      global: { stubs: { teleport: true } },
    })
    await flushPromises()

    const textarea = wrapper.find('textarea')
    expect(textarea.exists()).toBe(true)
    expect(textarea.element.value).toBe('AAA111 BBB222')
    expect(wrapper.find('.account-reserve-row').exists()).toBe(false)
  })

  it('marks reserve as used and removes copy access after clipboard action', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    const claimAccountReserve = vi.fn().mockResolvedValue({ claim_token: 'claim-1', reserve_key: 'reserve1' })
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        editAccount: {
          ...buildProps().editAccount,
          reserve_text: 'AAA111',
          existing_reserve_keys: ['reserve1'],
        },
        claimAccountReserve,
      }),
      global: { stubs: { teleport: true } },
    })
    await flushPromises()

    const copyButton = wrapper.find('button[aria-label="Копировать Резерв 1"]')
    await copyButton.trigger('click')
    await flushPromises()

    expect(claimAccountReserve).toHaveBeenCalledWith(5, 'reserve1')
    expect(writeText).toHaveBeenCalledWith('AAA111')
    expect(wrapper.find('button[aria-label="Копировать Резерв 1"]').exists()).toBe(false)
    expect(wrapper.find('.account-reserve-row input').element.value).toBe('AAA111')
    expect(wrapper.find('.account-reserve-row__badge').text()).toBe('использован')
  })

  it('opens deal editor when user clicks deal row in account modal', async () => {
    const startEditDeal = vi.fn()
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        accountDeals: [
          {
            deal_id: 123,
            product_id: 77,
            customer_nickname: 'buyer',
            product_title: 'Game',
            deal_type: 'Шеринг',
            flow_status: 'Завершен',
            purchase_at: '2026-05-20T10:00:00Z',
          },
        ],
        startEditDeal,
      }),
      global: { stubs: { teleport: true } },
    })

    const row = wrapper.find('tr.table-row--deal-open')
    expect(row.exists()).toBe(true)
    await row.trigger('click')
    expect(startEditDeal).toHaveBeenCalledTimes(1)
    expect(startEditDeal).toHaveBeenCalledWith(
      expect.objectContaining({ deal_id: 123 }),
      { returnTab: 'accounts', returnAccountId: 5 },
    )
  })

  it('triggers account refresh from modal action button in view mode', async () => {
    const refreshOpenAccountFromDb = vi.fn()
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'view',
        refreshOpenAccountFromDb,
      }),
      global: { stubs: { teleport: true } },
    })

    const refreshBtn = wrapper.find('button[title="Обновить из базы"]')
    expect(refreshBtn.exists()).toBe(true)
    await refreshBtn.trigger('click')
    expect(refreshOpenAccountFromDb).toHaveBeenCalledTimes(1)
  })

  it('shows quick product create in edit mode and passes edit target', async () => {
    const createQuickAccountProduct = vi.fn()
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'edit',
        filteredEditAccountProducts: [],
        editAccountProductType: 'game',
        createQuickAccountProduct,
        quickEditAccountProduct: { title: 'EA FC', platform_codes: ['ps5'] },
        platforms: [{ code: 'ps5', name: 'PlayStation 5' }],
      }),
      global: { stubs: { teleport: true } },
    })

    const toggleBtn = wrapper.findAll('button').find((btn) => btn.text().includes('Быстрое создание товара'))
    expect(toggleBtn).toBeTruthy()
    await toggleBtn.trigger('click')
    const createBtn = wrapper.findAll('button').find((btn) => btn.text().trim() === 'Создать')
    expect(createBtn).toBeTruthy()
    await createBtn.trigger('click')
    expect(createQuickAccountProduct).toHaveBeenCalledWith('game', 'edit')
  })

  it('prefills quick product title from create search input', async () => {
    const quickNewAccountProduct = { title: '', platform_codes: [] }
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'create',
        accountEditMode: 'edit',
        quickNewAccountProduct,
      }),
      global: { stubs: { teleport: true } },
    })

    await wrapper.setProps({ accountProductSearch: 'Ghost of Tsushima' })
    expect(quickNewAccountProduct.title).toBe('Ghost of Tsushima')
  })

  it('prefills quick product title from edit search input', async () => {
    const quickEditAccountProduct = { title: '', platform_codes: [] }
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'edit',
        quickEditAccountProduct,
      }),
      global: { stubs: { teleport: true } },
    })

    await wrapper.setProps({ editAccountProductSearch: 'PS Plus Deluxe' })
    expect(quickEditAccountProduct.title).toBe('PS Plus Deluxe')
  })

  it('hides account modal blocks and actions without action permissions', async () => {
    const wrapper = mount(WorkAccountEditorModal, {
      props: buildProps({
        accountModalMode: 'edit',
        accountEditMode: 'edit',
        canEditAccount: false,
        canDeleteAccount: false,
        canViewGames: false,
        canReflectEmail: false,
        canReflectDate: false,
        canReflectRegion: false,
        canReflectAccountPassword: false,
        canReflectEmailPassword: false,
        canReflectAuthCode: false,
        canReflectReserves: false,
        canReflectSlots: false,
        canReflectDeals: false,
        accountDeals: [{ deal_id: 123, product_id: 77, customer_nickname: 'buyer' }],
        accountSlotAssignments: [{ assignment_id: 1, slot_type_code: 'primary' }],
      }),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('button[title="Сохранить изменения"]').exists()).toBe(false)
    expect(wrapper.find('button[title="Редактировать"]').exists()).toBe(false)
    expect(wrapper.find('button[title="Удалить"]').exists()).toBe(false)
    expect(wrapper.find('.account-modal-title').text()).toBe('АККАУНТ')
    expect(wrapper.text()).not.toContain('Логин (без домена)')
    expect(wrapper.text()).not.toContain('Домен')
    expect(wrapper.text()).not.toContain('Регион')
    expect(wrapper.text()).not.toContain('Дата')
    expect(wrapper.text()).not.toContain('Пароль аккаунт')
    expect(wrapper.text()).not.toContain('Пароль почта')
    expect(wrapper.text()).not.toContain('Код аутентификатора')
    expect(wrapper.text()).not.toContain('Резерв')
    expect(wrapper.text()).not.toContain('Товары')
    expect(wrapper.text()).not.toContain('Слоты аккаунта')
    expect(wrapper.text()).not.toContain('Пользователи по сделкам')
  })
})
