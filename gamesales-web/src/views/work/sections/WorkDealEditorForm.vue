<template>
                    <div v-if="editDeal.open" class="form deal-form" :class="{ 'deal-form--sale': editDeal.deal_type_code === 'sale' || editDeal.deal_type_code === 'rental' }">
                      <div class="deal-form__col deal-form__col--left">
                        <div v-if="editDeal.deal_type_code === 'rental'" class="deal-form__triple deal-form__triple--sale-status-row">
                          <label class="field">
                            <span class="label">Дата создания</span>
                            <input
                              v-if="dealEditMode !== 'view' && canEditSystemDates"
                              v-model="editDeal.created_at"
                              class="input"
                              type="datetime-local"
                            />
                            <input
                              v-else
                              class="input"
                              :value="formatDateTimeMinutes(editDeal.created_at)"
                              readonly
                            />
                          </label>
                          <label class="field">
                            <span class="label">Дата завершения</span>
                            <input
                              v-if="dealEditMode !== 'view' && canEditSystemDates"
                              v-model="editDeal.completed_at"
                              class="input"
                              type="datetime-local"
                            />
                            <input
                              v-else
                              class="input"
                              :value="editDeal.completed_at ? formatDateTimeMinutes(editDeal.completed_at) : '—'"
                              readonly
                            />
                          </label>
                          <label class="field">
                            <span class="label">Статус</span>
                            <input
                              v-if="dealEditMode === 'view'"
                              class="input"
                              :value="getFlowStatusLabel(editDeal.flow_status_code)"
                              readonly
                            />
                            <select v-else v-model="editDeal.flow_status_code" class="input input--select">
                              <option value="">— не выбрано —</option>
                              <option v-for="s in editFlowStatusOptions" :key="s.code" :value="s.code">
                                {{ s.name }}
                              </option>
                            </select>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'rental' && !isEditDealPendingFlow && (dealEditMode !== 'view' || editDeal.is_refund)" class="field">
                          <span class="label">Возврат</span>
                          <input
                            v-if="dealEditMode === 'view'"
                            class="input"
                            :value="editDeal.is_refund ? 'Да' : 'Нет'"
                            readonly
                          />
                          <label v-else class="check-item" :title="refundEditBlockedReason">
                            <input
                              v-model="editDeal.is_refund"
                              type="checkbox"
                              :disabled="!canEditRefundFlag"
                            />
                            <span>Произвести возврат</span>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'rental'" class="deal-form__rental-layout">
                          <div class="deal-form__rental-main">
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Источник</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="getSourceLabelById(editDeal.source_id)"
                                  readonly
                                />
                                <select v-else v-model.number="editDeal.source_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="s in sourcesByCode" :key="s.source_id" :value="s.source_id">
                                    {{ s.name }} ({{ s.code }})
                                  </option>
                                </select>
                              </label>
                              <label class="field">
                                <span class="label">Мессенджер</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="getMessengerLabelById(editDeal.messenger_id)"
                                  readonly
                                />
                                <select v-else v-model.number="editDeal.messenger_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="m in messengersByCode" :key="m.messenger_id" :value="m.messenger_id">
                                    {{ m.name }} ({{ m.code }})
                                  </option>
                                </select>
                              </label>
                            </div>
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Номер заявки</span>
                                <input v-model.trim="editDeal.order_number" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
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
                                  :readonly="dealEditMode === 'view'"
                                />
                              </label>
                            </div>
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Покупатель</span>
                                <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                              </label>
                              <label class="field">
                                <span class="label">Ответственный</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="editDealResponsible || '— не выбрано —'"
                                  readonly
                                />
                                <select v-else v-model="editDealResponsible" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option
                                    v-for="responsibleName in responsibleUserOptions"
                                    :key="`edit-rental-responsible-${responsibleName}`"
                                    :value="responsibleName"
                                  >
                                    {{ responsibleName }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <label class="field field--sharing-account">
                              <span
                                v-if="dealEditMode === 'view' || dealAccountsForProductLoading || !editDeal.product_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length || editDeal.account_id"
                                class="label"
                              >
                                Аккаунт
                              </span>
                              <input
                                v-if="dealEditMode === 'view'"
                                class="input"
                                :value="getDealAccountLoginLabel('edit')"
                                readonly
                              />
                              <select
                                v-else-if="dealAccountsForProductLoading || !editDeal.product_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length || editDeal.account_id"
                                v-model.number="editDeal.account_id"
                                class="input input--select"
                                :disabled="!editDeal.product_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForProductLoading"
                              >
                                <option value="">
                                  {{ !editDeal.product_id ? 'Сначала выберите товар' : (!editDeal.slot_type_code ? 'Сначала выберите слот' : (dealAccountsForProductLoading ? '(формируется список)' : '— не выбрано —')) }}
                                </option>
                                <option v-for="a in dealAccountsForEdit" :key="a.account_id" :value="a.account_id">
                                  {{ a.login_full || a.account_id }}
                                </option>
                              </select>
                              <div v-if="canForceEditDuplicate" class="field field--inline-actions">
                                <button class="comment-toggle" type="button" @click="forceEditDuplicateMode = !forceEditDuplicateMode">
                                  {{ forceEditDuplicateMode ? 'Скрыть дубли' : 'Сделать дубль' }}
                                </button>
                              </div>
                              <div
                                v-if="shouldShowEditDuplicateList"
                                :class="[
                                  'quick-create',
                                  { 'quick-create--plain': isEditRentalSubscriptionMode || !hasAnyProductAssignmentsEdit || !dealProductAssignmentsForSelectedSlotEdit.length }
                                ]"
                              >
                                <div v-if="!dealLoading && !isEditRentalSubscriptionMode && hasAnyProductAssignmentsEdit && dealGameAssignmentsLoadingEdit" class="loader-wrap loader-wrap--compact">
                                  <div class="newtons-cradle" aria-label="Loading" role="img">
                                    <div class="newtons-cradle__dot"></div>
                                    <div class="newtons-cradle__dot"></div>
                                    <div class="newtons-cradle__dot"></div>
                                    <div class="newtons-cradle__dot"></div>
                                  </div>
                                </div>
                                <div v-else-if="!isEditRentalSubscriptionMode && hasAnyProductAssignmentsEdit && dealProductAssignmentsForSelectedSlotEdit.length" class="quick-create__table-scroll">
                                  <div class="quick-create__title">Список занятых слотов</div>
                                  <table class="table table--compact table--dense">
                                    <thead>
                                      <tr>
                                        <th>Аккаунт</th>
                                        <th>Слот</th>
                                        <th>Покупатель</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr
                                        v-for="s in dealProductAssignmentsForSelectedSlotEdit"
                                        :key="s.assignment_id"
                                        class="table-row--slot-release"
                                        @click="releaseSlotFromDeal(s, 'edit')"
                                      >
                                        <td>{{ getAccountLabelById(s.account_id) }}</td>
                                        <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                        <td>{{ s.customer_nickname || '—' }}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </label>
                            <div class="field field--comment-collapsible">
                              <button class="comment-toggle" type="button" @click="editDealCommentOpen = !editDealCommentOpen">
                                {{ editDealCommentOpen || editDeal.notes ? 'Комментарий' : '+ Комментарий' }}
                              </button>
                              <textarea
                                v-if="editDealCommentOpen || editDeal.notes"
                                v-model.trim="editDeal.notes"
                                class="input input--textarea input--textarea--compact"
                                :rows="getCompactNotesRows(editDeal.notes)"
                                :readonly="dealEditMode === 'view'"
                              />
                            </div>
                          </div>
                          <div class="deal-form__rental-side">
                            <div
                              v-if="showEditQuickAccountReminder"
                              class="deal-form__quick-reminder deal-form__quick-reminder--top"
                            >
                              <div class="deal-form__quick-reminder-title">Напоминание: заполните быстрый аккаунт до конца</div>
                              <div class="deal-form__quick-reminder-text">{{ editQuickAccountMissingText }}</div>
                            </div>
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Тип товара</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="selectedEditDealProductTypeLabel"
                                  readonly
                                />
                                <select v-else v-model="editDealProductTypeFilter" class="input input--select">
                                  <option value="game">Игра</option>
                                  <option value="subscription">Подписка</option>
                                </select>
                              </label>
                              <label
                                v-if="dealEditMode === 'view' || isEditRentalSubscriptionMode || dealAccountsForProductLoading || !editDeal.product_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length"
                                class="field"
                              >
                                <span class="label">Тип слота</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="getSlotTypeLabel(editDeal.slot_type_code)"
                                  readonly
                                />
                                <select
                                  v-else
                                  v-model="editDeal.slot_type_code"
                                  class="input input--select"
                                  :disabled="(!isEditRentalSubscriptionMode && !editDeal.product_id) || dealSlotAvailabilityLoadingEdit"
                                >
                                  <option value="">{{ (!isEditRentalSubscriptionMode && !editDeal.product_id) ? 'Сначала выберите товар' : (dealSlotAvailabilityLoadingEdit ? '(формируется список)' : '— не выбрано —') }}</option>
                                  <option
                                    v-for="st in getSlotTypeOptionsForDeal('edit')"
                                    :key="st.code"
                                    :value="st.code"
                                    :disabled="st.supported === false"
                                  >
                                    {{ getDealSlotTypeLabel(st) }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <label v-if="isEditRentalSubscriptionMode && editDeal.product_id && !editDeal.subscription_term_id" class="field">
                              <span class="label">Срок подписки</span>
                              <input
                                v-if="dealEditMode === 'view'"
                                class="input"
                                :value="getSelectedEditSubscriptionTermLabel()"
                                readonly
                              />
                              <select
                                v-else
                                v-model.number="editDeal.subscription_term_id"
                                class="input input--select"
                                :disabled="!editDeal.slot_type_code || subscriptionTermsLoadingEdit"
                              >
                                <option value="">
                                  {{ !editDeal.slot_type_code ? 'Сначала выберите слот' : (subscriptionTermsLoadingEdit ? '(формируется список)' : '— не выбрано —') }}
                                </option>
                                <option
                                  v-for="term in editSubscriptionTermOptions"
                                  :key="`edit-sub-term-${term.term_id}`"
                                  :value="term.term_id"
                                >
                                  {{ formatSubscriptionTermLabel(term) }}
                                </option>
                              </select>
                            </label>
                            <div
                              v-if="dealEditMode !== 'view' && isEditRentalSubscriptionMode && editDeal.product_id && editDeal.slot_type_code && !editDeal.subscription_term_id"
                              class="quick-create quick-create--subscription-term"
                            >
                              <div class="quick-create__header">
                                <button class="comment-toggle" type="button" @click="editQuickSubscriptionTermOpen = !editQuickSubscriptionTermOpen">
                                  {{ editQuickSubscriptionTermOpen ? 'Добавить срок подписки' : '+ Добавить срок подписки' }}
                                </button>
                                <button
                                  v-if="editQuickSubscriptionTermOpen"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="quickEditSubscriptionTermLoading"
                                  @click="createQuickSubscriptionTerm('edit')"
                                >
                                  <span v-if="quickEditSubscriptionTermLoading" class="spinner spinner--small"></span>
                                  Добавить
                                </button>
                              </div>
                              <template v-if="editQuickSubscriptionTermOpen">
                                <div class="deal-form__double">
                                  <select v-model.number="quickEditSubscriptionTerm.account_id" class="input input--select input--compact">
                                    <option value="">— аккаунт —</option>
                                    <option v-for="a in dealAccountsForEdit" :key="`qe-term-account-${a.account_id}`" :value="a.account_id">
                                      {{ a.login_full || a.account_id }}
                                    </option>
                                  </select>
                                  <input
                                    v-model="quickEditSubscriptionTerm.valid_until"
                                    class="input input--compact"
                                    type="date"
                                  />
                                </div>
                                <input
                                  v-model.trim="quickEditSubscriptionTerm.notes"
                                  class="input input--compact"
                                  placeholder="Комментарий (опционально)"
                                />
                                <span v-if="quickEditSubscriptionTermError" class="bad">{{ quickEditSubscriptionTermError }}</span>
                              </template>
                            </div>
                            <label
                              v-if="!isEditRentalSubscriptionMode || showEditDealProductSearch || editDeal.subscription_term_id"
                              class="field"
                            >
                              <span class="label">{{ showEditDealProductSearch ? 'Поиск' : 'Товар' }}</span>
                              <input
                                v-if="dealEditMode === 'view'"
                                class="input"
                                :value="getDealProductDisplayLabel('edit')"
                                readonly
                              />
                              <div v-else-if="showEditDealProductSearch" class="input input--search-row">
                                <input
                                  v-model.trim="editDealProductSearch"
                                  class="input--search-field"
                                  placeholder="поиск товара"
                                  @input="onEditDealProductSearch"
                                />
                              </div>
                              <div v-else-if="dealEditMode !== 'view'" class="input--select-wrap">
                                <input
                                  class="input"
                                  :value="editDeal.product_id
                                    ? getDealProductDisplayLabel('edit')
                                    : (isEditRentalSubscriptionMode && !editDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —')"
                                  readonly
                                />
                                <button
                                  v-if="editDeal.product_id"
                                  class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                  type="button"
                                  aria-label="Очистить товар"
                                  title="Очистить товар"
                                  @click="clearEditDealProduct"
                                >
                                  <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M6 6l12 12M18 6l-12 12" />
                                  </svg>
                                </button>
                              </div>
                            </label>
                            <label
                              v-if="dealEditMode !== 'view' && showEditDealProductSearch"
                              :class="[
                                'field field--product field--sharing-product-list',
                                {
                                  'field--sharing-product-list--selected': !!editDeal.product_id,
                                  'field--sharing-product-list--collapsed-empty': showEditDealProductNoMatches && !editQuickProductOpen,
                                  'field--sharing-product-list--expanded-empty': showEditDealProductNoMatches && editQuickProductOpen,
                                }
                              ]"
                            >
                              <div class="input--select-wrap">
                                <select
                                  v-if="!showEditDealProductNoMatches && isEditRentalSubscriptionMode"
                                  v-model.number="editDeal.subscription_term_id"
                                  :class="[
                                    'input input--select input--list input--list--product-short',
                                    {
                                      'input--list--sharing-height': !editDeal.subscription_term_id,
                                      'input--list--compact': !!editDeal.subscription_term_id,
                                    }
                                  ]"
                                  :size="editDeal.subscription_term_id ? 1 : 3"
                                  :disabled="isEditRentalSubscriptionMode && !editDeal.slot_type_code"
                                  @change="applyEditSubscriptionSelectionByTermId()"
                                >
                                  <option value="">
                                    {{ isEditRentalSubscriptionMode && !editDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —' }}
                                  </option>
                                  <option v-for="g in availableSubscriptionItemsEditFiltered" :key="`edit-sub-item-${g.term_id}`" :value="g.term_id">
                                    {{ formatAvailableSubscriptionItemLabel(g) }}
                                  </option>
                                </select>
                                <select
                                  v-else-if="!showEditDealProductNoMatches"
                                  v-model.number="editDeal.product_id"
                                  :class="[
                                    'input input--select input--list input--list--product-short',
                                    {
                                      'input--list--sharing-height': !editDeal.product_id,
                                      'input--list--compact': !!editDeal.product_id,
                                    }
                                  ]"
                                  :size="editDeal.product_id ? 1 : 3"
                                  :disabled="isEditRentalSubscriptionMode && !editDeal.slot_type_code"
                                  @change="syncEditDealProductSearch"
                                >
                                  <option value="">
                                    {{ isEditRentalSubscriptionMode && !editDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —' }}
                                  </option>
                                  <option v-for="g in filteredEditDealProductsByType" :key="g.product_id" :value="g.product_id">
                                    {{ getProductLabelById(g.product_id) }}
                                  </option>
                                </select>
                                <button
                                  v-if="editDeal.product_id"
                                  class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                  type="button"
                                  aria-label="Очистить товар"
                                  title="Очистить товар"
                                  @click="clearEditDealProduct"
                                >
                                  <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M6 6l12 12M18 6l-12 12" />
                                  </svg>
                                </button>
                              </div>
                              <div
                                v-if="showEditDealProductNoMatches && !isEditRentalSubscriptionMode"
                                :class="[
                                  'quick-create quick-create--product-empty',
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
                                    :disabled="quickEditProductLoading"
                                    @click="createQuickProduct('edit')"
                                  >
                                    <span v-if="quickEditProductLoading" class="spinner spinner--small"></span>
                                    Создать
                                  </button>
                                </div>
                                <template v-if="editQuickProductOpen">
                                  <input v-model.trim="quickEditProduct.title" class="input input--compact" placeholder="Название товара" />
                                  <div class="check-list check-list--compact check-list--platform-row">
                                    <label v-for="p in platforms" :key="`qe-${p.code}`" class="check-item">
                                      <input type="checkbox" :value="p.code" v-model="quickEditProduct.platform_codes" />
                                      <span>{{ p.name }} ({{ p.code }})</span>
                                    </label>
                                  </div>
                                  <span v-if="quickEditProductError" class="bad">{{ quickEditProductError }}</span>
                                </template>
                              </div>
                              <div v-if="showEditDealProductNoMatches && isEditRentalSubscriptionMode" class="quick-create quick-create--plain">
                                <div class="quick-create__title">Свободных подписок на выбранный слот нет</div>
                              </div>
                            </label>
                            <div v-if="editDeal.account_id" class="deal-form__account-details">
                              <div class="deal-form__account-details-head">Данные аккаунта</div>
                              <div v-if="!dealLoading && shouldShowDealAccountDetailsLoader('edit')" class="loader-wrap loader-wrap--compact deal-form__account-details-loader">
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
                              <template v-else>
                                <label class="field">
                                  <span class="label">Логин</span>
                                  <div class="input--select-wrap">
                                    <input class="input input--with-copy" :value="getDealAccountLoginLabel('edit')" readonly />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('edit', 'login')"
                                      :title="getSharingFieldCopyLabel('edit', 'login')"
                                      :disabled="!getSharingFieldCopyValue('edit', 'login')"
                                      @click="copySharingField('edit', 'login')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                                <label class="field">
                                  <span class="label">Пароль</span>
                                  <div class="input--select-wrap">
                                    <input class="input input--with-copy" :value="getAccountPasswordById(editDeal.account_id)" readonly />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('edit', 'password')"
                                      :title="getSharingFieldCopyLabel('edit', 'password')"
                                      :disabled="!getSharingFieldCopyValue('edit', 'password')"
                                      @click="copySharingField('edit', 'password')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                                <label class="field">
                                  <span class="label">Резерв</span>
                                  <div class="input--select-wrap">
                                    <input
                                      class="input input--with-copy"
                                      :value="getDealReserveLabel(editDeal.account_id, editDeal.reserve_key, editDeal.deal_id, { allowFallback: dealEditMode === 'edit', emptyLabel: '— не назначен' })"
                                      readonly
                                    />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('edit', 'reserve')"
                                      :title="getSharingFieldCopyLabel('edit', 'reserve')"
                                      :disabled="!getSharingFieldCopyValue('edit', 'reserve')"
                                      @click="copySharingField('edit', 'reserve')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                              </template>
                            </div>
                            <div
                              v-if="dealEditMode !== 'view'
                                && !dealAccountsForProductLoading
                                && editDeal.slot_type_code
                                && !editDeal.account_id
                                && !isDealSlotTypeUnsupported('edit')
                                && (
                                  (isEditRentalSubscriptionMode && (editDeal.product_id || showEditDealProductNoMatches))
                                  || (!isEditRentalSubscriptionMode && editDeal.product_id && !hasFreeDealSlots('edit'))
                                )"
                              class="quick-create quick-create--account"
                            >
                              <div
                                v-if="showEditQuickAccountReminder"
                                class="deal-form__quick-reminder"
                              >
                                <div class="deal-form__quick-reminder-title">Напоминание: заполните быстрый аккаунт до конца</div>
                                <div class="deal-form__quick-reminder-text">{{ editQuickAccountMissingText }}</div>
                              </div>
                              <div class="quick-create__header">
                                <button class="comment-toggle" type="button" @click="editQuickAccountOpen = !editQuickAccountOpen">
                                  {{ editQuickAccountOpen ? 'Быстрое создание аккаунта' : '+ Быстрое создание аккаунта' }}
                                </button>
                                <button
                                  v-if="editQuickAccountOpen"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="quickEditAccountLoading"
                                  @click="createQuickAccount('edit')"
                                >
                                  <span v-if="quickEditAccountLoading" class="spinner spinner--small"></span>
                                  Создать
                                </button>
                              </div>
                              <template v-if="editQuickAccountOpen">
                                <select
                                  v-if="isEditRentalSubscriptionMode && !editDeal.product_id"
                                  v-model.number="quickEditAccount.subscription_product_id"
                                  class="input input--select input--compact"
                                >
                                  <option value="">— подписка —</option>
                                  <option v-for="p in quickEditAccountSubscriptionProducts" :key="`qe-sub-product-${p.product_id}`" :value="p.product_id">
                                    {{ getProductLabelById(p.product_id) }}
                                  </option>
                                </select>
                                <div class="deal-form__double">
                                  <input v-model.trim="quickEditAccount.login_name" class="input input--compact" placeholder="Логин" />
                                  <select v-model="quickEditAccount.domain_code" class="input input--select input--compact">
                                    <option value="">— домен —</option>
                                    <option v-for="d in domains" :key="`qe-d-${d.code}`" :value="d.code">
                                      {{ d.name }} ({{ d.code }})
                                    </option>
                                  </select>
                                </div>
                                <div class="deal-form__double">
                                  <input v-model.trim="quickEditAccount.password" class="input input--compact" placeholder="Пароль аккаунта" />
                                  <input v-model.trim="quickEditAccount.notes" class="input input--compact" placeholder="Комментарий" />
                                </div>
                                <div class="check-list check-list--compact check-list--platform-row">
                                  <label v-for="p in platforms" :key="`qe-p-${p.code}`" class="check-item">
                                    <input type="checkbox" :value="p.code" v-model="quickEditAccount.platform_codes" />
                                    <span>{{ p.name }} ({{ p.code }})</span>
                                  </label>
                                </div>
                                <span v-if="quickEditAccountError" class="bad">{{ quickEditAccountError }}</span>
                              </template>
                            </div>
                          </div>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-status-row">
                          <label class="field">
                            <span class="label">Дата создания</span>
                            <input
                              v-if="dealEditMode !== 'view' && canEditSystemDates"
                              v-model="editDeal.created_at"
                              class="input"
                              type="datetime-local"
                            />
                            <input
                              v-else
                              class="input"
                              :value="formatDateTimeMinutes(editDeal.created_at)"
                              readonly
                            />
                          </label>
                          <label class="field">
                            <span class="label">Дата завершения</span>
                            <input
                              v-if="dealEditMode !== 'view' && canEditSystemDates"
                              v-model="editDeal.completed_at"
                              class="input"
                              type="datetime-local"
                            />
                            <input
                              v-else
                              class="input"
                              :value="editDeal.completed_at ? formatDateTimeMinutes(editDeal.completed_at) : '—'"
                              readonly
                            />
                          </label>
                          <label class="field">
                            <span class="label">Статус</span>
                            <input
                              v-if="dealEditMode === 'view'"
                              class="input"
                              :value="getFlowStatusLabel(editDeal.flow_status_code)"
                              readonly
                            />
                            <select v-else v-model="editDeal.flow_status_code" class="input input--select">
                              <option value="">— не выбрано —</option>
                              <option v-for="s in editFlowStatusOptions" :key="s.code" :value="s.code">
                                {{ s.name }}
                              </option>
                            </select>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'sale' && !isEditDealPendingFlow && (dealEditMode !== 'view' || editDeal.is_refund)" class="field">
                          <span class="label">Возврат</span>
                          <input
                            v-if="dealEditMode === 'view'"
                            class="input"
                            :value="editDeal.is_refund ? 'Да' : 'Нет'"
                            readonly
                          />
                          <label v-else class="check-item" :title="refundEditBlockedReason">
                            <input
                              v-model="editDeal.is_refund"
                              type="checkbox"
                              :disabled="!canEditRefundFlag"
                            />
                            <span>Произвести возврат</span>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__sale-layout">
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Мессенджер</span>
                              <input
                                v-if="dealEditMode === 'view'"
                                class="input"
                                :value="getMessengerLabelById(editDeal.messenger_id)"
                                readonly
                              />
                              <select v-else v-model.number="editDeal.messenger_id" class="input input--select">
                                <option value="">— не выбрано —</option>
                                <option v-for="m in messengersByCode" :key="m.messenger_id" :value="m.messenger_id">
                                  {{ m.name }} ({{ m.code }})
                                </option>
                              </select>
                            </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--source">
                              <label class="field">
                                <span class="label">Источник</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="getSourceLabelById(editDeal.source_id)"
                                  readonly
                                />
                                <select v-else v-model.number="editDeal.source_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="s in sourcesByCode" :key="s.source_id" :value="s.source_id">
                                    {{ s.name }} ({{ s.code }})
                                  </option>
                                </select>
                              </label>
                              <label class="field">
                                <span class="label">Номер заказа</span>
                                <input v-model.trim="editDeal.order_number" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                              </label>
                              <label class="field">
                                <span class="label">Ответственный</span>
                                <input
                                  v-if="dealEditMode === 'view'"
                                  class="input"
                                  :value="editDealResponsible || '— не выбрано —'"
                                  readonly
                                />
                                <select v-else v-model="editDealResponsible" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option
                                    v-for="responsibleName in responsibleUserOptions"
                                    :key="`edit-responsible-${responsibleName}`"
                                    :value="responsibleName"
                                  >
                                    {{ responsibleName }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <div class="field field--comment-collapsible deal-form__sale-comment">
                              <button class="comment-toggle" type="button" @click="editDealCommentOpen = !editDealCommentOpen">
                                {{ editDealCommentOpen || editDeal.notes ? 'Комментарий' : '+ Комментарий' }}
                              </button>
                              <textarea
                                v-if="editDealCommentOpen || editDeal.notes"
                                v-model.trim="editDeal.notes"
                                class="input input--textarea input--textarea--compact"
                                :rows="getCompactNotesRows(editDeal.notes)"
                                :readonly="dealEditMode === 'view'"
                              />
                            </div>
                          </div>
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Покупатель</span>
                              <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                            </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--account">
                              <label class="field">
                                <span class="label">Логин</span>
                                <input v-model.trim="editDeal.login" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                              </label>
                              <label class="field">
                                <span class="label">Пароль</span>
                                <input v-model.trim="editDeal.password" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                              </label>
                              <div class="deal-form__sale-links">
                                <label v-if="getSaleProductLinks('edit').length" class="field">
                                  <span class="label">Ссылка на товар</span>
                                  <div
                                    v-for="(linkValue, linkIndex) in editSaleProductLinks"
                                    :key="`edit-sale-link-${linkIndex}-${linkValue}`"
                                    class="deal-form__sale-link-row"
                                  >
                                    <div class="input--select-wrap">
                                      <input
                                        :value="linkValue"
                                        class="input input--with-copy"
                                        placeholder="https://..."
                                        :readonly="dealEditMode === 'view'"
                                        @input="setSaleProductLinkValue('edit', linkIndex, $event.target.value)"
                                      />
                                      <button
                                        class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                        type="button"
                                        :aria-label="getSaleLinkCopyLabel('edit', linkIndex)"
                                        :title="getSaleLinkCopyLabel('edit', linkIndex)"
                                        :disabled="!getSaleProductLinkValue('edit', linkIndex)"
                                        @click="copySaleProductLink('edit', linkIndex)"
                                      >
                                        <svg viewBox="0 0 24 24" aria-hidden="true">
                                          <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                          <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                        </svg>
                                      </button>
                                    </div>
                                    <button
                                      v-if="dealEditMode !== 'view' && canRemoveSaleProductLink('edit')"
                                      class="ghost ghost--small deal-form__sale-link-remove"
                                      type="button"
                                      @click="removeSaleProductLink('edit', linkIndex)"
                                    >
                                      Удалить
                                    </button>
                                  </div>
                                </label>
                                <button
                                  v-if="dealEditMode !== 'view'"
                                  class="comment-toggle deal-form__sale-link-add"
                                  type="button"
                                  @click="addSaleProductLink('edit')"
                                >
                                  + Добавить ссылку
                                </button>
                              </div>
                            </div>
                          </div>
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Регион</span>
                              <input
                                v-if="dealEditMode === 'view'"
                                class="input"
                                :value="getRegionLabel(editDeal.region_code)"
                                readonly
                              />
                              <select v-else v-model="editDeal.region_code" class="input input--select">
                                <option value="">— не выбрано —</option>
                                <option v-for="r in regions" :key="r.code" :value="r.code">
                                {{ r.name }} ({{ r.code }})
                              </option>
                            </select>
                          </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--price">
                              <label class="field">
                                <span class="label">Закупочная цена</span>
                                <input
                                  v-model.number="editDeal.purchase_cost"
                                  class="input"
                                  type="number"
                                  min="0"
                                  :max="maxPrice"
                                  @input="editDeal.purchase_cost = clampPrice(editDeal.purchase_cost)"
                                  :readonly="dealEditMode === 'view'"
                                />
                              </label>
                              <label class="field">
                                <span class="label">Сумма продажи</span>
                                <input
                                  v-model.number="editDeal.price"
                                  class="input"
                                  type="number"
                                  min="0"
                                  :max="maxPrice"
                                  @input="editDeal.price = clampPrice(editDeal.price)"
                                  :readonly="dealEditMode === 'view'"
                                />
                              </label>
                              <div class="deal-form__sale-col-bottom">
                                <label class="field">
                                  <span class="label">Метод оплаты</span>
                                  <select class="input input--select deal-form__input--locked" disabled>
                                    <option value="">— скоро будет —</option>
                                  </select>
                                </label>
                                <label class="field">
                                  <span class="label">Скидка</span>
                                  <select class="input input--select deal-form__input--locked" disabled>
                                    <option value="">— скоро будет —</option>
                                  </select>
                                </label>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="deal-form__full">
                        <div v-if="dealError" class="field field--inline-actions">
                          <p class="bad">{{ dealError }}</p>
                          <button
                            v-if="conflictDealIdFromError"
                            class="ghost ghost--small"
                            type="button"
                            @click="openConflictDealFromError"
                          >
                            Открыть сделку #{{ conflictDealIdFromError }}
                          </button>
                        </div>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div v-if="dealEditMode === 'edit'" class="toolbar-actions"></div>
                      </div>
                    </div>
                    <div v-else class="form deal-form" :class="{ 'deal-form--sale': newDeal.deal_type_code === 'sale' || newDeal.deal_type_code === 'rental' }">
                      <div class="deal-form__col deal-form__col--left">
                        <div v-if="newDeal.deal_type_code === 'rental'" class="deal-form__rental-layout">
                          <div class="deal-form__rental-main">
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Источник</span>
                                <select v-model.number="newDeal.source_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="s in sourcesByCode" :key="s.source_id" :value="s.source_id">
                                    {{ s.name }} ({{ s.code }})
                                  </option>
                                </select>
                              </label>
                              <label class="field">
                                <span class="label">Мессенджер</span>
                                <select v-model.number="newDeal.messenger_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="m in messengersByCode" :key="m.messenger_id" :value="m.messenger_id">
                                    {{ m.name }} ({{ m.code }})
                                  </option>
                                </select>
                              </label>
                            </div>
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Номер заявки</span>
                                <input v-model.trim="newDeal.order_number" class="input" placeholder="-" />
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
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Покупатель</span>
                                <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="-" />
                              </label>
                              <label class="field">
                                <span class="label">Ответственный</span>
                                <select v-model="newDealResponsible" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option
                                    v-for="responsibleName in responsibleUserOptions"
                                    :key="`new-rental-responsible-${responsibleName}`"
                                    :value="responsibleName"
                                  >
                                    {{ responsibleName }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <label class="field field--sharing-account">
                          <span
                            v-if="dealAccountsForProductLoading || !newDeal.product_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForNew.length || newDeal.account_id"
                            class="label"
                          >
                            Аккаунт
                          </span>
                          <select
                            v-if="dealAccountsForProductLoading || !newDeal.product_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForNew.length || newDeal.account_id"
                            v-model.number="newDeal.account_id"
                            class="input input--select"
                            :disabled="!newDeal.product_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForProductLoading"
                          >
                            <option value="">
                              {{ !newDeal.product_id ? 'Сначала выберите товар' : (!newDeal.slot_type_code ? 'Сначала выберите слот' : (dealAccountsForProductLoading ? '(формируется список)' : '— не выбрано —')) }}
                            </option>
                            <option v-for="a in dealAccountsForNew" :key="a.account_id" :value="a.account_id">
                              {{ a.login_full || a.account_id }}
                            </option>
                          </select>
                          <div v-if="canForceNewDuplicate" class="field field--inline-actions">
                            <button class="comment-toggle" type="button" @click="forceNewDuplicateMode = !forceNewDuplicateMode">
                              {{ forceNewDuplicateMode ? 'Скрыть дубли' : 'Сделать дубль' }}
                            </button>
                          </div>
                          <div
                            v-if="shouldShowNewDuplicateList"
                            :class="[
                              'quick-create',
                              { 'quick-create--plain': isNewRentalSubscriptionMode || !hasAnyProductAssignmentsNew || !dealProductAssignmentsForSelectedSlotNew.length }
                            ]"
                          >
                            <div v-if="!dealLoading && !isNewRentalSubscriptionMode && hasAnyProductAssignmentsNew && dealGameAssignmentsLoadingNew" class="loader-wrap loader-wrap--compact">
                              <div class="newtons-cradle" aria-label="Loading" role="img">
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                              </div>
                            </div>
                            <div v-else-if="!isNewRentalSubscriptionMode && hasAnyProductAssignmentsNew && dealProductAssignmentsForSelectedSlotNew.length" class="quick-create__table-scroll">
                              <div class="quick-create__title">Список занятых слотов</div>
                              <table class="table table--compact table--dense">
                                <thead>
                                  <tr>
                                    <th>Аккаунт</th>
                                    <th>Слот</th>
                                    <th>Покупатель</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  <tr
                                    v-for="s in dealProductAssignmentsForSelectedSlotNew"
                                    :key="s.assignment_id"
                                    class="table-row--slot-release"
                                    @click="releaseSlotFromDeal(s, 'new')"
                                  >
                                    <td>{{ getAccountLabelById(s.account_id) }}</td>
                                    <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                                    <td>{{ s.customer_nickname || '—' }}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </label>
                            <div class="field field--comment-collapsible">
                              <button class="comment-toggle" type="button" @click="newDealCommentOpen = !newDealCommentOpen">
                                {{ newDealCommentOpen || newDeal.notes ? 'Комментарий' : '+ Комментарий' }}
                              </button>
                              <textarea
                                v-if="newDealCommentOpen || newDeal.notes"
                                v-model.trim="newDeal.notes"
                                class="input input--textarea input--textarea--compact"
                                :rows="getCompactNotesRows(newDeal.notes)"
                              />
                            </div>
                          </div>
                          <div class="deal-form__rental-side">
                            <div
                              v-if="showNewQuickAccountReminder"
                              class="deal-form__quick-reminder deal-form__quick-reminder--top"
                            >
                              <div class="deal-form__quick-reminder-title">Напоминание: заполните быстрый аккаунт до конца</div>
                              <div class="deal-form__quick-reminder-text">{{ newQuickAccountMissingText }}</div>
                            </div>
                            <div class="deal-form__double">
                              <label class="field">
                                <span class="label">Тип товара</span>
                                <select v-model="newDealProductTypeFilter" class="input input--select">
                                  <option value="game">Игра</option>
                                  <option value="subscription">Подписка</option>
                                </select>
                              </label>
                              <label class="field">
                                <span class="label">Тип слота</span>
                                <select
                                  v-model="newDeal.slot_type_code"
                                  class="input input--select"
                                  :disabled="(!isNewRentalSubscriptionMode && !newDeal.product_id) || dealSlotAvailabilityLoadingNew"
                                >
                                  <option value="">{{ (!isNewRentalSubscriptionMode && !newDeal.product_id) ? 'Сначала выберите товар' : (dealSlotAvailabilityLoadingNew ? '(формируется список)' : '— не выбрано —') }}</option>
                                  <option
                                    v-for="st in getSlotTypeOptionsForDeal('new')"
                                    :key="st.code"
                                    :value="st.code"
                                    :disabled="st.supported === false"
                                  >
                                    {{ getDealSlotTypeLabel(st) }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <label v-if="isNewRentalSubscriptionMode && newDeal.product_id && !newDeal.subscription_term_id" class="field">
                              <span class="label">Срок подписки</span>
                              <select
                                v-model.number="newDeal.subscription_term_id"
                                class="input input--select"
                                :disabled="!newDeal.slot_type_code || subscriptionTermsLoadingNew"
                              >
                                <option value="">
                                  {{ !newDeal.slot_type_code ? 'Сначала выберите слот' : (subscriptionTermsLoadingNew ? '(формируется список)' : '— не выбрано —') }}
                                </option>
                                <option
                                  v-for="term in newSubscriptionTermOptions"
                                  :key="`new-sub-term-${term.term_id}`"
                                  :value="term.term_id"
                                >
                                  {{ formatSubscriptionTermLabel(term) }}
                                </option>
                              </select>
                            </label>
                            <div
                              v-if="isNewRentalSubscriptionMode && newDeal.product_id && newDeal.slot_type_code && !newDeal.subscription_term_id"
                              class="quick-create quick-create--subscription-term"
                            >
                              <div class="quick-create__header">
                                <button class="comment-toggle" type="button" @click="newQuickSubscriptionTermOpen = !newQuickSubscriptionTermOpen">
                                  {{ newQuickSubscriptionTermOpen ? 'Добавить срок подписки' : '+ Добавить срок подписки' }}
                                </button>
                                <button
                                  v-if="newQuickSubscriptionTermOpen"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="quickNewSubscriptionTermLoading"
                                  @click="createQuickSubscriptionTerm('new')"
                                >
                                  <span v-if="quickNewSubscriptionTermLoading" class="spinner spinner--small"></span>
                                  Добавить
                                </button>
                              </div>
                              <template v-if="newQuickSubscriptionTermOpen">
                                <div class="deal-form__double">
                                  <select v-model.number="quickNewSubscriptionTerm.account_id" class="input input--select input--compact">
                                    <option value="">— аккаунт —</option>
                                    <option v-for="a in dealAccountsForNew" :key="`qn-term-account-${a.account_id}`" :value="a.account_id">
                                      {{ a.login_full || a.account_id }}
                                    </option>
                                  </select>
                                  <input
                                    v-model="quickNewSubscriptionTerm.valid_until"
                                    class="input input--compact"
                                    type="date"
                                  />
                                </div>
                                <input
                                  v-model.trim="quickNewSubscriptionTerm.notes"
                                  class="input input--compact"
                                  placeholder="Комментарий (опционально)"
                                />
                                <span v-if="quickNewSubscriptionTermError" class="bad">{{ quickNewSubscriptionTermError }}</span>
                              </template>
                            </div>
                            <label
                              v-if="!isNewRentalSubscriptionMode || showNewDealProductSearch || newDeal.subscription_term_id"
                              class="field"
                            >
                              <span class="label">{{ showNewDealProductSearch ? 'Поиск' : 'Товар' }}</span>
                              <div v-if="showNewDealProductSearch" class="input input--search-row">
                                <input
                                  v-model.trim="newDealProductSearch"
                                  class="input--search-field"
                                  placeholder="поиск товара"
                                  @input="onNewDealProductSearch"
                                />
                              </div>
                              <div v-else class="input--select-wrap">
                                <input
                                  class="input"
                                  :value="newDeal.product_id
                                    ? getDealProductDisplayLabel('new')
                                    : (isNewRentalSubscriptionMode && !newDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —')"
                                  readonly
                                />
                                <button
                                  v-if="newDeal.product_id"
                                  class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                  type="button"
                                  aria-label="Очистить товар"
                                  title="Очистить товар"
                                  @click="clearNewDealProduct"
                                >
                                  <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M6 6l12 12M18 6l-12 12" />
                                  </svg>
                                </button>
                              </div>
                            </label>
                            <label
                              v-if="showNewDealProductSearch"
                              :class="[
                                'field field--product field--sharing-product-list',
                                {
                                  'field--sharing-product-list--selected': !!newDeal.product_id,
                                  'field--sharing-product-list--collapsed-empty': showNewDealProductNoMatches && !newQuickProductOpen,
                                  'field--sharing-product-list--expanded-empty': showNewDealProductNoMatches && newQuickProductOpen,
                                }
                              ]"
                            >
                              <div class="input--select-wrap">
                                <select
                                  v-if="!showNewDealProductNoMatches && isNewRentalSubscriptionMode"
                                  v-model.number="newDeal.subscription_term_id"
                                  :class="[
                                    'input input--select input--list input--list--product-short',
                                    {
                                      'input--list--sharing-height': !newDeal.subscription_term_id,
                                      'input--list--compact': !!newDeal.subscription_term_id,
                                    }
                                  ]"
                                  :size="newDeal.subscription_term_id ? 1 : 3"
                                  :disabled="isNewRentalSubscriptionMode && !newDeal.slot_type_code"
                                  @change="applyNewSubscriptionSelectionByTermId()"
                                >
                                  <option value="">
                                    {{ isNewRentalSubscriptionMode && !newDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —' }}
                                  </option>
                                  <option v-for="g in availableSubscriptionItemsNewFiltered" :key="`new-sub-item-${g.term_id}`" :value="g.term_id">
                                    {{ formatAvailableSubscriptionItemLabel(g) }}
                                  </option>
                                </select>
                                <select
                                  v-else-if="!showNewDealProductNoMatches"
                                  v-model.number="newDeal.product_id"
                                  :class="[
                                    'input input--select input--list input--list--product-short',
                                    {
                                      'input--list--sharing-height': !newDeal.product_id,
                                      'input--list--compact': !!newDeal.product_id,
                                    }
                                  ]"
                                  :size="newDeal.product_id ? 1 : 3"
                                  :disabled="isNewRentalSubscriptionMode && !newDeal.slot_type_code"
                                  @change="syncNewDealProductSearch"
                                >
                                  <option value="">
                                    {{ isNewRentalSubscriptionMode && !newDeal.slot_type_code ? 'Сначала выберите слот' : '— не выбрано —' }}
                                  </option>
                                  <option v-for="g in filteredNewDealProductsByType" :key="g.product_id" :value="g.product_id">
                                    {{ getProductLabelById(g.product_id) }}
                                  </option>
                                </select>
                                <button
                                  v-if="newDeal.product_id"
                                  class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                  type="button"
                                  aria-label="Очистить товар"
                                  title="Очистить товар"
                                  @click="clearNewDealProduct"
                                >
                                  <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M6 6l12 12M18 6l-12 12" />
                                  </svg>
                                </button>
                              </div>
                              <div
                                v-if="showNewDealProductNoMatches && !isNewRentalSubscriptionMode"
                                :class="[
                                  'quick-create quick-create--product-empty',
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
                                    :disabled="quickNewProductLoading"
                                    @click="createQuickProduct('new')"
                                  >
                                    <span v-if="quickNewProductLoading" class="spinner spinner--small"></span>
                                    Создать
                                  </button>
                                </div>
                                <template v-if="newQuickProductOpen">
                                  <input v-model.trim="quickNewProduct.title" class="input input--compact" placeholder="Название товара" />
                                  <div class="check-list check-list--compact check-list--platform-row">
                                    <label v-for="p in platforms" :key="`qn-${p.code}`" class="check-item">
                                      <input type="checkbox" :value="p.code" v-model="quickNewProduct.platform_codes" />
                                      <span>{{ p.name }} ({{ p.code }})</span>
                                    </label>
                                  </div>
                                  <span v-if="quickNewProductError" class="bad">{{ quickNewProductError }}</span>
                                </template>
                              </div>
                              <div v-if="showNewDealProductNoMatches && isNewRentalSubscriptionMode" class="quick-create quick-create--plain">
                                <div class="quick-create__title">Свободных подписок на выбранный слот нет</div>
                              </div>
                            </label>
                            <div v-if="newDeal.account_id" class="deal-form__account-details">
                              <div class="deal-form__account-details-head">Данные аккаунта</div>
                              <div v-if="!dealLoading && shouldShowDealAccountDetailsLoader('new')" class="loader-wrap loader-wrap--compact deal-form__account-details-loader">
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
                              <template v-else>
                                <label class="field">
                                  <span class="label">Логин</span>
                                  <div class="input--select-wrap">
                                    <input class="input input--with-copy" :value="getDealAccountLoginLabel('new')" readonly />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('new', 'login')"
                                      :title="getSharingFieldCopyLabel('new', 'login')"
                                      :disabled="!getSharingFieldCopyValue('new', 'login')"
                                      @click="copySharingField('new', 'login')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                                <label class="field">
                                  <span class="label">Пароль</span>
                                  <div class="input--select-wrap">
                                    <input class="input input--with-copy" :value="getAccountPasswordById(newDeal.account_id)" readonly />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('new', 'password')"
                                      :title="getSharingFieldCopyLabel('new', 'password')"
                                      :disabled="!getSharingFieldCopyValue('new', 'password')"
                                      @click="copySharingField('new', 'password')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                                <label class="field">
                                  <span class="label">Резерв</span>
                                  <div class="input--select-wrap">
                                    <input class="input input--with-copy" :value="getDealReserveLabel(newDeal.account_id, newDeal.reserve_key, null, { allowFallback: true })" readonly />
                                    <button
                                      class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                      type="button"
                                      :aria-label="getSharingFieldCopyLabel('new', 'reserve')"
                                      :title="getSharingFieldCopyLabel('new', 'reserve')"
                                      :disabled="!getSharingFieldCopyValue('new', 'reserve')"
                                      @click="copySharingField('new', 'reserve')"
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                        <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                      </svg>
                                    </button>
                                  </div>
                                </label>
                              </template>
                            </div>
                            <div
                              v-if="!dealAccountsForProductLoading
                                && newDeal.slot_type_code
                                && !newDeal.account_id
                                && !isDealSlotTypeUnsupported('new')
                                && (
                                  (isNewRentalSubscriptionMode && (newDeal.product_id || showNewDealProductNoMatches))
                                  || (!isNewRentalSubscriptionMode && newDeal.product_id && !hasFreeDealSlots('new'))
                                )"
                              class="quick-create quick-create--account"
                            >
                              <div
                                v-if="showNewQuickAccountReminder"
                                class="deal-form__quick-reminder"
                              >
                                <div class="deal-form__quick-reminder-title">Напоминание: заполните быстрый аккаунт до конца</div>
                                <div class="deal-form__quick-reminder-text">{{ newQuickAccountMissingText }}</div>
                              </div>
                              <div class="quick-create__header">
                                <button class="comment-toggle" type="button" @click="newQuickAccountOpen = !newQuickAccountOpen">
                                  {{ newQuickAccountOpen ? 'Быстрое создание аккаунта' : '+ Быстрое создание аккаунта' }}
                                </button>
                                <button
                                  v-if="newQuickAccountOpen"
                                  class="ghost ghost--small"
                                  type="button"
                                  :disabled="quickNewAccountLoading"
                                  @click="createQuickAccount('new')"
                                >
                                  <span v-if="quickNewAccountLoading" class="spinner spinner--small"></span>
                                  Создать
                                </button>
                              </div>
                              <template v-if="newQuickAccountOpen">
                                <select
                                  v-if="isNewRentalSubscriptionMode && !newDeal.product_id"
                                  v-model.number="quickNewAccount.subscription_product_id"
                                  class="input input--select input--compact"
                                >
                                  <option value="">— подписка —</option>
                                  <option v-for="p in quickNewAccountSubscriptionProducts" :key="`qn-sub-product-${p.product_id}`" :value="p.product_id">
                                    {{ getProductLabelById(p.product_id) }}
                                  </option>
                                </select>
                                <div class="deal-form__double">
                                  <input v-model.trim="quickNewAccount.login_name" class="input input--compact" placeholder="Логин" />
                                  <select v-model="quickNewAccount.domain_code" class="input input--select input--compact">
                                    <option value="">— домен —</option>
                                    <option v-for="d in domains" :key="`qn-d-${d.code}`" :value="d.code">
                                      {{ d.name }} ({{ d.code }})
                                    </option>
                                  </select>
                                </div>
                                <div class="deal-form__double">
                                  <input v-model.trim="quickNewAccount.password" class="input input--compact" placeholder="Пароль аккаунта" />
                                  <input v-model.trim="quickNewAccount.notes" class="input input--compact" placeholder="Комментарий" />
                                </div>
                                <div class="check-list check-list--compact check-list--platform-row">
                                  <label v-for="p in platforms" :key="`qn-p-${p.code}`" class="check-item">
                                    <input type="checkbox" :value="p.code" v-model="quickNewAccount.platform_codes" />
                                    <span>{{ p.name }} ({{ p.code }})</span>
                                  </label>
                                </div>
                                <span v-if="quickNewAccountError" class="bad">{{ quickNewAccountError }}</span>
                              </template>
                            </div>
                          </div>
                        </div>
                        <div v-if="newDeal.deal_type_code === 'sale'" class="deal-form__sale-layout">
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Мессенджер</span>
                              <select v-model.number="newDeal.messenger_id" class="input input--select">
                                <option value="">— не выбрано —</option>
                                <option v-for="m in messengersByCode" :key="m.messenger_id" :value="m.messenger_id">
                                  {{ m.name }} ({{ m.code }})
                                </option>
                              </select>
                            </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--source">
                              <label class="field">
                                <span class="label">Источник</span>
                                <select v-model.number="newDeal.source_id" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option v-for="s in sourcesByCode" :key="s.source_id" :value="s.source_id">
                                    {{ s.name }} ({{ s.code }})
                                  </option>
                                </select>
                              </label>
                              <label class="field">
                                <span class="label">Номер заказа</span>
                                <input v-model.trim="newDeal.order_number" class="input" placeholder="-" />
                              </label>
                              <label class="field">
                                <span class="label">Ответственный</span>
                                <select v-model="newDealResponsible" class="input input--select">
                                  <option value="">— не выбрано —</option>
                                  <option
                                    v-for="responsibleName in responsibleUserOptions"
                                    :key="`new-sale-responsible-${responsibleName}`"
                                    :value="responsibleName"
                                  >
                                    {{ responsibleName }}
                                  </option>
                                </select>
                              </label>
                            </div>
                            <div class="field field--comment-collapsible deal-form__sale-comment">
                              <button class="comment-toggle" type="button" @click="newDealCommentOpen = !newDealCommentOpen">
                                {{ newDealCommentOpen || newDeal.notes ? 'Комментарий' : '+ Комментарий' }}
                              </button>
                              <textarea
                                v-if="newDealCommentOpen || newDeal.notes"
                                v-model.trim="newDeal.notes"
                                class="input input--textarea input--textarea--compact"
                                :rows="getCompactNotesRows(newDeal.notes)"
                              />
                            </div>
                          </div>
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Покупатель</span>
                              <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="-" />
                            </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--account">
                              <label class="field">
                                <span class="label">Логин</span>
                                <input v-model.trim="newDeal.login" class="input" placeholder="-" />
                              </label>
                              <label class="field">
                                <span class="label">Пароль</span>
                                <input v-model.trim="newDeal.password" class="input" placeholder="-" />
                              </label>
                              <div class="deal-form__sale-links">
                                <label v-if="getSaleProductLinks('new').length" class="field">
                                  <span class="label">Ссылка на товар</span>
                                  <div
                                    v-for="(linkValue, linkIndex) in newSaleProductLinks"
                                    :key="`new-sale-link-${linkIndex}-${linkValue}`"
                                    class="deal-form__sale-link-row"
                                  >
                                    <div class="input--select-wrap">
                                      <input
                                        :value="linkValue"
                                        class="input input--with-copy"
                                        placeholder="https://..."
                                        @input="setSaleProductLinkValue('new', linkIndex, $event.target.value)"
                                      />
                                      <button
                                        class="btn btn--icon-plain btn--icon-round btn--icon-clear btn--icon-clear--select"
                                        type="button"
                                        :aria-label="getSaleLinkCopyLabel('new', linkIndex)"
                                        :title="getSaleLinkCopyLabel('new', linkIndex)"
                                        :disabled="!getSaleProductLinkValue('new', linkIndex)"
                                        @click="copySaleProductLink('new', linkIndex)"
                                      >
                                        <svg viewBox="0 0 24 24" aria-hidden="true">
                                          <rect x="9" y="9" width="10" height="10" rx="2" ry="2" />
                                          <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
                                        </svg>
                                      </button>
                                    </div>
                                    <button
                                      v-if="canRemoveSaleProductLink('new')"
                                      class="ghost ghost--small deal-form__sale-link-remove"
                                      type="button"
                                      @click="removeSaleProductLink('new', linkIndex)"
                                    >
                                      Удалить
                                    </button>
                                  </div>
                                </label>
                                <button
                                  class="comment-toggle deal-form__sale-link-add"
                                  type="button"
                                  @click="addSaleProductLink('new')"
                                >
                                  + Добавить ссылку
                                </button>
                              </div>
                            </div>
                          </div>
                          <div class="deal-form__sale-col">
                            <label class="field">
                              <span class="label">Регион</span>
                              <select v-model="newDeal.region_code" class="input input--select">
                                <option value="">— не выбрано —</option>
                                <option v-for="r in regions" :key="r.code" :value="r.code">
                                {{ r.name }} ({{ r.code }})
                              </option>
                            </select>
                          </label>
                            <div class="deal-form__account-details deal-form__account-details--sale deal-form__sale-group deal-form__sale-group--price">
                              <label class="field">
                                <span class="label">Закупочная цена</span>
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
                                <span class="label">Сумма продажи</span>
                                <input
                                  v-model.number="newDeal.price"
                                  class="input"
                                  type="number"
                                  min="0"
                                  :max="maxPrice"
                                  @input="newDeal.price = clampPrice(newDeal.price)"
                                />
                              </label>
                              <div class="deal-form__sale-col-bottom">
                                <label class="field">
                                  <span class="label">Метод оплаты</span>
                                  <select class="input input--select deal-form__input--locked" disabled>
                                    <option value="">— скоро будет —</option>
                                  </select>
                                </label>
                                <label class="field">
                                  <span class="label">Скидка</span>
                                  <select class="input input--select deal-form__input--locked" disabled>
                                    <option value="">— скоро будет —</option>
                                  </select>
                                </label>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="deal-form__full">
                        <div v-if="dealError" class="field field--inline-actions">
                          <p class="bad">{{ dealError }}</p>
                          <button
                            v-if="conflictDealIdFromError"
                            class="ghost ghost--small"
                            type="button"
                            @click="openConflictDealFromError"
                          >
                            Открыть сделку #{{ conflictDealIdFromError }}
                          </button>
                        </div>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div class="toolbar-actions"></div>
                      </div>
                    </div>
</template>

<script setup>
import { computed, reactive, ref, toRefs, watch } from 'vue'

// Большая форма сделки (режим редактирования и создания) вынесена из WorkView.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  editDeal,
  dealEditMode,
  allowCompletedDealEdit,
  dealAccountsForProductLoading,
  isDealSlotTypeUnsupported,
  dealAccountsForEdit,
  getSlotTypeLabel,
  dealSlotAvailabilityLoadingEdit,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  getAccountLabelById,
  getAccountSecret,
  getReserveSecretEntries,
  accountsAll,
  accountSecrets,
  ensureAccountSecretsLoaded,
  loadAccountsAll,
  sortedDeals,
  hasFreeDealSlots,
  hasAnyProductAssignmentsEdit,
  dealGameAssignmentsLoadingEdit,
  dealProductAssignmentsForSelectedSlotEdit,
  hasAnyProductAssignmentsNew,
  dealGameAssignmentsLoadingNew,
  dealProductAssignmentsForSelectedSlotNew,
  releaseSlotFromDeal,
  quickEditAccount,
  domains,
  platforms,
  quickEditAccountLoading,
  createQuickAccount,
  quickEditAccountError,
  quickEditSubscriptionTerm,
  quickEditSubscriptionTermLoading,
  quickEditSubscriptionTermError,
  createQuickSubscriptionTerm,
  slotTypes,
  formatDateTimeMinutes,
  getRegionLabel,
  regions,
  getSourceLabelById,
  getMessengerLabelById,
  sourcesByCode,
  messengersByCode,
  maxPrice,
  clampPrice,
  getFlowStatusLabel,
  dealFlowStatusOptions,
  editDealProductSearch,
  onEditDealProductSearch,
  filteredEditDealProducts,
  subscriptionTermsEdit,
  subscriptionTermsLoadingEdit,
  subscriptionAvailableItemsEdit,
  subscriptionAvailableItemsLoadingEdit,
  syncEditDealProductSearch,
  getProductLabelById,
  editDealProductNoMatches,
  clearEditDealProduct,
  quickEditProduct,
  quickEditProductLoading,
  createQuickProduct,
  quickEditProductError,
  dealLoading,
  dealError,
  dealOk,
  newDeal,
  responsibleUserOptions,
  newDealResponsible,
  editDealResponsible,
  newDealProductSearch,
  onNewDealProductSearch,
  filteredNewDealProducts,
  subscriptionTermsNew,
  subscriptionTermsLoadingNew,
  subscriptionAvailableItemsNew,
  subscriptionAvailableItemsLoadingNew,
  newDealProductNoMatches,
  syncNewDealProductSearch,
  clearNewDealProduct,
  quickNewProduct,
  quickNewProductLoading,
  quickNewProductError,
  dealSlotAvailabilityLoadingNew,
  dealAccountsForNew,
  quickNewAccount,
  quickNewAccountLoading,
  quickNewAccountError,
  quickNewSubscriptionTerm,
  quickNewSubscriptionTermLoading,
  quickNewSubscriptionTermError,
  newDealCommentOpen,
  editDealCommentOpen,
  showDealWarning,
  getCompactNotesRows,
} = toRefs(ctx)

const editDealProductTypeFilter = ref('game')
const newDealProductTypeFilter = ref('game')
const editQuickProductOpen = ref(false)
const editQuickAccountOpen = ref(false)
const editQuickSubscriptionTermOpen = ref(false)
const newQuickProductOpen = ref(false)
const newQuickAccountOpen = ref(false)
const newQuickSubscriptionTermOpen = ref(false)
const editSaleProductLinks = ref([])
const newSaleProductLinks = ref([])
const editDealAccountDetailsLoading = ref(false)
const newDealAccountDetailsLoading = ref(false)
const copiedSaleLinkKey = ref('')
const copiedSharingFieldKey = ref('')
const forceNewDuplicateMode = ref(false)
const forceEditDuplicateMode = ref(false)
let copiedSaleLinkTimerId = 0
let copiedSharingFieldTimerId = 0

const isEditRentalSubscriptionMode = computed(() => {
  return editDeal.value?.deal_type_code === 'rental' && editDealProductTypeFilter.value === 'subscription'
})

const isNewRentalSubscriptionMode = computed(() => {
  return newDeal.value?.deal_type_code === 'rental' && newDealProductTypeFilter.value === 'subscription'
})

const showEditDealProductSearch = computed(() => {
  if (editDeal.value?.deal_type_code === 'rental' && editDealProductTypeFilter.value === 'subscription') {
    // Для подписок поиск показываем только после выбора слота и до выбора товара.
    return !!editDeal.value?.slot_type_code && !editDeal.value?.product_id
  }
  // Для игр прячем поиск после выбора товара, чтобы форма не занимала лишнее место.
  return !(editDeal.value?.deal_type_code === 'rental'
    && editDealProductTypeFilter.value === 'game'
    && Boolean(editDeal.value?.product_id))
})

const showNewDealProductSearch = computed(() => {
  if (newDeal.value?.deal_type_code === 'rental' && newDealProductTypeFilter.value === 'subscription') {
    // В создании подписки логика такая же: слот -> поиск/список -> выбранный товар.
    return !!newDeal.value?.slot_type_code && !newDeal.value?.product_id
  }
  // После сброса товара поиск снова показываем, чтобы можно было выбрать другую игру.
  return !(newDeal.value?.deal_type_code === 'rental'
    && newDealProductTypeFilter.value === 'game'
    && Boolean(newDeal.value?.product_id))
})

// Базовые условия для блока дублей в создании шеринга.
const canShowNewDuplicateArea = computed(() => {
  return !dealAccountsForProductLoading.value
    && !isNewRentalSubscriptionMode.value
    && Boolean(newDeal.value?.slot_type_code)
    && !newDeal.value?.account_id
    && !isDealSlotTypeUnsupported.value?.('new')
    && Boolean(newDeal.value?.product_id)
})

// Базовые условия для блока дублей в редактировании шеринга.
const canShowEditDuplicateArea = computed(() => {
  return dealEditMode.value !== 'view'
    && !dealAccountsForProductLoading.value
    && !isEditRentalSubscriptionMode.value
    && Boolean(editDeal.value?.slot_type_code)
    && !editDeal.value?.account_id
    && !isDealSlotTypeUnsupported.value?.('edit')
    && Boolean(editDeal.value?.product_id)
})

// Флаг доступности принудительного дубля в создании: показываем кнопку, когда есть свободные слоты и есть кандидаты дубля.
const canForceNewDuplicate = computed(() => {
  return canShowNewDuplicateArea.value
    && hasFreeDealSlots.value('new')
    && Array.isArray(dealProductAssignmentsForSelectedSlotNew.value)
    && dealProductAssignmentsForSelectedSlotNew.value.length > 0
})

// Флаг доступности принудительного дубля в редактировании.
const canForceEditDuplicate = computed(() => {
  return canShowEditDuplicateArea.value
    && hasFreeDealSlots.value('edit')
    && Array.isArray(dealProductAssignmentsForSelectedSlotEdit.value)
    && dealProductAssignmentsForSelectedSlotEdit.value.length > 0
})

// Управляет показом списка дублей в создании: либо свободных слотов нет, либо менеджер включил принудительный режим.
const shouldShowNewDuplicateList = computed(() => {
  if (!canShowNewDuplicateArea.value) return false
  return !hasFreeDealSlots.value('new') || forceNewDuplicateMode.value
})

// Управляет показом списка дублей в редактировании.
const shouldShowEditDuplicateList = computed(() => {
  if (!canShowEditDuplicateArea.value) return false
  return !hasFreeDealSlots.value('edit') || forceEditDuplicateMode.value
})

// Определяет тип выбранного товара в редактировании, чтобы в режиме просмотра показать его как текст.
const selectedEditDealProductTypeLabel = computed(() => {
  const selectedId = Number(editDeal.value?.product_id || 0)
  if (!selectedId) return '— не выбрано —'
  const list = filteredEditDealProducts.value || []
  const found = list.find((item) => Number(item?.product_id || 0) === selectedId)
  const typeCode = String(found?.type_code || '').toLowerCase()
  if (typeCode === 'game') return 'Игра'
  if (typeCode === 'subscription') return 'Подписка'
  return '— не выбрано —'
})

// Определяет тип товара у выбранной позиции в редактируемой сделке.
function getSelectedEditDealProductTypeCode() {
  const selectedId = Number(editDeal.value?.product_id || 0)
  if (!selectedId) return ''
  const list = filteredEditDealProducts.value || []
  const found = list.find((item) => Number(item?.product_id || 0) === selectedId)
  return String(found?.type_code || '').toLowerCase()
}

// Синхронизирует фильтр типа в редактировании с фактически выбранным товаром сделки.
function syncEditProductTypeFilterFromSelectedProduct() {
  if (!editDeal.value?.open || editDeal.value?.deal_type_code !== 'rental') return
  if (!editDeal.value?.product_id) return
  const currentProductTypeCode = getSelectedEditDealProductTypeCode()
  if (!currentProductTypeCode) return
  if (currentProductTypeCode === 'subscription') {
    editDealProductTypeFilter.value = 'subscription'
  } else if (currentProductTypeCode === 'game') {
    editDealProductTypeFilter.value = 'game'
  }
}

// Фильтрует товары в редактировании сделки по выбранному типу.
const filteredEditDealProductsByType = computed(() => {
  const list = filteredEditDealProducts.value || []
  if (!editDealProductTypeFilter.value) return list
  const typed = list.filter((item) => item?.type_code === editDealProductTypeFilter.value)
  // Для подписок даем выбирать товар только после выбора слота.
  if (!isEditRentalSubscriptionMode.value) return typed
  if (!editDeal.value?.slot_type_code) return []
  // После выбора слота показываем весь список подписок выбранного типа.
  return typed
})

// Фильтрует товары в создании сделки по выбранному типу.
const filteredNewDealProductsByType = computed(() => {
  const list = filteredNewDealProducts.value || []
  // В шеринге по умолчанию показываем игры, чтобы список сразу был целевым.
  if (!newDealProductTypeFilter.value) return list
  const typed = list.filter((item) => item?.type_code === newDealProductTypeFilter.value)
  // Для подписок сначала выбираем слот, затем товар.
  if (!isNewRentalSubscriptionMode.value) return typed
  if (!newDeal.value?.slot_type_code) return []
  // После выбора слота показываем весь список подписок выбранного типа.
  return typed
})

// Возвращает список подписок для quick-создания аккаунта, когда свободных сроков нет.
const quickNewAccountSubscriptionProducts = computed(() => {
  const list = Array.isArray(filteredNewDealProducts.value) ? filteredNewDealProducts.value : []
  return list.filter((item) => String(item?.type_code || '').toLowerCase() === 'subscription')
})

// В редактировании используем тот же список подписок для ручного выбора товара в quick-блоке.
const quickEditAccountSubscriptionProducts = computed(() => {
  const list = Array.isArray(filteredEditDealProducts.value) ? filteredEditDealProducts.value : []
  return list.filter((item) => String(item?.type_code || '').toLowerCase() === 'subscription')
})

// Формирует подпись "товар + срок" для единого списка доступных подписок.
function formatAvailableSubscriptionItemLabel(item) {
  const title = String(item?.product_title || '').trim()
  return `${title} ${formatSubscriptionTermLabel(item)}`.trim()
}

// Фильтрует доступные подписки (товар+срок) для режима создания.
const availableSubscriptionItemsNewFiltered = computed(() => {
  const list = Array.isArray(subscriptionAvailableItemsNew.value) ? subscriptionAvailableItemsNew.value : []
  const query = String(newDealProductSearch.value || '').trim().toLowerCase()
  if (!query) return list
  return list.filter((item) => formatAvailableSubscriptionItemLabel(item).toLowerCase().includes(query))
})

// Фильтрует доступные подписки (товар+срок) для режима редактирования.
const availableSubscriptionItemsEditFiltered = computed(() => {
  const list = Array.isArray(subscriptionAvailableItemsEdit.value) ? subscriptionAvailableItemsEdit.value : []
  const query = String(editDealProductSearch.value || '').trim().toLowerCase()
  if (!query) return list
  return list.filter((item) => formatAvailableSubscriptionItemLabel(item).toLowerCase().includes(query))
})

// По выбранному сроку заполняет товар и аккаунт в новой сделке.
function applyNewSubscriptionSelectionByTermId() {
  const termId = Number(newDeal.value?.subscription_term_id || 0)
  if (!termId) {
    newDeal.value.product_id = ''
    newDeal.value.account_id = ''
    return
  }
  const selected = availableSubscriptionItemsNewFiltered.value.find((item) => Number(item?.term_id || 0) === termId)
    || (Array.isArray(subscriptionAvailableItemsNew.value) ? subscriptionAvailableItemsNew.value : []).find((item) => Number(item?.term_id || 0) === termId)
  if (!selected) return
  newDeal.value.product_id = Number(selected.product_id || 0) || ''
  newDeal.value.account_id = Number(selected.account_id || 0) || ''
}

// По выбранному сроку заполняет товар и аккаунт в редактировании сделки.
function applyEditSubscriptionSelectionByTermId() {
  const termId = Number(editDeal.value?.subscription_term_id || 0)
  if (!termId) {
    editDeal.value.product_id = ''
    editDeal.value.account_id = ''
    return
  }
  const selected = availableSubscriptionItemsEditFiltered.value.find((item) => Number(item?.term_id || 0) === termId)
    || (Array.isArray(subscriptionAvailableItemsEdit.value) ? subscriptionAvailableItemsEdit.value : []).find((item) => Number(item?.term_id || 0) === termId)
  if (!selected) return
  editDeal.value.product_id = Number(selected.product_id || 0) || ''
  editDeal.value.account_id = Number(selected.account_id || 0) || ''
}

const showEditDealProductNoMatches = computed(() => {
  // Для подписки показываем пустой список только после выбора слота и загрузки доступных сроков.
  if (isEditRentalSubscriptionMode.value && !editDeal.value?.slot_type_code) return false
  if (isEditRentalSubscriptionMode.value) {
    if (subscriptionAvailableItemsLoadingEdit.value) return false
    return availableSubscriptionItemsEditFiltered.value.length === 0
  }
  return Boolean(editDealProductNoMatches.value)
})

const showNewDealProductNoMatches = computed(() => {
  // Для подписки показываем пустой список только после выбора слота и загрузки доступных сроков.
  if (isNewRentalSubscriptionMode.value && !newDeal.value?.slot_type_code) return false
  if (isNewRentalSubscriptionMode.value) {
    if (subscriptionAvailableItemsLoadingNew.value) return false
    return availableSubscriptionItemsNewFiltered.value.length === 0
  }
  return Boolean(newDealProductNoMatches.value)
})

// Проверяет, заполнены ли ключевые поля быстрого аккаунта для продолжения шеринга.
function collectQuickAccountMissingLabels(state, { subscriptionMode = false, hasSelectedProduct = false } = {}) {
  const missing = []
  if (!String(state?.login_name || '').trim()) missing.push('логин')
  if (!String(state?.domain_code || '').trim()) missing.push('домен')
  if (!String(state?.password || '').trim()) missing.push('пароль аккаунта')
  if (subscriptionMode && !hasSelectedProduct && !Number(state?.subscription_product_id || 0)) missing.push('подписка')
  return missing
}

// Формирует текст для напоминания, чтобы менеджер сразу видел какие поля еще пустые.
function formatQuickAccountMissingText(missing) {
  if (!missing.length) return 'Все ключевые поля заполнены'
  return `Осталось заполнить: ${missing.join(', ')}`
}

const editQuickAccountMissingLabels = computed(() => {
  return collectQuickAccountMissingLabels(quickEditAccount.value, {
    subscriptionMode: isEditRentalSubscriptionMode.value,
    hasSelectedProduct: Boolean(editDeal.value?.product_id),
  })
})

const newQuickAccountMissingLabels = computed(() => {
  return collectQuickAccountMissingLabels(quickNewAccount.value, {
    subscriptionMode: isNewRentalSubscriptionMode.value,
    hasSelectedProduct: Boolean(newDeal.value?.product_id),
  })
})

// Показывает визуальную напоминалку до тех пор, пока в quick-блоке есть незаполненные обязательные поля.
const showEditQuickAccountReminder = computed(() => {
  if (!isEditRentalSubscriptionMode.value) return false
  if (!editQuickAccountOpen.value) return false
  if (!editDeal.value?.slot_type_code || editDeal.value?.account_id) return false
  return editQuickAccountMissingLabels.value.length > 0
})

const showNewQuickAccountReminder = computed(() => {
  if (!isNewRentalSubscriptionMode.value) return false
  if (!newQuickAccountOpen.value) return false
  if (!newDeal.value?.slot_type_code || newDeal.value?.account_id) return false
  return newQuickAccountMissingLabels.value.length > 0
})

const editQuickAccountMissingText = computed(() => formatQuickAccountMissingText(editQuickAccountMissingLabels.value))
const newQuickAccountMissingText = computed(() => formatQuickAccountMissingText(newQuickAccountMissingLabels.value))

// Достает id конфликтной сделки из текста ошибки дубля номера заказа.
function parseConflictDealIdFromError(errorText) {
  const raw = String(errorText || '')
  if (!raw) return 0
  const byDealLabel = raw.match(/Сделка\s*#\s*([0-9]+)/i)
  if (byDealLabel?.[1]) return Number(byDealLabel[1]) || 0
  const byLegacyToken = raw.match(/deal_id\s*=\s*([0-9]+)/i)
  if (byLegacyToken?.[1]) return Number(byLegacyToken[1]) || 0
  return 0
}

const conflictDealIdFromError = computed(() => parseConflictDealIdFromError(dealError.value))

// Открывает конфликтную сделку из текущего списка, чтобы менеджер сразу увидел детали.
function openConflictDealFromError() {
  const dealId = Number(conflictDealIdFromError.value || 0)
  if (!dealId) return
  const rows = Array.isArray(sortedDeals.value) ? sortedDeals.value : []
  const matched = rows.find((item) => Number(item?.deal_id || 0) === dealId)
  if (matched && typeof ctx.startEditDeal === 'function') {
    ctx.startEditDeal(matched)
    return
  }
  showDealWarning.value?.(`Сделка #${dealId} не найдена в текущем списке. Сбросьте фильтры и обновите таблицу.`)
}

// Возвращает пароль аккаунта для блока под выбранным аккаунтом в форме сделки.
function getAccountPasswordById(accountId) {
  if (!accountId) return '—'
  const value = String(getAccountSecret.value?.(accountId) || '').trim()
  return value || '—'
}

// Приводит ключ резерва к формату reserveN для стабильного сравнения.
function normalizeReserveKey(value) {
  const raw = String(value || '').trim().toLowerCase()
  if (!/^reserve\d+$/.test(raw)) return ''
  return `reserve${Number(raw.replace('reserve', ''))}`
}

// Собирает занятые ключи резервов по аккаунту из уже загруженных сделок.
function getUsedReserveKeysByAccount(accountId, currentDealId = null) {
  const targetId = Number(accountId || 0)
  if (!targetId) return new Set()
  const currentId = Number(currentDealId || 0)
  const items = Array.isArray(sortedDeals.value) ? sortedDeals.value : []
  const used = new Set()
  for (const deal of items) {
    if (String(deal?.deal_type_code || '').toLowerCase() !== 'rental') continue
    if (String(deal?.status_code || '').toLowerCase() === 'cancelled') continue
    if (Number(deal?.account_id || 0) !== targetId) continue
    if (currentId && Number(deal?.deal_id || 0) === currentId) continue
    const normalizedKey = normalizeReserveKey(deal?.reserve_key)
    if (normalizedKey) used.add(normalizedKey)
  }
  return used
}

// Возвращает список резервов аккаунта и признак, занят ли каждый резерв.
function getAccountReserveEntriesForDeal(accountId, currentDealId = null) {
  const entries = Array.isArray(getReserveSecretEntries.value?.(accountId))
    ? getReserveSecretEntries.value(accountId)
    : []
  const used = getUsedReserveKeysByAccount(accountId, currentDealId)
  return entries.map((item) => {
    const normalizedKey = normalizeReserveKey(item?.key)
    return {
      key: normalizedKey,
      value: String(item?.value || '').trim(),
      used: normalizedKey ? used.has(normalizedKey) : false,
    }
  })
}

// Выбирает первый свободный резерв из уже загруженных данных.
function pickFirstFreeReserveKey(accountId, currentDealId = null) {
  const entries = getAccountReserveEntriesForDeal(accountId, currentDealId)
  const free = entries.find((item) => item.key && !item.used)
  return free?.key || ''
}

// Возвращает строку для отображения резерва в блоке выбранного аккаунта.
function getDealReserveLabel(accountId, reserveKey, currentDealId = null, options = {}) {
  if (!accountId) return '—'
  const allowFallback = options?.allowFallback !== false
  const emptyLabel = options?.emptyLabel || '—'
  const normalizedKey = normalizeReserveKey(reserveKey)
  const entries = getAccountReserveEntriesForDeal(accountId, currentDealId)
  if (!entries.length) return emptyLabel
  // В просмотре показываем только фактический reserve_key; fallback включаем только в создании/редактировании.
  if (!normalizedKey && !allowFallback) return emptyLabel
  const selectedKey = normalizedKey || pickFirstFreeReserveKey(accountId, currentDealId)
  if (!selectedKey) return emptyLabel
  const selected = entries.find((item) => item.key === selectedKey)
  if (!selected) return emptyLabel
  if (!selected?.value) return emptyLabel
  return selected.used ? `${selected.value} (использован)` : selected.value
}

// Сравнивает id как число, чтобы не терять совпадение при строковом account_id из API.
function isSameAccountId(leftId, rightId) {
  const leftNum = Number(leftId)
  const rightNum = Number(rightId)
  if (Number.isFinite(leftNum) && Number.isFinite(rightNum)) {
    return leftNum === rightNum
  }
  return String(leftId || '').trim() === String(rightId || '').trim()
}

// Проверяет, есть ли в справочнике подпись для выбранного аккаунта.
function hasAccountLabelForDetails(accountId) {
  if (!accountId) return false
  const list = Array.isArray(accountsAll.value) ? accountsAll.value : []
  return list.some((item) => isSameAccountId(item?.account_id, accountId))
}

// Проверяет, догружены ли секреты выбранного аккаунта в локальный кеш.
function hasAccountSecretsForDetails(accountId) {
  const targetId = Number(accountId || 0)
  if (!targetId) return false
  const cache = accountSecrets.value || {}
  return Object.prototype.hasOwnProperty.call(cache, targetId)
}

// Возвращает выбранный account_id для нужной формы сделки.
function getDealAccountIdByTarget(target) {
  if (target === 'edit') return Number(editDeal.value?.account_id || 0)
  return Number(newDeal.value?.account_id || 0)
}

// Проверяет, что подпись аккаунта не свалилась в сырой account_id.
function hasHumanDealAccountLabel(accountId, label) {
  const targetId = String(accountId || '').trim()
  const targetLabel = String(label || '').trim()
  if (!targetId || !targetLabel) return false
  return targetLabel !== targetId
}

// Говорит, нужно ли показывать лоадер в блоке "Данные аккаунта".
function shouldShowDealAccountDetailsLoader(target) {
  const accountId = getDealAccountIdByTarget(target)
  if (!accountId) return false
  const loading = target === 'edit' ? editDealAccountDetailsLoading.value : newDealAccountDetailsLoading.value
  if (loading) return true
  return !hasAccountLabelForDetails(accountId) || !hasAccountSecretsForDetails(accountId)
}

// Возвращает логин аккаунта для полей сделки без fallback к сырому id.
function getDealAccountLoginLabel(target) {
  const accountId = getDealAccountIdByTarget(target)
  if (!accountId) return '—'
  if (shouldShowDealAccountDetailsLoader(target)) return '—'
  const label = String(getAccountLabelById.value?.(accountId) || '').trim()
  return hasHumanDealAccountLabel(accountId, label) ? label : '—'
}

// Догружает справочник и секреты для выбранного аккаунта перед показом блока с деталями.
async function ensureDealAccountDetailsLoaded(target) {
  const accountId = getDealAccountIdByTarget(target)
  if (!accountId) return
  const loadingRef = target === 'edit' ? editDealAccountDetailsLoading : newDealAccountDetailsLoading
  const hasLabel = hasAccountLabelForDetails(accountId)
  const hasSecrets = hasAccountSecretsForDetails(accountId)
  if (hasLabel && hasSecrets) return
  loadingRef.value = true
  try {
    const tasks = []
    if (!hasLabel && typeof loadAccountsAll.value === 'function') {
      // Для карточки сделки подгружаем только подпись нужного аккаунта, без полного /accounts.
      tasks.push(loadAccountsAll.value([accountId]))
    }
    if (!hasSecrets && typeof ensureAccountSecretsLoaded.value === 'function') {
      tasks.push(ensureAccountSecretsLoaded.value(accountId))
    }
    if (tasks.length) await Promise.allSettled(tasks)
  } finally {
    loadingRef.value = false
  }
}

// Форматирует подпись срока подписки для селекта и режима просмотра.
function formatSubscriptionTermLabel(term) {
  if (!term) return '— не выбрано —'
  const rawDate = String(term.valid_until || '').trim()
  if (!rawDate) return 'до —'
  const parsed = new Date(rawDate)
  if (Number.isNaN(parsed.getTime())) return `до ${rawDate}`
  const day = String(parsed.getDate()).padStart(2, '0')
  const month = String(parsed.getMonth() + 1).padStart(2, '0')
  const year = String(parsed.getFullYear())
  return `до ${day}.${month}.${year}`
}

// Оставляет в селектах только свободные сроки подписки.
function isFreeSubscriptionTerm(term) {
  return !(term?.occupied || term?.is_occupied)
}

const editSubscriptionTermOptions = computed(() => {
  const list = Array.isArray(subscriptionTermsEdit.value) ? subscriptionTermsEdit.value : []
  return list.filter(isFreeSubscriptionTerm)
})

const newSubscriptionTermOptions = computed(() => {
  const list = Array.isArray(subscriptionTermsNew.value) ? subscriptionTermsNew.value : []
  return list.filter(isFreeSubscriptionTerm)
})

function getSelectedEditSubscriptionTermLabel() {
  const termId = Number(editDeal.value?.subscription_term_id || 0)
  if (!termId) return '— не выбрано —'
  const selected = editSubscriptionTermOptions.value.find((item) => Number(item?.term_id || 0) === termId)
  return formatSubscriptionTermLabel(selected)
}

// Собирает подпись "товар + срок" в одном поле, когда выбран срок подписки.
function getDealProductDisplayLabel(target) {
  const isEdit = target === 'edit'
  const deal = isEdit ? editDeal.value : newDeal.value
  const productId = Number(deal?.product_id || 0)
  if (!productId) return '—'
  let productLabel = getProductLabelById.value(productId)
  const termId = Number(deal?.subscription_term_id || 0)
  const subscriptionMode = isEdit ? isEditRentalSubscriptionMode.value : isNewRentalSubscriptionMode.value
  // В просмотре сделки показываем срок всегда по факту сохраненного term_id, даже если фильтр типа еще не синхронизировался.
  const showTermInView = isEdit
    && dealEditMode.value === 'view'
    && String(deal?.deal_type_code || '').toLowerCase() === 'rental'
    && termId > 0
  if ((!subscriptionMode && !showTermInView) || !termId) return productLabel
  const allTerms = isEdit
    ? (Array.isArray(subscriptionTermsEdit.value) ? subscriptionTermsEdit.value : [])
    : (Array.isArray(subscriptionTermsNew.value) ? subscriptionTermsNew.value : [])
  let selectedTerm = allTerms.find((item) => Number(item?.term_id || 0) === termId)
  if (!selectedTerm) {
    const available = isEdit
      ? (Array.isArray(subscriptionAvailableItemsEdit.value) ? subscriptionAvailableItemsEdit.value : [])
      : (Array.isArray(subscriptionAvailableItemsNew.value) ? subscriptionAvailableItemsNew.value : [])
    selectedTerm = available.find((item) => Number(item?.term_id || 0) === termId)
  }
  // Если справочник товаров еще не догрузился, берем имя подписки из выбранного срока, чтобы не показывать product_id.
  if (String(productLabel || '').trim() === String(productId) && selectedTerm?.product_title) {
    productLabel = String(selectedTerm.product_title).trim()
  }
  const termLabel = formatSubscriptionTermLabel(selectedTerm)
  return `${productLabel} ${termLabel}`.trim()
}

// Возвращает список слотов для формы; у подписки до выбора товара даем полный список.
function getSlotTypeOptionsForDeal(target) {
  const isEdit = target === 'edit'
  const subscriptionMode = isEdit ? isEditRentalSubscriptionMode.value : isNewRentalSubscriptionMode.value
  const productId = isEdit ? editDeal.value?.product_id : newDeal.value?.product_id
  const selectedSlotTypeCode = String(isEdit ? editDeal.value?.slot_type_code || '' : newDeal.value?.slot_type_code || '').trim()
  if (subscriptionMode && !productId) {
    return (slotTypes.value || []).map((item) => ({
      code: item.code,
      name: item.name,
      supported: true,
    }))
  }
  const options = getDealSlotTypeOptions.value(target)
  // Скрываем неподдерживаемые слоты из выпадающего списка, чтобы не оставлять "пустые" строки.
  return options.filter((item) => item?.supported !== false || item?.code === selectedSlotTypeCode)
}

// Сбрасывает фильтр типа при новом открытии редактирования, чтобы не прятать товары.
watch(() => editDeal.value?.open, (isOpen) => {
  if (!isOpen) return
  // При открытии редактирования сбрасываем состояние раскрытых блоков быстрого создания.
  const currentProductTypeCode = getSelectedEditDealProductTypeCode()
  editDealProductTypeFilter.value = currentProductTypeCode === 'subscription' ? 'subscription' : 'game'
  editQuickProductOpen.value = false
  editQuickAccountOpen.value = false
  editQuickSubscriptionTermOpen.value = false
  forceEditDuplicateMode.value = false
})

watch(
  () => [editDeal.value?.open, editDeal.value?.product_id, filteredEditDealProducts.value?.length],
  () => {
    // Повторно синхронизируем тип после загрузки/обновления списка товаров.
    syncEditProductTypeFilterFromSelectedProduct()
  }
)

watch(
  () => dealEditMode.value,
  (mode) => {
    if (mode !== 'edit') return
    // При входе в редактирование всегда выравниваем фильтр с типом выбранного товара.
    syncEditProductTypeFilterFromSelectedProduct()
  }
)

// При открытии создания шеринга возвращает фильтр к "Игра", чтобы форма была предсказуемой.
watch(() => newDeal.value?.deal_type_code, (dealTypeCode) => {
  if (dealTypeCode !== 'rental') return
  // Для новой шеринговой сделки открываем форму в базовом состоянии с закрытым quick-create.
  newDealProductTypeFilter.value = 'game'
  newQuickProductOpen.value = false
  newQuickAccountOpen.value = false
  newQuickSubscriptionTermOpen.value = false
  forceNewDuplicateMode.value = false
})

watch(() => editDealProductTypeFilter.value, (typeCode, prev) => {
  if (!editDeal.value?.open || editDeal.value?.deal_type_code !== 'rental') return
  // В режиме просмотра фильтр обновляется автоматически, без сброса текущего выбора сделки.
  if (dealEditMode.value !== 'edit') return
  if (typeCode === prev) return
  // Если фильтр уже совпадает с типом выбранного товара, значит это автосинхронизация — ничего не сбрасываем.
  const selectedTypeCode = getSelectedEditDealProductTypeCode()
  if (selectedTypeCode && selectedTypeCode === typeCode) return
  // При переключении в подписки очищаем связку товар/аккаунт: выбор снова идет от слота.
  if (typeCode === 'subscription') {
    editDeal.value.product_id = ''
    editDeal.value.account_id = ''
    editDealProductSearch.value = ''
  }
})

watch(() => newDealProductTypeFilter.value, (typeCode, prev) => {
  if (newDeal.value?.deal_type_code !== 'rental') return
  if (typeCode === prev) return
  // Для подписок сбрасываем товар и аккаунт, чтобы начать выбор с типа слота.
  if (typeCode === 'subscription') {
    newDeal.value.product_id = ''
    newDeal.value.account_id = ''
    newDealProductSearch.value = ''
  }
})

watch(() => newDeal.value?.account_id, (accountId) => {
  if (!accountId) {
    newDealAccountDetailsLoading.value = false
    return
  }
  // Для блока "Данные аккаунта" заранее догружаем логин и секреты выбранного аккаунта.
  void ensureDealAccountDetailsLoaded('new')
}, { immediate: true })

watch(() => editDeal.value?.account_id, (accountId) => {
  if (!accountId) {
    editDealAccountDetailsLoading.value = false
    return
  }
  // В редактировании применяем ту же догрузку, чтобы в форме не мелькал сырой account_id.
  void ensureDealAccountDetailsLoaded('edit')
}, { immediate: true })

watch(() => newDeal.value?.product_id, () => {
  // При смене товара выходим из принудительного режима дубля: это уже другой сценарий.
  forceNewDuplicateMode.value = false
})

watch(() => editDeal.value?.product_id, () => {
  // В редактировании ведем себя так же: режим дубля пересобирается на новый товар.
  forceEditDuplicateMode.value = false
})

watch(() => newDeal.value?.slot_type_code, () => {
  // Смена слота обнуляет принудительный режим дубля.
  forceNewDuplicateMode.value = false
})

watch(() => editDeal.value?.slot_type_code, () => {
  // Для edit принудительный режим сбрасываем при смене метода.
  forceEditDuplicateMode.value = false
})

watch(() => editDeal.value?.slot_type_code, (slotTypeCode, prev) => {
  if (!editDeal.value?.open || !isEditRentalSubscriptionMode.value) return
  if (slotTypeCode === prev) return
  // Смена слота в подписках требует заново выбрать товар и аккаунт.
  editDeal.value.product_id = ''
  editDeal.value.subscription_term_id = ''
  editDeal.value.account_id = ''
  editDealProductSearch.value = ''
  editQuickSubscriptionTermOpen.value = false
})

watch(() => newDeal.value?.slot_type_code, (slotTypeCode, prev) => {
  if (!isNewRentalSubscriptionMode.value) return
  if (slotTypeCode === prev) return
  // В создании подписки смена слота также пересобирает выбор товара.
  newDeal.value.product_id = ''
  newDeal.value.subscription_term_id = ''
  newDeal.value.account_id = ''
  newDealProductSearch.value = ''
  newQuickSubscriptionTermOpen.value = false
})

watch(() => editDeal.value?.subscription_term_id, (termId) => {
  if (!editDeal.value?.open || !isEditRentalSubscriptionMode.value) return
  if (!termId) return
  // При выборе срока автоматически подставляем товар и аккаунт из плоского списка доступных подписок.
  applyEditSubscriptionSelectionByTermId()
  const selected = editSubscriptionTermOptions.value.find((item) => Number(item?.term_id || 0) === Number(termId))
    || availableSubscriptionItemsEditFiltered.value.find((item) => Number(item?.term_id || 0) === Number(termId))
  if (selected?.account_id) editDeal.value.account_id = Number(selected.account_id)
})

watch(() => newDeal.value?.subscription_term_id, (termId) => {
  if (!isNewRentalSubscriptionMode.value) return
  if (!termId) return
  // Для новой сделки по сроку сразу синхронизируем товар и аккаунт.
  applyNewSubscriptionSelectionByTermId()
  const selected = newSubscriptionTermOptions.value.find((item) => Number(item?.term_id || 0) === Number(termId))
    || availableSubscriptionItemsNewFiltered.value.find((item) => Number(item?.term_id || 0) === Number(termId))
  if (selected?.account_id) newDeal.value.account_id = Number(selected.account_id)
})

watch(() => newDeal.value?.account_id, (accountId) => {
  if (newDeal.value?.deal_type_code !== 'rental') return
  if (!accountId) {
    newDeal.value.reserve_key = ''
    return
  }
  // При выборе аккаунта подставляем первый свободный резерв, если он доступен.
  const reserveEntries = getAccountReserveEntriesForDeal(accountId)
  const reserveKey = pickFirstFreeReserveKey(accountId)
  newDeal.value.reserve_key = reserveKey
  // Предупреждение показываем только когда список резервов уже загружен и действительно весь занят.
  if (!reserveKey && reserveEntries.length > 0 && typeof showDealWarning.value === 'function') {
    showDealWarning.value('У выбранного аккаунта нет доступных резервов')
  }
})

watch(() => editDeal.value?.account_id, (accountId) => {
  if (!editDeal.value?.open || editDeal.value?.deal_type_code !== 'rental' || dealEditMode.value !== 'edit') return
  if (!accountId) {
    editDeal.value.reserve_key = ''
    return
  }
  const currentKey = normalizeReserveKey(editDeal.value?.reserve_key)
  if (currentKey) return
  // В редактировании подбираем резерв только когда в сделке еще нет ключа.
  editDeal.value.reserve_key = pickFirstFreeReserveKey(accountId, editDeal.value?.deal_id)
})

watch(() => dealEditMode.value, (mode) => {
  if (mode !== 'edit') return
  if (!editDeal.value?.open || editDeal.value?.deal_type_code !== 'rental') return
  if (!editDeal.value?.account_id) return
  if (normalizeReserveKey(editDeal.value?.reserve_key)) return
  // При входе в редактирование импортной сделки подбираем свободный резерв, но в режиме просмотра ничего не подставляем.
  editDeal.value.reserve_key = pickFirstFreeReserveKey(editDeal.value.account_id, editDeal.value?.deal_id)
})

watch(() => editDeal.value?.product_link, (value) => {
  const nextSerialized = serializeSaleProductLinks(parseSaleProductLinks(value))
  if (nextSerialized === serializeSaleProductLinks(editSaleProductLinks.value)) return
  // Синхронизируем список ссылок при открытии/переключении сделки.
  editSaleProductLinks.value = parseSaleProductLinks(value)
}, { immediate: true })

watch(() => newDeal.value?.product_link, (value) => {
  const nextSerialized = serializeSaleProductLinks(parseSaleProductLinks(value))
  if (nextSerialized === serializeSaleProductLinks(newSaleProductLinks.value)) return
  // Держим форму создания в актуальном состоянии после сбросов и переключений типа сделки.
  newSaleProductLinks.value = parseSaleProductLinks(value)
}, { immediate: true })

const isEditDealPendingFlow = computed(() => {
  // Для pending/draft скрываем возврат в форме: возврат проводится только отдельной кнопкой из таблицы.
  const status = String(editDeal.value?.flow_status_code || '').trim().toLowerCase()
  return status === 'pending' || status === 'draft'
})

const canEditRefundFlag = computed(() => {
  // Возврат в форме меняем только у завершенных сделок для admin/owner.
  const status = String(editDeal.value?.flow_status_code || '').trim().toLowerCase()
  return status === 'completed' && Boolean(allowCompletedDealEdit?.value)
})

const canEditSystemDates = computed(() => {
  // Даты создания/завершения даем редактировать admin/owner независимо от статуса.
  return Boolean(allowCompletedDealEdit?.value)
})

const refundEditBlockedReason = computed(() => {
  // Подсказываем причину блокировки, чтобы было понятно почему чекбокс недоступен.
  return canEditRefundFlag.value ? '' : 'Признак можно менять только у завершенной сделки (для admin/owner)'
})

const editFlowStatusOptions = computed(() => {
  // Для черновика не даем прямой переход в "Завершен" из формы редактирования.
  const currentStatus = String(editDeal.value?.flow_status_code || '').trim().toLowerCase()
  const list = Array.isArray(dealFlowStatusOptions.value) ? dealFlowStatusOptions.value : []
  if (currentStatus !== 'draft') return list
  return list.filter((item) => String(item?.code || '').trim().toLowerCase() !== 'completed')
})

// Возвращает true, если значение пустое или служебное и его не нужно копировать.
function isCopyPlaceholderValue(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return !normalized || normalized === '—' || normalized === '-' || normalized === '— не назначен' || normalized === '— не выбрано —'
}

// Универсально копирует текст в буфер с fallback для старых браузеров.
async function copyTextToClipboard(value) {
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
  document.execCommand('copy')
  document.body.removeChild(tempInput)
  return true
}

// Формирует единый ключ поля, чтобы показывать "Скопировано" только на нужной кнопке.
function getSharingFieldCopyKey(target, field) {
  return `${target}:${field}`
}

// Возвращает подпись иконки копирования для полей шеринга.
function getSharingFieldCopyLabel(target, field) {
  const copyKey = getSharingFieldCopyKey(target, field)
  if (copiedSharingFieldKey.value === copyKey) return 'Скопировано'
  if (field === 'password') return 'Копировать пароль'
  if (field === 'reserve') return 'Копировать резерв'
  return 'Копировать логин'
}

// Возвращает реальное значение поля шеринга для копирования без служебных подплейсхолдеров.
function getSharingFieldCopyValue(target, field) {
  const isEditTarget = target === 'edit'
  const deal = isEditTarget ? editDeal.value : newDeal.value
  const accountId = Number(deal?.account_id || 0)
  if (!accountId) return ''
  if (field === 'password') {
    const password = String(getAccountSecret.value?.(accountId) || '').trim()
    return isCopyPlaceholderValue(password) ? '' : password
  }
  if (field === 'reserve') {
    const reserveLabel = isEditTarget
      ? getDealReserveLabel(accountId, deal?.reserve_key, deal?.deal_id, { allowFallback: dealEditMode.value === 'edit', emptyLabel: '— не назначен' })
      : getDealReserveLabel(accountId, deal?.reserve_key, null, { allowFallback: true })
    const reserveValue = String(reserveLabel || '').replace(/\s+\(использован\)\s*$/i, '').trim()
    return isCopyPlaceholderValue(reserveValue) ? '' : reserveValue
  }
  const login = String(getDealAccountLoginLabel(target) || '').trim()
  return isCopyPlaceholderValue(login) ? '' : login
}

// Копирует выбранное поле шеринга и кратко показывает успешный статус на кнопке.
async function copySharingField(target, field) {
  const value = getSharingFieldCopyValue(target, field)
  if (!value) return
  try {
    await copyTextToClipboard(value)
    copiedSharingFieldKey.value = getSharingFieldCopyKey(target, field)
    if (copiedSharingFieldTimerId) window.clearTimeout(copiedSharingFieldTimerId)
    copiedSharingFieldTimerId = window.setTimeout(() => {
      copiedSharingFieldKey.value = ''
      copiedSharingFieldTimerId = 0
    }, 1400)
  } catch {
    showDealWarning.value?.('Не удалось скопировать значение')
  }
}

// Преобразует список ссылок в чистый вид: убирает пробелы по краям и пустые строки.
function serializeSaleProductLinks(list) {
  const source = Array.isArray(list) ? list : []
  const normalized = source
    .map((item) => String(item || '').trim())
    .filter((item) => !!item)
  return normalized.join('\n')
}

// Разбирает строку ссылок из БД/формы в массив для многострочного UI.
function parseSaleProductLinks(value) {
  const normalized = String(value || '')
    .split(/\r?\n/g)
    .map((item) => String(item || '').trim())
    .filter((item) => !!item)
  return normalized
}

// Возвращает ссылочный список нужной формы (создание или редактирование).
function getSaleProductLinksRef(target) {
  return target === 'edit' ? editSaleProductLinks : newSaleProductLinks
}

// Возвращает список ссылок для текущей формы.
function getSaleProductLinks(target) {
  return getSaleProductLinksRef(target).value
}

// Возвращает ссылку по индексу в готовом для копирования виде.
function getSaleProductLinkValue(target, index) {
  const links = getSaleProductLinks(target)
  if (!Array.isArray(links)) return ''
  return String(links[index] || '').trim()
}

// Синхронизирует массив ссылок обратно в одно поле product_link для API.
function syncSaleProductLinksToDeal(target) {
  const serialized = serializeSaleProductLinks(getSaleProductLinks(target))
  if (target === 'edit') {
    editDeal.value.product_link = serialized
    return
  }
  newDeal.value.product_link = serialized
}

// Обновляет конкретную строку ссылки в форме.
function setSaleProductLinkValue(target, index, value) {
  const linksRef = getSaleProductLinksRef(target)
  if (!Array.isArray(linksRef.value) || index < 0 || index >= linksRef.value.length) return
  linksRef.value[index] = String(value || '')
  syncSaleProductLinksToDeal(target)
}

// Добавляет новую пустую строку ссылки для продажи.
function addSaleProductLink(target) {
  const linksRef = getSaleProductLinksRef(target)
  linksRef.value.push('')
}

// Проверяет, можно ли удалить строку ссылки.
function canRemoveSaleProductLink(target) {
  return getSaleProductLinks(target).length > 0
}

// Удаляет строку ссылки и синхронизирует результат в поле сделки.
function removeSaleProductLink(target, index) {
  const linksRef = getSaleProductLinksRef(target)
  if (!canRemoveSaleProductLink(target)) return
  linksRef.value = linksRef.value.filter((_, rowIndex) => rowIndex !== index)
  syncSaleProductLinksToDeal(target)
}

// Формирует ключ для статуса "Скопировано" у конкретной строки ссылки.
function getSaleLinkCopyKey(target, index = 0) {
  return `${target}:${index}`
}

// Возвращает подпись для иконки копирования ссылки с учетом строки и короткого статуса.
function getSaleLinkCopyLabel(target, index = 0) {
  const copyKey = getSaleLinkCopyKey(target, index)
  return copiedSaleLinkKey.value === copyKey ? 'Скопировано' : 'Копировать ссылку'
}

// Копирует выбранную строку ссылки товара в буфер обмена.
async function copySaleProductLink(target, index = 0) {
  const value = getSaleProductLinkValue(target, index)
  if (!value) return
  try {
    await copyTextToClipboard(value)
    copiedSaleLinkKey.value = getSaleLinkCopyKey(target, index)
    if (copiedSaleLinkTimerId) window.clearTimeout(copiedSaleLinkTimerId)
    copiedSaleLinkTimerId = window.setTimeout(() => {
      copiedSaleLinkKey.value = ''
      copiedSaleLinkTimerId = 0
    }, 1400)
  } catch {
    showDealWarning.value?.('Не удалось скопировать ссылку')
  }
}
</script>
