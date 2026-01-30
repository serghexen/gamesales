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
        <p class="muted">Сохраняем изменения…</p>
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
              Продажа/аренда
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
            <button class="tab" :class="{ active: activeTab === 'accounts' }" @click="activeTab = 'accounts'">
              Аккаунты
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
                      <div class="toolbar-actions">
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
              <h2>Аккаунты</h2>
              <p class="muted">Создание аккаунтов и контроль слотов.</p>
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
                class="btn btn--icon btn--glow btn--glow-eye"
                :aria-label="showPasswords ? 'Скрыть пароли' : 'Показать пароли'"
                :title="showPasswords ? 'Скрыть пароли' : 'Показать пароли'"
                @click="showPasswords = !showPasswords"
              >
                <svg v-if="!showPasswords" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"
                  />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 3l18 18" />
                  <path d="M10.6 10.6a3 3 0 0 0 4.2 4.2" />
                  <path d="M6.5 6.5C4.2 8.2 2.8 10.4 2.5 12c1.4 2.5 4.8 6 9.5 6 1.6 0 3-.4 4.2-1" />
                  <path d="M9 5.3A10.9 10.9 0 0 1 12 5c6 0 9.5 6 9.5 6a14.3 14.3 0 0 1-2.6 3.3" />
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
                      Логин
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.login_q) }"
                        type="button"
                        aria-label="Фильтр по логину"
                        title="Фильтр по логину"
                        @click.stop="openAccountFilter('login')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'login'" class="filter-pop filter-pop--left" @click.stop>
                      <label class="field">
                        <span class="label">Логин</span>
                        <input v-model.trim="accountFilterDraft.login" class="input" placeholder="логин / домен" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('login')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('login')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleAccountSort('region')">
                    <span class="th-title th-title--filter">
                      Рег.
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.region_q) }"
                        type="button"
                        aria-label="Фильтр по региону"
                        title="Фильтр по региону"
                        @click.stop="openAccountFilter('region')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'region'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Регион</span>
                        <input v-model.trim="accountFilterDraft.region" class="input" placeholder="регион" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('region')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('region')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleAccountSort('status')">
                    <span class="th-title th-title--filter">
                      Стат.
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.status_q) }"
                        type="button"
                        aria-label="Фильтр по статусу"
                        title="Фильтр по статусу"
                        @click.stop="openAccountFilter('status')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'status'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Статус</span>
                        <input v-model.trim="accountFilterDraft.status" class="input" placeholder="статус" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('status')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('status')">Сбросить</button>
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
                        <input v-model.trim="accountFilterDraft.slots" class="input" placeholder="например ps4 2/6" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('slots')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('slots')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleAccountSort('date')">
                    <span class="th-title th-title--filter">
                      Дата
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(accountFilters.date_from || accountFilters.date_to) }"
                        type="button"
                        aria-label="Фильтр по дате"
                        title="Фильтр по дате"
                        @click.stop="openAccountFilter('date')"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeAccountFilter === 'date'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">С</span>
                        <input v-model="accountFilterDraft.date_from" class="input" type="date" />
                      </label>
                      <label class="field">
                        <span class="label">По</span>
                        <input v-model="accountFilterDraft.date_to" class="input" type="date" />
                      </label>
                      <p v-if="accountFilterErrors.date" class="bad">{{ accountFilterErrors.date }}</p>
                      <button class="ghost ghost--small" type="button" @click="applyAccountFilter('date')">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetAccountFilter('date')">Сбросить</button>
                    </div>
                  </th>
                  <th>Почта</th>
                  <th>Акк. пароль</th>
                  <th>Резерв</th>
                  <th>2FA код</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in sortedAccounts" :key="a.account_id" class="clickable-row" @click="startEditAccount(a)">
                  <td class="cell--account">{{ a.login_full || '—' }}</td>
                  <td>{{ a.region_code || '—' }}</td>
                  <td>{{ a.status }}</td>
                  <td>{{ formatAccountSlots(a) }}</td>
                  <td>{{ formatDateOnly(a.account_date) }}</td>
                  <td>{{ formatSecret(getEmailSecret(a.account_id)) }}</td>
                  <td>{{ formatSecret(getAccountSecret(a.account_id)) }}</td>
                  <td>{{ formatSecret(getReserveSecrets(a.account_id)) }}</td>
                  <td>{{ formatSecret(getAuthSecret(a.account_id)) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет аккаунтов.</p>

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
                        <input v-model="editAccount.account_date" class="input" type="date" :disabled="accountEditMode === 'view'" />
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
                      <div class="field field--full">
                        <span class="label">Пароли резерв</span>
                        <div class="input-list">
                        <div v-for="(p, idx) in editAccount.reserve_secrets" :key="idx" class="input-list__row">
                          <input
                            v-model.trim="editAccount.reserve_secrets[idx]"
                            class="input"
                            autocomplete="new-password"
                            :placeholder="`Резерв ${idx + 1}`"
                            :disabled="accountEditMode === 'view'"
                          />
                          <button
                            v-if="accountEditMode === 'edit'"
                            class="btn btn--icon-plain btn--icon-tiny"
                            type="button"
                            aria-label="Убрать"
                            title="Убрать"
                            @click="removeEditReserveSecret(idx)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                            </svg>
                          </button>
                        </div>
                        <button v-if="accountEditMode === 'edit'" class="ghost" type="button" @click="addEditReserveSecret">+ Добавить резервный пароль</button>
                      </div>
                      </div>
                      <div class="field field--full">
                        <span class="label">Игры</span>
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
                              <td>{{ d.game_title || '—' }}</td>
                              <td>{{ d.deal_type || '—' }}</td>
                              <td>{{ d.status || '—' }}</td>
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
                        <input v-model="newAccount.account_date" class="input" type="date" />
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
                      <div class="field field--full">
                        <span class="label">Пароли резерв</span>
                        <div class="input-list">
                          <div v-for="(p, idx) in newAccount.reserve_secrets" :key="idx" class="input-list__row">
                            <input
                              v-model.trim="newAccount.reserve_secrets[idx]"
                              class="input"
                              autocomplete="new-password"
                              :placeholder="`Резерв ${idx + 1}`"
                            />
                            <button
                              class="btn btn--icon-plain btn--icon-tiny"
                              type="button"
                              aria-label="Убрать"
                              title="Убрать"
                              @click="removeReserveSecret(idx)"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
                              </svg>
                            </button>
                          </div>
                          <button class="ghost" type="button" @click="addReserveSecret">+ Добавить резервный пароль</button>
                        </div>
                      </div>
                      <div class="field field--full">
                        <span class="label">Игры</span>
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
              <h2>Игры</h2>
              <p class="muted">Добавление игр в справочник.</p>
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
                <tr v-for="g in sortedGames" :key="g.game_id" class="clickable-row" @click="openGameAccounts(g)">
                  <td>{{ g.title }}</td>
                  <td>{{ g.platform_code || '—' }}</td>
                  <td>{{ g.region_code || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет игр.</p>

            <teleport to="body">
              <div v-if="selectedGame" class="modal-backdrop" @click.self="selectedGame = null">
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <div>
                      <h3>{{ selectedGame.title }}</h3>
                      <p class="muted">Аккаунты с игрой и свободные слоты.</p>
                    </div>
                    <div class="toolbar-actions">
                      <button
                        class="btn btn--icon-plain"
                        @click="refreshGameAccounts"
                        :disabled="gameAccountsLoading"
                        aria-label="Обновить список"
                        title="Обновить список"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                          <path d="M20 4v6h-6" />
                        </svg>
                      </button>
                      <button
                        class="btn btn--icon-plain"
                        @click="startEditGame(selectedGame)"
                        aria-label="Редактировать игру"
                        title="Редактировать игру"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                          <path d="M13 6l4 4" />
                        </svg>
                      </button>
                      <button
                        class="btn btn--icon-plain"
                        aria-label="Закрыть"
                        title="Закрыть"
                        @click="selectedGame = null"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M6 6l12 12M18 6l-12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div class="modal__body">
                    <p v-if="gameAccountsError" class="bad">{{ gameAccountsError }}</p>
                    <div v-if="gameAccountsLoading" class="loader-wrap">
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
                    <table v-else-if="pagedGameAccounts.length" class="table table--compact">
                      <thead>
                        <tr>
                          <th class="sortable" @click="sortGameAccounts('login_full')">Аккаунт</th>
                          <th class="sortable" @click="sortGameAccounts('platform_code')">Платформа</th>
                          <th class="sortable" @click="sortGameAccounts('free_slots')">Свободно</th>
                          <th class="sortable" @click="sortGameAccounts('occupied_slots')">Занято</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="a in pagedGameAccounts" :key="a.account_id" class="clickable-row" @click="goToAccount(a.login_full)">
                          <td>{{ a.login_full || a.account_id }}</td>
                          <td>{{ a.platform_code }}</td>
                          <td>{{ a.free_slots }}</td>
                          <td>{{ a.occupied_slots }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <p v-else class="muted">Пока нет аккаунтов.</p>

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
                </div>
              </div>
            </teleport>

            <div class="divider"></div>

            <teleport to="body">
              <div
                v-if="editGame.open || showGameForm"
                class="modal-backdrop"
                @click.self="closeGameModal"
              >
                <div ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>{{ editGame.open ? 'Редактирование игры' : 'Новая игра' }}</h3>
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
                  <div class="modal__body">
                    <div v-if="editGame.open" class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Название</span>
                        <input v-model.trim="editGame.title" class="input" placeholder="Например, GTA V" />
                      </label>
                      <label class="field">
                        <span class="label">Платформа</span>
                        <select v-model="editGame.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Регион</span>
                        <select v-model="editGame.region_code" class="input input--select">
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
                      <label class="field">
                        <span class="label">Название</span>
                        <input v-model.trim="newGame.title" class="input" placeholder="Например, GTA V" />
                      </label>
                      <label class="field">
                        <span class="label">Платформа (опционально)</span>
                        <select v-model="newGame.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }})
                          </option>
                        </select>
                      </label>
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
              <h2>Продажа / аренда</h2>
              <p class="muted">Фиксация выдач и продаж по аккаунтам.</p>
            </div>
            <div class="toolbar-actions">
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
                  <th class="sortable cell--account" @click="toggleDealSort('account')">
                    <span class="th-title th-title--filter">
                      Аккаунт
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.account_q) }"
                        type="button"
                        aria-label="Фильтр по аккаунту"
                        title="Фильтр по аккаунту"
                        @click.stop="activeDealFilter = activeDealFilter === 'account' ? '' : 'account'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'account'" class="filter-pop filter-pop--left" @click.stop>
                      <label class="field">
                        <span class="label">Аккаунт</span>
                        <input v-model.trim="dealFilters.account_q" class="input" placeholder="аккаунт" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('account')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleDealSort('game')">
                    <span class="th-title th-title--filter">
                      Игра
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.game_q) }"
                        type="button"
                        aria-label="Фильтр по игре"
                        title="Фильтр по игре"
                        @click.stop="activeDealFilter = activeDealFilter === 'game' ? '' : 'game'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'game'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Игра</span>
                        <input v-model.trim="dealFilters.game_q" class="input" placeholder="игра" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('game')">Сбросить</button>
                    </div>
                  </th>
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
                    <div v-if="activeDealFilter === 'type'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Тип</span>
                        <input v-model.trim="dealFilters.type_q" class="input" placeholder="тип сделки" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('type')">Сбросить</button>
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
                    <div v-if="activeDealFilter === 'status'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Статус</span>
                        <input v-model.trim="dealFilters.status_q" class="input" placeholder="статус" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('status')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleDealSort('customer')">
                    <span class="th-title th-title--filter">
                      Польз.
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
                        <input v-model.trim="dealFilters.customer_q" class="input" placeholder="пользователь" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('customer')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable cell--tight" @click="toggleDealSort('source')">
                    <span class="th-title th-title--filter">
                      Откуда
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.source_q) }"
                        type="button"
                        aria-label="Фильтр по источнику"
                        title="Фильтр по источнику"
                        @click.stop="activeDealFilter = activeDealFilter === 'source' ? '' : 'source'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'source'" class="filter-pop filter-pop--center" @click.stop>
                      <label class="field">
                        <span class="label">Источник</span>
                        <input v-model.trim="dealFilters.source_q" class="input" placeholder="источник" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('source')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable" @click="toggleDealSort('date')">
                    <span class="th-title th-title--filter">
                      Дата
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
                        <input v-model="dealFilters.purchase_from" class="input" type="date" />
                      </label>
                      <label class="field">
                        <span class="label">По</span>
                        <input v-model="dealFilters.purchase_to" class="input" type="date" />
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
                  <th class="sortable cell--tight" @click="toggleDealSort('platform')">
                    <span class="th-title th-title--filter">
                      Платф.
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.platform_q) }"
                        type="button"
                        aria-label="Фильтр по платформе"
                        title="Фильтр по платформе"
                        @click.stop="activeDealFilter = activeDealFilter === 'platform' ? '' : 'platform'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'platform'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">Платформа</span>
                        <input v-model.trim="dealFilters.platform_q" class="input" placeholder="платформа" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('platform')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable cell--tight cell--num" @click="toggleDealSort('price')">
                    <span class="th-title th-title--filter">
                      Цена
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.price_min || dealFilters.price_max) }"
                        type="button"
                        aria-label="Фильтр по цене"
                        title="Фильтр по цене"
                        @click.stop="activeDealFilter = activeDealFilter === 'price' ? '' : 'price'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'price'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">Цена от</span>
                        <input v-model.trim="dealFilters.price_min" class="input" type="number" min="0" />
                      </label>
                      <label class="field">
                        <span class="label">Цена до</span>
                        <input v-model.trim="dealFilters.price_max" class="input" type="number" min="0" />
                      </label>
                      <p v-if="dealFilterErrors.price" class="bad">{{ dealFilterErrors.price }}</p>
                      <button
                        class="ghost ghost--small"
                        type="button"
                        @click="validateDealRange('price') && (loadDeals(1), activeDealFilter = '')"
                      >
                        Применить
                      </button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('price')">Сбросить</button>
                    </div>
                  </th>
                  <th class="sortable cell--tight" @click="toggleDealSort('notes')">
                    <span class="th-title th-title--filter">
                      Комм.
                      <button
                        class="filter-icon"
                        :class="{ 'filter-icon--active': Boolean(dealFilters.notes_q) }"
                        type="button"
                        aria-label="Фильтр по комментарию"
                        title="Фильтр по комментарию"
                        @click.stop="activeDealFilter = activeDealFilter === 'notes' ? '' : 'notes'"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 6h16M7 12h10M10 18h4" />
                        </svg>
                      </button>
                    </span>
                    <div v-if="activeDealFilter === 'notes'" class="filter-pop filter-pop--right" @click.stop>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="dealFilters.notes_q" class="input" placeholder="комментарий" />
                      </label>
                      <button class="ghost ghost--small" type="button" @click="loadDeals(1); activeDealFilter = ''">Применить</button>
                      <button class="ghost ghost--small" type="button" @click="resetDealFilter('notes')">Сбросить</button>
                    </div>
                  </th>
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
                  <td class="cell--account">
                    <span class="clickable-cell" @click.stop="goToAccount(d.account_login)">{{ d.account_login || d.account_id }}</span>
                  </td>
                  <td>
                    <span class="clickable-cell" @click.stop="openDealGame(d)">{{ d.game_title || '—' }}</span>
                  </td>
                  <td class="cell--tight">{{ d.deal_type }}</td>
                  <td class="cell--tight">{{ d.status || '—' }}</td>
                  <td>{{ d.customer_nickname || '—' }}</td>
                  <td class="cell--tight">{{ getSourceName(d.source_code) }}</td>
                  <td>{{ formatDate(d.purchase_at || d.created_at) }}</td>
                  <td class="cell--tight">{{ d.platform_code || '—' }}</td>
                  <td class="cell--tight cell--num">{{ d.price }}</td>
                  <td class="cell--tight">{{ d.notes || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет сделок.</p>

            <div v-if="totalPages > 1" class="pager">
              <button class="ghost" @click="loadDeals(dealPage - 1)" :disabled="dealPage <= 1 || dealListLoading">
                ← Назад
              </button>
              <span class="muted">Страница {{ dealPage }} из {{ totalPages }}</span>
              <button
                class="ghost"
                @click="loadDeals(dealPage + 1)"
                :disabled="dealPage >= totalPages || dealListLoading"
              >
                Вперёд →
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
                    <h3>{{ editDeal.open ? 'Редактирование сделки' : 'Новая сделка' }}</h3>
                    <button
                      class="btn btn--icon-plain"
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
                  <div class="modal__body">
                    <div v-if="editDeal.open" class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Тип</span>
                        <select v-model="editDeal.deal_type_code" class="input input--select">
                          <option value="sale">Продажа</option>
                          <option value="rental">Аренда</option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Аккаунт</span>
                        <select v-model.number="editDeal.account_id" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="a in dealAccountsForEdit" :key="a.account_id" :value="a.account_id">
                            {{ a.login_full || a.account_id }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Игра</span>
                        <select v-model.number="editDeal.game_id" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="g in games" :key="g.game_id" :value="g.game_id">
                            {{ g.title }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Пользователь</span>
                        <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="nickname" />
                      </label>
                      <label class="field">
                        <span class="label">Откуда</span>
                        <select v-model="editDeal.source_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="s in sources" :key="s.code" :value="s.code">
                            {{ s.name }} ({{ s.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Платформа</span>
                        <select v-model="editDeal.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Цена</span>
                        <input v-model.number="editDeal.price" class="input" type="number" min="0" />
                      </label>
                      <label class="field">
                        <span class="label">Дата покупки</span>
                        <input v-model="editDeal.purchase_at" class="input" type="date" />
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="editDeal.notes" class="input" />
                      </label>
                      <p v-if="dealError" class="bad">{{ dealError }}</p>
                      <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                      <div class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="updateDeal"
                          :disabled="dealLoading"
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
                        <span class="label">Тип</span>
                        <select v-model="newDeal.deal_type_code" class="input input--select">
                          <option value="sale">Продажа</option>
                          <option value="rental">Аренда</option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Аккаунт</span>
                        <select v-model.number="newDeal.account_id" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="a in dealAccountsForNew" :key="a.account_id" :value="a.account_id">
                            {{ a.login_full || a.account_id }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Игра</span>
                        <select v-model.number="newDeal.game_id" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="g in games" :key="g.game_id" :value="g.game_id">
                            {{ g.title }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Пользователь</span>
                        <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="nickname" />
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
                      <label class="field">
                        <span class="label">Платформа</span>
                        <select v-model="newDeal.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Цена</span>
                        <input v-model.number="newDeal.price" class="input" type="number" min="0" />
                      </label>
                      <label class="field">
                        <span class="label">Дата покупки</span>
                        <input v-model="newDeal.purchase_at" class="input" type="date" />
                      </label>
                      <label v-if="newDeal.deal_type_code === 'rental'" class="field">
                        <span class="label">Слотов используется</span>
                        <input v-model.number="newDeal.slots_used" class="input" type="number" min="1" />
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="newDeal.notes" class="input" />
                      </label>
                      <p v-if="dealError" class="bad">{{ dealError }}</p>
                      <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                      <div class="toolbar-actions">
                        <button
                          class="btn btn--icon-plain"
                          @click="createDeal"
                          :disabled="dealLoading"
                          aria-label="Сохранить сделку"
                          title="Сохранить сделку"
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

        <section v-if="isAdmin && activeTab === 'catalogs'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Справочники</h2>
              <p class="muted">Домены, источники, платформы, регионы.</p>
            </div>
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
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { apiGet, apiPost, apiDelete, apiPut } from '../api/http'

const router = useRouter()
const auth = useAuth()

const apiOk = ref(null)
const loading = ref(false)
const error = ref(null)
const accounts = ref([])
const accountSecrets = ref({})
const accountsError = ref(null)
const accountsOk = ref(null)
const accountsLoading = ref(false)
const accountSaving = ref(false)
const accountDeals = ref([])
const accountDealsLoading = ref(false)
const accountDealsError = ref(null)
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
const selectedGame = ref(null)
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
const dealPageSize = ref(20)
const dealTotal = ref(0)
const pwdError = ref(null)
const pwdOk = ref(false)
const pwdLoading = ref(false)
const showPwdForm = ref(false)
const accountEditMode = ref('view')

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
  const gameMap = new Map((games.value || []).map((g) => [g.game_id, g.title]))
  return (editAccount.game_ids || []).map((id) => gameMap.get(id)).filter(Boolean)
})

const activeDealChips = computed(() => {
  const chips = []
  if (dealFilters.account_q) chips.push({ key: 'account', label: 'Аккаунт', value: dealFilters.account_q })
  if (dealFilters.game_q) chips.push({ key: 'game', label: 'Игра', value: dealFilters.game_q })
  if (dealFilters.type_q) chips.push({ key: 'type', label: 'Тип', value: dealFilters.type_q })
  if (dealFilters.status_q) chips.push({ key: 'status', label: 'Статус', value: dealFilters.status_q })
  if (dealFilters.customer_q) chips.push({ key: 'customer', label: 'Пользователь', value: dealFilters.customer_q })
  if (dealFilters.source_q) chips.push({ key: 'source', label: 'Откуда', value: dealFilters.source_q })
  if (dealFilters.purchase_from || dealFilters.purchase_to) {
    const from = dealFilters.purchase_from ? formatDateOnly(dealFilters.purchase_from) : '—'
    const to = dealFilters.purchase_to ? formatDateOnly(dealFilters.purchase_to) : '—'
    chips.push({ key: 'date', label: 'Дата', value: `${from} → ${to}` })
  }
  if (dealFilters.platform_q) chips.push({ key: 'platform', label: 'Платформа', value: dealFilters.platform_q })
  if (dealFilters.price_min || dealFilters.price_max) {
    const from = dealFilters.price_min || '—'
    const to = dealFilters.price_max || '—'
    chips.push({ key: 'price', label: 'Цена', value: `${from} → ${to}` })
  }
  if (dealFilters.notes_q) chips.push({ key: 'notes', label: 'Комментарий', value: dealFilters.notes_q })
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
  if (accountFilters.login_q) chips.push({ key: 'login', label: 'Логин', value: accountFilters.login_q })
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
  platform_code: '',
  region_code: '',
})

const newDeal = reactive({
  deal_type_code: 'sale',
  account_id: '',
  game_id: '',
  customer_nickname: '',
  source_code: '',
  platform_code: '',
  price: 0,
  purchase_at: '',
  slots_used: 1,
  notes: '',
})

const editDeal = reactive({
  open: false,
  deal_id: null,
  deal_type_code: 'sale',
  account_id: '',
  game_id: '',
  customer_nickname: '',
  source_code: '',
  platform_code: '',
  price: 0,
  purchase_at: '',
  slots_used: 1,
  notes: '',
})

const games = ref([])
const gamesLoading = ref(false)
const editGame = reactive({
  open: false,
  game_id: null,
  title: '',
  platform_code: '',
  region_code: '',
})
const dealFilters = reactive({
  account_q: '',
  game_q: '',
  type_q: '',
  status_q: '',
  customer_q: '',
  source_q: '',
  platform_q: '',
  purchase_from: '',
  purchase_to: '',
  price_min: '',
  price_max: '',
  notes_q: '',
})

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
  reserve_secrets: [],
  auth_code: '',
  game_ids: [],
})

const accountModalMode = ref('edit')
const showAccountFilters = ref(false)
const showPasswords = ref(false)
const accountGameSearch = ref('')
const editAccountGameSearch = ref('')
const accountGamesLoading = ref(false)
const activeAccountFilter = ref('')
const accountFilterDraft = reactive({
  login: '',
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
  reserve_secrets: [],
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
const showDomainForm = ref(false)
const showSourceForm = ref(false)
const showPlatformForm = ref(false)
const showRegionForm = ref(false)
const accountFilters = reactive({
  login_q: '',
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

const dealTypeOptions = [
  { code: 'sale', name: 'Продажа' },
  { code: 'rental', name: 'Аренда' },
  { code: 'expense', name: 'Расходы' },
  { code: 'adjustment', name: 'Корректирование' },
]

const dealStatusOptions = [
  { code: 'draft', name: 'Черновик' },
  { code: 'confirmed', name: 'Подтвержден' },
  { code: 'cancelled', name: 'Отменен' },
  { code: 'closed', name: 'Закрыт' },
]

const getAccountPlatformSlots = (account, platformCode) => {
  if (!account?.platform_slots || !platformCode) return null
  const code = String(platformCode).toLowerCase()
  return account.platform_slots.find((s) => String(s.platform_code || '').toLowerCase() === code) || null
}

const getAccountSlotsText = (account) => {
  const ps4 = getAccountPlatformSlots(account, 'ps4')
  const ps5 = getAccountPlatformSlots(account, 'ps5')
  const ps4Text = `PS4 ${ps4?.occupied_slots || 0}/${ps4?.slot_capacity || 0}`
  const ps5Text = `PS5 ${ps5?.occupied_slots || 0}/${ps5?.slot_capacity || 0}`
  return `${ps4Text} · ${ps5Text}`
}

const getAccountFreeTotal = (account) =>
  (account?.platform_slots || []).reduce((sum, s) => sum + Number(s?.free_slots || 0), 0)

const formatAccountSlots = (account) => getAccountSlotsText(account)

const getAccountFreeSlots = (account, platformCode) => {
  const slot = getAccountPlatformSlots(account, platformCode)
  return Number(slot?.free_slots || 0)
}

const filteredAccounts = computed(() => {
  let list = [...accounts.value]
  if (accountFilters.login_q) {
    const q = accountFilters.login_q.toLowerCase()
    list = list.filter((a) =>
      (a.login_full || '').toLowerCase().includes(q)
    )
  }
  if (accountFilters.region_q) {
    const q = accountFilters.region_q.toLowerCase()
    list = list.filter((a) => (a.region_code || '').toLowerCase().includes(q))
  }
  if (accountFilters.status_q) {
    const q = accountFilters.status_q.toLowerCase()
    list = list.filter((a) => (a.status || '').toLowerCase().includes(q))
  }
  if (accountFilters.slots_q) {
    const q = accountFilters.slots_q.toLowerCase()
    list = list.filter((a) => getAccountSlotsText(a).toLowerCase().includes(q))
  }
  if (accountFilters.date_from) {
    list = list.filter((a) => new Date(a.account_date || 0) >= new Date(accountFilters.date_from))
  }
  if (accountFilters.date_to) {
    list = list.filter((a) => new Date(a.account_date || 0) <= new Date(accountFilters.date_to))
  }
  return list
})

const sortedAccounts = computed(() => {
  const list = [...filteredAccounts.value]
  if (accountSort.value === 'login_asc') {
    list.sort((a, b) => (a.login_full || '').localeCompare(b.login_full || ''))
  } else if (accountSort.value === 'login_desc') {
    list.sort((a, b) => (b.login_full || '').localeCompare(a.login_full || ''))
  } else if (accountSort.value === 'region_asc') {
    list.sort((a, b) => (a.region_code || '').localeCompare(b.region_code || ''))
  } else if (accountSort.value === 'region_desc') {
    list.sort((a, b) => (b.region_code || '').localeCompare(a.region_code || ''))
  } else if (accountSort.value === 'status_asc') {
    list.sort((a, b) => (a.status || '').localeCompare(b.status || ''))
  } else if (accountSort.value === 'status_desc') {
    list.sort((a, b) => (b.status || '').localeCompare(a.status || ''))
  } else if (accountSort.value === 'slots_desc') {
    list.sort((a, b) => getAccountFreeTotal(b) - getAccountFreeTotal(a))
  } else if (accountSort.value === 'slots_asc') {
    list.sort((a, b) => getAccountFreeTotal(a) - getAccountFreeTotal(b))
  } else if (accountSort.value === 'date_desc') {
    list.sort((a, b) => new Date(b.account_date || 0) - new Date(a.account_date || 0))
  } else if (accountSort.value === 'date_asc') {
    list.sort((a, b) => new Date(a.account_date || 0) - new Date(b.account_date || 0))
  }
  return list
})

const dealAccountsForNew = computed(() => {
  let list = [...accounts.value]
  if (newDeal.platform_code) {
    return list.filter((a) => getAccountFreeSlots(a, newDeal.platform_code) > 0)
  }
  return list
})

const dealAccountsForEdit = computed(() => {
  let list = [...accounts.value]
  if (editDeal.platform_code) {
    return list.filter(
      (a) => getAccountFreeSlots(a, editDeal.platform_code) > 0 || a.account_id === editDeal.account_id
    )
  }
  return list
})



const filteredAccountGames = computed(() => {
  const q = accountGameSearch.value.trim().toLowerCase()
  if (!q) return games.value
  return games.value.filter((g) => (g.title || '').toLowerCase().includes(q))
})

const filteredEditAccountGames = computed(() => {
  const q = editAccountGameSearch.value.trim().toLowerCase()
  if (!q) return games.value
  return games.value.filter((g) => (g.title || '').toLowerCase().includes(q))
})

const gameFilters = reactive({
  q: '',
  platform_code: '',
  region_code: '',
})

const filteredGames = computed(() => {
  let list = [...games.value]
  if (gameFilters.q) {
    const q = gameFilters.q.toLowerCase()
    list = list.filter((g) => (g.title || '').toLowerCase().includes(q))
  }
  if (gameFilters.platform_code) {
    const q = gameFilters.platform_code.toLowerCase()
    list = list.filter((g) => (g.platform_code || '').toLowerCase().includes(q))
  }
  if (gameFilters.region_code) {
    const q = gameFilters.region_code.toLowerCase()
    list = list.filter((g) => (g.region_code || '').toLowerCase().includes(q))
  }
  return list
})

const sortedGames = computed(() => {
  const list = [...filteredGames.value]
  const { key, dir } = gamesSort.value
  list.sort((a, b) => {
    const av = key === 'title' ? a.title : key === 'platform' ? a.platform_code : a.region_code
    const bv = key === 'title' ? b.title : key === 'platform' ? b.platform_code : b.region_code
    return dir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''))
  })
  return list
})

const sortedDeals = computed(() => {
  const list = [...dealItems.value]
  const { key, dir } = dealSort.value
  const getVal = (d) => {
    if (key === 'account') return d.account_login || ''
    if (key === 'game') return d.game_title || ''
    if (key === 'type') return d.deal_type || ''
    if (key === 'status') return d.status || ''
    if (key === 'customer') return d.customer_nickname || ''
    if (key === 'source') return d.source_code || ''
    if (key === 'platform') return d.platform_code || ''
    if (key === 'price') return Number(d.price || 0)
    if (key === 'notes') return d.notes || ''
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
    error.value = e?.message || 'Ошибка'
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
    userError.value = e?.message || 'Ошибка'
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

function addReserveSecret() {
  newAccount.reserve_secrets.push('')
}

function removeReserveSecret(index) {
  newAccount.reserve_secrets.splice(index, 1)
}

function addEditReserveSecret() {
  editAccount.reserve_secrets.push('')
}

function removeEditReserveSecret(index) {
  editAccount.reserve_secrets.splice(index, 1)
}

function formatSecret(value, isList = false) {
  if (!value) return '—'
  if (!showPasswords.value) return '••••••'
  return value
}

function openGameAccounts(game) {
  resetModalPos()
  selectedGame.value = game
  gameAccountsPage.value = 1
  loadGameAccounts(game.game_id)
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
}

function toggleGamesSort(key) {
  const current = gamesSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    gamesSort.value = { key, dir: 'asc' }
  }
}

function toggleDealSort(key) {
  const current = dealSort.value
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc'
  } else {
    dealSort.value = { key, dir: 'asc' }
  }
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

function startEditGame(game) {
  resetModalPos()
  showGameForm.value = false
  editGame.open = true
  editGame.game_id = game.game_id
  editGame.title = game.title || ''
  editGame.platform_code = game.platform_code || ''
  editGame.region_code = game.region_code || ''
}

function cancelEditGame() {
  editGame.open = false
  editGame.game_id = null
  editGame.title = ''
  editGame.platform_code = ''
  editGame.region_code = ''
}

function openCreateGameModal() {
  resetModalPos()
  showGameForm.value = true
  cancelEditGame()
  gameError.value = null
  gameOk.value = null
}

function closeGameModal() {
  showGameForm.value = false
  cancelEditGame()
  gameError.value = null
  gameOk.value = null
  newGame.title = ''
  newGame.platform_code = ''
  newGame.region_code = ''
}

function refreshGameAccounts() {
  if (selectedGame.value) {
    gameAccountsPage.value = 1
    loadGameAccounts(selectedGame.value.game_id)
  }
}

function goToAccount(login) {
  activeTab.value = 'accounts'
  accountFilters.login_q = login || ''
}

function openDealGame(deal) {
  if (!deal || !deal.game_id) return
  activeTab.value = 'games'
  const game = games.value.find((g) => g.game_id === deal.game_id)
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
  if (kind === 'account') {
    dealFilters.account_q = ''
  } else if (kind === 'game') {
    dealFilters.game_q = ''
  } else if (kind === 'type') {
    dealFilters.type_q = ''
  } else if (kind === 'status') {
    dealFilters.status_q = ''
  } else if (kind === 'customer') {
    dealFilters.customer_q = ''
  } else if (kind === 'source') {
    dealFilters.source_q = ''
  } else if (kind === 'date') {
    dealFilters.purchase_from = ''
    dealFilters.purchase_to = ''
    dealFilterErrors.date = ''
  } else if (kind === 'platform') {
    dealFilters.platform_q = ''
  } else if (kind === 'price') {
    dealFilters.price_min = ''
    dealFilters.price_max = ''
    dealFilterErrors.price = ''
  } else if (kind === 'notes') {
    dealFilters.notes_q = ''
  } else if (kind === 'all') {
    dealFilters.account_q = ''
    dealFilters.game_q = ''
    dealFilters.type_q = ''
    dealFilters.status_q = ''
    dealFilters.customer_q = ''
    dealFilters.source_q = ''
    dealFilters.purchase_from = ''
    dealFilters.purchase_to = ''
    dealFilters.platform_q = ''
    dealFilters.price_min = ''
    dealFilters.price_max = ''
    dealFilters.notes_q = ''
    dealFilterErrors.date = ''
    dealFilterErrors.price = ''
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
  if (kind === 'price') {
    const from = Number(dealFilters.price_min)
    const to = Number(dealFilters.price_max)
    if (dealFilters.price_min !== '' && dealFilters.price_max !== '' && from > to) {
      error = 'Цена "от" не может быть больше цены "до"'
    }
  }
  dealFilterErrors[kind] = error
  return !error
}

const dealFilterErrors = reactive({
  date: '',
  price: '',
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
  activeGameFilter.value = ''
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
  activeGameFilter.value = ''
}

const resetAccountFilter = (kind) => {
  if (kind === 'login') {
    accountFilters.login_q = ''
    accountFilterDraft.login = ''
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
    accountFilters.login_q = ''
    accountFilters.region_q = ''
    accountFilters.status_q = ''
    accountFilters.slots_q = ''
    accountFilters.date_from = ''
    accountFilters.date_to = ''
    accountFilterDraft.login = ''
    accountFilterDraft.region = ''
    accountFilterDraft.status = ''
    accountFilterDraft.slots = ''
    accountFilterDraft.date_from = ''
    accountFilterDraft.date_to = ''
    accountFilterErrors.date = ''
  }
  activeAccountFilter.value = ''
}

const openAccountFilter = (kind) => {
  accountFilterDraft.login = accountFilters.login_q || ''
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
  newDeal.platform_code = ''
  newDeal.price = 0
  newDeal.purchase_at = ''
  newDeal.slots_used = 1
  newDeal.notes = ''
}

function startEditDeal(deal) {
  resetModalPos()
  showDealForm.value = false
  editDeal.open = true
  editDeal.deal_id = deal.deal_id
  editDeal.deal_type_code = deal.deal_type_code || (deal.deal_type === 'Аренда' ? 'rental' : 'sale')
  editDeal.account_id = deal.account_id
  editDeal.game_id = deal.game_id
  editDeal.customer_nickname = deal.customer_nickname || ''
  editDeal.source_code = deal.source_code || ''
  editDeal.platform_code = deal.platform_code || ''
  editDeal.price = Number(deal.price || 0)
  editDeal.purchase_at = deal.purchase_at ? String(deal.purchase_at).slice(0, 10) : ''
  editDeal.slots_used = deal.slots_used || (deal.deal_type_code === 'rental' ? 1 : 0)
  editDeal.notes = deal.notes || ''
}

function cancelEditDeal() {
  editDeal.open = false
  editDeal.deal_id = null
  editDeal.deal_type_code = 'sale'
  editDeal.account_id = ''
  editDeal.game_id = ''
  editDeal.customer_nickname = ''
  editDeal.source_code = ''
  editDeal.platform_code = ''
  editDeal.price = 0
  editDeal.purchase_at = ''
  editDeal.slots_used = 1
  editDeal.notes = ''
}

function formatDateOnly(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString()
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
  return reserves.join(', ')
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
    const g = await apiGet('/games', { token: auth.state.token })
    games.value = g || []
  } catch {
    games.value = []
  } finally {
    gamesLoading.value = false
  }
}

async function loadGameAccounts(gameId) {
  gameAccountsLoading.value = true
  gameAccountsError.value = null
  try {
    const data = await apiGet(`/games/${gameId}/accounts`, { token: auth.state.token })
    gameAccounts.value = data || []
  } catch (e) {
    gameAccountsError.value = e?.message || 'Ошибка'
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
    const data = await apiGet('/accounts', { token: auth.state.token })
    accounts.value = data || []
    await loadAccountSecrets(accounts.value)
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
  } finally {
    accountsLoading.value = false
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
    accountDealsError.value = e?.message || 'Ошибка'
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
  editAccount.reserve_secrets = reserves
    .sort((a1, a2) => a1.secret_key.localeCompare(a2.secret_key))
    .map((s) => (s.secret_value_b64 ? fromBase64(s.secret_value_b64) : ''))
  editAccount.existing_reserve_keys = reserves.map((s) => s.secret_key)
  editAccount.has_account = Boolean(account)
  editAccount.has_email = Boolean(email)
  editAccount.has_auth = Boolean(auth)
  loadAccountGames(a.account_id)
  loadAccountDeals(a.account_id)
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
  newAccount.reserve_secrets = []
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
  editAccount.reserve_secrets = []
  editAccount.existing_reserve_keys = []
  editAccount.has_account = false
  editAccount.has_email = false
  editAccount.has_auth = false
  editAccount.game_ids = []
  editAccountGameSearch.value = ''
  accountDeals.value = []
  accountDealsError.value = null
  accountDealsLoading.value = false
  accountEditMode.value = 'view'
  newAccount.login_name = ''
  newAccount.domain_code = ''
  newAccount.region_code = ''
  newAccount.notes = ''
  newAccount.account_date = ''
  newAccount.email_password = ''
  newAccount.account_password = ''
  newAccount.reserve_secrets = []
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
    newAccount.reserve_secrets
      .map((v) => v.trim())
      .filter(Boolean)
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
    newAccount.reserve_secrets = []
    newAccount.auth_code = ''
    newAccount.game_ids = []
    accountGameSearch.value = ''
    await loadAccounts()
    cancelEditAccount()
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
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

    const reserveValues = editAccount.reserve_secrets.map((v) => v.trim()).filter(Boolean)
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
    cancelEditAccount()
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
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
    userError.value = e?.message || 'Ошибка'
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
    pwdError.value = e?.message || 'Ошибка'
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
        platform_code: newGame.platform_code || null,
        region_code: newGame.region_code || null,
      },
      { token: auth.state.token }
    )
    gameOk.value = `Игра “${newGame.title}” добавлена`
    newGame.title = ''
    newGame.platform_code = ''
    newGame.region_code = ''
    await loadGames()
    closeGameModal()
  } catch (e) {
    gameError.value = e?.message || 'Ошибка'
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
        platform_code: editGame.platform_code || null,
        region_code: editGame.region_code || null,
      },
      { token: auth.state.token }
    )
    gameOk.value = 'Игра обновлена'
    await loadGames()
    cancelEditGame()
  } catch (e) {
    gameError.value = e?.message || 'Ошибка'
  } finally {
    gameLoading.value = false
    gameSaving.value = false
  }
}

async function createDeal() {
  dealError.value = null
  dealOk.value = null
  if (!newDeal.account_id || !newDeal.game_id || !newDeal.customer_nickname || !newDeal.platform_code) {
    dealError.value = 'Заполните аккаунт, игру, пользователя и платформу'
    return
  }
  dealLoading.value = true
  dealSaving.value = true
  try {
    await apiPost(
      '/deals',
      {
        deal_type_code: newDeal.deal_type_code,
        account_id: newDeal.account_id,
        game_id: newDeal.game_id,
        customer_nickname: newDeal.customer_nickname,
        source_code: newDeal.source_code || null,
        platform_code: newDeal.platform_code || null,
        price: newDeal.price || 0,
        purchase_at: newDeal.purchase_at ? `${newDeal.purchase_at}T00:00:00Z` : null,
        slots_used: newDeal.deal_type_code === 'rental' ? newDeal.slots_used : 0,
        notes: newDeal.notes || null,
      },
      { token: auth.state.token }
    )
    dealOk.value = 'Сделка сохранена'
    newDeal.customer_nickname = ''
    newDeal.price = 0
    newDeal.purchase_at = ''
    newDeal.notes = ''
    await loadDeals(1)
    closeDealModal()
  } catch (e) {
    dealError.value = e?.message || 'Ошибка'
  } finally {
    dealLoading.value = false
    dealSaving.value = false
  }
}

async function updateDeal() {
  dealError.value = null
  dealOk.value = null
  if (!editDeal.deal_id) return
  if (!editDeal.account_id || !editDeal.game_id || !editDeal.customer_nickname || !editDeal.platform_code) {
    dealError.value = 'Заполните аккаунт, игру, пользователя и платформу'
    return
  }
  dealLoading.value = true
  dealSaving.value = true
  try {
    await apiPut(
      `/deals/${editDeal.deal_id}`,
      {
        deal_type_code: editDeal.deal_type_code,
        account_id: editDeal.account_id,
        game_id: editDeal.game_id,
        customer_nickname: editDeal.customer_nickname,
        source_code: editDeal.source_code || null,
        platform_code: editDeal.platform_code || null,
        price: editDeal.price,
        purchase_at: editDeal.purchase_at || null,
        slots_used: editDeal.slots_used,
        notes: editDeal.notes || null,
      },
      { token: auth.state.token }
    )
    dealOk.value = 'Сделка обновлена'
    await loadDeals(dealPage.value)
    closeDealModal()
  } catch (e) {
    dealError.value = e?.message || 'Ошибка'
  } finally {
    dealLoading.value = false
    dealSaving.value = false
  }
}

async function loadDeals(page = 1) {
  dealListError.value = null
  dealListLoading.value = true
  try {
    const params = new URLSearchParams()
    if (dealFilters.account_q) params.set('account_q', dealFilters.account_q)
    if (dealFilters.game_q) params.set('game_q', dealFilters.game_q)
    if (dealFilters.type_q) params.set('type_q', dealFilters.type_q)
    if (dealFilters.status_q) params.set('status_q', dealFilters.status_q)
    if (dealFilters.customer_q) params.set('customer_q', dealFilters.customer_q)
    if (dealFilters.source_q) params.set('source_q', dealFilters.source_q)
    if (dealFilters.purchase_from) params.set('purchase_from', dealFilters.purchase_from)
    if (dealFilters.purchase_to) params.set('purchase_to', dealFilters.purchase_to)
    if (dealFilters.platform_q) params.set('platform_q', dealFilters.platform_q)
    if (dealFilters.price_min) params.set('price_min', String(dealFilters.price_min))
    if (dealFilters.price_max) params.set('price_max', String(dealFilters.price_max))
    if (dealFilters.notes_q) params.set('notes_q', dealFilters.notes_q)
    params.set('page', String(page))
    params.set('page_size', String(dealPageSize.value))
    const res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
    dealItems.value = res?.items || []
    dealTotal.value = res?.total || 0
    dealPage.value = page
  } catch (e) {
    dealListError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    catalogsError.value = e?.message || 'Ошибка'
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
    if (!games.value.length) {
      await loadGames()
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
    if (!games.value.length) {
      await loadGames()
    }
    await loadAccounts()
    showAccountFilters.value = false
    activeAccountFilter.value = ''
    return
  }
  if (tab === 'deals') {
    // стартуем список сразу, остальное догружаем параллельно
    const tasks = [loadDeals(1)]
    if (!accounts.value.length) tasks.push(loadAccounts())
    if (!games.value.length) tasks.push(loadGames())
    if (!platforms.value.length || !regions.value.length) tasks.push(loadCatalogs())
    if (!sources.value.length) tasks.push(loadSources())
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
