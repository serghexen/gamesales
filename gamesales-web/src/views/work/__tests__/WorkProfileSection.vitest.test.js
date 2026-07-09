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
            ...[
              ['deals_active.new.sale.create', 'Услуга - создание'],
              ['deals_active.new.sale.draft', 'Услуга - черновик'],
              ['deals_active.view.sale.edit', 'Услуга - редактирование'],
              ['deals_active.new.rental.create', 'Шеринг - создание'],
              ['deals_active.new.rental.draft', 'Шеринг - черновик'],
              ['deals_active.view.rental.edit', 'Шеринг - редактирование'],
            ].map(([action_code, action_name]) => ({
              group_code: 'deals_active',
              group_name: 'Активные сделки',
              group_description: '',
              action_code,
              action_name,
              can_do: true,
            })),
            ...[
              ['deals_completed.view', 'Просматривать'],
              ['deals_completed.edit', 'Редактирование'],
              ['deals_completed.list.customer', 'Список: покупатель'],
              ['deals_completed.view.sale.field.discount', 'Просмотр услуги: Скидка'],
            ].map(([action_code, action_name]) => ({
              group_code: 'deals_completed',
              group_name: 'Завершенные сделки',
              group_description: '',
              action_code,
              action_name,
              can_do: true,
            })),
            ...[
              ['deals_draft.view', 'Просматривать'],
              ['deals_draft.edit', 'Редактирование'],
              ['deals_draft.view.sale.field.discount', 'Просмотр услуги: Скидка'],
            ].map(([action_code, action_name]) => ({
              group_code: 'deals_draft',
              group_name: 'Черновики',
              group_description: '',
              action_code,
              action_name,
              can_do: true,
            })),
            ...[
              ['accounts.view_email', 'Просмотр почты'],
              ['accounts.view_games', 'Просмотр игры'],
              ['accounts.create', 'Создание аккаунта'],
              ['accounts.edit', 'Редактирование'],
              ['accounts.create.field.email', 'Создание: Почта'],
              ['accounts.view.field.email', 'Просмотр: Почта'],
              ['accounts.edit.field.email', 'Редактирование: Почта'],
            ].map(([action_code, action_name]) => ({
              group_code: 'accounts',
              group_name: 'Аккаунты',
              group_description: '',
              action_code,
              action_name,
              can_do: true,
            })),
            ...[
              ['products.view_games', 'Просмотр игр'],
              ['products.create_games', 'Создание игр'],
              ['products.reflect_accounts', 'Отражение аккаунтов'],
              ['products.edit', 'Редактирование'],
              ['products.list.type', 'Список: тип'],
              ['products.list.title', 'Список: товар'],
              ['products.list.platform', 'Список: платформа'],
              ['products.create.field.title', 'Создание: Название'],
              ['products.view.field.title', 'Просмотр: Название'],
              ['products.edit.field.title', 'Редактирование: Название'],
            ].map(([action_code, action_name]) => ({
              group_code: 'products',
              group_name: 'Товары',
              group_description: '',
              action_code,
              action_name,
              can_do: true,
            })),
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
    const sectionsPanel = wrapper.find('.role-access-group--sections')
    expect(sectionsPanel.element.tagName).toBe('DETAILS')
    expect(sectionsPanel.element.open).toBe(false)
    expect(sectionsPanel.find('summary').text()).toContain('Разделы')
    const activeDealsGroup = wrapper.find('.role-active-deals')
    expect(activeDealsGroup.element.tagName).toBe('DETAILS')
    expect(activeDealsGroup.element.open).toBe(false)
    expect(activeDealsGroup.find('summary').text()).toContain('Активные сделки')
    const dealGroups = wrapper.findAll('.role-active-deals')
    expect(dealGroups[0].find('.role-access-group__summary').text()).toContain('Активные сделки')
    expect(dealGroups[1].find('.role-access-group__summary').text()).toContain('Завершенные сделки')
    expect(dealGroups[2].find('.role-access-group__summary').text()).toContain('Черновики')
    expect(dealGroups.slice(0, 3).every((node) => node.element.open === false)).toBe(true)
    expect(dealGroups[1].text()).toContain('Просмотр услуги')
    expect(dealGroups[1].text()).not.toContain('Новая услуга')
    expect(dealGroups[2].text()).not.toContain('Список сделок')
    expect(dealGroups[0].findAll('.role-active-deals__required-badge').length).toBeGreaterThan(0)
    expect(dealGroups[0].findAll('.role-active-deals__required-badge').map((node) => node.text())).toContain('обяз.')
    const accountGroup = wrapper.findAll('.role-active-deals').find((node) => node.find('.role-access-group__summary').text().includes('Аккаунты'))
    expect(accountGroup).toBeTruthy()
    expect(accountGroup.element.open).toBe(false)
    expect(accountGroup.text()).toContain('Список аккаунтов')
    expect(accountGroup.text()).toContain('Поля формы')
    expect(accountGroup.findAll('.role-active-deals__required-badge').map((node) => node.text())).toContain('обяз.')
    expect(accountGroup.findAll('.role-active-deals__matrix th').map((node) => node.text())).toEqual([
      'Поле',
      'Создание',
      'Просмотр',
      'Редактирование',
    ])
    const productGroup = wrapper.findAll('.role-active-deals').find((node) => node.find('.role-access-group__summary').text().includes('Товары'))
    expect(productGroup).toBeTruthy()
    expect(productGroup.element.open).toBe(false)
    expect(productGroup.text()).toContain('Список товаров')
    expect(productGroup.text()).toContain('Поля формы')
    expect(productGroup.findAll('.role-active-deals__required-badge').map((node) => node.text())).toContain('обяз.')
    expect(productGroup.findAll('.role-active-deals__matrix th').map((node) => node.text())).toEqual([
      'Поле',
      'Создание',
      'Просмотр',
      'Редактирование',
    ])
    expect(wrapper.text()).toContain('Активные сделки')
    expect(wrapper.text()).toContain('Услуга - создание')
    expect(wrapper.text()).toContain('Услуга - черновик')
    expect(wrapper.text()).toContain('Услуга - редактирование')
    expect(wrapper.text()).toContain('Шеринг - создание')
    expect(wrapper.text()).toContain('Шеринг - черновик')
    expect(wrapper.text()).toContain('Шеринг - редактирование')
    expect(wrapper.text()).not.toContain('Создание · Новая услуга')
    const operationChips = wrapper.findAll('.role-active-deals__ops .role-active-deals__chip')
    expect(operationChips[3].text()).toContain('Шеринг - создание')
    expect(operationChips[3].classes()).toContain('role-active-deals__chip--new-row')
    const fieldPanel = wrapper.find('.role-active-deals__panel--fields')
    expect(fieldPanel.element.tagName).toBe('DETAILS')
    expect(fieldPanel.element.open).toBe(false)
    expect(fieldPanel.find('summary').text()).toContain('Поля формы')
    const nestedPanels = wrapper.findAll('.role-active-deals__panel')
    expect(nestedPanels.every((node) => node.element.open === false)).toBe(true)
    expect(wrapper.text()).not.toContain('Основное')
    expect(wrapper.text()).not.toContain('Клиент и заказ')
    const matrixHeaders = dealGroups[0].findAll('.role-active-deals__matrix th').map((node) => node.text())
    expect(matrixHeaders).toEqual([
      'Поле',
      'Новая услуга',
      'Просмотр услуги',
      'Редакт. услуги',
      'Новый шеринг',
      'Просмотр шеринга',
      'Редакт. шеринга',
    ])
    const completedMatrixHeaders = dealGroups[1].findAll('.role-active-deals__matrix th').map((node) => node.text())
    expect(completedMatrixHeaders).toEqual([
      'Поле',
      'Просмотр услуги',
      'Редакт. услуги',
      'Просмотр шеринга',
      'Редакт. шеринга',
    ])
  })
})
