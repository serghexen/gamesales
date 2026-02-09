<template>

            <teleport to="body">
              <div v-if="editAccount.open" class="work-page work-modal-root modal-backdrop" @click.self="cancelEditAccount">
                <div :ref="modalRef" class="modal" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>{{ accountModalMode === 'create' ? 'Новый аккаунт' : 'Аккаунт' }}</h3>
                    <div class="toolbar-actions">
                      <button
                        v-if="accountModalMode === 'edit' && accountEditMode === 'edit'"
                        class="btn btn--icon-plain"
                        @click="updateAccount"
                        :disabled="accountsLoading"
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
                        v-if="accountModalMode === 'create'"
                        class="btn btn--icon-plain"
                        @click="createAccount"
                        :disabled="accountsLoading"
                        aria-label="Создать аккаунт"
                        title="Создать аккаунт"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 4h12l4 4v12H4z" />
                          <path d="M7 4v6h8V4" />
                          <path d="M7 20v-6h10v6" />
                        </svg>
                      </button>
                      <button
                        v-if="accountModalMode === 'edit'"
                        class="btn btn--icon-plain btn--edit"
                        type="button"
                        aria-label="Редактировать"
                        title="Редактировать"
                        @click="setAccountEditMode('edit')"
                        :disabled="accountEditMode === 'edit'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                          <path d="M13 6l4 4" />
                        </svg>
                      </button>
                      <button
                        v-if="accountModalMode === 'edit'"
                        class="btn btn--icon-plain btn--danger"
                        type="button"
                        aria-label="Удалить"
                        title="Удалить"
                        @click="deleteAccount"
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
                        @click="cancelEditAccount"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div class="modal__body" :class="{ 'modal__body--locked': accountsLoading }">
                    <div v-if="accountsLoading" class="modal__body-overlay">
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
                    <div v-if="accountModalMode === 'edit' && accountGamesLoading" class="loader-wrap">
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
                    <div v-else-if="accountModalMode === 'edit'" class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Логин (без домена)</span>
                        <input v-model.trim="editAccount.login_name" class="input" placeholder="user" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Домен</span>
                        <input
                          v-if="accountEditMode === 'view'"
                          class="input"
                          :value="getDomainLabel(editAccount.domain_code)"
                          readonly
                        />
                        <select v-else v-model="editAccount.domain_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="d in domains" :key="d.name" :value="d.name">
                            {{ d.name }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Регион</span>
                        <input
                          v-if="accountEditMode === 'view'"
                          class="input"
                          :value="getRegionLabel(editAccount.region_code)"
                          readonly
                        />
                        <select v-else v-model="editAccount.region_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="r in regions" :key="r.code" :value="r.code">
                            {{ r.name }} ({{ r.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Статус</span>
                        <input
                          v-if="accountEditMode === 'view'"
                          class="input"
                          :value="getAccountStatusLabel(editAccount.status_code)"
                          readonly
                        />
                        <select v-else v-model="editAccount.status_code" class="input input--select">
                          <option value="active">active</option>
                          <option value="banned">banned</option>
                          <option value="archived">archived</option>
                          <option value="problem">problem</option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Дата</span>
                        <input v-model="editAccount.account_date" class="input" type="date" :max="maxDate" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="editAccount.notes" class="input" placeholder="заметки" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль почта</span>
                        <input v-model.trim="editAccount.email_password" class="input" autocomplete="new-password" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль аккаунт</span>
                        <input v-model.trim="editAccount.account_password" class="input" autocomplete="new-password" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="editAccount.auth_code" class="input" placeholder="код" :readonly="accountEditMode === 'view'" />
                      </label>
                      <label class="field field--full">
                        <span class="label">Резерв</span>
                        <textarea
                          v-model.trim="editAccount.reserve_text"
                          class="input input--textarea"
                          placeholder="mkn4N5 6uGjMm ..."
                          :readonly="accountEditMode === 'view'"
                        />
                      </label>
                      <div class="field field--full">
                        <span class="label">Игры (необязательно)</span>
                        <div v-if="accountEditMode === 'view'" class="pill-list">
                          <span v-for="t in accountGameTitles" :key="t" class="pill">{{ t }}</span>
                          <span v-if="!accountGameTitles.length" class="muted">Пока нет игр.</span>
                        </div>
                        <div v-else>
                          <input v-model.trim="editAccountGameSearchModel" class="input" placeholder="поиск" />
                          <div class="check-list">
                            <label v-for="g in filteredEditAccountGames" :key="g.game_id" class="check-item">
                              <input type="checkbox" :value="g.game_id" v-model="editAccount.game_ids" />
                              <span>{{ g.title }}</span>
                            </label>
                          </div>
                        </div>
                      </div>
                      <div class="field field--full">
                        <span class="label">Слоты аккаунта</span>
                        <p v-if="accountSlotAssignmentsError" class="bad">{{ accountSlotAssignmentsError }}</p>
                        <div v-if="accountSlotAssignmentsLoading" class="loader-wrap loader-wrap--compact">
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
                        <table v-else-if="accountSlotAssignments.length" class="table table--compact table--dense">
                          <thead>
                            <tr>
                              <th>Слот</th>
                              <th>Игра</th>
                              <th>Покупатель</th>
                              <th>Статус</th>
                              <th>Назначено</th>
                              <th>Снято</th>
                              <th>Кем снято</th>
                              <th class="cell--tight"></th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="s in sortedAccountSlotAssignments" :key="s.assignment_id">
                              <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                              <td>{{ s.game_title || '—' }}</td>
                              <td>{{ s.customer_nickname || '—' }}</td>
                              <td>{{ getSlotAssignmentStatus(s) }}</td>
                              <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                              <td>{{ s.released_at ? formatDateTimeMinutes(s.released_at) : '—' }}</td>
                              <td>{{ s.released_by || '—' }}</td>
                              <td class="cell--tight">
                                <button
                                  v-if="!s.released_at"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="accountSlotReleaseLoading"
                                  @click="releaseSlotAssignment(s.assignment_id)"
                                >
                                  Снять
                                </button>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                        <p v-else class="muted">Слотов по аккаунту пока нет.</p>
                      </div>
                      <div class="field field--full">
                        <span class="label">Пользователи по сделкам</span>
                        <p v-if="accountDealsError" class="bad">{{ accountDealsError }}</p>
                        <div v-if="accountDealsLoading" class="loader-wrap loader-wrap--compact">
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
                        <table v-else-if="accountDeals.length" class="table table--compact table--dense">
                          <thead>
                            <tr>
                              <th>Покупатель</th>
                              <th>Игра</th>
                              <th>Тип</th>
                              <th>Статус</th>
                              <th>Дата покупки</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="d in accountDeals" :key="`${d.deal_id}-${d.game_id}`">
                              <td>{{ d.customer_nickname || '—' }}</td>
                              <td>
                                <span :title="getDealGameTitleTooltip(d)">{{ getDealGameTitleDisplay(d) }}</span>
                              </td>
                              <td>{{ d.deal_type || '—' }}</td>
                              <td>{{ d.flow_status || '—' }}</td>
                              <td>{{ formatDate(d.purchase_at || d.created_at) }}</td>
                            </tr>
                          </tbody>
                        </table>
                        <p v-else class="muted">Сделок по аккаунту пока нет.</p>
                      </div>
                      <p v-if="accountsError" class="bad">{{ accountsError }}</p>
                      <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
                      <div v-if="accountEditMode === 'edit'" class="toolbar-actions">
                      </div>
                    </div>
                    <div v-else class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Логин (без домена)</span>
                        <input v-model.trim="newAccount.login_name" class="input" placeholder="user" />
                      </label>
                      <label class="field">
                        <span class="label">Домен</span>
                        <select v-model="newAccount.domain_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="d in domains" :key="d.name" :value="d.name">
                            {{ d.name }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Регион</span>
                        <select v-model="newAccount.region_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="r in regions" :key="r.code" :value="r.code">
                            {{ r.name }} ({{ r.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="newAccount.notes" class="input" placeholder="заметки" />
                      </label>
                      <label class="field">
                        <span class="label">Дата</span>
                        <input v-model="newAccount.account_date" class="input" type="date" :max="maxDate" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль почта</span>
                        <input v-model.trim="newAccount.email_password" class="input" autocomplete="new-password" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль аккаунт</span>
                        <input v-model.trim="newAccount.account_password" class="input" autocomplete="new-password" />
                      </label>
                      <label class="field">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="newAccount.auth_code" class="input" placeholder="код" />
                      </label>
                      <label class="field field--full">
                        <span class="label">Резерв</span>
                        <textarea
                          v-model.trim="newAccount.reserve_text"
                          class="input input--textarea"
                          placeholder="mkn4N5 6uGjMm ..."
                        />
                      </label>
                      <div class="field field--full">
                        <span class="label">Игры (необязательно)</span>
                        <input v-model.trim="accountGameSearchModel" class="input" placeholder="поиск" />
                        <div class="check-list">
                          <label v-for="g in filteredAccountGames" :key="g.game_id" class="check-item">
                            <input type="checkbox" :value="g.game_id" v-model="newAccount.game_ids" />
                            <span>{{ g.title }}</span>
                          </label>
                        </div>
                      </div>
                      <p v-if="accountsError" class="bad">{{ accountsError }}</p>
                      <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps([
  'editAccount',
  'cancelEditAccount',
  'modalRef',
  'modalStyle',
  'startModalDrag',
  'accountModalMode',
  'accountEditMode',
  'setAccountEditMode',
  'updateAccount',
  'accountsLoading',
  'createAccount',
  'deleteAccount',
  'accountGamesLoading',
  'getDomainLabel',
  'domains',
  'getRegionLabel',
  'regions',
  'getAccountStatusLabel',
  'maxDate',
  'accountGameTitles',
  'editAccountGameSearch',
  'filteredEditAccountGames',
  'accountSlotAssignmentsError',
  'accountSlotAssignmentsLoading',
  'accountSlotAssignments',
  'sortedAccountSlotAssignments',
  'getSlotTypeLabel',
  'getSlotAssignmentStatus',
  'formatDateTimeMinutes',
  'accountSlotReleaseLoading',
  'releaseSlotAssignment',
  'accountDealsError',
  'accountDealsLoading',
  'accountDeals',
  'getDealGameTitleTooltip',
  'getDealGameTitleDisplay',
  'formatDate',
  'accountsError',
  'accountsOk',
  'newAccount',
  'accountGameSearch',
  'filteredAccountGames',
  'setEditAccountGameSearch',
  'setAccountGameSearch',
])

const editAccountGameSearchModel = computed({
  get: () => props.editAccountGameSearch,
  set: (value) => props.setEditAccountGameSearch(value),
})

const accountGameSearchModel = computed({
  get: () => props.accountGameSearch,
  set: (value) => props.setAccountGameSearch(value),
})
</script>
