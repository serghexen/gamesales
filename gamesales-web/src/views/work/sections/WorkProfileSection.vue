<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div v-if="showAdminTabs" class="tabs profile-admin-links">
        <router-link
          v-if="ctx.canViewUsersSection"
          class="tab"
          :class="{ active: !rolePermissionsFormOpen }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'profile', admin_panel: undefined } }"
          @click="openUsersPanel"
        >
          Пользователи
        </router-link>
        <button
          v-if="ctx.canManageRolePermissions"
          class="tab profile-role-permissions__toggle"
          :class="{ active: rolePermissionsFormOpen }"
          type="button"
          :disabled="ctx.rolePermissionsLoading || ctx.rolePermissionsSaving"
          @click="openRolePermissionsForm"
        >
          Доступы
        </button>
        <!-- Переносим вход в аналитику в профиль админа, чтобы не держать вкладку в шапке. -->
        <router-link
          v-if="ctx.canViewAnalyticsSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics', admin_panel: undefined } }"
        >
          Аналитика
        </router-link>
        <!-- Переносим справочники в профиль админа, чтобы разгрузить шапку. -->
        <router-link
          v-if="ctx.canViewCatalogsSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs', admin_panel: undefined } }"
        >
          Справочники
        </router-link>
        <router-link
          v-if="ctx.canViewFinanceSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'finance', admin_panel: undefined } }"
        >
          Финансы
        </router-link>
      </div>
      <section v-if="ctx.canManageRolePermissions && rolePermissionsFormOpen" class="panel admin-content-shell profile-role-permissions">
        <div class="panel__body">
          <div class="profile-role-permissions__form">
            <div class="deal-form__double">
              <label class="field">
                <span class="label">Роль</span>
                <select
                  :value="ctx.rolePermissionsRoleCode"
                  class="input input--select"
                  :disabled="ctx.rolePermissionsLoading || ctx.rolePermissionsSaving"
                  @change="ctx.setRolePermissionsRoleCode($event.target.value)"
                >
                  <option value="">— выберите роль —</option>
                  <option
                    v-for="role in (ctx.rolePermissionsRoles || [])"
                    :key="`role-permission-${role.code}`"
                    :value="role.code"
                  >
                    {{ role.name }} ({{ role.code }})
                  </option>
                </select>
              </label>
              <div class="field field--align-end">
                <button
                  class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--save profile-role-permissions__save"
                  type="button"
                  aria-label="Сохранить права"
                  title="Сохранить права"
                  :disabled="!ctx.rolePermissionsRoleCode || ctx.rolePermissionsLoading || ctx.rolePermissionsSaving"
                  @click="ctx.saveRolePermissions"
                >
                  <svg v-if="!ctx.rolePermissionsSaving" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 4h12l4 4v12H4z" />
                    <path d="M7 4v6h8V4" />
                    <path d="M7 20v-6h10v6" />
                  </svg>
                  <span v-else class="spinner" aria-hidden="true"></span>
                </button>
              </div>
            </div>
            <p v-if="ctx.rolePermissionsLoading" class="muted">Загрузка доступов…</p>
            <div v-else class="check-list check-list--compact check-list--role-permissions">
              <label
                v-for="item in (ctx.rolePermissionsItems || [])"
                :key="`section-permission-${item.section_code}`"
                class="check-item"
              >
                <input
                  type="checkbox"
                  :checked="item.can_view"
                  :disabled="ctx.rolePermissionsLoading || ctx.rolePermissionsSaving"
                  @change="ctx.setRolePermissionItem(item.section_code, $event.target.checked)"
                />
                <span>{{ item.section_name }}</span>
              </label>
              <p v-if="!(ctx.rolePermissionsItems || []).length" class="muted">Для выбранной роли пока нет настроек.</p>
            </div>
            <p v-if="ctx.rolePermissionsError" class="bad">{{ ctx.rolePermissionsError }}</p>
            <p v-if="ctx.rolePermissionsOk" class="ok">{{ ctx.rolePermissionsOk }}</p>
          </div>
        </div>
      </section>
      <WorkUsersSection v-if="ctx.canViewUsersSection && !rolePermissionsFormOpen" :ctx="ctx.usersSectionCtx" />
    </div>
  </section>
</template>

<script setup>
import { computed, ref, unref, watch } from 'vue'
import WorkUsersSection from './WorkUsersSection.vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})
const rolePermissionsFormOpen = ref(false)
const showAdminTabs = computed(() => Boolean(
  props.ctx.canViewUsersSection
  || props.ctx.canManageRolePermissions
  || props.ctx.canViewAnalyticsSection
  || props.ctx.canViewCatalogsSection
  || props.ctx.canViewFinanceSection,
))

// Сохраняем текущие query-параметры при переходе в аналитику из профиля.
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
const accessPanelRequested = computed(() => String(routeQuery.value?.admin_panel || '').trim().toLowerCase() === 'access')

// Открывает форму управления доступами как отдельную вкладку без toggle-поведения.
const openRolePermissionsForm = async () => {
  if (rolePermissionsFormOpen.value) return
  rolePermissionsFormOpen.value = true
  // Перед показом формы подгружаем роли и права, чтобы список не открывался пустым.
  if (typeof props.ctx.ensureRolePermissionsFormDataLoaded === 'function') {
    await props.ctx.ensureRolePermissionsFormDataLoaded()
  }
}

// Возвращает профиль в режим пользователей даже если route не меняется.
const openUsersPanel = () => {
  rolePermissionsFormOpen.value = false
}

// При переходе из других разделов сразу открываем форму доступов по query-параметру.
watch(accessPanelRequested, async (requested) => {
  if (!requested) {
    // При возврате на "Пользователи" закрываем панель доступов.
    rolePermissionsFormOpen.value = false
    return
  }
  if (rolePermissionsFormOpen.value || !props.ctx.canManageRolePermissions) return
  rolePermissionsFormOpen.value = true
  if (typeof props.ctx.ensureRolePermissionsFormDataLoaded === 'function') {
    await props.ctx.ensureRolePermissionsFormDataLoaded()
  }
}, { immediate: true })
</script>
