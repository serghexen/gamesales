import { describe, it, expect } from 'vitest'
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
    onLogout: () => {},
    ...overrides,
  }
}

describe('WorkTopBar', () => {
  it('renders all managers without limiting preview list', () => {
    const wrapper = mount(WorkTopBar, {
      props: {
        ctx: buildCtx({
          managersLoadItems: [
            { username: 'm1', name: 'Дмитрий', pending_count: 3, is_online: true },
            { username: 'm2', name: 'Лера', pending_count: 1, is_online: true },
            { username: 'm3', name: 'Анатолий', pending_count: 2, is_online: false },
            { username: 'm4', name: 'Оператор', pending_count: 4, is_online: true },
            { username: 'm5', name: 'Менеджер 5', pending_count: 0, is_online: false },
          ],
        }),
      },
      global: {
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.findAll('.tab-workload__item')).toHaveLength(5)
    expect(wrapper.text()).toContain('Менеджер 5')
  })

  it('marks only online users with blinking dot class', () => {
    const wrapper = mount(WorkTopBar, {
      props: {
        ctx: buildCtx({
          managersLoadItems: [
            { username: 'm1', name: 'Дмитрий', pending_count: 3, is_online: true },
            { username: 'm2', name: 'Лера', pending_count: 1, is_online: false },
          ],
        }),
      },
      global: {
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.findAll('.tab-workload__dot.is-online')).toHaveLength(1)
    expect(wrapper.findAll('.tab-workload__dot')).toHaveLength(2)
  })
})
