import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkDashboardPanel from '../sections/WorkDashboardPanel.vue'

function buildCtx(overrides = {}) {
  return {
    apiOk: true,
    loading: false,
    checkApi: () => {},
    managersLoadItems: [],
    managersLoadOnlineCount: 0,
    managersLoadDate: '2026-03-02',
    managersLoadTimezone: 'Europe/Moscow',
    managersLoadLoading: false,
    managersLoadError: '',
    refreshManagersWorkload: () => {},
    ...overrides,
  }
}

describe('WorkDashboardPanel', () => {
  it('renders managers table with username, name and pending count', () => {
    const wrapper = mount(WorkDashboardPanel, {
      props: {
        ctx: buildCtx({
          managersLoadOnlineCount: 1,
          managersLoadItems: [{ username: 'manager1', name: 'Иван', pending_count: 4 }],
        }),
      },
    })

    expect(wrapper.text()).toContain('Онлайн: 1')
    expect(wrapper.text()).toContain('manager1 (Иван)')
    expect(wrapper.text()).toContain('4 заявок')
  })

  it('shows empty-state text when no managers are online', () => {
    const wrapper = mount(WorkDashboardPanel, {
      props: {
        ctx: buildCtx({ managersLoadItems: [] }),
      },
    })

    expect(wrapper.text()).toContain('Сейчас нет менеджеров онлайн.')
  })
})
