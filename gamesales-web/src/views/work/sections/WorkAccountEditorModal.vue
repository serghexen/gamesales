<template>

            <teleport to="body">
              <div v-if="editAccount.open" class="work-page work-modal-root modal-backdrop" @click.self="cancelEditAccount">
                <div :ref="modalRef" class="modal modal--auto modal--account-editor" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <div class="account-modal-head">
                      <div class="account-modal-title-wrap">
                        <h3 class="account-modal-title">{{ accountModalTitle }}</h3>
                        <button
                          v-if="accountModalMode === 'edit' && canReflectEmail"
                          class="btn btn--icon-plain btn--icon-clear"
                          type="button"
                          :aria-label="getAccountFieldCopyLabel('email')"
                          :title="getAccountFieldCopyLabel('email')"
                          :disabled="!getAccountFieldCopyValue('email')"
                          @click="copyAccountField('email')"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                            <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                          </svg>
                        </button>
                      </div>
                      <label
                        v-if="showDeactivationToggle"
                        class="check-item account-modal-head__toggle"
                      >
                        <input
                          type="checkbox"
                          v-model="editAccount.is_deactivated"
                          :disabled="deactivationToggleDisabled"
                        />
                        <span>Деактивирован</span>
                      </label>
                      <p v-if="showDeactivatedHeaderStatus" class="account-modal-status">
                        <span class="account-modal-status__danger">Деактивирован.</span>
                        <span>{{ deactivationViewLabel }}</span>
                      </p>
                      <p v-if="showDeactivatedEditStatus" class="account-modal-status account-modal-status--edit">
                        <span>{{ deactivationViewLabel }}</span>
                      </p>
                    </div>
                    <div class="toolbar-actions">
                      <button
                        v-if="accountModalMode === 'edit' && accountEditMode === 'edit' && canEditAccountModal"
                        class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
                        @click="updateAccount"
                        :disabled="accountBusy"
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
                        v-if="accountModalMode === 'create' && canCreateAccountModal"
                        class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
                        @click="createAccount"
                        :disabled="accountBusy"
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
                        v-if="accountModalMode === 'edit' && canEditAccountModal"
                        class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
                        type="button"
                        aria-label="Редактировать"
                        title="Редактировать"
                        @click="toggleAccountEditMode"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                          <path d="M13 6l4 4" />
                        </svg>
                      </button>
                      <button
                        v-if="accountModalMode === 'edit' && canDeleteAccountModal"
                        class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
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
                        v-if="accountModalMode === 'edit'"
                        class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--refresh"
                        type="button"
                        aria-label="Обновить из базы"
                        title="Обновить из базы"
                        :disabled="accountBusy || accountEditMode === 'edit'"
                        @click="refreshOpenAccountFromDb"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                          <path d="M20 4v6h-6" />
                        </svg>
                      </button>
                      <button
                        class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
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
                  <div class="modal__body" :class="{ 'modal__body--locked': accountBusy }">
                    <div v-if="accountBusy" class="modal__body-overlay">
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
                        <p class="muted">Загрузка…</p>
                      </div>
                    </div>
                    <div v-if="accountModalMode === 'edit' && accountProductsLoading && !accountBusy" class="loader-wrap">
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
                      <div v-if="canReflectEmail" class="deal-form__double field--full">
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
                      </div>
                      <div v-if="canReflectRegion || canReflectPurchaseCost || canReflectDate" class="deal-form__triple field--full">
                        <label v-if="canReflectRegion" class="field">
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
                        <label v-if="canReflectPurchaseCost" class="field">
                          <span class="label">Закупочная цена</span>
                          <input
                            v-model.number="editAccount.purchase_cost"
                            class="input"
                            type="number"
                            min="0"
                            step="0.01"
                            :readonly="accountEditMode === 'view'"
                            @input="editAccount.purchase_cost = normalizeAccountPurchaseCost(editAccount.purchase_cost)"
                          />
                        </label>
                        <label v-if="canReflectDate" class="field">
                          <span class="label">Дата</span>
                          <input v-model="editAccount.account_date" class="input" type="date" :max="maxDate" :readonly="accountEditMode === 'view'" />
                        </label>
                      </div>
                      <div v-if="canReflectAccountPassword || canReflectEmailPassword" class="deal-form__double field--full">
                        <label v-if="canReflectAccountPassword" class="field">
                          <span class="label">Пароль аккаунт</span>
                          <div class="input--select-wrap">
                            <input v-model.trim="editAccount.account_password" class="input input--with-copy" autocomplete="new-password" :readonly="accountEditMode === 'view'" />
                            <button
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              :aria-label="getAccountFieldCopyLabel('account_password')"
                              :title="getAccountFieldCopyLabel('account_password')"
                              :disabled="!getAccountFieldCopyValue('account_password')"
                              @click="copyAccountField('account_password')"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                              </svg>
                            </button>
                          </div>
                        </label>
                        <label v-if="canReflectEmailPassword" class="field">
                          <span class="label">Пароль почта</span>
                          <div class="input--select-wrap">
                            <input v-model.trim="editAccount.email_password" class="input input--with-copy" autocomplete="new-password" :readonly="accountEditMode === 'view'" />
                            <button
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              :aria-label="getAccountFieldCopyLabel('email_password')"
                              :title="getAccountFieldCopyLabel('email_password')"
                              :disabled="!getAccountFieldCopyValue('email_password')"
                              @click="copyAccountField('email_password')"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                              </svg>
                            </button>
                          </div>
                        </label>
                      </div>
                      <label v-if="canReflectAuthCode" class="field field--full">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="editAccount.auth_code" class="input" placeholder="код" :readonly="accountEditMode === 'view'" />
                      </label>
                      <div v-if="canReflectReserves" class="field field--comment-collapsible field--full">
                        <button class="comment-toggle" type="button" @click="editAccountReserveOpen = !editAccountReserveOpen" :disabled="accountEditMode === 'view'">
                          {{ editAccountReserveOpen || editAccount.reserve_text ? 'Резерв' : '+ Резерв' }}
                        </button>
                        <textarea
                          v-if="accountEditMode !== 'view' && (editAccountReserveOpen || editAccount.reserve_text)"
                          v-model.trim="editAccount.reserve_text"
                          class="input input--textarea input--textarea--compact"
                          :rows="getCompactNotesRows(editAccount.reserve_text)"
                          placeholder="mkn4N5 6uGjMm ..."
                        />
                        <div v-else-if="editAccountReserveOpen || editAccount.reserve_text" class="field field--full account-reserve-list">
                          <div
                            v-for="(reserveItem, idx) in editReserveRows"
                            :key="`edit-reserve-${reserveItem.key || idx}`"
                            class="account-reserve-row"
                          >
                            <div class="account-reserve-row__meta">
                              <span class="label account-reserve-row__label">{{ reserveItem.label }}</span>
                              <span
                                v-if="isReserveUsedByKey(reserveItem.key)"
                                class="account-reserve-row__badge"
                              >
                                использован
                              </span>
                            </div>
                            <div class="input--select-wrap">
                              <input
                                class="input input--compact input--with-copy"
                                :value="getReserveDisplayValue(reserveItem)"
                                placeholder="код резерва"
                                readonly
                              />
                              <button
                                v-if="!isReserveUsedByKey(reserveItem.key)"
                                class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                type="button"
                                :aria-label="getReserveCopyLabel(reserveItem)"
                                :title="getReserveCopyLabel(reserveItem)"
                                :disabled="!getReserveCopyValue(reserveItem)"
                                @click="copyAccountField('reserve', reserveItem)"
                              >
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                  <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                  <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div v-if="canShowReflectSlots" class="field field--full">
                        <span class="label account-products-title">Товары</span>
                        <div v-if="accountEditMode === 'view'" class="pill-list">
                          <span v-for="t in accountProductTitles" :key="t" class="pill">{{ t }}</span>
                          <span v-if="!accountProductTitles.length" class="muted">Пока нет товаров.</span>
                        </div>
                        <div v-else>
                          <div class="account-product-filters field--full">
                            <label class="field">
                              <span class="label">Поиск</span>
                              <input v-model.trim="editAccountProductSearchModel" class="input" placeholder="поиск" />
                            </label>
                          <label class="field">
                            <span class="label">Тип товара</span>
                            <select v-model="editAccountProductTypeModel" class="input input--select">
                              <option value="game">Игра</option>
                              <option value="subscription">Подписка</option>
                            </select>
                          </label>
                          </div>
                          <div class="check-list check-list--account-products">
                            <label v-for="g in filteredEditAccountProducts" :key="g.product_id" class="check-item">
                              <input type="checkbox" :value="g.product_id" v-model="editAccount.product_ids" />
                              <span>{{ g.title }}</span>
                            </label>
                          </div>
                          <div
                            v-if="showEditAccountProductNoMatches"
                            :class="[
                              'quick-create quick-create--account-product',
                              { 'quick-create--collapsed': !editQuickProductOpen }
                            ]"
                          >
                            <div class="quick-create__header">
                              <button class="comment-toggle" type="button" @click="editQuickProductOpen = !editQuickProductOpen">
                                {{ editQuickProductOpen ? 'Быстрое создание товара' : '+ Быстрое создание товара' }}
                              </button>
                              <button
                                v-if="editQuickProductOpen"
                                class="ghost ghost--small"
                                type="button"
                                :disabled="quickEditAccountProductLoading"
                                @click="createQuickAccountProduct(editAccountProductTypeModel, 'edit')"
                              >
                                <span v-if="quickEditAccountProductLoading" class="spinner spinner--small"></span>
                                Создать
                              </button>
                            </div>
                            <template v-if="editQuickProductOpen">
                              <input v-model.trim="quickEditAccountProduct.title" class="input input--compact" placeholder="Название товара" />
                              <div class="check-list check-list--compact check-list--platform-row">
                                <label v-for="p in platforms" :key="`qae-p-${p.code}`" class="check-item">
                                  <input type="checkbox" :value="p.code" v-model="quickEditAccountProduct.platform_codes" />
                                  <span>{{ p.name }} ({{ p.code }})</span>
                                </label>
                              </div>
                              <span v-if="quickEditAccountProductError" class="bad">{{ quickEditAccountProductError }}</span>
                            </template>
                          </div>
                        </div>
                      </div>
                      <div v-if="canShowReflectSlots" class="field field--full">
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
                              <th>Товар</th>
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
                              <td>{{ s.product_title || '—' }}</td>
                              <td>{{ s.customer_nickname || '—' }}</td>
                              <td>{{ getSlotAssignmentStatus(s) }}</td>
                              <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                              <td>{{ s.released_at ? formatDateTimeMinutes(s.released_at) : '—' }}</td>
                              <td>{{ s.released_by || '—' }}</td>
                              <td class="cell--tight">
                                <button
                                  v-if="canManageSlotAssignments && !s.released_at"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="accountSlotReleaseLoading"
                                  @click="releaseSlotAssignment(s.assignment_id)"
                                >
                                  Снять
                                </button>
                                <button
                                  v-else-if="canManageSlotAssignments"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="accountSlotReleaseLoading"
                                  @click="restoreSlotAssignment(s.assignment_id)"
                                >
                                  Вернуть
                                </button>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                        <p v-else class="muted">Слотов по аккаунту пока нет.</p>
                      </div>
                      <div v-if="canShowReflectDeals" class="field field--full">
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
                              <th>Товар</th>
                              <th>Тип</th>
                              <th>Статус</th>
                              <th>Дата покупки</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr
                              v-for="d in accountDeals"
                              :key="`${d.deal_id}-${d.product_id}`"
                              class="table-row--deal-open"
                              role="button"
                              tabindex="0"
                              @click="openDealFromAccount(d)"
                              @keydown.enter.prevent="openDealFromAccount(d)"
                              @keydown.space.prevent="openDealFromAccount(d)"
                            >
                              <td>{{ d.customer_nickname || '—' }}</td>
                              <td>
                                <span :title="getDealProductTitleTooltip(d)">{{ getDealProductTitleDisplay(d) }}</span>
                              </td>
                              <td>{{ d.deal_type || '—' }}</td>
                              <td>{{ d.flow_status || '—' }}</td>
                              <td>{{ formatDate(d.purchase_at || d.created_at) }}</td>
                            </tr>
                          </tbody>
                        </table>
                        <p v-else class="muted">Сделок по аккаунту пока нет.</p>
                      </div>
                      <div class="field field--comment-collapsible field--full">
                        <button class="comment-toggle" type="button" @click="editAccountCommentOpen = !editAccountCommentOpen" :disabled="accountEditMode === 'view'">
                          {{ editAccountCommentOpen || editAccount.notes ? 'Комментарий' : '+ Комментарий' }}
                        </button>
                        <textarea
                          v-if="editAccountCommentOpen || editAccount.notes"
                          v-model.trim="editAccount.notes"
                          class="input input--textarea input--textarea--compact"
                          :rows="getCompactNotesRows(editAccount.notes)"
                          :readonly="accountEditMode === 'view'"
                        />
                      </div>
                      <p v-if="accountsError" class="bad">{{ accountsError }}</p>
                      <p v-if="accountsOk" class="ok">{{ accountsOk }}</p>
                      <div v-if="accountEditMode === 'edit'" class="toolbar-actions">
                      </div>
                    </div>
                    <div v-else class="form form--stack form--compact">
                      <div class="deal-form__double field--full">
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
                      </div>
                      <div class="deal-form__triple field--full">
                        <label class="field">
                          <span class="label">Регион</span>
                          <select v-model="newAccount.region_code" class="input input--select">
                            <option value="">— не выбрано —</option>
                            <option v-for="r in regions" :key="r.code" :value="r.code">
                              {{ r.name }} ({{ r.code }})
                            </option>
                          </select>
                        </label>
                        <label v-if="canReflectPurchaseCost" class="field">
                          <span class="label">Закупочная цена</span>
                          <input
                            v-model.number="newAccount.purchase_cost"
                            class="input"
                            type="number"
                            min="0"
                            step="0.01"
                            @input="newAccount.purchase_cost = normalizeAccountPurchaseCost(newAccount.purchase_cost)"
                          />
                        </label>
                        <label class="field">
                          <span class="label">Дата</span>
                          <input v-model="newAccount.account_date" class="input" type="date" :max="maxDate" />
                        </label>
                      </div>
                      <div v-if="canReflectAccountPassword || canReflectEmailPassword" class="deal-form__double field--full">
                        <label v-if="canReflectAccountPassword" class="field">
                          <span class="label">Пароль аккаунт</span>
                          <div class="input--select-wrap">
                            <input v-model.trim="newAccount.account_password" class="input input--with-copy" autocomplete="new-password" />
                            <button
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              :aria-label="getAccountFieldCopyLabel('account_password_new')"
                              :title="getAccountFieldCopyLabel('account_password_new')"
                              :disabled="!getAccountFieldCopyValue('account_password_new')"
                              @click="copyAccountField('account_password_new')"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                              </svg>
                            </button>
                          </div>
                        </label>
                        <label v-if="canReflectEmailPassword" class="field">
                          <span class="label">Пароль почта</span>
                          <div class="input--select-wrap">
                            <input v-model.trim="newAccount.email_password" class="input input--with-copy" autocomplete="new-password" />
                            <button
                              class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                              type="button"
                              :aria-label="getAccountFieldCopyLabel('email_password_new')"
                              :title="getAccountFieldCopyLabel('email_password_new')"
                              :disabled="!getAccountFieldCopyValue('email_password_new')"
                              @click="copyAccountField('email_password_new')"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                              </svg>
                            </button>
                          </div>
                        </label>
                      </div>
                      <label v-if="canReflectAuthCode" class="field field--full">
                        <span class="label">Код аутентификатора</span>
                        <input v-model.trim="newAccount.auth_code" class="input" placeholder="код" />
                      </label>
                      <div v-if="canReflectReserves" class="field field--comment-collapsible field--full">
                        <button class="comment-toggle" type="button" @click="newAccountReserveOpen = !newAccountReserveOpen">
                          {{ newAccountReserveOpen || newAccount.reserve_text ? 'Резерв' : '+ Резерв' }}
                        </button>
                        <textarea
                          v-if="newAccountReserveOpen || newAccount.reserve_text"
                          v-model.trim="newAccount.reserve_text"
                          class="input input--textarea input--textarea--compact"
                          :rows="getCompactNotesRows(newAccount.reserve_text)"
                          placeholder="mkn4N5 6uGjMm ..."
                        />
                      </div>
                      <div v-if="canShowReflectSlots" class="field field--full">
                        <span class="label account-products-title">Товары</span>
                        <div class="account-product-filters field--full">
                          <label class="field">
                            <span class="label">Поиск</span>
                            <input v-model.trim="accountProductSearchModel" class="input" placeholder="поиск" />
                          </label>
                          <label class="field">
                            <span class="label">Тип товара</span>
                            <select v-model="accountProductTypeModel" class="input input--select">
                              <option value="game">Игра</option>
                              <option value="subscription">Подписка</option>
                            </select>
                          </label>
                        </div>
                        <div class="check-list check-list--account-products">
                          <label v-for="g in filteredAccountProducts" :key="g.product_id" class="check-item">
                            <input type="checkbox" :value="g.product_id" v-model="newAccount.product_ids" />
                            <span>{{ g.title }}</span>
                          </label>
                        </div>
                        <div
                          v-if="showNewAccountQuickCreate"
                          :class="[
                            'quick-create quick-create--account-product',
                            { 'quick-create--collapsed': !newQuickProductOpen }
                          ]"
                        >
                          <div class="quick-create__header">
                            <button class="comment-toggle" type="button" @click="newQuickProductOpen = !newQuickProductOpen">
                              {{ newQuickProductOpen ? 'Быстрое создание товара' : '+ Быстрое создание товара' }}
                            </button>
                            <button
                              v-if="newQuickProductOpen"
                              class="ghost ghost--small"
                              type="button"
                              :disabled="quickNewAccountProductLoading"
                              @click="createQuickAccountProduct(accountProductTypeModel)"
                            >
                              <span v-if="quickNewAccountProductLoading" class="spinner spinner--small"></span>
                              Создать
                            </button>
                          </div>
                          <template v-if="newQuickProductOpen">
                            <input v-model.trim="quickNewAccountProduct.title" class="input input--compact" placeholder="Название товара" />
                            <div class="check-list check-list--compact check-list--platform-row">
                              <label v-for="p in platforms" :key="`qa-p-${p.code}`" class="check-item">
                                <input type="checkbox" :value="p.code" v-model="quickNewAccountProduct.platform_codes" />
                                <span>{{ p.name }} ({{ p.code }})</span>
                              </label>
                            </div>
                            <span v-if="quickNewAccountProductError" class="bad">{{ quickNewAccountProductError }}</span>
                          </template>
                        </div>
                        <div
                          v-if="isCreateSubscriptionMode && hasCreateSubscriptionProduct"
                          class="field field--full quick-create quick-create--subscription-term"
                        >
                          <div class="quick-create__header">
                            <button class="comment-toggle" type="button" @click="newSubscriptionTermOpen = !newSubscriptionTermOpen">
                              {{ newSubscriptionTermOpen ? 'Добавить срок подписки' : '+ Добавить срок подписки' }}
                            </button>
                          </div>
                          <template v-if="newSubscriptionTermOpen">
                            <input
                              v-model="newAccount.subscription_valid_until"
                              class="input input--compact"
                              type="date"
                            />
                          </template>
                        </div>
                      </div>
                      <div class="field field--comment-collapsible field--full">
                        <button class="comment-toggle" type="button" @click="newAccountCommentOpen = !newAccountCommentOpen">
                          {{ newAccountCommentOpen || newAccount.notes ? 'Комментарий' : '+ Комментарий' }}
                        </button>
                        <textarea
                          v-if="newAccountCommentOpen || newAccount.notes"
                          v-model.trim="newAccount.notes"
                          class="input input--textarea input--textarea--compact"
                          :rows="getCompactNotesRows(newAccount.notes)"
                        />
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
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps([
  'editAccount',
  'canToggleDeactivation',
  'canCreateAccount',
  'canEditAccount',
  'canDeleteAccount',
  'canViewGames',
  'canReflectEmail',
  'canReflectDate',
  'canReflectRegion',
  'canReflectPurchaseCost',
  'canReflectAccountPassword',
  'canReflectEmailPassword',
  'canReflectAuthCode',
  'canReflectReserves',
  'canReflectSlots',
  'canReflectDeals',
  'cancelEditAccount',
  'modalRef',
  'modalStyle',
  'startModalDrag',
  'accountModalMode',
  'accountEditMode',
  'setAccountEditMode',
  'toggleAccountEditMode',
  'refreshOpenAccountFromDb',
  'updateAccount',
  'accountsLoading',
  'accountSaving',
  'createAccount',
  'deleteAccount',
  'accountProductsLoading',
  'getDomainLabel',
  'domains',
  'getRegionLabel',
  'regions',
  'getAccountStatusLabel',
  'maxDate',
  'accountProductTitles',
  'editAccountProductSearch',
  'editAccountProductType',
  'filteredEditAccountProducts',
  'accountSlotAssignmentsError',
  'accountSlotAssignmentsLoading',
  'accountSlotAssignments',
  'sortedAccountSlotAssignments',
  'getSlotTypeLabel',
  'getSlotAssignmentStatus',
  'formatDateTimeMinutes',
  'accountSlotReleaseLoading',
  'canManageAccountSlotAssignments',
  'releaseSlotAssignment',
  'restoreSlotAssignment',
  'accountDealsError',
  'accountDealsLoading',
  'accountDeals',
  'loadAccountUsedReserveKeys',
  'claimAccountReserve',
  'releaseAccountReserveClaim',
  'startEditDeal',
  'getDealProductTitleTooltip',
  'getDealProductTitleDisplay',
  'formatDate',
  'accountsError',
  'accountsOk',
  'newAccount',
  'accountProductSearch',
  'accountProductType',
  'filteredAccountProducts',
  'createQuickAccountProduct',
  'quickNewAccountProduct',
  'quickNewAccountProductLoading',
  'quickNewAccountProductError',
  'quickEditAccountProduct',
  'quickEditAccountProductLoading',
  'quickEditAccountProductError',
  'platforms',
  'setEditAccountProductSearch',
  'setAccountProductSearch',
  'setEditAccountProductType',
  'setAccountProductType',
])

const canShowReflectSlots = computed(() => props.canReflectSlots === true)
const canShowReflectDeals = computed(() => props.canReflectDeals === true)
const canCreateAccountModal = computed(() => props.canCreateAccount === true)
const canEditAccountModal = computed(() => props.canEditAccount === true)
const canDeleteAccountModal = computed(() => props.canDeleteAccount === true)
const canReflectEmail = computed(() => props.canReflectEmail === true)
const canReflectDate = computed(() => props.canReflectDate === true)
const canReflectRegion = computed(() => props.canReflectRegion === true)
const canReflectPurchaseCost = computed(() => props.canReflectPurchaseCost === true)
const canReflectAccountPassword = computed(() => props.canReflectAccountPassword === true)
const canReflectEmailPassword = computed(() => props.canReflectEmailPassword === true)
const canReflectAuthCode = computed(() => props.canReflectAuthCode === true)
const canReflectReserves = computed(() => props.canReflectReserves === true)

// Галочку деактивации показываем только тем ролям, которым разрешено менять этот флаг.
const showDeactivationToggle = computed(() => {
  return props.accountModalMode === 'edit'
    && props.accountEditMode === 'edit'
    && props.canToggleDeactivation === true
})

const editAccountProductSearchModel = computed({
  get: () => props.editAccountProductSearch,
  set: (value) => props.setEditAccountProductSearch(value),
})

// Блокируем форму при загрузке или сохранении, чтобы пользователь видел единый индикатор.
const accountBusy = computed(() => Boolean(props.accountsLoading || props.accountSaving))

// Ручное снятие и возврат слотов доступны только административным ролям.
const canManageSlotAssignments = computed(() => props.canManageAccountSlotAssignments === true)

// Обновляет текущую карточку аккаунта с сервера, чтобы подтянуть изменения из других вкладок.
const refreshOpenAccountFromDb = () => {
  if (typeof props.refreshOpenAccountFromDb !== 'function') return
  props.refreshOpenAccountFromDb()
}

const editAccountProductTypeModel = computed({
  get: () => props.editAccountProductType,
  set: (value) => props.setEditAccountProductType(value),
})

const accountProductSearchModel = computed({
  get: () => props.accountProductSearch,
  set: (value) => props.setAccountProductSearch(value),
})

// Держим закупочную цену в допустимом формате, чтобы в API не уходили отрицательные значения.
const normalizeAccountPurchaseCost = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num) || num < 0) return 0
  return Math.round(num * 100) / 100
}

const accountProductTypeModel = computed({
  get: () => props.accountProductType,
  set: (value) => props.setAccountProductType(value),
})

// Показывает быстрый create товара, когда в текущем фильтре нет доступных позиций.
const showNewAccountProductNoMatches = computed(() => {
  if (props.accountModalMode !== 'create') return false
  return !Array.isArray(props.filteredAccountProducts) || props.filteredAccountProducts.length === 0
})

// В создании подписки всегда показываем только быстрый create нового товара.
const isCreateSubscriptionMode = computed(() => {
  return props.accountModalMode === 'create'
    && String(accountProductTypeModel.value || '').trim().toLowerCase() === 'subscription'
})

// Блок быстрого create в создании: всегда для подписки, для игр только когда список пуст.
const showNewAccountQuickCreate = computed(() => {
  return !isCreateSubscriptionMode.value && showNewAccountProductNoMatches.value
})

const hasCreateSubscriptionProduct = computed(() => {
  const ids = Array.isArray(props.newAccount?.product_ids) ? props.newAccount.product_ids : []
  return ids.length > 0
})

// Показывает быстрый create товара в редактировании, если текущий фильтр вернул пустой список.
const showEditAccountProductNoMatches = computed(() => {
  if (props.accountModalMode !== 'edit' || props.accountEditMode === 'view') return false
  return !Array.isArray(props.filteredEditAccountProducts) || props.filteredEditAccountProducts.length === 0
})

// Считает, сколько полных суток осталось до повторной активации аккаунта.
const deactivationDaysLeft = computed(() => {
  if (!props.editAccount?.is_deactivated) return null
  const raw = String(props.editAccount?.next_activation_at || '').trim()
  if (!raw) return null
  const nextActivationAt = new Date(raw)
  if (Number.isNaN(nextActivationAt.getTime())) return null
  const diffMs = nextActivationAt.getTime() - Date.now()
  if (diffMs <= 0) return 0
  return Math.ceil(diffMs / (24 * 60 * 60 * 1000))
})

// Блокирует чекбокс деактивации до окончания таймера повторной активации.
const deactivationToggleDisabled = computed(() => {
  // Разрешаем ручное снятие деактивации в любой момент; блокируем только на время сохранения/загрузки.
  return accountBusy.value
})

// В режиме просмотра показываем статус рядом с именем только для деактивированного аккаунта.
const showDeactivatedHeaderStatus = computed(() => {
  return props.accountModalMode === 'edit'
    && props.accountEditMode === 'view'
    && Boolean(props.editAccount?.is_deactivated)
})

// В режиме редактирования текст-подсказку показываем только когда аккаунт уже деактивирован.
const showDeactivatedEditStatus = computed(() => {
  return props.accountModalMode === 'edit'
    && props.accountEditMode === 'edit'
    && Boolean(props.editAccount?.is_deactivated)
})

// Текст статуса для формы просмотра рядом с именем аккаунта.
const deactivationViewLabel = computed(() => {
  const days = deactivationDaysLeft.value
  if (days === null) return 'Повторная деактивация: ожидание'
  if (days <= 0) return 'Повторная деактивация через 0 дней'
  return `Повторная деактивация через ${days} дней`
})

// Формирует заголовок модалки аккаунта в нужном формате.
const accountModalTitle = computed(() => {
  if (props.accountModalMode === 'create') return 'Новый аккаунт'
  // Если почта роли скрыта, не выводим login/domain даже в заголовке карточки.
  if (!canReflectEmail.value) return 'АККАУНТ'
  const login = String(props.editAccount?.login_name || '').trim()
  const domain = String(props.editAccount?.domain_code || '').trim()
  if (!login && !domain) return 'АККАУНТ'
  if (!domain) return `АККАУНТ - ${login}`
  if (!login) return `АККАУНТ - @${domain}`
  return `АККАУНТ - ${login}@${domain}`
})

const newAccountReserveOpen = ref(false)
const newAccountCommentOpen = ref(false)
const newQuickProductOpen = ref(false)
const newSubscriptionTermOpen = ref(false)
const editQuickProductOpen = ref(false)
const editAccountReserveOpen = ref(false)
const editAccountCommentOpen = ref(false)
const editReserveRows = ref([])
const copiedAccountFieldKey = ref('')
const persistedUsedReserveKeys = ref(new Set())
const persistedReserveUsageLoaded = ref(false)
let reserveUsageRequestSeq = 0
let copiedAccountFieldTimerId = 0

// Возвращает дату срока подписки по умолчанию: текущая дата плюс один год.
const getDefaultSubscriptionTermDate = () => {
  const nextYearDate = new Date()
  nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
  const year = nextYearDate.getFullYear()
  const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
  const day = String(nextYearDate.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// Подбирает компактную высоту textarea для комментариев и резерва.
const getCompactNotesRows = (value) => {
  const text = String(value || '')
  if (!text) return 2
  return Math.max(2, Math.min(6, Math.ceil(text.length / 110)))
}

// Возвращает true, если значение пустое или служебное и его не нужно копировать.
const isCopyPlaceholderValue = (value) => {
  const normalized = String(value || '').trim().toLowerCase()
  return !normalized || normalized === '—' || normalized === '-'
}

// Универсально копирует текст в буфер с fallback для окружений без Clipboard API.
const copyTextToClipboard = async (value) => {
  const text = String(value || '').trim()
  if (!text) return false
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return true
  }
  const tempInput = document.createElement('textarea')
  tempInput.value = text
  tempInput.setAttribute('readonly', '')
  tempInput.style.position = 'absolute'
  tempInput.style.left = '-9999px'
  document.body.appendChild(tempInput)
  tempInput.select()
  if (typeof document.execCommand === 'function') {
    document.execCommand('copy')
  }
  document.body.removeChild(tempInput)
  return true
}

// Формирует email аккаунта в формате login@domain для копирования из шапки модалки.
const getAccountEmailForCopy = () => {
  const source = props.accountModalMode === 'create' ? props.newAccount : props.editAccount
  const login = String(source?.login_name || '').trim()
  const domain = String(source?.domain_code || '').trim()
  if (!login || !domain) return ''
  return `${login}@${domain}`
}

// Возвращает значение поля аккаунта для копирования.
const getAccountFieldCopyValue = (field, reserveItem = null) => {
  // Копирование читает те же флаги, что и видимость полей, чтобы скрытое право не обходилось кнопкой.
  if (field === 'email' && !canReflectEmail.value) return ''
  if ((field === 'account_password' || field === 'account_password_new') && !canReflectAccountPassword.value) return ''
  if ((field === 'email_password' || field === 'email_password_new') && !canReflectEmailPassword.value) return ''
  if (field === 'reserve' && !canReflectReserves.value) return ''
  if (field === 'email') return getAccountEmailForCopy()
  if (field === 'account_password') return String(props.editAccount?.account_password || '').trim()
  if (field === 'email_password') return String(props.editAccount?.email_password || '').trim()
  if (field === 'account_password_new') return String(props.newAccount?.account_password || '').trim()
  if (field === 'email_password_new') return String(props.newAccount?.email_password || '').trim()
  if (field === 'reserve') return String(reserveItem?.value || '').trim()
  return ''
}

// Собирает ключ копирования, чтобы короткий статус "Скопировано" показывался только для нажатой кнопки.
const getAccountFieldCopyKey = (field, reserveItem = null) => {
  if (field !== 'reserve') return field
  return `reserve:${String(reserveItem?.key || reserveItem?.label || '')}`
}

// Возвращает подпись кнопки копирования поля аккаунта.
const getAccountFieldCopyLabel = (field, reserveItem = null) => {
  const copyKey = getAccountFieldCopyKey(field, reserveItem)
  if (copiedAccountFieldKey.value === copyKey) return 'Скопировано'
  if (field === 'email') return 'Копировать почту'
  if (field === 'account_password' || field === 'account_password_new') return 'Копировать пароль аккаунта'
  if (field === 'email_password' || field === 'email_password_new') return 'Копировать пароль почты'
  if (field === 'reserve') return `Копировать ${String(reserveItem?.label || 'резерв')}`
  return 'Копировать'
}

// Возвращает подпись копирования для строки резерва.
const getReserveCopyLabel = (reserveItem) => getAccountFieldCopyLabel('reserve', reserveItem)

// Возвращает значение резерва для копирования без служебных пустых меток.
const getReserveCopyValue = (reserveItem) => getAccountFieldCopyValue('reserve', reserveItem)

// Возвращает реальное значение резерва; блокировка копирования идет через кнопку и обработчик.
const getReserveDisplayValue = (reserveItem) => {
  return String(reserveItem?.value || '').trim()
}

// Копирует выбранное поле аккаунта и показывает короткий статус на кнопке.
const copyAccountField = async (field, reserveItem = null) => {
  const value = getAccountFieldCopyValue(field, reserveItem)
  if (isCopyPlaceholderValue(value)) return
  const accountId = Number(props.editAccount?.account_id || 0)
  const reserveKey = normalizeReserveKey(reserveItem?.key)
  if (field === 'reserve' && (!accountId || !reserveKey || isReserveUsedByKey(reserveKey))) return
  let claimToken = ''
  try {
    if (field === 'reserve') {
      const claim = await props.claimAccountReserve?.(accountId, reserveKey)
      claimToken = String(claim?.claim_token || '').trim()
      if (!claimToken) return
      persistedUsedReserveKeys.value = new Set([...persistedUsedReserveKeys.value, reserveKey])
    }
    await copyTextToClipboard(value)
    copiedAccountFieldKey.value = getAccountFieldCopyKey(field, reserveItem)
    if (copiedAccountFieldTimerId) window.clearTimeout(copiedAccountFieldTimerId)
    copiedAccountFieldTimerId = window.setTimeout(() => {
      copiedAccountFieldKey.value = ''
      copiedAccountFieldTimerId = 0
    }, 1400)
  } catch {
    if (field === 'reserve' && claimToken) {
      await Promise.resolve(props.releaseAccountReserveClaim?.(accountId, reserveKey, claimToken)).catch(() => {})
      const nextKeys = new Set(persistedUsedReserveKeys.value)
      nextKeys.delete(reserveKey)
      persistedUsedReserveKeys.value = nextKeys
    }
    // Ошибку копирования игнорируем: форма продолжает работать без блокировки.
  }
}

// Открывает выбранную сделку из карточки аккаунта в общем окне сделки.
const openDealFromAccount = (deal) => {
  if (typeof props.startEditDeal !== 'function') return
  const dealId = Number(deal?.deal_id || 0)
  if (!dealId) return
  const accountId = Number(deal?.account_id || props.editAccount?.account_id || 0)
  // Передаем вкладку-источник, чтобы после закрытия сделки вернуть пользователя в аккаунты.
  props.startEditDeal(deal, { returnTab: 'accounts', returnAccountId: accountId })
}

// Разбивает строку резервов по пробелам и убирает пустые элементы.
const parseReserveValues = (value) => {
  const rows = String(value || '')
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean)
  return rows
}

// Нормализует ключ резерва к формату reserveN, чтобы сравнение работало стабильно.
const normalizeReserveKey = (value) => {
  const raw = String(value || '').trim().toLowerCase()
  if (!/^reserve\d+$/.test(raw)) return ''
  return `reserve${Number(raw.replace('reserve', ''))}`
}

// Вычисляет номер из reserve-ключа, чтобы показывать пользователю реальный идентификатор.
const getReserveNumber = (key) => Number(String(key || '').replace('reserve', '')) || 0

// Собирает ряды резервов с реальными ключами и читабельными подписями.
const buildReserveRows = (reserveText, existingKeys) => {
  const values = parseReserveValues(reserveText)
  const keys = Array.from(
    new Set(
      (Array.isArray(existingKeys) ? existingKeys : [])
        .map((key) => normalizeReserveKey(key))
        .filter(Boolean)
    )
  ).sort((left, right) => getReserveNumber(left) - getReserveNumber(right))
  return values.map((value, idx) => {
    const key = keys[idx] || `reserve${idx + 1}`
    const reserveNumber = getReserveNumber(key) || idx + 1
    return {
      key,
      value,
      label: `Резерв ${reserveNumber}`,
    }
  })
}

// Собирает использованные резервы по сделкам аккаунта (шеринг).
const usedReserveKeys = computed(() => {
  const deals = Array.isArray(props.accountDeals) ? props.accountDeals : []
  const keys = new Set()
  deals.forEach((deal) => {
    if (String(deal?.deal_type_code || '').toLowerCase() !== 'rental') return
    const key = normalizeReserveKey(deal?.reserve_key)
    if (key) keys.add(key)
  })
  persistedUsedReserveKeys.value.forEach((key) => keys.add(key))
  return keys
})

// Пока usage не загрузился, не показываем резервные коды в карточке аккаунта.
const isReserveUsagePending = () => {
  return Boolean(props.editAccount?.open && props.accountModalMode === 'edit' && !persistedReserveUsageLoaded.value)
}

// Проверяет, занят ли конкретный reserve-ключ в активных шеринговых сделках аккаунта.
const isReserveUsedByKey = (key) => {
  const normalizedKey = normalizeReserveKey(key)
  if (!normalizedKey) return false
  if (isReserveUsagePending()) return true
  return usedReserveKeys.value.has(normalizedKey)
}

// Загружает постоянные отметки копирования при каждом открытии карточки аккаунта.
const loadPersistedReserveUsage = async () => {
  const requestId = ++reserveUsageRequestSeq
  const accountId = Number(props.editAccount?.account_id || 0)
  if (!props.editAccount?.open || props.accountModalMode !== 'edit' || !accountId) {
    persistedUsedReserveKeys.value = new Set()
    persistedReserveUsageLoaded.value = false
    return
  }
  persistedReserveUsageLoaded.value = false
  try {
    const keys = await props.loadAccountUsedReserveKeys?.(accountId)
    if (requestId !== reserveUsageRequestSeq || Number(props.editAccount?.account_id || 0) !== accountId) return
    persistedUsedReserveKeys.value = new Set(
      (Array.isArray(keys) ? keys : []).map(normalizeReserveKey).filter(Boolean)
    )
    persistedReserveUsageLoaded.value = true
  } catch {
    if (requestId === reserveUsageRequestSeq) {
      persistedUsedReserveKeys.value = new Set()
      persistedReserveUsageLoaded.value = false
    }
  }
}

// Синхронизирует локальные строки резервов с полем reserve_text из формы.
const syncReserveRows = () => {
  editReserveRows.value = buildReserveRows(
    props.editAccount?.reserve_text || '',
    props.editAccount?.existing_reserve_keys || []
  )
}

// Синхронизирует состояние сворачиваемых полей по содержимому при каждом открытии модалки.
const syncCollapsiblePanels = () => {
  const isOpen = Boolean(props.editAccount?.open)
  if (!isOpen) {
    newAccountReserveOpen.value = false
    newAccountCommentOpen.value = false
    newQuickProductOpen.value = false
    newSubscriptionTermOpen.value = false
    editQuickProductOpen.value = false
    editAccountReserveOpen.value = false
    editAccountCommentOpen.value = false
    editReserveRows.value = []
    return
  }
  const isCreate = props.accountModalMode === 'create'
  if (isCreate) {
    newAccountReserveOpen.value = Boolean(String(props.newAccount?.reserve_text || '').trim())
    newAccountCommentOpen.value = Boolean(String(props.newAccount?.notes || '').trim())
    newSubscriptionTermOpen.value = false
  } else {
    editAccountReserveOpen.value = Boolean(String(props.editAccount?.reserve_text || '').trim())
    editAccountCommentOpen.value = Boolean(String(props.editAccount?.notes || '').trim())
  }
  syncReserveRows()
}

watch(
  () => [props.editAccount?.open, props.accountModalMode, props.editAccount?.account_id, props.accountEditMode, props.editAccount?.reserve_text],
  () => syncCollapsiblePanels(),
  { immediate: true },
)

watch(
  () => [props.editAccount?.open, props.accountModalMode, props.editAccount?.account_id, props.accountEditMode],
  () => {
    void loadPersistedReserveUsage()
  },
  { immediate: true },
)

watch(
  () => showNewAccountProductNoMatches.value,
  (noMatches) => {
    // Автоматически сворачиваем быстрый create, когда снова появились товары в списке.
    if (!noMatches && !isCreateSubscriptionMode.value) newQuickProductOpen.value = false
  },
)

watch(
  () => accountProductTypeModel.value,
  (typeCode) => {
    // При выборе подписки в создании аккаунта очищаем текущий выбор, затем пользователь выбирает нужный товар из списка.
    if (props.accountModalMode !== 'create') return
    if (String(typeCode || '').trim().toLowerCase() !== 'subscription') return
    if (Array.isArray(props.newAccount?.product_ids)) {
      props.newAccount.product_ids = []
    }
    if (props.newAccount) {
      props.newAccount.subscription_valid_until = getDefaultSubscriptionTermDate()
    }
    newQuickProductOpen.value = false
  },
)

watch(
  () => [isCreateSubscriptionMode.value, hasCreateSubscriptionProduct.value],
  ([isSubscriptionMode, hasProduct]) => {
    // Блок срока показываем только когда создана подписка для нового аккаунта.
    if (!isSubscriptionMode || !hasProduct) {
      newSubscriptionTermOpen.value = false
      return
    }
    if (props.newAccount && !String(props.newAccount.subscription_valid_until || '').trim()) {
      props.newAccount.subscription_valid_until = getDefaultSubscriptionTermDate()
    }
  },
)

watch(
  () => showEditAccountProductNoMatches.value,
  (noMatches) => {
    // Для режима редактирования применяем ту же логику.
    if (!noMatches) editQuickProductOpen.value = false
  },
)

watch(
  () => accountProductSearchModel.value,
  (value) => {
    // В создании аккаунта подставляем поиск в быстрое создание, как в форме Шеринг+.
    const title = String(value || '').trim()
    if (!title) return
    if (props.quickNewAccountProduct) {
      props.quickNewAccountProduct.title = title
    }
  },
)

watch(
  () => editAccountProductSearchModel.value,
  (value) => {
    // В редактировании аккаунта используем тот же автоподбор названия для быстрого создания.
    const title = String(value || '').trim()
    if (!title) return
    if (props.quickEditAccountProduct) {
      props.quickEditAccountProduct.title = title
    }
  },
)

onBeforeUnmount(() => {
  if (copiedAccountFieldTimerId) {
    window.clearTimeout(copiedAccountFieldTimerId)
    copiedAccountFieldTimerId = 0
  }
})
</script>
