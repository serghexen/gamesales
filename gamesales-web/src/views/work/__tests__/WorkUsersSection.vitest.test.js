import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import WorkUsersSection from '../sections/WorkUsersSection.vue'

function buildCtx(overrides = {}) {
  // Собираем минимальный контекст секции пользователей для проверки разметки.
  return {
    openUserModal: vi.fn(),
    openUserViewModal: vi.fn(),
    loadUsers: vi.fn(),
    userLoading: false,
    showUserForm: false,
    userFormMode: 'create',
    startUserEdit: vi.fn(),
    closeUserModal: vi.fn(),
    modalRef: ref(null),
    modalStyle: {},
    startModalDrag: vi.fn(),
    newUser: { username: '', password: '', name: '', role_code: 'manager' },
    editUser: { username: '', name: '', role_code: 'manager', created_at: '' },
    roles: [{ code: 'manager', name: 'Менеджер' }],
    createUser: vi.fn(),
    updateUser: vi.fn(),
    submitUserForm: vi.fn(),
    openUserRoleModal: vi.fn(),
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
      props: { ctx: buildCtx({ showUserForm: true, userFormMode: 'create' }) },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.find('.modal__head .deal-create-action-btn--save').exists()).toBe(true)
    expect(wrapper.find('.modal__head .deal-create-action-btn--close').exists()).toBe(true)
    expect(wrapper.find('.modal__head .deal-create-action-btn--edit').exists()).toBe(false)
  })

  it('renders user view mode with edit action and readonly fields', () => {
    const wrapper = mount(WorkUsersSection, {
      props: {
        ctx: buildCtx({
          showUserForm: true,
          userFormMode: 'view',
          editUser: {
            username: 'manager1',
            name: 'Иван',
            role_code: 'operator',
            created_at: '2026-05-27T07:00:00Z',
          },
        }),
      },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.text()).toContain('Пользователь: manager1')
    expect(wrapper.find('.modal__head .deal-create-action-btn--edit').exists()).toBe(true)
    expect(wrapper.find('input[readonly]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  it('opens user card when clicking table row', async () => {
    const openUserViewModal = vi.fn()
    const wrapper = mount(WorkUsersSection, {
      props: {
        ctx: buildCtx({
          openUserViewModal,
          sortedUsers: [{ username: 'manager1', name: 'Иван', role: 'manager', created_at: '2026-05-27T07:00:00Z' }],
        }),
      },
      global: {
        stubs: { teleport: true },
      },
    })

    await wrapper.find('tbody tr.clickable-row').trigger('click')
    expect(openUserViewModal).toHaveBeenCalledTimes(1)
  })

  it('renders edit mode with editable name field', () => {
    const wrapper = mount(WorkUsersSection, {
      props: {
        ctx: buildCtx({
          showUserForm: true,
          userFormMode: 'edit',
          editUser: {
            username: 'manager1',
            name: 'Иван',
            role_code: 'operator',
            created_at: '2026-05-27T07:00:00Z',
          },
        }),
      },
      global: {
        stubs: { teleport: true },
      },
    })

    expect(wrapper.text()).toContain('Редактирование пользователя: manager1')
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
    expect(wrapper.find('select.input--select').exists()).toBe(true)
  })
})
