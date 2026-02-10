<template>
                    <div v-if="editDeal.open" class="form deal-form" :class="{ 'deal-form--sale': editDeal.deal_type_code === 'sale' }">
                      <div class="deal-form__col deal-form__col--left">
                        <label
                          v-if="editDeal.deal_type_code === 'rental' && (dealEditMode === 'view' || dealAccountsForGameLoading || !editDeal.game_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length)"
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
                            :disabled="!editDeal.game_id || dealSlotAvailabilityLoadingEdit"
                          >
                            <option value="">{{ !editDeal.game_id ? 'Сначала выберите игру' : (dealSlotAvailabilityLoadingEdit ? '(формируется список)' : '— не выбрано —') }}</option>
                            <option
                              v-for="st in getDealSlotTypeOptions('edit')"
                              :key="st.code"
                              :value="st.code"
                              :disabled="!st.supported"
                            >
                              {{ getDealSlotTypeLabel(st) }}
                            </option>
                          </select>
                        </label>
                        <label v-if="editDeal.deal_type_code === 'rental'" class="field">
                          <span
                            v-if="dealEditMode === 'view' || dealAccountsForGameLoading || !editDeal.game_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length || editDeal.account_id"
                            class="label"
                          >
                            Аккаунт
                          </span>
                          <input
                            v-if="dealEditMode === 'view'"
                            class="input"
                            :value="getAccountLabelById(editDeal.account_id)"
                            readonly
                          />
                          <select
                            v-else-if="dealAccountsForGameLoading || !editDeal.game_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForEdit.length || editDeal.account_id"
                            v-model.number="editDeal.account_id"
                            class="input input--select"
                            :disabled="!editDeal.game_id || !editDeal.slot_type_code || isDealSlotTypeUnsupported('edit') || dealAccountsForGameLoading"
                          >
                            <option value="">
                              {{ !editDeal.game_id ? 'Сначала выберите игру' : (!editDeal.slot_type_code ? 'Сначала выберите слот' : (dealAccountsForGameLoading ? '(формируется список)' : '— не выбрано —')) }}
                            </option>
                            <option v-for="a in dealAccountsForEdit" :key="a.account_id" :value="a.account_id">
                              {{ a.login_full || a.account_id }}
                            </option>
                          </select>
                          <div
                            v-if="dealEditMode !== 'view' && !dealAccountsForGameLoading && editDeal.game_id && editDeal.slot_type_code && !editDeal.account_id && !isDealSlotTypeUnsupported('edit') && !hasFreeDealSlots('edit')"
                            class="quick-create"
                          >
                            <div class="quick-create__title">
                              {{ hasAnyGameAssignmentsEdit ? 'Нет свободных слотов — можно снять занятый' : 'Нет аккаунтов с игрой' }}
                            </div>
                            <div v-if="hasAnyGameAssignmentsEdit && dealGameAssignmentsLoadingEdit" class="loader-wrap loader-wrap--compact">
                              <div class="newtons-cradle" aria-label="Loading" role="img">
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                              </div>
                            </div>
                            <div v-else-if="hasAnyGameAssignmentsEdit && dealGameAssignmentsForSelectedSlotEdit.length" class="quick-create__table-scroll">
                              <table class="table table--compact table--dense">
                                <thead>
                                  <tr>
                                    <th>Аккаунт</th>
                                    <th>Слот</th>
                                    <th>Покупатель</th>
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
                            </div>
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
                            <div class="newtons-cradle" aria-label="Loading" role="img">
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                            </div>
                          </div>
                          <table v-else-if="dealAccountAssignmentsEdit.filter((s) => !s.released_at).length" class="table table--compact table--dense">
                            <thead>
                              <tr>
                                <th>Слот</th>
                                <th>Игра</th>
                                <th>Покупатель</th>
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
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-status-row">
                          <label class="field">
                            <span class="label">Дата создания</span>
                            <input class="input" :value="formatDateTimeMinutes(editDeal.created_at)" readonly />
                          </label>
                          <label class="field">
                            <span class="label">Дата завершения</span>
                            <input
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
                              <option v-for="s in dealFlowStatusOptions" :key="s.code" :value="s.code">
                                {{ s.name }}
                              </option>
                            </select>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-top">
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
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-auth">
                          <label class="field">
                            <span class="label">Покупатель</span>
                            <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                          </label>
                          <label class="field">
                            <span class="label">Логин</span>
                            <input v-model.trim="editDeal.login" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                          </label>
                          <label class="field">
                            <span class="label">Пароль</span>
                            <input v-model.trim="editDeal.password" class="input" placeholder="-" :readonly="dealEditMode === 'view'"/>
                          </label>
                        </div>
                        <div v-if="editDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-costs">
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
                          <label class="field">
                            <span class="label">Закуп</span>
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
                        <label v-else class="field">
                          <span class="label">Покупатель</span>
                          <input v-model.trim="editDeal.customer_nickname" class="input" placeholder="-" :readonly="dealEditMode === 'view'" />
                        </label>
                        <label v-if="editDeal.deal_type_code !== 'sale'" class="field">
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
                        <label v-if="editDeal.deal_type_code === 'rental'" class="field">
                          <span class="label">Дата</span>
                          <input
                            v-model="editDeal.purchase_at"
                            class="input"
                            type="date"
                            :max="maxDate"
                            :readonly="dealEditMode === 'view'"
                          />
                        </label>
                        <label v-if="editDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Ссылка на игру</span>
                          <input
                            v-model.trim="editDeal.game_link"
                            class="input"
                            placeholder="https://..."
                            :readonly="dealEditMode === 'view'"
                          />
                        </label>
                        <label v-if="editDeal.deal_type_code !== 'sale'" class="field">
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
                        <label v-if="editDeal.deal_type_code !== 'sale'" class="field">
                          <span class="label">Статус</span>
                          <input
                            v-if="dealEditMode === 'view'"
                            class="input"
                            :value="getFlowStatusLabel(editDeal.flow_status_code)"
                            readonly
                          />
                          <select v-else v-model="editDeal.flow_status_code" class="input input--select">
                            <option value="">— не выбрано —</option>
                            <option v-for="s in dealFlowStatusOptions" :key="s.code" :value="s.code">
                              {{ s.name }}
                            </option>
                          </select>
                        </label>
                        <label v-if="editDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Комментарий</span>
                          <textarea
                            v-model.trim="editDeal.notes"
                            class="input input--textarea input--textarea--compact"
                            :rows="getCompactNotesRows(editDeal.notes)"
                            :readonly="dealEditMode === 'view'"
                          />
                        </label>
                      </div>
                      <div v-if="editDeal.deal_type_code !== 'sale'" class="deal-form__col deal-form__col--right">
                        <label
                          v-if="editDeal.deal_type_code === 'rental'"
                          class="field field--game"
                          :class="{ 'field--game-selected': Boolean(editDeal.game_id) && !editDealGameSearch }"
                        >
                          <span class="label">Игра</span>
                          <input
                            v-if="dealEditMode === 'view'"
                            class="input"
                            :value="getGameLabelById(editDeal.game_id)"
                            readonly
                          />
                          <div v-else-if="!editDeal.game_id" class="input input--compact input--search input--search-row">
                            <input
                              v-model.trim="editDealGameSearch"
                              class="input--search-field"
                              placeholder="поиск игры"
                              @input="onEditDealGameSearch"
                            />
                          </div>
                          <div
                            v-if="dealEditMode !== 'view'"
                            class="input--select-wrap"
                            :class="{ 'input--select-wrap--selected': Boolean(editDeal.game_id) && !editDealGameSearch }"
                          >
                            <input
                              v-if="editDeal.game_id && !editDealGameSearch"
                              class="input"
                              :value="getGameLabelById(editDeal.game_id)"
                              readonly
                            />
                            <select
                              v-else-if="!editDealGameNoMatches"
                              v-model.number="editDeal.game_id"
                              :class="[
                                'input input--select input--list',
                                { 'input--list--compact': editDealGameNoMatches || (editDeal.game_id && !editDealGameSearch) }
                              ]"
                              :size="editDealGameNoMatches ? 1 : 8"
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
                              @click="clearEditDealGame"
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M6 6l12 12M18 6l-12 12" />
                              </svg>
                            </button>
                          </div>
                          <div
                            v-if="dealEditMode !== 'view' && editDealGameNoMatches"
                            class="quick-create quick-create--game-empty"
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
                            :readonly="dealEditMode === 'view'"
                          />
                        </label>
                      </div>
                      <div class="deal-form__full">
                        <p v-if="dealError" class="bad">{{ dealError }}</p>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div v-if="dealEditMode === 'edit'" class="toolbar-actions"></div>
                      </div>
                    </div>
                    <div v-else class="form deal-form" :class="{ 'deal-form--sale': newDeal.deal_type_code === 'sale' || newDeal.deal_type_code === 'rental' }">
                      <div class="deal-form__col deal-form__col--left">
                        <div
                          class="deal-form__triple"
                          :class="{
                            'deal-form__triple--sale-top': newDeal.deal_type_code === 'sale',
                            'deal-form__triple--rental-top': newDeal.deal_type_code === 'rental',
                          }"
                        >
                          <label class="field">
                            <span class="label">Источник</span>
                            <select v-model.number="newDeal.source_id" class="input input--select">
                              <option value="">— не выбрано —</option>
                              <option v-for="s in sourcesByCode" :key="s.source_id" :value="s.source_id">
                                {{ s.name }} ({{ s.code }})
                              </option>
                            </select>
                          </label>
                          <label v-if="newDeal.deal_type_code === 'sale' || newDeal.deal_type_code === 'rental'" class="field">
                            <span class="label">{{ newDeal.deal_type_code === 'rental' ? 'Номер заявки' : 'Номер заказа' }}</span>
                            <input v-model.trim="newDeal.order_number" class="input" placeholder="-" />
                          </label>
                          <label v-if="newDeal.deal_type_code !== 'sale'" class="field">
                            <span class="label">Покупатель</span>
                            <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="-" />
                          </label>
                          <label v-if="newDeal.deal_type_code === 'sale'" class="field">
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
                          <label v-if="newDeal.deal_type_code === 'rental'" class="field">
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
                        <label
                          v-if="newDeal.deal_type_code === 'rental'"
                          class="field field--game"
                          :class="{ 'field--game-selected': Boolean(newDeal.game_id) && !newDealGameSearch }"
                        >
                          <span class="label">Игра</span>
                          <div v-if="!newDeal.game_id" class="input input--compact input--search input--search-row">
                            <input
                              v-model.trim="newDealGameSearch"
                              class="input--search-field"
                              placeholder="поиск игры"
                              @input="onNewDealGameSearch"
                            />
                          </div>
                          <div class="input--select-wrap" :class="{ 'input--select-wrap--selected': Boolean(newDeal.game_id) && !newDealGameSearch }">
                            <input
                              v-if="newDeal.game_id && !newDealGameSearch"
                              class="input"
                              :value="getGameLabelById(newDeal.game_id)"
                              readonly
                            />
                            <select
                              v-else-if="!newDealGameNoMatches"
                              v-model.number="newDeal.game_id"
                              :class="[
                                'input input--select input--list input--list--game-short',
                                { 'input--list--compact': newDealGameNoMatches || (newDeal.game_id && !newDealGameSearch) }
                              ]"
                              :size="newDealGameNoMatches ? 1 : 3"
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
                            v-if="newDealGameNoMatches"
                            class="quick-create quick-create--game-empty"
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
                        <div v-if="newDeal.deal_type_code === 'rental'" class="deal-form__double">
                          <label class="field">
                            <span class="label">Тип слота</span>
                            <select
                              v-model="newDeal.slot_type_code"
                              class="input input--select"
                              :disabled="!newDeal.game_id || dealSlotAvailabilityLoadingNew"
                            >
                              <option value="">{{ !newDeal.game_id ? 'Сначала выберите игру' : (dealSlotAvailabilityLoadingNew ? '(формируется список)' : '— не выбрано —') }}</option>
                              <option
                                v-for="st in getDealSlotTypeOptions('new')"
                                :key="st.code"
                                :value="st.code"
                                :disabled="!st.supported"
                              >
                                {{ getDealSlotTypeLabel(st) }}
                              </option>
                            </select>
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
                        <label v-if="newDeal.deal_type_code === 'rental'" class="field">
                          <span
                            v-if="dealAccountsForGameLoading || !newDeal.game_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForNew.length || newDeal.account_id"
                            class="label"
                          >
                            Аккаунт
                          </span>
                          <select
                            v-if="dealAccountsForGameLoading || !newDeal.game_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForNew.length || newDeal.account_id"
                            v-model.number="newDeal.account_id"
                            class="input input--select"
                            :disabled="!newDeal.game_id || !newDeal.slot_type_code || isDealSlotTypeUnsupported('new') || dealAccountsForGameLoading"
                          >
                            <option value="">
                              {{ !newDeal.game_id ? 'Сначала выберите игру' : (!newDeal.slot_type_code ? 'Сначала выберите слот' : (dealAccountsForGameLoading ? '(формируется список)' : '— не выбрано —')) }}
                            </option>
                            <option v-for="a in dealAccountsForNew" :key="a.account_id" :value="a.account_id">
                              {{ a.login_full || a.account_id }}
                            </option>
                          </select>
                          <div
                            v-if="!dealAccountsForGameLoading && newDeal.game_id && newDeal.slot_type_code && !newDeal.account_id && !isDealSlotTypeUnsupported('new') && !hasFreeDealSlots('new')"
                            class="quick-create"
                          >
                            <div class="quick-create__title">
                              {{ hasAnyGameAssignmentsNew ? 'Нет свободных слотов — можно снять занятый' : 'Нет аккаунтов с игрой' }}
                            </div>
                            <div v-if="hasAnyGameAssignmentsNew && dealGameAssignmentsLoadingNew" class="loader-wrap loader-wrap--compact">
                              <div class="newtons-cradle" aria-label="Loading" role="img">
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                                <div class="newtons-cradle__dot"></div>
                              </div>
                            </div>
                            <div v-else-if="hasAnyGameAssignmentsNew && dealGameAssignmentsForSelectedSlotNew.length" class="quick-create__table-scroll">
                              <table class="table table--compact table--dense">
                                <thead>
                                  <tr>
                                    <th>Аккаунт</th>
                                    <th>Слот</th>
                                    <th>Покупатель</th>
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
                            </div>
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
                            <div class="newtons-cradle" aria-label="Loading" role="img">
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                              <div class="newtons-cradle__dot"></div>
                            </div>
                          </div>
                          <table v-else-if="dealAccountAssignmentsNew.filter((s) => !s.released_at).length" class="table table--compact table--dense">
                            <thead>
                              <tr>
                                <th>Слот</th>
                                <th>Игра</th>
                                <th>Покупатель</th>
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
                        <div v-if="newDeal.deal_type_code === 'rental'" class="field field--comment-collapsible">
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
                        <div v-if="newDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-auth">
                          <label class="field">
                            <span class="label">Покупатель</span>
                            <input v-model.trim="newDeal.customer_nickname" class="input" placeholder="-" />
                          </label>
                          <label class="field">
                            <span class="label">Логин</span>
                            <input v-model.trim="newDeal.login" class="input" placeholder="-" />
                          </label>
                          <label class="field">
                            <span class="label">Пароль</span>
                            <input v-model.trim="newDeal.password" class="input" placeholder="-"/>
                          </label>
                        </div>
                        <div v-if="newDeal.deal_type_code === 'sale'" class="deal-form__triple deal-form__triple--sale-costs">
                          <label class="field">
                            <span class="label">Регион</span>
                            <select v-model="newDeal.region_code" class="input input--select">
                              <option value="">— не выбрано —</option>
                              <option v-for="r in regions" :key="r.code" :value="r.code">
                                {{ r.name }} ({{ r.code }})
                              </option>
                            </select>
                          </label>
                          <label class="field">
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
                        <label v-if="newDeal.deal_type_code === 'sale'" class="field">
                          <span class="label">Ссылка на игру</span>
                          <input v-model.trim="newDeal.game_link" class="input" placeholder="https://..." />
                        </label>
                        <div v-if="newDeal.deal_type_code === 'sale'" class="field field--comment-collapsible">
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
                      <div class="deal-form__full">
                        <p v-if="dealError" class="bad">{{ dealError }}</p>
                        <p v-if="dealOk" class="ok">{{ dealOk }}</p>
                        <div class="toolbar-actions"></div>
                      </div>
                    </div>
</template>

<script setup>
import { reactive, toRefs } from 'vue'

// Большая форма сделки (режим редактирования и создания) вынесена из WorkView.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  editDeal,
  dealEditMode,
  dealAccountsForGameLoading,
  isDealSlotTypeUnsupported,
  dealAccountsForEdit,
  getSlotTypeLabel,
  dealSlotAvailabilityLoadingEdit,
  getDealSlotTypeOptions,
  getDealSlotTypeLabel,
  getAccountLabelById,
  hasFreeDealSlots,
  hasAnyGameAssignmentsEdit,
  dealGameAssignmentsLoadingEdit,
  dealGameAssignmentsForSelectedSlotEdit,
  accountSlotReleaseLoading,
  releaseSlotFromDeal,
  quickEditAccount,
  domains,
  platforms,
  quickEditAccountLoading,
  createQuickAccount,
  quickEditAccountError,
  accountSlotStatusEdit,
  slotTypes,
  getSortedSlotStatus,
  dealAccountAssignmentsLoadingEdit,
  dealAccountAssignmentsEdit,
  formatDateTimeMinutes,
  getRegionLabel,
  regions,
  getSourceLabelById,
  sourcesByCode,
  maxDate,
  maxPrice,
  clampPrice,
  getFlowStatusLabel,
  dealFlowStatusOptions,
  editDealGameSearch,
  onEditDealGameSearch,
  filteredEditDealGames,
  syncEditDealGameSearch,
  getGameLabelById,
  editDealGameNoMatches,
  clearEditDealGame,
  quickEditGame,
  quickEditGameLoading,
  createQuickGame,
  quickEditGameError,
  getNotesRows,
  dealError,
  dealOk,
  newDeal,
  responsibleUserOptions,
  newDealResponsible,
  editDealResponsible,
  newDealGameSearch,
  onNewDealGameSearch,
  filteredNewDealGames,
  newDealGameNoMatches,
  syncNewDealGameSearch,
  clearNewDealGame,
  quickNewGame,
  quickNewGameLoading,
  quickNewGameError,
  dealSlotAvailabilityLoadingNew,
  dealAccountsForNew,
  hasAnyGameAssignmentsNew,
  dealGameAssignmentsLoadingNew,
  dealGameAssignmentsForSelectedSlotNew,
  quickNewAccount,
  quickNewAccountLoading,
  quickNewAccountError,
  accountSlotStatusNew,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsNew,
  newDealCommentOpen,
  getCompactNotesRows,
} = toRefs(ctx)
</script>
