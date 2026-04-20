<template>
  <teleport to="body">
    <div
      v-if="editProduct.open || showProductForm"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeProductModal"
    >
      <div
        :ref="modalRef"
        :class="['modal', 'modal--auto', 'modal--product-editor']"
        :style="modalStyle"
      >
        <!-- Шапка модалки: действия сохранить/создать/удалить/закрыть -->
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editProduct.open ? editProductTitle : createProductTitle }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editProduct.open && productEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="updateProduct"
              :disabled="productLoading"
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
              v-if="!editProduct.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createProduct"
              :disabled="productLoading"
              aria-label="Добавить товар"
              title="Добавить товар"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editProduct.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="toggleProductEditMode"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editProduct.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="archiveProduct"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeProductModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal__body" :class="{ 'modal__body--locked': productLoading }">
          <div v-if="productLoading" class="modal__body-overlay">
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

          <!-- Редактирование существующего товара -->
          <div v-if="editProduct.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editProduct.title" class="input" placeholder="" :readonly="productEditMode === 'view'" />
            </label>
            <label v-if="isEditGameType" class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="editProduct.short_title" class="input" placeholder="" :readonly="productEditMode === 'view'" />
            </label>
            <template v-if="isEditGameType">
              <label class="field">
                <span class="label">Язык текста</span>
                <input
                  v-if="productEditMode === 'view'"
                  class="input"
                  :value="editProduct.text_lang || '— не выбрано —'"
                  readonly
                />
                <select v-else v-model="editProduct.text_lang" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="lang in gameTextLanguageOptions" :key="`edit-text-lang-${lang}`" :value="lang">
                    {{ lang }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Язык озвучки</span>
                <input
                  v-if="productEditMode === 'view'"
                  class="input"
                  :value="editProduct.audio_lang || '— не выбрано —'"
                  readonly
                />
                <select v-else v-model="editProduct.audio_lang" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="lang in gameAudioLanguageOptions" :key="`edit-audio-lang-${lang}`" :value="lang">
                    {{ lang }}
                  </option>
                </select>
              </label>
              <div class="deal-form__double field--full">
                <label class="field">
                  <span class="label">Поддержка VR</span>
                  <input
                    v-if="productEditMode === 'view'"
                    class="input"
                    :value="editProduct.vr_support || '— не выбрано —'"
                    readonly
                  />
                  <select v-else v-model="editProduct.vr_support" class="input input--select">
                    <option value="">— не выбрано —</option>
                    <option v-for="vrMode in gameVrOptions" :key="`edit-vr-${vrMode}`" :value="vrMode">
                      {{ vrMode }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span class="label">Регион</span>
                  <input
                    v-if="productEditMode === 'view'"
                    class="input"
                    :value="getRegionLabel(editProduct.region_code)"
                    readonly
                  />
                  <select v-else v-model="editProduct.region_code" class="input input--select">
                    <option value="">— не выбрано —</option>
                    <option v-for="r in regions" :key="r.code" :value="r.code">
                      {{ r.name }} ({{ r.code }})
                    </option>
                  </select>
                </label>
              </div>
              <div class="field field--full">
                <span class="label account-products-title">Аккаунты</span>
                <div v-if="productEditMode === 'view'" class="pill-list">
                  <span v-for="title in editProductAccountTitles" :key="`product-edit-account-pill-${title}`" class="pill">{{ title }}</span>
                  <span v-if="!editProductAccountTitles.length" class="muted">Пока нет привязанных аккаунтов.</span>
                </div>
                <div v-else>
                  <label class="field">
                    <span class="label">Поиск</span>
                    <input v-model.trim="editProductAccountSearch" class="input" placeholder="поиск" />
                  </label>
                  <div class="check-list check-list--account-products">
                    <label v-for="a in filteredEditProductAccounts" :key="`product-edit-account-${a.account_id}`" class="check-item">
                      <input type="checkbox" :value="a.account_id" v-model="editProduct.account_ids" />
                      <span>{{ formatAccountTitle(a) }}</span>
                    </label>
                  </div>
                </div>
              </div>
              <div v-if="productEditMode !== 'view'" class="quick-create quick-create--account">
                <div class="quick-create__header">
                  <button class="comment-toggle" type="button" @click="editQuickAccountOpen = !editQuickAccountOpen">
                    {{ editQuickAccountOpen ? 'Быстрое создание аккаунта' : '+ Быстрое создание аккаунта' }}
                  </button>
                  <button
                    v-if="editQuickAccountOpen"
                    class="ghost ghost--small"
                    type="button"
                    :disabled="quickEditProductAccountLoading"
                    @click="createQuickProductAccount('edit')"
                  >
                    <span v-if="quickEditProductAccountLoading" class="spinner spinner--small"></span>
                    Создать
                  </button>
                </div>
                <template v-if="editQuickAccountOpen">
                  <div class="deal-form__double">
                    <input v-model.trim="quickEditProductAccount.login_name" class="input input--compact" placeholder="Логин" />
                    <select v-model="quickEditProductAccount.domain_code" class="input input--select input--compact">
                      <option value="">— домен —</option>
                      <option v-for="d in domains" :key="`product-edit-domain-${d.code}`" :value="d.code">
                        {{ d.name }} ({{ d.code }})
                      </option>
                    </select>
                  </div>
                  <div class="check-list check-list--compact check-list--platform-row">
                    <label v-for="p in platforms" :key="`product-edit-platform-${p.code}`" class="check-item">
                      <input type="checkbox" :value="p.code" v-model="quickEditProductAccount.platform_codes" />
                      <span>{{ p.name }} ({{ p.code }})</span>
                    </label>
                  </div>
                  <span v-if="quickEditProductAccountError" class="bad">{{ quickEditProductAccountError }}</span>
                </template>
              </div>
              <div class="field field--full">
                <span class="label">Платформа</span>
                <div class="check-list check-list--compact">
                  <label v-for="p in platforms" :key="p.code" class="check-item">
                    <input type="checkbox" :value="p.code" v-model="editProduct.platform_codes" :disabled="productEditMode === 'view'" />
                    <span>{{ p.name }} ({{ p.code }})</span>
                  </label>
                </div>
              </div>
              <label class="field field--full">
                <span class="label">Ссылка</span>
                <input v-model.trim="editProduct.link" class="input" placeholder="https://..." :readonly="productEditMode === 'view'" />
              </label>
              <div class="field field--comment-collapsible field--full">
                <button class="comment-toggle" type="button" @click="editProductCommentOpen = !editProductCommentOpen" :disabled="productEditMode === 'view'">
                  {{ editProductCommentOpen || editProduct.subscription_notes ? 'Комментарий' : '+ Комментарий' }}
                </button>
                <textarea
                  v-if="editProductCommentOpen || editProduct.subscription_notes"
                  v-model.trim="editProduct.subscription_notes"
                  class="input input--textarea input--textarea--compact"
                  :rows="getCompactNotesRows(editProduct.subscription_notes)"
                  :readonly="productEditMode === 'view'"
                />
              </div>
            </template>
            <template v-else>
              <label class="field">
                <span class="label">Регион</span>
                <input
                  v-if="productEditMode === 'view'"
                  class="input"
                  :value="getRegionLabel(editProduct.region_code)"
                  readonly
                />
                <select v-else v-model="editProduct.region_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="r in regions" :key="r.code" :value="r.code">
                    {{ r.name }} ({{ r.code }})
                  </option>
                </select>
              </label>
              <div v-if="false && productEditMode !== 'view'" class="field field--full quick-create quick-create--subscription-term">
                <div class="quick-create__header">
                  <button class="comment-toggle" type="button" @click="subscriptionTermOpen = !subscriptionTermOpen">
                    {{ subscriptionTermOpen ? 'Добавить срок подписки' : '+ Добавить срок подписки' }}
                  </button>
                  <button
                    v-if="subscriptionTermOpen"
                    class="ghost ghost--small"
                    type="button"
                    :disabled="subscriptionTermLoading"
                    @click="addSubscriptionTerm"
                  >
                    <span v-if="subscriptionTermLoading" class="spinner spinner--small"></span>
                    Добавить
                  </button>
                </div>
                <template v-if="subscriptionTermOpen">
                  <label class="field">
                    <span class="label">Поиск аккаунта</span>
                    <input v-model.trim="subscriptionTermAccountSearch" class="input input--compact" placeholder="login@domain" />
                  </label>
                  <div class="check-list check-list--account-products">
                    <label
                      v-for="a in filteredSubscriptionTermAccounts"
                      :key="`subscription-term-account-${a.account_id}`"
                      class="check-item"
                    >
                      <input type="radio" :value="a.account_id" v-model.number="subscriptionTermForm.account_id" name="subscription-term-account" />
                      <span>{{ formatAccountTitle(a) }}</span>
                    </label>
                    <span v-if="!filteredSubscriptionTermAccounts.length" class="muted">Аккаунты не найдены</span>
                  </div>
                  <input v-model="subscriptionTermForm.valid_until" type="date" class="input input--compact" />
                  <span v-if="subscriptionTermError" class="bad">{{ subscriptionTermError }}</span>
                </template>
              </div>
              <div v-if="false && productEditMode !== 'view'" class="field field--full quick-create quick-create--account">
                <div class="quick-create__header">
                  <button class="comment-toggle" type="button" @click="editQuickAccountOpen = !editQuickAccountOpen">
                    {{ editQuickAccountOpen ? 'Быстрое создание аккаунта' : '+ Быстрое создание аккаунта' }}
                  </button>
                  <button
                    v-if="editQuickAccountOpen"
                    class="ghost ghost--small"
                    type="button"
                    :disabled="quickEditProductAccountLoading"
                    @click="createQuickProductAccount('edit')"
                  >
                    <span v-if="quickEditProductAccountLoading" class="spinner spinner--small"></span>
                    Создать
                  </button>
                </div>
                <template v-if="editQuickAccountOpen">
                  <div class="deal-form__double">
                    <input v-model.trim="quickEditProductAccount.login_name" class="input input--compact" placeholder="Логин" />
                    <select v-model="quickEditProductAccount.domain_code" class="input input--select input--compact">
                      <option value="">— домен —</option>
                      <option v-for="d in domains" :key="`product-edit-domain-sub-${d.code}`" :value="d.code">
                        {{ d.name }} ({{ d.code }})
                      </option>
                    </select>
                  </div>
                  <div class="check-list check-list--compact check-list--platform-row">
                    <label v-for="p in platforms" :key="`product-edit-platform-sub-${p.code}`" class="check-item">
                      <input type="checkbox" :value="p.code" v-model="quickEditProductAccount.platform_codes" />
                      <span>{{ p.name }} ({{ p.code }})</span>
                    </label>
                  </div>
                  <span v-if="quickEditProductAccountError" class="bad">{{ quickEditProductAccountError }}</span>
                </template>
              </div>
              <div class="field field--full">
                <span class="label">Платформа</span>
                <div class="check-list check-list--compact">
                  <label v-for="p in platforms" :key="p.code" class="check-item">
                    <input type="checkbox" :value="p.code" v-model="editProduct.platform_codes" :disabled="productEditMode === 'view'" />
                    <span>{{ p.name }} ({{ p.code }})</span>
                  </label>
                </div>
              </div>
            </template>
            <div class="divider"></div>
            <div v-if="!isEditGameType" class="field field--full">
              <span class="label">Сроки подписки ({{ productSubscriptionTermsCount }})</span>
              <p v-if="productSubscriptionTermsErrorText" class="bad">{{ productSubscriptionTermsErrorText }}</p>
              <div v-else-if="productSubscriptionTermsLoadingState" class="loader-wrap loader-wrap--compact">
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
              <table v-else-if="sortedProductSubscriptionTerms.length" class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th>
                      <span class="th-title th-title--filter">
                        Дата
                        <span class="th-actions">
                          <button
                            class="filter-icon filter-icon--sort"
                            type="button"
                            aria-label="Сортировка сроков по дате"
                            title="Сортировка сроков по дате"
                            @click.stop="toggleSubscriptionTermsSort('valid_until')"
                            :class="getSubscriptionTermsSortClass('valid_until')"
                          >
                            <svg viewBox="0 0 24 24">
                              <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                              <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                            </svg>
                          </button>
                        </span>
                      </span>
                    </th>
                    <th>
                      <span class="th-title th-title--filter">
                        Статус
                        <span class="th-actions">
                          <button
                            class="filter-icon filter-icon--sort"
                            type="button"
                            aria-label="Сортировка сроков по статусу"
                            title="Сортировка сроков по статусу"
                            @click.stop="toggleSubscriptionTermsSort('status')"
                            :class="getSubscriptionTermsSortClass('status')"
                          >
                            <svg viewBox="0 0 24 24">
                              <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                              <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                            </svg>
                          </button>
                        </span>
                      </span>
                    </th>
                    <th>
                      <span class="th-title th-title--filter">
                        Аккаунт
                        <span class="th-actions">
                          <button
                            class="filter-icon filter-icon--sort"
                            type="button"
                            aria-label="Сортировка сроков по аккаунту"
                            title="Сортировка сроков по аккаунту"
                            @click.stop="toggleSubscriptionTermsSort('account')"
                            :class="getSubscriptionTermsSortClass('account')"
                          >
                            <svg viewBox="0 0 24 24">
                              <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                              <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                            </svg>
                          </button>
                        </span>
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="term in pagedProductSubscriptionTerms" :key="`product-subscription-term-${term.term_id}`">
                    <td>{{ formatTermDateLabel(term.valid_until) }}</td>
                    <td>{{ term.occupied ? 'занят' : 'свободен' }}</td>
                    <td>{{ term.login_full || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="productSubscriptionTermsTotalPages > 1" class="pager">
                <button class="ghost" type="button" @click="prevProductSubscriptionTermsPage" :disabled="productSubscriptionTermsPage <= 1">
                  ← Назад
                </button>
                <span class="muted">Страница {{ productSubscriptionTermsPage }} из {{ productSubscriptionTermsTotalPages }}</span>
                <button class="ghost" type="button" @click="nextProductSubscriptionTermsPage" :disabled="productSubscriptionTermsPage >= productSubscriptionTermsTotalPages">
                  Вперёд →
                </button>
              </div>
              <p
                v-if="!productSubscriptionTermsErrorText && !productSubscriptionTermsLoadingState && !sortedProductSubscriptionTerms.length"
                class="muted"
              >
                Сроков подписки пока нет.
              </p>
            </div>
            <div v-if="!isEditGameType" class="field field--comment-collapsible field--full">
              <button class="comment-toggle" type="button" @click="editProductCommentOpen = !editProductCommentOpen" :disabled="productEditMode === 'view'">
                {{ editProductCommentOpen || editProduct.subscription_notes ? 'Комментарий' : '+ Комментарий' }}
              </button>
              <textarea
                v-if="editProductCommentOpen || editProduct.subscription_notes"
                v-model.trim="editProduct.subscription_notes"
                class="input input--textarea input--textarea--compact"
                :rows="getCompactNotesRows(editProduct.subscription_notes)"
                :readonly="productEditMode === 'view'"
              />
            </div>
            <div v-if="isEditGameType" class="field field--full">
              <button
                class="section-toggle"
                type="button"
                :aria-expanded="productAccountsOpen ? 'true' : 'false'"
                @click="productAccountsOpen = !productAccountsOpen"
              >
                <span class="label">{{ isEditGameType ? `Сделок (${productAccountsCount}):` : `(${productAccountsCount})` }}</span>
                <svg class="section-toggle__chevron" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
              <template v-if="productAccountsOpen">
                <p v-if="productAccountsError" class="bad">{{ productAccountsError }}</p>
                <div v-if="productAccountsLoading" class="loader-wrap loader-wrap--compact">
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
                <table v-else-if="pagedProductAccounts.length" ref="accountsTableEl" class="table table--compact table--dense">
                  <colgroup>
                    <col :style="getProductAccountsColumnStyle('account')" />
                    <col :style="getProductAccountsColumnStyle('user')" />
                    <col :style="getProductAccountsColumnStyle('date')" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Аккаунт
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка по аккаунту"
                              title="Сортировка по аккаунту"
                              @click.stop="sortProductAccounts('login_full')"
                              :class="getProductAccountsSortClass('login_full')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Аккаунт"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductAccountsResize($event, 'account')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Пользователь
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка по пользователю"
                              title="Сортировка по пользователю"
                              @click.stop="sortProductAccounts('customer_nickname')"
                              :class="getProductAccountsSortClass('customer_nickname')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Пользователь"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductAccountsResize($event, 'user')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Дата сделки
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка по дате сделки"
                              title="Сортировка по дате сделки"
                              @click.stop="sortProductAccounts('deal_date')"
                              :class="getProductAccountsSortClass('deal_date')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Дата сделки"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductAccountsResize($event, 'date')"
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="a in pagedProductAccounts" :key="a.deal_item_id || `${a.account_id}-${a.deal_date || ''}`">
                      <td class="product-account-cell" @click="openAccountFromCell(a.login_full)">
                        <span class="product-account-cell__text">{{ a.login_full || '—' }}</span>
                      </td>
                      <td>{{ a.customer_nickname || '—' }}</td>
                      <td>{{ a.deal_date ? formatDateTimeMinutes(a.deal_date) : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Сделок по товару пока нет.</p>
                <div v-if="productAccountsTotalPages > 1" class="pager">
                  <button class="ghost" @click="prevProductAccountsPage" :disabled="productAccountsPage <= 1">
                    ← Назад
                  </button>
                  <span class="muted">Страница {{ productAccountsPage }} из {{ productAccountsTotalPages }}</span>
                  <button class="ghost" @click="nextProductAccountsPage" :disabled="productAccountsPage >= productAccountsTotalPages">
                    Вперёд →
                  </button>
                </div>
              </template>
            </div>
            <div v-if="isEditGameType" class="field field--full">
              <button
                class="section-toggle"
                type="button"
                :aria-expanded="productSlotsOpen ? 'true' : 'false'"
                @click="productSlotsOpen = !productSlotsOpen"
              >
                <span class="label">{{ isEditGameType ? `Слоты по товару (${productSlotsCount})` : `(${productSlotsCount})` }}</span>
                <svg class="section-toggle__chevron" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
              <template v-if="productSlotsOpen">
                <p v-if="productSlotAssignmentsError" class="bad">{{ productSlotAssignmentsError }}</p>
                <div v-if="productSlotAssignmentsLoading" class="loader-wrap loader-wrap--compact">
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
                <table v-else-if="pagedProductSlotAssignments.length" ref="slotsTableEl" class="table table--compact table--dense">
                  <colgroup>
                    <col :style="getProductSlotsColumnStyle('account')" />
                    <col :style="getProductSlotsColumnStyle('slot')" />
                    <col :style="getProductSlotsColumnStyle('customer')" />
                    <col :style="getProductSlotsColumnStyle('status')" />
                    <col :style="getProductSlotsColumnStyle('assigned')" />
                    <col :style="getProductSlotsColumnStyle('released')" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Аккаунт
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по аккаунту"
                              title="Сортировка слотов по аккаунту"
                              @click.stop="toggleProductSlotsSort('account')"
                              :class="getProductSlotsSortClass('account')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Аккаунт слотов"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductSlotsResize($event, 'account')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Слот
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по типу"
                              title="Сортировка слотов по типу"
                              @click.stop="toggleProductSlotsSort('slot')"
                              :class="getProductSlotsSortClass('slot')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Слот"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductSlotsResize($event, 'slot')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Покупатель
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по покупателю"
                              title="Сортировка слотов по покупателю"
                              @click.stop="toggleProductSlotsSort('customer')"
                              :class="getProductSlotsSortClass('customer')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Покупатель слотов"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductSlotsResize($event, 'customer')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Статус
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по статусу"
                              title="Сортировка слотов по статусу"
                              @click.stop="toggleProductSlotsSort('status')"
                              :class="getProductSlotsSortClass('status')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Статус слотов"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductSlotsResize($event, 'status')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Назначено
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по дате назначения"
                              title="Сортировка слотов по дате назначения"
                              @click.stop="toggleProductSlotsSort('assigned')"
                              :class="getProductSlotsSortClass('assigned')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                        <button
                          class="table-col-resizer"
                          type="button"
                          aria-label="Изменить ширину колонки Назначено"
                          title="Потяните для изменения ширины"
                          @mousedown.stop.prevent="startProductSlotsResize($event, 'assigned')"
                        />
                      </th>
                      <th class="sortable">
                        <span class="th-title th-title--filter">
                          Снято
                          <span class="th-actions">
                            <button
                              class="filter-icon filter-icon--sort"
                              type="button"
                              aria-label="Сортировка слотов по дате снятия"
                              title="Сортировка слотов по дате снятия"
                              @click.stop="toggleProductSlotsSort('released')"
                              :class="getProductSlotsSortClass('released')"
                            >
                              <svg viewBox="0 0 24 24">
                                <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                                <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                              </svg>
                            </button>
                          </span>
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="s in pagedProductSlotAssignments" :key="s.assignment_id">
                      <td>{{ s.account_login || s.account_id || '—' }}</td>
                      <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                      <td>{{ s.customer_nickname || '—' }}</td>
                      <td>{{ getSlotAssignmentStatus(s) }}</td>
                      <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                      <td>{{ s.released_at ? formatDateTimeMinutes(s.released_at) : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="muted">Слотов по товару пока нет.</p>
                <div v-if="productSlotsTotalPages > 1" class="pager">
                  <button class="ghost" @click="prevProductSlotsPage" :disabled="productSlotsPage <= 1">
                    ← Назад
                  </button>
                  <span class="muted">Страница {{ productSlotsPage }} из {{ productSlotsTotalPages }}</span>
                  <button class="ghost" @click="nextProductSlotsPage" :disabled="productSlotsPage >= productSlotsTotalPages">
                    Вперёд →
                  </button>
                </div>
              </template>
            </div>
            <p v-if="productError" class="bad">{{ productError }}</p>
            <p v-if="productOk" class="ok">{{ productOk }}</p>
          </div>

          <!-- Создание нового товара -->
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="newProduct.title" class="input" placeholder="" />
            </label>
            <label v-if="newProduct.type_code === PRODUCT_TYPE_PRIMARY" class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="newProduct.short_title" class="input" placeholder="" />
            </label>
            <template v-if="newProduct.type_code === PRODUCT_TYPE_PRIMARY">
              <label class="field">
                <span class="label">Язык текста</span>
                <select v-model="newProduct.text_lang" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="lang in gameTextLanguageOptions" :key="`new-text-lang-${lang}`" :value="lang">
                    {{ lang }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="label">Язык озвучки</span>
                <select v-model="newProduct.audio_lang" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="lang in gameAudioLanguageOptions" :key="`new-audio-lang-${lang}`" :value="lang">
                    {{ lang }}
                  </option>
                </select>
              </label>
              <div class="deal-form__double field--full">
                <label class="field">
                  <span class="label">Поддержка VR</span>
                  <select v-model="newProduct.vr_support" class="input input--select">
                    <option value="">— не выбрано —</option>
                    <option v-for="vrMode in gameVrOptions" :key="`new-vr-${vrMode}`" :value="vrMode">
                      {{ vrMode }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span class="label">Регион</span>
                  <select v-model="newProduct.region_code" class="input input--select">
                    <option value="">— не выбрано —</option>
                    <option v-for="r in regions" :key="r.code" :value="r.code">
                      {{ r.name }} ({{ r.code }})
                    </option>
                  </select>
                </label>
              </div>
              <div class="field field--full">
                <span class="label account-products-title">Аккаунты</span>
                <label class="field">
                  <span class="label">Поиск</span>
                  <input v-model.trim="newProductAccountSearch" class="input" placeholder="поиск" />
                </label>
                <div class="check-list check-list--account-products">
                  <label v-for="a in filteredNewProductAccounts" :key="`product-new-account-${a.account_id}`" class="check-item">
                    <input type="checkbox" :value="a.account_id" v-model="newProduct.account_ids" />
                    <span>{{ formatAccountTitle(a) }}</span>
                  </label>
                </div>
              </div>
              <div class="quick-create quick-create--account">
                <div class="quick-create__header">
                  <button class="comment-toggle" type="button" @click="newQuickAccountOpen = !newQuickAccountOpen">
                    {{ newQuickAccountOpen ? 'Быстрое создание аккаунта' : '+ Быстрое создание аккаунта' }}
                  </button>
                  <button
                    v-if="newQuickAccountOpen"
                    class="ghost ghost--small"
                    type="button"
                    :disabled="quickNewProductAccountLoading"
                    @click="createQuickProductAccount('new')"
                  >
                    <span v-if="quickNewProductAccountLoading" class="spinner spinner--small"></span>
                    Создать
                  </button>
                </div>
                <template v-if="newQuickAccountOpen">
                  <div class="deal-form__double">
                    <input v-model.trim="quickNewProductAccount.login_name" class="input input--compact" placeholder="Логин" />
                    <select v-model="quickNewProductAccount.domain_code" class="input input--select input--compact">
                      <option value="">— домен —</option>
                      <option v-for="d in domains" :key="`product-new-domain-${d.code}`" :value="d.code">
                        {{ d.name }} ({{ d.code }})
                      </option>
                    </select>
                  </div>
                  <div class="check-list check-list--compact check-list--platform-row">
                    <label v-for="p in platforms" :key="`product-new-platform-${p.code}`" class="check-item">
                      <input type="checkbox" :value="p.code" v-model="quickNewProductAccount.platform_codes" />
                      <span>{{ p.name }} ({{ p.code }})</span>
                    </label>
                  </div>
                  <span v-if="quickNewProductAccountError" class="bad">{{ quickNewProductAccountError }}</span>
                </template>
              </div>
              <div class="field field--full">
                <span class="label">Платформа</span>
                <div class="check-list check-list--compact">
                  <label v-for="p in platforms" :key="p.code" class="check-item">
                    <input type="checkbox" :value="p.code" v-model="newProduct.platform_codes" />
                    <span>{{ p.name }} ({{ p.code }})</span>
                  </label>
                </div>
              </div>
              <label class="field field--full">
                <span class="label">Ссылка</span>
                <input v-model.trim="newProduct.link" class="input" placeholder="https://..." />
              </label>
              <div class="field field--comment-collapsible field--full">
                <button class="comment-toggle" type="button" @click="newProductCommentOpen = !newProductCommentOpen">
                  {{ newProductCommentOpen || newProduct.subscription_notes ? 'Комментарий' : '+ Комментарий' }}
                </button>
                <textarea
                  v-if="newProductCommentOpen || newProduct.subscription_notes"
                  v-model.trim="newProduct.subscription_notes"
                  class="input input--textarea input--textarea--compact"
                  :rows="getCompactNotesRows(newProduct.subscription_notes)"
                />
              </div>
            </template>
            <template v-else>
              <label class="field">
                <span class="label">Регион</span>
                <select v-model="newProduct.region_code" class="input input--select">
                  <option value="">— не выбрано —</option>
                  <option v-for="r in regions" :key="r.code" :value="r.code">
                    {{ r.name }} ({{ r.code }})
                  </option>
                </select>
              </label>
              <div class="field field--full">
                <span class="label">Платформа</span>
                <div class="check-list check-list--compact">
                  <label v-for="p in platforms" :key="p.code" class="check-item">
                    <input type="checkbox" :value="p.code" v-model="newProduct.platform_codes" />
                    <span>{{ p.name }} ({{ p.code }})</span>
                  </label>
                </div>
              </div>
              <div class="field field--comment-collapsible field--full">
                <button class="comment-toggle" type="button" @click="newProductCommentOpen = !newProductCommentOpen">
                  {{ newProductCommentOpen || newProduct.subscription_notes ? 'Комментарий' : '+ Комментарий' }}
                </button>
                <textarea
                  v-if="newProductCommentOpen || newProduct.subscription_notes"
                  v-model.trim="newProduct.subscription_notes"
                  class="input input--textarea input--textarea--compact"
                  :rows="getCompactNotesRows(newProduct.subscription_notes)"
                />
              </div>
            </template>
            <p v-if="productError" class="bad">{{ productError }}</p>
            <p v-if="productOk" class="ok">{{ productOk }}</p>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, reactive, ref, toRefs, watch } from 'vue'
import { PRODUCT_TYPE_PRIMARY } from '../domainUtils'
import { useResizableTableColumns } from '../useResizableTableColumns'

// Передаем один объект контекста, чтобы не раздувать длинный список props.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)
// Фиксированные значения для полей игры, чтобы исключить разнобой в карточках.
const gameTextLanguageOptions = ['RU']
const gameAudioLanguageOptions = ['RU']
const gameVrOptions = ['VR1', 'VR2']

const {
  editProduct,
  showProductForm,
  closeProductModal,
  modalRef,
  modalStyle,
  startModalDrag,
  productEditMode,
  updateProduct,
  toggleProductEditMode,
  productLoading,
  createProduct,
  archiveProduct,
  platforms,
  getRegionLabel,
  regions,
  productAccountsError,
  productAccountsLoading,
  productAccounts,
  pagedProductAccounts,
  productAccountsSort,
  productAccountOptions,
  sortProductAccounts,
  openAccountFromProduct,
  productAccountsTotalPages,
  productAccountsPage,
  prevProductAccountsPage,
  nextProductAccountsPage,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  productSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  productError,
  productOk,
  newProduct,
  domains,
  createQuickProductAccount,
  quickNewProductAccount,
  quickNewProductAccountLoading,
  quickNewProductAccountError,
  quickEditProductAccount,
  quickEditProductAccountLoading,
  quickEditProductAccountError,
} = toRefs(ctx)

// Заголовок новой карточки зависит от типа товара, который выбран кнопкой в шапке вкладки.
const createProductTitle = computed(() => (
  (newProduct.value?.type_code || PRODUCT_TYPE_PRIMARY) === PRODUCT_TYPE_PRIMARY
    ? 'НОВЫЙ ТОВАР - ИГРА'
    : 'НОВЫЙ ТОВАР - ПОДПИСКА'
))

const isEditGameType = computed(() => (editProduct.value?.type_code || PRODUCT_TYPE_PRIMARY) === PRODUCT_TYPE_PRIMARY)

// В заголовке редактирования показываем тип товара и текущее название.
const editProductTitle = computed(() => {
  const typeLabel = isEditGameType.value ? 'ИГРА' : 'ПОДПИСКА'
  const title = String(editProduct.value?.title || '').trim()
  return `ТОВАР (${typeLabel}) - ${title || 'БЕЗ НАЗВАНИЯ'}`
})

const newProductCommentOpen = ref(false)
const editProductCommentOpen = ref(false)
const newQuickAccountOpen = ref(false)
const editQuickAccountOpen = ref(false)
const newProductAccountSearch = ref('')
const editProductAccountSearch = ref('')
const productAccountsOpen = ref(false)
const productSlotsOpen = ref(false)
const productSlotsPage = ref(1)
const productSlotsPageSize = 10
const productSlotsSort = ref({ key: 'assigned', dir: 'desc' })
const productSubscriptionTermsPage = ref(1)
const productSubscriptionTermsPageSize = 10
const subscriptionTermsSort = ref({ key: 'valid_until', dir: 'asc' })
const subscriptionTermOpen = ref(false)
// Возвращает дату в формате input[type=date] как сегодня + 1 год.
const getDefaultSubscriptionTermDate = () => {
  const nextYearDate = new Date()
  nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
  const year = nextYearDate.getFullYear()
  const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
  const day = String(nextYearDate.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const subscriptionTermForm = reactive({ account_id: '', valid_until: getDefaultSubscriptionTermDate() })
const subscriptionTermAccountSearch = ref('')
const subscriptionTermLoading = ref(false)
const subscriptionTermError = ref('')
const accountsTableEl = ref(null)
const slotsTableEl = ref(null)

const { getColumnStyle: getProductAccountsColumnStyle, startResize: startProductAccountsResize } = useResizableTableColumns({
  tableRef: accountsTableEl,
  storageKey: 'work.productmodal.accounts.columns.v1',
  columns: [
    { key: 'account', defaultWidth: 44, minWidth: 24 },
    { key: 'user', defaultWidth: 28, minWidth: 16 },
    { key: 'date', defaultWidth: 28, minWidth: 16 },
  ],
})

const { getColumnStyle: getProductSlotsColumnStyle, startResize: startProductSlotsResize } = useResizableTableColumns({
  tableRef: slotsTableEl,
  storageKey: 'work.productmodal.slots.columns.v1',
  columns: [
    { key: 'account', defaultWidth: 18, minWidth: 12 },
    { key: 'slot', defaultWidth: 12, minWidth: 10 },
    { key: 'customer', defaultWidth: 18, minWidth: 12 },
    { key: 'status', defaultWidth: 16, minWidth: 10 },
    { key: 'assigned', defaultWidth: 18, minWidth: 12 },
    { key: 'released', defaultWidth: 18, minWidth: 12 },
  ],
})

const productAccountsCount = computed(() => (Array.isArray(productAccounts.value) ? productAccounts.value.length : 0))
const productSlotsCount = computed(() => (Array.isArray(productSlotAssignments.value) ? productSlotAssignments.value.length : 0))
const productSubscriptionTermsList = computed(() => (
  Array.isArray(ctx.productSubscriptionTerms) ? ctx.productSubscriptionTerms : []
))
const productSubscriptionTermsCount = computed(() => productSubscriptionTermsList.value.length)
const sortedProductSubscriptionTerms = computed(() => {
  const list = [...productSubscriptionTermsList.value]
  const { key, dir } = subscriptionTermsSort.value
  const factor = dir === 'asc' ? 1 : -1
  list.sort((a, b) => {
    const av = getSubscriptionTermSortValue(a, key)
    const bv = getSubscriptionTermSortValue(b, key)
    if (typeof av === 'number' && typeof bv === 'number') {
      if (av !== bv) return (av - bv) * factor
      return (Number(a?.term_id || 0) - Number(b?.term_id || 0)) * factor
    }
    return String(av || '').localeCompare(String(bv || '')) * factor
  })
  return list
})
// Делит список сроков подписки на страницы, чтобы не растягивать форму.
const productSubscriptionTermsTotalPages = computed(() => {
  const pages = Math.ceil(productSubscriptionTermsCount.value / productSubscriptionTermsPageSize)
  return pages > 0 ? pages : 1
})
const pagedProductSubscriptionTerms = computed(() => {
  const start = (productSubscriptionTermsPage.value - 1) * productSubscriptionTermsPageSize
  return sortedProductSubscriptionTerms.value.slice(start, start + productSubscriptionTermsPageSize)
})
const productSubscriptionTermsLoadingState = computed(() => Boolean(ctx.productSubscriptionTermsLoading))
const productSubscriptionTermsErrorText = computed(() => String(ctx.productSubscriptionTermsError || '').trim())
const selectableAccountOptions = computed(() => {
  // Используем подготовленный сервером список доступных аккаунтов под тип товара.
  const list = Array.isArray(productAccountOptions.value) ? [...productAccountOptions.value] : []
  list.sort((a, b) => String(a?.login_name || '').localeCompare(String(b?.login_name || '')))
  return list
})
// Формирует подпись аккаунта с доменом для единообразного списка выбора.
const formatAccountTitle = (account) => {
  const login = String(account?.login_name || '').trim()
  const domain = String(account?.domain_code || '').trim()
  if (!login && !domain) return '—'
  if (!domain) return login
  if (!login) return `@${domain}`
  return `${login}@${domain}`
}
const filteredNewProductAccounts = computed(() => {
  // Фильтрует аккаунты в создании товара по строке поиска.
  const query = String(newProductAccountSearch.value || '').trim().toLowerCase()
  if (!query) return selectableAccountOptions.value
  return selectableAccountOptions.value.filter((item) => formatAccountTitle(item).toLowerCase().includes(query))
})
const filteredEditProductAccounts = computed(() => {
  // Фильтрует аккаунты в редактировании товара по строке поиска.
  const query = String(editProductAccountSearch.value || '').trim().toLowerCase()
  if (!query) return selectableAccountOptions.value
  return selectableAccountOptions.value.filter((item) => formatAccountTitle(item).toLowerCase().includes(query))
})
const filteredSubscriptionTermAccounts = computed(() => {
  // Фильтрует аккаунты в блоке добавления срока подписки.
  const query = String(subscriptionTermAccountSearch.value || '').trim().toLowerCase()
  if (!query) return selectableAccountOptions.value
  return selectableAccountOptions.value.filter((item) => formatAccountTitle(item).toLowerCase().includes(query))
})
const editProductAccountTitles = computed(() => {
  // В режиме просмотра показываем выбранные аккаунты как плашки.
  const selected = Array.isArray(editProduct.value?.account_ids) ? editProduct.value.account_ids : []
  const byId = new Map(selectableAccountOptions.value.map((item) => [Number(item?.account_id || 0), formatAccountTitle(item)]))
  return selected
    .map((idValue) => byId.get(Number(idValue || 0)))
    .filter(Boolean)
})

// Считаем количество страниц для списка слотов внутри модалки товара.
const productSlotsTotalPages = computed(() => {
  const pages = Math.ceil(productSlotsCount.value / productSlotsPageSize)
  return pages > 0 ? pages : 1
})

// Сортируем слоты локально в модалке, чтобы быстро переключать порядок колонок.
const sortedProductSlotAssignments = computed(() => {
  const list = [...(productSlotAssignments.value || [])]
  const { key, dir } = productSlotsSort.value
  const factor = dir === 'asc' ? 1 : -1
  list.sort((a, b) => {
    const av = getProductSlotSortValue(a, key)
    const bv = getProductSlotSortValue(b, key)
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * factor
    return String(av || '').localeCompare(String(bv || '')) * factor
  })
  return list
})

// Показываем только текущую страницу слотов, чтобы таблица не росла бесконечно.
const pagedProductSlotAssignments = computed(() => {
  const start = (productSlotsPage.value - 1) * productSlotsPageSize
  return sortedProductSlotAssignments.value.slice(start, start + productSlotsPageSize)
})

// Переключает страницу слотов назад с защитой от выхода за границы.
const prevProductSlotsPage = () => {
  if (productSlotsPage.value > 1) productSlotsPage.value -= 1
}

// Переключает страницу слотов вперед с защитой от выхода за границы.
const nextProductSlotsPage = () => {
  if (productSlotsPage.value < productSlotsTotalPages.value) productSlotsPage.value += 1
}

// Повторяет визуальное поведение иконки сортировки, как в основных таблицах.
const getSortButtonClass = (state) => ({
  'sort-icon--active': Boolean(state),
  'sort-icon--asc': state === 'asc',
  'sort-icon--desc': state === 'desc',
})

// Меняет колонку сортировки слотов и направление по повторному клику.
const toggleProductSlotsSort = (key) => {
  const current = productSlotsSort.value
  if (current.key === key) {
    productSlotsSort.value = { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
  } else {
    productSlotsSort.value = { key, dir: 'asc' }
  }
  productSlotsPage.value = 1
}

// Возвращает текстовый индикатор направления, чтобы пользователь видел активную сортировку.
const getProductSlotsSortClass = (key) => getSortButtonClass(productSlotsSort.value.key === key ? productSlotsSort.value.dir : '')
const getProductAccountsSortClass = (key) => getSortButtonClass(productAccountsSort.value?.key === key ? productAccountsSort.value?.dir : '')
const getSubscriptionTermsSortClass = (key) => getSortButtonClass(subscriptionTermsSort.value.key === key ? subscriptionTermsSort.value.dir : '')

// Переключает сортировку списка сроков подписки в стиле остальных таблиц.
const toggleSubscriptionTermsSort = (key) => {
  const current = subscriptionTermsSort.value
  if (current.key === key) {
    subscriptionTermsSort.value = { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
  } else {
    subscriptionTermsSort.value = { key, dir: 'asc' }
  }
  productSubscriptionTermsPage.value = 1
}
const prevProductSubscriptionTermsPage = () => {
  if (productSubscriptionTermsPage.value > 1) productSubscriptionTermsPage.value -= 1
}
const nextProductSubscriptionTermsPage = () => {
  if (productSubscriptionTermsPage.value < productSubscriptionTermsTotalPages.value) productSubscriptionTermsPage.value += 1
}

// Открывает аккаунт из ячейки только при обычном клике, без выделенного текста.
const openAccountFromCell = (login) => {
  const selectedText = String(window.getSelection?.()?.toString?.() || '').trim()
  if (selectedText) return
  if (!login) return
  openAccountFromProduct.value(login)
}

// Показывает дату срока в привычном формате ДД.ММ.ГГГГ.
const formatTermDateLabel = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return '—'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  const day = String(parsed.getDate()).padStart(2, '0')
  const month = String(parsed.getMonth() + 1).padStart(2, '0')
  const year = String(parsed.getFullYear()).slice(-2)
  return `${day}/${month}/${year}`
}

// Достает значение для сравнения по выбранной колонке слотов.
const getProductSlotSortValue = (item, key) => {
  if (key === 'account') return item?.account_login || item?.account_id || ''
  if (key === 'slot') return getSlotTypeLabel.value(item?.slot_type_code)
  if (key === 'customer') return item?.customer_nickname || ''
  if (key === 'status') return getSlotAssignmentStatus.value(item)
  if (key === 'assigned') return Date.parse(item?.assigned_at || '') || 0
  if (key === 'released') return Date.parse(item?.released_at || '') || 0
  return ''
}

// Достает значение для сортировки сроков подписки.
const getSubscriptionTermSortValue = (item, key) => {
  if (key === 'valid_until') return Date.parse(String(item?.valid_until || '')) || 0
  if (key === 'status') return item?.occupied ? 1 : 0
  if (key === 'account') return String(item?.login_full || item?.account_login || '').trim().toLowerCase()
  return ''
}

// Создает новый срок подписки в карточке товара и сразу обновляет таблицу сроков.
const addSubscriptionTerm = async () => {
  subscriptionTermError.value = ''
  const createFn = ctx.createQuickProductSubscriptionTerm
  if (typeof createFn !== 'function') {
    subscriptionTermError.value = 'Функция создания срока недоступна'
    return
  }
  try {
    subscriptionTermLoading.value = true
    await createFn({
      account_id: Number(subscriptionTermForm.account_id || 0),
      valid_until: String(subscriptionTermForm.valid_until || '').trim(),
    })
    subscriptionTermForm.account_id = ''
    subscriptionTermForm.valid_until = getDefaultSubscriptionTermDate()
    subscriptionTermAccountSearch.value = ''
  } catch (error) {
    subscriptionTermError.value = String(error?.message || 'Не удалось добавить срок подписки')
  } finally {
    subscriptionTermLoading.value = false
  }
}

// При новом открытии карточки товара раскрываем секции и сбрасываем пагинацию слотов.
watch(
  () => editProduct.value?.product_id,
  () => {
    productAccountsOpen.value = false
    productSlotsOpen.value = false
    productSlotsPage.value = 1
    productSubscriptionTermsPage.value = 1
    subscriptionTermsSort.value = { key: 'valid_until', dir: 'asc' }
    subscriptionTermOpen.value = false
    subscriptionTermForm.account_id = ''
    subscriptionTermForm.valid_until = getDefaultSubscriptionTermDate()
    subscriptionTermAccountSearch.value = ''
    subscriptionTermError.value = ''
  },
)

// Синхронизирует состояние блока комментария при открытии/закрытии модалки.
const syncCommentPanels = () => {
  const showCreate = Boolean(showProductForm.value)
  const showEdit = Boolean(editProduct.value?.open)
  if (!showCreate && !showEdit) {
    newProductCommentOpen.value = false
    editProductCommentOpen.value = false
    newQuickAccountOpen.value = false
    editQuickAccountOpen.value = false
    newProductAccountSearch.value = ''
    editProductAccountSearch.value = ''
    return
  }
  // Если комментарий пустой, блок стартует свернутым; если текст есть — раскрываем.
  if (showCreate) newProductCommentOpen.value = Boolean(String(newProduct.value?.subscription_notes || '').trim())
  if (showEdit) editProductCommentOpen.value = Boolean(String(editProduct.value?.subscription_notes || '').trim())
}

watch(
  () => [showProductForm.value, editProduct.value?.open, editProduct.value?.product_id],
  () => syncCommentPanels(),
  { immediate: true },
)

watch(
  () => newProduct.value?.type_code,
  (typeCode) => {
    // При смене типа сбрасываем только строку поиска и состояние quick-create.
    if (typeCode !== PRODUCT_TYPE_PRIMARY) {
      newProductAccountSearch.value = ''
      newQuickAccountOpen.value = false
    }
  },
)

watch(
  () => editProduct.value?.type_code,
  (typeCode) => {
    // При смене типа сбрасываем только строку поиска и состояние quick-create.
    if (typeCode !== PRODUCT_TYPE_PRIMARY) {
      editProductAccountSearch.value = ''
      editQuickAccountOpen.value = false
    }
  },
)

// Если данных стало меньше, держим текущую страницу слотов в допустимом диапазоне.
watch(productSlotsTotalPages, (total) => {
  if (productSlotsPage.value > total) productSlotsPage.value = total
})
watch(productSubscriptionTermsTotalPages, (total) => {
  if (productSubscriptionTermsPage.value > total) productSubscriptionTermsPage.value = total
})

// Подбираем высоту textarea, чтобы комментарий не занимал лишнее место.
const getCompactNotesRows = (value) => {
  const text = String(value || '')
  if (!text) return 2
  return Math.max(2, Math.min(6, Math.ceil(text.length / 110)))
}
</script>
