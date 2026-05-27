<template>
  <component :is="props.embedded ? 'div' : 'section'" :class="props.embedded ? 'work-users-embedded' : 'panel panel--wide'">
    <div class="panel__head panel__head--users">
      <div class="toolbar-actions toolbar-actions--users">
        <button class="deal-create-btn" type="button" aria-label="Добавить пользователя" title="Добавить пользователя" @click="ctx.openUserModal">
          <span class="deal-create-btn__text">Пользователь</span>
          <span class="deal-create-btn__icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
              <line y2="19" y1="5" x2="12" x1="12"></line>
              <line y2="12" y1="12" x2="19" x1="5"></line>
            </svg>
          </span>
        </button>
      </div>
      <div class="toolbar-actions toolbar-actions--users-refresh">
        <button
          class="deal-refresh-btn"
          title="Обновить список"
          aria-label="Обновить список"
          :disabled="ctx.userLoading"
          @click="ctx.loadUsers"
        >
          <span class="deal-refresh-btn__content">
            <svg viewBox="0 0 24 24" aria-hidden="true" class="deal-refresh-btn__icon">
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v6h-6" />
            </svg>
          </span>
        </button>
      </div>
    </div>
    <div class="panel__body">
      <teleport to="body">
        <div v-if="ctx.showUserForm" class="work-page work-modal-root modal-backdrop" @click.self="ctx.closeUserModal">
          <div :ref="ctx.modalRef" class="modal modal--auto" :style="ctx.modalStyle">
            <div class="panel__head panel__head--tight modal__head" @mousedown="ctx.startModalDrag">
              <h3>{{ getUserModalTitle() }}</h3>
              <div class="toolbar-actions">
                <button
                  v-if="ctx.userFormMode === 'create' || ctx.userFormMode === 'edit'"
                  class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
                  :disabled="ctx.userLoading"
                  aria-label="Сохранить"
                  title="Сохранить"
                  @click="ctx.submitUserForm"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 4h12l4 4v12H4z" />
                    <path d="M7 4v6h8V4" />
                    <path d="M7 20v-6h10v6" />
                  </svg>
                </button>
                <button
                  v-if="ctx.userFormMode === 'view'"
                  class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
                  type="button"
                  aria-label="Редактировать"
                  title="Редактировать"
                  :disabled="ctx.userLoading"
                  @click="ctx.startUserEdit"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                    <path d="M13 6l4 4" />
                  </svg>
                </button>
                <button
                  class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
                  type="button"
                  aria-label="Закрыть"
                  title="Закрыть"
                  @click="ctx.closeUserModal"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 6l12 12M18 6l-12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="modal__body" :class="{ 'modal__body--locked': ctx.userLoading }">
              <div v-if="ctx.userLoading" class="modal__body-overlay">
                <div class="loader-wrap loader-wrap--compact">
                  <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster wheel-and-hamster--mini">
                    <div class="wheel"></div>
                    <div class="hamster">
                      <div class="hamster__body">
                        <div class="hamster__head">
                          <div class="hamster__ear"></div>
                          <div class="hamster__eye"></div>
                          <div class="hamster__nose"></div>
                        </div>
                        <div class="hamster__limb hamster__limb--fr"></div>
                        <div class="hamster__limb hamster__limb--fl"></div>
                        <div class="hamster__limb hamster__limb--br"></div>
                        <div class="hamster__limb hamster__limb--bl"></div>
                        <div class="hamster__tail"></div>
                      </div>
                    </div>
                    <div class="spoke"></div>
                  </div>
                  <p class="muted">Загрузка…</p>
                </div>
              </div>
              <div class="form form--stack form--compact">
                <template v-if="ctx.userFormMode === 'create'">
                  <label class="field">
                    <span class="label">Логин</span>
                    <input v-model.trim="ctx.newUser.username" class="input" placeholder="manager1" />
                  </label>
                  <label class="field">
                    <span class="label">Пароль</span>
                    <input v-model="ctx.newUser.password" class="input" type="password" />
                  </label>
                  <label class="field">
                    <span class="label">Имя</span>
                    <input v-model.trim="ctx.newUser.name" class="input" placeholder="Иван Иванов" />
                  </label>
                  <label class="field">
                    <span class="label">Роль</span>
                    <select v-model="ctx.newUser.role_code" class="input input--select">
                      <option v-for="r in ctx.roles" :key="r.code" :value="r.code">{{ r.name }}</option>
                    </select>
                  </label>
                </template>
                <template v-else>
                  <label class="field">
                    <span class="label">Логин</span>
                    <input :value="ctx.editUser.username" class="input" readonly />
                  </label>
                  <label class="field">
                    <span class="label">Имя</span>
                    <input v-model.trim="ctx.editUser.name" class="input" :readonly="ctx.userFormMode === 'view'" />
                  </label>
                  <label class="field">
                    <span class="label">Роль</span>
                    <select v-if="ctx.userFormMode === 'edit'" v-model="ctx.editUser.role_code" class="input input--select">
                      <option v-for="r in ctx.roles" :key="r.code" :value="r.code">{{ r.name }}</option>
                    </select>
                    <input
                      v-else
                      class="input"
                      :value="getRoleLabel(ctx.editUser.role_code)"
                      readonly
                    />
                  </label>
                  <label class="field">
                    <span class="label">Создан</span>
                    <input class="input" :value="formatUserDate(ctx.editUser.created_at)" readonly />
                  </label>
                </template>
              </div>
            </div>
          </div>
        </div>
      </teleport>

      <p v-if="ctx.userError" class="bad">{{ ctx.userError }}</p>
      <p v-if="ctx.userOk" class="ok">{{ ctx.userOk }}</p>
      <div v-if="ctx.userLoading" class="loader-wrap">
        <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster">
          <div class="wheel"></div>
          <div class="hamster">
            <div class="hamster__body">
              <div class="hamster__head">
                <div class="hamster__ear"></div>
                <div class="hamster__eye"></div>
                <div class="hamster__nose"></div>
              </div>
              <div class="hamster__limb hamster__limb--fr"></div>
              <div class="hamster__limb hamster__limb--fl"></div>
              <div class="hamster__limb hamster__limb--br"></div>
              <div class="hamster__limb hamster__limb--bl"></div>
              <div class="hamster__tail"></div>
            </div>
          </div>
          <div class="spoke"></div>
        </div>
      </div>
      <table v-else-if="ctx.sortedUsers.length" ref="tableEl" class="table">
        <colgroup>
          <col :style="getColumnStyle('username')" />
          <col :style="getColumnStyle('name')" />
          <col :style="getColumnStyle('role')" />
          <col :style="getColumnStyle('createdAt')" />
        </colgroup>
        <thead>
          <tr>
            <th class="sortable" @click="ctx.toggleUsersSort('username')">
              Логин
              <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Логин пользователя" title="Потяните для изменения ширины" @click.stop.prevent @mousedown.stop.prevent="startResize($event, 'username')" />
            </th>
            <th class="sortable" @click="ctx.toggleUsersSort('name')">
              Имя
              <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Имя пользователя" title="Потяните для изменения ширины" @click.stop.prevent @mousedown.stop.prevent="startResize($event, 'name')" />
            </th>
            <th class="sortable" @click="ctx.toggleUsersSort('role')">
              Роль
              <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Роль пользователя" title="Потяните для изменения ширины" @click.stop.prevent @mousedown.stop.prevent="startResize($event, 'role')" />
            </th>
            <th class="sortable" @click="ctx.toggleUsersSort('created_at')">Создан</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in ctx.sortedUsers"
            :key="u.username"
            class="clickable-row"
            @click="ctx.openUserViewModal(u)"
          >
            <td>{{ u.username }}</td>
            <td>{{ u.name || '—' }}</td>
            <td>{{ u.role }}</td>
            <td>{{ new Date(u.created_at).toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">Пока нет пользователей.</p>
    </div>
  </component>
</template>

<script setup>
import { ref } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'

const tableEl = ref(null)
const { getColumnStyle, startResize } = useResizableTableColumns({
  tableRef: tableEl,
  storageKey: 'work.users.columns.v1',
  columns: [
    { key: 'username', defaultWidth: 28, minWidth: 16 },
    { key: 'name', defaultWidth: 28, minWidth: 16 },
    { key: 'role', defaultWidth: 20, minWidth: 14 },
    { key: 'createdAt', defaultWidth: 24, minWidth: 20 },
  ],
})

// Контекст секции пользователей.
const props = defineProps({
  ctx: { type: Object, required: true },
  embedded: { type: Boolean, default: false },
})

// Возвращает заголовок модалки по текущему сценарию.
function getUserModalTitle() {
  if (props.ctx.userFormMode === 'create') return 'Новый пользователь'
  if (props.ctx.userFormMode === 'edit') return `Редактирование пользователя: ${props.ctx.editUser.username}`
  return `Пользователь: ${props.ctx.editUser.username}`
}

// Преобразует код роли в человекочитаемое название.
function getRoleLabel(roleCode) {
  const code = String(roleCode || '').trim()
  const found = Array.isArray(props.ctx.roles)
    ? props.ctx.roles.find((item) => String(item?.code || '').trim() === code)
    : null
  return found?.name || code || '—'
}

// Форматирует дату создания пользователя для readonly-поля карточки.
function formatUserDate(value) {
  const raw = String(value || '').trim()
  if (!raw) return '—'
  const date = new Date(raw)
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleString()
}
</script>
