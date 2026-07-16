import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkTopBar from '../sections/WorkTopBar.vue'

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
  it('shows InterHub payments tab when the role permits it', () => {
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

  it('shows TR card balance before workload for all users', () => {
    const wrapper = mountTopBar(buildCtx({ canManageRolePermissions: false }))

    expect(wrapper.find('[data-test="finance-tr-card-balance"]').text()).toContain('19000 TRY')
    expect(wrapper.find('[data-test="finance-edit-tr-card-balance"]').exists()).toBe(false)
    expect(wrapper.html().indexOf('data-test="finance-tr-card-balance"')).toBeLessThan(wrapper.html().indexOf('tab-workload'))
  })

  it('allows privileged users to refresh and edit TR card balance', async () => {
    const ctx = buildCtx({ financeTrCardBalance: { current_balance: -500 } })
    const wrapper = mountTopBar(ctx)

    expect(wrapper.find('.tr-card-balance__value').classes()).toContain('tr-card-balance__value--negative')
    await wrapper.find('[data-test="finance-refresh-tr-card-balance"]').trigger('click')
    expect(ctx.loadFinanceTrCardBalance).toHaveBeenCalledTimes(1)

    await wrapper.find('[data-test="finance-edit-tr-card-balance"]').trigger('click')
    expect(wrapper.find('[aria-label="Фактический баланс TR-карты"]').exists()).toBe(true)
    await wrapper.find('[data-test="finance-save-tr-card-balance"]').trigger('click')
    expect(ctx.saveFinanceTrCardBalance).toHaveBeenCalledTimes(1)
  })

  it('shows loader while TR balance is refreshing', () => {
    const wrapper = mountTopBar(buildCtx({ financeTrCardBalanceLoading: true }))

    expect(wrapper.find('[data-test="finance-refresh-tr-card-balance"] .wheel-and-hamster').exists()).toBe(true)
  })
})
