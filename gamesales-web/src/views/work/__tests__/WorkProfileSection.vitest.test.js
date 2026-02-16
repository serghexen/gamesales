import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import WorkProfileSection from '../sections/WorkProfileSection.vue'

function buildCtx(overrides = {}) {
  // Собираем минимальный контекст профиля для проверки видимости секции пользователей.
  return {
    isAdmin: false,
    usersSectionCtx: {},
    openPwdModal: vi.fn(),
    showPwdForm: false,
    closePwdModal: vi.fn(),
    modalRef: ref(null),
    modalStyle: {},
    startModalDrag: vi.fn(),
    pwdLoading: false,
    pwdForm: { current: '', next: '', next2: '' },
    pwdError: '',
    pwdOk: '',
    changePassword: vi.fn(),
    ...overrides,
  }
}

describe('WorkProfileSection', () => {
  it('renders users section for admin inside profile tab', () => {
    const wrapper = mount(WorkProfileSection, {
      props: {
        ctx: buildCtx({ isAdmin: true, usersSectionCtx: { sortedUsers: [{ username: 'admin' }] } }),
      },
      global: {
        stubs: {
          teleport: true,
          WorkUsersSection: {
            template: '<div class="users-stub">Users section</div>',
          },
        },
      },
    })

    expect(wrapper.find('.users-stub').exists()).toBe(true)
  })

  it('hides users section for non-admin', () => {
    const wrapper = mount(WorkProfileSection, {
      props: {
        ctx: buildCtx({ isAdmin: false }),
      },
      global: {
        stubs: {
          teleport: true,
          WorkUsersSection: {
            template: '<div class="users-stub">Users section</div>',
          },
        },
      },
    })

    expect(wrapper.find('.users-stub').exists()).toBe(false)
  })
})
