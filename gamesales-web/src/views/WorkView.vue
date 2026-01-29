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
            >
              Пользователи
            </button>
            <button class="tab" :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">
              Профиль
            </button>
          </nav>
          <button class="danger" @click="onLogout">Выйти</button>
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
                class="btn btn--icon btn--glow btn--glow-filter"
                :aria-label="showAccountFilters ? 'Скрыть фильтры' : 'Фильтр'"
                :title="showAccountFilters ? 'Скрыть фильтры' : 'Фильтр'"
                @click="showAccountFilters = !showAccountFilters"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
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
            <div v-if="showAccountFilters" class="form form--stack form--card form--compact">
              <label class="field">
                <span class="label">Поиск</span>
                <input v-model.trim="accountFilters.q" class="input" placeholder="логин / домен" />
              </label>
              <label class="field">
                <span class="label">Платформа</span>
                <select v-model="accountFilters.platform_code" class="input input--select">
                  <option value="">Все</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }}) — {{ p.slot_capacity }} сл.
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Сортировка</span>
                <select v-model="accountSort" class="input input--select">
                  <option value="login_asc">Логин ↑</option>
                  <option value="login_desc">Логин ↓</option>
                  <option value="platform_asc">Платформа ↑</option>
                  <option value="platform_desc">Платформа ↓</option>
                  <option value="region_asc">Регион ↑</option>
                  <option value="region_desc">Регион ↓</option>
                  <option value="status_asc">Статус ↑</option>
                  <option value="status_desc">Статус ↓</option>
                  <option value="slots_desc">Слоты ↓</option>
                  <option value="slots_asc">Слоты ↑</option>
                  <option value="date_desc">Дата ↓</option>
                  <option value="date_asc">Дата ↑</option>
                </select>
              </label>
            </div>

            <div v-if="accountsLoading" class="loader-wrap">
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
              <p class="muted">Загрузка аккаунтов…</p>
            </div>

            <table v-else-if="sortedAccounts.length" class="table table--compact">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleAccountSort('login')">Логин</th>
                  <th class="sortable" @click="toggleAccountSort('platform')">Платформа</th>
                  <th class="sortable" @click="toggleAccountSort('region')">Регион</th>
                  <th class="sortable" @click="toggleAccountSort('status')">Статус</th>
                  <th class="sortable" @click="toggleAccountSort('slots')">Слоты</th>
                  <th class="sortable" @click="toggleAccountSort('date')">Дата</th>
                  <th>Пароль почта</th>
                  <th>Пароль аккаунт</th>
                  <th>Пароль резерв</th>
                  <th>Код аутентификатора</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in sortedAccounts" :key="a.account_id" class="clickable-row" @click="startEditAccount(a)">
                  <td>{{ a.login_full || '—' }}</td>
                  <td>{{ a.platform_code }}</td>
                  <td>{{ a.region_code || '—' }}</td>
                  <td>{{ a.status }}</td>
                  <td>{{ a.occupied_slots }}/{{ a.slot_capacity }}</td>
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
                    <h3>{{ accountModalMode === 'create' ? 'Новый аккаунт' : 'Редактирование аккаунта' }}</h3>
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
                      <p class="muted">Загрузка аккаунта…</p>
                    </div>
                    <div v-else-if="accountModalMode === 'edit'" class="form form--stack form--compact">
                      <label class="field">
                        <span class="label">Логин (без домена)</span>
                        <input v-model.trim="editAccount.login_name" class="input" placeholder="user" />
                      </label>
                      <label class="field">
                        <span class="label">Домен</span>
                        <select v-model="editAccount.domain_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="d in domains" :key="d.name" :value="d.name">
                            {{ d.name }}
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Платформа</span>
                        <select v-model="editAccount.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }}) — {{ p.slot_capacity }} сл.
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Регион</span>
                        <select v-model="editAccount.region_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="r in regions" :key="r.code" :value="r.code">
                            {{ r.name }} ({{ r.code }})
                          </option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Статус</span>
                        <select v-model="editAccount.status_code" class="input input--select">
                          <option value="active">active</option>
                          <option value="banned">banned</option>
                          <option value="archived">archived</option>
                          <option value="problem">problem</option>
                        </select>
                      </label>
                      <label class="field">
                        <span class="label">Дата</span>
                        <input v-model="editAccount.account_date" class="input" type="date" />
                      </label>
                      <label class="field">
                        <span class="label">Комментарий</span>
                        <input v-model.trim="editAccount.notes" class="input" placeholder="заметки" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль почта</span>
                        <input v-model.trim="editAccount.email_password" class="input" autocomplete="new-password" />
                      </label>
                      <label class="field">
                        <span class="label">Пароль аккаунт</span>
                        <input v-model.trim="editAccount.account_password" class="input" autocomplete="new-password" />
                      </label>
                      <label class="field">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="editAccount.auth_code" class="input" placeholder="код" />
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
                          />
                          <button
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
                        <button class="ghost" type="button" @click="addEditReserveSecret">+ Добавить резервный пароль</button>
                      </div>
                      </div>
                      <div class="field field--full">
                        <span class="label">Игры</span>
                        <input v-model.trim="editAccountGameSearch" class="input" placeholder="поиск игры" />
                        <div class="check-list">
                          <label v-for="g in filteredEditAccountGames" :key="g.game_id" class="check-item">
                            <input type="checkbox" :value="g.game_id" v-model="editAccount.game_ids" />
                            <span>{{ g.title }}</span>
                          </label>
                        </div>
                      </div>
                      <p v-if="accountsError" class="bad">{{ accountsError }}</p>
                      <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
                      <div class="toolbar-actions">
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
                        <span class="label">Платформа</span>
                        <select v-model="newAccount.platform_code" class="input input--select">
                          <option value="">— не выбрано —</option>
                          <option v-for="p in platforms" :key="p.code" :value="p.code">
                            {{ p.name }} ({{ p.code }}) — {{ p.slot_capacity }} сл.
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
                        <input v-model.trim="accountGameSearch" class="input" placeholder="поиск игры" />
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
                class="btn btn--icon btn--glow btn--glow-filter"
                :title="showGameFilters ? 'Скрыть фильтры' : 'Фильтр'"
                :aria-label="showGameFilters ? 'Скрыть фильтры' : 'Фильтр'"
                @click="showGameFilters = !showGameFilters"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
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
            <div v-if="showGameFilters" class="form form--stack form--card form--compact">
              <label class="field">
                <span class="label">Поиск</span>
                <input v-model.trim="gameFilters.q" class="input" placeholder="название игры" />
              </label>
              <label class="field">
                <span class="label">Платформа</span>
                <select v-model="gameFilters.platform_code" class="input input--select">
                  <option value="">Все</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Регион</span>
                <select v-model="gameFilters.region_code" class="input input--select">
                  <option value="">Все</option>
                  <option v-for="r in regions" :key="r.code" :value="r.code">
                    {{ r.name }} ({{ r.code }})
                  </option>
                </select>
              </label>
            </div>
            <div v-if="gamesLoading" class="loader-wrap">
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
              <p class="muted">Загрузка игр…</p>
            </div>
            <table v-else-if="sortedGames.length" class="table table--compact">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleGamesSort('title')">Игра</th>
                  <th class="sortable" @click="toggleGamesSort('platform')">Платформа</th>
                  <th class="sortable" @click="toggleGamesSort('region')">Регион</th>
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
                      <p class="muted">Загрузка аккаунтов…</p>
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
                class="btn btn--icon btn--glow btn--glow-filter"
                :title="showDealFilters ? 'Скрыть фильтры' : 'Фильтр'"
                :aria-label="showDealFilters ? 'Скрыть фильтры' : 'Фильтр'"
                @click="showDealFilters = !showDealFilters"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
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
            <div v-if="showDealFilters" class="form form--stack form--card form--compact">
              <label class="field">
                <span class="label">Фильтр по аккаунту</span>
                <select v-model.number="dealFilters.account_id" class="input input--select">
                  <option value="">— все —</option>
                  <option v-for="a in accounts" :key="a.account_id" :value="a.account_id">
                    {{ a.login_full || a.account_id }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Фильтр по игре</span>
                <select v-model.number="dealFilters.game_id" class="input input--select">
                  <option value="">— все —</option>
                  <option v-for="g in games" :key="g.game_id" :value="g.game_id">
                    {{ g.title }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Фильтр по платформе</span>
                <select v-model="dealFilters.platform_code" class="input input--select">
                  <option value="">— все —</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Поиск</span>
                <input v-model.trim="dealFilters.q" class="input" placeholder="игра / логин / пользователь" />
              </label>
              <label class="field">
                <span class="label">Показывать на странице</span>
                <select v-model.number="dealPageSize" class="input input--select">
                  <option :value="10">10</option>
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
              </label>
              <button class="btn" @click="loadDeals(1)" :disabled="dealListLoading">
                {{ dealListLoading ? 'Ищем…' : 'Применить фильтры' }}
              </button>
            </div>

            <p v-if="dealListError" class="bad">{{ dealListError }}</p>
            <div v-else-if="dealListLoading" class="loader-wrap">
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
              <p class="muted">Загрузка сделок…</p>
            </div>
            <table v-else-if="sortedDeals.length" class="table">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleDealSort('account')">Аккаунт</th>
                  <th class="sortable" @click="toggleDealSort('game')">Игра</th>
                  <th class="sortable" @click="toggleDealSort('type')">Тип</th>
                  <th class="sortable" @click="toggleDealSort('status')">Статус</th>
                  <th class="sortable" @click="toggleDealSort('customer')">Пользователь</th>
                  <th class="sortable" @click="toggleDealSort('source')">Откуда</th>
                  <th class="sortable" @click="toggleDealSort('date')">Дата покупки</th>
                  <th class="sortable" @click="toggleDealSort('platform')">Платформа</th>
                  <th class="sortable" @click="toggleDealSort('price')">Цена</th>
                  <th class="sortable" @click="toggleDealSort('notes')">Комментарий</th>
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
                  <td>
                    <span class="clickable-cell" @click.stop="goToAccount(d.account_login)">{{ d.account_login || d.account_id }}</span>
                  </td>
                  <td>
                    <span class="clickable-cell" @click.stop="openDealGame(d)">{{ d.game_title || '—' }}</span>
                  </td>
                  <td>{{ d.deal_type }}</td>
                  <td>{{ d.status || '—' }}</td>
                  <td>{{ d.customer_nickname || '—' }}</td>
                  <td>{{ d.source_code || '—' }}</td>
                  <td>{{ formatDate(d.purchase_at || d.created_at) }}</td>
                  <td>{{ d.platform_code || '—' }}</td>
                  <td>{{ d.price }}</td>
                  <td>{{ d.notes || '—' }}</td>
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

            <div v-if="catalogsLoading" class="loader-wrap">
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
              <p class="muted">Загрузка справочников…</p>
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
              <p class="muted">Загрузка пользователей…</p>
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
  account_id: '',
  game_id: '',
  platform_code: '',
  q: '',
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
  platform_code: '',
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
const editAccount = reactive({
  open: false,
  account_id: null,
  login_name: '',
  domain_code: '',
  platform_code: '',
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
const showDealFilters = ref(false)
const showDomainForm = ref(false)
const showSourceForm = ref(false)
const showPlatformForm = ref(false)
const showRegionForm = ref(false)
const accountFilters = reactive({
  q: '',
  platform_code: '',
})
const accountSort = ref('login_asc')
const gamesSort = ref({ key: 'title', dir: 'asc' })
const dealSort = ref({ key: 'date', dir: 'desc' })
const usersSort = ref({ key: 'created_at', dir: 'desc' })
const domainsSortAsc = ref(true)
const sourcesSort = ref({ key: 'code', dir: 'asc' })
const platformsSort = ref({ key: 'code', dir: 'asc' })
const regionsSort = ref({ key: 'code', dir: 'asc' })

const filteredAccounts = computed(() => {
  let list = [...accounts.value]
  if (accountFilters.q) {
    const q = accountFilters.q.toLowerCase()
    list = list.filter((a) =>
      (a.login_full || '').toLowerCase().includes(q)
    )
  }
  if (accountFilters.platform_code) {
    list = list.filter((a) => a.platform_code === accountFilters.platform_code)
  }
  return list
})

const sortedAccounts = computed(() => {
  const list = [...filteredAccounts.value]
  if (accountSort.value === 'login_asc') {
    list.sort((a, b) => (a.login_full || '').localeCompare(b.login_full || ''))
  } else if (accountSort.value === 'login_desc') {
    list.sort((a, b) => (b.login_full || '').localeCompare(a.login_full || ''))
  } else if (accountSort.value === 'platform_asc') {
    list.sort((a, b) => (a.platform_code || '').localeCompare(b.platform_code || ''))
  } else if (accountSort.value === 'platform_desc') {
    list.sort((a, b) => (b.platform_code || '').localeCompare(a.platform_code || ''))
  } else if (accountSort.value === 'region_asc') {
    list.sort((a, b) => (a.region_code || '').localeCompare(b.region_code || ''))
  } else if (accountSort.value === 'region_desc') {
    list.sort((a, b) => (b.region_code || '').localeCompare(a.region_code || ''))
  } else if (accountSort.value === 'status_asc') {
    list.sort((a, b) => (a.status || '').localeCompare(b.status || ''))
  } else if (accountSort.value === 'status_desc') {
    list.sort((a, b) => (b.status || '').localeCompare(a.status || ''))
  } else if (accountSort.value === 'slots_desc') {
    list.sort((a, b) => (b.slot_capacity || 0) - (a.slot_capacity || 0))
  } else if (accountSort.value === 'slots_asc') {
    list.sort((a, b) => (a.slot_capacity || 0) - (b.slot_capacity || 0))
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
    list = list.filter((a) => a.platform_code === newDeal.platform_code)
  }
  return list
})

const dealAccountsForEdit = computed(() => {
  let list = [...accounts.value]
  if (editDeal.platform_code) {
    list = list.filter((a) => a.platform_code === editDeal.platform_code)
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
    list = list.filter((g) => g.platform_code === gameFilters.platform_code)
  }
  if (gameFilters.region_code) {
    list = list.filter((g) => g.region_code === gameFilters.region_code)
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
    platform: ['platform_asc', 'platform_desc'],
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
  accountFilters.q = login || ''
}

function openDealGame(deal) {
  if (!deal || !deal.game_id) return
  activeTab.value = 'games'
  const game = games.value.find((g) => g.game_id === deal.game_id)
  if (game) {
    openGameAccounts(game)
  }
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

function startEditAccount(a) {
  resetModalPos()
  accountModalMode.value = 'edit'
  editAccount.open = true
  editAccount.account_id = a.account_id
  editAccount.login_name = a.login_name || ''
  editAccount.domain_code = a.domain_code || ''
  editAccount.platform_code = a.platform_code || ''
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
}

function openCreateAccountModal() {
  resetModalPos()
  accountModalMode.value = 'create'
  editAccount.open = true
  accountGamesLoading.value = false
  accountsError.value = null
  accountsOk.value = null
  newAccount.login_name = ''
  newAccount.domain_code = ''
  newAccount.platform_code = ''
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
  editAccount.platform_code = ''
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
  newAccount.login_name = ''
  newAccount.domain_code = ''
  newAccount.platform_code = ''
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
  if (!newAccount.login_name || !newAccount.domain_code || !newAccount.platform_code) {
    accountsError.value = 'Укажите логин, домен и платформу'
    return
  }
  accountsLoading.value = true
  try {
    const created = await apiPost(
      '/accounts',
      {
        platform_code: newAccount.platform_code,
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
    newAccount.platform_code = ''
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
  if (!editAccount.login_name || !editAccount.domain_code || !editAccount.platform_code) {
    accountsError.value = 'Укажите логин, домен и платформу'
    return
  }
  accountSaving.value = true
  try {
    await apiPut(
      `/accounts/${editAccount.account_id}`,
      {
        platform_code: editAccount.platform_code,
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
    if (dealFilters.account_id) params.set('account_id', String(dealFilters.account_id))
    if (dealFilters.game_id) params.set('game_id', String(dealFilters.game_id))
    if (dealFilters.platform_code) params.set('platform_code', String(dealFilters.platform_code))
    if (dealFilters.q) params.set('q', dealFilters.q)
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

const syncDealPlatformFromAccount = (deal, accountsList) => {
  if (!deal.account_id) return
  const acc = accountsList.find((a) => a.account_id === deal.account_id)
  if (acc) {
    deal.platform_code = acc.platform_code || ''
  }
}

const clearDealAccountIfMismatch = (deal, accountsList) => {
  if (!deal.account_id) return
  const acc = accountsList.find((a) => a.account_id === deal.account_id)
  if (acc && deal.platform_code && acc.platform_code !== deal.platform_code) {
    deal.account_id = ''
  }
}

watch(
  () => newDeal.account_id,
  () => {
    syncDealPlatformFromAccount(newDeal, accounts.value)
  }
)

watch(
  () => newDeal.platform_code,
  () => {
    clearDealAccountIfMismatch(newDeal, accounts.value)
  }
)

watch(
  () => editDeal.account_id,
  () => {
    syncDealPlatformFromAccount(editDeal, accounts.value)
  }
)

watch(
  () => editDeal.platform_code,
  () => {
    clearDealAccountIfMismatch(editDeal, accounts.value)
  }
)

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

:root {
  --bg-1: #0c1024;
  --bg-2: #151b35;
  --bg-3: #0f2431;
  --accent: #3ee8b5;
  --accent-2: #f7b955;
  --ink: #eef2ff;
  --muted: rgba(238, 242, 255, 0.7);
  --card: rgba(10, 16, 32, 0.6);
  --stroke: rgba(255, 255, 255, 0.12);
}

.page {
  min-height: 100svh;
  padding:
    max(18px, env(safe-area-inset-top))
    max(18px, env(safe-area-inset-right))
    max(18px, env(safe-area-inset-bottom))
    max(18px, env(safe-area-inset-left));
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
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tab {
  background: rgba(11, 15, 25, 0.06);
  border: 1px solid rgba(11, 15, 25, 0.12);
  color: #4b5565;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
}

.tab:hover {
  background: rgba(11, 15, 25, 0.12);
  color: #1f2937;
}

.tab.active {
  background: linear-gradient(135deg, rgba(62, 232, 181, 0.45), rgba(247, 185, 85, 0.3));
  border-color: rgba(255, 255, 255, 0.3);
  color: #0b0f19;
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
  background: rgba(11, 15, 25, 0.06);
  border: 1px solid rgba(11, 15, 25, 0.12);
  color: #2b3441;
}

.ghost:hover {
  background: rgba(11, 15, 25, 0.12);
  color: #111827;
}

.ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.danger {
  background: #ff6b6b;
  color: white;
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

.modal {
  width: min(980px, 96vw);
  height: min(92vh, 820px);
  overflow: hidden;
  background: #f6f8fb;
  color: #111827;
  border: 1px solid rgba(17, 24, 39, 0.12);
  border-radius: 20px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 24px 60px rgba(0, 0, 0, 0.35),
    0 6px 18px rgba(0, 0, 0, 0.25);
}

.modal--auto {
  height: auto;
  max-height: min(90vh, 720px);
}

.modal--auto .modal__body {
  max-height: min(74vh, 560px);
}

.modal .label {
  color: #4b5563;
}

.modal .muted {
  color: #6b7280;
}

.modal .input {
  background: #ffffff;
  color: #111827;
  border: 1px solid rgba(17, 24, 39, 0.12);
}

.modal .btn--ghost,
.modal .ghost {
  background: rgba(17, 24, 39, 0.06);
  color: #1f2937;
  border: 1px solid rgba(17, 24, 39, 0.1);
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
  background: #f2f4f8;
  color: #1f2937;
  border: 1px solid rgba(17, 24, 39, 0.12);
  border-radius: 10px;
}

.btn--icon-plain:hover {
  background: #e8ecf3;
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
  transform: rotate(4deg) translate(-0.8em, 1.85em);
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
  from, to { transform: rotate(4deg) translate(-0.8em, 1.85em); }
  50% { transform: rotate(0) translate(-0.8em, 1.85em); }
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
  font-size: 12px;
}

.btn--ghost {
  background: rgba(255, 255, 255, 0.08);
  color: #e8eefc;
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
  background: rgba(12, 14, 24, 0.85);
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
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(8, 12, 24, 0.6);
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
  font-size: 13px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 0 0 1px rgba(17, 24, 39, 0.06),
    0 6px 18px rgba(17, 24, 39, 0.04);
}

.table th,
.table td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(17, 24, 39, 0.06);
  border-right: 1px solid rgba(17, 24, 39, 0.04);
}

.table th:last-child,
.table td:last-child {
  border-right: 0;
}

.table th {
  background: rgba(17, 24, 39, 0.03);
  font-weight: 600;
  color: #1f2937;
}

.table tr:last-child td {
  border-bottom: 0;
}

.table tbody tr:hover td {
  background: rgba(62, 232, 181, 0.08);
}

.clickable-row {
  cursor: pointer;
}

.clickable-row td {
  transition: background 0.2s ease;
}

.clickable-row:hover td {
  background: rgba(88, 130, 255, 0.08);
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
  color: #0f172a;
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
  background: linear-gradient(135deg, #3ee8b5, #7df0c6);
  color: #0b0f19;
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
