import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import WorkUsersSection from '../sections/WorkUsersSection.vue'

function buildCtx(overrides = {}) {
  // Собираем минимальный контекст секции пользователей для проверки разметки.
  return {
    openUserModal: vi.fn(),
    loadUsers: vi.fn(),
    userLoading: false,
    showUserForm: false,
    closeUserModal: vi.fn(),
    modalRef: ref(null),
    modalStyle: {},
    startModalDrag: vi.fn(),
    newUser: { username: '', password: '', role_code: 'manager' },
    roles: [{ code: 'manager', name: 'Менеджер' }],
    createUser: vi.fn(),
    userError: '',
    userOk: '',
    sortedUsers: [],
    toggleUsersSort: vi.fn(),
    ...overrides,
  }
}

describe('WorkUsersSection', () => {
  it('renders panel wrapper by default', () => {
    const wrapper = mount(WorkUsersSection, {
      props: { ctx: buildCtx() },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.classes()).toContain('panel')
    expect(wrapper.find('.deal-create-btn').exists()).toBe(true)
    expect(wrapper.find('.deal-refresh-btn').exists()).toBe(true)
  })

  it('renders embedded mode without panel wrapper', () => {
    const wrapper = mount(WorkUsersSection, {
      props: { ctx: buildCtx(), embedded: true },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.classes()).toContain('work-users-embedded')
    expect(wrapper.find('h2').exists()).toBe(false)
  })

  it('uses new styled save/close buttons in user modal header', () => {
    const wrapper = mount(WorkUsersSection, {
      props: { ctx: buildCtx({ showUserForm: true }) },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.find('.modal__head .deal-create-action-btn--save').exists()).toBe(true)
    expect(wrapper.find('.modal__head .deal-create-action-btn--close').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Создать пользователя"]').exists()).toBe(false)
  })
})
