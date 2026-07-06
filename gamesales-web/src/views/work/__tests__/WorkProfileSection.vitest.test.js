import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import WorkProfileSection from '../sections/WorkProfileSection.vue'

function buildCtx(overrides = {}) {
  // Собираем минимальный контекст профиля для проверки видимости секции пользователей.
  return {
    isAdmin: false,
    canManageRolePermissions: false,
    canViewCatalogsSection: false,
    canViewFinanceSection: false,
    canViewUsersSection: false,
    routeQuery: {},
    usersSectionCtx: {},
    rolePermissionsRoles: [],
    rolePermissionsRoleCode: '',
    rolePermissionsItems: [],
    roleActionPermissionsItems: [],
    rolePermissionsLoading: false,
    rolePermissionsSaving: false,
    rolePermissionsError: '',
    rolePermissionsOk: '',
    ensureRolePermissionsFormDataLoaded: vi.fn().mockResolvedValue(undefined),
    setRolePermissionsRoleCode: vi.fn(),
    setRolePermissionItem: vi.fn(),
    setRoleActionPermissionItem: vi.fn(),
    saveRolePermissions: vi.fn(),
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
        ctx: buildCtx({
          isAdmin: true,
          canManageRolePermissions: true,
          canViewCatalogsSection: true,
          canViewFinanceSection: true,
          canViewUsersSection: true,
          usersSectionCtx: { sortedUsers: [{ username: 'admin' }] },
        }),
      },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a class="admin-link"><slot /></a>',
          },
          WorkUsersSection: {
            template: '<div class="users-stub">Users section</div>',
          },
        },
      },
    })

    expect(wrapper.find('.users-stub').exists()).toBe(true)
    expect(wrapper.findAll('.admin-link')).toHaveLength(3)
    expect(wrapper.text()).toContain('Пользователи')
    expect(wrapper.text()).not.toContain('Аналитика')
    expect(wrapper.text()).toContain('Справочники')
    expect(wrapper.text()).toContain('Финансы')
  })

  it('hides users section for non-admin', () => {
    const wrapper = mount(WorkProfileSection, {
      props: {
        ctx: buildCtx({ isAdmin: false }),
      },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a class="admin-link"><slot /></a>',
          },
          WorkUsersSection: {
            template: '<div class="users-stub">Users section</div>',
          },
        },
      },
    })

    expect(wrapper.find('.users-stub').exists()).toBe(false)
    expect(wrapper.find('.admin-link').exists()).toBe(false)
  })

  it('opens role permissions form after clicking access button', async () => {
    const ensureRolePermissionsFormDataLoaded = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(WorkProfileSection, {
      props: {
        ctx: buildCtx({
          canManageRolePermissions: true,
          ensureRolePermissionsFormDataLoaded,
          rolePermissionsRoles: [{ code: 'manager', name: 'Manager' }],
          rolePermissionsRoleCode: 'manager',
          rolePermissionsItems: [
            { section_code: 'deals', section_name: 'Сделки', can_view: true },
            { section_code: 'finance', section_name: 'Финансы', can_view: false },
          ],
          roleActionPermissionsItems: [
            {
              group_code: 'deals_active',
              group_name: 'Активные сделки',
              group_description: 'Что можно делать в активных сделках',
              action_code: 'deals_active.create',
              action_name: 'Создание',
              can_do: true,
            },
          ],
        }),
      },
      global: {
        stubs: {
          teleport: true,
          RouterLink: {
            props: ['to'],
            template: '<a class="admin-link"><slot /></a>',
          },
          WorkUsersSection: {
            template: '<div class="users-stub">Users section</div>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Доступы')
    expect(wrapper.find('button[aria-label="Сохранить права"]').exists()).toBe(false)
    await wrapper.find('button.profile-role-permissions__toggle').trigger('click')
    expect(ensureRolePermissionsFormDataLoaded).toHaveBeenCalledTimes(1)
    expect(wrapper.find('button[aria-label="Сохранить права"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Сделки')
    expect(wrapper.text()).toContain('Финансы')
    expect(wrapper.text()).toContain('Активные сделки')
    expect(wrapper.text()).toContain('Создание')
  })
})
