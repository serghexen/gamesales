<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div v-if="ctx.canViewAnalyticsSection || ctx.canViewCatalogsSection || ctx.canManageRolePermissions" class="tabs profile-admin-links">
        <!-- Переносим вход в аналитику в профиль админа, чтобы не держать вкладку в шапке. -->
        <router-link
          v-if="ctx.canViewAnalyticsSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics' } }"
        >
          Аналитика
        </router-link>
        <!-- Переносим справочники в профиль админа, чтобы разгрузить шапку. -->
        <router-link
          v-if="ctx.canViewCatalogsSection"
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs' } }"
        >
          Справочники
        </router-link>
        <button
          v-if="ctx.canManageRolePermissions"
          class="tab profile-role-permissions__toggle"
          type="button"
          :disabled="ctx.rolePermissionsLoading || ctx.rolePermissionsSaving"
          @click="toggleRolePermissionsForm"
        >
          {{ rolePermissionsFormOpen ? 'Скрыть доступы' : 'Доступы' }}
        </button>
      </div>
      <section v-if="ctx.canManageRolePermissions" class="field field--full profile-role-permissions">
        <div v-if="rolePermissionsFormOpen" class="profile-role-permissions__form">
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
          <div v-else class="check-list check-list--compact">
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
      </section>
      <WorkUsersSection v-if="ctx.canViewUsersSection" :ctx="ctx.usersSectionCtx" />
    </div>
  </section>
</template>

<script setup>
import { computed, ref, unref } from 'vue'
import WorkUsersSection from './WorkUsersSection.vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})
const rolePermissionsFormOpen = ref(false)

// Сохраняем текущие query-параметры при переходе в аналитику из профиля.
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})

// Переключает форму управления доступами внутри профиля.
const toggleRolePermissionsForm = async () => {
  const next = !rolePermissionsFormOpen.value
  rolePermissionsFormOpen.value = next
  if (!next) return
  // Перед показом формы подгружаем роли и права, чтобы список не открывался пустым.
  if (typeof props.ctx.ensureRolePermissionsFormDataLoaded === 'function') {
    await props.ctx.ensureRolePermissionsFormDataLoaded()
  }
}
</script>
