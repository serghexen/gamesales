<template>
  <teleport to="body">
    <div
      v-if="editGame.open || showGameForm"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeGameModal"
    >
      <div
        :ref="modalRef"
        :class="['modal', editGame.open ? 'modal--full' : 'modal--auto']"
        :style="modalStyle"
      >
        <!-- Шапка модалки: действия сохранить/создать/удалить/закрыть -->
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editGame.open ? (editGame.title ? `Игра ${editGame.title}` : 'Игра') : 'Новая игра' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editGame.open && gameEditMode === 'edit'"
              class="btn btn--icon-plain"
              @click="updateGame"
              :disabled="gameLoading"
              aria-label="Сохранить изменения"
              title="Сохранить изменения"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="!editGame.open"
              class="btn btn--icon-plain"
              @click="createGame"
              :disabled="gameLoading"
              aria-label="Добавить игру"
              title="Добавить игру"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editGame.open"
              class="btn btn--icon-plain btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="gameEditMode = 'edit'"
              :disabled="gameEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editGame.open"
              class="btn btn--icon-plain btn--danger"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deleteGame"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeGameModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal__body" :class="{ 'modal__body--locked': gameLoading }">
          <div v-if="gameLoading" class="modal__body-overlay">
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

          <!-- Редактирование существующей игры -->
          <div v-if="editGame.open" class="form form--stack form--compact">
            <div class="field field--full">
              <span class="label">Логотип</span>
              <div class="logo-upload">
                <div v-if="editGame.logo_b64" class="logo-preview">
                  <img :src="gameLogoSrc" alt="logo" />
                </div>
                <div v-else-if="gameLogoLoading" class="logo-preview logo-preview--loading">
                  <span class="muted">Загрузка…</span>
                </div>
                <div class="logo-actions">
                  <input
                    class="input input--file"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    @change="onGameLogoSelected"
                    :disabled="gameEditMode === 'view'"
                  />
                  <span v-if="gameLogoUploading" class="muted">Загрузка {{ gameLogoProgress }}%</span>
                  <button
                    v-if="editGame.logo_b64"
                    class="ghost ghost--small ghost--danger"
                    type="button"
                    @click="removeGameLogo"
                    :disabled="gameEditMode === 'view'"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            </div>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editGame.title" class="input" placeholder="Например, GTA V" :readonly="gameEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="editGame.short_title" class="input" placeholder="Например, GTA V" :readonly="gameEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Ссылка</span>
              <input v-model.trim="editGame.link" class="input" placeholder="https://..." :readonly="gameEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Язык текста</span>
              <input v-model.trim="editGame.text_lang" class="input" placeholder="RU/EN/..." :readonly="gameEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Язык озвучки</span>
              <input v-model.trim="editGame.audio_lang" class="input" placeholder="RU/EN/..." :readonly="gameEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Поддержка VR</span>
              <input v-model.trim="editGame.vr_support" class="input" placeholder="например: есть/нет" :readonly="gameEditMode === 'view'" />
            </label>
            <div class="field field--full">
              <span class="label">Платформы</span>
              <div class="check-list check-list--compact">
                <label v-for="p in platforms" :key="p.code" class="check-item">
                  <input type="checkbox" :value="p.code" v-model="editGame.platform_codes" :disabled="gameEditMode === 'view'" />
                  <span>{{ p.name }} ({{ p.code }})</span>
                </label>
              </div>
            </div>
            <label class="field">
              <span class="label">Регион</span>
              <input
                v-if="gameEditMode === 'view'"
                class="input"
                :value="getRegionLabel(editGame.region_code)"
                readonly
              />
              <select v-else v-model="editGame.region_code" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="r in regions" :key="r.code" :value="r.code">
                  {{ r.name }} ({{ r.code }})
                </option>
              </select>
            </label>
            <div class="divider"></div>
            <div class="field field--full">
              <span class="label">Аккаунты по сделкам</span>
              <p v-if="gameAccountsError" class="bad">{{ gameAccountsError }}</p>
              <div v-if="gameAccountsLoading" class="loader-wrap loader-wrap--compact">
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
              </div>
              <table v-else-if="pagedGameAccounts.length" class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th class="sortable" @click="sortGameAccounts('login_full')">Аккаунт</th>
                    <th class="sortable" @click="sortGameAccounts('platform_code')">Платформа</th>
                    <th class="sortable cell--num" @click="sortGameAccounts('free_slots')">Свободно</th>
                    <th class="sortable cell--num" @click="sortGameAccounts('occupied_slots')">Занято</th>
                    <th class="cell--tight"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in pagedGameAccounts" :key="`${a.account_id}-${a.platform_code}`">
                    <td>{{ a.login_full || '—' }}</td>
                    <td>{{ (a.platform_code || '—').toUpperCase() }}</td>
                    <td class="cell--num">{{ a.free_slots ?? 0 }}</td>
                    <td class="cell--num">{{ a.occupied_slots ?? 0 }}</td>
                    <td class="cell--tight">
                      <button class="ghost ghost--small" type="button" @click="openAccountFromGame(a.login_full)">
                        Открыть
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Сделок по игре пока нет.</p>
              <div v-if="gameAccountsTotalPages > 1" class="pager">
                <button class="ghost" @click="prevGameAccountsPage" :disabled="gameAccountsPage <= 1">
                  ← Назад
                </button>
                <span class="muted">Страница {{ gameAccountsPage }} из {{ gameAccountsTotalPages }}</span>
                <button class="ghost" @click="nextGameAccountsPage" :disabled="gameAccountsPage >= gameAccountsTotalPages">
                  Вперёд →
                </button>
              </div>
            </div>
            <div class="field field--full">
              <span class="label">Слоты по игре</span>
              <p v-if="gameSlotAssignmentsError" class="bad">{{ gameSlotAssignmentsError }}</p>
              <div v-if="gameSlotAssignmentsLoading" class="loader-wrap loader-wrap--compact">
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
              </div>
              <table v-else-if="gameSlotAssignments.length" class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th>Аккаунт</th>
                    <th>Слот</th>
                    <th>Покупатель</th>
                    <th>Статус</th>
                    <th>Назначено</th>
                    <th>Снято</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in gameSlotAssignments" :key="s.assignment_id">
                    <td>{{ s.account_login || s.account_id || '—' }}</td>
                    <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                    <td>{{ s.customer_nickname || '—' }}</td>
                    <td>{{ getSlotAssignmentStatus(s) }}</td>
                    <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                    <td>{{ s.released_at ? formatDateTimeMinutes(s.released_at) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Слотов по игре пока нет.</p>
            </div>
            <p v-if="gameError" class="bad">{{ gameError }}</p>
            <p v-if="gameOk" class="ok">{{ gameOk }}</p>
          </div>

          <!-- Создание новой игры -->
          <div v-else class="form form--stack form--compact">
            <div class="field field--full">
              <span class="label">Логотип</span>
              <p class="muted">Логотип можно загрузить после создания игры.</p>
            </div>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="newGame.title" class="input" placeholder="Например, GTA V" />
            </label>
            <label class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="newGame.short_title" class="input" placeholder="Например, GTA V" />
            </label>
            <label class="field">
              <span class="label">Ссылка</span>
              <input v-model.trim="newGame.link" class="input" placeholder="https://..." />
            </label>
            <label class="field">
              <span class="label">Язык текста</span>
              <input v-model.trim="newGame.text_lang" class="input" placeholder="RU/EN/..." />
            </label>
            <label class="field">
              <span class="label">Язык озвучки</span>
              <input v-model.trim="newGame.audio_lang" class="input" placeholder="RU/EN/..." />
            </label>
            <label class="field">
              <span class="label">Поддержка VR</span>
              <input v-model.trim="newGame.vr_support" class="input" placeholder="например: есть/нет" />
            </label>
            <div class="field field--full">
              <span class="label">Платформы (опционально)</span>
              <div class="check-list check-list--compact">
                <label v-for="p in platforms" :key="p.code" class="check-item">
                  <input type="checkbox" :value="p.code" v-model="newGame.platform_codes" />
                  <span>{{ p.name }} ({{ p.code }})</span>
                </label>
              </div>
            </div>
            <label class="field">
              <span class="label">Регион (опционально)</span>
              <select v-model="newGame.region_code" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="r in regions" :key="r.code" :value="r.code">
                  {{ r.name }} ({{ r.code }})
                </option>
              </select>
            </label>
            <p v-if="gameError" class="bad">{{ gameError }}</p>
            <p v-if="gameOk" class="ok">{{ gameOk }}</p>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { reactive, toRefs } from 'vue'

// Передаем один объект контекста, чтобы не раздувать длинный список props.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  editGame,
  showGameForm,
  closeGameModal,
  modalRef,
  modalStyle,
  startModalDrag,
  gameEditMode,
  updateGame,
  gameLoading,
  createGame,
  deleteGame,
  gameLogoSrc,
  gameLogoLoading,
  onGameLogoSelected,
  gameLogoUploading,
  gameLogoProgress,
  removeGameLogo,
  platforms,
  getRegionLabel,
  regions,
  gameAccountsError,
  gameAccountsLoading,
  pagedGameAccounts,
  sortGameAccounts,
  openAccountFromGame,
  gameAccountsTotalPages,
  gameAccountsPage,
  prevGameAccountsPage,
  nextGameAccountsPage,
  gameSlotAssignmentsError,
  gameSlotAssignmentsLoading,
  gameSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  gameError,
  gameOk,
  newGame,
} = toRefs(ctx)
</script>
