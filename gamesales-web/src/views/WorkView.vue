<template>
  <div class="page">
    <div v-if="globalSaving" class="overlay">
      <div class="loader-wrap">
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
    </div>
    <div class="shell">
      <header class="top">
        <div class="brand">
          <div class="logo">
            <img src="../assets/logo.jpg" alt="Логотип" />
          </div>
          <div>
            <div class="title">Рабочая зона</div>
            <div class="sub">Пользователь: <b>{{ auth.state.user }}</b></div>
          </div>
        </div>

        <div class="actions">
          <nav class="tabs">
            <button class="tab" :class="{ active: activeTab === 'deals' }" @click="activeTab = 'deals'">
              Продажи/Шеринг
            </button>
            <button class="tab" :class="{ active: activeTab === 'accounts' }" @click="activeTab = 'accounts'">
              Аккаунты
            </button>
            <button class="tab" :class="{ active: activeTab === 'games' }" @click="activeTab = 'games'">
              Игры
            </button>
            <button
              v-if="isAdmin"
              class="tab"
              :class="{ active: activeTab === 'catalogs' }"
              @click="activeTab = 'catalogs'"
            >
              Справочники
            </button>
            <button
              v-if="isAdmin"
              class="tab"
              :class="{ active: activeTab === 'users' }"
              @click="activeTab = 'users'"
              style="display:none"
            >
              Пользователи
            </button>
          </nav>
          <div class="tabs tabs--right">
            <button
              class="tab tab--icon"
              :class="{ active: activeTab === 'profile' }"
              @click="activeTab = 'profile'"
              aria-label="Профиль"
              title="Профиль"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
                <path d="M4 20a8 8 0 0 1 16 0" />
              </svg>
            </button>
            <button
              class="tab tab--icon tab--danger"
              @click="onLogout"
              aria-label="Выйти"
              title="Выйти"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <path d="M10 17l5-5-5-5" />
                <path d="M15 12H3" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <section v-if="activeTab === 'dashboard'" class="hero" style="display:none">
        <div>
          <h1 class="hero__title">Операции в реальном времени</h1>
          <p class="hero__text">
            Контролируй слоты, выдачи и платежи, а система сама покажет статус
            API и свежие данные по аккаунтам.
          </p>
        </div>
        <div class="hero__cards">
          <div class="mini">
            <div class="mini__label">API</div>
            <div class="mini__value" :class="{ bad: apiOk === false }">
              <span v-if="apiOk === null">не проверяли</span>
              <span v-else-if="apiOk">OK</span>
              <span v-else>ошибка</span>
            </div>
          </div>
          <div class="mini">
            <div class="mini__label">Запросы</div>
            <div class="mini__value">{{ loading ? '...' : '200/мин' }}</div>
          </div>
        </div>
      </section>

      <main class="main">
        <section v-if="activeTab === 'dashboard'" class="panel panel--wide" style="display:none">
          <div class="panel__body">
            <div class="status">
              <div class="dot" :class="{ ok: apiOk, bad: apiOk === false }"></div>
              <span>
                <span v-if="apiOk === null">не проверяли</span>
                <span v-else-if="apiOk">OK</span>
                <span v-else>ошибка</span>
              </span>
            </div>
            <button class="btn" @click="checkApi" :disabled="loading">
              {{ loading ? 'Проверяем…' : 'Проверить API' }}
            </button>
          </div>
        </section>

        <section v-if="activeTab === 'profile'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Профиль</h2>
              <p class="muted">Сменить пароль текущего пользователя.</p>
            </div>
            <div class="toolbar-actions">
              <button
                v-if="isAdmin"
                class="btn btn--icon btn--glow btn--glow-add"
                title="Пользователи"
                aria-label="Пользователи"
                @click="activeTab = 'users'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
                  <path d="M8 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Z" />
                  <path d="M2 20a6 6 0 0 1 12 0" />
                  <path d="M14 20a5 5 0 0 1 8 0" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-eye"
                title="Сменить пароль"
                aria-label="Сменить пароль"
                @click="openPwdModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M7 10a5 5 0 0 1 10 0v4a5 5 0 0 1-10 0v-4Z" />
                  <path d="M9 10V8a3 3 0 0 1 6 0v2" />
                </svg>
              </button>
            </div>
          </div>
          <div class="panel__body">
            <p class="muted">Нажмите иконку, чтобы открыть форму смены пароля.</p>
            <teleport to="body">
              <div v-if="showPwdForm" class="modal-backdrop" @click.self="closePwdModal">
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>Смена пароля</h3>
                    <button
                      class="btn btn--icon-plain"
                      type="button"
                      aria-label="Закрыть"
                      title="Закрыть"
                      @click="closePwdModal"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6l-12 12" />
                      </svg>
                    </button>
                  </div>
                  <div class="modal__body">
                    <div class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Текущий пароль</span>
                        <input v-model="pwdForm.current" class="input" type="password" />
                      </label>
                      <label class="field">
                        <span class="label">Новый пароль</span>
                        <input v-model="pwdForm.next" class="input" type="password" />
                      </label>
                      <label class="field">
                        <span class="label">Повторите пароль</span>
                        <input v-model="pwdForm.next2" class="input" type="password" />
                      </label>
                      <p v-if="pwdError" class="bad">{{ pwdError }}</p>
                      <p v-if="pwdOk" class="ok">Пароль обновлён</p>
                      <div class="toolbar-actions import-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="changePassword"
                          :disabled="pwdLoading"
                          aria-label="Сохранить"
                          title="Сохранить"
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
          </div>
        </section>

        <section v-if="activeTab === 'accounts'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <div class="toolbar-actions">
                <label class="field field--compact">
                  <input
                    v-model.trim="accountFilters.search_q"
                    class="input input--compact"
                    placeholder="почта, домен, регион, игра"
                    @keydown.enter.prevent="applyAccountSearch"
                  />
                </label>
                <button
                  class="btn btn--icon btn--glow btn--glow-filter"
                  type="button"
                  @click="applyAccountSearch"
                  aria-label="Найти"
                  title="Найти"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 21l-4.2-4.2" />
                    <circle cx="11" cy="11" r="7" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="toolbar-actions">
              <button
                class="btn btn--icon btn--glow btn--glow-add"
                aria-label="Добавить аккаунт"
                title="Добавить аккаунт"
                @click="openCreateAccountModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-refresh"
                aria-label="Обновить список"
                title="Обновить список"
                @click="loadAccounts"
                :disabled="accountsLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <div class="panel__body">
            <div v-if="accountsLoading" class="loader-wrap loader-overlay">
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

            <div v-else-if="activeAccountChips.length" class="chip-row">
              <button class="chip chip--reset" type="button" @click="resetAccountFilter('all')">
                Сбросить все
              </button>
              <span v-for="chip in activeAccountChips" :key="chip.key" class="chip">
                <span class="chip__label">{{ chip.label }}:</span>
                <span class="chip__value">{{ chip.value }}</span>
                <button
                  class="chip__clear"
                  type="button"
                  aria-label="Сбросить фильтр"
                  title="Сбросить фильтр"
                  @click="resetAccountFilter(chip.key)"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 6l12 12M18 6l-12 12" />
                  </svg>
                </button>
              </span>
            </div>

            <table v-if="sortedAccounts.length" class="table table--compact">
              <thead>
                <tr>
                  <th class="sortable cell--account" @click="toggleAccountSort('login')">
                    <span class="th-title th-title--filter">
                      Почта
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.login_q) }"
                        type="button"
                        aria-label="Фильтр по почте"
                        title="Фильтр по почте"
                        @click.stop="openAccountFilter('login')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'login'" class="filter-pop filter-pop--left" @click.stop>
                      <label class="field">
                        <span class="label">Почта</span>
                        <input v-model.trim="accountFilterDraft.login" class="input" placeholder="почта" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('login')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('login')">Сбросить</button>
                    </div>
                  </th>
                  <th>
                    <span class="th-title th-title--filter">
                      Игры
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.game_q) }"
                        type="button"
                        aria-label="Фильтр по играм"
                        title="Фильтр по играм"
                        @click.stop="openAccountFilter('game')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'game'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Игра</span>
                        <input v-model.trim="accountFilterDraft.game" class="input" placeholder="название игры" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('game')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('game')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleAccountSort('slots')">
                    <span class="th-title th-title--filter">
                      Слоты
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.slots_q) }"
                        type="button"
                        aria-label="Фильтр по слотам"
                        title="Фильтр по слотам"
                        @click.stop="openAccountFilter('slots')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'slots'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Слоты</span>
                        <input v-model.trim="accountFilterDraft.slots" class="input" placeholder="например play_ps4 1/1" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('slots')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('slots')">Сбросить</button>
                    </div>
                  </th>
                  <th>Резерв</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in sortedAccounts" :key="a.account_id" class="clickable-row" @click="startEditAccount(a)">
                  <td class="cell--account">{{ a.login_full || '—' }}</td>
                  <td>{{ formatAccountGamesLine(a) }}</td>
                  <td class="cell--slots">
                    <span v-if="!getAccountSlotStatusList(a).length" class="slot-line">—</span>
                    <span v-for="s in getAccountSlotStatusList(a)" :key="s.slot_type_code" class="slot-line">
                      {{ formatAccountSlotStatusLine(s) }}
                    </span>
                  </td>
                  <td class="cell--selectable" @click.stop>{{ formatSecret(getReserveSecrets(a.account_id)) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет аккаунтов.</p>
            <div v-if="accountsTotal > 0" class="pager">
              <span class="muted">Всего: {{ accountsTotal }}</span>
              <label class="pager__size">
                <span class="muted">Показывать</span>
                <select v-model.number="accountsPageSize" class="input input--select input--compact">
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
              </label>
              <button class="ghost" @click="setAccountsPage(1)" :disabled="accountsPage <= 1">
                «
              </button>
              <button class="ghost" @click="prevAccountsPage" :disabled="accountsPage <= 1">
                ← Назад
              </button>
              <label class="pager__jump">
                <span class="muted">Стр.</span>
                <input
                  v-model.number="accountsPageInput"
                  class="input input--compact input--page"
                  type="number"
                  min="1"
                  :max="accountsTotalPages"
                  @keydown.enter.prevent="jumpAccountsPage"
                  @blur="jumpAccountsPage"
                />
              </label>
              <span class="muted">из {{ accountsTotalPages }}</span>
              <button class="ghost" @click="nextAccountsPage" :disabled="accountsPage >= accountsTotalPages">
                Вперёд →
              </button>
              <button class="ghost" @click="setAccountsPage(accountsTotalPages)" :disabled="accountsPage >= accountsTotalPages">
                »
              </button>
            </div>

            <div class="divider"></div>

            <teleport to="body">
              <div v-if="editAccount.open" class="modal-backdrop" @click.self="cancelEditAccount">
                <div ref="modalRef" class="modal" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>{{ accountModalMode === 'create' ? 'Новый аккаунт' : 'Аккаунт' }}</h3>
                    <div class="toolbar-actions">
                      <button
                        v-if="accountModalMode === 'edit'"
                        class="btn btn--icon-plain"
                        type="button"
                        aria-label="Редактировать"
                        title="Редактировать"
                        @click="accountEditMode = 'edit'"
                        :disabled="accountEditMode === 'edit'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                          <path d="M13 6l4 4" />
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
                  <div class="modal__body">
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
                        <input v-model.trim="editAccount.login_name" class="input" placeholder="user" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Домен</span>
                        <select v-model="editAccount.domain_code" class="input input--select" :disabled="accountEditMode === 'view'">
                          <option value="">— не выбрано —</option>
                          <option v-for="d in domains" :key="d.name" :value="d.name">
                            {{ d.name }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Регион</span>
                        <select v-model="editAccount.region_code" class="input input--select" :disabled="accountEditMode === 'view'">
                          <option value="">— не выбрано —</option>
                          <option v-for="r in regions" :key="r.code" :value="r.code">
                            {{ r.name }} ({{ r.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Статус</span>
                        <select v-model="editAccount.status_code" class="input input--select" :disabled="accountEditMode === 'view'">
                          <option value="active">active</option>
                          <option value="banned">banned</option>
                          <option value="archived">archived</option>
                          <option value="problem">problem</option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Дата</span>
                        <input v-model="editAccount.account_date" class="input" type="date" :max="maxDate" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="editAccount.notes" class="input" placeholder="заметки" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль почта</span>
                        <input v-model.trim="editAccount.email_password" class="input" autocomplete="new-password" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль аккаунт</span>
                        <input v-model.trim="editAccount.account_password" class="input" autocomplete="new-password" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="editAccount.auth_code" class="input" placeholder="код" :disabled="accountEditMode === 'view'" />
                      </label>
                      <label class="field field--full">
                        <span class="label">Резерв</span>
                        <textarea
                          v-model.trim="editAccount.reserve_text"
                          class="input input--textarea"
                          placeholder="mkn4N5 jYVLY8 6uGjMm ..."
                          :disabled="accountEditMode === 'view'"
                        />
                      </label>
                      <div class="field field--full">
                        <span class="label">Игры (необязательно)</span>
                        <div v-if="accountEditMode === 'view'" class="pill-list">
                          <span v-for="t in accountGameTitles" :key="t" class="pill">{{ t }}</span>
                          <span v-if="!accountGameTitles.length" class="muted">Пока нет игр.</span>
                        </div>
                        <div v-else>
                          <input v-model.trim="editAccountGameSearch" class="input" placeholder="поиск" />
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
                              <th>Пользователь</th>
                              <th>Статус</th>
                              <th>Назначено</th>
                              <th>Снято</th>
                              <th>Кем снято</th>
                              <th class="cell--tight"></th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="s in accountSlotAssignments" :key="s.assignment_id">
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
                              <th>Пользователь</th>
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
                        <button
                          class="btn btn--icon-plain"
                          @click="updateAccount"
                          :disabled="accountsLoading"
                          aria-label="Сохранить изменения"
                          title="Сохранить изменения"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
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
                          placeholder="mkn4N5 jYVLY8 6uGjMm ..."
                        />
                      </label>
                      <div class="field field--full">
                        <span class="label">Игры (необязательно)</span>
                        <input v-model.trim="accountGameSearch" class="input" placeholder="поиск" />
                        <div class="check-list">
                          <label v-for="g in filteredAccountGames" :key="g.game_id" class="check-item">
                            <input type="checkbox" :value="g.game_id" v-model="newAccount.game_ids" />
                            <span>{{ g.title }}</span>
                          </label>
                        </div>
                      </div>
                      <p v-if="accountsError" class="bad">{{ accountsError }}</p>
                      <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
                      <div class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="createAccount"
                          :disabled="accountsLoading"
                          aria-label="Создать аккаунт"
                          title="Создать аккаунт"
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
          </div>
        </section>

        <section v-if="activeTab === 'games'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <div class="toolbar-actions">
                <label class="field field--compact">
                  <input
                    v-model.trim="gameFilters.q"
                    class="input input--compact"
                    placeholder="название игры"
                    @keydown.enter.prevent="applyGameSearch"
                  />
                </label>
                <button class="btn btn--icon btn--glow btn--glow-filter" type="button" @click="applyGameSearch" aria-label="Найти" title="Найти">
                  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 21l-4.2-4.2" />
                    <circle cx="11" cy="11" r="7" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="toolbar-actions">
              <button
                class="btn btn--icon btn--glow btn--glow-add"
                title="Добавить игру"
                aria-label="Добавить игру"
                @click="openCreateGameModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-import"
                title="Импорт игр"
                aria-label="Импорт игр"
                @click="openGameImport"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3v12" />
                  <path d="M7 10l5 5 5-5" />
                  <path d="M5 21h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-export"
                title="Выгрузить игры"
                aria-label="Выгрузить игры"
                @click="downloadGamesExport"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 21V9" />
                  <path d="M7 14l5-5 5 5" />
                  <path d="M5 3h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-refresh"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadGames"
                :disabled="gamesLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <div class="panel__body">
            <div v-if="gamesLoading" class="loader-wrap loader-overlay">
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
            <div v-else-if="activeGameChips.length" class="chip-row">
              <button class="chip chip--reset" type="button" @click="resetGameFilter('all')">
                Сбросить все
              </button>
              <span v-for="chip in activeGameChips" :key="chip.key" class="chip">
                <span class="chip__label">{{ chip.label }}:</span>
                <span class="chip__value">{{ chip.value }}</span>
                <button
                  class="chip__clear"
                  type="button"
                  aria-label="Сбросить фильтр"
                  title="Сбросить фильтр"
                  @click="resetGameFilter(chip.key)"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 6l12 12M18 6l-12 12" />
                  </svg>
                </button>
              </span>
            </div>
            <teleport to="body">
              <div
                v-if="showGameImport"
                class="modal-backdrop"
                @click.self="closeGameImport"
              >
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>Импорт игр из файла</h3>
                    <button
                      class="btn btn--icon-plain"
                      type="button"
                      aria-label="Закрыть"
                      title="Закрыть"
                      @click="closeGameImport"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6l-12 12" />
                      </svg>
                    </button>
                  </div>
                  <div class="modal__body">
                    <div class="toolbar-actions import-actions import-actions--fixed">
                      <button class="ghost" type="button" @click="downloadGameTemplate">
                        Шаблон
                      </button>
                      <button class="ghost" type="button" @click="validateGameImport" :disabled="!gameImportFile || gameImportLoading">
                        <span v-if="gameImportLoading && gameImportAction === 'validate'" class="spinner spinner--small"></span>
                        Проверка
                      </button>
                      <button
                        class="ghost"
                        type="button"
                        @click="uploadGameImport"
                        :disabled="!gameImportValidated || !gameImportFile || gameImportLoading"
                        title="Загрузить"
                        aria-label="Загрузить"
                      >
                        <span v-if="gameImportLoading && gameImportAction === 'upload'" class="spinner spinner--small"></span>
                        Загрузить
                      </button>
                      <button
                        v-if="gameImportLoading && gameImportJobId"
                        class="ghost"
                        type="button"
                        @click="cancelGameImport"
                        title="Отменить импорт"
                        aria-label="Отменить импорт"
                      >
                        Отмена
                      </button>
                      <button v-if="gameImportLoading" class="import-status" type="button" @click="scrollToImportDetails">
                        <span v-if="gameImportAction === 'validate'">Проверка…</span>
                        <span v-else-if="gameImportAction === 'cancel'">Отмена…</span>
                        <span v-else-if="gameImportAction === 'upload' && gameImportProgress.total">Загрузка: {{ gameImportProgress.current }} из {{ gameImportProgress.total }}</span>
                        <span v-else-if="gameImportAction === 'upload'">Загрузка…</span>
                      </button>
                    </div>
                    <div class="form form--stack form--compact">
                      <label class="field field--full">
                        <span class="label">Файл (xlsx/xls)</span>
                        <input
                          class="input input--file"
                          type="file"
                          accept=".xlsx,.xls"
                          @change="onGameImportFile"
                          :disabled="gameImportLoading"
                        />
                      </label>
                      <div ref="importDetailsRef">
                        <p v-if="gameImportMessage" class="ok">{{ gameImportMessage }}</p>
                      <p v-if="gameImportStats" class="muted">
                        Итог: создано {{ gameImportStats.created }}, обновлено {{ gameImportStats.updated }}, пропущено {{ gameImportStats.skipped }}, ошибок {{ gameImportStats.failed }}, всего {{ gameImportStats.total }}
                      </p>
                      <div v-if="gameImportWarnings.length" class="import-errors">
                        <p class="muted">Предупреждения: {{ gameImportWarnings.length }}</p>
                        <table class="table table--compact table--dense">
                          <thead>
                            <tr>
                              <th>Строка</th>
                              <th>Поле</th>
                              <th>Предупреждение</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(e, idx) in gameImportWarnings" :key="`w-${idx}`">
                              <td>{{ e.row }}</td>
                              <td>{{ e.field }}</td>
                              <td>{{ e.message }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <div v-if="gameImportErrors.length" class="import-errors">
                        <p class="bad">Ошибки: {{ gameImportErrors.length }}</p>
                        <table class="table table--compact table--dense">
                          <thead>
                            <tr>
                              <th>Строка</th>
                              <th>Поле</th>
                              <th>Ошибка</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(e, idx) in gameImportErrors" :key="idx">
                              <td>{{ e.row }}</td>
                              <td>{{ e.field }}</td>
                              <td>{{ e.message }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </teleport>

            <table v-if="sortedGames.length" class="table table--compact">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleGamesSort('title')">
                    <span class="th-title th-title--filter">
                      Игра
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(gameFilters.q) }"
                        type="button"
                        aria-label="Фильтр по игре"
                        title="Фильтр по игре"
                        @click.stop="openGameFilter('title')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeGameFilter === 'title'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Игра</span>
                        <input v-model.trim="gameFilterDraft.title" class="input" placeholder="игра" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyGameFilter('title')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetGameFilter('title')">Сбросить</button>
                    </div>
                  </th>
                  <th>Короткое</th>
                  <th class="sortable" @click="toggleGamesSort('platform')">
                    <span class="th-title th-title--filter">
                      Платформа
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(gameFilters.platform_code) }"
                        type="button"
                        aria-label="Фильтр по платформе"
                        title="Фильтр по платформе"
                        @click.stop="openGameFilter('platform')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeGameFilter === 'platform'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Платформа</span>
                        <input v-model.trim="gameFilterDraft.platform" class="input" placeholder="платформа" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyGameFilter('platform')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetGameFilter('platform')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleGamesSort('region')">
                    <span class="th-title th-title--filter">
                      Регион
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(gameFilters.region_code) }"
                        type="button"
                        aria-label="Фильтр по региону"
                        title="Фильтр по региону"
                        @click.stop="openGameFilter('region')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeGameFilter === 'region'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">Регион</span>
                        <input v-model.trim="gameFilterDraft.region" class="input" placeholder="регион" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyGameFilter('region')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetGameFilter('region')">Сбросить</button>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in pagedGames" :key="g.game_id" class="clickable-row" @click="openGameAccounts(g)">
                  <td>{{ g.title }}</td>
                  <td>{{ g.short_title || '—' }}</td>
                  <td>{{ formatGamePlatforms(g.platform_codes) }}</td>
                  <td>{{ g.region_code || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет игр.</p>

            <div v-if="gamesTotal > 0" class="pager">
              <span class="muted">Всего: {{ gamesTotal }}</span>
              <label class="pager__size">
                <span class="label">Показывать</span>
                <select v-model.number="gamesPageSize" class="input input--select input--compact">
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
              </label>
              <button class="ghost" @click="setGamesPage(1)" :disabled="gamesPage <= 1">
                «
              </button>
              <button class="ghost" @click="prevGamesPage" :disabled="gamesPage <= 1">
                ← Назад
              </button>
              <label class="pager__jump">
                <span class="muted">Стр.</span>
                <input
                  v-model.number="gamesPageInput"
                  class="input input--compact input--page"
                  type="number"
                  min="1"
                  :max="gamesTotalPages"
                  @keydown.enter.prevent="jumpGamesPage"
                  @blur="jumpGamesPage"
                />
              </label>
              <span class="muted">из {{ gamesTotalPages }}</span>
              <button class="ghost" @click="nextGamesPage" :disabled="gamesPage >= gamesTotalPages">
                Вперёд →
              </button>
              <button class="ghost" @click="setGamesPage(gamesTotalPages)" :disabled="gamesPage >= gamesTotalPages">
                »
              </button>
            </div>

            <div class="divider"></div>

            <teleport to="body">
              <div
                v-if="editGame.open || showGameForm"
                class="modal-backdrop"
                @click.self="closeGameModal"
              >
                <div
                  ref="modalRef"
                  :class="['modal', editGame.open ? 'modal--full' : 'modal--auto']"
                  :style="modalStyle"
                >
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>{{ editGame.open ? (editGame.title ? `Игра ${editGame.title}` : 'Игра') : 'Новая игра' }}</h3>
                    <div class="toolbar-actions">
                      <button
                        v-if="editGame.open"
                        class="btn btn--icon-plain"
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
                  <div class="modal__body">
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
                              class="ghost ghost--small"
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
                        <input v-model.trim="editGame.title" class="input" placeholder="Например, GTA V" :disabled="gameEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Короткое название</span>
                        <input v-model.trim="editGame.short_title" class="input" placeholder="Например, GTA V" :disabled="gameEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Ссылка</span>
                        <input v-model.trim="editGame.link" class="input" placeholder="https://..." :disabled="gameEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Язык текста</span>
                        <input v-model.trim="editGame.text_lang" class="input" placeholder="RU/EN/..." :disabled="gameEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Язык озвучки</span>
                        <input v-model.trim="editGame.audio_lang" class="input" placeholder="RU/EN/..." :disabled="gameEditMode === 'view'" />
                      </label>
                      <label class="field">
                        <span class="label">Поддержка VR</span>
                        <input v-model.trim="editGame.vr_support" class="input" placeholder="например: есть/нет" :disabled="gameEditMode === 'view'" />
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
                        <select v-model="editGame.region_code" class="input input--select" :disabled="gameEditMode === 'view'">
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
                              <th>Пользователь</th>
                              <th>Статус</th>
                              <th>Назначено</th>
                              <th>Снято</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="s in gameSlotAssignments" :key="s.assignment_id">
                              <td>{{ s.account_id || '—' }}</td>
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
                      <div v-if="gameEditMode === 'edit'" class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="updateGame"
                          :disabled="gameLoading"
                          aria-label="Сохранить изменения"
                          title="Сохранить изменения"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                      </div>
                    </div>
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
                      <div class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="createGame"
                          :disabled="gameLoading"
                          aria-label="Добавить игру"
                          title="Добавить игру"
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
          </div>
        </section>

        <section v-if="activeTab === 'deals'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <div class="toolbar-actions">
                <label class="field field--compact">
                  <input
                    v-model.trim="dealFilters.search_q"
                    class="input input--compact"
                    placeholder="пользователь, регион, дата, статус, тип"
                    @keydown.enter.prevent="applyDealSearch"
                  />
                </label>
                <button class="btn btn--icon btn--glow btn--glow-filter" type="button" @click="applyDealSearch" aria-label="Найти" title="Найти">
                  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 21l-4.2-4.2" />
                    <circle cx="11" cy="11" r="7" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="toolbar-actions">
              <div class="switch-wrap">
                <label class="switch">
                  <input v-model="dealShowCompleted" type="checkbox" @change="loadDeals(1)" />
                  <div class="slider">
                    <div class="circle">
                      <svg class="cross" viewBox="0 0 365.696 365.696" aria-hidden="true">
                        <path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path>
                      </svg>
                      <svg class="checkmark" viewBox="0 0 24 24" aria-hidden="true">
                        <path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path>
                      </svg>
                    </div>
                  </div>
                </label>
                <span class="switch-label">Показать завершенные</span>
              </div>
              <button
                class="btn btn--icon btn--glow btn--glow-add"
                title="Добавить продажу"
                aria-label="Добавить продажу"
                @click="openCreateDealModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-refresh"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadDeals(1)"
                :disabled="dealListLoading"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>
            </div>
          </div>
          <div class="panel__body">
            <p v-if="dealListError" class="bad">{{ dealListError }}</p>
            <div v-else-if="dealListLoading" class="loader-wrap loader-overlay">
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
            <div v-else-if="activeDealChips.length" class="chip-row">
              <button class="chip chip--reset" type="button" @click="resetDealFilter('all')">
                Сбросить все
              </button>
              <span v-for="chip in activeDealChips" :key="chip.key" class="chip">
                <span class="chip__label">{{ chip.label }}:</span>
                <span class="chip__value">{{ chip.value }}</span>
                <button
                  class="chip__clear"
                  type="button"
                  aria-label="Сбросить фильтр"
                  title="Сбросить фильтр"
                  @click="resetDealFilter(chip.key)"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 6l12 12M18 6l-12 12" />
                  </svg>
                </button>
              </span>
            </div>
            <table v-if="sortedDeals.length" class="table">
              <thead>
                <tr>
                  <th class="sortable cell--tight" @click="toggleDealSort('type')">
                    <span class="th-title th-title--filter">
                      Тип
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.type_q) }"
                        type="button"
                        aria-label="Фильтр по типу"
                        title="Фильтр по типу"
                        @click.stop="activeDealFilter = activeDealFilter === 'type' ? '' : 'type'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'type'" class="filter-pop filter-pop--left" @click.stop>
                      <label class="field">
                        <span class="label">Тип</span>
                        <select v-model="dealFilters.type_q" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="t in dealTypeOptions" :key="t.code" :value="t.code">
                            {{ t.name }}
                          </option>
                        </select>
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('type')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleDealSort('customer')">
                    <span class="th-title th-title--filter">
                      Пользователь
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.customer_q) }"
                        type="button"
                        aria-label="Фильтр по пользователю"
                        title="Фильтр по пользователю"
                        @click.stop="activeDealFilter = activeDealFilter === 'customer' ? '' : 'customer'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'customer'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Пользователь</span>
                        <input
                          v-model.trim="dealFilters.customer_q"
                          class="input"
                          placeholder="пользователь"
                          @keydown.enter.prevent="loadDeals(1); activeDealFilter = ''"
                        />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('customer')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable cell--tight" @click="toggleDealSort('region')">
                    <span class="th-title th-title--filter">
                      Регион
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.region_q) }"
                        type="button"
                        aria-label="Фильтр по региону"
                        title="Фильтр по региону"
                        @click.stop="activeDealFilter = activeDealFilter === 'region' ? '' : 'region'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'region'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Регион</span>
                        <select v-model="dealFilters.region_q" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="r in regions" :key="r.code" :value="r.code">
                            {{ r.name }} ({{ r.code }})
                          </option>
                        </select>
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('region')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleDealSort('date')">
                    <span class="th-title th-title--filter">
                      Дата/время
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.purchase_from || dealFilters.purchase_to) }"
                        type="button"
                        aria-label="Фильтр по дате"
                        title="Фильтр по дате"
                        @click.stop="activeDealFilter = activeDealFilter === 'date' ? '' : 'date'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'date'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">С</span>
                        <input
                          v-model="dealFilters.purchase_from"
                          class="input"
                          type="date"
                          :min="minDate"
                          :max="maxDate"
                          @keydown.enter.prevent="validateDealRange('date') && (loadDeals(1), activeDealFilter = '')"
                        />
                      </label>
                      <label class="field">
                        <span class="label">По</span>
                        <input
                          v-model="dealFilters.purchase_to"
                          class="input"
                          type="date"
                          :min="minDate"
                          :max="maxDate"
                          @keydown.enter.prevent="validateDealRange('date') && (loadDeals(1), activeDealFilter = '')"
                        />
                      </label>
                      <p v-if="dealFilterErrors.date" class="bad">{{ dealFilterErrors.date }}</p>
                      <button
                        class="ghost ghost--small"
                        type="button"
                        @click="validateDealRange('date') && (loadDeals(1), activeDealFilter = '')"
                      >
                        Применить
                      </button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('date')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable cell--tight" @click="toggleDealSort('status')">
                    <span class="th-title th-title--filter">
                      Статус
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.status_q) }"
                        type="button"
                        aria-label="Фильтр по статусу"
                        title="Фильтр по статусу"
                        @click.stop="activeDealFilter = activeDealFilter === 'status' ? '' : 'status'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'status'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">Статус</span>
                        <select v-model="dealFilters.status_q" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="s in dealFlowStatusOptions" :key="s.code" :value="s.code">
                            {{ s.name }}
                          </option>
                        </select>
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('status')">Сбросить</button>
                    </div>
                  </th>
                  <th v-if="!dealShowCompleted" class="cell--tight">Действие</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="d in sortedDeals"
                  :key="d.deal_id"
                  class="clickable-row"
                  :class="{ 'row-active': editDeal.open && editDeal.deal_id === d.deal_id }"
                  @click="startEditDeal(d)"
                >
                  <td class="cell--tight">{{ d.deal_type || '—' }}</td>
                  <td>{{ d.customer_nickname || '—' }}</td>
                  <td class="cell--tight">{{ d.region_code || '—' }}</td>
                  <td>{{ formatDateTimeMinutes(d.purchase_at || d.created_at) }}</td>
                  <td class="cell--tight">{{ d.flow_status || '—' }}</td>
                  <td v-if="!dealShowCompleted" class="cell--tight">
                    <button class="mini-btn" type="button" @click.stop="markDealCompleted(d)" :disabled="dealSaving">
                      Завершить
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет сделок.</p>

            <div v-if="dealTotal > 0" class="pager">
              <span class="muted">Всего: {{ dealTotal }}</span>
              <label class="pager__size">
                <span class="muted">Показывать</span>
                <select v-model.number="dealPageSize" class="input input--select input--compact">
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
              </label>
              <button class="ghost" @click="setDealPage(1)" :disabled="dealPage <= 1 || dealListLoading">
                «
              </button>
              <button class="ghost" @click="prevDealPage" :disabled="dealPage <= 1 || dealListLoading">
                ← Назад
              </button>
              <label class="pager__jump">
                <span class="muted">Стр.</span>
                <input
                  v-model.number="dealPageInput"
                  class="input input--compact input--page"
                  type="number"
                  min="1"
                  :max="totalPages"
                  @keydown.enter.prevent="jumpDealPage"
                  @blur="jumpDealPage"
                />
              </label>
              <span class="muted">из {{ totalPages }}</span>
              <button
                class="ghost"
                @click="nextDealPage"
                :disabled="dealPage >= totalPages || dealListLoading"
              >
                Вперёд →
              </button>
              <button class="ghost" @click="setDealPage(totalPages)" :disabled="dealPage >= totalPages || dealListLoading">
                »
              </button>
            </div>

            <div class="divider"></div>
            <teleport to="body">
              <div
                v-if="editDeal.open || showDealForm"
                class="modal-backdrop"
                @click.self="closeDealModal"
              >
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>{{ dealModalTitle }}</h3>
                    <div class="toolbar-actions">
                      <button
                        v-if="editDeal.open && dealEditMode === 'edit'"
                        class="btn btn--icon-plain btn--icon-round"
                        type="button"
                        aria-label="Сохранить изменения"
                        title="Сохранить изменения"
                        @click="updateDeal"
                        :disabled="dealLoading"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h12l4 4v10H4V6Z" />
                          <path d="M8 6v4h6V6" />
                          <path d="M8 18v-4h8v4" />
                        </svg>
                      </button>
                      <button
                        v-if="!editDeal.open"
                        class="btn btn--icon-plain btn--icon-round"
                        type="button"
                        aria-label="Сохранить сделку"
                        title="Сохранить сделку"
                        @click="createDeal"
                        :disabled="dealLoading"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h12l4 4v10H4V6Z" />
                          <path d="M8 6v4h6V6" />
                          <path d="M8 18v-4h8v4" />
                        </svg>
                      </button>
                      <button
                        v-if="editDeal.open"
                        class="btn btn--icon-plain btn--icon-round"
                        type="button"
                        aria-label="Редактировать"
                        title="Редактировать"
                        @click="dealEditMode = 'edit'"
                        :disabled="dealEditMode === 'edit'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                          <path d="M13 6l4 4" />
                        </svg>
                      </button>
                      <button
                        class="btn btn--icon-plain btn--icon-round"
                        type="button"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="closeDealModal"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div class="modal__body" :class="{ 'modal__body--locked': dealQuickAccountBusy || dealQuickGameBusy }">
                    <div v-if="dealQuickAccountBusy || dealQuickGameBusy" class="modal__body-overlay">
                      <div class="modal__body-overlay-content">
                        <span class="spinner"></span>
                        <span class="muted">{{ dealQuickAccountBusy ? 'Создаем аккаунт…' : 'Создаем игру…' }}</span>
                      </div>
                    </div>
                    <div v-if="editDeal.open" class="form deal-form">
                      <div class="deal-form__col deal-form__col--left">
                        <label class="field">
                          <span class="label">Тип</span>
                          <select v-model="editDeal.deal_type_code" class="input input--select" :disabled="dealEditMode === 'view'">
                            <option value="sale">Продажа</option>
                            <option value="rental">Шеринг</option>
                          </select>
                        </label>
                        <label v-if="editDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Тип слота</span>
                          <select
                            v-model="editDeal.slot_type_code"
                            class="input input--select"
                            :disabled="dealEditMode === 'view' || !editDeal.game_id"
                          >
                            <option value="">— не выбрано —</option>
                            <option
                              v-for="st in getDealSlotTypeOptions('edit')"
                              :key="st.code"
                              :value="st.code"
                              :disabled="!st.supported"
                            >
                              {{ getDealSlotTypeLabel(st) }}
                            </option>
                          </select>
                          <span v-if="!editDeal.game_id" class="muted muted--small">Сначала выберите игру</span>
                        </label>
                        <label v-if="editDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Аккаунт</span>
                          <select
                            v-model.number="editDeal.account_id"
                            class="input input--select"
                            :disabled="dealEditMode === 'view' || !editDeal.game_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit')"
                          >
                            <option value="">— не выбрано —</option>
                            <option v-for="a in dealAccountsForEdit" :key="a.account_id" :value="a.account_id">
                              {{ a.login_full || a.account_id }}
                            </option>
                          </select>
                          <span v-if="!editDeal.game_id" class="muted muted--small">Сначала выберите игру</span>
                          <span v-else-if="!editDeal.slot_type_code" class="muted muted--small">Сначала выберите слот</span>
                          <div
                            v-if="dealEditMode !== 'view' && editDeal.game_id && editDeal.slot_type_code && !editDeal.account_id && !isDealSlotTypeUnsupported('edit') && !hasFreeDealSlots('edit')"
                            class="quick-create"
                          >
                            <div class="quick-create__title">
                              {{ hasAnyGameAssignmentsEdit ? 'Нет свободных слотов — можно снять занятый' : 'Нет аккаунтов с игрой' }}
                            </div>
                            <div v-if="hasAnyGameAssignmentsEdit && dealGameAssignmentsLoadingEdit" class="loader-wrap loader-wrap--compact">
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
                            <table v-else-if="hasAnyGameAssignmentsEdit && dealGameAssignmentsForSelectedSlotEdit.length" class="table table--compact table--dense">
                              <thead>
                                <tr>
                                  <th>Аккаунт</th>
                                  <th>Слот</th>
                                  <th>Пользователь</th>
                                  <th class="cell--tight"></th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr v-for="s in dealGameAssignmentsForSelectedSlotEdit" :key="s.assignment_id">
                                  <td>{{ getAccountLabelById(s.account_id) }}</td>
                                  <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                  <td>{{ s.customer_nickname || '—' }}</td>
                                  <td class="cell--tight">
                                    <button
                                      v-if="!s.released_at"
                                      class="ghost ghost--small"
                                      type="button"
                                      :disabled="accountSlotReleaseLoading"
                                      @click="releaseSlotFromDeal(s, 'edit')"
                                    >
                                      Снять
                                    </button>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                            <p v-else-if="hasAnyGameAssignmentsEdit" class="muted">Нет активных слотов по игре.</p>
                            <div class="quick-create__title">Быстро создать аккаунт</div>
                            <input v-model.trim="quickEditAccount.login_name" class="input input--compact" placeholder="Логин" />
                            <select v-model="quickEditAccount.domain_code" class="input input--select input--compact">
                              <option value="">— домен —</option>
                              <option v-for="d in domains" :key="`qe-d-${d.code}`" :value="d.code">
                                {{ d.name }} ({{ d.code }})
                              </option>
                            </select>
                            <div class="check-list check-list--compact">
                              <label v-for="p in platforms" :key="`qe-p-${p.code}`" class="check-item">
                                <input type="checkbox" :value="p.code" v-model="quickEditAccount.platform_codes" />
                                <span>{{ p.name }} ({{ p.code }})</span>
                              </label>
                            </div>
                            <div class="quick-create__actions">
                              <button
                                class="ghost ghost--small"
                                type="button"
                                :disabled="quickEditAccountLoading"
                                @click="createQuickAccount('edit')"
                              >
                                <span v-if="quickEditAccountLoading" class="spinner spinner--small"></span>
                                Создать
                              </button>
                              <span v-if="quickEditAccountError" class="bad">{{ quickEditAccountError }}</span>
                            </div>
                          </div>
                        </label>
                        <div v-if="editDeal.deal_type_code === 'rental' && editDeal.account_id && accountSlotStatusEdit.length" class="slot-status">
                          <div class="slot-status__title">Слоты</div>
                          <div class="slot-status__list">
                            <div v-for="s in getSortedSlotStatus(accountSlotStatusEdit)" :key="s.slot_type_code" class="slot-status__row">
                              <span class="slot-status__name">{{ slotTypes.find((t) => t.code === s.slot_type_code)?.name || s.slot_type_code }}</span>
                              <span class="slot-status__value">{{ s.occupied }}/{{ s.capacity }}</span>
                            </div>
                          </div>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'rental' && editDeal.account_id" class="field field--full">
                          <span class="label">Слоты аккаунта (занято)</span>
                          <div v-if="dealAccountAssignmentsLoadingEdit" class="loader-wrap loader-wrap--compact">
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
                          <table v-else-if="dealAccountAssignmentsEdit.filter((s) => !s.released_at).length" class="table table--compact table--dense">
                            <thead>
                              <tr>
                                <th>Слот</th>
                                <th>Игра</th>
                                <th>Пользователь</th>
                                <th>Назначено</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="s in dealAccountAssignmentsEdit.filter((s) => !s.released_at)" :key="s.assignment_id">
                                <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                <td>{{ s.game_title || '—' }}</td>
                                <td>{{ s.customer_nickname || '—' }}</td>
                                <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                              </tr>
                            </tbody>
                          </table>
                          <p v-else class="muted">Пока нет назначенных слотов.</p>
                        </div>
                        <label class="field">
                          <span class="label">Пользователь</span>
                          <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="nickname" :disabled="dealEditMode === 'view'" />
                        </label>
                        <label v-if="editDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Регион</span>
                          <select v-model="editDeal.region_code" class="input input--select" :disabled="dealEditMode === 'view'">
                            <option value="">— не выбрано —</option>
                            <option v-for="r in regions" :key="r.code" :value="r.code">
                              {{ r.name }} ({{ r.code }})
                            </option>
                          </select>
                        </label>
                        <label class="field">
                          <span class="label">Откуда</span>
                          <select v-model="editDeal.source_code" class="input input--select" :disabled="dealEditMode === 'view'">
                            <option value="">— не выбрано —</option>
                            <option v-for="s in sources" :key="s.code" :value="s.code">
                              {{ s.name }} ({{ s.code }})
                            </option>
                          </select>
                        </label>
                        <label v-if="editDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Ссылка на игру</span>
                          <input
                            v-model.trim="editDeal.game_link"
                            class="input"
                            placeholder="https://..."
                            :disabled="dealEditMode === 'view'"
                          />
                        </label>
                        <label v-if="editDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Закуп</span>
                          <input
                            v-model.number="editDeal.purchase_cost"
                            class="input"
                            type="number"
                            min="0"
                            :max="maxPrice"
                            @input="editDeal.purchase_cost = clampPrice(editDeal.purchase_cost)"
                            :disabled="dealEditMode === 'view'"
                          />
                        </label>
                        <label class="field">
                          <span class="label">Сумма</span>
                          <input
                            v-model.number="editDeal.price"
                            class="input"
                            type="number"
                            min="0"
                            :max="maxPrice"
                            @input="editDeal.price = clampPrice(editDeal.price)"
                            :disabled="dealEditMode === 'view'"
                          />
                        </label>
                        <label class="field">
                          <span class="label">Статус</span>
                          <select v-model="editDeal.flow_status_code" class="input input--select" :disabled="dealEditMode === 'view'">
                            <option value="">— не выбрано —</option>
                            <option v-for="s in dealFlowStatusOptions" :key="s.code" :value="s.code">
                              {{ s.name }}
                            </option>
                          </select>
                        </label>
                      </div>
                      <div class="deal-form__col deal-form__col--right">
                        <label v-if="editDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Игра</span>
                          <div class="input input--compact input--search input--search-row">
                            <input
                              v-model.trim="editDealGameSearch"
                              class="input--search-field"
                              placeholder="поиск игры"
                              :disabled="dealEditMode === 'view'"
                              @input="onEditDealGameSearch"
                            />
                          </div>
                          <div class="input--select-wrap">
                            <select
                              v-model.number="editDeal.game_id"
                              class="input input--select input--list"
                              :disabled="dealEditMode === 'view'"
                              :size="editDealGameSearch ? 8 : (editDeal.game_id ? 1 : 8)"
                              @change="syncEditDealGameSearch"
                            >
                              <option value="">— не выбрано —</option>
                              <option v-for="g in filteredEditDealGames" :key="g.game_id" :value="g.game_id">
                                {{ g.title }}
                              </option>
                            </select>
                            <button
                              v-if="editDeal.game_id"
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              aria-label="Очистить игру"
                              title="Очистить игру"
                              :disabled="dealEditMode === 'view'"
                              @click="clearEditDealGame"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M6 6l12 12M18 6l-12 12" />
                              </svg>
                            </button>
                          </div>
                          <div
                            v-if="dealEditMode !== 'view' && editDealGameSearch && filteredEditDealGames.length === 0"
                            class="quick-create"
                          >
                            <div class="quick-create__title">Быстро создать игру</div>
                            <input v-model.trim="quickEditGame.title" class="input input--compact" placeholder="Название игры" />
                            <div class="check-list check-list--compact">
                              <label v-for="p in platforms" :key="`qe-${p.code}`" class="check-item">
                                <input type="checkbox" :value="p.code" v-model="quickEditGame.platform_codes" />
                                <span>{{ p.name }} ({{ p.code }})</span>
                              </label>
                            </div>
                            <div class="quick-create__actions">
                              <button
                                class="ghost ghost--small"
                                type="button"
                                :disabled="quickEditGameLoading"
                                @click="createQuickGame('edit')"
                              >
                                <span v-if="quickEditGameLoading" class="spinner spinner--small"></span>
                                Создать
                              </button>
                              <span v-if="quickEditGameError" class="bad">{{ quickEditGameError }}</span>
                            </div>
                          </div>
                        </label>
                        <label class="field">
                          <span class="label">Комментарий</span>
                          <textarea
                            v-model.trim="editDeal.notes"
                            class="input input--textarea input--textarea--tall"
                            :rows="getNotesRows(editDeal.notes)"
                            :disabled="dealEditMode === 'view'"
                          />
                        </label>
                      </div>
                      <div class="deal-form__full">
                        <p v-if="dealError" class="bad">{{ dealError }}</p>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div v-if="dealEditMode === 'edit'" class="toolbar-actions"></div>
                      </div>
                    </div>
                    <div v-else class="form deal-form">
                      <div class="deal-form__col deal-form__col--left">
                        <label class="field">
                          <span class="label">Тип</span>
                          <select v-model="newDeal.deal_type_code" class="input input--select">
                            <option value="sale">Продажа</option>
                            <option value="rental">Шеринг</option>
                          </select>
                        </label>
                        <label v-if="newDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Тип слота</span>
                          <select
                            v-model="newDeal.slot_type_code"
                            class="input input--select"
                            :disabled="!newDeal.game_id"
                          >
                            <option value="">— не выбрано —</option>
                            <option
                              v-for="st in getDealSlotTypeOptions('new')"
                              :key="st.code"
                              :value="st.code"
                              :disabled="!st.supported"
                            >
                              {{ getDealSlotTypeLabel(st) }}
                            </option>
                          </select>
                          <span v-if="!newDeal.game_id" class="muted muted--small">Сначала выберите игру</span>
                        </label>
                        <label v-if="newDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Аккаунт</span>
                          <select
                            v-model.number="newDeal.account_id"
                            class="input input--select"
                            :disabled="!newDeal.game_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new')"
                          >
                            <option value="">— не выбрано —</option>
                            <option v-for="a in dealAccountsForNew" :key="a.account_id" :value="a.account_id">
                              {{ a.login_full || a.account_id }}
                            </option>
                          </select>
                          <span v-if="!newDeal.game_id" class="muted muted--small">Сначала выберите игру</span>
                          <span v-else-if="!newDeal.slot_type_code" class="muted muted--small">Сначала выберите слот</span>
                          <div
                            v-if="newDeal.game_id && newDeal.slot_type_code && !newDeal.account_id && !isDealSlotTypeUnsupported('new') && !hasFreeDealSlots('new')"
                            class="quick-create"
                          >
                            <div class="quick-create__title">
                              {{ hasAnyGameAssignmentsNew ? 'Нет свободных слотов — можно снять занятый' : 'Нет аккаунтов с игрой' }}
                            </div>
                            <div v-if="hasAnyGameAssignmentsNew && dealGameAssignmentsLoadingNew" class="loader-wrap loader-wrap--compact">
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
                            <table v-else-if="hasAnyGameAssignmentsNew && dealGameAssignmentsForSelectedSlotNew.length" class="table table--compact table--dense">
                              <thead>
                                <tr>
                                  <th>Аккаунт</th>
                                  <th>Слот</th>
                                  <th>Пользователь</th>
                                  <th class="cell--tight"></th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr v-for="s in dealGameAssignmentsForSelectedSlotNew" :key="s.assignment_id">
                                  <td>{{ getAccountLabelById(s.account_id) }}</td>
                                  <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                  <td>{{ s.customer_nickname || '—' }}</td>
                                  <td class="cell--tight">
                                    <button
                                      v-if="!s.released_at"
                                      class="ghost ghost--small"
                                      type="button"
                                      :disabled="accountSlotReleaseLoading"
                                      @click="releaseSlotFromDeal(s, 'new')"
                                    >
                                      Снять
                                    </button>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                            <p v-else-if="hasAnyGameAssignmentsNew" class="muted">Нет активных слотов по игре.</p>
                            <div class="quick-create__title">Быстро создать аккаунт</div>
                            <input v-model.trim="quickNewAccount.login_name" class="input input--compact" placeholder="Логин" />
                            <select v-model="quickNewAccount.domain_code" class="input input--select input--compact">
                              <option value="">— домен —</option>
                              <option v-for="d in domains" :key="`qn-d-${d.code}`" :value="d.code">
                                {{ d.name }} ({{ d.code }})
                              </option>
                            </select>
                            <div class="check-list check-list--compact">
                              <label v-for="p in platforms" :key="`qn-p-${p.code}`" class="check-item">
                                <input type="checkbox" :value="p.code" v-model="quickNewAccount.platform_codes" />
                                <span>{{ p.name }} ({{ p.code }})</span>
                              </label>
                            </div>
                            <div class="quick-create__actions">
                              <button
                                class="ghost ghost--small"
                                type="button"
                                :disabled="quickNewAccountLoading"
                                @click="createQuickAccount('new')"
                              >
                                <span v-if="quickNewAccountLoading" class="spinner spinner--small"></span>
                                Создать
                              </button>
                              <span v-if="quickNewAccountError" class="bad">{{ quickNewAccountError }}</span>
                            </div>
                          </div>
                        </label>
                        <div v-if="newDeal.deal_type_code === 'rental' && newDeal.account_id && accountSlotStatusNew.length" class="slot-status">
                          <div class="slot-status__title">Слоты</div>
                          <div class="slot-status__list">
                            <div v-for="s in getSortedSlotStatus(accountSlotStatusNew)" :key="s.slot_type_code" class="slot-status__row">
                              <span class="slot-status__name">{{ slotTypes.find((t) => t.code === s.slot_type_code)?.name || s.slot_type_code }}</span>
                              <span class="slot-status__value">{{ s.occupied }}/{{ s.capacity }}</span>
                            </div>
                          </div>
                        </div>
                        <div v-if="newDeal.deal_type_code === 'rental' && newDeal.account_id" class="field field--full">
                          <span class="label">Слоты аккаунта (занято)</span>
                          <div v-if="dealAccountAssignmentsLoadingNew" class="loader-wrap loader-wrap--compact">
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
                          <table v-else-if="dealAccountAssignmentsNew.filter((s) => !s.released_at).length" class="table table--compact table--dense">
                            <thead>
                              <tr>
                                <th>Слот</th>
                                <th>Игра</th>
                                <th>Пользователь</th>
                                <th>Назначено</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="s in dealAccountAssignmentsNew.filter((s) => !s.released_at)" :key="s.assignment_id">
                                <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                <td>{{ s.game_title || '—' }}</td>
                                <td>{{ s.customer_nickname || '—' }}</td>
                                <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                              </tr>
                            </tbody>
                          </table>
                          <p v-else class="muted">Пока нет назначенных слотов.</p>
                        </div>
                        <label class="field">
                          <span class="label">Пользователь</span>
                          <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="nickname" />
                        </label>
                        <label v-if="newDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Регион</span>
                          <select v-model="newDeal.region_code" class="input input--select">
                            <option value="">— не выбрано —</option>
                            <option v-for="r in regions" :key="r.code" :value="r.code">
                              {{ r.name }} ({{ r.code }})
                            </option>
                          </select>
                        </label>
                        <label class="field">
                          <span class="label">Откуда</span>
                          <select v-model="newDeal.source_code" class="input input--select">
                            <option value="">— не выбрано —</option>
                            <option v-for="s in sources" :key="s.code" :value="s.code">
                              {{ s.name }} ({{ s.code }})
                            </option>
                          </select>
                        </label>
                        <label v-if="newDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Ссылка на игру</span>
                          <input v-model.trim="newDeal.game_link" class="input" placeholder="https://..." />
                        </label>
                        <label v-if="newDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Закуп</span>
                          <input
                            v-model.number="newDeal.purchase_cost"
                            class="input"
                            type="number"
                            min="0"
                            :max="maxPrice"
                            @input="newDeal.purchase_cost = clampPrice(newDeal.purchase_cost)"
                          />
                        </label>
                        <label class="field">
                          <span class="label">Сумма</span>
                          <input
                            v-model.number="newDeal.price"
                            class="input"
                            type="number"
                            min="0"
                            :max="maxPrice"
                            @input="newDeal.price = clampPrice(newDeal.price)"
                          />
                        </label>
                      </div>
                      <div class="deal-form__col deal-form__col--right">
                        <label v-if="newDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Игра</span>
                          <div class="input input--compact input--search input--search-row">
                            <input
                              v-model.trim="newDealGameSearch"
                              class="input--search-field"
                              placeholder="поиск игры"
                              @input="onNewDealGameSearch"
                            />
                          </div>
                          <div class="input--select-wrap">
                            <select
                              v-model.number="newDeal.game_id"
                              class="input input--select input--list"
                              :size="newDealGameSearch ? 8 : (newDeal.game_id ? 1 : 8)"
                              @change="syncNewDealGameSearch"
                            >
                              <option value="">— не выбрано —</option>
                              <option v-for="g in filteredNewDealGames" :key="g.game_id" :value="g.game_id">
                                {{ g.title }}
                              </option>
                            </select>
                            <button
                              v-if="newDeal.game_id"
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              aria-label="Очистить игру"
                              title="Очистить игру"
                              @click="clearNewDealGame"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M6 6l12 12M18 6l-12 12" />
                              </svg>
                            </button>
                          </div>
                          <div
                            v-if="newDealGameSearch && filteredNewDealGames.length === 0"
                            class="quick-create"
                          >
                            <div class="quick-create__title">Быстро создать игру</div>
                            <input v-model.trim="quickNewGame.title" class="input input--compact" placeholder="Название игры" />
                            <div class="check-list check-list--compact">
                              <label v-for="p in platforms" :key="`qn-${p.code}`" class="check-item">
                                <input type="checkbox" :value="p.code" v-model="quickNewGame.platform_codes" />
                                <span>{{ p.name }} ({{ p.code }})</span>
                              </label>
                            </div>
                            <div class="quick-create__actions">
                              <button
                                class="ghost ghost--small"
                                type="button"
                                :disabled="quickNewGameLoading"
                                @click="createQuickGame('new')"
                              >
                                <span v-if="quickNewGameLoading" class="spinner spinner--small"></span>
                                Создать
                              </button>
                              <span v-if="quickNewGameError" class="bad">{{ quickNewGameError }}</span>
                            </div>
                          </div>
                        </label>
                        <label class="field">
                          <span class="label">Комментарий</span>
                          <textarea
                            v-model.trim="newDeal.notes"
                            class="input input--textarea input--textarea--tall"
                            :rows="getNotesRows(newDeal.notes)"
                          />
                        </label>
                      </div>
                      <div class="deal-form__full">
                        <p v-if="dealError" class="bad">{{ dealError }}</p>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div class="toolbar-actions"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </teleport>
          </div>
        </section>

        <section v-if="isAdmin && activeTab === 'catalogs'" class="panel panel--wide">
          <div class="panel__head">
          </div>
          <div class="panel__body">
            <p v-if="catalogsError" class="bad">{{ catalogsError }}</p>
            <p v-if="catalogsOk" class="ok">{{ catalogsOk }}</p>

            <div v-if="catalogsLoading" class="loader-wrap loader-overlay">
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

            <div v-else>
            <div class="catalog">
              <div class="panel__head">
                <div>
                  <h3>Домены</h3>
                </div>
                <div class="toolbar-actions">
                  <button
                    class="btn btn--icon btn--glow btn--glow-add"
                    title="Добавить домен"
                    aria-label="Добавить домен"
                    @click="openDomainModal"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                  </button>
                  <button
                    class="btn btn--icon btn--glow btn--glow-refresh"
                    title="Обновить список"
                    aria-label="Обновить список"
                    @click="loadDomains"
                    :disabled="catalogsLoading"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                      <path d="M20 4v6h-6" />
                    </svg>
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="showDomainForm || editDomain.open"
                  class="modal-backdrop"
                  @click.self="closeDomainModal"
                >
                  <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                    <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                      <h3>{{ editDomain.open ? 'Редактирование домена' : 'Новый домен' }}</h3>
                      <button
                        class="btn btn--icon-plain"
                        type="button"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="closeDomainModal"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                    <div class="modal__body">
                      <div v-if="editDomain.open" class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Домен</span>
                          <input v-model.trim="editDomain.name" class="input" placeholder="example.com" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="saveEditDomain"
                            :disabled="catalogsLoading"
                            aria-label="Сохранить"
                            title="Сохранить"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            class="btn btn--icon-plain"
                            type="button"
                            aria-label="Удалить"
                            title="Удалить"
                            @click="deleteDomain(editDomain.original)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div v-else class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Новый домен</span>
                          <input v-model.trim="newDomain" class="input" placeholder="example.com" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="createDomain"
                            :disabled="catalogsLoading"
                            aria-label="Добавить домен"
                            title="Добавить домен"
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
              <table v-if="sortedDomains.length" class="table table--compact">
                <thead>
                  <tr>
                    <th class="sortable" @click="toggleDomainsSort">Домен</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in sortedDomains" :key="d.name" class="clickable-row" @click="openEditDomain(d)">
                    <td>{{ d.name }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Пока нет доменов.</p>
            </div>

            <div class="catalog">
              <div class="panel__head">
                <div>
                  <h3>Источники</h3>
                </div>
                <div class="toolbar-actions">
                  <button
                    class="btn btn--icon btn--glow btn--glow-add"
                    title="Добавить источник"
                    aria-label="Добавить источник"
                    @click="openSourceModal"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                  </button>
                  <button
                    class="btn btn--icon btn--glow btn--glow-refresh"
                    title="Обновить список"
                    aria-label="Обновить список"
                    @click="loadSources"
                    :disabled="catalogsLoading"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                      <path d="M20 4v6h-6" />
                    </svg>
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="showSourceForm || editSource.open"
                  class="modal-backdrop"
                  @click.self="closeSourceModal"
                >
                  <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                    <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                      <h3>{{ editSource.open ? 'Редактирование источника' : 'Новый источник' }}</h3>
                      <button
                        class="btn btn--icon-plain"
                        type="button"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="closeSourceModal"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                    <div class="modal__body">
                      <div v-if="editSource.open" class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Код</span>
                          <input v-model.trim="editSource.code" class="input" disabled />
                        </label>
                        <label class="field">
                          <span class="label">Название</span>
                          <input v-model.trim="editSource.name" class="input" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="saveEditSource"
                            :disabled="catalogsLoading"
                            aria-label="Сохранить"
                            title="Сохранить"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            class="btn btn--icon-plain"
                            type="button"
                            aria-label="Удалить"
                            title="Удалить"
                            @click="deleteSource(editSource.code)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div v-else class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Источник (код)</span>
                          <input v-model.trim="newSource.code" class="input" placeholder="tg" />
                        </label>
                        <label class="field">
                          <span class="label">Источник (название)</span>
                          <input v-model.trim="newSource.name" class="input" placeholder="Telegram" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="createSource"
                            :disabled="catalogsLoading"
                            aria-label="Добавить источник"
                            title="Добавить источник"
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
              <table v-if="sortedSources.length" class="table table--compact">
                <thead>
                  <tr>
                    <th class="sortable" @click="toggleSourcesSort('code')">Код</th>
                    <th class="sortable" @click="toggleSourcesSort('name')">Название</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in sortedSources" :key="s.code" class="clickable-row" @click="openEditSource(s)">
                    <td>{{ s.code }}</td>
                    <td>{{ s.name }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Пока нет источников.</p>
            </div>

            <div class="catalog">
              <div class="panel__head">
                <div>
                  <h3>Платформы</h3>
                </div>
                <div class="toolbar-actions">
                  <button
                    class="btn btn--icon btn--glow btn--glow-add"
                    title="Добавить платформу"
                    aria-label="Добавить платформу"
                    @click="openPlatformModal"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                  </button>
                  <button
                    class="btn btn--icon btn--glow btn--glow-refresh"
                    title="Обновить список"
                    aria-label="Обновить список"
                    @click="loadCatalogs"
                    :disabled="catalogsLoading"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                      <path d="M20 4v6h-6" />
                    </svg>
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="showPlatformForm || editPlatform.open"
                  class="modal-backdrop"
                  @click.self="closePlatformModal"
                >
                  <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                    <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                      <h3>{{ editPlatform.open ? 'Редактирование платформы' : 'Новая платформа' }}</h3>
                      <button
                        class="btn btn--icon-plain"
                        type="button"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="closePlatformModal"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                    <div class="modal__body">
                      <div v-if="editPlatform.open" class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Код</span>
                          <input v-model.trim="editPlatform.code" class="input" disabled />
                        </label>
                        <label class="field">
                          <span class="label">Название</span>
                          <input v-model.trim="editPlatform.name" class="input" />
                        </label>
                        <label class="field">
                          <span class="label">Слотов на аккаунт</span>
                          <input v-model.number="editPlatform.slot_capacity" class="input" type="number" min="0" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="saveEditPlatform"
                            :disabled="catalogsLoading"
                            aria-label="Сохранить"
                            title="Сохранить"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            class="btn btn--icon-plain"
                            type="button"
                            aria-label="Удалить"
                            title="Удалить"
                            @click="deletePlatform(editPlatform.code)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div v-else class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Платформа (код)</span>
                          <input v-model.trim="newPlatform.code" class="input" placeholder="steam" />
                        </label>
                        <label class="field">
                          <span class="label">Платформа (название)</span>
                          <input v-model.trim="newPlatform.name" class="input" placeholder="Steam" />
                        </label>
                        <label class="field">
                          <span class="label">Слотов на аккаунт</span>
                          <input v-model.number="newPlatform.slot_capacity" class="input" type="number" min="0" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="createPlatform"
                            :disabled="catalogsLoading"
                            aria-label="Добавить платформу"
                            title="Добавить платформу"
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
              <table v-if="sortedPlatforms.length" class="table table--compact">
                <thead>
                  <tr>
                    <th class="sortable" @click="togglePlatformsSort('code')">Код</th>
                    <th class="sortable" @click="togglePlatformsSort('name')">Название</th>
                    <th class="sortable" @click="togglePlatformsSort('slot_capacity')">Слоты</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in sortedPlatforms" :key="p.code" class="clickable-row" @click="openEditPlatform(p)">
                    <td>{{ p.code }}</td>
                    <td>{{ p.name }}</td>
                    <td>{{ p.slot_capacity }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Пока нет платформ.</p>
            </div>

            <div class="catalog">
              <div class="panel__head">
                <div>
                  <h3>Регионы</h3>
                </div>
                <div class="toolbar-actions">
                  <button
                    class="btn btn--icon btn--glow btn--glow-add"
                    title="Добавить регион"
                    aria-label="Добавить регион"
                    @click="openRegionModal"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                  </button>
                  <button
                    class="btn btn--icon btn--glow btn--glow-refresh"
                    title="Обновить список"
                    aria-label="Обновить список"
                    @click="loadCatalogs"
                    :disabled="catalogsLoading"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                      <path d="M20 4v6h-6" />
                    </svg>
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="showRegionForm || editRegion.open"
                  class="modal-backdrop"
                  @click.self="closeRegionModal"
                >
                  <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                    <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                      <h3>{{ editRegion.open ? 'Редактирование региона' : 'Новый регион' }}</h3>
                      <button
                        class="btn btn--icon-plain"
                        type="button"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="closeRegionModal"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                    <div class="modal__body">
                      <div v-if="editRegion.open" class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Код</span>
                          <input v-model.trim="editRegion.code" class="input" disabled />
                        </label>
                        <label class="field">
                          <span class="label">Название</span>
                          <input v-model.trim="editRegion.name" class="input" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="saveEditRegion"
                            :disabled="catalogsLoading"
                            aria-label="Сохранить"
                            title="Сохранить"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            class="btn btn--icon-plain"
                            type="button"
                            aria-label="Удалить"
                            title="Удалить"
                            @click="deleteRegion(editRegion.code)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div v-else class="form form--stack form--compact">
                        <label class="field">
                          <span class="label">Регион (код)</span>
                          <input v-model.trim="newRegion.code" class="input" placeholder="RU" />
                        </label>
                        <label class="field">
                          <span class="label">Регион (название)</span>
                          <input v-model.trim="newRegion.name" class="input" placeholder="Russia" />
                        </label>
                        <div class="toolbar-actions">
                          <button
                            class="btn btn--icon-plain"
                            @click="createRegion"
                            :disabled="catalogsLoading"
                            aria-label="Добавить регион"
                            title="Добавить регион"
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
              <table v-if="sortedRegions.length" class="table table--compact">
                <thead>
                  <tr>
                    <th class="sortable" @click="toggleRegionsSort('code')">Код</th>
                    <th class="sortable" @click="toggleRegionsSort('name')">Название</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in sortedRegions" :key="r.code" class="clickable-row" @click="openEditRegion(r)">
                    <td>{{ r.code }}</td>
                    <td>{{ r.name }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Пока нет регионов.</p>
            </div>
            </div>
          </div>
        </section>

        <section v-if="isAdmin && activeTab === 'users'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Пользователи</h2>
              <p class="muted">Создание менеджеров и управление доступом.</p>
            </div>
            <div class="toolbar-actions">
              <button
                class="btn btn--icon btn--glow btn--glow-add"
                title="Добавить пользователя"
                aria-label="Добавить пользователя"
                @click="openUserModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button
                class="btn btn--icon btn--glow btn--glow-refresh"
                title="Обновить список"
                aria-label="Обновить список"
                @click="loadUsers"
                :disabled="userLoading"
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
              <div v-if="showUserForm" class="modal-backdrop" @click.self="closeUserModal">
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>Новый пользователь</h3>
                    <button
                      class="btn btn--icon-plain"
                      type="button"
                      aria-label="Закрыть"
                      title="Закрыть"
                      @click="closeUserModal"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6l-12 12" />
                      </svg>
                    </button>
                  </div>
                  <div class="modal__body">
                    <div class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Логин</span>
                        <input v-model.trim="newUser.username" class="input" placeholder="manager1" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль</span>
                        <input v-model="newUser.password" class="input" type="password" />
                      </label>
                      <label class="field">
                        <span class="label">Роль</span>
                        <select v-model="newUser.role_code" class="input input--select">
                          <option v-for="r in roles" :key="r.code" :value="r.code">{{ r.name }}</option>
                        </select>
                      </label>
                      <div class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="createUser"
                          :disabled="userLoading"
                          aria-label="Создать пользователя"
                          title="Создать пользователя"
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

            <p v-if="userError" class="bad">{{ userError }}</p>
            <p v-if="userOk" class="ok">{{ userOk }}</p>
            <div v-if="userLoading" class="loader-wrap">
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
            <table v-else-if="sortedUsers.length" class="table">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleUsersSort('username')">Логин</th>
                  <th class="sortable" @click="toggleUsersSort('role')">Роль</th>
                  <th class="sortable" @click="toggleUsersSort('created_at')">Создан</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in sortedUsers" :key="u.username">
                  <td>{{ u.username }}</td>
                  <td>{{ u.role }}</td>
                  <td>{{ new Date(u.created_at).toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет пользователей.</p>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { apiGet, apiPost, apiDelete, apiPut, apiPostForm, apiGetFile, apiPostFormWithProgress } from '../api/http'

const router = useRouter()
const auth = useAuth()

const apiOk = ref(null)
const loading = ref(false)
const error = ref(null)
const accounts = ref([])
const accountsAll = ref([])
const accountsTotal = ref(0)
const accountsPage = ref(1)
const accountsPageInput = ref(1)
const accountsPageSize = ref(50)
const accountSecrets = ref({})
const accountsError = ref(null)
const accountsOk = ref(null)
const accountsLoading = ref(false)
const accountSaving = ref(false)
const accountDeals = ref([])
const accountDealsLoading = ref(false)
const accountDealsError = ref(null)
const accountSlotAssignments = ref([])
const accountSlotAssignmentsLoading = ref(false)
const accountSlotAssignmentsError = ref(null)
const accountSlotReleaseLoading = ref(false)
const dealSaving = ref(false)
const gameSaving = ref(false)
const catalogSaving = ref(false)
const users = ref([])
const roles = ref([])
const platforms = ref([])
const regions = ref([])
const domains = ref([])
const sources = ref([])
const catalogsError = ref(null)
const catalogsOk = ref(null)
const catalogsLoading = ref(false)
const userError = ref(null)
const userOk = ref(null)
const userLoading = ref(false)
const showUserForm = ref(false)
const gameError = ref(null)
const gameOk = ref(null)
const gameLoading = ref(false)
const gameAccounts = ref([])
const gameAccountsLoading = ref(false)
const gameAccountsError = ref(null)
const gameSlotAssignments = ref([])
const gameSlotAssignmentsLoading = ref(false)
const gameSlotAssignmentsError = ref(null)
const dealGameAssignmentsNew = ref([])
const dealGameAssignmentsEdit = ref([])
const dealGameAssignmentsLoadingNew = ref(false)
const dealGameAssignmentsLoadingEdit = ref(false)
const gameAccountsSort = ref({ key: 'free_slots', dir: 'desc' })
const gameAccountsPage = ref(1)
const gameAccountsPageSize = 15
const dealError = ref(null)
const dealOk = ref(null)
const dealLoading = ref(false)
const dealItems = ref([])
const dealListError = ref(null)
const dealListLoading = ref(false)
const dealPage = ref(1)
const dealPageInput = ref(1)
const dealPageSize = ref(20)
const dealTotal = ref(0)
const dealInitLock = ref(false)
const pwdError = ref(null)
const pwdOk = ref(false)
const pwdLoading = ref(false)
const showPwdForm = ref(false)
const accountEditMode = ref('view')
const dealEditMode = ref('view')
const gameEditMode = ref('view')

const sourceNameByCode = computed(() => {
  const map = new Map()
  for (const s of sources.value || []) {
    if (!s?.code) continue
    map.set(s.code, s.name || s.code)
  }
  return map
})

const getSourceName = (code) => {
  if (!code) return '—'
  return sourceNameByCode.value.get(code) || code
}

const accountGameTitles = computed(() => {
  const gameMap = new Map((gamesAll.value || []).map((g) => [g.game_id, g.title]))
  return (editAccount.game_ids || []).map((id) => gameMap.get(id)).filter(Boolean)
})

const activeDealChips = computed(() => {
  const chips = []
  if (dealFilters.search_q) chips.push({ key: 'search', label: 'Поиск', value: dealFilters.search_q })
  if (dealFilters.type_q) {
    const label = dealTypeOptions.find((t) => t.code === dealFilters.type_q)?.name || dealFilters.type_q
    chips.push({ key: 'type', label: 'Тип', value: label })
  }
  if (dealFilters.customer_q) chips.push({ key: 'customer', label: 'Пользователь', value: dealFilters.customer_q })
  if (dealFilters.region_q) {
    const label = regions.value.find((r) => r.code === dealFilters.region_q)?.name || dealFilters.region_q
    chips.push({ key: 'region', label: 'Регион', value: label })
  }
  if (dealFilters.status_q) {
    const label = dealFlowStatusOptions.find((s) => s.code === dealFilters.status_q)?.name || dealFilters.status_q
    chips.push({ key: 'status', label: 'Статус', value: label })
  }
  if (dealFilters.purchase_from || dealFilters.purchase_to) {
    const from = dealFilters.purchase_from ? formatDateOnly(dealFilters.purchase_from) : '—'
    const to = dealFilters.purchase_to ? formatDateOnly(dealFilters.purchase_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  return chips
})

const activeGameChips = computed(() => {
  const chips = []
  if (gameFilters.q) {
    chips.push({ key: 'title', label: 'Игра', value: gameFilters.q })
  }
  if (gameFilters.platform_code) {
    const platform = platforms.value.find((p) => p.code === gameFilters.platform_code)
    chips.push({ key: 'platform', label: 'Платформа', value: platform?.name ? `${platform.name} (${platform.code})` : gameFilters.platform_code })
  }
  if (gameFilters.region_code) {
    const region = regions.value.find((r) => r.code === gameFilters.region_code)
    chips.push({ key: 'region', label: 'Регион', value: region?.name ? `${region.name} (${region.code})` : gameFilters.region_code })
  }
  return chips
})

const activeAccountChips = computed(() => {
  const chips = []
  if (accountFilters.search_q) chips.push({ key: 'search', label: 'Поиск', value: accountFilters.search_q })
  if (accountFilters.login_q) chips.push({ key: 'login', label: 'Логин', value: accountFilters.login_q })
  if (accountFilters.game_q) chips.push({ key: 'game', label: 'Игра', value: accountFilters.game_q })
  if (accountFilters.region_q) chips.push({ key: 'region', label: 'Регион', value: accountFilters.region_q })
  if (accountFilters.status_q) chips.push({ key: 'status', label: 'Статус', value: accountFilters.status_q })
  if (accountFilters.slots_q) chips.push({ key: 'slots', label: 'Слоты', value: accountFilters.slots_q })
  if (accountFilters.date_from || accountFilters.date_to) {
    const from = accountFilters.date_from ? formatDateOnly(accountFilters.date_from) : '—'
    const to = accountFilters.date_to ? formatDateOnly(accountFilters.date_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  return chips
})

const globalSaving = computed(() => accountSaving.value || dealSaving.value || gameSaving.value || catalogSaving.value)

const isAdmin = computed(() => auth.state.role === 'admin')

const dealModalTitle = computed(() => {
  if (showDealForm.value) return 'Новая сделка'
  if (!editDeal.open) return 'Сделка'
  const dateLabel = formatDateOnly(editDeal.purchase_at || editDeal.created_at)
  return dateLabel === '—' ? 'Сделка' : `Сделка ${dateLabel}`
})


const modalRef = ref(null)
const modalPos = reactive({ x: 0, y: 0 })
const modalDragging = ref(false)
const modalDragStart = reactive({ x: 0, y: 0 })
const modalBase = reactive({ left: 0, top: 0, width: 0, height: 0 })
const modalPadding = 16

const modalStyle = computed(() => ({
  transform: `translate(${modalPos.x}px, ${modalPos.y}px)`,
}))

const resetModalPos = () => {
  modalPos.x = 0
  modalPos.y = 0
}

const startModalDrag = (event) => {
  if (event.button !== 0) return
  const rect = modalRef.value?.getBoundingClientRect()
  if (!rect) return
  modalBase.left = rect.left - modalPos.x
  modalBase.top = rect.top - modalPos.y
  modalBase.width = rect.width
  modalBase.height = rect.height
  modalDragging.value = true
  modalDragStart.x = event.clientX - modalPos.x
  modalDragStart.y = event.clientY - modalPos.y
  window.addEventListener('mousemove', onModalDrag)
  window.addEventListener('mouseup', stopModalDrag)
}

const onModalDrag = (event) => {
  if (!modalDragging.value) return
  const nextX = event.clientX - modalDragStart.x
  const nextY = event.clientY - modalDragStart.y
  const minX = modalPadding - modalBase.left
  const maxX = window.innerWidth - modalPadding - (modalBase.left + modalBase.width)
  const minY = modalPadding - modalBase.top
  const maxY = window.innerHeight - modalPadding - (modalBase.top + modalBase.height)
  modalPos.x = Math.min(Math.max(nextX, minX), maxX)
  modalPos.y = Math.min(Math.max(nextY, minY), maxY)
}

const stopModalDrag = () => {
  modalDragging.value = false
  window.removeEventListener('mousemove', onModalDrag)
  window.removeEventListener('mouseup', stopModalDrag)
}

const newUser = reactive({
  username: '',
  password: '',
  role_code: 'manager',
})

const pwdForm = reactive({
  current: '',
  next: '',
  next2: '',
})

const activeTab = ref('deals')

const newGame = reactive({
  title: '',
  short_title: '',
  link: '',
  logo_url: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
})

const newDeal = reactive({
  deal_type_code: 'sale',
  account_id: '',
  game_id: '',
  customer_nickname: '',
  source_code: '',
  region_code: '',
  slot_type_code: '',
  price: 0,
  purchase_cost: 0,
  game_link: '',
  purchase_at: '',
  slots_used: 1,
  notes: '',
})

const editDeal = reactive({
  open: false,
  deal_id: null,
  created_at: '',
  deal_type_code: 'sale',
  account_id: '',
  game_id: '',
  customer_nickname: '',
  source_code: '',
  region_code: '',
  slot_type_code: '',
  price: 0,
  purchase_cost: 0,
  game_link: '',
  purchase_at: '',
  slots_used: 1,
  notes: '',
  flow_status_code: '',
})

const games = ref([])
const gamesAll = ref([])
const gamesTotal = ref(0)
const gamesLoading = ref(false)
const editGame = reactive({
  open: false,
  game_id: null,
  title: '',
  short_title: '',
  link: '',
  logo_url: '',
  logo_b64: '',
  logo_mime: '',
  text_lang: '',
  audio_lang: '',
  vr_support: '',
  platform_codes: [],
  region_code: '',
})
const dealFilters = reactive({
  search_q: '',
  customer_q: '',
  region_q: '',
  status_q: '',
  purchase_from: '',
  purchase_to: '',
  type_q: '',
})
const dealShowCompleted = ref(false)
const slotTypes = ref([])
const accountSlotStatusNew = ref([])
const accountSlotStatusEdit = ref([])
const dealAccountAssignmentsNew = ref([])
const dealAccountAssignmentsEdit = ref([])
const dealAccountAssignmentsLoadingNew = ref(false)
const dealAccountAssignmentsLoadingEdit = ref(false)
const dealSlotAvailabilityNew = ref({})
const dealSlotAvailabilityEdit = ref({})
const dealSlotAvailabilityLoadingNew = ref(false)
const dealSlotAvailabilityLoadingEdit = ref(false)
const dealSlotAutoAssign = ref(false)

const totalPages = computed(() => {
  const pages = Math.ceil(dealTotal.value / dealPageSize.value)
  return pages > 0 ? pages : 1
})

const newDomain = ref('')
const editDomain = reactive({ open: false, name: '', original: '' })
const newSource = reactive({
  code: '',
  name: '',
})
const editSource = reactive({ open: false, code: '', name: '' })
const newPlatform = reactive({
  code: '',
  name: '',
  slot_capacity: 0,
})
const editPlatform = reactive({ open: false, code: '', name: '', slot_capacity: 0 })
const newRegion = reactive({
  code: '',
  name: '',
})
const editRegion = reactive({ open: false, code: '', name: '' })

const newAccount = reactive({
  login_name: '',
  domain_code: '',
  region_code: '',
  notes: '',
  account_date: '',
  email_password: '',
  account_password: '',
  reserve_text: '',
  auth_code: '',
  game_ids: [],
})

const accountModalMode = ref('edit')
const showAccountFilters = ref(false)
const accountGameSearch = ref('')
const editAccountGameSearch = ref('')
const accountGamesLoading = ref(false)
const activeAccountFilter = ref('')
const accountFilterDraft = reactive({
  login: '',
  game: '',
  region: '',
  status: '',
  slots: '',
  date_from: '',
  date_to: '',
})
const editAccount = reactive({
  open: false,
  account_id: null,
  login_name: '',
  domain_code: '',
  region_code: '',
  status_code: 'active',
  notes: '',
  account_date: '',
  email_password: '',
  account_password: '',
  account_key: 'account_password',
  email_key: 'email_password',
  auth_code: '',
  auth_key: 'auth_code',
  reserve_text: '',
  existing_reserve_keys: [],
  has_account: false,
  has_email: false,
  has_auth: false,
  game_ids: [],
})
const showGameForm = ref(false)
const showGameFilters = ref(false)
const showDealForm = ref(false)
const activeDealFilter = ref('')
const activeGameFilter = ref('')
const gameFilterDraft = reactive({
  title: '',
  platform: '',
  region: '',
})
const showGameImport = ref(false)
const gameImportFile = ref(null)
const gameImportValidated = ref(false)
const gameImportErrors = ref([])
const gameImportWarnings = ref([])
const gameImportTotal = ref(0)
const gameImportLoading = ref(false)
const gameImportMessage = ref('')
const gameImportAction = ref('')
const gameImportStats = ref(null)
const gameImportProgress = reactive({ current: 0, total: 0, phase: '' })
const gameImportJobId = ref('')
const importDetailsRef = ref(null)
let gameImportStatusTimer = null
const GAME_IMPORT_JOB_KEY = 'gamesales_game_import_job_v1'
const gameLogoLoading = ref(false)
const gameLogoCache = new Map()
const gameLogoUploading = ref(false)
const gameLogoProgress = ref(0)
const GAME_LOGO_CACHE_KEY = 'gamesales_game_logo_cache_v1'
const GAME_LOGO_CACHE_TTL_MS = 24 * 60 * 60 * 1000
const showDomainForm = ref(false)
const showSourceForm = ref(false)
const showPlatformForm = ref(false)
const showRegionForm = ref(false)
const accountFilters = reactive({
  search_q: '',
  login_q: '',
  game_q: '',
  region_q: '',
  status_q: '',
  slots_q: '',
  date_from: '',
  date_to: '',
})
const accountSort = ref('login_asc')
const gamesSort = ref({ key: 'title', dir: 'asc' })
const dealSort = ref({ key: 'date', dir: 'desc' })
const usersSort = ref({ key: 'created_at', dir: 'desc' })
const domainsSortAsc = ref(true)
const sourcesSort = ref({ key: 'code', dir: 'asc' })
const platformsSort = ref({ key: 'code', dir: 'asc' })
const regionsSort = ref({ key: 'code', dir: 'asc' })
const gamesPage = ref(1)
const gamesPageInput = ref(1)
const gamesPageSize = ref(20)
const newDealGameSearch = ref('')
const editDealGameSearch = ref('')
const dealAccountsForGameNew = ref([])
const dealAccountsForGameEdit = ref([])
const dealAccountsForGameLoading = ref(false)
const quickNewGame = reactive({ title: '', platform_codes: [] })
const quickEditGame = reactive({ title: '', platform_codes: [] })
const quickNewGameLoading = ref(false)
const quickEditGameLoading = ref(false)
const quickNewGameError = ref('')
const quickEditGameError = ref('')
const quickNewAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickEditAccount = reactive({ login_name: '', domain_code: '', platform_codes: [] })
const quickNewAccountLoading = ref(false)
const quickEditAccountLoading = ref(false)
const quickNewAccountError = ref('')
const quickEditAccountError = ref('')
const dealQuickAccountBusy = computed(() => quickNewAccountLoading.value || quickEditAccountLoading.value)
const dealQuickGameBusy = computed(() => quickNewGameLoading.value || quickEditGameLoading.value)

const dealTypeOptions = [
  { code: 'sale', name: 'Продажа' },
  { code: 'rental', name: 'Шеринг' },
  { code: 'expense', name: 'Расходы' },
  { code: 'adjustment', name: 'Корректирование' },
]

const dealStatusOptions = [
  { code: 'draft', name: 'Черновик' },
  { code: 'confirmed', name: 'Подтвержден' },
  { code: 'cancelled', name: 'Отменен' },
  { code: 'closed', name: 'Закрыт' },
]

const dealFlowStatusOptions = [
  { code: 'pending', name: 'В ожидании' },
  { code: 'completed', name: 'Завершен' },
]

const minDate = '2020-01-01'
const maxDate = new Date().toISOString().slice(0, 10)
const maxPrice = 999999
const maxGameTitleLength = 10

const getAccountPlatformSlots = (account, platformCode) => {
  if (!account?.platform_slots || !platformCode) return null
  const code = String(platformCode).toLowerCase()
  return account.platform_slots.find((s) => String(s.platform_code || '').toLowerCase() === code) || null
}

const getAccountSlotsText = (account) => {
  const list = Array.isArray(account?.slot_status) ? account.slot_status : []
  if (list.length) {
    return list.map((s) => `${getSlotTypeLabel(s.slot_type_code)} ${s.occupied || 0}/${s.capacity || 0}`).join(' · ')
  }
  const ps4 = getAccountPlatformSlots(account, 'ps4')
  const ps5 = getAccountPlatformSlots(account, 'ps5')
  const ps4Text = `PS4 ${ps4?.occupied_slots || 0}/${ps4?.slot_capacity || 0}`
  const ps5Text = `PS5 ${ps5?.occupied_slots || 0}/${ps5?.slot_capacity || 0}`
  return `${ps4Text} · ${ps5Text}`
}

const formatAccountSlotStatusLine = (slot) => {
  if (!slot) return '—'
  return `${getSlotTypeLabel(slot.slot_type_code)} - ${slot.occupied || 0}/${slot.capacity || 0}`
}

const formatAccountGamesLine = (account) => {
  const list = Array.isArray(account?.game_titles) ? account.game_titles : []
  if (!list.length) return '—'
  return list.join(', ')
}

const getSortedSlotStatus = (list) => {
  const items = Array.isArray(list) ? [...list] : []
  const order = new Map((slotTypes.value || []).map((t, idx) => [t.code, idx]))
  items.sort((a, b) => {
    const ai = order.has(a.slot_type_code) ? order.get(a.slot_type_code) : 999
    const bi = order.has(b.slot_type_code) ? order.get(b.slot_type_code) : 999
    if (ai !== bi) return ai - bi
    return String(a.slot_type_code || '').localeCompare(String(b.slot_type_code || ''))
  })
  return items
}

const getAccountSlotStatusList = (account) => {
  const list = Array.isArray(account?.slot_status) ? account.slot_status : []
  if (list.length) return getSortedSlotStatus(list)
  return []
}

const getAccountFreeTotal = (account) => {
  const list = Array.isArray(account?.slot_status) ? account.slot_status : null
  if (list) return list.reduce((sum, s) => sum + Number(s?.free || 0), 0)
  return (account?.platform_slots || []).reduce((sum, s) => sum + Number(s?.free_slots || 0), 0)
}

const formatAccountSlots = (account) => getAccountSlotsText(account)

const getAccountFreeSlots = (account, platformCode) => {
  const slot = getAccountPlatformSlots(account, platformCode)
  return Number(slot?.free_slots || 0)
}

const getSlotTypeLabel = (code) => {
  if (!code) return '—'
  return slotTypes.value.find((t) => t.code === code)?.name || code
}

const getGameById = (gameId) => (gamesAll.value || []).find((g) => g.game_id === gameId)

const getGamePlatformCodes = (gameId) => {
  const game = getGameById(gameId)
  const codes = Array.isArray(game?.platform_codes) ? game.platform_codes : []
  return codes.map((c) => String(c).toLowerCase())
}

const isSlotTypeSupportedForGame = (slotTypeCode, gameId) => {
  if (!slotTypeCode || !gameId) return false
  const type = slotTypes.value.find((t) => t.code === slotTypeCode)
  if (!type?.platform_code) return true
  const platforms = getGamePlatformCodes(gameId)
  if (!platforms.length) return true
  const hasPs4 = platforms.includes('ps4')
  const hasPs5 = platforms.includes('ps5')
  if (hasPs4) return true
  if (hasPs5) return String(type.platform_code).toLowerCase() === 'ps5'
  return true
}

const getDealSlotTypeOptions = (target) => {
  const isEdit = target === 'edit'
  const gameId = isEdit ? editDeal.game_id : newDeal.game_id
  const availability = isEdit ? dealSlotAvailabilityEdit.value : dealSlotAvailabilityNew.value
  const hasAssignments = isEdit ? hasAnyGameAssignmentsEdit.value : hasAnyGameAssignmentsNew.value
  return (slotTypes.value || []).map((t) => {
    const supported = isSlotTypeSupportedForGame(t.code, gameId)
    const hasFree = availability?.[t.code]?.hasFree
    const noAccounts = supported && hasFree === false && !hasAssignments
    return { code: t.code, name: t.name, platform_code: t.platform_code, supported, hasFree, noAccounts }
  })
}

const getDealSlotTypeLabel = (slot) => {
  if (!slot) return '—'
  if (!slot.supported) return `${slot.name} — недоступно`
  if (slot.noAccounts) return slot.name
  if (slot.hasFree === false) return `${slot.name} — заняты`
  return slot.name
}

const isDealSlotTypeUnsupported = (target) => {
  const isEdit = target === 'edit'
  const gameId = isEdit ? editDeal.game_id : newDeal.game_id
  const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
  if (!gameId || !slotTypeCode) return false
  return !isSlotTypeSupportedForGame(slotTypeCode, gameId)
}

const hasFreeDealSlots = (target) => {
  const isEdit = target === 'edit'
  const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
  if (!slotTypeCode) return false
  const availability = isEdit ? dealSlotAvailabilityEdit.value : dealSlotAvailabilityNew.value
  if (availability && Object.prototype.hasOwnProperty.call(availability, slotTypeCode)) {
    return Boolean(availability[slotTypeCode]?.hasFree)
  }
  const list = isEdit ? dealAccountsForGameEdit.value : dealAccountsForGameNew.value
  return Array.isArray(list) && list.length > 0
}

const getSlotAssignmentStatus = (item) => (item?.released_at ? 'Снят' : 'Занят')

const getAccountLabelById = (accountId) => {
  if (!accountId) return '—'
  const found = (accountsAll.value || []).find((a) => a.account_id === accountId)
  return found?.login_full || found?.login_name || String(accountId)
}

const getAvailableSlotTypes = (statusList, selected) => {
  const list = Array.isArray(statusList) ? statusList : []
  const allowed = list.filter((s) => Number(s.free || 0) > 0 || s.slot_type_code === selected)
  if (!allowed.length && selected) {
    const fallback = slotTypes.value.find((t) => t.code === selected)
    return fallback ? [{ slot_type_code: fallback.code }] : []
  }
  return getSortedSlotStatus(allowed)
}

const clampPrice = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return 0
  return Math.min(Math.max(num, 0), maxPrice)
}

const clampPriceFilter = (value) => {
  if (value === '' || value === null || value === undefined) return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return ''
  return String(Math.min(Math.max(num, 0), maxPrice))
}

const formatPrice = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
    .format(num)
    .replace(/\u00A0/g, ' ')
}

const getNotesRows = (value) => {
  if (!value) return 2
  const len = String(value).length
  return Math.min(8, Math.max(3, Math.ceil(len / 60)))
}

const mapApiError = (message) => {
  const text = String(message || '')
  if (!text) return 'Ошибка'
  if (text.includes('Not enough free slots.')) {
    const free = text.match(/free_slots=([0-9]+)/)?.[1]
    const req = text.match(/requested=([0-9]+)/)?.[1]
    if (free && req) return `Недостаточно свободных слотов: свободно ${free}, нужно ${req}`
    return 'Недостаточно свободных слотов'
  }
  if (text.includes('slot_type_code is required for rental')) return 'Для шеринга нужно выбрать тип слота'
  if (text.includes('slots_used must be >= 1 for rental')) return 'Для шеринга укажите количество слотов (минимум 1)'
  if (text.includes('slots_used must be >= 1')) return 'Количество слотов должно быть не меньше 1'
  if (text.includes('deal_type_code must be sale or rental')) return 'Тип сделки должен быть продажа или шеринг'
  if (text.includes('Unknown flow_status_code')) return 'Неизвестный статус'
  if (text.includes('region_code is required for sale')) return 'Для продажи укажите регион'
  if (text.includes('account_id is required for rental')) return 'Для шеринга укажите аккаунт'
  if (text.includes('game_id is required for rental')) return 'Для шеринга укажите игру'
  if (text.includes('login_name and domain_code are required')) return 'Укажите логин и домен'
  if (text.includes('title is required')) return 'Укажите название игры'
  if (text.includes('account_date must be between')) return 'Дата аккаунта должна быть между 2020-01-01 и сегодня'
  if (text.includes('purchase_at must be between')) return 'Дата покупки должна быть между 2020-01-01 и сегодня'
  if (text.includes('start_at must be between')) return 'Дата начала должна быть между 2020-01-01 и сегодня'
  if (text.includes('end_at must be between')) return 'Дата окончания должна быть между 2020-01-01 и сегодня'
  if (text.includes('end_at must be >= start_at')) return 'Дата окончания не может быть раньше даты начала'
  if (text.includes('Unknown platform_code')) return 'Неизвестная платформа'
  if (text.includes('Unknown slot_type_code')) return 'Неизвестный тип слота'
  if (text.includes('Unknown region_code')) return 'Неизвестный регион'
  if (text.includes('Unknown domain')) return 'Неизвестный домен'
  if (text.includes('User not found')) return 'Пользователь не найден'
  if (text.includes('Account not found')) return 'Аккаунт не найден'
  if (text.includes('Game not found')) return 'Игра не найдена'
  if (text.includes('Source not found')) return 'Источник не найден'
  if (text.includes('Domain not found')) return 'Домен не найден'
  if (text.includes('Region not found')) return 'Регион не найден'
  if (text.includes('Platform not found')) return 'Платформа не найдена'
  if (text.includes('Game already exists for platforms:')) {
    const list = text.split('Game already exists for platforms:')[1]?.trim()
    return `Игра с таким названием уже есть на платформах: ${list || ''}`.trim()
  }
  return text
}

const gameLogoSrc = computed(() => {
  if (!editGame.logo_b64 || !editGame.logo_mime) return ''
  return `data:${editGame.logo_mime};base64,${editGame.logo_b64}`
})

const filteredNewDealGames = computed(() => {
  const list = gamesAll.value || []
  const q = newDealGameSearch.value.trim().toLowerCase()
  if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
  if (newDeal.game_id) return list.filter((g) => g.game_id === newDeal.game_id)
  return list
})

const filteredEditDealGames = computed(() => {
  const list = gamesAll.value || []
  const q = editDealGameSearch.value.trim().toLowerCase()
  if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
  if (editDeal.game_id) return list.filter((g) => g.game_id === editDeal.game_id)
  return list
})

const getLogoCacheStore = () => {
  try {
    const raw = localStorage.getItem(GAME_LOGO_CACHE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

const saveLogoCacheStore = (store) => {
  try {
    localStorage.setItem(GAME_LOGO_CACHE_KEY, JSON.stringify(store))
  } catch {
    // ignore storage errors
  }
}

const readLogoCache = (gameId) => {
  const store = getLogoCacheStore()
  const item = store[gameId]
  if (!item) return null
  if (Date.now() - item.ts > GAME_LOGO_CACHE_TTL_MS) {
    delete store[gameId]
    saveLogoCacheStore(store)
    return null
  }
  return item
}

const writeLogoCache = (gameId, value) => {
  const store = getLogoCacheStore()
  store[gameId] = { ...value, ts: Date.now() }
  saveLogoCacheStore(store)
}

const clearLogoCache = (gameId) => {
  const store = getLogoCacheStore()
  if (store[gameId]) {
    delete store[gameId]
    saveLogoCacheStore(store)
  }
}

const getDealGameTitleDisplay = (deal) => {
  if (!deal) return '—'
  const title = String(deal.game_title || '')
  const shortTitle = String(deal.game_short_title || '')
  if (title.length > maxGameTitleLength && shortTitle) {
    return shortTitle
  }
  return title || '—'
}

const getDealGameTitleTooltip = (deal) => {
  if (!deal) return ''
  const title = String(deal.game_title || '')
  const shortTitle = String(deal.game_short_title || '')
  if (title.length > maxGameTitleLength && shortTitle) {
    return title
  }
  return ''
}

const formatGamePlatforms = (codes) => {
  const list = Array.isArray(codes) ? codes : []
  if (!list.length) return '—'
  return list.join(', ')
}

const sortedAccounts = computed(() => [...accounts.value])

const dealAccountsForNew = computed(() => {
  if (!newDeal.game_id || !newDeal.slot_type_code) return []
  return [...dealAccountsForGameNew.value]
})

const dealAccountsForEdit = computed(() => {
  if (!editDeal.game_id || !editDeal.slot_type_code) return []
  return [...dealAccountsForGameEdit.value]
})

const dealGameAssignmentsForSelectedSlotNew = computed(() => {
  if (!newDeal.slot_type_code) return []
  return (dealGameAssignmentsNew.value || []).filter((s) => !s.released_at && s.slot_type_code === newDeal.slot_type_code)
})

const dealGameAssignmentsForSelectedSlotEdit = computed(() => {
  if (!editDeal.slot_type_code) return []
  return (dealGameAssignmentsEdit.value || []).filter((s) => !s.released_at && s.slot_type_code === editDeal.slot_type_code)
})

const hasAnyGameAssignmentsNew = computed(() => (dealGameAssignmentsNew.value || []).some((s) => !s.released_at))
const hasAnyGameAssignmentsEdit = computed(() => (dealGameAssignmentsEdit.value || []).some((s) => !s.released_at))



const filteredAccountGames = computed(() => {
  const q = accountGameSearch.value.trim().toLowerCase()
  if (!q) return gamesAll.value
  return gamesAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
})

const filteredEditAccountGames = computed(() => {
  const q = editAccountGameSearch.value.trim().toLowerCase()
  if (!q) return gamesAll.value
  return gamesAll.value.filter((g) => (g.title || '').toLowerCase().includes(q))
})

const gameFilters = reactive({
  q: '',
  platform_code: '',
  region_code: '',
})

const sortedGames = computed(() => [...games.value])

const gamesTotalPages = computed(() => {
  const pages = Math.ceil(gamesTotal.value / gamesPageSize.value)
  return pages > 0 ? pages : 1
})

const pagedGames = computed(() => {
  return sortedGames.value
})

const accountsTotalPages = computed(() => {
  const pages = Math.ceil(accountsTotal.value / accountsPageSize.value)
  return pages > 0 ? pages : 1
})

watch(gamesTotalPages, (total) => {
  if (gamesPage.value > total) gamesPage.value = total
})

watch(gamesPage, (val) => {
  gamesPageInput.value = val
})

watch(gamesPageSize, () => {
  gamesPage.value = 1
  loadGames()
})

watch(accountsTotalPages, (total) => {
  if (accountsPage.value > total) accountsPage.value = total
})

watch(accountsPage, (val) => {
  accountsPageInput.value = val
})

watch(accountsPageSize, () => {
  accountsPage.value = 1
  loadAccounts()
})

watch(totalPages, (total) => {
  if (dealPage.value > total) dealPage.value = total
})

watch(dealPage, (val) => {
  dealPageInput.value = val
})

watch(dealPageSize, () => {
  dealPage.value = 1
  loadDeals(1)
})

const sortedDeals = computed(() => {
  const list = [...dealItems.value]
  const { key, dir } = dealSort.value
  const getVal = (d) => {
    if (key === 'type') return d.deal_type || ''
    if (key === 'customer') return d.customer_nickname || ''
    if (key === 'region') return d.region_code || ''
    if (key === 'status') return d.flow_status || ''
    if (key === 'date') return new Date(d.purchase_at || d.created_at || 0).getTime()
    return ''
  }
  list.sort((a, b) => {
    const av = getVal(a)
    const bv = getVal(b)
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const sortedUsers = computed(() => {
  const list = [...users.value]
  const { key, dir } = usersSort.value
  list.sort((a, b) => {
    const av = key === 'created_at' ? new Date(a.created_at || 0).getTime() : a[key]
    const bv = key === 'created_at' ? new Date(b.created_at || 0).getTime() : b[key]
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const sortedDomains = computed(() => {
  const list = [...domains.value]
  list.sort((a, b) =>
    domainsSortAsc.value
      ? String(a.name || '').localeCompare(String(b.name || ''))
      : String(b.name || '').localeCompare(String(a.name || ''))
  )
  return list
})

const sortedSources = computed(() => {
  const list = [...sources.value]
  const { key, dir } = sourcesSort.value
  list.sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const sortedPlatforms = computed(() => {
  const list = [...platforms.value]
  const { key, dir } = platformsSort.value
  list.sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const sortedRegions = computed(() => {
  const list = [...regions.value]
  const { key, dir } = regionsSort.value
  list.sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

async function checkApi() {
  loading.value = true
  error.value = null
  try {
    await apiGet('/health', { token: auth.state.token })
    apiOk.value = true
  } catch (e) {
    apiOk.value = false
    error.value = mapApiError(e?.message)
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  if (!isAdmin.value) return
  userLoading.value = true
  userError.value = null
  try {
    const rolesData = await apiGet('/user-roles', { token: auth.state.token })
    roles.value = rolesData || []
    const data = await apiGet('/users', { token: auth.state.token })
    users.value = data || []
  } catch (e) {
    userError.value = mapApiError(e?.message)
  } finally {
    userLoading.value = false
  }
}

async function loadCatalogs() {
  catalogsLoading.value = true
  try {
    const [p, r] = await Promise.all([
      apiGet('/platforms', { token: auth.state.token }),
      apiGet('/regions', { token: auth.state.token }),
    ])
    platforms.value = p || []
    regions.value = r || []
  } catch {
    platforms.value = []
    regions.value = []
  } finally {
    catalogsLoading.value = false
  }
}

async function loadSlotTypes() {
  try {
    const data = await apiGet('/slot-types', { token: auth.state.token })
    slotTypes.value = data || []
    if (newDeal.game_id) loadDealSlotAvailability('new')
    if (editDeal.open && editDeal.game_id) loadDealSlotAvailability('edit')
  } catch {
    slotTypes.value = []
  }
}

async function loadDomains() {
  catalogsLoading.value = true
  try {
    const d = await apiGet('/domains', { token: auth.state.token })
    domains.value = d || []
  } catch {
    domains.value = []
  } finally {
    catalogsLoading.value = false
  }
}

async function loadSources() {
  catalogsLoading.value = true
  try {
    const s = await apiGet('/sources', { token: auth.state.token })
    sources.value = s || []
  } catch {
    sources.value = []
  } finally {
    catalogsLoading.value = false
  }
}

function fromBase64(value) {
  try {
    const binary = atob(value)
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
    return new TextDecoder().decode(bytes)
  } catch {
    return ''
  }
}

function formatSecret(value, isList = false) {
  if (!value) return '—'
  return value
}

function openGameAccounts(game) {
  resetModalPos()
  startEditGame(game)
  gameAccounts.value = []
  gameAccountsPage.value = 1
  loadGameAccounts(game.game_id)
  loadGameSlotAssignments(game.game_id)
}

function toggleAccountSort(key) {
  const map = {
    login: ['login_asc', 'login_desc'],
    region: ['region_asc', 'region_desc'],
    status: ['status_asc', 'status_desc'],
    slots: ['slots_asc', 'slots_desc'],
    date: ['date_asc', 'date_desc'],
  }
  const [asc, desc] = map[key] || []
  if (!asc) return
  accountSort.value = accountSort.value === asc ? desc : asc
  accountsPage.value = 1
  loadAccounts()
}

function toggleGamesSort(key) {
  const current = gamesSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    gamesSort.value = { key, dir: 'asc' }
  }
  gamesPage.value = 1
  loadGames()
}

function toggleDealSort(key) {
  const current = dealSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    dealSort.value = { key, dir: 'asc' }
  }
}

function setDealPage(page) {
  const target = Math.min(Math.max(1, Number(page) || 1), totalPages.value)
  if (target === dealPage.value) return
  loadDeals(target)
}

function jumpDealPage() {
  setDealPage(dealPageInput.value)
}

function prevDealPage() {
  setDealPage(dealPage.value - 1)
}

function nextDealPage() {
  setDealPage(dealPage.value + 1)
}

function toggleUsersSort(key) {
  const current = usersSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    usersSort.value = { key, dir: 'asc' }
  }
}

function toggleDomainsSort() {
  domainsSortAsc.value = !domainsSortAsc.value
}

function toggleSourcesSort(key) {
  const current = sourcesSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    sourcesSort.value = { key, dir: 'asc' }
  }
}

function togglePlatformsSort(key) {
  const current = platformsSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    platformsSort.value = { key, dir: 'asc' }
  }
}

function toggleRegionsSort(key) {
  const current = regionsSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    regionsSort.value = { key, dir: 'asc' }
  }
}

function setGamesPage(page) {
  const target = Math.min(Math.max(1, Number(page) || 1), gamesTotalPages.value)
  if (target === gamesPage.value) return
  gamesPage.value = target
  loadGames()
}

function jumpGamesPage() {
  setGamesPage(gamesPageInput.value)
}

function prevGamesPage() {
  setGamesPage(gamesPage.value - 1)
}

function nextGamesPage() {
  setGamesPage(gamesPage.value + 1)
}

function setAccountsPage(page) {
  const target = Math.min(Math.max(1, Number(page) || 1), accountsTotalPages.value)
  if (target === accountsPage.value) return
  accountsPage.value = target
  loadAccounts()
}

function jumpAccountsPage() {
  setAccountsPage(accountsPageInput.value)
}

function prevAccountsPage() {
  setAccountsPage(accountsPage.value - 1)
}

function nextAccountsPage() {
  setAccountsPage(accountsPage.value + 1)
}

function startEditGame(game) {
  resetModalPos()
  showGameForm.value = false
  editGame.open = true
  gameEditMode.value = 'view'
  editGame.game_id = game.game_id
  editGame.title = game.title || ''
  editGame.short_title = game.short_title || ''
  editGame.link = game.link || ''
  editGame.logo_url = game.logo_url || ''
  editGame.logo_b64 = ''
  editGame.logo_mime = ''
  editGame.text_lang = game.text_lang || ''
  editGame.audio_lang = game.audio_lang || ''
  editGame.vr_support = game.vr_support || ''
  editGame.platform_codes = Array.isArray(game.platform_codes) ? [...game.platform_codes] : []
  editGame.region_code = game.region_code || ''
  loadGameLogo(game.game_id)
  loadGameSlotAssignments(game.game_id)
}

function cancelEditGame() {
  editGame.open = false
  editGame.game_id = null
  gameEditMode.value = 'view'
  editGame.title = ''
  editGame.short_title = ''
  editGame.link = ''
  editGame.logo_url = ''
  editGame.logo_b64 = ''
  editGame.logo_mime = ''
  editGame.text_lang = ''
  editGame.audio_lang = ''
  editGame.vr_support = ''
  editGame.platform_codes = []
  editGame.region_code = ''
  gameLogoLoading.value = false
  gameLogoUploading.value = false
  gameLogoProgress.value = 0
  gameSlotAssignments.value = []
  gameSlotAssignmentsError.value = null
  gameSlotAssignmentsLoading.value = false
}

function openCreateGameModal() {
  resetModalPos()
  showGameForm.value = true
  gameEditMode.value = 'edit'
  cancelEditGame()
  gameError.value = null
  gameOk.value = null
}

function openGameImport() {
  resetModalPos()
  showGameImport.value = true
  gameImportFile.value = null
  gameImportValidated.value = false
  gameImportErrors.value = []
  gameImportWarnings.value = []
  gameImportTotal.value = 0
  gameImportLoading.value = false
  gameImportMessage.value = ''
  gameImportAction.value = ''
  gameImportStats.value = null
  gameImportProgress.current = 0
  gameImportProgress.total = 0
  gameImportProgress.phase = ''
  gameImportJobId.value = ''
  stopGameImportStatusPolling()
  const stored = localStorage.getItem(GAME_IMPORT_JOB_KEY)
  if (stored) {
    gameImportJobId.value = stored
    gameImportAction.value = 'upload'
    gameImportLoading.value = true
    startGameImportStatusPolling()
  }
}

function closeGameImport() {
  showGameImport.value = false
  gameImportFile.value = null
  gameImportValidated.value = false
  gameImportErrors.value = []
  gameImportWarnings.value = []
  gameImportTotal.value = 0
  gameImportLoading.value = false
  gameImportMessage.value = ''
  gameImportAction.value = ''
  gameImportStats.value = null
  gameImportProgress.current = 0
  gameImportProgress.total = 0
  gameImportProgress.phase = ''
  gameImportJobId.value = ''
  stopGameImportStatusPolling()
}

async function pollGameImportStatusOnce() {
  if (!gameImportJobId.value) return
  try {
    const status = await apiGet(`/games/import/status?job_id=${encodeURIComponent(gameImportJobId.value)}`, { token: auth.state.token })
    if (!status) return
    gameImportProgress.current = Number(status.current || 0)
    gameImportProgress.total = Number(status.total || 0)
    gameImportProgress.phase = status.phase || ''
    if (status.done && status.result) {
      applyGameImportResult(status.result)
      return
    }
    if (status.done) {
      gameImportMessage.value = 'Импорт завершен'
      gameImportLoading.value = false
      gameImportAction.value = ''
      gameImportJobId.value = ''
      localStorage.removeItem(GAME_IMPORT_JOB_KEY)
      stopGameImportStatusPolling()
    }
  } catch {
    // ignore polling errors
  }
}

function startGameImportStatusPolling() {
  stopGameImportStatusPolling()
  pollGameImportStatusOnce()
  gameImportStatusTimer = setInterval(async () => {
    try {
      if (!gameImportJobId.value) return
      const status = await apiGet(`/games/import/status?job_id=${encodeURIComponent(gameImportJobId.value)}`, { token: auth.state.token })
      if (!status) return
      gameImportProgress.current = Number(status.current || 0)
      gameImportProgress.total = Number(status.total || 0)
      gameImportProgress.phase = status.phase || ''
      if (status.done && status.result) {
        applyGameImportResult(status.result)
      }
      if (status.done && !status.result) {
        gameImportMessage.value = 'Импорт завершен'
        gameImportLoading.value = false
        gameImportAction.value = ''
        gameImportJobId.value = ''
        localStorage.removeItem(GAME_IMPORT_JOB_KEY)
        stopGameImportStatusPolling()
      }
      if (status.done && !gameImportLoading.value) stopGameImportStatusPolling()
    } catch {
      // ignore polling errors
    }
  }, 600)
}

function stopGameImportStatusPolling() {
  if (!gameImportStatusTimer) return
  clearInterval(gameImportStatusTimer)
  gameImportStatusTimer = null
}

function scrollToImportDetails() {
  if (!importDetailsRef.value) return
  importDetailsRef.value.scrollIntoView({ behavior: "smooth", block: "start" })
}

async function applyGameImportResult(res) {
  if (!res) return
  if (res?.cancelled) {
    gameImportMessage.value = 'Импорт отменен'
    gameImportErrors.value = []
    gameImportWarnings.value = []
    gameImportStats.value = null
    gameImportLoading.value = false
    gameImportAction.value = ''
    gameImportJobId.value = ''
    localStorage.removeItem(GAME_IMPORT_JOB_KEY)
    stopGameImportStatusPolling()
    return
  }
  const created = res?.created || 0
  const updated = res?.updated || 0
  const skipped = res?.skipped || 0
  const failed = res?.failed || 0
  gameImportErrors.value = res?.errors || []
  gameImportWarnings.value = res?.warnings || []
  if (res?.ok) {
    gameImportMessage.value = `Загружено. Создано: ${created}, обновлено: ${updated}, пропущено: ${skipped}`
  } else {
    const until = res?.success_until_row ? `до строки ${res.success_until_row}` : 'до строки —'
    gameImportMessage.value = `Загрузка с ошибками, успешно ${until}. Ошибок: ${failed}`
  }
  gameImportStats.value = { created, updated, skipped, failed, total: res?.total || 0 }
  gameImportLoading.value = false
  gameImportAction.value = ''
  gameImportJobId.value = ''
  localStorage.removeItem(GAME_IMPORT_JOB_KEY)
  stopGameImportStatusPolling()
  await loadGames()
  await loadGamesAll()
}

function onGameImportFile(event) {
  const file = event?.target?.files?.[0]
  gameImportFile.value = file || null
  gameImportValidated.value = false
  gameImportErrors.value = []
  gameImportWarnings.value = []
  gameImportTotal.value = 0
  gameImportMessage.value = ''
  gameImportAction.value = ''
  gameImportStats.value = null
  gameImportProgress.current = 0
  gameImportProgress.total = 0
  gameImportProgress.phase = ''
  gameImportJobId.value = ''
  stopGameImportStatusPolling()
}

async function downloadGameTemplate() {
  try {
    const blob = await apiGetFile('/games/import/template', { token: auth.state.token })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'games_import_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    gameImportMessage.value = mapApiError(e?.message)
  }
}

async function validateGameImport() {
  if (!gameImportFile.value) return
  const form = new FormData()
  form.append('file', gameImportFile.value)
  gameImportValidated.value = false
  gameImportAction.value = 'validate'
  gameImportLoading.value = true
  gameImportProgress.current = 0
  gameImportProgress.total = gameImportTotal.value || 0
  gameImportProgress.phase = ''
  try {
    const res = await apiPostForm('/games/import/validate', form, { token: auth.state.token })
    gameImportErrors.value = res?.errors || []
    gameImportWarnings.value = res?.warnings || []
    gameImportTotal.value = res?.total || 0
    gameImportValidated.value = Boolean(res?.ok)
    if (res?.ok) {
      gameImportMessage.value = gameImportWarnings.value.length
        ? `Файл корректный. Некоторые строки будут пропущены: ${gameImportWarnings.value.length}.`
        : `Файл корректный. Строк: ${gameImportTotal.value}. Можно загружать.`
    } else {
      gameImportMessage.value = 'Файл не корректен. Исправьте ошибки ниже.'
    }
  } catch (e) {
    gameImportValidated.value = false
    gameImportErrors.value = []
    gameImportWarnings.value = []
    gameImportMessage.value = mapApiError(e?.message)
  } finally {
    gameImportLoading.value = false
    gameImportAction.value = ''
    stopGameImportStatusPolling()
  }
}

async function uploadGameImport() {
  if (!gameImportFile.value || !gameImportValidated.value) return
  const form = new FormData()
  form.append('file', gameImportFile.value)
  gameImportAction.value = 'upload'
  gameImportLoading.value = true
  gameImportProgress.current = 0
  gameImportProgress.total = gameImportTotal.value || 0
  gameImportProgress.phase = ''
  try {
    const res = await apiPostForm('/games/import', form, { token: auth.state.token })
    if (res?.job_id) {
      gameImportJobId.value = res.job_id
      localStorage.setItem(GAME_IMPORT_JOB_KEY, res.job_id)
      startGameImportStatusPolling()
    } else {
      gameImportMessage.value = 'Не удалось запустить импорт'
      gameImportLoading.value = false
      gameImportAction.value = ''
    }
  } catch (e) {
    gameImportMessage.value = mapApiError(e?.message)
    gameImportLoading.value = false
    gameImportAction.value = ''
  } finally {
    // wait for background job result
  }
}

async function cancelGameImport() {
  if (!gameImportJobId.value) return
  gameImportAction.value = 'cancel'
  gameImportLoading.value = true
  try {
    await apiPost(`/games/import/cancel?job_id=${encodeURIComponent(gameImportJobId.value)}`, {}, { token: auth.state.token })
    startGameImportStatusPolling()
  } catch (e) {
    gameImportMessage.value = mapApiError(e?.message)
    gameImportLoading.value = false
    gameImportAction.value = ''
  }
}

function downloadGamesExport() {
  gameImportMessage.value = 'Выгрузка будет добавлена позже'
  showGameImport.value = true
}

function closeGameModal() {
  showGameForm.value = false
  cancelEditGame()
  gameError.value = null
  gameOk.value = null
  gameAccounts.value = []
  gameAccountsError.value = null
  gameAccountsLoading.value = false
  gameSlotAssignments.value = []
  gameSlotAssignmentsError.value = null
  gameSlotAssignmentsLoading.value = false
  newGame.title = ''
  newGame.short_title = ''
  newGame.link = ''
  newGame.logo_url = ''
  newGame.text_lang = ''
  newGame.audio_lang = ''
  newGame.vr_support = ''
  newGame.platform_codes = []
  newGame.region_code = ''
}

function refreshGameAccounts() {
  if (editGame.game_id) {
    gameAccountsPage.value = 1
    loadGameAccounts(editGame.game_id)
  }
}

async function loadGameLogo(gameId) {
  editGame.logo_b64 = ''
  editGame.logo_mime = ''
  gameLogoLoading.value = true
  if (gameLogoCache.has(gameId)) {
    const cached = gameLogoCache.get(gameId)
    editGame.logo_b64 = cached?.data_b64 || ''
    editGame.logo_mime = cached?.mime || ''
    gameLogoLoading.value = false
    return
  }
  const stored = readLogoCache(gameId)
  if (stored) {
    editGame.logo_b64 = stored?.data_b64 || ''
    editGame.logo_mime = stored?.mime || ''
    gameLogoCache.set(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
    gameLogoLoading.value = false
    return
  }
  try {
    const res = await apiGet(`/games/${gameId}/logo`, { token: auth.state.token })
    editGame.logo_b64 = res?.data_b64 || ''
    editGame.logo_mime = res?.mime || ''
    gameLogoCache.set(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
    writeLogoCache(gameId, { data_b64: editGame.logo_b64, mime: editGame.logo_mime })
  } catch {
    // no logo or error, ignore
  } finally {
    gameLogoLoading.value = false
  }
}

async function onGameLogoSelected(event) {
  const file = event?.target?.files?.[0]
  if (!file || !editGame.game_id) return
  const form = new FormData()
  form.append('file', file)
  gameLogoLoading.value = true
  gameLogoUploading.value = true
  gameLogoProgress.value = 0
  try {
    await apiPostFormWithProgress(`/games/${editGame.game_id}/logo`, form, {
      token: auth.state.token,
      onProgress: (p) => { gameLogoProgress.value = p },
    })
    gameLogoCache.delete(editGame.game_id)
    clearLogoCache(editGame.game_id)
    await loadGameLogo(editGame.game_id)
  } catch (e) {
    gameError.value = mapApiError(e?.message)
    gameLogoLoading.value = false
  } finally {
    gameLogoUploading.value = false
    event.target.value = ''
  }
}

async function removeGameLogo() {
  if (!editGame.game_id) return
  gameLogoLoading.value = true
  gameLogoUploading.value = false
  try {
    await apiDelete(`/games/${editGame.game_id}/logo`, { token: auth.state.token })
    editGame.logo_b64 = ''
    editGame.logo_mime = ''
    gameLogoCache.delete(editGame.game_id)
    clearLogoCache(editGame.game_id)
  } catch (e) {
    gameError.value = mapApiError(e?.message)
  } finally {
    gameLogoLoading.value = false
  }
}

function goToAccount(login) {
  activeTab.value = 'accounts'
  accountFilters.login_q = login || ''
}

function openAccountFromGame(login) {
  if (!login) return
  closeGameModal()
  goToAccount(login)
}

async function openDealGame(deal) {
  if (!deal || !deal.game_id) return
  activeTab.value = 'games'
  gameFilters.q = deal.game_title || ''
  gameFilters.platform_code = ''
  gameFilters.region_code = ''
  gameFilterDraft.title = gameFilters.q
  gameFilterDraft.platform = ''
  gameFilterDraft.region = ''
  gamesPage.value = 1
  await loadGames()
  if (!gamesAll.value.length) {
    await loadGamesAll()
  }
  const game = gamesAll.value.find((g) => g.game_id === deal.game_id) || games.value.find((g) => g.game_id === deal.game_id)
  if (game) {
    openGameAccounts(game)
  }
}

const onDealFilterOutside = (event) => {
  if (!activeDealFilter.value) return
  const target = event.target
  if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
  activeDealFilter.value = ''
}

const resetDealFilter = (kind) => {
  if (kind === 'customer') {
    dealFilters.customer_q = ''
  } else if (kind === 'region') {
    dealFilters.region_q = ''
  } else if (kind === 'type') {
    dealFilters.type_q = ''
  } else if (kind === 'status') {
    dealFilters.status_q = ''
  } else if (kind === 'search') {
    dealFilters.search_q = ''
  } else if (kind === 'date') {
    dealFilters.purchase_from = ''
    dealFilters.purchase_to = ''
    dealFilterErrors.date = ''
  } else if (kind === 'all') {
    dealFilters.search_q = ''
    dealFilters.type_q = ''
    dealFilters.customer_q = ''
    dealFilters.region_q = ''
    dealFilters.status_q = ''
    dealFilters.purchase_from = ''
    dealFilters.purchase_to = ''
    dealFilterErrors.date = ''
  }
  activeDealFilter.value = ''
  loadDeals(1)
}

const validateDealRange = (kind) => {
  let error = ''
  if (kind === 'date') {
    const from = dealFilters.purchase_from
    const to = dealFilters.purchase_to
    if (from && to && new Date(from) > new Date(to)) {
      error = 'Дата "с" не может быть позже даты "по"'
    }
  }
  dealFilterErrors[kind] = error
  return !error
}

const dealFilterErrors = reactive({
  date: '',
})

const resetGameFilter = (kind) => {
  if (kind === 'title') {
    gameFilters.q = ''
    gameFilterDraft.title = ''
  } else if (kind === 'platform') {
    gameFilters.platform_code = ''
    gameFilterDraft.platform = ''
  } else if (kind === 'region') {
    gameFilters.region_code = ''
    gameFilterDraft.region = ''
  } else if (kind === 'all') {
    gameFilters.q = ''
    gameFilters.platform_code = ''
    gameFilters.region_code = ''
    gameFilterDraft.title = ''
    gameFilterDraft.platform = ''
    gameFilterDraft.region = ''
  }
  gamesPage.value = 1
  activeGameFilter.value = ''
  loadGames()
}

const openGameFilter = (kind) => {
  gameFilterDraft.title = gameFilters.q || ''
  gameFilterDraft.platform = gameFilters.platform_code || ''
  gameFilterDraft.region = gameFilters.region_code || ''
  activeGameFilter.value = activeGameFilter.value === kind ? '' : kind
}

const applyGameFilter = (kind) => {
  if (kind === 'title') {
    gameFilters.q = gameFilterDraft.title.trim()
  } else if (kind === 'platform') {
    gameFilters.platform_code = gameFilterDraft.platform.trim()
  } else if (kind === 'region') {
    gameFilters.region_code = gameFilterDraft.region.trim()
  }
  gamesPage.value = 1
  activeGameFilter.value = ''
  loadGames()
}

const resetAccountFilter = (kind) => {
  if (kind === 'login') {
    accountFilters.login_q = ''
    accountFilterDraft.login = ''
  } else if (kind === 'game') {
    accountFilters.game_q = ''
    accountFilterDraft.game = ''
  } else if (kind === 'region') {
    accountFilters.region_q = ''
    accountFilterDraft.region = ''
  } else if (kind === 'status') {
    accountFilters.status_q = ''
    accountFilterDraft.status = ''
  } else if (kind === 'slots') {
    accountFilters.slots_q = ''
    accountFilterDraft.slots = ''
  } else if (kind === 'date') {
    accountFilters.date_from = ''
    accountFilters.date_to = ''
    accountFilterDraft.date_from = ''
    accountFilterDraft.date_to = ''
    accountFilterErrors.date = ''
  } else if (kind === 'all') {
    accountFilters.search_q = ''
    accountFilters.login_q = ''
    accountFilters.game_q = ''
    accountFilters.region_q = ''
    accountFilters.status_q = ''
    accountFilters.slots_q = ''
    accountFilters.date_from = ''
    accountFilters.date_to = ''
    accountFilterDraft.login = ''
    accountFilterDraft.game = ''
    accountFilterDraft.region = ''
    accountFilterDraft.status = ''
    accountFilterDraft.slots = ''
    accountFilterDraft.date_from = ''
    accountFilterDraft.date_to = ''
    accountFilterErrors.date = ''
  }
  activeAccountFilter.value = ''
  accountsPage.value = 1
  loadAccounts()
}

const openAccountFilter = (kind) => {
  accountFilterDraft.login = accountFilters.login_q || ''
  accountFilterDraft.game = accountFilters.game_q || ''
  accountFilterDraft.region = accountFilters.region_q || ''
  accountFilterDraft.status = accountFilters.status_q || ''
  accountFilterDraft.slots = accountFilters.slots_q || ''
  accountFilterDraft.date_from = accountFilters.date_from || ''
  accountFilterDraft.date_to = accountFilters.date_to || ''
  activeAccountFilter.value = activeAccountFilter.value === kind ? '' : kind
}

const applyAccountFilter = (kind) => {
  if (kind === 'login') {
    accountFilters.login_q = accountFilterDraft.login.trim()
  } else if (kind === 'game') {
    accountFilters.game_q = accountFilterDraft.game.trim()
  } else if (kind === 'region') {
    accountFilters.region_q = accountFilterDraft.region.trim()
  } else if (kind === 'status') {
    accountFilters.status_q = accountFilterDraft.status.trim()
  } else if (kind === 'slots') {
    accountFilters.slots_q = accountFilterDraft.slots.trim()
  } else if (kind === 'date') {
    if (!validateAccountDateRange()) return
    accountFilters.date_from = accountFilterDraft.date_from
    accountFilters.date_to = accountFilterDraft.date_to
  }
  activeAccountFilter.value = ''
  accountsPage.value = 1
  loadAccounts()
}

const accountFilterErrors = reactive({
  date: '',
})

const validateAccountDateRange = () => {
  let error = ''
  if (accountFilterDraft.date_from && accountFilterDraft.date_to) {
    if (new Date(accountFilterDraft.date_from) > new Date(accountFilterDraft.date_to)) {
      error = 'Дата "с" не может быть позже даты "по"'
    }
  }
  accountFilterErrors.date = error
  return !error
}

function openCreateDealModal() {
  resetModalPos()
  showDealForm.value = true
  cancelEditDeal()
  dealError.value = null
  dealOk.value = null
  newDealGameSearch.value = ''
  editDealGameSearch.value = ''
  quickNewGame.title = ''
  quickNewGame.platform_codes = []
  quickNewGameError.value = ''
  quickNewAccount.login_name = ''
  quickNewAccount.domain_code = ''
  quickNewAccount.platform_codes = []
  quickNewAccountError.value = ''
  dealAccountsForGameNew.value = []
  dealSlotAvailabilityNew.value = {}
}

function closeDealModal() {
  showDealForm.value = false
  cancelEditDeal()
  dealError.value = null
  dealOk.value = null
  newDeal.deal_type_code = 'sale'
  newDeal.account_id = ''
  newDeal.game_id = ''
  newDeal.customer_nickname = ''
  newDeal.source_code = ''
  newDeal.region_code = ''
  newDeal.slot_type_code = ''
  newDeal.price = 0
  newDeal.purchase_cost = 0
  newDeal.game_link = ''
  newDeal.purchase_at = ''
  newDeal.slots_used = 1
  newDeal.notes = ''
  newDealGameSearch.value = ''
  editDealGameSearch.value = ''
  quickNewGame.title = ''
  quickNewGame.platform_codes = []
  quickNewGameError.value = ''
  quickEditGame.title = ''
  quickEditGame.platform_codes = []
  quickEditGameError.value = ''
  quickNewAccount.login_name = ''
  quickNewAccount.domain_code = ''
  quickNewAccount.platform_codes = []
  quickNewAccountError.value = ''
  quickEditAccount.login_name = ''
  quickEditAccount.domain_code = ''
  quickEditAccount.platform_codes = []
  quickEditAccountError.value = ''
  dealAccountsForGameNew.value = []
  dealAccountsForGameEdit.value = []
  dealAccountAssignmentsNew.value = []
  dealAccountAssignmentsEdit.value = []
  dealSlotAvailabilityNew.value = {}
  dealSlotAvailabilityEdit.value = {}
}

function startEditDeal(deal) {
  resetModalPos()
  showDealForm.value = false
  editDeal.open = true
  dealInitLock.value = true
  dealEditMode.value = 'view'
  editDealGameSearch.value = ''
  quickEditGame.title = ''
  quickEditGame.platform_codes = []
  quickEditGameError.value = ''
  quickEditAccount.login_name = ''
  quickEditAccount.domain_code = ''
  quickEditAccount.platform_codes = []
  quickEditAccountError.value = ''
  dealAccountsForGameEdit.value = []
  editDeal.deal_id = deal.deal_id
  editDeal.created_at = deal.created_at || ''
  editDeal.deal_type_code = deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale')
  editDeal.account_id = deal.account_id
  editDeal.game_id = deal.game_id
  editDeal.customer_nickname = deal.customer_nickname || ''
  editDeal.source_code = deal.source_code || ''
  editDeal.region_code = deal.region_code || ''
  editDeal.slot_type_code = deal.slot_type_code || ''
  editDeal.price = Number(deal.price || 0)
  editDeal.purchase_cost = Number(deal.purchase_cost || 0)
  editDeal.game_link = deal.game_link || ''
  editDeal.purchase_at = deal.purchase_at ? String(deal.purchase_at).slice(0, 10) : ''
  editDeal.slots_used = deal.slots_used || (deal.deal_type_code === 'rental' ? 1 : 0)
  editDeal.notes = deal.notes || ''
  editDeal.flow_status_code = deal.flow_status_code || ''
  nextTick(() => {
    setTimeout(() => {
      dealInitLock.value = false
      if (editDeal.game_id) loadDealSlotAvailability('edit')
    }, 0)
  })
}

function cancelEditDeal() {
  editDeal.open = false
  editDeal.deal_id = null
  editDeal.created_at = ''
  editDeal.deal_type_code = 'sale'
  editDeal.account_id = ''
  editDeal.game_id = ''
  editDeal.customer_nickname = ''
  editDeal.source_code = ''
  editDeal.region_code = ''
  editDeal.slot_type_code = ''
  editDeal.price = 0
  editDeal.purchase_cost = 0
  editDeal.game_link = ''
  editDeal.purchase_at = ''
  editDeal.slots_used = 1
  editDeal.notes = ''
  editDeal.flow_status_code = ''
  dealEditMode.value = 'view'
  dealAccountAssignmentsEdit.value = []
  dealSlotAvailabilityEdit.value = {}
}

function formatDateOnly(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString()
}

function formatDateTimeMinutes(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const date = d.toLocaleDateString()
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return `${date} ${time}`
}

function getEmailSecret(accountId) {
  const list = accountSecrets.value[accountId] || []
  const item = list.find((s) => s.secret_key === 'email_password')
  return item?.secret_value_b64 ? fromBase64(item.secret_value_b64) : ''
}

function getAccountSecret(accountId) {
  const list = accountSecrets.value[accountId] || []
  const item = list.find((s) => s.secret_key === 'account_password' || s.secret_key === 'primary' || s.secret_key === 'password')
  return item?.secret_value_b64 ? fromBase64(item.secret_value_b64) : ''
}

function getReserveSecrets(accountId) {
  const list = accountSecrets.value[accountId] || []
  const reserves = list
    .filter((s) => s.secret_key?.startsWith('reserve'))
    .map((s) => (s.secret_value_b64 ? fromBase64(s.secret_value_b64) : ''))
    .filter(Boolean)
  return reserves.join(' ')
}

function getAuthSecret(accountId) {
  const list = accountSecrets.value[accountId] || []
  const item = list.find((s) => s.secret_key === 'auth_code')
  return item?.secret_value_b64 ? fromBase64(item.secret_value_b64) : ''
}

async function loadAccountSecrets(list) {
  accountSecrets.value = {}
  if (!list.length) return
  await Promise.all(
    list.map(async (a) => {
      try {
        const s = await apiGet(`/accounts/${a.account_id}/secrets`, { token: auth.state.token })
        accountSecrets.value[a.account_id] = s || []
      } catch {
        accountSecrets.value[a.account_id] = []
      }
    })
  )
}

async function loadAccountGames(accountId) {
  accountGamesLoading.value = true
  try {
    const items = await apiGet(`/accounts/${accountId}/games`, { token: auth.state.token })
    editAccount.game_ids = (items || []).map((g) => g.game_id)
  } catch {
    editAccount.game_ids = []
  } finally {
    accountGamesLoading.value = false
  }
}

async function loadGames() {
  gamesLoading.value = true
  try {
    const params = new URLSearchParams()
    if (gameFilters.q) params.set('q', gameFilters.q)
    if (gameFilters.platform_code) params.set('platform_code', gameFilters.platform_code)
    if (gameFilters.region_code) params.set('region_code', gameFilters.region_code)
    params.set('sort_key', gamesSort.value.key)
    params.set('sort_dir', gamesSort.value.dir)
    params.set('page', String(gamesPage.value))
    params.set('page_size', String(gamesPageSize.value))
    const res = await apiGet(`/games?${params.toString()}`, { token: auth.state.token })
    games.value = res?.items || []
    gamesTotal.value = Number(res?.total || 0)
  } catch {
    games.value = []
    gamesTotal.value = 0
  } finally {
    gamesLoading.value = false
  }
}

async function loadGamesAll() {
  try {
    const params = new URLSearchParams()
    params.set('all', 'true')
    params.set('sort_key', 'title')
    params.set('sort_dir', 'asc')
    const res = await apiGet(`/games?${params.toString()}`, { token: auth.state.token })
    gamesAll.value = res?.items || []
  } catch {
    gamesAll.value = []
  }
}

async function loadGameAccounts(gameId) {
  gameAccountsLoading.value = true
  gameAccountsError.value = null
  try {
    const data = await apiGet(`/games/${gameId}/accounts`, { token: auth.state.token })
    gameAccounts.value = data || []
  } catch (e) {
    gameAccountsError.value = mapApiError(e?.message)
    gameAccounts.value = []
  } finally {
    gameAccountsLoading.value = false
  }
}

const sortedGameAccounts = computed(() => {
  const list = [...gameAccounts.value]
  const { key, dir } = gameAccountsSort.value
  list.sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const gameAccountsTotalPages = computed(() => {
  const pages = Math.ceil(sortedGameAccounts.value.length / gameAccountsPageSize)
  return pages > 0 ? pages : 1
})

const pagedGameAccounts = computed(() => {
  const start = (gameAccountsPage.value - 1) * gameAccountsPageSize
  return sortedGameAccounts.value.slice(start, start + gameAccountsPageSize)
})

function sortGameAccounts(key) {
  const current = gameAccountsSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    gameAccountsSort.value = { key, dir: 'asc' }
  }
  gameAccountsPage.value = 1
}

function nextGameAccountsPage() {
  if (gameAccountsPage.value < gameAccountsTotalPages.value) {
    gameAccountsPage.value += 1
  }
}

function prevGameAccountsPage() {
  if (gameAccountsPage.value > 1) {
    gameAccountsPage.value -= 1
  }
}

async function loadAccounts() {
  accountsLoading.value = true
  accountsError.value = null
  accountsOk.value = null
  try {
    const params = new URLSearchParams()
    if (accountFilters.search_q) params.set('q', accountFilters.search_q)
    if (accountFilters.login_q) params.set('login_q', accountFilters.login_q)
    if (accountFilters.game_q) params.set('game_q', accountFilters.game_q)
    if (accountFilters.region_q) params.set('region_q', accountFilters.region_q)
    if (accountFilters.status_q) params.set('status_q', accountFilters.status_q)
    if (accountFilters.slots_q) params.set('slots_q', accountFilters.slots_q)
    if (accountFilters.date_from) params.set('date_from', accountFilters.date_from)
    if (accountFilters.date_to) params.set('date_to', accountFilters.date_to)
    const sortMap = {
      login_asc: { key: 'login', dir: 'asc' },
      login_desc: { key: 'login', dir: 'desc' },
      region_asc: { key: 'region', dir: 'asc' },
      region_desc: { key: 'region', dir: 'desc' },
      status_asc: { key: 'status', dir: 'asc' },
      status_desc: { key: 'status', dir: 'desc' },
      slots_asc: { key: 'slots', dir: 'asc' },
      slots_desc: { key: 'slots', dir: 'desc' },
      date_asc: { key: 'date', dir: 'asc' },
      date_desc: { key: 'date', dir: 'desc' },
    }
    const sort = sortMap[accountSort.value] || sortMap.login_asc
    params.set('sort_key', sort.key)
    params.set('sort_dir', sort.dir)
    params.set('page', String(accountsPage.value))
    params.set('page_size', String(accountsPageSize.value))
    const data = await apiGet(`/accounts?${params.toString()}`, { token: auth.state.token })
    accounts.value = data?.items || []
    accountsTotal.value = Number(data?.total || 0)
    await loadAccountSecrets(accounts.value)
  } catch (e) {
    accountsError.value = mapApiError(e?.message)
    accountsTotal.value = 0
  } finally {
    accountsLoading.value = false
  }
}

async function loadAccountsAll() {
  try {
    const params = new URLSearchParams()
    params.set('all', 'true')
    params.set('sort_key', 'login')
    params.set('sort_dir', 'asc')
    const data = await apiGet(`/accounts?${params.toString()}`, { token: auth.state.token })
    accountsAll.value = data?.items || []
  } catch {
    accountsAll.value = []
  }
}

async function loadAccountDeals(accountId) {
  accountDealsLoading.value = true
  accountDealsError.value = null
  try {
    const params = new URLSearchParams()
    params.set('account_id', String(accountId))
    params.set('page', '1')
    params.set('page_size', '200')
    const res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
    accountDeals.value = res?.items || []
  } catch (e) {
    accountDealsError.value = mapApiError(e?.message)
    accountDeals.value = []
  } finally {
    accountDealsLoading.value = false
  }
}

function startEditAccount(a) {
  resetModalPos()
  accountModalMode.value = 'edit'
  accountEditMode.value = 'view'
  editAccount.open = true
  editAccount.account_id = a.account_id
  editAccount.login_name = a.login_name || ''
  editAccount.domain_code = a.domain_code || ''
  editAccount.region_code = a.region_code || ''
  editAccount.status_code = a.status || 'active'
  editAccount.notes = a.notes || ''
  editAccount.account_date = a.account_date || ''

  const secrets = accountSecrets.value[a.account_id] || []
  const email = secrets.find((s) => s.secret_key === 'email_password')
  const account = secrets.find((s) => s.secret_key === 'account_password' || s.secret_key === 'primary' || s.secret_key === 'password')
  const auth = secrets.find((s) => s.secret_key === 'auth_code')
  const reserves = secrets.filter((s) => s.secret_key?.startsWith('reserve'))
  editAccount.email_password = email?.secret_value_b64 ? fromBase64(email.secret_value_b64) : ''
  editAccount.email_key = email?.secret_key || 'email_password'
  editAccount.account_password = account?.secret_value_b64 ? fromBase64(account.secret_value_b64) : ''
  editAccount.account_key = account?.secret_key || 'account_password'
  editAccount.auth_code = auth?.secret_value_b64 ? fromBase64(auth.secret_value_b64) : ''
  editAccount.auth_key = auth?.secret_key || 'auth_code'
  editAccount.reserve_text = reserves
    .sort((a1, a2) => a1.secret_key.localeCompare(a2.secret_key))
    .map((s) => (s.secret_value_b64 ? fromBase64(s.secret_value_b64) : ''))
    .filter(Boolean)
    .join(' ')
  editAccount.existing_reserve_keys = reserves.map((s) => s.secret_key)
  editAccount.has_account = Boolean(account)
  editAccount.has_email = Boolean(email)
  editAccount.has_auth = Boolean(auth)
  loadAccountGames(a.account_id)
  loadAccountDeals(a.account_id)
  loadAccountSlotAssignments(a.account_id)
}

function openCreateAccountModal() {
  resetModalPos()
  accountModalMode.value = 'create'
  accountEditMode.value = 'edit'
  editAccount.open = true
  accountGamesLoading.value = false
  accountsError.value = null
  accountsOk.value = null
  newAccount.login_name = ''
  newAccount.domain_code = ''
  newAccount.region_code = ''
  newAccount.notes = ''
  newAccount.account_date = ''
  newAccount.email_password = ''
  newAccount.account_password = ''
  newAccount.reserve_text = ''
  newAccount.auth_code = ''
  newAccount.game_ids = []
  accountGameSearch.value = ''
}

function cancelEditAccount() {
  editAccount.open = false
  accountModalMode.value = 'edit'
  editAccount.account_id = null
  editAccount.login_name = ''
  editAccount.domain_code = ''
  editAccount.region_code = ''
  editAccount.status_code = 'active'
  editAccount.notes = ''
  editAccount.account_date = ''
  editAccount.email_password = ''
  editAccount.email_key = 'email_password'
  editAccount.account_password = ''
  editAccount.account_key = 'account_password'
  editAccount.auth_code = ''
  editAccount.auth_key = 'auth_code'
  editAccount.reserve_text = ''
  editAccount.existing_reserve_keys = []
  editAccount.has_account = false
  editAccount.has_email = false
  editAccount.has_auth = false
  editAccount.game_ids = []
  editAccountGameSearch.value = ''
  accountDeals.value = []
  accountDealsError.value = null
  accountDealsLoading.value = false
  accountSlotAssignments.value = []
  accountSlotAssignmentsError.value = null
  accountSlotAssignmentsLoading.value = false
  accountEditMode.value = 'view'
  newAccount.login_name = ''
  newAccount.domain_code = ''
  newAccount.region_code = ''
  newAccount.notes = ''
  newAccount.account_date = ''
  newAccount.email_password = ''
  newAccount.account_password = ''
  newAccount.reserve_text = ''
  newAccount.auth_code = ''
  newAccount.game_ids = []
  accountGameSearch.value = ''
}

async function createAccount() {
  accountsError.value = null
  accountsOk.value = null
  if (!newAccount.login_name || !newAccount.domain_code) {
    accountsError.value = 'Укажите логин и домен'
    return
  }
  accountsLoading.value = true
  try {
    const created = await apiPost(
      '/accounts',
      {
        region_code: newAccount.region_code || null,
        login_name: newAccount.login_name || null,
        domain_code: newAccount.domain_code || null,
        notes: newAccount.notes || null,
        account_date: newAccount.account_date || null,
      },
      { token: auth.state.token }
    )

    const secretTasks = []
    if (newAccount.email_password) {
      secretTasks.push(
        apiPost(
          `/accounts/${created.account_id}/secrets`,
          { secret_key: 'email_password', secret_value: newAccount.email_password },
          { token: auth.state.token }
        )
      )
    }
    if (newAccount.account_password) {
      secretTasks.push(
        apiPost(
          `/accounts/${created.account_id}/secrets`,
          { secret_key: 'account_password', secret_value: newAccount.account_password },
          { token: auth.state.token }
        )
      )
    }
    if (newAccount.auth_code) {
      secretTasks.push(
        apiPost(
          `/accounts/${created.account_id}/secrets`,
          { secret_key: 'auth_code', secret_value: newAccount.auth_code },
          { token: auth.state.token }
        )
      )
    }
    const reserveValues = (newAccount.reserve_text || '')
      .split(/\s+/)
      .map((v) => v.trim())
      .filter(Boolean)
    reserveValues
      .forEach((val, idx) => {
        secretTasks.push(
          apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: `reserve${idx + 1}`, secret_value: val },
            { token: auth.state.token }
          )
        )
      })
    if (secretTasks.length) {
      await Promise.all(secretTasks)
    }

    if (newAccount.game_ids.length) {
      await apiPut(
        `/accounts/${created.account_id}/games`,
        { game_ids: newAccount.game_ids },
        { token: auth.state.token }
      )
    }

    accountsOk.value = `Аккаунт ${newAccount.login_name}@${newAccount.domain_code} создан`
    newAccount.login_name = ''
    newAccount.domain_code = ''
    newAccount.region_code = ''
    newAccount.notes = ''
    newAccount.account_date = ''
    newAccount.email_password = ''
    newAccount.account_password = ''
    newAccount.reserve_text = ''
    newAccount.auth_code = ''
    newAccount.game_ids = []
    accountGameSearch.value = ''
    await loadAccounts()
    await loadAccountsAll()
    cancelEditAccount()
  } catch (e) {
    accountsError.value = mapApiError(e?.message)
  } finally {
    accountsLoading.value = false
  }
}

async function updateAccount() {
  accountsError.value = null
  accountsOk.value = null
  if (!editAccount.account_id) return
  if (!editAccount.login_name || !editAccount.domain_code) {
    accountsError.value = 'Укажите логин и домен'
    return
  }
  accountSaving.value = true
  try {
    await apiPut(
      `/accounts/${editAccount.account_id}`,
      {
        region_code: editAccount.region_code || null,
        login_name: editAccount.login_name || null,
        domain_code: editAccount.domain_code || null,
        notes: editAccount.notes || null,
        account_date: editAccount.account_date || null,
        status_code: editAccount.status_code || 'active',
      },
      { token: auth.state.token }
    )

    const secretTasks = []
    if (editAccount.email_password) {
      secretTasks.push(
        apiPost(
          `/accounts/${editAccount.account_id}/secrets`,
          { secret_key: editAccount.email_key || 'email_password', secret_value: editAccount.email_password },
          { token: auth.state.token }
        )
      )
    } else if (editAccount.has_email) {
      secretTasks.push(
        apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.email_key || 'email_password'}`, {
          token: auth.state.token,
        })
      )
    }

    if (editAccount.account_password) {
      secretTasks.push(
        apiPost(
          `/accounts/${editAccount.account_id}/secrets`,
          { secret_key: editAccount.account_key || 'account_password', secret_value: editAccount.account_password },
          { token: auth.state.token }
        )
      )
    } else if (editAccount.has_account) {
      secretTasks.push(
        apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.account_key || 'account_password'}`, {
          token: auth.state.token,
        })
      )
    }

    if (editAccount.auth_code) {
      secretTasks.push(
        apiPost(
          `/accounts/${editAccount.account_id}/secrets`,
          { secret_key: editAccount.auth_key || 'auth_code', secret_value: editAccount.auth_code },
          { token: auth.state.token }
        )
      )
    } else if (editAccount.has_auth) {
      secretTasks.push(
        apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.auth_key || 'auth_code'}`, {
          token: auth.state.token,
        })
      )
    }

    const reserveValues = (editAccount.reserve_text || '')
      .split(/\s+/)
      .map((v) => v.trim())
      .filter(Boolean)
    const keepKeys = []
    reserveValues.forEach((val, idx) => {
      const key = `reserve${idx + 1}`
      keepKeys.push(key)
      secretTasks.push(
        apiPost(
          `/accounts/${editAccount.account_id}/secrets`,
          { secret_key: key, secret_value: val },
          { token: auth.state.token }
        )
      )
    })
    editAccount.existing_reserve_keys
      .filter((k) => !keepKeys.includes(k))
      .forEach((k) => {
        secretTasks.push(apiDelete(`/accounts/${editAccount.account_id}/secrets/${k}`, { token: auth.state.token }))
      })

    if (secretTasks.length) {
      await Promise.all(secretTasks)
    }

    await apiPut(
      `/accounts/${editAccount.account_id}/games`,
      { game_ids: editAccount.game_ids || [] },
      { token: auth.state.token }
    )

    accountsOk.value = 'Аккаунт обновлён'
    await loadAccounts()
    await loadAccountsAll()
    cancelEditAccount()
  } catch (e) {
    accountsError.value = mapApiError(e?.message)
  } finally {
    accountSaving.value = false
  }
}

async function createUser() {
  userError.value = null
  userOk.value = null
  if (!newUser.username || !newUser.password) {
    userError.value = 'Заполните логин и пароль'
    return
  }
  userLoading.value = true
  try {
    await apiPost('/users', newUser, { token: auth.state.token })
    userOk.value = `Пользователь ${newUser.username} создан`
    newUser.username = ''
    newUser.password = ''
    await loadUsers()
    closeUserModal()
  } catch (e) {
    userError.value = mapApiError(e?.message)
  } finally {
    userLoading.value = false
  }
}

function openUserModal() {
  resetModalPos()
  showUserForm.value = true
  userError.value = null
  userOk.value = null
}

function closeUserModal() {
  showUserForm.value = false
  userError.value = null
  userOk.value = null
  newUser.username = ''
  newUser.password = ''
}

async function changePassword() {
  pwdError.value = null
  pwdOk.value = false
  if (!pwdForm.current || !pwdForm.next || !pwdForm.next2) {
    pwdError.value = 'Заполните все поля'
    return
  }
  if (pwdForm.next !== pwdForm.next2) {
    pwdError.value = 'Пароли не совпадают'
    return
  }
  pwdLoading.value = true
  try {
    await apiPost(
      '/auth/change-password',
      { current_password: pwdForm.current, new_password: pwdForm.next },
      { token: auth.state.token }
    )
    pwdOk.value = true
    pwdForm.current = ''
    pwdForm.next = ''
    pwdForm.next2 = ''
  } catch (e) {
    pwdError.value = mapApiError(e?.message)
  } finally {
    pwdLoading.value = false
  }
}

function openPwdModal() {
  resetModalPos()
  showPwdForm.value = true
  pwdError.value = null
  pwdOk.value = false
}

function closePwdModal() {
  showPwdForm.value = false
  pwdError.value = null
  pwdOk.value = false
  pwdForm.current = ''
  pwdForm.next = ''
  pwdForm.next2 = ''
}

async function createGame() {
  gameError.value = null
  gameOk.value = null
  if (!newGame.title) {
    gameError.value = 'Укажите название игры'
    return
  }
  gameLoading.value = true
  gameSaving.value = true
  try {
    await apiPost(
      '/games',
      {
        title: newGame.title,
        short_title: newGame.short_title || null,
        link: newGame.link || null,
        logo_url: newGame.logo_url || null,
        text_lang: newGame.text_lang || null,
        audio_lang: newGame.audio_lang || null,
        vr_support: newGame.vr_support || null,
        platform_codes: newGame.platform_codes || [],
        region_code: newGame.region_code || null,
      },
      { token: auth.state.token }
    )
    gameOk.value = `Игра “${newGame.title}” добавлена`
    newGame.title = ''
    newGame.short_title = ''
    newGame.link = ''
    newGame.logo_url = ''
    newGame.text_lang = ''
    newGame.audio_lang = ''
    newGame.vr_support = ''
    newGame.platform_codes = []
    newGame.region_code = ''
    await loadGames()
    await loadGamesAll()
    closeGameModal()
  } catch (e) {
    gameError.value = mapApiError(e?.message)
  } finally {
    gameLoading.value = false
    gameSaving.value = false
  }
}

async function updateGame() {
  gameError.value = null
  gameOk.value = null
  if (!editGame.game_id) return
  if (!editGame.title) {
    gameError.value = 'Укажите название игры'
    return
  }
  gameLoading.value = true
  gameSaving.value = true
  try {
    await apiPut(
      `/games/${editGame.game_id}`,
      {
        title: editGame.title,
        short_title: editGame.short_title || null,
        link: editGame.link || null,
        logo_url: editGame.logo_url || null,
        text_lang: editGame.text_lang || null,
        audio_lang: editGame.audio_lang || null,
        vr_support: editGame.vr_support || null,
        platform_codes: editGame.platform_codes || [],
        region_code: editGame.region_code || null,
      },
      { token: auth.state.token }
    )
    gameOk.value = 'Игра обновлена'
    await loadGames()
    await loadGamesAll()
    cancelEditGame()
  } catch (e) {
    gameError.value = mapApiError(e?.message)
  } finally {
    gameLoading.value = false
    gameSaving.value = false
  }
}

async function createDeal() {
  dealError.value = null
  dealOk.value = null
  if (!newDeal.customer_nickname) {
    dealError.value = 'Укажите пользователя'
    return
  }
  if (newDeal.deal_type_code === 'rental') {
    if (!newDeal.account_id || !newDeal.game_id) {
      dealError.value = 'Для шеринга укажите аккаунт и игру'
      return
    }
    if (!newDeal.slot_type_code) {
      dealError.value = 'Для шеринга выберите тип слота'
      return
    }
  }
  if (newDeal.deal_type_code === 'sale' && !newDeal.region_code) {
    dealError.value = 'Для продажи укажите регион'
    return
  }
  dealLoading.value = true
  dealSaving.value = true
  try {
    await apiPost(
      '/deals',
      {
        deal_type_code: newDeal.deal_type_code,
        account_id: newDeal.deal_type_code === 'rental' ? newDeal.account_id : null,
        game_id: newDeal.deal_type_code === 'rental' ? newDeal.game_id : null,
        customer_nickname: newDeal.customer_nickname,
        source_code: newDeal.source_code || null,
        region_code: newDeal.region_code || null,
        slot_type_code: newDeal.deal_type_code === 'rental' ? (newDeal.slot_type_code || null) : null,
        price: newDeal.price || 0,
        purchase_cost: newDeal.purchase_cost || 0,
        game_link: newDeal.game_link || null,
        purchase_at: newDeal.deal_type_code === 'sale' ? null : (newDeal.purchase_at ? `${newDeal.purchase_at}T00:00:00Z` : null),
        slots_used: newDeal.deal_type_code === 'rental' ? 1 : 0,
        notes: newDeal.notes || null,
      },
      { token: auth.state.token }
    )
    dealOk.value = 'Сделка сохранена'
    newDeal.customer_nickname = ''
    newDeal.price = 0
    newDeal.purchase_cost = 0
    newDeal.game_link = ''
    newDeal.purchase_at = ''
    newDeal.notes = ''
    await loadDeals(1)
    await loadAccountsAll()
    closeDealModal()
  } catch (e) {
    dealError.value = mapApiError(e?.message)
  } finally {
    dealLoading.value = false
    dealSaving.value = false
  }
}

async function updateDeal() {
  dealError.value = null
  dealOk.value = null
  if (!editDeal.deal_id) return
  if (!editDeal.customer_nickname) {
    dealError.value = 'Укажите пользователя'
    return
  }
  if (editDeal.deal_type_code === 'rental') {
    if (!editDeal.account_id || !editDeal.game_id) {
      dealError.value = 'Для шеринга укажите аккаунт и игру'
      return
    }
    if (!editDeal.slot_type_code) {
      dealError.value = 'Для шеринга выберите тип слота'
      return
    }
  }
  if (editDeal.deal_type_code === 'sale' && !editDeal.region_code) {
    dealError.value = 'Для продажи укажите регион'
    return
  }
  dealLoading.value = true
  dealSaving.value = true
  try {
    await apiPut(
      `/deals/${editDeal.deal_id}`,
      {
        deal_type_code: editDeal.deal_type_code,
        account_id: editDeal.deal_type_code === 'rental' ? editDeal.account_id : null,
        game_id: editDeal.deal_type_code === 'rental' ? editDeal.game_id : null,
        customer_nickname: editDeal.customer_nickname,
        source_code: editDeal.source_code || null,
        region_code: editDeal.region_code || null,
        slot_type_code: editDeal.deal_type_code === 'rental' ? (editDeal.slot_type_code || null) : null,
        price: editDeal.price,
        purchase_cost: editDeal.purchase_cost || 0,
        game_link: editDeal.game_link || null,
        purchase_at: editDeal.deal_type_code === 'sale' ? null : (editDeal.purchase_at || null),
        slots_used: editDeal.deal_type_code === 'rental' ? 1 : 0,
        notes: editDeal.notes || null,
        flow_status_code: editDeal.flow_status_code || null,
      },
      { token: auth.state.token }
    )
    dealOk.value = 'Сделка обновлена'
    await loadDeals(dealPage.value)
    await loadAccountsAll()
    closeDealModal()
  } catch (e) {
    dealError.value = mapApiError(e?.message)
  } finally {
    dealLoading.value = false
    dealSaving.value = false
  }
}

async function markDealCompleted(deal) {
  if (!deal?.deal_id) return
  dealError.value = null
  dealOk.value = null
  dealSaving.value = true
  try {
    await apiPut(
      `/deals/${deal.deal_id}`,
      { flow_status_code: 'completed' },
      { token: auth.state.token }
    )
    await loadDeals(dealPage.value)
  } catch (e) {
    dealError.value = mapApiError(e?.message)
  } finally {
    dealSaving.value = false
  }
}

async function loadDeals(page = 1) {
  dealListError.value = null
  dealListLoading.value = true
  try {
    const params = new URLSearchParams()
    if (dealFilters.search_q) params.set('q', dealFilters.search_q)
    if (dealFilters.type_q) params.set('type_q', dealFilters.type_q)
    if (dealFilters.customer_q) params.set('customer_q', dealFilters.customer_q)
    if (dealFilters.region_q) params.set('region_q', dealFilters.region_q)
    if (dealFilters.status_q) {
      params.set('flow_status_q', dealFilters.status_q)
    } else if (dealShowCompleted.value) {
      params.set('flow_status_q', 'completed')
    } else {
      params.set('flow_status_q', 'pending')
    }
    if (dealFilters.purchase_from) params.set('purchase_from', dealFilters.purchase_from)
    if (dealFilters.purchase_to) params.set('purchase_to', dealFilters.purchase_to)
    params.set('page', String(page))
    params.set('page_size', String(dealPageSize.value))
    const res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
    dealItems.value = res?.items || []
    dealTotal.value = res?.total || 0
    dealPage.value = page
  } catch (e) {
    dealListError.value = mapApiError(e?.message)
  } finally {
    dealListLoading.value = false
  }
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function openEditDomain(d) {
  resetModalPos()
  showDomainForm.value = false
  editDomain.open = true
  editDomain.name = d.name
  editDomain.original = d.name
}

function applyDealSearch() {
  loadDeals(1)
}

function applyAccountSearch() {
  accountsPage.value = 1
  accountsPageInput.value = 1
  loadAccounts()
}

function applyGameSearch() {
  gamesPage.value = 1
  gamesPageInput.value = 1
  loadGames()
}

async function createQuickGame(target) {
  const isEdit = target === 'edit'
  const state = isEdit ? quickEditGame : quickNewGame
  const loading = isEdit ? quickEditGameLoading : quickNewGameLoading
  const error = isEdit ? quickEditGameError : quickNewGameError
  error.value = ''
  if (!state.title) {
    error.value = 'Укажите название игры'
    return
  }
  if (!state.platform_codes.length) {
    error.value = 'Выберите платформу'
    return
  }
  loading.value = true
  try {
    const created = await apiPost(
      '/games',
      {
        title: state.title,
        platform_codes: state.platform_codes,
        short_title: null,
        link: null,
        logo_url: null,
        text_lang: null,
        audio_lang: null,
        vr_support: null,
        region_code: null,
      },
      { token: auth.state.token }
    )
    await loadGamesAll()
    if (created?.game_id) {
      if (isEdit) {
        editDeal.game_id = created.game_id
        editDealGameSearch.value = ''
      } else {
        newDeal.game_id = created.game_id
        newDealGameSearch.value = ''
      }
    }
    state.title = ''
    state.platform_codes = []
  } catch (e) {
    error.value = mapApiError(e?.message)
  } finally {
    loading.value = false
  }
}

async function createQuickAccount(target) {
  const isEdit = target === 'edit'
  const state = isEdit ? quickEditAccount : quickNewAccount
  const loading = isEdit ? quickEditAccountLoading : quickNewAccountLoading
  const error = isEdit ? quickEditAccountError : quickNewAccountError
  error.value = ''
  if (!state.login_name) {
    error.value = 'Укажите логин'
    return
  }
  if (!state.domain_code) {
    error.value = 'Выберите домен'
    return
  }
  if (!state.platform_codes.length) {
    error.value = 'Выберите платформу'
    return
  }
  loading.value = true
  try {
    const created = await apiPost(
      '/accounts',
      {
        login_name: state.login_name,
        domain_code: state.domain_code,
        region_code: isEdit ? editDeal.region_code || null : newDeal.region_code || null,
        account_date: null,
        notes: null,
      },
      { token: auth.state.token }
    )
    await loadAccountsAll()
    const selectedGameId = isEdit ? editDeal.game_id : newDeal.game_id
    if (created?.account_id && selectedGameId) {
      try {
        const existing = await apiGet(`/accounts/${created.account_id}/games`, { token: auth.state.token })
        const ids = new Set((existing || []).map((g) => g.game_id))
        ids.add(selectedGameId)
        await apiPut(
          `/accounts/${created.account_id}/games`,
          { game_ids: Array.from(ids) },
          { token: auth.state.token }
        )
      } catch {
        // ignore game attachment errors
      }
    }
    if (created?.account_id) {
      if (isEdit) {
        editDeal.account_id = created.account_id
      } else {
        newDeal.account_id = created.account_id
      }
    }
    if (created?.account_id) {
      const targetList = isEdit ? dealAccountsForGameEdit : dealAccountsForGameNew
      const exists = (targetList.value || []).some((a) => a.account_id === created.account_id)
      if (!exists) {
        const fallback = (accountsAll.value || []).find((a) => a.account_id === created.account_id) || created
        targetList.value = [fallback, ...(targetList.value || [])]
      }
      if (isEdit) {
        dealGameAssignmentsEdit.value = []
      } else {
        dealGameAssignmentsNew.value = []
      }
    }
    if (isEdit) {
      await loadDealSlotAvailability('edit')
      await loadDealAccountsForGame('edit')
    } else {
      await loadDealSlotAvailability('new')
      await loadDealAccountsForGame('new')
    }
    state.login_name = ''
    state.domain_code = ''
    state.platform_codes = []
  } catch (e) {
    error.value = mapApiError(e?.message)
  } finally {
    loading.value = false
  }
}

function syncNewDealGameSearch() {
  newDealGameSearch.value = ''
}

function syncEditDealGameSearch() {
  editDealGameSearch.value = ''
}

function clearNewDealGame() {
  newDeal.game_id = ''
  newDealGameSearch.value = ''
  dealAccountsForGameNew.value = []
}

function clearEditDealGame() {
  editDeal.game_id = ''
  editDealGameSearch.value = ''
  dealAccountsForGameEdit.value = []
}


async function loadDealAccountsForGame(target) {
  const isEdit = target === 'edit'
  const gameId = isEdit ? editDeal.game_id : newDeal.game_id
  const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
  if (!gameId) {
    if (isEdit) dealAccountsForGameEdit.value = []
    else dealAccountsForGameNew.value = []
    return
  }
  if (!slotTypeCode) {
    if (isEdit) dealAccountsForGameEdit.value = []
    else dealAccountsForGameNew.value = []
    return
  }
  if (!isSlotTypeSupportedForGame(slotTypeCode, gameId)) {
    if (isEdit) dealAccountsForGameEdit.value = []
    else dealAccountsForGameNew.value = []
    return
  }
  dealAccountsForGameLoading.value = true
  try {
    const params = new URLSearchParams()
    params.set('game_id', String(gameId))
    if (slotTypeCode) params.set('slot_type_code', slotTypeCode)
    const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
    if (isEdit) {
      let list = data || []
      const currentId = editDeal.account_id
      if (currentId && !list.find((a) => a.account_id === currentId)) {
        const fallback = (accountsAll.value || []).find((a) => a.account_id === currentId)
        if (fallback) list = [fallback, ...list]
      }
      dealAccountsForGameEdit.value = list
    } else {
      dealAccountsForGameNew.value = data || []
    }
  } catch {
    if (isEdit) dealAccountsForGameEdit.value = []
    else dealAccountsForGameNew.value = []
  } finally {
    dealAccountsForGameLoading.value = false
  }
}

async function loadAccountSlotStatus(target) {
  const isEdit = target === 'edit'
  const accountId = isEdit ? editDeal.account_id : newDeal.account_id
  if (!accountId) {
    if (isEdit) accountSlotStatusEdit.value = []
    else accountSlotStatusNew.value = []
    return
  }
  try {
    const data = await apiGet(`/accounts/${accountId}/slot-status`, { token: auth.state.token })
    if (isEdit) accountSlotStatusEdit.value = data || []
    else accountSlotStatusNew.value = data || []
  } catch {
    if (isEdit) accountSlotStatusEdit.value = []
    else accountSlotStatusNew.value = []
  }
}

async function loadDealAccountAssignments(target) {
  const isEdit = target === 'edit'
  const accountId = isEdit ? editDeal.account_id : newDeal.account_id
  if (!accountId) {
    if (isEdit) dealAccountAssignmentsEdit.value = []
    else dealAccountAssignmentsNew.value = []
    return
  }
  const loading = isEdit ? dealAccountAssignmentsLoadingEdit : dealAccountAssignmentsLoadingNew
  loading.value = true
  try {
    const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
    if (isEdit) dealAccountAssignmentsEdit.value = data || []
    else dealAccountAssignmentsNew.value = data || []
  } catch {
    if (isEdit) dealAccountAssignmentsEdit.value = []
    else dealAccountAssignmentsNew.value = []
  } finally {
    loading.value = false
  }
}

async function loadAccountSlotAssignments(accountId) {
  if (!accountId) {
    accountSlotAssignments.value = []
    return
  }
  accountSlotAssignmentsLoading.value = true
  accountSlotAssignmentsError.value = null
  try {
    const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
    accountSlotAssignments.value = data || []
  } catch (e) {
    accountSlotAssignmentsError.value = mapApiError(e?.message)
    accountSlotAssignments.value = []
  } finally {
    accountSlotAssignmentsLoading.value = false
  }
}

async function loadGameSlotAssignments(gameId) {
  if (!gameId) {
    gameSlotAssignments.value = []
    return
  }
  gameSlotAssignmentsLoading.value = true
  gameSlotAssignmentsError.value = null
  try {
    const data = await apiGet(`/games/${gameId}/slot-assignments`, { token: auth.state.token })
    gameSlotAssignments.value = data || []
  } catch (e) {
    gameSlotAssignmentsError.value = mapApiError(e?.message)
    gameSlotAssignments.value = []
  } finally {
    gameSlotAssignmentsLoading.value = false
  }
}

async function loadDealGameAssignments(target) {
  const isEdit = target === 'edit'
  const gameId = isEdit ? editDeal.game_id : newDeal.game_id
  if (!gameId) {
    if (isEdit) dealGameAssignmentsEdit.value = []
    else dealGameAssignmentsNew.value = []
    return
  }
  const loading = isEdit ? dealGameAssignmentsLoadingEdit : dealGameAssignmentsLoadingNew
  loading.value = true
  try {
    const data = await apiGet(`/games/${gameId}/slot-assignments`, { token: auth.state.token })
    if (isEdit) dealGameAssignmentsEdit.value = data || []
    else dealGameAssignmentsNew.value = data || []
  } catch {
    if (isEdit) dealGameAssignmentsEdit.value = []
    else dealGameAssignmentsNew.value = []
  } finally {
    loading.value = false
  }
}

async function loadDealSlotAvailability(target) {
  const isEdit = target === 'edit'
  const gameId = isEdit ? editDeal.game_id : newDeal.game_id
  if (!gameId) {
    if (isEdit) dealSlotAvailabilityEdit.value = {}
    else dealSlotAvailabilityNew.value = {}
    return
  }
  const loading = isEdit ? dealSlotAvailabilityLoadingEdit : dealSlotAvailabilityLoadingNew
  loading.value = true
  try {
    const platforms = getGamePlatformCodes(gameId)
    const list = slotTypes.value || []
    const results = await Promise.all(
      list.map(async (t) => {
        const supported = !platforms.length || platforms.includes(String(t.platform_code || '').toLowerCase())
        if (!supported) {
          return [t.code, { hasFree: false }]
        }
        try {
          const params = new URLSearchParams()
          params.set('game_id', String(gameId))
          params.set('slot_type_code', t.code)
          const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
          return [t.code, { hasFree: Array.isArray(data) && data.length > 0 }]
        } catch {
          return [t.code, { hasFree: false }]
        }
      })
    )
    const map = Object.fromEntries(results)
    if (isEdit) dealSlotAvailabilityEdit.value = map
    else dealSlotAvailabilityNew.value = map
  } finally {
    loading.value = false
  }
}

async function releaseSlotAssignment(assignmentId) {
  if (!assignmentId) return
  if (!window.confirm('Снять слот у пользователя?')) return
  accountSlotReleaseLoading.value = true
  try {
    await apiPost(`/slot-assignments/${assignmentId}/release`, {}, { token: auth.state.token })
    if (editAccount.open && editAccount.account_id) {
      await loadAccountSlotAssignments(editAccount.account_id)
    }
    if (editDeal.open && editDeal.account_id) {
      await loadAccountSlotStatus('edit')
      await loadDealAccountAssignments('edit')
      await loadDealAccountsForGame('edit')
    }
    if (showDealForm.value && newDeal.account_id) {
      await loadAccountSlotStatus('new')
      await loadDealAccountAssignments('new')
      await loadDealAccountsForGame('new')
    }
    if (editDeal.open) {
      await loadDealGameAssignments('edit')
    }
    if (showDealForm.value) {
      await loadDealGameAssignments('new')
    }
  } catch (e) {
    dealError.value = mapApiError(e?.message)
  } finally {
    accountSlotReleaseLoading.value = false
  }
}

async function releaseSlotFromDeal(item, target) {
  if (!item?.assignment_id) return
  if (!window.confirm('Снять слот у пользователя?')) return
  accountSlotReleaseLoading.value = true
  try {
    await apiPost(`/slot-assignments/${item.assignment_id}/release`, {}, { token: auth.state.token })
    const accountId = item.account_id
    const slotTypeCode = item.slot_type_code
    dealSlotAutoAssign.value = true
    if (target === 'edit') {
      editDeal.account_id = accountId || ''
      editDeal.slot_type_code = slotTypeCode || ''
      await loadAccountSlotStatus('edit')
      await loadDealAccountAssignments('edit')
      await loadDealAccountsForGame('edit')
      await loadDealGameAssignments('edit')
      await loadDealSlotAvailability('edit')
    } else {
      newDeal.account_id = accountId || ''
      newDeal.slot_type_code = slotTypeCode || ''
      await loadAccountSlotStatus('new')
      await loadDealAccountAssignments('new')
      await loadDealAccountsForGame('new')
      await loadDealGameAssignments('new')
      await loadDealSlotAvailability('new')
    }
  } catch (e) {
    dealError.value = mapApiError(e?.message)
  } finally {
    dealSlotAutoAssign.value = false
    accountSlotReleaseLoading.value = false
  }
}

function onNewDealGameSearch() {
  if (newDeal.game_id) newDeal.game_id = ''
  quickNewGameError.value = ''
  if (newDealGameSearch.value) quickNewGame.title = newDealGameSearch.value
}

function onEditDealGameSearch() {
  if (editDeal.game_id) editDeal.game_id = ''
  quickEditGameError.value = ''
  if (editDealGameSearch.value) quickEditGame.title = editDealGameSearch.value
}


function cancelEditDomain() {
  editDomain.open = false
  editDomain.name = ''
  editDomain.original = ''
}

function openDomainModal() {
  resetModalPos()
  showDomainForm.value = true
  cancelEditDomain()
  catalogsError.value = null
  catalogsOk.value = null
}

function closeDomainModal() {
  showDomainForm.value = false
  cancelEditDomain()
  catalogsError.value = null
  catalogsOk.value = null
  newDomain.value = ''
}

async function saveEditDomain() {
  if (!editDomain.name) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPut(`/domains/${encodeURIComponent(editDomain.original)}`, { name: editDomain.name }, { token: auth.state.token })
    catalogsOk.value = `Домен обновлён`
    await loadDomains()
    closeDomainModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

function openEditSource(s) {
  resetModalPos()
  showSourceForm.value = false
  editSource.open = true
  editSource.code = s.code
  editSource.name = s.name
}

function cancelEditSource() {
  editSource.open = false
  editSource.code = ''
  editSource.name = ''
}

function openSourceModal() {
  resetModalPos()
  showSourceForm.value = true
  cancelEditSource()
  catalogsError.value = null
  catalogsOk.value = null
}

function closeSourceModal() {
  showSourceForm.value = false
  cancelEditSource()
  catalogsError.value = null
  catalogsOk.value = null
  newSource.code = ''
  newSource.name = ''
}

async function saveEditSource() {
  if (!editSource.code || !editSource.name) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPut(`/sources/${encodeURIComponent(editSource.code)}`, { name: editSource.name }, { token: auth.state.token })
    catalogsOk.value = `Источник обновлён`
    await loadSources()
    closeSourceModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

function openEditPlatform(p) {
  resetModalPos()
  showPlatformForm.value = false
  editPlatform.open = true
  editPlatform.code = p.code
  editPlatform.name = p.name
  editPlatform.slot_capacity = p.slot_capacity || 0
}

function cancelEditPlatform() {
  editPlatform.open = false
  editPlatform.code = ''
  editPlatform.name = ''
  editPlatform.slot_capacity = 0
}

function openPlatformModal() {
  resetModalPos()
  showPlatformForm.value = true
  cancelEditPlatform()
  catalogsError.value = null
  catalogsOk.value = null
}

function closePlatformModal() {
  showPlatformForm.value = false
  cancelEditPlatform()
  catalogsError.value = null
  catalogsOk.value = null
  newPlatform.code = ''
  newPlatform.name = ''
  newPlatform.slot_capacity = 0
}

async function saveEditPlatform() {
  if (!editPlatform.code || !editPlatform.name) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPut(
      `/platforms/${encodeURIComponent(editPlatform.code)}`,
      { name: editPlatform.name, slot_capacity: editPlatform.slot_capacity },
      { token: auth.state.token }
    )
    catalogsOk.value = `Платформа обновлена`
    await loadCatalogs()
    closePlatformModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

function openEditRegion(r) {
  resetModalPos()
  showRegionForm.value = false
  editRegion.open = true
  editRegion.code = r.code
  editRegion.name = r.name
}

function cancelEditRegion() {
  editRegion.open = false
  editRegion.code = ''
  editRegion.name = ''
}

function openRegionModal() {
  resetModalPos()
  showRegionForm.value = true
  cancelEditRegion()
  catalogsError.value = null
  catalogsOk.value = null
}

function closeRegionModal() {
  showRegionForm.value = false
  cancelEditRegion()
  catalogsError.value = null
  catalogsOk.value = null
  newRegion.code = ''
  newRegion.name = ''
}

async function saveEditRegion() {
  if (!editRegion.code || !editRegion.name) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPut(`/regions/${encodeURIComponent(editRegion.code)}`, { name: editRegion.name }, { token: auth.state.token })
    catalogsOk.value = `Регион обновлён`
    await loadCatalogs()
    closeRegionModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function createDomain() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newDomain.value) {
    catalogsError.value = 'Введите домен'
    return
  }
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPost('/domains', { name: newDomain.value }, { token: auth.state.token })
    catalogsOk.value = `Домен ${newDomain.value} добавлен`
    newDomain.value = ''
    await loadDomains()
    closeDomainModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function createSource() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newSource.code || !newSource.name) {
    catalogsError.value = 'Введите код и название источника'
    return
  }
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPost('/sources', newSource, { token: auth.state.token })
    catalogsOk.value = `Источник ${newSource.code} добавлен`
    newSource.code = ''
    newSource.name = ''
    await loadSources()
    closeSourceModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function createPlatform() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newPlatform.code || !newPlatform.name) {
    catalogsError.value = 'Введите код и название платформы'
    return
  }
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPost('/platforms', newPlatform, { token: auth.state.token })
    catalogsOk.value = `Платформа ${newPlatform.code} добавлена`
    newPlatform.code = ''
    newPlatform.name = ''
    newPlatform.slot_capacity = 0
    await loadCatalogs()
    closePlatformModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function createRegion() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newRegion.code || !newRegion.name) {
    catalogsError.value = 'Введите код и название региона'
    return
  }
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiPost('/regions', newRegion, { token: auth.state.token })
    catalogsOk.value = `Регион ${newRegion.code} добавлен`
    newRegion.code = ''
    newRegion.name = ''
    await loadCatalogs()
    closeRegionModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function deleteDomain(name) {
  if (!window.confirm(`Удалить домен ${name}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiDelete(`/domains/${encodeURIComponent(name)}`, { token: auth.state.token })
    catalogsOk.value = `Домен ${name} удалён`
    await loadDomains()
    if (editDomain.open && editDomain.original === name) closeDomainModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function deleteSource(code) {
  if (!window.confirm(`Удалить источник ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiDelete(`/sources/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Источник ${code} удалён`
    await loadSources()
    if (editSource.open && editSource.code === code) closeSourceModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function deletePlatform(code) {
  if (!window.confirm(`Удалить платформу ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiDelete(`/platforms/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Платформа ${code} удалена`
    await loadCatalogs()
    if (editPlatform.open && editPlatform.code === code) closePlatformModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}

async function deleteRegion(code) {
  if (!window.confirm(`Удалить регион ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  catalogSaving.value = true
  try {
    await apiDelete(`/regions/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Регион ${code} удалён`
    await loadCatalogs()
    if (editRegion.open && editRegion.code === code) closeRegionModal()
  } catch (e) {
    catalogsError.value = mapApiError(e?.message)
  } finally {
    catalogsLoading.value = false
    catalogSaving.value = false
  }
}


function onLogout() {
  auth.logout()
  router.replace('/login')
}

onMounted(async () => {
  await auth.loadMe()
  if (isAdmin.value) {
    await loadUsers()
  }
})

watch(activeDealFilter, (val) => {
  if (val) {
    window.addEventListener('click', onDealFilterOutside)
  } else {
    window.removeEventListener('click', onDealFilterOutside)
  }
})

const onGameFilterOutside = (event) => {
  if (!activeGameFilter.value) return
  const target = event.target
  if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
  activeGameFilter.value = ''
}

watch(activeGameFilter, (val) => {
  if (val) {
    window.addEventListener('click', onGameFilterOutside)
  } else {
    window.removeEventListener('click', onGameFilterOutside)
  }
})

const onAccountFilterOutside = (event) => {
  if (!activeAccountFilter.value) return
  const target = event.target
  if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
  activeAccountFilter.value = ''
}

watch(activeAccountFilter, (val) => {
  if (val) {
    window.addEventListener('click', onAccountFilterOutside)
  } else {
    window.removeEventListener('click', onAccountFilterOutside)
  }
})

watch(activeTab, async (tab) => {
  if (tab === 'dashboard') {
    checkApi()
    return
  }
  if (tab === 'profile') {
    pwdOk.value = false
    showPwdForm.value = false
    return
  }
  if (tab === 'games') {
    if (!platforms.value.length || !regions.value.length) {
      await loadCatalogs()
    }
    gamesPage.value = 1
    if (!games.value.length) {
      await loadGames()
    }
    if (!gamesAll.value.length) {
      await loadGamesAll()
    }
    showGameForm.value = false
    showGameFilters.value = false
    activeGameFilter.value = ''
    editGame.open = false
    return
  }
  if (tab === 'accounts') {
    if (!platforms.value.length || !regions.value.length) {
      await loadCatalogs()
    }
    if (!domains.value.length) {
      await loadDomains()
    }
    if (!gamesAll.value.length) {
      await loadGamesAll()
    }
    if (!slotTypes.value.length) {
      await loadSlotTypes()
    }
    accountsPage.value = 1
    await loadAccounts()
    showAccountFilters.value = false
    activeAccountFilter.value = ''
    return
  }
  if (tab === 'deals') {
    // стартуем список сразу, остальное догружаем параллельно
    const tasks = [loadDeals(1)]
    if (!accountsAll.value.length) tasks.push(loadAccountsAll())
    if (!gamesAll.value.length) tasks.push(loadGamesAll())
    if (!platforms.value.length || !regions.value.length) tasks.push(loadCatalogs())
    if (!sources.value.length) tasks.push(loadSources())
    if (!domains.value.length) tasks.push(loadDomains())
    if (!slotTypes.value.length) tasks.push(loadSlotTypes())
    await Promise.all(tasks)
    showDealForm.value = false
    return
  }
  if (tab === 'catalogs') {
    await Promise.all([loadDomains(), loadSources(), loadCatalogs()])
    return
  }
  if (tab === 'users' && isAdmin.value) {
    await loadUsers()
    showUserForm.value = false
  }
}, { immediate: true })

watch([() => editAccount.open], async ([showEdit]) => {
  if (showEdit && !domains.value.length) {
    await loadDomains()
  }
})

watch(
  () => editAccount.open,
  (open) => {
    if (open) {
      resetModalPos()
    }
  }
)

watch(
  () => [newDeal.game_id, newDeal.slot_type_code],
  () => {
    loadDealAccountsForGame('new')
    if (newDeal.game_id) loadDealGameAssignments('new')
  }
)

watch(
  () => [editDeal.game_id, editDeal.slot_type_code],
  () => {
    if (editDeal.open) loadDealAccountsForGame('edit')
    if (editDeal.open && editDeal.game_id) loadDealGameAssignments('edit')
  }
)

watch(
  () => newDeal.account_id,
  () => {
    loadAccountSlotStatus('new')
    loadDealAccountAssignments('new')
  }
)

watch(
  () => editDeal.account_id,
  () => {
    if (editDeal.open) loadAccountSlotStatus('edit')
    if (editDeal.open) loadDealAccountAssignments('edit')
  }
)

watch(
  () => newDeal.game_id,
  (val, prev) => {
    if (val === prev) return
    newDeal.account_id = ''
    newDeal.slot_type_code = ''
    accountSlotStatusNew.value = []
    dealAccountAssignmentsNew.value = []
    dealSlotAvailabilityNew.value = {}
    loadDealSlotAvailability('new')
  }
)

watch(
  () => editDeal.game_id,
  (val, prev) => {
    if (!editDeal.open || dealInitLock.value) return
    if (val === prev) return
    editDeal.account_id = ''
    editDeal.slot_type_code = ''
    accountSlotStatusEdit.value = []
    dealAccountAssignmentsEdit.value = []
    dealSlotAvailabilityEdit.value = {}
    loadDealSlotAvailability('edit')
  }
)

watch(
  () => newDeal.account_id,
  (val) => {
    if (!val) {
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
    }
  }
)

watch(
  () => editDeal.account_id,
  (val, prev) => {
    if (!editDeal.open || dealInitLock.value) return
    if (!val) {
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
      return
    }
    if (!prev) return
    accountSlotStatusEdit.value = []
    dealAccountAssignmentsEdit.value = []
  }
)

watch(
  () => newDeal.slot_type_code,
  (val, prev) => {
    if (dealSlotAutoAssign.value || val === prev) return
    if (!val) {
      newDeal.account_id = ''
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
      return
    }
    newDeal.account_id = ''
    accountSlotStatusNew.value = []
    dealAccountAssignmentsNew.value = []
  }
)

watch(
  () => editDeal.slot_type_code,
  (val, prev) => {
    if (!editDeal.open || dealInitLock.value) return
    if (dealSlotAutoAssign.value || val === prev) return
    if (!val) {
      editDeal.account_id = ''
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
      return
    }
    editDeal.account_id = ''
    accountSlotStatusEdit.value = []
    dealAccountAssignmentsEdit.value = []
  }
)

</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,650&display=swap');

:global(:root) {
  --bg-1: #0c1024;
  --bg-2: #151b35;
  --bg-3: #0f2431;
  --accent: #3ee8b5;
  --accent-2: #f7b955;
  --ink: #eef2ff;
  --muted: rgba(238, 242, 255, 0.7);
  --card: rgba(10, 16, 32, 0.6);
  --stroke: rgba(255, 255, 255, 0.12);
  --ghost-bg: rgba(11, 15, 25, 0.08);
  --ghost-border: rgba(255, 255, 255, 0.12);
  --ghost-text: #e8eefc;
  --tab-bg: rgba(255, 255, 255, 0.06);
  --tab-border: rgba(255, 255, 255, 0.12);
  --tab-text: #c9d6ee;
  --tab-hover-bg: rgba(255, 255, 255, 0.12);
  --tab-hover-text: #f8fafc;
  --tab-active-bg: linear-gradient(135deg, rgba(62, 232, 181, 0.45), rgba(247, 185, 85, 0.3));
  --tab-active-text: #0b0f19;
  --input-bg: rgba(8, 12, 24, 0.6);
  --input-border: rgba(255, 255, 255, 0.16);
  --table-bg: rgba(255, 255, 255, 0.08);
  --table-border: rgba(255, 255, 255, 0.08);
  --modal-bg: rgba(10, 16, 32, 0.92);
  --modal-text: #eef2ff;
  --btn-bg: linear-gradient(135deg, #3ee8b5, #7df0c6);
  --btn-text: #0b0f19;
  --danger-bg: #ff6b6b;
  --glow-ring: rgba(12, 14, 24, 0.85);
}

:global(html),
:global(body) {
  font-family: 'Space Grotesk', sans-serif;
  scrollbar-gutter: stable;
}

.page {
  min-height: 100svh;
  padding:
    max(18px, env(safe-area-inset-top))
    max(18px, env(safe-area-inset-right))
    max(18px, env(safe-area-inset-bottom))
    max(18px, env(safe-area-inset-left));
  overflow-y: scroll;
  background:
    radial-gradient(900px 520px at 12% 10%, rgba(62, 232, 181, 0.16), transparent 70%),
    radial-gradient(900px 520px at 88% 12%, rgba(247, 185, 85, 0.18), transparent 70%),
    linear-gradient(135deg, var(--bg-1), var(--bg-2) 55%, var(--bg-3));
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
}

.shell {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px 18px;
  backdrop-filter: blur(12px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(62, 232, 181, 0.3), rgba(247, 185, 85, 0.3));
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-weight: 700;
  overflow: hidden;
}

.logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.title {
  font-size: 20px;
  font-weight: 700;
}

.sub {
  opacity: 0.8;
  font-size: 13px;
  margin-top: 4px;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  flex: 1;
  justify-content: flex-start;
}


.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tabs--right {
  margin-left: auto;
}

.tab {
  background: var(--tab-bg);
  border: 1px solid var(--tab-border);
  color: var(--tab-text);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
}

.tab--icon {
  width: 36px;
  height: 36px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.tab--icon svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}

.tab--danger {
  background: rgba(255, 77, 79, 0.18);
  border-color: rgba(255, 77, 79, 0.35);
  color: #ffb3b3;
}

.tab--danger:hover {
  background: rgba(255, 77, 79, 0.32);
  color: #ffe5e5;
}

.tab:hover {
  background: var(--tab-hover-bg);
  color: var(--tab-hover-text);
}

.tab.active {
  background: var(--tab-active-bg);
  border-color: var(--stroke);
  color: var(--tab-active-text);
}

button {
  padding: 10px 14px;
  border-radius: 12px;
  border: 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}

.ghost {
  background: var(--ghost-bg);
  border: 1px solid var(--ghost-border);
  color: var(--ghost-text);
}

.ghost:hover {
  background: var(--tab-hover-bg);
  color: var(--tab-hover-text);
}

.ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.danger {
  background: var(--danger-bg);
  color: #fff;
  box-shadow: 0 8px 16px rgba(255, 93, 93, 0.35);
  border: 1px solid rgba(255, 77, 79, 0.4);
}

.danger:hover {
  filter: brightness(0.98);
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
}

.hero__title {
  margin: 0 0 8px;
  font-family: 'Fraunces', serif;
  font-size: clamp(22px, 4.2vw, 32px);
}

.hero__text {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.hero__cards {
  display: grid;
  gap: 12px;
  min-width: 200px;
}

.mini {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(10, 16, 32, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mini__label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--muted);
}

.mini__value {
  margin-top: 6px;
  font-weight: 700;
  font-size: 18px;
}

.main {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.panel {
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(10px);
}

.panel--wide {
  min-height: 0;
  grid-column: auto;
}

.panel--wide {
  min-height: 72svh;
  overflow-x: auto;
}

.panel__toggle {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  color: var(--ink);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}

.panel__body {
  margin-top: 10px;
}

.chev {
  display: inline-flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: transform 0.2s ease;
}

.chev.open {
  transform: rotate(180deg);
}

.panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel__head--tight {
  margin-bottom: 6px;
}

h2 {
  margin: 0 0 8px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.85;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 12px;
}

.catalog {
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.catalog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.divider {
  height: 1px;
  width: 100%;
  background: rgba(255, 255, 255, 0.08);
  margin: 12px 0;
}

.loader-wrap {
  display: grid;
  place-items: center;
  gap: 6px;
  padding: 10px 0;
}

.loader-wrap .muted {
  margin-top: -22px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(6, 10, 18, 0.45);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 50;
  padding: 24px 18px;
  overflow: auto;
}

.loader-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  isolation: isolate;
}

.loader-overlay::before {
  content: "";
  position: absolute;
  inset: 0;
  background: rgba(6, 10, 18, 0.6);
  backdrop-filter: blur(8px);
  z-index: 0;
}

.loader-overlay .wheel-and-hamster,
.loader-overlay .muted {
  position: relative;
  z-index: 1;
  filter: none;
}

.loader-overlay .container_SevMini {
  position: relative;
  z-index: 1;
}

.loader-overlay .wheel-and-hamster {
  flex: 0 0 auto;
  clip-path: circle(50% at 50% 50%);
}

.loader-overlay .muted {
  margin: 0;
  transform: none;
}

.modal {
  width: min(980px, 96vw);
  height: min(92vh, 820px);
  overflow: hidden;
  background: var(--modal-bg, rgba(10, 16, 32, 0.92));
  color: var(--modal-text, #eef2ff);
  border: 1px solid var(--stroke);
  border-radius: 20px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  font-family: inherit;
  box-shadow:
    0 24px 60px rgba(0, 0, 0, 0.35),
    0 6px 18px rgba(0, 0, 0, 0.25);
}

.modal input,
.modal select,
.modal textarea,
.modal button {
  font-family: inherit;
}

.modal--auto {
  height: auto;
  max-height: min(90vh, 720px);
}

.modal--auto .modal__body {
  max-height: min(74vh, 560px);
}

.modal--full {
  height: min(92vh, 880px);
}

.modal--full .modal__body {
  max-height: min(78vh, 680px);
}

.modal .label {
  color: var(--muted);
}

.modal .muted {
  color: var(--muted);
}

.modal .input {
  background: var(--input-bg);
  color: var(--ink);
  border: 1px solid var(--input-border);
}

.modal .btn--ghost,
.modal .ghost {
  background: var(--ghost-bg);
  color: var(--ghost-text);
  border: 1px solid var(--ghost-border);
}

.modal__head {
  cursor: move;
  user-select: none;
}

.modal .panel__head {
  margin-bottom: 8px;
}

.modal__body {
  overflow: auto;
  flex: 1;
  min-height: 0;
  padding-right: 4px;
}

.modal__body--locked {
  position: relative;
  pointer-events: none;
}

.modal__body--locked .deal-form {
  opacity: 0.45;
}

.modal__body-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: grid;
  place-items: center;
  background: rgba(6, 9, 18, 0.6);
  border-radius: 12px;
  pointer-events: all;
}

.modal__body-overlay-content {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(12, 18, 32, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.btn--icon-plain {
  width: 28px;
  height: 28px;
  padding: 0;
  display: grid;
  place-items: center;
  background: var(--ghost-bg);
  color: var(--ghost-text);
  border: 1px solid var(--ghost-border);
  border-radius: 10px;
}

.btn--icon-round {
  width: 44px;
  height: 44px;
  border-radius: 999px;
}

.modal__head .btn--icon-plain {
  width: 44px;
  height: 44px;
  min-width: 44px;
  border-radius: 999px;
}

.btn--icon-plain:hover {
  background: var(--tab-hover-bg);
}

.btn--icon-plain svg {
  width: 13px;
  height: 13px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}

.spinner--small {
  width: 12px;
  height: 12px;
}

.ghost .spinner {
  margin-right: 6px;
}

.import-status {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}

.import-status:hover {
  color: var(--ink);
}

.btn--icon-plain .spinner {
  margin: 0;
}

.btn--icon-tiny {
  width: 22px;
  height: 22px;
  border-radius: 8px;
}

/* Hamster loader (Uiverse.io by Nawsome) */
.wheel-and-hamster {
  --dur: 1s;
  position: relative;
  width: 11.5em;
  height: 11.5em;
  font-size: 10px;
  overflow: visible;
}

.wheel,
.hamster,
.hamster div,
.spoke {
  position: absolute;
}

.wheel,
.spoke {
  border-radius: 50%;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.wheel {
  background: radial-gradient(100% 100% at center, hsla(0, 0%, 60%, 0) 47.8%, hsl(0, 0%, 60%) 48%);
  z-index: 2;
}

.hamster {
  animation: hamster var(--dur) ease-in-out infinite;
  top: 50%;
  left: calc(50% - 3.5em);
  width: 7em;
  height: 3.75em;
  transform: rotate(4deg) translate(-0.8em, 1.4em);
  transform-origin: 50% 0;
  z-index: 1;
}

.hamster__head {
  animation: hamsterHead var(--dur) ease-in-out infinite;
  background: hsl(30, 90%, 55%);
  border-radius: 70% 30% 0 100% / 40% 25% 25% 60%;
  box-shadow: 0 -0.25em 0 hsl(30, 90%, 80%) inset,
    0.75em -1.55em 0 hsl(30, 90%, 90%) inset;
  top: 0;
  left: -2em;
  width: 2.75em;
  height: 2.5em;
  transform-origin: 100% 50%;
}

.hamster__ear {
  animation: hamsterEar var(--dur) ease-in-out infinite;
  background: hsl(0, 90%, 85%);
  border-radius: 50%;
  box-shadow: -0.25em 0 hsl(30, 90%, 55%) inset;
  top: -0.25em;
  right: -0.25em;
  width: 0.75em;
  height: 0.75em;
  transform-origin: 50% 75%;
}

.hamster__eye {
  animation: hamsterEye var(--dur) linear infinite;
  background-color: hsl(0, 0%, 0%);
  border-radius: 50%;
  top: 0.375em;
  left: 1.25em;
  width: 0.5em;
  height: 0.5em;
}

.hamster__nose {
  background: hsl(0, 90%, 75%);
  border-radius: 35% 65% 85% 15% / 70% 50% 50% 30%;
  top: 0.75em;
  left: 0;
  width: 0.2em;
  height: 0.25em;
}

.hamster__body {
  animation: hamsterBody var(--dur) ease-in-out infinite;
  background: hsl(30, 90%, 90%);
  border-radius: 50% 30% 50% 30% / 15% 60% 40% 40%;
  box-shadow: 0.1em 0.75em 0 hsl(30, 90%, 55%) inset,
    0.15em -0.5em 0 hsl(30, 90%, 80%) inset;
  top: 0.25em;
  left: 2em;
  width: 4.5em;
  height: 3em;
  transform-origin: 17% 50%;
  transform-style: preserve-3d;
}

.hamster__limb--fr,
.hamster__limb--fl {
  clip-path: polygon(0 0, 100% 0, 70% 80%, 60% 100%, 0% 100%, 40% 80%);
  top: 2em;
  left: 0.5em;
  width: 1em;
  height: 1.5em;
  transform-origin: 50% 0;
}

.hamster__limb--fr {
  animation: hamsterFRLimb var(--dur) linear infinite;
  background: linear-gradient(hsl(30, 90%, 80%) 80%, hsl(0, 90%, 75%) 80%);
  transform: rotate(15deg) translateZ(-1px);
}

.hamster__limb--fl {
  animation: hamsterFLLimb var(--dur) linear infinite;
  background: linear-gradient(hsl(30, 90%, 90%) 80%, hsl(0, 90%, 85%) 80%);
  transform: rotate(15deg);
}

.hamster__limb--br,
.hamster__limb--bl {
  border-radius: 0.75em 0.75em 0 0;
  clip-path: polygon(0 0, 100% 0, 100% 30%, 70% 90%, 70% 100%, 30% 100%, 40% 90%, 0% 30%);
  top: 1em;
  left: 2.8em;
  width: 1.5em;
  height: 2.5em;
  transform-origin: 50% 30%;
}

.hamster__limb--br {
  animation: hamsterBRLimb var(--dur) linear infinite;
  background: linear-gradient(hsl(30, 90%, 80%) 90%, hsl(0, 90%, 75%) 90%);
  transform: rotate(-25deg) translateZ(-1px);
}

.hamster__limb--bl {
  animation: hamsterBLLimb var(--dur) linear infinite;
  background: linear-gradient(hsl(30, 90%, 90%) 90%, hsl(0, 90%, 85%) 90%);
  transform: rotate(-25deg);
}

.hamster__tail {
  animation: hamsterTail var(--dur) linear infinite;
  background: hsl(0, 90%, 85%);
  border-radius: 0.25em 50% 50% 0.25em;
  box-shadow: 0 -0.2em 0 hsl(0, 90%, 75%) inset;
  top: 1.5em;
  right: -0.5em;
  width: 1em;
  height: 0.5em;
  transform: rotate(30deg) translateZ(-1px);
  transform-origin: 0.25em 0.25em;
}

.spoke {
  animation: spoke var(--dur) linear infinite;
  background: radial-gradient(100% 100% at center, hsl(0, 0%, 60%) 4.8%, hsla(0, 0%, 60%, 0) 5%),
    linear-gradient(hsla(0, 0%, 55%, 0) 46.9%, hsl(0, 0%, 65%) 47% 52.9%, hsla(0, 0%, 65%, 0) 53%) 50% 50% / 99% 99% no-repeat;
}

@keyframes hamster {
  from, to { transform: rotate(4deg) translate(-0.8em, 1.4em); }
  50% { transform: rotate(0) translate(-0.8em, 1.4em); }
}
@keyframes hamsterHead {
  from, 25%, 50%, 75%, to { transform: rotate(0); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(8deg); }
}
@keyframes hamsterEye {
  from, 90%, to { transform: scaleY(1); }
  95% { transform: scaleY(0); }
}
@keyframes hamsterEar {
  from, 25%, 50%, 75%, to { transform: rotate(0); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(12deg); }
}
@keyframes hamsterBody {
  from, 25%, 50%, 75%, to { transform: rotate(0); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-2deg); }
}
@keyframes hamsterFRLimb {
  from, 25%, 50%, 75%, to { transform: rotate(50deg) translateZ(-1px); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-30deg) translateZ(-1px); }
}
@keyframes hamsterFLLimb {
  from, 25%, 50%, 75%, to { transform: rotate(-30deg); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(50deg); }
}
@keyframes hamsterBRLimb {
  from, 25%, 50%, 75%, to { transform: rotate(-60deg) translateZ(-1px); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(20deg) translateZ(-1px); }
}
@keyframes hamsterBLLimb {
  from, 25%, 50%, 75%, to { transform: rotate(20deg); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(-60deg); }
}
@keyframes hamsterTail {
  from, 25%, 50%, 75%, to { transform: rotate(30deg) translateZ(-1px); }
  12.5%, 37.5%, 62.5%, 87.5% { transform: rotate(10deg) translateZ(-1px); }
}
@keyframes spoke {
  from { transform: rotate(0); }
  to { transform: rotate(-1turn); }
}
@keyframes spin {
  to { transform: rotate(1turn); }
}

.list {
  margin: 0;
  padding-left: 16px;
  color: var(--ink);
}

.list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
}

.list-text {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-actions {
  display: inline-flex;
  gap: 6px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  font-size: 12px;
}

.mini-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #cfe1ff;
  border-radius: 10px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.mini-btn:hover {
  background: rgba(207, 225, 255, 0.15);
}

.mini-btn--danger {
  color: #ffb4b4;
}

.mini-btn--danger:hover {
  background: rgba(255, 180, 180, 0.15);
}

h3 {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.7;
}

.form {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.form--stack {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 10px;
}

.form--compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: end;
}

.form--compact .btn {
  min-width: 200px;
  justify-self: end;
}

.form--card {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(8, 12, 24, 0.4);
  margin-bottom: 12px;
}

.field--full {
  grid-column: 1 / -1;
}

.deal-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.deal-form__col {
  display: grid;
  gap: 10px;
  align-content: start;
}

.deal-form__full {
  grid-column: 1 / -1;
  display: grid;
  gap: 8px;
}

.quick-create {
  display: grid;
  gap: 8px;
  padding: 10px;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.2);
  background: rgba(6, 9, 18, 0.45);
}

.quick-create__title {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.quick-create__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.input-list {
  display: grid;
  gap: 8px;
}

.input-list__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.check-list {
  display: grid;
  gap: 6px;
  max-height: 200px;
  overflow: auto;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.pill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
  font-size: 12px;
}

.table--dense th,
.table--dense td {
  padding: 8px 10px;
  font-size: 12px;
}

.loader-wrap--compact {
  min-height: 120px;
  padding: 12px;
}

.wheel-and-hamster--mini {
  width: 8em;
  height: 8em;
  font-size: 10px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 10px;
}

.toolbar__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  flex: 1 1 0;
}

.toolbar__filters .field {
  min-width: 0;
}

.toolbar__filters .input {
  min-width: 0;
}

.toolbar-actions {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.switch-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-right: 6px;
}

.switch-label {
  font-size: 12px;
  color: var(--muted);
}

.switch {
  --switch-width: 46px;
  --switch-height: 24px;
  --switch-bg: rgb(131, 131, 131);
  --switch-checked-bg: rgb(0, 218, 80);
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 18px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(146, 146, 146, 0.45);
  --circle-checked-shadow: -1px 1px 2px rgba(163, 163, 163, 0.45);
  --circle-transition: var(--switch-transition);
  --icon-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: var(--switch-bg);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all 0.2s ease-in-out;
  display: inline-block;
}

.switch input {
  display: none;
}

.switch svg {
  transition: var(--icon-transition);
  position: absolute;
  height: auto;
}

.switch .checkmark {
  width: var(--icon-checkmark-size);
  color: var(--icon-checkmark-color);
  transform: scale(0);
}

.switch .cross {
  width: var(--icon-cross-size);
  color: var(--icon-cross-color);
}

.slider {
  box-sizing: border-box;
  width: var(--switch-width);
  height: var(--switch-height);
  background: var(--switch-bg);
  border-radius: 999px;
  display: flex;
  align-items: center;
  position: relative;
  transition: var(--switch-transition);
  cursor: pointer;
}

.circle {
  width: var(--circle-diameter);
  height: var(--circle-diameter);
  background: var(--circle-bg);
  border-radius: inherit;
  box-shadow: var(--circle-shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--circle-transition);
  z-index: 1;
  position: absolute;
  left: var(--switch-offset);
}

.slider::before {
  content: "";
  position: absolute;
  width: var(--effect-width);
  height: var(--effect-height);
  left: calc(var(--switch-offset) + (var(--effect-width) / 2));
  background: var(--effect-bg);
  border-radius: var(--effect-border-radius);
  transition: var(--effect-transition);
}

.switch input:checked + .slider {
  background: var(--switch-checked-bg);
}

.switch input:checked + .slider .checkmark {
  transform: scale(1);
}

.switch input:checked + .slider .cross {
  transform: scale(0);
}

.switch input:checked + .slider::before {
  left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset));
}

.switch input:checked + .slider .circle {
  left: calc(100% - var(--circle-diameter) - var(--switch-offset));
  box-shadow: var(--circle-checked-shadow);
}


.import-actions {
  position: sticky;
  bottom: 0;
  z-index: 2;
  align-self: flex-start;
  padding: 8px 0;
  background: linear-gradient(0deg, rgba(10, 16, 32, 0.95) 0%, rgba(10, 16, 32, 0.7) 70%, rgba(10, 16, 32, 0) 100%);
}

.import-actions--fixed {
  top: 0;
  bottom: auto;
  margin-bottom: 8px;
  background: linear-gradient(180deg, rgba(10, 16, 32, 0.95) 0%, rgba(10, 16, 32, 0.7) 70%, rgba(10, 16, 32, 0) 100%);
}

.field,
.input {
  box-sizing: border-box;
}

.field--compact .label {
  font-size: 11px;
}

.table--compact th,
.table--compact td {
  padding: 6px 8px;
  font-size: 11px;
}

.btn--ghost {
  background: var(--ghost-bg);
  color: var(--ghost-text);
}

.btn--icon {
  padding: 0;
  width: 28px;
  height: 28px;
  aspect-ratio: 1 / 1;
  display: grid;
  place-items: center;
}

.btn--icon svg {
  width: 13px;
  height: 13px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.btn--glow {
  border-radius: 50% !important;
  border: none;
  position: relative;
  z-index: 0;
  color: #fff;
  transition: transform 0.1s ease, filter 0.2s ease;
}

.btn--glow::before {
  content: "";
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: var(--glow-ring);
  z-index: -1;
  transition: 0.35s ease;
}

.btn--glow:hover::before {
  inset: 100%;
}

.btn--glow:active {
  transform: scale(0.9);
}

.btn--glow-add {
  background: linear-gradient(120deg, #02ff2c, #008a12);
}

.btn--glow-import {
  background: linear-gradient(120deg, #38bdf8, #2563eb);
}

.btn--glow-export {
  background: linear-gradient(120deg, #facc15, #fb7185);
}

.btn--glow-filter {
  background: linear-gradient(120deg, #3b82f6, #06b6d4);
}

.btn--glow-eye {
  background: linear-gradient(120deg, #833ab4, #fd1d1d, #fcb045);
}

.btn--glow-refresh {
  background: linear-gradient(120deg, #f97316, #ef4444);
}

.btn--glow-danger {
  background: linear-gradient(120deg, #ff6b6b, #ef4444);
}

.btn--glow svg {
  color: #fff;
  stroke: currentColor;
  fill: none;
}

.field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.label {
  font-size: 12px;
  color: var(--muted);
}

.input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--input-border);
  background: var(--input-bg);
  color: var(--ink);
  outline: none;
  font-size: 14px;
}

.input--textarea {
  height: auto;
  min-height: 120px;
  padding: 8px 12px;
  resize: vertical;
}

.input--textarea--tall {
  min-height: 180px;
}

.input--file {
  height: auto;
  padding: 8px 10px;
}

.logo-upload {
  display: grid;
  gap: 10px;
}

.logo-preview {
  width: 140px;
  height: 140px;
  border-radius: 12px;
  border: 1px solid var(--input-border);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  display: grid;
  place-items: center;
}

.logo-preview--loading {
  background: rgba(255, 255, 255, 0.06);
}

.logo-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.logo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.import-errors {
  display: grid;
  gap: 8px;
}

.form--inline .btn {
  width: 100%;
  height: 44px;
}

.input--select {
  appearance: none;
}

.ok {
  color: #3ee8b5;
  font-size: 13px;
}

table.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 12px;
  table-layout: fixed;
  border-radius: 12px;
  overflow: visible;
  background: var(--table-bg);
  box-shadow:
    inset 0 0 0 1px var(--table-border),
    0 6px 18px rgba(17, 24, 39, 0.04);
}

.table th,
.table td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--table-border);
  border-right: 1px solid var(--table-border);
  word-break: break-word;
}

.table th.cell--tight,
.table td.cell--tight {
  font-size: 11px;
  padding: 6px 8px;
  line-height: 1.2;
}

.table th.cell--account,
.table td.cell--account {
  min-width: 220px;
  width: 22%;
}

.cell--num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.cell--slots {
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
}

.cell--selectable {
  user-select: text;
  cursor: text;
}

.slot-line {
  display: block;
}

.table th:last-child,
.table td:last-child {
  border-right: 0;
}

.table th {
  background: color-mix(in srgb, var(--table-bg) 80%, transparent);
  font-weight: 600;
  color: var(--ink);
  position: relative;
  overflow: visible;
}

.th-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.th-title--filter {
  position: relative;
  display: flex;
  width: 100%;
  justify-content: space-between;
  padding-right: 4px;
}

.th-title--filter .filter-icon {
  margin-left: auto;
}

.filter-pop {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 240px;
  max-width: 320px;
  z-index: 5;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(10, 16, 32, 0.95);
  box-shadow:
    0 18px 36px rgba(0, 0, 0, 0.4),
    0 6px 16px rgba(0, 0, 0, 0.3);
  display: grid;
  gap: 10px;
}

.filter-pop .field {
  grid-template-columns: 1fr;
}

.filter-pop .input {
  height: 36px;
  font-size: 12px;
  background: rgba(6, 9, 18, 0.9);
  border-color: rgba(255, 255, 255, 0.2);
}

.filter-pop .label {
  color: rgba(238, 242, 255, 0.85);
}

.filter-results {
  display: grid;
  gap: 6px;
  max-height: 180px;
  overflow: auto;
  padding: 6px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(6, 9, 18, 0.7);
}

.filter-result {
  text-align: left;
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: var(--ink);
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.filter-result:hover {
  background: rgba(255, 255, 255, 0.16);
}

.filter-result--muted {
  background: transparent;
  color: var(--muted);
  cursor: default;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 6px 0 10px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  font-size: 12px;
}

.chip--reset {
  background: rgba(62, 232, 181, 0.16);
  border-color: rgba(62, 232, 181, 0.45);
  color: var(--ink);
  font-weight: 600;
}

.chip__label {
  color: var(--muted);
}

.chip__value {
  color: var(--ink);
}

.chip__clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  border: 0;
  background: rgba(255, 255, 255, 0.12);
  color: var(--ink);
  padding: 0;
}

.chip__clear svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}

.chip__clear:hover {
  background: rgba(255, 255, 255, 0.2);
}

.filter-pop--right {
  left: auto;
  right: 0;
}

.filter-pop--center {
  left: 50%;
  transform: translateX(-50%);
}

.ghost--small {
  height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

.filter-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: var(--ink);
  padding: 0;
}

.filter-icon--active {
  background: color-mix(in srgb, var(--accent) 25%, transparent);
  border-color: color-mix(in srgb, var(--accent) 45%, transparent);
  color: var(--accent);
  box-shadow: 0 0 0 2px rgba(62, 232, 181, 0.15);
}

.filter-icon svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}

.filter-icon:hover {
  background: rgba(255, 255, 255, 0.16);
}

.pager__size {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.pager__jump {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.input--compact {
  height: 32px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 10px;
}

.input--search {
  margin-bottom: 6px;
}

.input--search-row {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 12px;
}

.input--search-field {
  flex: 1;
  background: transparent;
  border: 0;
  color: inherit;
  outline: none;
  font-size: 12px;
  padding-right: 36px;
}

.btn--icon-clear {
  width: 24px;
  height: 24px;
  min-width: 24px;
}

.input--select-wrap {
  position: relative;
}

.btn--icon-clear--select {
  position: absolute;
  top: 8px;
  right: 8px;
}

.input--list {
  height: auto;
  min-height: 180px;
}

.input--page {
  width: 70px;
  text-align: center;
}

.table tr:last-child td {
  border-bottom: 0;
}

.table tbody tr:hover td {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
}

.clickable-row {
  cursor: pointer;
}

.clickable-row td {
  transition: background 0.2s ease;
}

.clickable-row:hover td {
  background: color-mix(in srgb, var(--accent-2) 10%, transparent);
}

.clickable-cell {
  cursor: pointer;
}

.clickable-cell:hover {
  text-decoration: underline;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: var(--ink);
}

.row-active td {
  background: rgba(247, 185, 85, 0.18);
}

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: grid;
  place-items: center;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 16px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #9aa4b8;
}

.dot.ok {
  background: #3ee8b5;
}

.dot.bad {
  background: #ff9aa2;
}

.btn {
  height: 44px;
  border-radius: 12px;
  border: 0;
  background: var(--btn-bg);
  color: var(--btn-text);
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
}

.btn.btn--icon {
  width: 28px;
  height: 28px;
  padding: 0;
  background: transparent;
}

.btn.btn--glow {
  background: transparent;
}

.btn.btn--glow-add {
  background: linear-gradient(120deg, #02ff2c, #008a12);
}

.btn.btn--glow-import {
  background: linear-gradient(120deg, #38bdf8, #2563eb);
}

.btn.btn--glow-export {
  background: linear-gradient(120deg, #facc15, #fb7185);
}

.btn.btn--glow-filter {
  background: linear-gradient(120deg, #3b82f6, #06b6d4);
}

.btn.btn--glow-eye {
  background: linear-gradient(120deg, #833ab4, #fd1d1d, #fcb045);
}

.btn.btn--glow-refresh {
  background: linear-gradient(120deg, #f97316, #ef4444);
}

pre {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px;
  overflow: auto;
  max-height: 60vh;
}

.bad {
  color: #ff9aa2;
}

.muted {
  opacity: 0.7;
}

@media (max-width: 980px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .main {
    grid-template-columns: 1fr;
  }

  .panel--wide {
    grid-column: span 1;
  }
}

@media (max-width: 1100px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar .btn--ghost {
    width: 100%;
  }

  .toolbar__filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form--compact {
    grid-template-columns: 1fr;
  }

  .form--compact .btn {
    width: 100%;
    justify-self: stretch;
  }
}

@media (max-width: 720px) {
  .toolbar__filters {
    grid-template-columns: 1fr;
  }

  .deal-form {
    grid-template-columns: 1fr;
  }

  .form,
  .form--stack {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1100px) {
  .form,
  .form--stack {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
