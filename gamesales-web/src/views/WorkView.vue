<template>
  <div class="page">
    <div class="shell">
      <header class="top">
        <div class="brand">
          <div class="logo">GS</div>
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
              <button class="btn btn--ghost" @click="showPwdForm = !showPwdForm">
                {{ showPwdForm ? 'Скрыть форму' : 'Сменить пароль' }}
              </button>
            </div>
          </div>
          <div class="panel__body">
            <div v-if="showPwdForm" class="form">
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
              <button class="btn" @click="changePassword" :disabled="pwdLoading">
                {{ pwdLoading ? 'Сохраняем…' : 'Сменить пароль' }}
              </button>
            </div>
            <p v-else class="muted">Нажмите «Сменить пароль», чтобы открыть форму.</p>
          </div>
        </section>

        <section v-if="activeTab === 'accounts'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Аккаунты</h2>
              <p class="muted">Создание аккаунтов и контроль слотов.</p>
            </div>
            <div class="toolbar-actions">
              <button class="btn btn--ghost" @click="showAccountForm = !showAccountForm">
                {{ showAccountForm ? 'Скрыть форму' : 'Добавить аккаунт' }}
              </button>
              <button class="btn btn--ghost" @click="showAccountFilters = !showAccountFilters">
                {{ showAccountFilters ? 'Скрыть фильтры' : 'Фильтр' }}
              </button>
              <button class="btn btn--ghost" @click="showPasswords = !showPasswords">
                {{ showPasswords ? 'Скрыть пароли' : 'Показать пароли' }}
              </button>
              <button class="btn btn--ghost" @click="loadAccounts" :disabled="accountsLoading">
                {{ accountsLoading ? 'Обновляем…' : 'Обновить список' }}
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
                    {{ p.name }} ({{ p.code }})
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Сортировка</span>
                <select v-model="accountSort" class="input input--select">
                  <option value="login_asc">Логин ↑</option>
                  <option value="login_desc">Логин ↓</option>
                  <option value="free_desc">Свободные слоты ↓</option>
                  <option value="free_asc">Свободные слоты ↑</option>
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

            <table v-else-if="filteredAccounts.length" class="table table--compact">
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>Платформа</th>
                  <th>Регион</th>
                  <th>Статус</th>
                  <th>Свободно</th>
                  <th>Основной пароль</th>
                  <th>Резервные</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in filteredAccounts" :key="a.account_id">
                  <td>{{ a.login_full || '—' }}</td>
                  <td>{{ a.platform_code }}</td>
                  <td>{{ a.region_code || '—' }}</td>
                  <td>{{ a.status }}</td>
                  <td>{{ a.free_slots }}/{{ a.slot_capacity }}</td>
                  <td>{{ formatSecret(getPrimarySecret(a.account_id)) }}</td>
                  <td>{{ formatSecret(getReserveSecrets(a.account_id), true) }}</td>
                  <td>
                    <button class="ghost" @click="startEditAccount(a)">Редактировать</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет аккаунтов.</p>

            <div class="divider"></div>

            <div v-if="showAccountForm" class="form form--stack form--card form--compact">
              <label class="field">
                <span class="label">Логин (без домена)</span>
                <input v-model.trim="newAccount.login_name" class="input" placeholder="user" />
              </label>
              <label class="field">
                <span class="label">Домен</span>
                <select v-model="newAccount.domain_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="d in domains" :key="d.code" :value="d.code">
                    {{ d.name }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Платформа</span>
                <select v-model="newAccount.platform_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
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
                <span class="label">Всего слотов</span>
                <input v-model.number="newAccount.slot_capacity" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Зарезервировано</span>
                <input v-model.number="newAccount.slot_reserved" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Комментарий</span>
                <input v-model.trim="newAccount.notes" class="input" placeholder="заметки" />
              </label>
              <label class="field">
                <span class="label">Основной пароль</span>
                <input v-model.trim="newAccount.primary_secret" class="input" type="password" autocomplete="new-password" />
              </label>
              <div class="field field--full">
                <span class="label">Резервные пароли</span>
                <div class="input-list">
                  <div v-for="(p, idx) in newAccount.reserve_secrets" :key="idx" class="input-list__row">
                    <input
                      v-model.trim="newAccount.reserve_secrets[idx]"
                      class="input"
                      type="password"
                      autocomplete="new-password"
                      :placeholder="`Резерв ${idx + 1}`"
                    />
                    <button class="ghost" type="button" @click="removeReserveSecret(idx)">Убрать</button>
                  </div>
                  <button class="ghost" type="button" @click="addReserveSecret">+ Добавить резервный пароль</button>
                </div>
              </div>
              <p v-if="accountsError" class="bad">{{ accountsError }}</p>
              <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
              <button class="btn" @click="createAccount" :disabled="accountsLoading">
                {{ accountsLoading ? 'Создаём…' : 'Добавить аккаунт' }}
              </button>
            </div>

            <div v-if="editAccount.open" class="form form--stack form--card form--compact">
              <h3>Редактирование аккаунта</h3>
              <label class="field">
                <span class="label">Логин (без домена)</span>
                <input v-model.trim="editAccount.login_name" class="input" placeholder="user" />
              </label>
              <label class="field">
                <span class="label">Домен</span>
                <select v-model="editAccount.domain_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="d in domains" :key="d.code" :value="d.code">
                    {{ d.name }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Платформа</span>
                <select v-model="editAccount.platform_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="p in platforms" :key="p.code" :value="p.code">
                    {{ p.name }} ({{ p.code }})
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
                <span class="label">Всего слотов</span>
                <input v-model.number="editAccount.slot_capacity" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Зарезервировано</span>
                <input v-model.number="editAccount.slot_reserved" class="input" type="number" min="0" />
              </label>
              <label class="field">
                <span class="label">Комментарий</span>
                <input v-model.trim="editAccount.notes" class="input" placeholder="заметки" />
              </label>
              <label class="field">
                <span class="label">Основной пароль</span>
                <input v-model.trim="editAccount.primary_secret" class="input" type="password" autocomplete="new-password" />
              </label>
              <div class="field field--full">
                <span class="label">Резервные пароли</span>
                <div class="input-list">
                  <div v-for="(p, idx) in editAccount.reserve_secrets" :key="idx" class="input-list__row">
                    <input
                      v-model.trim="editAccount.reserve_secrets[idx]"
                      class="input"
                      type="password"
                      autocomplete="new-password"
                      :placeholder="`Резерв ${idx + 1}`"
                    />
                    <button class="ghost" type="button" @click="removeEditReserveSecret(idx)">Убрать</button>
                  </div>
                  <button class="ghost" type="button" @click="addEditReserveSecret">+ Добавить резервный пароль</button>
                </div>
              </div>
              <p v-if="accountsError" class="bad">{{ accountsError }}</p>
              <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
              <div class="toolbar-actions">
                <button class="btn" @click="updateAccount" :disabled="accountsLoading">
                  {{ accountsLoading ? 'Сохраняем…' : 'Сохранить изменения' }}
                </button>
                <button class="btn btn--ghost" type="button" @click="cancelEditAccount">Отмена</button>
              </div>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'games'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Игры</h2>
              <p class="muted">Добавление игр в справочник.</p>
            </div>
            <div class="toolbar-actions">
              <button class="btn btn--ghost" @click="showGameForm = !showGameForm">
                {{ showGameForm ? 'Скрыть форму' : 'Добавить игру' }}
              </button>
              <button class="btn btn--ghost" @click="showGameFilters = !showGameFilters">
                {{ showGameFilters ? 'Скрыть фильтры' : 'Фильтр' }}
              </button>
              <button class="btn btn--ghost" @click="loadGames" :disabled="gamesLoading">
                {{ gamesLoading ? 'Обновляем…' : 'Обновить список' }}
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
            <table v-else-if="filteredGames.length" class="table table--compact">
              <thead>
                <tr>
                  <th>Игра</th>
                  <th>Платформа</th>
                  <th>Регион</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in filteredGames" :key="g.game_id">
                  <td>{{ g.title }}</td>
                  <td>{{ g.platform_code || '—' }}</td>
                  <td>{{ g.region_code || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет игр.</p>

            <div class="divider"></div>

            <div v-if="showGameForm" class="form form--stack form--card form--compact">
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
              <button class="btn" @click="createGame" :disabled="gameLoading">
                {{ gameLoading ? 'Сохраняем…' : 'Добавить игру' }}
              </button>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'deals'" class="panel panel--wide">
          <div class="panel__head">
            <div>
              <h2>Продажа / аренда</h2>
              <p class="muted">Фиксация выдач и продаж по аккаунтам.</p>
            </div>
            <div class="toolbar-actions">
              <button class="btn btn--ghost" @click="showDealForm = !showDealForm">
                {{ showDealForm ? 'Скрыть форму' : 'Добавить продажу' }}
              </button>
              <button class="btn btn--ghost" @click="showDealFilters = !showDealFilters">
                {{ showDealFilters ? 'Скрыть фильтры' : 'Фильтр' }}
              </button>
              <button class="btn btn--ghost" @click="loadDeals(1)" :disabled="dealListLoading">
                {{ dealListLoading ? 'Обновляем…' : 'Обновить список' }}
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
            <table v-else-if="dealItems.length" class="table">
              <thead>
                <tr>
                  <th>Аккаунт</th>
                  <th>Игра</th>
                  <th>Тип</th>
                  <th>Статус</th>
                  <th>Пользователь</th>
                  <th>Откуда</th>
                  <th>Дата покупки</th>
                  <th>Платформа</th>
                  <th>Цена</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in dealItems" :key="d.deal_id">
                  <td>{{ d.account_login || d.account_id }}</td>
                  <td>{{ d.game_title || '—' }}</td>
                  <td>{{ d.deal_type }}</td>
                  <td>{{ d.status || '—' }}</td>
                  <td>{{ d.customer_nickname || '—' }}</td>
                  <td>{{ d.source_code || '—' }}</td>
                  <td>{{ formatDate(d.purchase_at || d.created_at) }}</td>
                  <td>{{ d.platform_code || '—' }}</td>
                  <td>{{ d.price }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">Пока нет сделок.</p>

            <div class="pager">
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

            <div v-if="showDealForm" class="form form--stack form--card form--compact">
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
                  <option v-for="a in accounts" :key="a.account_id" :value="a.account_id">
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
              <button class="btn" @click="createDeal" :disabled="dealLoading">
                {{ dealLoading ? 'Сохраняем…' : 'Сохранить' }}
              </button>
            </div>
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
                  <button class="btn btn--ghost" @click="showDomainForm = !showDomainForm">
                    {{ showDomainForm ? 'Скрыть форму' : 'Добавить домен' }}
                  </button>
                  <button class="btn btn--ghost" @click="loadDomains" :disabled="catalogsLoading">
                    {{ catalogsLoading ? 'Обновляем…' : 'Обновить список' }}
                  </button>
                </div>
              </div>
              <div v-if="showDomainForm" class="form form--stack form--card form--compact">
                <label class="field">
                  <span class="label">Новый домен</span>
                  <input v-model.trim="newDomain" class="input" placeholder="example.com" />
                </label>
                <button class="btn" @click="createDomain" :disabled="catalogsLoading">
                  {{ catalogsLoading ? 'Сохраняем…' : 'Добавить домен' }}
                </button>
              </div>
              <table v-if="domains.length" class="table table--compact">
                <thead>
                  <tr>
                    <th>Домен</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in domains" :key="d.code">
                    <td>{{ d.name }}</td>
                    <td>
                      <div class="list-actions">
                        <button class="mini-btn" @click="editDomain(d.code)">Редактировать</button>
                        <button class="mini-btn mini-btn--danger" @click="deleteDomain(d.code)">Удалить</button>
                      </div>
                    </td>
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
                  <button class="btn btn--ghost" @click="showSourceForm = !showSourceForm">
                    {{ showSourceForm ? 'Скрыть форму' : 'Добавить источник' }}
                  </button>
                  <button class="btn btn--ghost" @click="loadSources" :disabled="catalogsLoading">
                    {{ catalogsLoading ? 'Обновляем…' : 'Обновить список' }}
                  </button>
                </div>
              </div>
              <div v-if="showSourceForm" class="form form--stack form--card form--compact">
                <label class="field">
                  <span class="label">Источник (код)</span>
                  <input v-model.trim="newSource.code" class="input" placeholder="tg" />
                </label>
                <label class="field">
                  <span class="label">Источник (название)</span>
                  <input v-model.trim="newSource.name" class="input" placeholder="Telegram" />
                </label>
                <button class="btn" @click="createSource" :disabled="catalogsLoading">
                  {{ catalogsLoading ? 'Сохраняем…' : 'Добавить источник' }}
                </button>
              </div>
              <table v-if="sources.length" class="table table--compact">
                <thead>
                  <tr>
                    <th>Код</th>
                    <th>Название</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in sources" :key="s.code">
                    <td>{{ s.code }}</td>
                    <td>{{ s.name }}</td>
                    <td>
                      <div class="list-actions">
                        <button class="mini-btn" @click="editSource(s.code, s.name)">Редактировать</button>
                        <button class="mini-btn mini-btn--danger" @click="deleteSource(s.code)">Удалить</button>
                      </div>
                    </td>
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
                  <button class="btn btn--ghost" @click="showPlatformForm = !showPlatformForm">
                    {{ showPlatformForm ? 'Скрыть форму' : 'Добавить платформу' }}
                  </button>
                  <button class="btn btn--ghost" @click="loadCatalogs" :disabled="catalogsLoading">
                    {{ catalogsLoading ? 'Обновляем…' : 'Обновить список' }}
                  </button>
                </div>
              </div>
              <div v-if="showPlatformForm" class="form form--stack form--card form--compact">
                <label class="field">
                  <span class="label">Платформа (код)</span>
                  <input v-model.trim="newPlatform.code" class="input" placeholder="steam" />
                </label>
                <label class="field">
                  <span class="label">Платформа (название)</span>
                  <input v-model.trim="newPlatform.name" class="input" placeholder="Steam" />
                </label>
                <button class="btn" @click="createPlatform" :disabled="catalogsLoading">
                  {{ catalogsLoading ? 'Сохраняем…' : 'Добавить платформу' }}
                </button>
              </div>
              <table v-if="platforms.length" class="table table--compact">
                <thead>
                  <tr>
                    <th>Код</th>
                    <th>Название</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in platforms" :key="p.code">
                    <td>{{ p.code }}</td>
                    <td>{{ p.name }}</td>
                    <td>
                      <div class="list-actions">
                        <button class="mini-btn" @click="editPlatform(p.code, p.name)">Редактировать</button>
                        <button class="mini-btn mini-btn--danger" @click="deletePlatform(p.code)">Удалить</button>
                      </div>
                    </td>
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
                  <button class="btn btn--ghost" @click="showRegionForm = !showRegionForm">
                    {{ showRegionForm ? 'Скрыть форму' : 'Добавить регион' }}
                  </button>
                  <button class="btn btn--ghost" @click="loadCatalogs" :disabled="catalogsLoading">
                    {{ catalogsLoading ? 'Обновляем…' : 'Обновить список' }}
                  </button>
                </div>
              </div>
              <div v-if="showRegionForm" class="form form--stack form--card form--compact">
                <label class="field">
                  <span class="label">Регион (код)</span>
                  <input v-model.trim="newRegion.code" class="input" placeholder="RU" />
                </label>
                <label class="field">
                  <span class="label">Регион (название)</span>
                  <input v-model.trim="newRegion.name" class="input" placeholder="Russia" />
                </label>
                <button class="btn" @click="createRegion" :disabled="catalogsLoading">
                  {{ catalogsLoading ? 'Сохраняем…' : 'Добавить регион' }}
                </button>
              </div>
              <table v-if="regions.length" class="table table--compact">
                <thead>
                  <tr>
                    <th>Код</th>
                    <th>Название</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in regions" :key="r.code">
                    <td>{{ r.code }}</td>
                    <td>{{ r.name }}</td>
                    <td>
                      <div class="list-actions">
                        <button class="mini-btn" @click="editRegion(r.code, r.name)">Редактировать</button>
                        <button class="mini-btn mini-btn--danger" @click="deleteRegion(r.code)">Удалить</button>
                      </div>
                    </td>
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
              <button class="btn btn--ghost" @click="showUserForm = !showUserForm">
                {{ showUserForm ? 'Скрыть форму' : 'Добавить пользователя' }}
              </button>
              <button class="btn btn--ghost" @click="loadUsers" :disabled="userLoading">
                {{ userLoading ? 'Обновляем…' : 'Обновить список' }}
              </button>
            </div>
          </div>
          <div class="panel__body">
            <div v-if="showUserForm" class="form form--stack form--card form--compact">
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
              <button class="btn" @click="createUser" :disabled="userLoading">
                {{ userLoading ? 'Создаём…' : 'Создать' }}
              </button>
            </div>
            <p v-else class="muted">Нажмите «Добавить пользователя», чтобы открыть форму.</p>

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
            <table v-else-if="users.length" class="table">
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>Роль</th>
                  <th>Создан</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in users" :key="u.username">
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

const isAdmin = computed(() => auth.state.role === 'admin')

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

const games = ref([])
const gamesLoading = ref(false)
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
const newSource = reactive({
  code: '',
  name: '',
})
const newPlatform = reactive({
  code: '',
  name: '',
})
const newRegion = reactive({
  code: '',
  name: '',
})

const newAccount = reactive({
  login_name: '',
  domain_code: '',
  platform_code: '',
  region_code: '',
  slot_capacity: 1,
  slot_reserved: 0,
  notes: '',
  primary_secret: '',
  reserve_secrets: [],
})

const showAccountForm = ref(false)
const showAccountFilters = ref(false)
const showPasswords = ref(false)
const editAccount = reactive({
  open: false,
  account_id: null,
  login_name: '',
  domain_code: '',
  platform_code: '',
  region_code: '',
  status_code: 'active',
  slot_capacity: 1,
  slot_reserved: 0,
  notes: '',
  primary_secret: '',
  primary_key: 'primary',
  reserve_secrets: [],
  existing_reserve_keys: [],
  has_primary: false,
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
  if (accountSort.value === 'login_asc') {
    list.sort((a, b) => (a.login_full || '').localeCompare(b.login_full || ''))
  } else if (accountSort.value === 'login_desc') {
    list.sort((a, b) => (b.login_full || '').localeCompare(a.login_full || ''))
  } else if (accountSort.value === 'free_desc') {
    list.sort((a, b) => (b.free_slots || 0) - (a.free_slots || 0))
  } else if (accountSort.value === 'free_asc') {
    list.sort((a, b) => (a.free_slots || 0) - (b.free_slots || 0))
  }
  return list
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

function getPrimarySecret(accountId) {
  const list = accountSecrets.value[accountId] || []
  const primary = list.find((s) => s.secret_key === 'primary' || s.secret_key === 'password')
  return primary?.secret_value_b64 ? fromBase64(primary.secret_value_b64) : ''
}

function getReserveSecrets(accountId) {
  const list = accountSecrets.value[accountId] || []
  const reserves = list
    .filter((s) => s.secret_key?.startsWith('reserve'))
    .map((s) => (s.secret_value_b64 ? fromBase64(s.secret_value_b64) : ''))
    .filter(Boolean)
  return reserves.join(', ')
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
  editAccount.open = true
  editAccount.account_id = a.account_id
  editAccount.login_name = a.login_name || ''
  editAccount.domain_code = a.domain_code || ''
  editAccount.platform_code = a.platform_code || ''
  editAccount.region_code = a.region_code || ''
  editAccount.status_code = a.status || 'active'
  editAccount.slot_capacity = a.slot_capacity || 0
  editAccount.slot_reserved = a.slot_reserved || 0
  editAccount.notes = a.notes || ''

  const secrets = accountSecrets.value[a.account_id] || []
  const primary = secrets.find((s) => s.secret_key === 'primary' || s.secret_key === 'password')
  const reserves = secrets.filter((s) => s.secret_key?.startsWith('reserve'))
  editAccount.primary_secret = primary?.secret_value_b64 ? fromBase64(primary.secret_value_b64) : ''
  editAccount.primary_key = primary?.secret_key || 'primary'
  editAccount.reserve_secrets = reserves
    .sort((a1, a2) => a1.secret_key.localeCompare(a2.secret_key))
    .map((s) => (s.secret_value_b64 ? fromBase64(s.secret_value_b64) : ''))
  editAccount.existing_reserve_keys = reserves.map((s) => s.secret_key)
  editAccount.has_primary = Boolean(primary)
}

function cancelEditAccount() {
  editAccount.open = false
  editAccount.account_id = null
  editAccount.login_name = ''
  editAccount.domain_code = ''
  editAccount.platform_code = ''
  editAccount.region_code = ''
  editAccount.status_code = 'active'
  editAccount.slot_capacity = 1
  editAccount.slot_reserved = 0
  editAccount.notes = ''
  editAccount.primary_secret = ''
  editAccount.primary_key = 'primary'
  editAccount.reserve_secrets = []
  editAccount.existing_reserve_keys = []
  editAccount.has_primary = false
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
        slot_capacity: newAccount.slot_capacity,
        slot_reserved: newAccount.slot_reserved,
        notes: newAccount.notes || null,
      },
      { token: auth.state.token }
    )

    const secretTasks = []
    if (newAccount.primary_secret) {
      secretTasks.push(
        apiPost(
          `/accounts/${created.account_id}/secrets`,
          { secret_key: 'primary', secret_value: newAccount.primary_secret },
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

    accountsOk.value = `Аккаунт ${newAccount.login_name}@${newAccount.domain_code} создан`
    newAccount.login_name = ''
    newAccount.domain_code = ''
    newAccount.platform_code = ''
    newAccount.region_code = ''
    newAccount.slot_capacity = 1
    newAccount.slot_reserved = 0
    newAccount.notes = ''
    newAccount.primary_secret = ''
    newAccount.reserve_secrets = []
    await loadAccounts()
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
  accountsLoading.value = true
  try {
    await apiPut(
      `/accounts/${editAccount.account_id}`,
      {
        platform_code: editAccount.platform_code,
        region_code: editAccount.region_code || null,
        login_name: editAccount.login_name || null,
        domain_code: editAccount.domain_code || null,
        slot_capacity: editAccount.slot_capacity,
        slot_reserved: editAccount.slot_reserved,
        notes: editAccount.notes || null,
        status_code: editAccount.status_code || 'active',
      },
      { token: auth.state.token }
    )

    const secretTasks = []
    if (editAccount.primary_secret) {
      secretTasks.push(
        apiPost(
          `/accounts/${editAccount.account_id}/secrets`,
          { secret_key: editAccount.primary_key || 'primary', secret_value: editAccount.primary_secret },
          { token: auth.state.token }
        )
      )
    } else if (editAccount.has_primary) {
      secretTasks.push(
        apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.primary_key || 'primary'}`, {
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

    accountsOk.value = 'Аккаунт обновлён'
    await loadAccounts()
    cancelEditAccount()
  } catch (e) {
    accountsError.value = e?.message || 'Ошибка'
  } finally {
    accountsLoading.value = false
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
  } catch (e) {
    userError.value = e?.message || 'Ошибка'
  } finally {
    userLoading.value = false
  }
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

async function createGame() {
  gameError.value = null
  gameOk.value = null
  if (!newGame.title) {
    gameError.value = 'Укажите название игры'
    return
  }
  gameLoading.value = true
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
  } catch (e) {
    gameError.value = e?.message || 'Ошибка'
  } finally {
    gameLoading.value = false
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
  } catch (e) {
    dealError.value = e?.message || 'Ошибка'
  } finally {
    dealLoading.value = false
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

async function createDomain() {
  catalogsError.value = null
  catalogsOk.value = null
  if (!newDomain.value) {
    catalogsError.value = 'Введите домен'
    return
  }
  catalogsLoading.value = true
  try {
    await apiPost('/domains', { name: newDomain.value }, { token: auth.state.token })
    catalogsOk.value = `Домен ${newDomain.value} добавлен`
    newDomain.value = ''
    await loadDomains()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
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
  try {
    await apiPost('/sources', newSource, { token: auth.state.token })
    catalogsOk.value = `Источник ${newSource.code} добавлен`
    newSource.code = ''
    newSource.name = ''
    await loadSources()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
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
  try {
    await apiPost('/platforms', newPlatform, { token: auth.state.token })
    catalogsOk.value = `Платформа ${newPlatform.code} добавлена`
    newPlatform.code = ''
    newPlatform.name = ''
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
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
  try {
    await apiPost('/regions', newRegion, { token: auth.state.token })
    catalogsOk.value = `Регион ${newRegion.code} добавлен`
    newRegion.code = ''
    newRegion.name = ''
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function deleteDomain(name) {
  if (!window.confirm(`Удалить домен ${name}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiDelete(`/domains/${encodeURIComponent(name)}`, { token: auth.state.token })
    catalogsOk.value = `Домен ${name} удалён`
    await loadDomains()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function deleteSource(code) {
  if (!window.confirm(`Удалить источник ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiDelete(`/sources/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Источник ${code} удалён`
    await loadSources()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function deletePlatform(code) {
  if (!window.confirm(`Удалить платформу ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiDelete(`/platforms/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Платформа ${code} удалена`
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function deleteRegion(code) {
  if (!window.confirm(`Удалить регион ${code}?`)) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiDelete(`/regions/${encodeURIComponent(code)}`, { token: auth.state.token })
    catalogsOk.value = `Регион ${code} удалён`
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function editDomain(name) {
  const next = window.prompt('Новый домен', name)
  if (!next || next === name) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiPut(`/domains/${encodeURIComponent(name)}`, { name: next }, { token: auth.state.token })
    catalogsOk.value = `Домен обновлён`
    await loadDomains()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function editSource(code, currentName) {
  const next = window.prompt('Новое название источника', currentName)
  if (!next || next === currentName) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiPut(`/sources/${encodeURIComponent(code)}`, { name: next }, { token: auth.state.token })
    catalogsOk.value = `Источник обновлён`
    await loadSources()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function editPlatform(code, currentName) {
  const next = window.prompt('Новое название платформы', currentName)
  if (!next || next === currentName) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiPut(`/platforms/${encodeURIComponent(code)}`, { name: next }, { token: auth.state.token })
    catalogsOk.value = `Платформа обновлена`
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
  }
}

async function editRegion(code, currentName) {
  const next = window.prompt('Новое название региона', currentName)
  if (!next || next === currentName) return
  catalogsError.value = null
  catalogsOk.value = null
  catalogsLoading.value = true
  try {
    await apiPut(`/regions/${encodeURIComponent(code)}`, { name: next }, { token: auth.state.token })
    catalogsOk.value = `Регион обновлён`
    await loadCatalogs()
  } catch (e) {
    catalogsError.value = e?.message || 'Ошибка'
  } finally {
    catalogsLoading.value = false
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
    return
  }
  if (tab === 'accounts') {
    if (!platforms.value.length || !regions.value.length) {
      await loadCatalogs()
    }
    if (!domains.value.length) {
      await loadDomains()
    }
    await loadAccounts()
    showAccountForm.value = false
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
  width: 28px;
  height: 28px;
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
