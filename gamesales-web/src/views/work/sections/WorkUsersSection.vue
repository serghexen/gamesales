<template>
  <section class="panel panel--wide">
    <div class="panel__head">
      <div>
        <h2>Пользователи</h2>
        <p class="muted">Создание менеджеров и управление доступом.</p>
      </div>
      <div class="toolbar-actions">
        <button class="deal-create-btn" type="button" aria-label="Добавить пользователя" title="Добавить пользователя" @click="ctx.openUserModal">
          <span class="deal-create-btn__text">Пользователь</span>
          <span class="deal-create-btn__icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke="currentColor" fill="none" class="deal-create-btn__svg" aria-hidden="true">
              <line y2="19" y1="5" x2="12" x1="12"></line>
              <line y2="12" y1="12" x2="19" x1="5"></line>
            </svg>
          </span>
        </button>
        <button
          class="btn btn--icon btn--glow btn--glow-refresh"
          title="Обновить список"
          aria-label="Обновить список"
          :disabled="ctx.userLoading"
          @click="ctx.loadUsers"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 12a8 8 0 1 1-2.3-5.7" />
            <path d="M20 4v6h-6" />
          </svg>
        </button>
      </div>
    </div>
    <div class="panel__body">
      <p class="muted">Нажмите иконку, чтобы добавить пользователя.</p>
      <teleport to="body">
        <div v-if="ctx.showUserForm" class="work-page work-modal-root modal-backdrop" @click.self="ctx.closeUserModal">
          <div :ref="ctx.modalRef" class="modal modal--auto" :style="ctx.modalStyle">
            <div class="panel__head panel__head--tight modal__head" @mousedown="ctx.startModalDrag">
              <h3>Новый пользователь</h3>
              <button
                class="btn btn--icon-plain"
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
                <label class="field">
                  <span class="label">Логин</span>
                  <input v-model.trim="ctx.newUser.username" class="input" placeholder="manager1" />
                </label>
                <label class="field">
                  <span class="label">Пароль</span>
                  <input v-model="ctx.newUser.password" class="input" type="password" />
                </label>
                <label class="field">
                  <span class="label">Роль</span>
                  <select v-model="ctx.newUser.role_code" class="input input--select">
                    <option v-for="r in ctx.roles" :key="r.code" :value="r.code">{{ r.name }}</option>
                  </select>
                </label>
                <div class="toolbar-actions">
                  <button
                    class="btn btn--icon-plain"
                    :disabled="ctx.userLoading"
                    aria-label="Создать пользователя"
                    title="Создать пользователя"
                    @click="ctx.createUser"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                </div>
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
          <col :style="getColumnStyle('role')" />
          <col :style="getColumnStyle('createdAt')" />
        </colgroup>
        <thead>
          <tr>
            <th class="sortable" @click="ctx.toggleUsersSort('username')">
              Логин
              <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Логин пользователя" title="Потяните для изменения ширины" @click.stop.prevent @mousedown.stop.prevent="startResize($event, 'username')" />
            </th>
            <th class="sortable" @click="ctx.toggleUsersSort('role')">
              Роль
              <button class="table-col-resizer" type="button" aria-label="Изменить ширину колонки Роль пользователя" title="Потяните для изменения ширины" @click.stop.prevent @mousedown.stop.prevent="startResize($event, 'role')" />
            </th>
            <th class="sortable" @click="ctx.toggleUsersSort('created_at')">Создан</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in ctx.sortedUsers" :key="u.username">
            <td>{{ u.username }}</td>
            <td>{{ u.role }}</td>
            <td>{{ new Date(u.created_at).toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">Пока нет пользователей.</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'

const tableEl = ref(null)
const { getColumnStyle, startResize } = useResizableTableColumns({
  tableRef: tableEl,
  storageKey: 'work.users.columns.v1',
  columns: [
    { key: 'username', defaultWidth: 34, minWidth: 18 },
    { key: 'role', defaultWidth: 26, minWidth: 14 },
    { key: 'createdAt', defaultWidth: 40, minWidth: 22 },
  ],
})

// Контекст секции пользователей.
defineProps({
  ctx: { type: Object, required: true },
})
</script>
