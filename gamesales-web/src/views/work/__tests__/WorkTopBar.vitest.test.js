import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkTopBar from '../sections/WorkTopBar.vue'

vi.mock('../../../api/http', () => ({
  apiGet: vi.fn(async (path) => path.includes('/config')
    ? { enabled: true, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 }
    : { total: 0, unseen_confirmed_count: 0, items: [] }),
  apiPost: vi.fn(async () => null),
}))

function buildCtx(overrides = {}) {
  return {
    activeTab: 'deals',
    routeQuery: {},
    isAdmin: true,
    canViewDealsSection: true,
    canViewAccountsSection: true,
    canViewProductsSection: true,
    canViewNsGiftSection: true,
    canViewInterhubSection: false,
    canViewTelegramSection: false,
    canViewUsersSection: false,
    canViewProfileSection: true,
    canViewDashboardSection: false,
    showChatsTab: false,
    showUsersTab: false,
    showDashboard: false,
    userRoleName: 'Админ',
    currentUsername: 'admin',
    authToken: 'token-1',
    managersLoadItems: [],
    managersLoadOnlineCount: 0,
    managersLoadLoading: false,
    canManageRolePermissions: true,
    financeTrCardBalance: { current_balance: 19000 },
    financeTrCardBalanceDraft: '19000',
    financeTrCardBalanceLoading: false,
    financeTrCardBalanceSaving: false,
    financeTrCardBalanceError: '',
    loadFinanceTrCardBalance: vi.fn(),
    saveFinanceTrCardBalance: vi.fn().mockResolvedValue(true),
    formatPrice: (value) => String(Math.round(Number(value || 0))),
    onLogout: () => {},
    ...overrides,
  }
}

function mountTopBar(ctx) {
  return mount(WorkTopBar, {
    props: { ctx },
    global: {
      stubs: {
        teleport: true,
        RouterLink: {
          props: ['to'],
          template: '<a><slot /></a>',
        },
      },
    },
  })
}

describe('WorkTopBar', () => {
  it('shows the supplier payments tab when the role permits it', () => {
    const wrapper = mountTopBar(buildCtx({ canViewInterhubSection: true }))

    expect(wrapper.text()).toContain('Платежи')
  })

  it('renders only managers with active pending deals', () => {
    const wrapper = mountTopBar(buildCtx({
      managersLoadItems: [
        { username: 'm1', name: 'Дмитрий', pending_count: 3, is_online: true },
        { username: 'm2', name: 'Лера', pending_count: 1, is_online: true },
        { username: 'm3', name: 'Анатолий', pending_count: 2, is_online: false },
        { username: 'm4', name: 'Оператор', pending_count: 4, is_online: true },
        { username: 'm5', name: 'Менеджер 5', pending_count: 0, is_online: false },
      ],
    }))

    expect(wrapper.findAll('.tab-workload__item')).toHaveLength(4)
    expect(wrapper.text()).not.toContain('Менеджер 5')
  })

  it('renders brand logo near navigation tabs', () => {
    const wrapper = mountTopBar(buildCtx())
    const logo = wrapper.find('.logo img')

    expect(logo.exists()).toBe(true)
    expect(logo.attributes('alt')).toBe('Логотип')
    expect(wrapper.html().indexOf('class="logo"')).toBeLessThan(wrapper.html().indexOf('class="tabs"'))
  })

  it('marks only online users with blinking dot class', () => {
    const wrapper = mountTopBar(buildCtx({
      managersLoadItems: [
        { username: 'm1', name: 'Дмитрий', pending_count: 3, is_online: true },
        { username: 'm2', name: 'Лера', pending_count: 1, is_online: false },
      ],
    }))

    expect(wrapper.findAll('.tab-workload__dot.is-online')).toHaveLength(1)
    expect(wrapper.findAll('.tab-workload__dot')).toHaveLength(2)
  })

  it.each(['operator', 'manager', 'admin', 'owner'])('temporarily hides TR card balance and controls for %s', (role) => {
    // Скрываем весь виджет, включая обновление и редактор, не затрагивая соседние элементы шапки.
    const privileged = ['admin', 'owner'].includes(role)
    const ctx = buildCtx({ userRoleName: role, isAdmin: privileged, canManageRolePermissions: privileged, financeTrCardBalance: { current_balance: -477.13 } })
    const wrapper = mountTopBar(ctx)
    expect(wrapper.find('[data-test="finance-tr-card-balance"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="finance-refresh-tr-card-balance"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="finance-edit-tr-card-balance"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('TRY')
    expect(wrapper.find('.tab-workload').exists()).toBe(true)
    expect(wrapper.find('[data-test="sbp-open"]').exists()).toBe(true)
    expect(ctx.loadFinanceTrCardBalance).not.toHaveBeenCalled()
    expect(ctx.saveFinanceTrCardBalance).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('shows the SBP payment center to an ordinary authenticated user', async () => {
    const wrapper = mountTopBar(buildCtx({ isAdmin: false, canManageRolePermissions: false }))

    expect(wrapper.find('[data-test="sbp-open"]').exists()).toBe(true)
    await wrapper.find('[data-test="sbp-open"]').trigger('click')
    expect(wrapper.find('[data-test="sbp-description"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="sbp-buyer"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Быстрый выбор суммы')
  })

})
